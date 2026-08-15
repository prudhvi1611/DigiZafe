# DigiZafe — Sprint 5 Identity Graph & PDSS Scoring  
**Complete Implementation Guide from Sprint 4 Baseline + All File Contents**

**Document version:** 1.0  
**Based on:** MASTER_ENGINEERING_CONTEXT.md v2.1  
**Depends on:** Sprint 0–4 green (Auth, Identifiers, Verification, Connectors, Discovery & Evidence with findings from XposedOrNot primary)  
**Goal:** From completed Sprint 4 → **Identity Graph** (deciban / Fellegi–Sunter-style pairwise linkage + collision review), **full hybrid PDSS** (CVSS-inspired Base / Temporal / Environmental vector + non-saturating surprisal, two-track Confirmed / Possible), **durable explanation records** (drivers, counterfactuals, XposedOrNot fields), **model card v1**, **score history**, and **what-if simulator**.

**Effort estimate:** ~12 days (solo)  
**Critical path next:** Sprint 6 Recommendations & Alerts

> **Load MASTER_ENGINEERING_CONTEXT.md first in every session.**  
> You implement; you do not re-decide architecture.  
> Domain is pure (no I/O). Scoring is deterministic + versioned. Every score contribution must be explainable (G3).

---

# PART A — Pre-Sprint 5 (run once from DigiZafe root)

```bash
# 1. Confirm Sprint 4 is green
docker compose ps
curl -s http://localhost:8000/api/v1/health | jq .
# Must have: verified identifier → scan → findings (incl. source=xposedornot)

# 2. Package dirs
mkdir -p backend/app/domain
mkdir -p backend/app/{services,repositories,models,schemas,tasks}
mkdir -p shared/score_model
mkdir -p docs/model-cards
mkdir -p backend/tests/unit
touch backend/app/domain/__init__.py

# 3. Optional: no new hard deps (pure Python PDSS). NetworkX optional for graph viz later.
# Keep pure adjacency in Postgres for MVP.

docker compose build api worker beat
echo "✅ Pre-Sprint 5 ready. Apply file contents below."
```

---

# PART B — Sprint 5 File Contents

---

## 1. UPDATE: Root `.env.example` (append)

```bash
# === Sprint 5: Identity Graph & PDSS ===
PDSS_MODEL_VERSION=pdss-v1.0.0
PDSS_CATALOG_PATH=./shared/score_model/pdss_catalog.json
DECIBAN_WEIGHTS_PATH=./shared/score_model/deciban-weights.json

# Linkage thresholds (deciban / match weight → probability)
LINKAGE_AUTO_LINK_PROB=0.95
LINKAGE_REVIEW_PROB=0.70
LINKAGE_COLLISION_FLAG_PROB=0.50

# Scoring
SCORE_HISTORY_RETENTION_DAYS=365
WHATIF_MAX_FINDINGS_REMOVED=50
```

Merge into your real `.env`.

---

## 2. UPDATE: `backend/app/core/config.py`

Add to `Settings` (keep all prior fields):

```python
    # === Sprint 5: Identity & PDSS ===
    pdss_model_version: str = "pdss-v1.0.0"
    pdss_catalog_path: str = "./shared/score_model/pdss_catalog.json"
    deciban_weights_path: str = "./shared/score_model/deciban-weights.json"

    linkage_auto_link_prob: float = 0.95
    linkage_review_prob: float = 0.70
    linkage_collision_flag_prob: float = 0.50

    score_history_retention_days: int = 365
    whatif_max_findings_removed: int = 50
```

---

## 3. NEW: `shared/score_model/pdss_catalog.json`

```json
{
  "model_version": "pdss-v1.0.0",
  "description": "Hybrid Personal Data Severity Score — CVSS-inspired Base/Temporal/Environmental + surprisal two-track",
  "score_range": [0.0, 10.0],
  "tracks": ["confirmed", "possible"],
  "severity_bands": {
    "none": [0.0, 0.0],
    "low": [0.1, 3.9],
    "medium": [4.0, 6.9],
    "high": [7.0, 8.9],
    "critical": [9.0, 10.0]
  },
  "kind_base_weights": {
    "breach": {
      "sensitivity": 0.75,
      "discoverability": 0.85,
      "linkability": 0.70,
      "impact": 0.80
    },
    "password_exposure": {
      "sensitivity": 0.95,
      "discoverability": 0.90,
      "linkability": 0.85,
      "impact": 0.95
    },
    "certificate": {
      "sensitivity": 0.25,
      "discoverability": 0.90,
      "linkability": 0.55,
      "impact": 0.30
    },
    "dns_rdap": {
      "sensitivity": 0.20,
      "discoverability": 0.85,
      "linkability": 0.40,
      "impact": 0.25
    },
    "profile": {
      "sensitivity": 0.40,
      "discoverability": 0.80,
      "linkability": 0.60,
      "impact": 0.35
    },
    "username_presence": {
      "sensitivity": 0.35,
      "discoverability": 0.75,
      "linkability": 0.55,
      "impact": 0.30
    },
    "serp": {
      "sensitivity": 0.30,
      "discoverability": 0.70,
      "linkability": 0.45,
      "impact": 0.25
    },
    "other": {
      "sensitivity": 0.30,
      "discoverability": 0.50,
      "linkability": 0.40,
      "impact": 0.30
    }
  },
  "exposed_data_boosts": {
    "passwords": 0.25,
    "password": 0.25,
    "plaintext": 0.30,
    "ssn": 0.35,
    "social security": 0.35,
    "credit card": 0.30,
    "phone": 0.10,
    "address": 0.12,
    "date of birth": 0.15,
    "email": 0.05,
    "username": 0.05,
    "ip": 0.08,
    "photos": 0.08,
    "financial": 0.28
  },
  "password_risk_map": {
    "plaintext": 1.0,
    "easytocrack": 0.85,
    "easy_to_crack": 0.85,
    "hardtocrack": 0.45,
    "hard_to_crack": 0.45,
    "unknown": 0.55
  },
  "risk_label_map": {
    "critical": 1.0,
    "high": 0.85,
    "medium": 0.55,
    "low": 0.30,
    "unknown": 0.40
  },
  "layer_multipliers": {
    "surface": 1.0,
    "deep": 1.08,
    "constrained_dark": 1.15
  },
  "temporal": {
    "recency_half_life_days": 730,
    "min_recency_factor": 0.55,
    "reuse_bonus_per_extra_source": 0.08,
    "reuse_bonus_cap": 0.35
  },
  "environmental": {
    "identifier_type_criticality": {
      "email": 1.0,
      "phone": 1.05,
      "domain": 0.9,
      "username": 0.85,
      "github_username": 0.9,
      "password": 1.15
    },
    "identity_graph_link_boost_per_edge": 0.04,
    "identity_graph_link_boost_cap": 0.20
  },
  "surprisal": {
    "base": 2.0,
    "scale": 1.35,
    "cap_contribution": 4.5
  },
  "aggregation": {
    "confirmed_weight": 1.0,
    "possible_weight": 0.55,
    "diminishing_k": 0.65,
    "max_findings_in_vector_detail": 40
  },
  "vector_metric_labels": {
    "S": "Sensitivity",
    "D": "Discoverability",
    "L": "Linkability",
    "I": "Impact",
    "T": "Temporal",
    "E": "Environmental",
    "U": "Surprisal",
    "R": "Reuse"
  }
}
```

---

## 4. NEW: `shared/score_model/deciban-weights.json`

