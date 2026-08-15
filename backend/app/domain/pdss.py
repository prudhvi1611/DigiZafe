"""
Hybrid PDSS (Personal Data Severity Score) — pure domain.

Inspired by CVSS metric groups (Base / Temporal / Environmental) but specialized
for personal digital exposure (not software vulns).

Two-track: Confirmed vs Possible (finding.track).
Surprisal: non-saturating information-style contribution so many medium items still add risk.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _round1(x: float) -> float:
    return round(x + 1e-12, 1)


def severity_band(score: float, bands: dict[str, list[float]]) -> str:
    for name, (lo, hi) in bands.items():
        if lo <= score <= hi:
            return name
    if score <= 0:
        return "none"
    return "critical"


@dataclass
class FindingScoreInput:
    id: str
    kind: str
    source: str
    title: str
    confidence: float
    layer: str
    track: str  # confirmed | possible
    severity_hint: str
    raw_ref: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    observed_at: datetime | None = None
    attribution: str | None = None


@dataclass
class FindingContribution:
    finding_id: str
    kind: str
    source: str
    track: str
    title: str
    base: float
    temporal: float
    environmental: float
    surprisal: float
    reuse: float
    raw_score: float
    weighted_score: float  # after track weight
    drivers: list[dict[str, Any]] = field(default_factory=list)
    vector_fragment: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "kind": self.kind,
            "source": self.source,
            "track": self.track,
            "title": self.title,
            "base": round(self.base, 4),
            "temporal": round(self.temporal, 4),
            "environmental": round(self.environmental, 4),
            "surprisal": round(self.surprisal, 4),
            "reuse": round(self.reuse, 4),
            "raw_score": round(self.raw_score, 4),
            "weighted_score": round(self.weighted_score, 4),
            "drivers": self.drivers,
            "vector_fragment": self.vector_fragment,
        }


@dataclass
class PDSSResult:
    model_version: str
    score_confirmed: float
    score_possible: float
    score_combined: float
    severity: str
    vector: str
    metrics: dict[str, float]
    contributions: list[FindingContribution]
    explanation_summary: str
    counterfactuals: list[dict[str, Any]]
    attributions: list[str]
    computed_at: str
    input_finding_count: int
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_version": self.model_version,
            "score_confirmed": self.score_confirmed,
            "score_possible": self.score_possible,
            "score_combined": self.score_combined,
            "severity": self.severity,
            "vector": self.vector,
            "metrics": self.metrics,
            "contributions": [c.to_dict() for c in self.contributions],
            "explanation_summary": self.explanation_summary,
            "counterfactuals": self.counterfactuals,
            "attributions": self.attributions,
            "computed_at": self.computed_at,
            "input_finding_count": self.input_finding_count,
            "meta": self.meta,
        }


class PDSSEngine:
    def __init__(self, catalog: dict[str, Any]) -> None:
        self.cat = catalog
        self.model_version = str(catalog.get("model_version", "pdss-v1.0.0"))

    def score(
        self,
        findings: list[FindingScoreInput],
        *,
        identifier_type: str = "email",
        identity_edge_count: int = 0,
        now: datetime | None = None,
        exclude_finding_ids: set[str] | None = None,
        compute_counterfactuals: bool = True,
    ) -> PDSSResult:
        now = now or datetime.now(UTC)
        exclude_finding_ids = exclude_finding_ids or set()
        active = [f for f in findings if f.id not in exclude_finding_ids and f.confidence > 0]

        # reuse: same raw_ref or breach_name across sources
        ref_counts: dict[str, int] = {}
        source_by_ref: dict[str, set[str]] = {}
        for f in active:
            ref = (f.raw_ref or f.title or f.id).lower()
            ref_counts[ref] = ref_counts.get(ref, 0) + 1
            source_by_ref.setdefault(ref, set()).add(f.source)

        contribs: list[FindingContribution] = []
        for f in active:
            c = self._score_one(
                f,
                identifier_type=identifier_type,
                identity_edge_count=identity_edge_count,
                ref_counts=ref_counts,
                source_by_ref=source_by_ref,
                now=now,
            )
            contribs.append(c)

        # sort by weighted contribution desc
        contribs.sort(key=lambda x: x.weighted_score, reverse=True)

        confirmed = [c for c in contribs if c.track == "confirmed"]
        possible = [c for c in contribs if c.track != "confirmed"]

        sc_conf = self._aggregate([c.weighted_score for c in confirmed])
        sc_poss = self._aggregate([c.weighted_score for c in possible])

        agg = self.cat.get("aggregation", {})
        w_c = float(agg.get("confirmed_weight", 1.0))
        w_p = float(agg.get("possible_weight", 0.55))
        combined_raw = w_c * sc_conf + w_p * sc_poss
        # soft cap to 10
        combined = _round1(min(10.0, combined_raw))
        sc_conf = _round1(min(10.0, sc_conf))
        sc_poss = _round1(min(10.0, sc_poss))

        bands = self.cat.get("severity_bands", {})
        sev = severity_band(combined, bands)

        metrics = self._aggregate_metrics(contribs)
        vector = self._build_vector(metrics, combined, sev)

        attributions = sorted({
            f.attribution for f in active if f.attribution
        } | {
            "XposedOrNot" for f in active if f.source == "xposedornot"
        })

        summary = self._summary(combined, sev, contribs, sc_conf, sc_poss)
        counterfactuals = []
        if compute_counterfactuals:
            counterfactuals = self._counterfactuals(findings, contribs, identifier_type, identity_edge_count, now)

        return PDSSResult(
            model_version=self.model_version,
            score_confirmed=sc_conf,
            score_possible=sc_poss,
            score_combined=combined,
            severity=sev,
            vector=vector,
            metrics=metrics,
            contributions=contribs[: int(agg.get("max_findings_in_vector_detail", 40))],
            explanation_summary=summary,
            counterfactuals=counterfactuals,
            attributions=attributions,
            computed_at=now.isoformat(),
            input_finding_count=len(active),
            meta={
                "identifier_type": identifier_type,
                "identity_edge_count": identity_edge_count,
                "excluded_count": len(exclude_finding_ids),
            },
        )

    def _score_one(
        self,
        f: FindingScoreInput,
        *,
        identifier_type: str,
        identity_edge_count: int,
        ref_counts: dict[str, int],
        source_by_ref: dict[str, set[str]],
        now: datetime,
    ) -> FindingContribution:
        drivers: list[dict[str, Any]] = []
        kind_w = self.cat.get("kind_base_weights", {}).get(f.kind) or self.cat["kind_base_weights"]["other"]

        S = float(kind_w["sensitivity"])
        D = float(kind_w["discoverability"])
        L = float(kind_w["linkability"])
        I = float(kind_w["impact"])
        drivers.append({"metric": "kind_base", "kind": f.kind, "S": S, "D": D, "L": L, "I": I})

        attrs = f.attributes or {}
        # XposedOrNot / breach enrichments
        xposed = str(attrs.get("xposed_data") or attrs.get("exposed_data") or "")
        boosts = self.cat.get("exposed_data_boosts", {})
        data_boost = 0.0
        hit_types: list[str] = []
        for key, b in boosts.items():
            if key.lower() in xposed.lower() or key.lower() in (f.summary if hasattr(f, "summary") else "").lower():
                data_boost = max(data_boost, float(b))
                hit_types.append(key)
        # also scan attribute values
        for v in attrs.values():
            vs = str(v).lower()
            for key, b in boosts.items():
                if key.lower() in vs:
                    data_boost = max(data_boost, float(b))
                    if key not in hit_types:
                        hit_types.append(key)
        if data_boost:
            S = _clamp(S + data_boost * 0.5)
            I = _clamp(I + data_boost * 0.6)
            drivers.append({"metric": "exposed_data_boost", "boost": data_boost, "types": hit_types[:8]})

        pr = str(attrs.get("password_risk") or "").lower().replace(" ", "")
        pr_map = self.cat.get("password_risk_map", {})
        if pr in pr_map:
            factor = float(pr_map[pr])
            I = _clamp(I * 0.5 + factor * 0.5 + 0.2)
            S = _clamp(S * 0.6 + factor * 0.4)
            drivers.append({"metric": "password_risk", "value": pr, "factor": factor})

        risk_label = str(attrs.get("risk_label") or "").lower()
        rl_map = self.cat.get("risk_label_map", {})
        if risk_label in rl_map:
            rf = float(rl_map[risk_label])
            I = _clamp(max(I, rf * 0.9))
            drivers.append({"metric": "risk_label", "value": risk_label, "factor": rf})

        # confidence modulates base
        conf = _clamp(float(f.confidence))
        base = 10.0 * (0.25 * S + 0.20 * D + 0.20 * L + 0.35 * I) * (0.55 + 0.45 * conf)
        drivers.append({"metric": "confidence", "value": conf})

        # Temporal: recency
        tcfg = self.cat.get("temporal", {})
        half = float(tcfg.get("recency_half_life_days", 730))
        min_rf = float(tcfg.get("min_recency_factor", 0.55))
        recency = 1.0
        year = attrs.get("xposed_date") or attrs.get("year")
        obs = f.observed_at
        age_days = None
        if year and str(year).isdigit():
            try:
                age_days = max(0, now.year - int(year)) * 365.25
            except Exception:
                pass
        if age_days is None and obs is not None:
            if obs.tzinfo is None:
                obs = obs.replace(tzinfo=UTC)
            age_days = max(0.0, (now - obs).total_seconds() / 86400.0)
        if age_days is not None:
            # exponential decay toward min_rf
            recency = min_rf + (1.0 - min_rf) * math.exp(-math.log(2) * age_days / half)
            drivers.append({"metric": "recency", "age_days": round(age_days, 1), "factor": round(recency, 4)})

        # reuse across sources
        ref = (f.raw_ref or f.title or f.id).lower()
        n_src = len(source_by_ref.get(ref, {f.source}))
        reuse_bonus = min(
            max(0, n_src - 1) * float(tcfg.get("reuse_bonus_per_extra_source", 0.08)),
            float(tcfg.get("reuse_bonus_cap", 0.35)),
        )
        temporal = _clamp(recency + reuse_bonus, 0.0, 1.35)
        drivers.append({"metric": "reuse", "distinct_sources": n_src, "bonus": reuse_bonus})

        # Environmental
        ecfg = self.cat.get("environmental", {})
        id_crit = float(ecfg.get("identifier_type_criticality", {}).get(identifier_type, 1.0))
        layer_m = float(self.cat.get("layer_multipliers", {}).get(f.layer, 1.0))
        edge_boost = min(
            identity_edge_count * float(ecfg.get("identity_graph_link_boost_per_edge", 0.04)),
            float(ecfg.get("identity_graph_link_boost_cap", 0.20)),
        )
        environmental = id_crit * layer_m * (1.0 + edge_boost)
        drivers.append({
            "metric": "environmental",
            "identifier_criticality": id_crit,
            "layer_multiplier": layer_m,
            "identity_edge_boost": edge_boost,
        })

        # Surprisal (non-saturating): higher when rare-ish high-impact
        scfg = self.cat.get("surprisal", {})
        # treat lower confidence / unique breach as higher surprisal contribution shape
        rarity = 1.0 / math.sqrt(max(1, ref_counts.get(ref, 1)))
        impactish = (S + I) / 2.0
        surprisal_raw = float(scfg.get("base", 2.0)) * impactish * rarity * conf
        surprisal = min(float(scfg.get("cap_contribution", 4.5)), float(scfg.get("scale", 1.35)) * surprisal_raw)
        drivers.append({"metric": "surprisal", "rarity": round(rarity, 4), "value": round(surprisal, 4)})

        # Combine finding-level score (0..~12 before clamp)
        raw = (base * temporal * environmental) / 10.0 * 6.5 + surprisal * 0.55
        raw = _clamp(raw, 0.0, 10.0)

        track = (f.track or "possible").lower()
        track_w = 1.0 if track == "confirmed" else float(self.cat.get("aggregation", {}).get("possible_weight", 0.55))
        weighted = raw * track_w

        # fragment vector for this finding
        frag = (
            f"S:{S:.2f}/D:{D:.2f}/L:{L:.2f}/I:{I:.2f}/"
            f"T:{temporal:.2f}/E:{environmental:.2f}/U:{surprisal:.2f}/R:{reuse_bonus:.2f}"
        )

        return FindingContribution(
            finding_id=f.id,
            kind=f.kind,
            source=f.source,
            track=track,
            title=f.title,
            base=base,
            temporal=temporal,
            environmental=environmental,
            surprisal=surprisal,
            reuse=reuse_bonus,
            raw_score=raw,
            weighted_score=weighted,
            drivers=drivers,
            vector_fragment=frag,
        )

    def _aggregate(self, scores: list[float]) -> float:
        """Diminishing aggregation so N findings don't linear-explode."""
        if not scores:
            return 0.0
        k = float(self.cat.get("aggregation", {}).get("diminishing_k", 0.65))
        scores = sorted(scores, reverse=True)
        total = 0.0
        for i, s in enumerate(scores):
            total += s * (k**i)
        # map into 0..10-ish
        return min(10.0, total * 0.85)

    def _aggregate_metrics(self, contribs: list[FindingContribution]) -> dict[str, float]:
        if not contribs:
            return {"S": 0, "D": 0, "L": 0, "I": 0, "T": 0, "E": 0, "U": 0, "R": 0}
        # average of top-5 fragments approx via fields
        top = contribs[:5]
        n = len(top)
        return {
            "S": round(sum(c.base for c in top) / n / 10.0, 3),  # normalized-ish
            "D": round(sum(1 for _ in top) / n, 3),  # placeholder density
            "L": round(sum(c.reuse for c in top) / max(n, 1), 3),
            "I": round(sum(c.raw_score for c in top) / n / 10.0, 3),
            "T": round(sum(c.temporal for c in top) / n, 3),
            "E": round(sum(c.environmental for c in top) / n, 3),
            "U": round(sum(c.surprisal for c in top) / n, 3),
            "R": round(sum(c.reuse for c in top) / n, 3),
        }

    def _build_vector(self, metrics: dict[str, float], combined: float, sev: str) -> str:
        # PDSS:1.0/S:x/D:x/L:x/I:x/T:x/E:x/U:x/R:x/SC:score/SV:sev
        parts = [f"PDSS:{self.model_version}"]
        for k in ("S", "D", "L", "I", "T", "E", "U", "R"):
            parts.append(f"{k}:{metrics.get(k, 0):.2f}")
        parts.append(f"SC:{combined:.1f}")
        parts.append(f"SV:{sev}")
        return "/".join(parts)

    def _summary(
        self,
        combined: float,
        sev: str,
        contribs: list[FindingContribution],
        sc_conf: float,
        sc_poss: float,
    ) -> str:
        if not contribs:
            return "No findings — PDSS is 0 (no exposure signals in scope)."
        top = contribs[0]
        xpn = sum(1 for c in contribs if c.source == "xposedornot")
        return (
            f"PDSS {combined:.1f} ({sev}). "
            f"Confirmed track {sc_conf:.1f}, possible track {sc_poss:.1f}. "
            f"Top driver: [{top.source}] {top.title} (weighted {top.weighted_score:.2f}). "
            f"Findings scored: {len(contribs)}"
            + (f", of which {xpn} from XposedOrNot." if xpn else ".")
        )

    def _counterfactuals(
        self,
        all_findings: list[FindingScoreInput],
        contribs: list[FindingContribution],
        identifier_type: str,
        identity_edge_count: int,
        now: datetime,
    ) -> list[dict[str, Any]]:
        """What-if: remove top contributors one at a time."""
        out: list[dict[str, Any]] = []
        base_score = self._aggregate([c.weighted_score for c in contribs if c.track == "confirmed"]) * float(
            self.cat.get("aggregation", {}).get("confirmed_weight", 1.0)
        ) + self._aggregate([c.weighted_score for c in contribs if c.track != "confirmed"]) * float(
            self.cat.get("aggregation", {}).get("possible_weight", 0.55)
        )
        base_score = min(10.0, base_score)

        for c in contribs[:5]:
            res = self.score(
                all_findings,
                identifier_type=identifier_type,
                identity_edge_count=identity_edge_count,
                now=now,
                exclude_finding_ids={c.finding_id},
                compute_counterfactuals=False,
            )
            delta = round(base_score - res.score_combined, 2)
            out.append({
                "action": "remove_finding",
                "finding_id": c.finding_id,
                "title": c.title,
                "source": c.source,
                "score_before": round(base_score, 1),
                "score_after": res.score_combined,
                "delta": delta,
                "narrative": f"If '{c.title}' were remediated/removed, estimated PDSS {res.score_combined:.1f} (Δ {delta}).",
            })
        return out
