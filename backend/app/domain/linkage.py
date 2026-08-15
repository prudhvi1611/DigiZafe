"""Identity linkage (pure). Fellegi–Sunter-style match weights in log2 units."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


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