```json
{
  "model_version": "linkage-v1.0.0",
  "description": "Fellegi–Sunter style partial match weights in log2 (deciban-like) units for identity graph edges among a user's own identifiers",
  "prior_match_prob": 0.02,
  "comparisons": {
    "same_user_ownership": {
      "agree_weight": 6.0,
      "disagree_weight": -8.0,
      "note": "All DigiZafe identifiers already share user_id; this is always agree for in-user graph"
    },
    "type_pair": {
      "email_email": 1.2,
      "email_username": 0.8,
      "email_github_username": 1.0,
      "email_domain": 0.6,
      "email_phone": 0.5,
      "username_github_username": 2.5,
      "username_username": 1.0,
      "domain_domain": 1.5,
      "phone_phone": 2.0,
      "default": 0.3
    },
    "canonical_similarity": {
      "exact": 5.0,
      "local_part_match": 2.5,
      "domain_part_match": 1.5,
      "substring": 1.0,
      "none": -1.5
    },
    "shared_finding_sources": {
      "per_shared_source": 0.6,
      "cap": 3.0
    },
    "shared_breach_names": {
      "per_shared_breach": 0.4,
      "cap": 2.5
    },
    "profile_url_overlap": {
      "agree": 2.0,
      "disagree": 0.0
    }
  },
  "thresholds": {
    "auto_link_prob": 0.95,
    "review_prob": 0.70,
    "collision_flag_prob": 0.50
  }
}
```

---

## 5. NEW: `backend/app/domain/linkage.py`  
*(pure — deciban / F–S style)*

```python
"""Identity linkage (pure). Fellegi–Sunter-style match weights in log2 units."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional


def match_weight_to_prob(weight: float) -> float:
    """p = 2^w / (1 + 2^w)"""
    # numerically stable
    if weight >= 30:
        return 1.0
    if weight <= -30:
        return 0.0
    t = 2.0**weight
    return t / (1.0 + t)


def prior_weight(prior_prob: float) -> float:
    p = min(max(prior_prob, 1e-9), 1.0 - 1e-9)
    return math.log2(p / (1.0 - p))


@dataclass
class IdentifierView:
    id: str
    type: str
    value_canonical: str
    is_verified: bool = True
    finding_sources: list[str] = field(default_factory=list)
    breach_names: list[str] = field(default_factory=list)
    profile_urls: list[str] = field(default_factory=list)


@dataclass
class LinkEvidence:
    component: str
    weight: float
    detail: str


@dataclass
class LinkResult:
    left_id: str
    right_id: str
    match_weight: float
    match_prob: float
    decision: str  # auto_link | review | weak | none
    evidence: list[LinkEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_id": self.left_id,
            "right_id": self.right_id,
            "match_weight": round(self.match_weight, 4),
            "match_prob": round(self.match_prob, 6),
            "decision": self.decision,
            "evidence": [
                {"component": e.component, "weight": round(e.weight, 4), "detail": e.detail}
                for e in self.evidence
            ],
        }


def _type_pair_key(a: str, b: str) -> str:
    x, y = sorted([a, b])
    return f"{x}_{y}"


def _canonical_similarity(a: IdentifierView, b: IdentifierView, weights: dict) -> LinkEvidence:
    wcfg = weights.get("canonical_similarity", {})
    va, vb = a.value_canonical.lower(), b.value_canonical.lower()
    if va == vb:
        return LinkEvidence("canonical_similarity", float(wcfg.get("exact", 5.0)), "exact canonical match")

    # email local / domain
    if a.type == "email" and b.type == "email":
        la, _, da = va.partition("@")
        lb, _, db = vb.partition("@")
        if la and la == lb:
            return LinkEvidence("canonical_similarity", float(wcfg.get("local_part_match", 2.5)), "email local-part match")
        if da and da == db:
            return LinkEvidence("canonical_similarity", float(wcfg.get("domain_part_match", 1.5)), "email domain match")

    # username contained in email local
    if {a.type, b.type} >= {"email", "username"} or {a.type, b.type} >= {"email", "github_username"}:
        email = va if a.type == "email" else vb
        user = vb if a.type == "email" else va
        local = email.split("@", 1)[0]
        if user and user in local:
            return LinkEvidence("canonical_similarity", float(wcfg.get("substring", 1.0)), "username in email local-part")

    if va in vb or vb in va:
        return LinkEvidence("canonical_similarity", float(wcfg.get("substring", 1.0)), "substring overlap")

    return LinkEvidence("canonical_similarity", float(wcfg.get("none", -1.5)), "no canonical similarity")


def score_pair(
    left: IdentifierView,
    right: IdentifierView,
    weights: dict[str, Any],
    *,
    auto_link_prob: float = 0.95,
    review_prob: float = 0.70,
    collision_flag_prob: float = 0.50,
) -> LinkResult:
    if left.id == right.id:
        return LinkResult(left.id, right.id, 99.0, 1.0, "auto_link", [
            LinkEvidence("identity", 99.0, "same identifier")
        ])

    evidence: list[LinkEvidence] = []
    prior_p = float(weights.get("prior_match_prob", 0.02))
    pw = prior_weight(prior_p)
    evidence.append(LinkEvidence("prior", pw, f"prior_match_prob={prior_p}"))

    # same-user ownership (always true in DigiZafe self-graph)
    own = weights.get("comparisons", {}).get("same_user_ownership", {})
    evidence.append(
        LinkEvidence("same_user_ownership", float(own.get("agree_weight", 6.0)), "both owned by same verified user")
    )

    # type pair
    tp = weights.get("comparisons", {}).get("type_pair", {})
    key = _type_pair_key(left.type, right.type)
    tw = float(tp.get(key, tp.get("default", 0.3)))
    evidence.append(LinkEvidence("type_pair", tw, f"{left.type}+{right.type}"))

    # canonical similarity
    evidence.append(_canonical_similarity(left, right, weights.get("comparisons", {})))

    # shared finding sources
    s_cfg = weights.get("comparisons", {}).get("shared_finding_sources", {})
    shared_src = set(left.finding_sources) & set(right.finding_sources)
    sw = min(len(shared_src) * float(s_cfg.get("per_shared_source", 0.6)), float(s_cfg.get("cap", 3.0)))
    evidence.append(LinkEvidence("shared_finding_sources", sw, f"shared={sorted(shared_src)}"))

    # shared breach names (strong XposedOrNot signal across emails/usernames co-owned)
    b_cfg = weights.get("comparisons", {}).get("shared_breach_names", {})
    shared_b = set(left.breach_names) & set(right.breach_names)
    bw = min(len(shared_b) * float(b_cfg.get("per_shared_breach", 0.4)), float(b_cfg.get("cap", 2.5)))
    evidence.append(
        LinkEvidence(
            "shared_breach_names",
            bw,
            f"shared_breaches={sorted(list(shared_b))[:10]} count={len(shared_b)}",
        )
    )

    # profile URL overlap
    p_cfg = weights.get("comparisons", {}).get("profile_url_overlap", {})
    shared_urls = set(u.lower() for u in left.profile_urls) & set(u.lower() for u in right.profile_urls)
    if shared_urls:
        evidence.append(
            LinkEvidence("profile_url_overlap", float(p_cfg.get("agree", 2.0)), f"urls={list(shared_urls)[:3]}")
        )
    else:
        evidence.append(LinkEvidence("profile_url_overlap", float(p_cfg.get("disagree", 0.0)), "no shared profile URLs"))

    total = sum(e.weight for e in evidence)
    prob = match_weight_to_prob(total)

    if prob >= auto_link_prob:
        decision = "auto_link"
    elif prob >= review_prob:
        decision = "review"
    elif prob >= collision_flag_prob:
        decision = "weak"
    else:
        decision = "none"

    return LinkResult(
        left_id=left.id,
        right_id=right.id,
        match_weight=total,
        match_prob=prob,
        decision=decision,
        evidence=evidence,
    )


def build_edges(
    identifiers: list[IdentifierView],
    weights: dict[str, Any],
    **threshold_kwargs: float,
) -> list[LinkResult]:
    edges: list[LinkResult] = []
    for i in range(len(identifiers)):
        for j in range(i + 1, len(identifiers)):
            edges.append(score_pair(identifiers[i], identifiers[j], weights, **threshold_kwargs))
    return edges
```

