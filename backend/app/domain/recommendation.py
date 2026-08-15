"""Two-lane recommendations with urgency, ROI, and dependency DAG (pure)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class FindingLite:
    id: str
    kind: str
    source: str
    title: str
    severity_hint: str
    confidence: float
    track: str
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "open"
    weighted_score: float = 0.0  # from PDSS contribution if available


@dataclass
class RecommendationDraft:
    code: str
    lane: str  # guided | semi_automated
    title: str
    summary: str
    urgency: float
    effort_hours: float
    roi: float
    priority: float
    depends_on: list[str]
    related_finding_ids: list[str]
    steps: list[str]
    links: list[dict[str, str]]
    playbook_key: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "lane": self.lane,
            "title": self.title,
            "summary": self.summary,
            "urgency": round(self.urgency, 4),
            "effort_hours": self.effort_hours,
            "roi": round(self.roi, 4),
            "priority": round(self.priority, 4),
            "depends_on": self.depends_on,
            "related_finding_ids": self.related_finding_ids,
            "steps": self.steps,
            "links": self.links,
            "playbook_key": self.playbook_key,
            "meta": self.meta,
        }


def _sev_ok(finding_sev: str, min_sev: str) -> bool:
    return SEVERITY_RANK.get(finding_sev, 0) >= SEVERITY_RANK.get(min_sev, 0)


def _attr_hits(attrs: dict[str, Any], keywords: list[str]) -> bool:
    blob = " ".join(str(v).lower() for v in attrs.values()) + " " + " ".join(attrs.keys()).lower()
    return any(k.lower() in blob for k in keywords)


def matching_findings(template: dict[str, Any], findings: list[FindingLite]) -> list[FindingLite]:
    trig = template.get("triggers") or {}
    if trig.get("always_if_open_findings"):
        return [f for f in findings if f.status == "open"]

    kinds = set(trig.get("kinds") or [])
    min_sev = trig.get("min_severity") or "info"
    keywords = trig.get("attribute_contains") or []

    out: list[FindingLite] = []
    for f in findings:
        if f.status in {"dismissed", "resolved"}:
            continue
        if kinds and f.kind not in kinds:
            continue
        if not _sev_ok(f.severity_hint, min_sev):
            continue
        if keywords and not _attr_hits(f.attributes or {}, keywords):
            # still allow if severity high enough and kind matches for freeze-like rules
            if SEVERITY_RANK.get(f.severity_hint, 0) < SEVERITY_RANK["high"]:
                continue
        out.append(f)
    return out


def compute_priority(
    *,
    urgency_base: float,
    roi_weight: float,
    effort_hours: float,
    marginal_pdss: float,
    formula: dict[str, Any],
    finding_boost: float,
) -> tuple[float, float, float]:
    """Returns (urgency, roi, priority)."""
    uw = float(formula.get("urgency_weight", 0.45))
    rw = float(formula.get("roi_weight", 0.40))
    ep = float(formula.get("effort_penalty", 0.15))
    mb = float(formula.get("pdss_marginal_boost", 0.35))

    urgency = min(1.0, urgency_base * (0.7 + 0.3 * finding_boost) + mb * min(1.0, marginal_pdss / 3.0))
    # ROI: weight * expected score reduction per effort hour (diminishing)
    effort = max(0.05, effort_hours)
    roi = roi_weight * (0.5 + min(1.5, marginal_pdss) / effort) / 2.0
    roi = min(1.5, max(0.05, roi))
    priority = uw * urgency + rw * min(1.0, roi) - ep * min(1.0, effort / 2.0)
    return urgency, roi, priority


def topo_sort_codes(drafts: list[RecommendationDraft]) -> list[str]:
    """Kahn topological sort; independent nodes ordered by priority desc."""
    by_code = {d.code: d for d in drafts}
    codes = set(by_code)
    indeg: dict[str, int] = {c: 0 for c in codes}
    adj: dict[str, list[str]] = defaultdict(list)
    for d in drafts:
        for dep in d.depends_on:
            if dep in codes and dep != d.code:
                adj[dep].append(d.code)
                indeg[d.code] += 1

    # ready: no deps, sort by priority desc
    ready = sorted(
        [c for c in codes if indeg[c] == 0],
        key=lambda c: by_code[c].priority,
        reverse=True,
    )
    order: list[str] = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                # insert keeping priority order
                ready.append(m)
                ready.sort(key=lambda c: by_code[c].priority, reverse=True)
    # cycles / missing: append remaining by priority
    remaining = [c for c in codes if c not in order]
    remaining.sort(key=lambda c: by_code[c].priority, reverse=True)
    order.extend(remaining)
    return order


def build_recommendations(
    catalog: dict[str, Any],
    findings: list[FindingLite],
    *,
    pdss_counterfactuals: list[dict[str, Any]] | None = None,
    score_combined: float = 0.0,
) -> list[RecommendationDraft]:
    """
    Match templates to open findings; score urgency/ROI; attach DAG deps;
    return drafts in topological priority order.
    """
    formula = catalog.get("priority_formula") or {}
    # map finding_id -> estimated delta from PDSS counterfactuals
    delta_by_fid: dict[str, float] = {}
    for cf in pdss_counterfactuals or []:
        fid = str(cf.get("finding_id") or "")
        if fid:
            delta_by_fid[fid] = float(cf.get("delta") or 0.0)

    drafts: list[RecommendationDraft] = []
    for tmpl in catalog.get("templates") or []:
        matched = matching_findings(tmpl, findings)
        always = (tmpl.get("triggers") or {}).get("always_if_open_findings")
        if not matched and not always:
            continue
        if always and not any(f.status == "open" for f in findings):
            continue
        if not matched and always:
            matched = [f for f in findings if f.status == "open"][:5]

        fids = [f.id for f in matched]
        marginal = sum(delta_by_fid.get(i, f.weighted_score * 0.3) for i, f in zip(fids, matched)) or (
            score_combined * 0.1 if matched else 0.0
        )
        finding_boost = min(1.0, len(matched) / 5.0)
        urgency, roi, priority = compute_priority(
            urgency_base=float(tmpl.get("urgency_base", 0.5)),
            roi_weight=float(tmpl.get("roi_weight", 0.5)),
            effort_hours=float(tmpl.get("effort_hours", 0.5)),
            marginal_pdss=marginal,
            formula=formula,
            finding_boost=finding_boost,
        )
        drafts.append(
            RecommendationDraft(
                code=tmpl["code"],
                lane=tmpl.get("lane", "guided"),
                title=tmpl["title"],
                summary=tmpl.get("summary", ""),
                urgency=urgency,
                effort_hours=float(tmpl.get("effort_hours", 0.5)),
                roi=roi,
                priority=priority,
                depends_on=list(tmpl.get("depends_on") or []),
                related_finding_ids=fids,
                steps=list(tmpl.get("steps") or []),
                links=list(tmpl.get("links") or []),
                playbook_key=tmpl.get("playbook_key") or tmpl["code"],
                meta={
                    "sprint7_required": bool(tmpl.get("sprint7_required")),
                    "aidr_lineage": tmpl.get("aidr_lineage"),
                    "matched_count": len(matched),
                    "estimated_pdss_delta": round(marginal, 3),
                    "score_context": score_combined,
                },
            )
        )

    order = topo_sort_codes(drafts)
    by = {d.code: d for d in drafts}
    return [by[c] for c in order if c in by]


def recommend_freeze(findings: list[FindingLite], freeze_rule: dict[str, Any] | None = None) -> bool:
    """AIDR recommendFreeze analogue — pure."""
    rule = freeze_rule or {}
    min_sevs = set(rule.get("min_severity_hint") or ["high", "critical"])
    keywords = rule.get("attribute_keywords") or ["ssn", "password", "financial"]
    for f in findings:
        if f.status in {"dismissed", "resolved"}:
            continue
        if f.severity_hint in min_sevs:
            return True
        if f.kind in {"breach", "password_exposure"} and _attr_hits(f.attributes or {}, keywords):
            return True
    return False