---

## 6. NEW: `backend/app/domain/pdss.py`  
*(pure hybrid PDSS + surprisal)*

```python
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
from datetime import datetime, timezone
from typing import Any, Optional


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
    raw_ref: Optional[str] = None
    attributes: dict[str, Any] = field(default_factory=dict)
    observed_at: Optional[datetime] = None
    attribution: Optional[str] = None


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
    ) -> PDSSResult:
        now = now or datetime.now(timezone.utc)
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
                obs = obs.replace(tzinfo=timezone.utc)
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
```

---

## 7. NEW: `backend/app/models/identity.py`

```python
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IdentityEdge(Base):
    """Pairwise link between two identifiers of the same user."""

    __tablename__ = "identity_edges"
    __table_args__ = (
        UniqueConstraint("user_id", "left_identifier_id", "right_identifier_id", name="uq_identity_edge_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    left_identifier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    right_identifier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=False
    )

    match_weight: Mapped[float] = mapped_column(Float, nullable=False)
    match_prob: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # auto_link | review | weak | none | accepted | rejected

    evidence: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="linkage-v1.0.0")

    # Human review
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    # open | accepted | rejected
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class IdentityCollision(Base):
    """Flagged potential collisions for manual review."""

    __tablename__ = "identity_collisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    edge_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_edges.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

---

## 8. NEW: `backend/app/models/score.py`

```python
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScoreSnapshot(Base):
    """Durable PDSS result for a user scope (per identifier or whole identity)."""

    __tablename__ = "score_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # null identifier_id = whole-user / identity-graph aggregate
    identifier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=True
    )

    model_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    score_confirmed: Mapped[float] = mapped_column(Float, nullable=False)
    score_possible: Mapped[float] = mapped_column(Float, nullable=False)
    score_combined: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    vector: Mapped[str] = mapped_column(String(512), nullable=False)

    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    contributions: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    counterfactuals: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    attributions: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    explanation_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    # manual | post_scan | whatif | revalidate

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )


class ExplanationRecord(Base):
    """Durable explainability record (G3) — redacted drivers only."""

    __tablename__ = "explanation_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_snapshots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    finding_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)

    kind: Mapped[str] = mapped_column(String(64), nullable=False)  # contribution | counterfactual | summary
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # drivers, vector_fragment, narrative, etc.

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

---

## 9. UPDATE: `backend/app/models/__init__.py`

```python
from app.models.user import User, RefreshToken
from app.models.audit import AuditLog
from app.models.identifier import Identifier, VerificationChallenge
from app.models.consent_egress import ConsentRecord, EgressLedger
from app.models.connector_config import ConnectorConfig
from app.models.scan import Scan, ScanConnectorRun
from app.models.observation_finding import Observation, Finding, EvidenceBlob
from app.models.identity import IdentityEdge, IdentityCollision
from app.models.score import ScoreSnapshot, ExplanationRecord

__all__ = [
    "User", "RefreshToken", "AuditLog",
    "Identifier", "VerificationChallenge",
    "ConsentRecord", "EgressLedger",
    "ConnectorConfig",
    "Scan", "ScanConnectorRun",
    "Observation", "Finding", "EvidenceBlob",
    "IdentityEdge", "IdentityCollision",
    "ScoreSnapshot", "ExplanationRecord",
]
```

---

## 10. NEW: `backend/app/schemas/identity_score.py`

```python
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class IdentityEdgePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    left_identifier_id: UUID
    right_identifier_id: UUID
    match_weight: float
    match_prob: float
    decision: str
    evidence: Optional[dict[str, Any]] = None
    review_status: str
    review_note: Optional[str] = None
    model_version: str
    created_at: datetime


class IdentityGraphPublic(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[IdentityEdgePublic]
    collisions: list[dict[str, Any]] = []
    model_version: str


class EdgeReviewRequest(BaseModel):
    review_status: str = Field(..., pattern="^(accepted|rejected)$")
    review_note: Optional[str] = None


class ScoreRequest(BaseModel):
    identifier_id: Optional[UUID] = None  # null = whole identity
    persist: bool = True
    trigger: str = "manual"


class WhatIfRequest(BaseModel):
    identifier_id: Optional[UUID] = None
    exclude_finding_ids: list[UUID] = Field(default_factory=list)
    # optional: simulate removing kinds/sources
    exclude_sources: list[str] = Field(default_factory=list)
    exclude_kinds: list[str] = Field(default_factory=list)


class ScorePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    identifier_id: Optional[UUID] = None
    model_version: str
    score_confirmed: float
    score_possible: float
    score_combined: float
    severity: str
    vector: str
    metrics: Optional[dict[str, Any]] = None
    contributions: Optional[list[Any]] = None
    counterfactuals: Optional[list[Any]] = None
    attributions: Optional[list[Any]] = None
    explanation_summary: str
    finding_count: int = 0
    trigger: str = "manual"
    created_at: Optional[datetime] = None
    meta: Optional[dict[str, Any]] = None


class ScoreHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: Optional[UUID] = None
    score_combined: float
    severity: str
    model_version: str
    trigger: str
    finding_count: int
    created_at: datetime


class Message(BaseModel):
    message: str
```

---

## 11. NEW: `backend/app/repositories/identity_repository.py`

```python
from __future__ import annotations

import uuid
from typing import Any, Optional, Sequence

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import IdentityEdge, IdentityCollision


def _ordered_pair(a: uuid.UUID, b: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    return (a, b) if str(a) <= str(b) else (b, a)


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_edges(self, user_id: uuid.UUID) -> Sequence[IdentityEdge]:
        result = await self.session.execute(
            select(IdentityEdge).where(IdentityEdge.user_id == user_id).order_by(IdentityEdge.match_prob.desc())
        )
        return result.scalars().all()

    async def upsert_edge(
        self,
        *,
        user_id: uuid.UUID,
        left_id: uuid.UUID,
        right_id: uuid.UUID,
        match_weight: float,
        match_prob: float,
        decision: str,
        evidence: dict[str, Any] | None,
        model_version: str,
    ) -> IdentityEdge:
        left_id, right_id = _ordered_pair(left_id, right_id)
        result = await self.session.execute(
            select(IdentityEdge).where(
                IdentityEdge.user_id == user_id,
                IdentityEdge.left_identifier_id == left_id,
                IdentityEdge.right_identifier_id == right_id,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.match_weight = match_weight
            row.match_prob = match_prob
            row.decision = decision
            row.evidence = evidence
            row.model_version = model_version
            await self.session.flush()
            return row
        row = IdentityEdge(
            user_id=user_id,
            left_identifier_id=left_id,
            right_identifier_id=right_id,
            match_weight=match_weight,
            match_prob=match_prob,
            decision=decision,
            evidence=evidence,
            model_version=model_version,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_edge(self, edge_id: uuid.UUID, user_id: uuid.UUID) -> Optional[IdentityEdge]:
        result = await self.session.execute(
            select(IdentityEdge).where(IdentityEdge.id == edge_id, IdentityEdge.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def set_review(
        self, edge: IdentityEdge, status: str, note: str | None
    ) -> IdentityEdge:
        edge.review_status = status
        edge.review_note = note
        if status == "accepted":
            edge.decision = "auto_link"
        elif status == "rejected":
            edge.decision = "none"
        await self.session.flush()
        return edge

    async def count_accepted_edges(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(IdentityEdge).where(
                IdentityEdge.user_id == user_id,
                or_(
                    IdentityEdge.decision == "auto_link",
                    IdentityEdge.review_status == "accepted",
                ),
            )
        )
        return len(result.scalars().all())

    async def add_collision(
        self,
        *,
        user_id: uuid.UUID,
        edge_id: uuid.UUID | None,
        reason: str,
        details: dict | None,
    ) -> IdentityCollision:
        row = IdentityCollision(
            user_id=user_id, edge_id=edge_id, reason=reason, details=details
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_collisions(self, user_id: uuid.UUID, unresolved_only: bool = True) -> Sequence[IdentityCollision]:
        q = select(IdentityCollision).where(IdentityCollision.user_id == user_id)
        if unresolved_only:
            q = q.where(IdentityCollision.resolved.is_(False))
        result = await self.session.execute(q.order_by(IdentityCollision.created_at.desc()))
        return result.scalars().all()
```

---

## 12. NEW: `backend/app/repositories/score_repository.py`

```python
from __future__ import annotations

import uuid
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.score import ScoreSnapshot, ExplanationRecord


class ScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_snapshot(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID | None,
        payload: dict[str, Any],
        trigger: str,
    ) -> ScoreSnapshot:
        row = ScoreSnapshot(
            user_id=user_id,
            identifier_id=identifier_id,
            model_version=payload["model_version"],
            score_confirmed=payload["score_confirmed"],
            score_possible=payload["score_possible"],
            score_combined=payload["score_combined"],
            severity=payload["severity"],
            vector=payload["vector"],
            metrics=payload.get("metrics"),
            contributions=payload.get("contributions"),
            counterfactuals=payload.get("counterfactuals"),
            attributions=payload.get("attributions"),
            explanation_summary=payload.get("explanation_summary") or "",
            meta=payload.get("meta"),
            finding_count=payload.get("input_finding_count") or 0,
            trigger=trigger,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_explanation(
        self,
        *,
        user_id: uuid.UUID,
        score_snapshot_id: uuid.UUID,
        kind: str,
        title: str,
        body: dict[str, Any],
        finding_id: uuid.UUID | None = None,
    ) -> ExplanationRecord:
        row = ExplanationRecord(
            user_id=user_id,
            score_snapshot_id=score_snapshot_id,
            finding_id=finding_id,
            kind=kind,
            title=title,
            body=body,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def latest(
        self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None
    ) -> Optional[ScoreSnapshot]:
        q = select(ScoreSnapshot).where(ScoreSnapshot.user_id == user_id)
        if identifier_id is None:
            q = q.where(ScoreSnapshot.identifier_id.is_(None))
        else:
            q = q.where(ScoreSnapshot.identifier_id == identifier_id)
        q = q.order_by(ScoreSnapshot.created_at.desc()).limit(1)
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def history(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> Sequence[ScoreSnapshot]:
        q = select(ScoreSnapshot).where(ScoreSnapshot.user_id == user_id)
        if identifier_id is not None:
            q = q.where(ScoreSnapshot.identifier_id == identifier_id)
        q = q.order_by(ScoreSnapshot.created_at.desc()).limit(limit)
        result = await self.session.execute(q)
        return result.scalars().all()

    async def get(self, snapshot_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ScoreSnapshot]:
        result = await self.session.execute(
            select(ScoreSnapshot).where(
                ScoreSnapshot.id == snapshot_id, ScoreSnapshot.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_explanations(
        self, snapshot_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[ExplanationRecord]:
        result = await self.session.execute(
            select(ExplanationRecord).where(
                ExplanationRecord.score_snapshot_id == snapshot_id,
                ExplanationRecord.user_id == user_id,
            )
        )
        return result.scalars().all()
```

---

## 13. NEW: `backend/app/services/catalog_loader.py`

```python
"""Load versioned score / linkage catalogs from shared/score_model."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _load_json(path: str) -> dict[str, Any]:
    p = Path(path)
    # try relative to cwd and /app
    candidates = [p, Path("/app") / p, Path("/app/shared") / p.name, Path("shared/score_model") / p.name]
    for c in candidates:
        if c.exists():
            with c.open("r", encoding="utf-8") as f:
                return json.load(f)
    # embedded minimal fallback
    return {
        "model_version": "pdss-v1.0.0-fallback",
        "kind_base_weights": {
            "breach": {"sensitivity": 0.75, "discoverability": 0.85, "linkability": 0.7, "impact": 0.8},
            "other": {"sensitivity": 0.3, "discoverability": 0.5, "linkability": 0.4, "impact": 0.3},
        },
        "severity_bands": {
            "none": [0.0, 0.0],
            "low": [0.1, 3.9],
            "medium": [4.0, 6.9],
            "high": [7.0, 8.9],
            "critical": [9.0, 10.0],
        },
        "aggregation": {"confirmed_weight": 1.0, "possible_weight": 0.55, "diminishing_k": 0.65},
        "surprisal": {"base": 2.0, "scale": 1.35, "cap_contribution": 4.5},
        "temporal": {"recency_half_life_days": 730, "min_recency_factor": 0.55},
        "environmental": {"identifier_type_criticality": {"email": 1.0}},
        "layer_multipliers": {"surface": 1.0},
        "exposed_data_boosts": {"passwords": 0.25},
        "password_risk_map": {},
        "risk_label_map": {},
    }


@lru_cache
def get_pdss_catalog() -> dict[str, Any]:
    settings = get_settings()
    return _load_json(settings.pdss_catalog_path)


@lru_cache
def get_linkage_weights() -> dict[str, Any]:
    settings = get_settings()
    data = _load_json(settings.deciban_weights_path)
    if "prior_match_prob" not in data:
        data = {
            "prior_match_prob": 0.02,
            "comparisons": data.get("comparisons", {}),
            "model_version": data.get("model_version", "linkage-v1.0.0"),
        }
    return data
```

---

## 14. NEW: `backend/app/services/identity_service.py`

```python
from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.linkage import IdentifierView, build_edges
from app.repositories.identity_repository import IdentityRepository
from app.repositories.identifier_repository import IdentifierRepository
from app.repositories.finding_repository import FindingRepository
from app.services.audit_service import AuditService
from app.services.catalog_loader import get_linkage_weights
from app.schemas.identity_score import IdentityGraphPublic, IdentityEdgePublic


class IdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.edges = IdentityRepository(session)
        self.identifiers = IdentifierRepository(session)
        self.findings = FindingRepository(session)
        self.audit = AuditService(session)
        self.settings = get_settings()

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def rebuild_graph(self, user_id: uuid.UUID) -> IdentityGraphPublic:
        await self._set_rls(user_id)
        idents = await self.identifiers.list_for_user(user_id)
        weights = get_linkage_weights()

        views: list[IdentifierView] = []
        for ident in idents:
            flist = await self.findings.list_findings(user_id, identifier_id=ident.id, limit=500)
            sources = sorted({f.source for f in flist})
            breaches = sorted({
                str((f.attributes or {}).get("breach_name") or f.raw_ref or "")
                for f in flist
                if f.kind == "breach"
            } - {""})
            urls = []
            for f in flist:
                u = (f.attributes or {}).get("html_url") or (f.attributes or {}).get("url")
                if u:
                    urls.append(str(u))
            views.append(
                IdentifierView(
                    id=str(ident.id),
                    type=ident.type,
                    value_canonical=ident.value_canonical,
                    is_verified=ident.is_verified,
                    finding_sources=sources,
                    breach_names=breaches,
                    profile_urls=urls,
                )
            )

        results = build_edges(
            views,
            weights,
            auto_link_prob=self.settings.linkage_auto_link_prob,
            review_prob=self.settings.linkage_review_prob,
            collision_flag_prob=self.settings.linkage_collision_flag_prob,
        )

        edge_rows = []
        collisions = []
        for r in results:
            if r.decision == "none":
                continue
            row = await self.edges.upsert_edge(
                user_id=user_id,
                left_id=uuid.UUID(r.left_id),
                right_id=uuid.UUID(r.right_id),
                match_weight=r.match_weight,
                match_prob=r.match_prob,
                decision=r.decision,
                evidence={"items": [e.__dict__ for e in r.evidence]},
                model_version=str(weights.get("model_version", "linkage-v1.0.0")),
            )
            edge_rows.append(row)
            if r.decision in {"review", "weak"}:
                col = await self.edges.add_collision(
                    user_id=user_id,
                    edge_id=row.id,
                    reason=f"linkage_{r.decision}",
                    details=r.to_dict(),
                )
                collisions.append({
                    "id": str(col.id),
                    "edge_id": str(row.id),
                    "reason": col.reason,
                    "details": col.details,
                })

        await self.audit.log(
            "identity.graph_rebuilt",
            user_id=user_id,
            details={"nodes": len(views), "edges": len(edge_rows), "collisions": len(collisions)},
        )
        await self.session.commit()

        nodes = [
            {
                "id": str(i.id),
                "type": i.type,
                "value_display": i.value_display,
                "is_verified": i.is_verified,
            }
            for i in idents
        ]
        return IdentityGraphPublic(
            nodes=nodes,
            edges=[IdentityEdgePublic.model_validate(e) for e in edge_rows],
            collisions=collisions,
            model_version=str(weights.get("model_version", "linkage-v1.0.0")),
        )

    async def get_graph(self, user_id: uuid.UUID) -> IdentityGraphPublic:
        await self._set_rls(user_id)
        idents = await self.identifiers.list_for_user(user_id)
        edges = await self.edges.list_edges(user_id)
        cols = await self.edges.list_collisions(user_id)
        weights = get_linkage_weights()
        return IdentityGraphPublic(
            nodes=[
                {
                    "id": str(i.id),
                    "type": i.type,
                    "value_display": i.value_display,
                    "is_verified": i.is_verified,
                }
                for i in idents
            ],
            edges=[IdentityEdgePublic.model_validate(e) for e in edges],
            collisions=[
                {"id": str(c.id), "edge_id": str(c.edge_id) if c.edge_id else None, "reason": c.reason, "details": c.details}
                for c in cols
            ],
            model_version=str(weights.get("model_version", "linkage-v1.0.0")),
        )

    async def review_edge(
        self, user_id: uuid.UUID, edge_id: uuid.UUID, status: str, note: str | None
    ) -> IdentityEdgePublic:
        await self._set_rls(user_id)
        edge = await self.edges.get_edge(edge_id, user_id)
        if not edge:
            raise HTTPException(status_code=404, detail="Edge not found")
        edge = await self.edges.set_review(edge, status, note)
        await self.audit.log(
            "identity.edge_reviewed",
            user_id=user_id,
            resource_type="identity_edge",
            resource_id=str(edge_id),
            details={"review_status": status},
        )
        await self.session.commit()
        return IdentityEdgePublic.model_validate(edge)

    async def accepted_edge_count(self, user_id: uuid.UUID) -> int:
        return await self.edges.count_accepted_edges(user_id)
```

---

## 15. NEW: `backend/app/services/scoring_service.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.pdss import PDSSEngine, FindingScoreInput
from app.repositories.score_repository import ScoreRepository
from app.repositories.finding_repository import FindingRepository
from app.repositories.identifier_repository import IdentifierRepository
from app.services.identity_service import IdentityService
from app.services.audit_service import AuditService
from app.services.catalog_loader import get_pdss_catalog
from app.schemas.identity_score import ScorePublic


class ScoringService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.scores = ScoreRepository(session)
        self.findings = FindingRepository(session)
        self.identifiers = IdentifierRepository(session)
        self.identity = IdentityService(session)
        self.audit = AuditService(session)
        self.settings = get_settings()
        self.engine = PDSSEngine(get_pdss_catalog())

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def _load_finding_inputs(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID | None,
    ) -> tuple[list[FindingScoreInput], str, int]:
        if identifier_id:
            ident = await self.identifiers.get(identifier_id, user_id)
            if not ident:
                raise HTTPException(status_code=404, detail="Identifier not found")
            rows = await self.findings.list_findings(user_id, identifier_id=identifier_id, limit=500)
            id_type = ident.type
        else:
            rows = await self.findings.list_findings(user_id, limit=1000)
            id_type = "email"  # aggregate default criticality baseline

        edge_count = await self.identity.accepted_edge_count(user_id)

        inputs = [
            FindingScoreInput(
                id=str(f.id),
                kind=f.kind,
                source=f.source,
                title=f.title,
                confidence=float(f.confidence or 0.5),
                layer=f.layer or "surface",
                track=f.track or "confirmed",
                severity_hint=f.severity_hint or "info",
                raw_ref=f.raw_ref,
                attributes=f.attributes or {},
                observed_at=f.last_seen_at or f.first_seen_at,
                attribution=f.attribution,
            )
            for f in rows
            if f.status != "dismissed"
        ]
        return inputs, id_type, edge_count

    async def compute(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        persist: bool = True,
        trigger: str = "manual",
        exclude_finding_ids: set[str] | None = None,
        exclude_sources: set[str] | None = None,
        exclude_kinds: set[str] | None = None,
    ) -> ScorePublic:
        await self._set_rls(user_id)
        inputs, id_type, edge_count = await self._load_finding_inputs(user_id, identifier_id)

        excl = set(exclude_finding_ids or set())
        if exclude_sources or exclude_kinds:
            for f in inputs:
                if exclude_sources and f.source in exclude_sources:
                    excl.add(f.id)
                if exclude_kinds and f.kind in exclude_kinds:
                    excl.add(f.id)

        result = self.engine.score(
            inputs,
            identifier_type=id_type,
            identity_edge_count=edge_count,
            exclude_finding_ids=excl,
        )
        payload = result.to_dict()

        snapshot_id = None
        created_at = None
        if persist and not excl:
            # only persist real scores, not pure what-if exclusions (what-if can persist with trigger=whatif if desired)
            snap = await self.scores.create_snapshot(
                user_id=user_id,
                identifier_id=identifier_id,
                payload=payload,
                trigger=trigger,
            )
            snapshot_id = snap.id
            created_at = snap.created_at

            # G3 durable explanation records
            await self.scores.add_explanation(
                user_id=user_id,
                score_snapshot_id=snap.id,
                kind="summary",
                title="PDSS summary",
                body={
                    "explanation_summary": result.explanation_summary,
                    "vector": result.vector,
                    "severity": result.severity,
                    "scores": {
                        "confirmed": result.score_confirmed,
                        "possible": result.score_possible,
                        "combined": result.score_combined,
                    },
                    "attributions": result.attributions,
                },
            )
            for c in result.contributions[:30]:
                fid = None
                try:
                    fid = uuid.UUID(c.finding_id)
                except Exception:
                    pass
                await self.scores.add_explanation(
                    user_id=user_id,
                    score_snapshot_id=snap.id,
                    kind="contribution",
                    title=c.title[:512],
                    finding_id=fid,
                    body=c.to_dict(),
                )
            for cf in result.counterfactuals:
                await self.scores.add_explanation(
                    user_id=user_id,
                    score_snapshot_id=snap.id,
                    kind="counterfactual",
                    title=cf.get("narrative", "counterfactual")[:512],
                    body=cf,
                )

            await self.audit.log(
                "score.computed",
                user_id=user_id,
                resource_type="score_snapshot",
                resource_id=str(snap.id),
                details={
                    "score_combined": result.score_combined,
                    "severity": result.severity,
                    "identifier_id": str(identifier_id) if identifier_id else None,
                    "model_version": result.model_version,
                },
            )
            await self.session.commit()
        elif persist and excl:
            snap = await self.scores.create_snapshot(
                user_id=user_id,
                identifier_id=identifier_id,
                payload={**payload, "meta": {**(payload.get("meta") or {}), "whatif": True, "excluded": list(excl)}},
                trigger="whatif",
            )
            snapshot_id = snap.id
            created_at = snap.created_at
            await self.session.commit()

        return ScorePublic(
            id=snapshot_id,
            identifier_id=identifier_id,
            model_version=result.model_version,
            score_confirmed=result.score_confirmed,
            score_possible=result.score_possible,
            score_combined=result.score_combined,
            severity=result.severity,
            vector=result.vector,
            metrics=result.metrics,
            contributions=[c.to_dict() for c in result.contributions],
            counterfactuals=result.counterfactuals,
            attributions=result.attributions,
            explanation_summary=result.explanation_summary,
            finding_count=result.input_finding_count,
            trigger=trigger if not excl else "whatif",
            created_at=created_at,
            meta=result.meta,
        )

    async def latest(self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None) -> ScorePublic:
        await self._set_rls(user_id)
        snap = await self.scores.latest(user_id, identifier_id)
        if not snap:
            raise HTTPException(status_code=404, detail="No score yet — POST /scores/compute first")
        return ScorePublic(
            id=snap.id,
            identifier_id=snap.identifier_id,
            model_version=snap.model_version,
            score_confirmed=snap.score_confirmed,
            score_possible=snap.score_possible,
            score_combined=snap.score_combined,
            severity=snap.severity,
            vector=snap.vector,
            metrics=snap.metrics,
            contributions=snap.contributions,
            counterfactuals=snap.counterfactuals,
            attributions=snap.attributions,
            explanation_summary=snap.explanation_summary,
            finding_count=snap.finding_count,
            trigger=snap.trigger,
            created_at=snap.created_at,
            meta=snap.meta,
        )

    async def history(self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None, limit: int = 50):
        await self._set_rls(user_id)
        return await self.scores.history(user_id, identifier_id=identifier_id, limit=limit)

    async def get_snapshot(self, user_id: uuid.UUID, snapshot_id: uuid.UUID) -> ScorePublic:
        await self._set_rls(user_id)
        snap = await self.scores.get(snapshot_id, user_id)
        if not snap:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        return ScorePublic(
            id=snap.id,
            identifier_id=snap.identifier_id,
            model_version=snap.model_version,
            score_confirmed=snap.score_confirmed,
            score_possible=snap.score_possible,
            score_combined=snap.score_combined,
            severity=snap.severity,
            vector=snap.vector,
            metrics=snap.metrics,
            contributions=snap.contributions,
            counterfactuals=snap.counterfactuals,
            attributions=snap.attributions,
            explanation_summary=snap.explanation_summary,
            finding_count=snap.finding_count,
            trigger=snap.trigger,
            created_at=snap.created_at,
            meta=snap.meta,
        )

    async def explanations(self, user_id: uuid.UUID, snapshot_id: uuid.UUID) -> list[dict[str, Any]]:
        await self._set_rls(user_id)
        rows = await self.scores.list_explanations(snapshot_id, user_id)
        return [
            {
                "id": str(r.id),
                "kind": r.kind,
                "title": r.title,
                "finding_id": str(r.finding_id) if r.finding_id else None,
                "body": r.body,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
```

---

## 16. NEW: `backend/app/api/v1/identity.py`

```python
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.identity_score import (
    IdentityGraphPublic,
    IdentityEdgePublic,
    EdgeReviewRequest,
)
from app.services.identity_service import IdentityService

router = APIRouter(prefix="/identity", tags=["identity"])


def _svc(db: AsyncSession = Depends(get_db)) -> IdentityService:
    return IdentityService(db)


@router.get("/graph", response_model=IdentityGraphPublic)
async def get_graph(current_user: CurrentUser, svc: IdentityService = Depends(_svc)):
    return await svc.get_graph(current_user.id)


@router.post("/graph/rebuild", response_model=IdentityGraphPublic)
async def rebuild_graph(current_user: CurrentUser, svc: IdentityService = Depends(_svc)):
    """Recompute pairwise deciban/F–S links across the user's identifiers."""
    return await svc.rebuild_graph(current_user.id)


@router.post("/edges/{edge_id}/review", response_model=IdentityEdgePublic)
async def review_edge(
    edge_id: UUID,
    body: EdgeReviewRequest,
    current_user: CurrentUser,
    svc: IdentityService = Depends(_svc),
):
    return await svc.review_edge(current_user.id, edge_id, body.review_status, body.review_note)
```

---

## 17. NEW: `backend/app/api/v1/scores.py`

```python
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.identity_score import (
    ScoreRequest,
    ScorePublic,
    ScoreHistoryItem,
    WhatIfRequest,
)
from app.services.scoring_service import ScoringService

router = APIRouter(prefix="/scores", tags=["scores"])


def _svc(db: AsyncSession = Depends(get_db)) -> ScoringService:
    return ScoringService(db)


@router.post("/compute", response_model=ScorePublic)
async def compute_score(
    body: ScoreRequest,
    current_user: CurrentUser,
    svc: ScoringService = Depends(_svc),
):
    """
    Compute hybrid PDSS (Base/Temporal/Environmental + surprisal, two-track).
    Includes XposedOrNot drivers from finding attributes when present.
    """
    return await svc.compute(
        current_user.id,
        identifier_id=body.identifier_id,
        persist=body.persist,
        trigger=body.trigger,
    )


@router.get("/latest", response_model=ScorePublic)
async def latest_score(
    current_user: CurrentUser,
    identifier_id: Optional[UUID] = None,
    svc: ScoringService = Depends(_svc),
):
    return await svc.latest(current_user.id, identifier_id)


@router.get("/history", response_model=list[ScoreHistoryItem])
async def score_history(
    current_user: CurrentUser,
    identifier_id: Optional[UUID] = None,
    limit: int = Query(50, ge=1, le=200),
    svc: ScoringService = Depends(_svc),
):
    rows = await svc.history(current_user.id, identifier_id=identifier_id, limit=limit)
    return [ScoreHistoryItem.model_validate(r) for r in rows]


@router.get("/{snapshot_id}", response_model=ScorePublic)
async def get_snapshot(
    snapshot_id: UUID,
    current_user: CurrentUser,
    svc: ScoringService = Depends(_svc),
):
    return await svc.get_snapshot(current_user.id, snapshot_id)


@router.get("/{snapshot_id}/explanations")
async def get_explanations(
    snapshot_id: UUID,
    current_user: CurrentUser,
    svc: ScoringService = Depends(_svc),
):
    """Durable G3 explanation records for a snapshot."""
    return await svc.explanations(current_user.id, snapshot_id)


@router.post("/whatif", response_model=ScorePublic)
async def whatif(
    body: WhatIfRequest,
    current_user: CurrentUser,
    svc: ScoringService = Depends(_svc),
):
    """
    What-if simulator: recompute PDSS excluding selected findings/sources/kinds.
    Persists with trigger=whatif for history/comparison.
    """
    return await svc.compute(
        current_user.id,
        identifier_id=body.identifier_id,
        persist=True,
        trigger="whatif",
        exclude_finding_ids={str(x) for x in body.exclude_finding_ids},
        exclude_sources=set(body.exclude_sources or []),
        exclude_kinds=set(body.exclude_kinds or []),
    )
```

---

## 18. UPDATE: `backend/app/main.py`

```python
from app.api.v1 import health, auth, identifiers, connectors, scans, identity, scores

# Routers
app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(identifiers.router, prefix=settings.api_v1_prefix)
app.include_router(connectors.router, prefix=settings.api_v1_prefix)
app.include_router(scans.router, prefix=settings.api_v1_prefix)
app.include_router(identity.router, prefix=settings.api_v1_prefix)
app.include_router(scores.router, prefix=settings.api_v1_prefix)

@app.get("/")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.5.0",
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
        "message": "DigiZafe Sprint 5 Identity Graph & PDSS Scoring — ready",
    }
```

Also ensure Dockerfile/compose mounts `./shared` (already done in Sprint 0).

---

## 19. UPDATE: `backend/app/alembic/env.py`

```python
from app.models.identity import IdentityEdge, IdentityCollision  # noqa: F401
from app.models.score import ScoreSnapshot, ExplanationRecord  # noqa: F401
# ... keep all previous model imports
```

---

## 20. Alembic migration `sprint5_identity_pdss`

```bash
docker compose exec api alembic revision -m "sprint5_identity_pdss"
```

```python
"""sprint5_identity_pdss"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "sprint5_pdss_001"
down_revision: Union[str, None] = "sprint4_disc_001"  # ← your Sprint 4 rev
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("left_identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("right_identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_weight", sa.Float(), nullable=False),
        sa.Column("match_prob", sa.Float(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=False, server_default="linkage-v1.0.0"),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "left_identifier_id", "right_identifier_id", name="uq_identity_edge_pair"),
    )
    op.create_index("ix_identity_edges_user_id", "identity_edges", ["user_id"])
    op.create_index("ix_identity_edges_decision", "identity_edges", ["decision"])
    op.create_index("ix_identity_edges_review_status", "identity_edges", ["review_status"])

    op.create_table(
        "identity_collisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("edge_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity_edges.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(128), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_identity_collisions_user_id", "identity_collisions", ["user_id"])

    op.create_table(
        "score_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("score_confirmed", sa.Float(), nullable=False),
        sa.Column("score_possible", sa.Float(), nullable=False),
        sa.Column("score_combined", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("vector", sa.String(512), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("contributions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("counterfactuals", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attributions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("explanation_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("finding_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trigger", sa.String(64), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_score_snapshots_user_id", "score_snapshots", ["user_id"])
    op.create_index("ix_score_snapshots_identifier_id", "score_snapshots", ["identifier_id"])
    op.create_index("ix_score_snapshots_score_combined", "score_snapshots", ["score_combined"])
    op.create_index("ix_score_snapshots_severity", "score_snapshots", ["severity"])
    op.create_index("ix_score_snapshots_created_at", "score_snapshots", ["created_at"])
    op.create_index("ix_score_snapshots_model_version", "score_snapshots", ["model_version"])

    op.create_table(
        "explanation_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score_snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("score_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_explanation_records_user_id", "explanation_records", ["user_id"])
    op.create_index("ix_explanation_records_score_snapshot_id", "explanation_records", ["score_snapshot_id"])
    op.create_index("ix_explanation_records_finding_id", "explanation_records", ["finding_id"])

    for table in ("identity_edges", "identity_collisions", "score_snapshots", "explanation_records"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY identity_edges_self ON identity_edges
        FOR ALL USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY identity_collisions_self ON identity_collisions
        FOR ALL USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY score_snapshots_self ON score_snapshots
        FOR ALL USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY explanation_records_self ON explanation_records
        FOR ALL USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)


def downgrade() -> None:
    for pol, tbl in [
        ("explanation_records_self", "explanation_records"),
        ("score_snapshots_self", "score_snapshots"),
        ("identity_collisions_self", "identity_collisions"),
        ("identity_edges_self", "identity_edges"),
    ]:
        op.execute(f"DROP POLICY IF EXISTS {pol} ON {tbl}")
    for table in ("explanation_records", "score_snapshots", "identity_collisions", "identity_edges"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
```

---

## 21. Optional: auto-score after scan finalize

In `backend/app/services/discovery_service.py` at end of `execute_scan` after `try_finalize` success:

```python
        # Sprint 5: closed-loop score (best-effort)
        try:
            from app.services.scoring_service import ScoringService
            scoring = ScoringService(self.session)
            await scoring.compute(
                scan.user_id,
                identifier_id=scan.identifier_id,
                persist=True,
                trigger="post_scan",
            )
        except Exception:
            logger.exception("post_scan_score_failed", scan_id=str(scan.id))
```

---

## 22. Unit tests

### `backend/tests/unit/test_linkage.py`

```python
from app.domain.linkage import IdentifierView, score_pair, match_weight_to_prob, build_edges


def test_match_weight_to_prob_mid():
    assert abs(match_weight_to_prob(0.0) - 0.5) < 1e-9
    assert match_weight_to_prob(10) > 0.99


def test_same_user_email_username_link():
    weights = {
        "prior_match_prob": 0.02,
        "comparisons": {
            "same_user_ownership": {"agree_weight": 6.0},
            "type_pair": {"email_github_username": 1.0, "default": 0.3},
            "canonical_similarity": {"exact": 5.0, "substring": 1.0, "none": -1.5, "local_part_match": 2.5},
            "shared_finding_sources": {"per_shared_source": 0.6, "cap": 3.0},
            "shared_breach_names": {"per_shared_breach": 0.4, "cap": 2.5},
            "profile_url_overlap": {"agree": 2.0, "disagree": 0.0},
        },
    }
    a = IdentifierView("1", "email", "alice@example.com", finding_sources=["xposedornot"], breach_names=["Adobe"])
    b = IdentifierView("2", "github_username", "alice", finding_sources=["github", "xposedornot"], breach_names=["Adobe"])
    r = score_pair(a, b, weights, auto_link_prob=0.95, review_prob=0.7, collision_flag_prob=0.5)
    assert r.match_prob > 0.5
    assert r.decision in {"auto_link", "review", "weak"}
```

### `backend/tests/unit/test_pdss.py`

```python
from app.domain.pdss import PDSSEngine, FindingScoreInput
from app.services.catalog_loader import get_pdss_catalog


def test_empty_score():
    eng = PDSSEngine(get_pdss_catalog())
    r = eng.score([])
    assert r.score_combined == 0.0
    assert r.severity in {"none", "low"}


def test_xposedornot_breach_drives_score():
    eng = PDSSEngine(get_pdss_catalog())
    findings = [
        FindingScoreInput(
            id="f1",
            kind="breach",
            source="xposedornot",
            title="Breach: Adobe",
            confidence=0.9,
            layer="surface",
            track="confirmed",
            severity_hint="high",
            raw_ref="Adobe",
            attributes={
                "breach_name": "Adobe",
                "xposed_data": "Email addresses;Passwords",
                "password_risk": "easytocrack",
                "xposed_date": "2013",
                "risk_label": "high",
                "provider": "xposedornot",
            },
            attribution="Data: XposedOrNot",
        ),
        FindingScoreInput(
            id="f2",
            kind="profile",
            source="gravatar",
            title="Gravatar present",
            confidence=0.9,
            layer="surface",
            track="confirmed",
            severity_hint="low",
            raw_ref="gravatar",
            attributes={},
        ),
    ]
    r = eng.score(findings, identifier_type="email", identity_edge_count=1)
    assert r.score_combined > 0
    assert r.contributions
    assert any(c.source == "xposedornot" for c in r.contributions)
    assert "PDSS:" in r.vector
    assert r.counterfactuals
    # what-if remove adobe should lower score
    r2 = eng.score(findings, exclude_finding_ids={"f1"})
    assert r2.score_combined <= r.score_combined
```

---

## 23. Docs

### `docs/model-cards/pdss-v1.md`

```markdown
# Model Card — PDSS v1.0.0

**Status:** Accepted (Sprint 5)  
**Type:** Hybrid deterministic exposure score (CVSS-inspired metric groups + surprisal)  
**Tracks:** Confirmed / Possible  
**Training data:** None (rules + catalogs; optional residual ML is Sprint 12)  
**Version:** pdss-v1.0.0  
**Catalog:** `shared/score_model/pdss_catalog.json`

## Intended use
Score an individual's **verified** digital exposure from DigiZafe findings (surface free path, XposedOrNot primary breaches, etc.) with full explainability.

## Metrics (vector groups)
| Code | Name | Role |
|------|------|------|
| S | Sensitivity | How sensitive exposed data types are |
| D | Discoverability | How easily found on public surface |
| L | Linkability | Cross-identifier / cross-source link risk |
| I | Impact | Harm potential (password plaintext, financial, etc.) |
| T | Temporal | Recency + reuse over time |
| E | Environmental | Identifier criticality, layer, identity-graph density |
| U | Surprisal | Non-saturating information-style contribution |
| R | Reuse | Same breach/ref across sources |

**Combined score:** 0.0–10.0 with severity bands (none/low/medium/high/critical).  
**Vector string example:** `PDSS:pdss-v1.0.0/S:0.72/D:1.00/L:0.08/I:0.65/T:0.81/E:1.04/U:1.20/R:0.08/SC:6.4/SV:medium`

## Two-track
- **Confirmed:** high-confidence breaches/exposures (e.g. XposedOrNot breach list confidence ≥ threshold in normalize)
- **Possible:** SERP/username presence/lower confidence  
Possible track weighted (~0.55) in combined score.

## XposedOrNot drivers
Uses finding attributes when present: `breach_name`, `xposed_data`, `password_risk`, `risk_label`, `xposed_date`, `xposed_records`. Attribution preserved on score snapshot.

## Explainability (G3)
Every compute persists:
- `score_snapshots` with contributions + counterfactuals
- `explanation_records` (summary, per-contribution drivers, counterfactual narratives)

## Out of scope
Opaque black-box ML as sole score; third-party scanning; paid API dependence.

## Limitations
- Deterministic catalogs may under/over-weight rare breach types.
- Recency uses year when only year available.
- Aggregate whole-user score uses default identifier criticality when identifier_id is null.

## Change control
Bump `model_version` + update this model card; never silent formula changes in production.
```

### `docs/runbooks/identity-pdss.md`

```markdown
# Identity Graph & PDSS (Sprint 5)

## After a scan
1. `POST /api/v1/scores/compute` `{"identifier_id":"...","persist":true}`
2. Or rely on post_scan hook if enabled
3. `GET /api/v1/scores/latest?identifier_id=`
4. `GET /api/v1/scores/{id}/explanations`

## Identity graph
1. Add & verify multiple identifiers
2. `POST /api/v1/identity/graph/rebuild`
3. Review collisions: `POST /api/v1/identity/edges/{id}/review` `{"review_status":"accepted"}`
4. Re-score — environmental boost applies for accepted edges

## What-if
`POST /api/v1/scores/whatif`  
`{"identifier_id":"...","exclude_finding_ids":["..."],"exclude_sources":["serp_ddg"]}`

## Catalogs
- `shared/score_model/pdss_catalog.json`
- `shared/score_model/deciban-weights.json`
```

---

# PART C — How to finish Sprint 5

```bash
# 1. Copy catalogs into shared/score_model/
# 2. Merge .env, rebuild, migrate
docker compose build api worker beat
docker compose up -d
docker compose exec api alembic upgrade head

# 3. Ensure findings exist (Sprint 4 scan on verified email)

# 4. Rebuild identity graph
curl -s -X POST http://localhost:8000/api/v1/identity/graph/rebuild \
  -H "Authorization: Bearer $ACCESS" | jq .

# 5. Compute PDSS
curl -s -X POST http://localhost:8000/api/v1/scores/compute \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d "{\"identifier_id\":\"$ID\",\"persist\":true}" | jq .

# 6. Latest + history + explanations
curl -s "http://localhost:8000/api/v1/scores/latest?identifier_id=$ID" \
  -H "Authorization: Bearer $ACCESS" | jq .
curl -s "http://localhost:8000/api/v1/scores/history?identifier_id=$ID" \
  -H "Authorization: Bearer $ACCESS" | jq .

# 7. What-if (exclude xposedornot)
curl -s -X POST http://localhost:8000/api/v1/scores/whatif \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d "{\"identifier_id\":\"$ID\",\"exclude_sources\":[\"xposedornot\"]}" | jq .

# 8. Unit tests
docker compose exec api pytest backend/tests/unit/test_linkage.py backend/tests/unit/test_pdss.py -v

# 9. Commit
git add .
git commit -m "feat(sprint-5): identity graph (deciban/F-S), hybrid PDSS+surprisal two-track, explanations, history, what-if, model card v1"
```

---

# Sprint 5 Definition of Done Checklist

- [ ] MASTER_ENGINEERING_CONTEXT.md respected  
- [ ] Pure domain `linkage.py` (deciban/F–S weights → probability, review/collision decisions)  
- [ ] Pure domain `pdss.py` hybrid Base/Temporal/Environmental + surprisal + two-track  
- [ ] Versioned catalogs in `shared/score_model/`  
- [ ] Identity edges + collisions tables + rebuild/review API  
- [ ] Score snapshots + explanation_records (G3 durable)  
- [ ] XposedOrNot attributes feed Sensitivity/Impact/Temporal drivers + attribution on snapshot  
- [ ] Vector string on every score  
- [ ] Counterfactuals + `/scores/whatif`  
- [ ] Score history API  
- [ ] Model card `docs/model-cards/pdss-v1.md`  
- [ ] RLS on new tables  
- [ ] Unit tests for linkage + PDSS green  
- [ ] Optional post_scan auto-score  
- [ ] Zero paid keys  

→ **Sprint 5 complete.**  
Next: **Sprint 6 — Recommendations & Alerts** (two-lane + DAG, dispute→rescore, deltas, alerts, quota rescans).

---

## Endpoint quick reference

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | /api/v1/identity/graph | Bearer | Current graph |
| POST | /api/v1/identity/graph/rebuild | Bearer | Recompute edges |
| POST | /api/v1/identity/edges/{id}/review | Bearer | Accept/reject link |
| POST | /api/v1/scores/compute | Bearer | Compute & persist PDSS |
| GET | /api/v1/scores/latest | Bearer | Latest snapshot |
| GET | /api/v1/scores/history | Bearer | Trend history |
| GET | /api/v1/scores/{id} | Bearer | Snapshot by id |
| GET | /api/v1/scores/{id}/explanations | Bearer | G3 records |
| POST | /api/v1/scores/whatif | Bearer | What-if rescore |

---

## File checklist (create/update)

| Action | Path |
|--------|------|
| UPDATE | `.env.example` |
| UPDATE | `backend/app/core/config.py` |
| NEW | `shared/score_model/pdss_catalog.json` |
| NEW | `shared/score_model/deciban-weights.json` |
| NEW | `backend/app/domain/linkage.py` |
| NEW | `backend/app/domain/pdss.py` |
| NEW | `backend/app/models/identity.py` |
| NEW | `backend/app/models/score.py` |
| UPDATE | `backend/app/models/__init__.py` |
| NEW | `backend/app/schemas/identity_score.py` |
| NEW | `backend/app/repositories/identity_repository.py` |
| NEW | `backend/app/repositories/score_repository.py` |
| NEW | `backend/app/services/catalog_loader.py` |
| NEW | `backend/app/services/identity_service.py` |
| NEW | `backend/app/services/scoring_service.py` |
| NEW | `backend/app/api/v1/identity.py` |
| NEW | `backend/app/api/v1/scores.py` |
| UPDATE | `backend/app/main.py` |
| UPDATE | `backend/app/alembic/env.py` |
| NEW | `backend/app/alembic/versions/*_sprint5_identity_pdss.py` |
| OPTIONAL | post_scan hook in `discovery_service.py` |
| NEW | `backend/tests/unit/test_linkage.py` |
| NEW | `backend/tests/unit/test_pdss.py` |
| NEW | `docs/model-cards/pdss-v1.md` |
| NEW | `docs/runbooks/identity-pdss.md` |

---

**You are ready for Sprint 5.**  
1. Save this file as `Sprint5.md` next to your other sprint docs.  
2. Copy catalogs → `shared/score_model/`.  
3. Apply code files in order; set `down_revision` to your Sprint 4 revision.  
4. Migrate → rebuild graph → compute PDSS on a scanned verified email → check vector, explanations, what-if.  
5. Commit when the DoD checklist is green.

If any import/migration/catalog-path issue appears, paste the error for a surgical fix.  
When Sprint 5 is green, ask for **Sprint 6** the same way.