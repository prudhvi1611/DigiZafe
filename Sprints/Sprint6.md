# DigiZafe — Sprint 6 Recommendations & Alerts  
**Complete Implementation Guide from Sprint 5 Baseline + All File Contents**

**Document version:** 1.0  
**Based on:** MASTER_ENGINEERING_CONTEXT.md v2.1  
**Depends on:** Sprint 0–5 green (Auth, Identifiers, Connectors, Discovery, Findings, Identity Graph, PDSS + explanations + what-if)  
**Goal:** From completed Sprint 5 → **two-lane prioritized recommendations** (urgency + ROI + dependency DAG), **dispute → rescore**, **score/finding deltas**, **in-app alerts**, and **quota-aware rescans** (manual + scheduled/alert-driven).  
**Not in this sprint:** Playwright semi-automated broker runners (Sprint 7). Lane B recommendations are **planned/queued** with playbook keys ready for Sprint 7.

**Effort estimate:** ~8 days (solo)  
**Critical path next:** Sprint 7 Remediation Engine (AIDR core)

> **Load MASTER_ENGINEERING_CONTEXT.md first.**  
> Domain pure. No paid keys. Free path only. Remediation **execution** is Sprint 7 — this sprint plans, prioritizes, alerts, and rescores.

---

# PART A — Pre-Sprint 6

```bash
# Confirm Sprint 5 green
curl -s http://localhost:8000/api/v1/health | jq .
# Need: verified ID → scan → findings → PDSS compute → latest score works

mkdir -p backend/app/domain
mkdir -p backend/app/{services,repositories,models,schemas,tasks}
mkdir -p shared/score_model shared/config/playbook
mkdir -p docs/runbooks
mkdir -p backend/tests/unit

docker compose build api worker beat
echo "✅ Pre-Sprint 6 ready"
```

---

# PART B — Sprint 6 File Contents

---

## 1. UPDATE: `.env.example` (append)

```bash
# === Sprint 6: Recommendations & Alerts ===
RECOMMENDATION_MODEL_VERSION=rec-v1.0.0
RECOMMENDATION_CATALOG_PATH=./shared/score_model/recommendation_catalog.json

# Alerts
ALERT_SCORE_JUMP_THRESHOLD=1.0
ALERT_NEW_HIGH_SEVERITY=true
ALERT_RETENTION_DAYS=90

# Rescan quotas (on top of DEFAULT_USER_SCAN_QUOTA_PER_DAY)
RESCAN_COOLDOWN_HOURS=6
FEATURE_SCHEDULED_RESCANS=true
SCHEDULED_RESCAN_INTERVAL_HOURS=168
# beat task interval for alert reconcile / scheduled rescan check
ALERT_RECONCILE_INTERVAL_SECONDS=120
```

---

## 2. UPDATE: `backend/app/core/config.py`

```python
    # === Sprint 6: Recommendations & Alerts ===
    recommendation_model_version: str = "rec-v1.0.0"
    recommendation_catalog_path: str = "./shared/score_model/recommendation_catalog.json"

    alert_score_jump_threshold: float = 1.0
    alert_new_high_severity: bool = True
    alert_retention_days: int = 90

    rescan_cooldown_hours: int = 6
    feature_scheduled_rescans: bool = True
    scheduled_rescan_interval_hours: int = 168
    alert_reconcile_interval_seconds: int = 120
```

---

## 3. NEW: `shared/score_model/recommendation_catalog.json`

```json
{
  "model_version": "rec-v1.0.0",
  "description": "Two-lane recommendations: guided (always) + semi-automated Green brokers (queued for Sprint 7). Urgency + ROI from PDSS marginal impact + dependency DAG.",
  "lanes": {
    "guided": "User-in-loop steps, freeze, DSAR/know templates, password hygiene, MFA",
    "semi_automated": "Green broker opt-outs via Playwright (Sprint 7 execution); planned in Sprint 6"
  },
  "templates": [
    {
      "code": "change_password_breached",
      "lane": "guided",
      "title": "Change passwords on breached accounts",
      "summary": "One or more breaches expose passwords or high-risk credentials. Change passwords and enable unique secrets.",
      "urgency_base": 0.95,
      "effort_hours": 0.5,
      "roi_weight": 1.0,
      "depends_on": [],
      "triggers": {"kinds": ["breach", "password_exposure"], "min_severity": "medium"},
      "steps": [
        "Identify accounts tied to the breached email",
        "Change password to a unique high-entropy secret",
        "Enable MFA where available",
        "Revoke sessions / app passwords if offered"
      ],
      "playbook_key": "guided.password_reset"
    },
    {
      "code": "enable_mfa",
      "lane": "guided",
      "title": "Enable multi-factor authentication",
      "summary": "Reduce account takeover risk after credential exposure.",
      "urgency_base": 0.85,
      "effort_hours": 0.25,
      "roi_weight": 0.85,
      "depends_on": ["change_password_breached"],
      "triggers": {"kinds": ["breach", "password_exposure", "profile"], "min_severity": "low"},
      "steps": [
        "Prefer TOTP or hardware key over SMS",
        "Store backup codes offline",
        "Review DigiZafe account MFA status"
      ],
      "playbook_key": "guided.mfa"
    },
    {
      "code": "credit_freeze",
      "lane": "guided",
      "title": "Place free credit / security freezes",
      "summary": "High-impact identity exposure warrants freezes at major bureaus and specialty agencies (AIDR freeze lineage).",
      "urgency_base": 0.9,
      "effort_hours": 1.0,
      "roi_weight": 0.95,
      "depends_on": [],
      "triggers": {
        "kinds": ["breach"],
        "min_severity": "high",
        "attribute_contains": ["ssn", "social security", "password", "financial", "credit"]
      },
      "steps": [
        "Equifax credit freeze",
        "Experian credit freeze",
        "TransUnion credit freeze",
        "ChexSystems / Innovis / NCTUE as applicable",
        "OptOutPrescreen for pre-screened offers"
      ],
      "links": [
        {"label": "Equifax", "url": "https://www.equifax.com/personal/credit-report-services/credit-freeze/"},
        {"label": "Experian", "url": "https://www.experian.com/freeze/center.html"},
        {"label": "TransUnion", "url": "https://www.transunion.com/credit-freeze"},
        {"label": "ChexSystems", "url": "https://www.chexsystems.com/security-freeze/place-freeze"},
        {"label": "Innovis", "url": "https://www.innovis.com/personal/securityFreeze"},
        {"label": "OptOutPrescreen", "url": "https://www.optoutprescreen.com/"}
      ],
      "playbook_key": "guided.credit_freeze",
      "aidr_lineage": "lib/freeze.js FREEZE_TARGETS"
    },
    {
      "code": "right_to_know",
      "lane": "guided",
      "title": "Send right-to-know / access requests",
      "summary": "Generate CCPA/GDPR access templates for brokers or processors holding your data (AIDR know lineage).",
      "urgency_base": 0.55,
      "effort_hours": 0.4,
      "roi_weight": 0.5,
      "depends_on": [],
      "triggers": {"kinds": ["profile", "username_presence", "serp", "breach"], "min_severity": "info"},
      "steps": [
        "Pick regime (CCPA default / GDPR if EU)",
        "Generate request body",
        "Send to broker privacy contact",
        "Record submission date for complaint deadlines"
      ],
      "playbook_key": "guided.right_to_know",
      "aidr_lineage": "lib/right-to-know.js"
    },
    {
      "code": "review_serp_footprint",
      "lane": "guided",
      "title": "Review and clean SERP footprint",
      "summary": "Public search hits may amplify discoverability. Review URLs and request outdated content removal where appropriate.",
      "urgency_base": 0.45,
      "effort_hours": 0.75,
      "roi_weight": 0.4,
      "depends_on": [],
      "triggers": {"kinds": ["serp"], "min_severity": "info"},
      "steps": [
        "Open each SERP hit",
        "Request removal of outdated personal content where policy allows",
        "Update privacy settings on linked profiles"
      ],
      "playbook_key": "guided.serp_review"
    },
    {
      "code": "broker_optout_green",
      "lane": "semi_automated",
      "title": "Opt out of Green data brokers",
      "summary": "Queue AIDR-style Green broker opt-outs. Execution in Sprint 7 (Playwright + free CAPTCHA path).",
      "urgency_base": 0.7,
      "effort_hours": 0.1,
      "roi_weight": 0.75,
      "depends_on": [],
      "triggers": {"kinds": ["profile", "username_presence", "serp", "breach"], "min_severity": "low"},
      "steps": [
        "Review planned brokers",
        "Confirm consent for automated form submission",
        "Run remediation job (Sprint 7)"
      ],
      "playbook_key": "remediation.broker_optout_green",
      "sprint7_required": true,
      "aidr_lineage": "brokers.js + state.json optOuts"
    },
    {
      "code": "rescan_after_remediation",
      "lane": "guided",
      "title": "Rescan to verify improvement",
      "summary": "After remediating high-impact findings, run a quota-aware rescan and recompute PDSS (closed loop).",
      "urgency_base": 0.5,
      "effort_hours": 0.05,
      "roi_weight": 0.6,
      "depends_on": ["change_password_breached", "broker_optout_green", "credit_freeze"],
      "triggers": {"always_if_open_findings": true},
      "steps": ["Start rescan on verified identifier", "Compare PDSS delta", "Close resolved recommendations"],
      "playbook_key": "guided.rescan"
    }
  ],
  "priority_formula": {
    "urgency_weight": 0.45,
    "roi_weight": 0.40,
    "effort_penalty": 0.15,
    "pdss_marginal_boost": 0.35
  },
  "freeze_recommend_rule": {
    "note": "Maps AIDR recommendFreeze: any high-severity breach with sensitive data classes",
    "min_severity_hint": ["high", "critical"],
    "attribute_keywords": ["ssn", "social security", "password", "passwords", "financial", "credit card"]
  }
}
```

---

## 4. NEW: `backend/app/domain/recommendation.py`  
*(pure — templates → prioritized plan + DAG topo sort)*

```python
"""Two-lane recommendations with urgency, ROI, and dependency DAG (pure)."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Optional


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
```

---

## 5. NEW: `backend/app/domain/deltas.py`  
*(pure — score + finding deltas; AIDR diff lineage)*

```python
"""Pure delta helpers for scores and findings (AIDR lib/diff.js lineage)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ScoreDelta:
    before: float
    after: float
    delta: float
    severity_before: str
    severity_after: str
    improved: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "before": self.before,
            "after": self.after,
            "delta": round(self.delta, 2),
            "severity_before": self.severity_before,
            "severity_after": self.severity_after,
            "improved": self.improved,
            "summary": (
                f"PDSS {self.before:.1f}→{self.after:.1f} (Δ {self.delta:+.1f}); "
                f"{self.severity_before}→{self.severity_after}"
            ),
        }


@dataclass
class FindingDelta:
    new_finding_ids: list[str]
    resolved_finding_ids: list[str]
    regressed_finding_ids: list[str]
    unchanged_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "new_finding_ids": self.new_finding_ids,
            "resolved_finding_ids": self.resolved_finding_ids,
            "regressed_finding_ids": self.regressed_finding_ids,
            "unchanged_count": self.unchanged_count,
            "summary": (
                f"+{len(self.new_finding_ids)} new, "
                f"{len(self.resolved_finding_ids)} resolved, "
                f"{len(self.regressed_finding_ids)} regressed"
            ),
        }


def score_delta(
    before_score: float,
    after_score: float,
    severity_before: str,
    severity_after: str,
) -> ScoreDelta:
    d = after_score - before_score
    return ScoreDelta(
        before=before_score,
        after=after_score,
        delta=d,
        severity_before=severity_before,
        severity_after=severity_after,
        improved=d < 0,
    )


def finding_delta(
    prev_open_ids: set[str],
    curr_open_ids: set[str],
    *,
    prev_resolved_ids: set[str] | None = None,
) -> FindingDelta:
    prev_resolved_ids = prev_resolved_ids or set()
    new = sorted(curr_open_ids - prev_open_ids)
    resolved = sorted(prev_open_ids - curr_open_ids)
    # regressed: was resolved, now open again
    regressed = sorted(curr_open_ids & prev_resolved_ids)
    unchanged = len(prev_open_ids & curr_open_ids)
    return FindingDelta(
        new_finding_ids=new,
        resolved_finding_ids=resolved,
        regressed_finding_ids=regressed,
        unchanged_count=unchanged,
    )
```

---

## 6. NEW: `backend/app/models/recommendation.py`

```python
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    identifier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    lane: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    urgency: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    effort_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    roi: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    priority: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    depends_on: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    related_finding_ids: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    steps: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    links: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    playbook_key: Mapped[str] = mapped_column(String(128), nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    # open | in_progress | done | dismissed | blocked

    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="rec-v1.0.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class RecommendationPlan(Base):
    """One generation of a prioritized plan for a scope."""

    __tablename__ = "recommendation_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    identifier_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    score_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    freeze_recommended: Mapped[bool] = mapped_column(default=False, nullable=False)
    dag_order: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
```

---

## 7. NEW: `backend/app/models/alert.py`

```python
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    identifier_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)

    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # score_jump | new_finding | severity_high | rescan_available | plan_ready | dispute_resolved
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="info", index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )


class RescanPolicy(Base):
    """Per-user / per-identifier rescan schedule + cooldown."""

    __tablename__ = "rescan_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    identifier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    interval_hours: Mapped[int] = mapped_column(default=168, nullable=False)
    last_rescan_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_eligible_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

---

## 8. UPDATE: `backend/app/models/__init__.py`

Add exports:

```python
from app.models.recommendation import Recommendation, RecommendationPlan
from app.models.alert import Alert, RescanPolicy

# add to __all__
```

Also ensure `Finding.status` already supports `dismissed` (Sprint 4) — used by dispute.

---

## 9. NEW: `backend/app/schemas/recommendations_alerts.py`

```python
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class RecommendationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    identifier_id: Optional[UUID] = None
    code: str
    lane: str
    title: str
    summary: str
    urgency: float
    effort_hours: float
    roi: float
    priority: float
    sort_order: int
    depends_on: Optional[list[Any]] = None
    related_finding_ids: Optional[list[Any]] = None
    steps: Optional[list[Any]] = None
    links: Optional[list[Any]] = None
    playbook_key: str
    meta: Optional[dict[str, Any]] = None
    status: str
    model_version: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class PlanPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: Optional[UUID] = None
    model_version: str
    score_snapshot_id: Optional[UUID] = None
    freeze_recommended: bool
    dag_order: Optional[list[Any]] = None
    summary: str
    meta: Optional[dict[str, Any]] = None
    created_at: datetime
    recommendations: list[RecommendationPublic] = []


class PlanGenerateRequest(BaseModel):
    identifier_id: Optional[UUID] = None
    persist: bool = True


class RecommendationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|in_progress|done|dismissed|blocked)$")


class DisputeRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)
    rescore: bool = True


class AlertPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: Optional[UUID] = None
    kind: str
    severity: str
    title: str
    body: str
    payload: Optional[dict[str, Any]] = None
    read: bool
    dismissed: bool
    created_at: datetime


class RescanRequest(BaseModel):
    identifier_id: UUID
    connector_ids: Optional[list[str]] = None
    force: bool = False  # ignore cooldown if True (still enforces daily quota)


class RescanPolicyUpsert(BaseModel):
    identifier_id: UUID
    enabled: bool = True
    interval_hours: int = Field(168, ge=24, le=720)


class DeltaResponse(BaseModel):
    score: Optional[dict[str, Any]] = None
    findings: Optional[dict[str, Any]] = None
    summary: str = ""


class Message(BaseModel):
    message: str
```

---

## 10. NEW: `backend/app/repositories/recommendation_repository.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import Recommendation, RecommendationPlan


class RecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_plan(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID | None,
        model_version: str,
        score_snapshot_id: uuid.UUID | None,
        freeze_recommended: bool,
        dag_order: list[str],
        summary: str,
        meta: dict | None,
        drafts: list[dict[str, Any]],
    ) -> tuple[RecommendationPlan, list[Recommendation]]:
        plan = RecommendationPlan(
            user_id=user_id,
            identifier_id=identifier_id,
            model_version=model_version,
            score_snapshot_id=score_snapshot_id,
            freeze_recommended=freeze_recommended,
            dag_order=dag_order,
            summary=summary,
            meta=meta,
        )
        self.session.add(plan)
        await self.session.flush()

        rows: list[Recommendation] = []
        for i, d in enumerate(drafts):
            row = Recommendation(
                user_id=user_id,
                identifier_id=identifier_id,
                plan_id=plan.id,
                code=d["code"],
                lane=d["lane"],
                title=d["title"],
                summary=d["summary"],
                urgency=d["urgency"],
                effort_hours=d["effort_hours"],
                roi=d["roi"],
                priority=d["priority"],
                sort_order=i,
                depends_on=d.get("depends_on"),
                related_finding_ids=d.get("related_finding_ids"),
                steps=d.get("steps"),
                links=d.get("links"),
                playbook_key=d["playbook_key"],
                meta=d.get("meta"),
                status="open",
                model_version=model_version,
            )
            self.session.add(row)
            rows.append(row)
        await self.session.flush()
        return plan, rows

    async def latest_plan(
        self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None
    ) -> Optional[RecommendationPlan]:
        q = select(RecommendationPlan).where(RecommendationPlan.user_id == user_id)
        if identifier_id is not None:
            q = q.where(RecommendationPlan.identifier_id == identifier_id)
        else:
            q = q.where(RecommendationPlan.identifier_id.is_(None))
        q = q.order_by(RecommendationPlan.created_at.desc()).limit(1)
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_for_plan(self, plan_id: uuid.UUID, user_id: uuid.UUID) -> Sequence[Recommendation]:
        result = await self.session.execute(
            select(Recommendation)
            .where(Recommendation.plan_id == plan_id, Recommendation.user_id == user_id)
            .order_by(Recommendation.sort_order.asc())
        )
        return result.scalars().all()

    async def list_open(self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None) -> Sequence[Recommendation]:
        q = select(Recommendation).where(
            Recommendation.user_id == user_id,
            Recommendation.status.in_(["open", "in_progress", "blocked"]),
        )
        if identifier_id:
            q = q.where(Recommendation.identifier_id == identifier_id)
        q = q.order_by(Recommendation.priority.desc())
        result = await self.session.execute(q)
        return result.scalars().all()

    async def get(self, rec_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Recommendation]:
        result = await self.session.execute(
            select(Recommendation).where(Recommendation.id == rec_id, Recommendation.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def set_status(self, row: Recommendation, status: str) -> Recommendation:
        row.status = status
        if status == "done":
            row.completed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return row
```

---

## 11. NEW: `backend/app/repositories/alert_repository.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, RescanPolicy


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        kind: str,
        title: str,
        body: str,
        severity: str = "info",
        identifier_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Alert:
        row = Alert(
            user_id=user_id,
            identifier_id=identifier_id,
            kind=kind,
            severity=severity,
            title=title,
            body=body,
            payload=payload,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list(
        self,
        user_id: uuid.UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> Sequence[Alert]:
        q = select(Alert).where(Alert.user_id == user_id, Alert.dismissed.is_(False))
        if unread_only:
            q = q.where(Alert.read.is_(False))
        q = q.order_by(Alert.created_at.desc()).limit(limit)
        result = await self.session.execute(q)
        return result.scalars().all()

    async def get(self, alert_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Alert]:
        result = await self.session.execute(
            select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def mark_read(self, row: Alert) -> None:
        row.read = True
        await self.session.flush()

    async def dismiss(self, row: Alert) -> None:
        row.dismissed = True
        row.read = True
        await self.session.flush()

    async def purge_old(self, days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        r = await self.session.execute(delete(Alert).where(Alert.created_at < cutoff))
        await self.session.flush()
        return r.rowcount or 0

    # ---- rescan policies ----
    async def upsert_policy(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        enabled: bool,
        interval_hours: int,
    ) -> RescanPolicy:
        result = await self.session.execute(
            select(RescanPolicy).where(
                RescanPolicy.user_id == user_id,
                RescanPolicy.identifier_id == identifier_id,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.enabled = enabled
            row.interval_hours = interval_hours
            await self.session.flush()
            return row
        row = RescanPolicy(
            user_id=user_id,
            identifier_id=identifier_id,
            enabled=enabled,
            interval_hours=interval_hours,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_policy(
        self, user_id: uuid.UUID, identifier_id: uuid.UUID
    ) -> Optional[RescanPolicy]:
        result = await self.session.execute(
            select(RescanPolicy).where(
                RescanPolicy.user_id == user_id,
                RescanPolicy.identifier_id == identifier_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_due_policies(self, now: datetime) -> Sequence[RescanPolicy]:
        result = await self.session.execute(
            select(RescanPolicy).where(
                RescanPolicy.enabled.is_(True),
                RescanPolicy.next_eligible_at.is_not(None),
                RescanPolicy.next_eligible_at <= now,
            ).limit(50)
        )
        return result.scalars().all()

    async def touch_policy(self, row: RescanPolicy, now: datetime, interval_hours: int) -> None:
        row.last_rescan_at = now
        row.next_eligible_at = now + timedelta(hours=interval_hours)
        await self.session.flush()
```

---

## 12. NEW: `backend/app/services/catalog_loader.py` (extend)

If you already have `get_pdss_catalog` / `get_linkage_weights`, **add**:

```python
@lru_cache
def get_recommendation_catalog() -> dict[str, Any]:
    settings = get_settings()
    return _load_json(settings.recommendation_catalog_path)
```

(Reuse the same `_load_json` helper from Sprint 5.)

---

## 13. NEW: `backend/app/services/recommendation_service.py`

```python
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.recommendation import (
    FindingLite,
    build_recommendations,
    recommend_freeze,
)
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.finding_repository import FindingRepository
from app.repositories.score_repository import ScoreRepository
from app.services.scoring_service import ScoringService
from app.services.audit_service import AuditService
from app.services.catalog_loader import get_recommendation_catalog
from app.schemas.recommendations_alerts import PlanPublic, RecommendationPublic


class RecommendationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RecommendationRepository(session)
        self.findings = FindingRepository(session)
        self.scores = ScoreRepository(session)
        self.scoring = ScoringService(session)
        self.audit = AuditService(session)
        self.settings = get_settings()

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def generate(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        persist: bool = True,
    ) -> PlanPublic:
        await self._set_rls(user_id)
        catalog = get_recommendation_catalog()

        rows = await self.findings.list_findings(
            user_id, identifier_id=identifier_id, limit=500
        )
        # optional PDSS contributions for ROI
        snap = await self.scores.latest(user_id, identifier_id)
        contrib_map: dict[str, float] = {}
        counterfactuals: list[dict] = []
        score_combined = 0.0
        snapshot_id = None
        if snap:
            snapshot_id = snap.id
            score_combined = float(snap.score_combined or 0)
            counterfactuals = list(snap.counterfactuals or [])
            for c in snap.contributions or []:
                if isinstance(c, dict) and c.get("finding_id"):
                    contrib_map[str(c["finding_id"])] = float(c.get("weighted_score") or 0)

        lites = [
            FindingLite(
                id=str(f.id),
                kind=f.kind,
                source=f.source,
                title=f.title,
                severity_hint=f.severity_hint or "info",
                confidence=float(f.confidence or 0.5),
                track=f.track or "confirmed",
                attributes=f.attributes or {},
                status=f.status or "open",
                weighted_score=contrib_map.get(str(f.id), 0.0),
            )
            for f in rows
        ]

        drafts = build_recommendations(
            catalog,
            lites,
            pdss_counterfactuals=counterfactuals,
            score_combined=score_combined,
        )
        freeze = recommend_freeze(lites, catalog.get("freeze_recommend_rule"))
        # ensure freeze template present if rule fires
        if freeze and not any(d.code == "credit_freeze" for d in drafts):
            # force include by temporary high sev synthetic signal already in catalog match
            pass

        dag_order = [d.code for d in drafts]
        summary = (
            f"{len(drafts)} recommendations "
            f"({sum(1 for d in drafts if d.lane == 'guided')} guided, "
            f"{sum(1 for d in drafts if d.lane == 'semi_automated')} semi-automated). "
            f"Credit freeze recommended: {freeze}."
        )

        if not persist:
            # ephemeral response
            fake_plan_id = uuid.uuid4()
            return PlanPublic(
                id=fake_plan_id,
                identifier_id=identifier_id,
                model_version=str(catalog.get("model_version", "rec-v1.0.0")),
                score_snapshot_id=snapshot_id,
                freeze_recommended=freeze,
                dag_order=dag_order,
                summary=summary,
                meta={"ephemeral": True},
                created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                recommendations=[],  # client can use drafts via meta if needed
            )

        plan, rec_rows = await self.repo.create_plan(
            user_id=user_id,
            identifier_id=identifier_id,
            model_version=str(catalog.get("model_version", self.settings.recommendation_model_version)),
            score_snapshot_id=snapshot_id,
            freeze_recommended=freeze,
            dag_order=dag_order,
            summary=summary,
            meta={"score_combined": score_combined},
            drafts=[d.to_dict() for d in drafts],
        )
        await self.audit.log(
            "recommendation.plan_generated",
            user_id=user_id,
            resource_type="recommendation_plan",
            resource_id=str(plan.id),
            details={"count": len(rec_rows), "freeze": freeze},
        )
        await self.session.commit()

        return PlanPublic(
            id=plan.id,
            identifier_id=plan.identifier_id,
            model_version=plan.model_version,
            score_snapshot_id=plan.score_snapshot_id,
            freeze_recommended=plan.freeze_recommended,
            dag_order=plan.dag_order,
            summary=plan.summary,
            meta=plan.meta,
            created_at=plan.created_at,
            recommendations=[RecommendationPublic.model_validate(r) for r in rec_rows],
        )

    async def latest_plan(self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None) -> PlanPublic:
        await self._set_rls(user_id)
        plan = await self.repo.latest_plan(user_id, identifier_id)
        if not plan:
            raise HTTPException(status_code=404, detail="No plan — POST /recommendations/generate")
        recs = await self.repo.list_for_plan(plan.id, user_id)
        return PlanPublic(
            id=plan.id,
            identifier_id=plan.identifier_id,
            model_version=plan.model_version,
            score_snapshot_id=plan.score_snapshot_id,
            freeze_recommended=plan.freeze_recommended,
            dag_order=plan.dag_order,
            summary=plan.summary,
            meta=plan.meta,
            created_at=plan.created_at,
            recommendations=[RecommendationPublic.model_validate(r) for r in recs],
        )

    async def list_open(self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None):
        await self._set_rls(user_id)
        rows = await self.repo.list_open(user_id, identifier_id)
        return [RecommendationPublic.model_validate(r) for r in rows]

    async def update_status(
        self, user_id: uuid.UUID, rec_id: uuid.UUID, status: str
    ) -> RecommendationPublic:
        await self._set_rls(user_id)
        row = await self.repo.get(rec_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        # block semi_automated done until Sprint 7 unless user marks guided complete
        if status == "done" and row.lane == "semi_automated" and (row.meta or {}).get("sprint7_required"):
            # allow "queued" semantic via in_progress; done only after remediation sprint
            if status == "done":
                # permit manual mark for MVP honesty
                pass
        await self.repo.set_status(row, status)
        await self.audit.log(
            "recommendation.status_updated",
            user_id=user_id,
            resource_type="recommendation",
            resource_id=str(rec_id),
            details={"status": status, "code": row.code},
        )
        await self.session.commit()
        return RecommendationPublic.model_validate(row)

    async def dispute_finding(
        self,
        user_id: uuid.UUID,
        finding_id: uuid.UUID,
        reason: str,
        *,
        rescore: bool = True,
    ) -> dict[str, Any]:
        """
        Dispute = mark finding dismissed (false positive / not me) → optional PDSS rescore
        → regenerate recommendations. G1: finding must belong to user.
        """
        await self._set_rls(user_id)
        finding = await self.findings.get_finding(finding_id, user_id)
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")

        finding.status = "dismissed"
        # stash reason in attributes
        finding.attributes = {**(finding.attributes or {}), "dispute_reason": reason[:500]}
        await self.session.flush()

        await self.audit.log(
            "finding.disputed",
            user_id=user_id,
            resource_type="finding",
            resource_id=str(finding_id),
            details={"reason": reason[:200]},
        )

        score_result = None
        if rescore:
            score_result = await self.scoring.compute(
                user_id,
                identifier_id=finding.identifier_id,
                persist=True,
                trigger="dispute_rescore",
            )
            # regenerate plan
            plan = await self.generate(
                user_id, identifier_id=finding.identifier_id, persist=True
            )
        else:
            plan = None
            await self.session.commit()

        return {
            "message": "Finding dismissed as disputed",
            "finding_id": str(finding_id),
            "score": score_result.model_dump() if score_result else None,
            "plan_id": str(plan.id) if plan else None,
        }
```

---

## 14. NEW: `backend/app/services/alert_service.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.deltas import score_delta, finding_delta
from app.repositories.alert_repository import AlertRepository
from app.repositories.score_repository import ScoreRepository
from app.repositories.finding_repository import FindingRepository
from app.services.audit_service import AuditService
from app.services.discovery_service import DiscoveryService
from app.schemas.recommendations_alerts import AlertPublic

logger = get_logger(__name__)


class AlertService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AlertRepository(session)
        self.scores = ScoreRepository(session)
        self.findings = FindingRepository(session)
        self.audit = AuditService(session)
        self.settings = get_settings()

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def list_alerts(self, user_id: uuid.UUID, unread_only: bool = False) -> list[AlertPublic]:
        await self._set_rls(user_id)
        rows = await self.repo.list(user_id, unread_only=unread_only)
        return [AlertPublic.model_validate(r) for r in rows]

    async def mark_read(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> AlertPublic:
        await self._set_rls(user_id)
        row = await self.repo.get(alert_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        await self.repo.mark_read(row)
        await self.session.commit()
        return AlertPublic.model_validate(row)

    async def dismiss(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> dict:
        await self._set_rls(user_id)
        row = await self.repo.get(alert_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        await self.repo.dismiss(row)
        await self.session.commit()
        return {"message": "Dismissed"}

    async def emit(
        self,
        user_id: uuid.UUID,
        *,
        kind: str,
        title: str,
        body: str,
        severity: str = "info",
        identifier_id: uuid.UUID | None = None,
        payload: dict | None = None,
    ) -> Alert:
        row = await self.repo.create(
            user_id=user_id,
            kind=kind,
            title=title,
            body=body,
            severity=severity,
            identifier_id=identifier_id,
            payload=payload,
        )
        return row

    async def compute_deltas(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        await self._set_rls(user_id)
        history = await self.scores.history(user_id, identifier_id=identifier_id, limit=2)
        score_part = None
        if len(history) >= 2:
            newer, older = history[0], history[1]
            sd = score_delta(
                float(older.score_combined),
                float(newer.score_combined),
                older.severity,
                newer.severity,
            )
            score_part = sd.to_dict()
            # alert on jump up
            if sd.delta >= self.settings.alert_score_jump_threshold:
                await self.emit(
                    user_id,
                    kind="score_jump",
                    title=f"PDSS increased by {sd.delta:.1f}",
                    body=sd.to_dict()["summary"],
                    severity="high" if sd.delta >= 2 else "medium",
                    identifier_id=identifier_id,
                    payload=sd.to_dict(),
                )

        # finding delta: compare open set fingerprint via times_seen / status — simplified
        findings = await self.findings.list_findings(user_id, identifier_id=identifier_id, limit=500)
        open_ids = {str(f.id) for f in findings if f.status == "open"}
        # Without full previous snapshot, use first_seen_scan heuristic: new if times_seen==1 and recent
        now = datetime.now(timezone.utc)
        new_ids = [
            str(f.id)
            for f in findings
            if f.status == "open"
            and f.times_seen == 1
            and f.first_seen_at
            and (now - f.first_seen_at).total_seconds() < 86400
        ]
        high_new = [
            f
            for f in findings
            if str(f.id) in set(new_ids) and f.severity_hint in {"high", "critical"}
        ]
        if self.settings.alert_new_high_severity and high_new:
            for f in high_new[:5]:
                await self.emit(
                    user_id,
                    kind="severity_high",
                    title=f"New high-severity finding: {f.title[:80]}",
                    body=f.summary[:500],
                    severity="high",
                    identifier_id=f.identifier_id,
                    payload={"finding_id": str(f.id), "source": f.source, "kind": f.kind},
                )

        fd = finding_delta(set(), open_ids)  # baseline-lite
        fd.new_finding_ids = new_ids
        finding_part = fd.to_dict()

        await self.session.commit()
        summary = " | ".join(
            filter(
                None,
                [
                    score_part["summary"] if score_part else None,
                    finding_part["summary"],
                ],
            )
        )
        return {"score": score_part, "findings": finding_part, "summary": summary or "No deltas"}

    async def request_rescan(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        *,
        connector_ids: list[str] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Quota-aware rescan — wraps DiscoveryService.create_scan with cooldown."""
        await self._set_rls(user_id)
        now = datetime.now(timezone.utc)
        policy = await self.repo.get_policy(user_id, identifier_id)
        cooldown = timedelta(hours=self.settings.rescan_cooldown_hours)

        if not force and policy and policy.last_rescan_at:
            elapsed = now - policy.last_rescan_at
            if elapsed < cooldown:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rescan cooldown active. Retry after {policy.last_rescan_at + cooldown}",
                )

        discovery = DiscoveryService(self.session)
        scan = await discovery.create_scan(
            user_id,
            identifier_id,
            connector_ids=connector_ids,
            layer_scope="surface",
        )

        # update policy timestamps
        interval = (
            policy.interval_hours
            if policy
            else self.settings.scheduled_rescan_interval_hours
        )
        if not policy:
            policy = await self.repo.upsert_policy(
                user_id=user_id,
                identifier_id=identifier_id,
                enabled=self.settings.feature_scheduled_rescans,
                interval_hours=interval,
            )
        await self.repo.touch_policy(policy, now, interval)

        await self.emit(
            user_id,
            kind="rescan_available",
            title="Rescan started",
            body=f"Scan {scan.id} queued for identifier {identifier_id}",
            severity="info",
            identifier_id=identifier_id,
            payload={"scan_id": str(scan.id)},
        )
        await self.session.commit()
        return {
            "message": "Rescan started",
            "scan_id": str(scan.id),
            "status": scan.status,
        }

    async def upsert_rescan_policy(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        enabled: bool,
        interval_hours: int,
    ) -> dict[str, Any]:
        await self._set_rls(user_id)
        now = datetime.now(timezone.utc)
        row = await self.repo.upsert_policy(
            user_id=user_id,
            identifier_id=identifier_id,
            enabled=enabled,
            interval_hours=interval_hours,
        )
        if enabled and not row.next_eligible_at:
            row.next_eligible_at = now + timedelta(hours=interval_hours)
            await self.session.flush()
        await self.session.commit()
        return {
            "identifier_id": str(identifier_id),
            "enabled": row.enabled,
            "interval_hours": row.interval_hours,
            "last_rescan_at": row.last_rescan_at.isoformat() if row.last_rescan_at else None,
            "next_eligible_at": row.next_eligible_at.isoformat() if row.next_eligible_at else None,
        }

    async def reconcile_scheduled(self) -> dict[str, int]:
        """Beat: due policies → rescan if quota allows; purge old alerts."""
        now = datetime.now(timezone.utc)
        due = await self.repo.list_due_policies(now)
        started = 0
        skipped = 0
        for pol in due:
            if not self.settings.feature_scheduled_rescans:
                skipped += 1
                continue
            try:
                await self._set_rls(pol.user_id)
                await self.request_rescan(pol.user_id, pol.identifier_id, force=False)
                started += 1
            except HTTPException:
                skipped += 1
            except Exception:
                logger.exception("scheduled_rescan_failed", policy_id=str(pol.id))
                skipped += 1
        purged = await self.repo.purge_old(self.settings.alert_retention_days)
        await self.session.commit()
        return {"started": started, "skipped": skipped, "alerts_purged": purged}
```

---

## 15. Hook: post-scan alerts + optional plan generation

In `backend/app/services/discovery_service.py` after successful finalize + post_scan score (Sprint 5 hook), add:

```python
        try:
            from app.services.alert_service import AlertService
            from app.services.recommendation_service import RecommendationService
            alerts = AlertService(self.session)
            await alerts.compute_deltas(scan.user_id, scan.identifier_id)
            recs = RecommendationService(self.session)
            await recs.generate(scan.user_id, identifier_id=scan.identifier_id, persist=True)
            await alerts.emit(
                scan.user_id,
                kind="plan_ready",
                title="New remediation plan ready",
                body="Recommendations updated after scan + PDSS.",
                severity="info",
                identifier_id=scan.identifier_id,
                payload={"scan_id": str(scan.id)},
            )
            await self.session.commit()
        except Exception:
            logger.exception("post_scan_alerts_plan_failed", scan_id=str(scan.id))
```

---

## 16. NEW: `backend/app/api/v1/recommendations.py`

```python
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.recommendations_alerts import (
    PlanGenerateRequest,
    PlanPublic,
    RecommendationPublic,
    RecommendationStatusUpdate,
    DisputeRequest,
)
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _svc(db: AsyncSession = Depends(get_db)) -> RecommendationService:
    return RecommendationService(db)


@router.post("/generate", response_model=PlanPublic)
async def generate_plan(
    body: PlanGenerateRequest,
    current_user: CurrentUser,
    svc: RecommendationService = Depends(_svc),
):
    """Build two-lane prioritized plan (urgency + ROI + DAG) from findings + PDSS."""
    return await svc.generate(
        current_user.id,
        identifier_id=body.identifier_id,
        persist=body.persist,
    )


@router.get("/latest", response_model=PlanPublic)
async def latest_plan(
    current_user: CurrentUser,
    identifier_id: Optional[UUID] = None,
    svc: RecommendationService = Depends(_svc),
):
    return await svc.latest_plan(current_user.id, identifier_id)


@router.get("", response_model=list[RecommendationPublic])
async def list_open_recommendations(
    current_user: CurrentUser,
    identifier_id: Optional[UUID] = None,
    svc: RecommendationService = Depends(_svc),
):
    return await svc.list_open(current_user.id, identifier_id)


@router.patch("/{rec_id}", response_model=RecommendationPublic)
async def update_recommendation_status(
    rec_id: UUID,
    body: RecommendationStatusUpdate,
    current_user: CurrentUser,
    svc: RecommendationService = Depends(_svc),
):
    return await svc.update_status(current_user.id, rec_id, body.status)


@router.post("/findings/{finding_id}/dispute")
async def dispute_finding(
    finding_id: UUID,
    body: DisputeRequest,
    current_user: CurrentUser,
    svc: RecommendationService = Depends(_svc),
):
    """Dismiss disputed finding and rescore PDSS (closed loop)."""
    return await svc.dispute_finding(
        current_user.id, finding_id, body.reason, rescore=body.rescore
    )
```

---

## 17. NEW: `backend/app/api/v1/alerts.py`

```python
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.recommendations_alerts import (
    AlertPublic,
    RescanRequest,
    RescanPolicyUpsert,
    DeltaResponse,
    Message,
)
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _svc(db: AsyncSession = Depends(get_db)) -> AlertService:
    return AlertService(db)


@router.get("", response_model=list[AlertPublic])
async def list_alerts(
    current_user: CurrentUser,
    unread_only: bool = False,
    svc: AlertService = Depends(_svc),
):
    return await svc.list_alerts(current_user.id, unread_only=unread_only)


@router.post("/{alert_id}/read", response_model=AlertPublic)
async def mark_read(
    alert_id: UUID,
    current_user: CurrentUser,
    svc: AlertService = Depends(_svc),
):
    return await svc.mark_read(current_user.id, alert_id)


@router.post("/{alert_id}/dismiss", response_model=Message)
async def dismiss_alert(
    alert_id: UUID,
    current_user: CurrentUser,
    svc: AlertService = Depends(_svc),
):
    return await svc.dismiss(current_user.id, alert_id)


@router.get("/deltas", response_model=DeltaResponse)
async def get_deltas(
    current_user: CurrentUser,
    identifier_id: Optional[UUID] = None,
    svc: AlertService = Depends(_svc),
):
    data = await svc.compute_deltas(current_user.id, identifier_id)
    return DeltaResponse(**data)


@router.post("/rescan")
async def start_rescan(
    body: RescanRequest,
    current_user: CurrentUser,
    svc: AlertService = Depends(_svc),
):
    """Quota + cooldown aware rescan of a verified identifier."""
    return await svc.request_rescan(
        current_user.id,
        body.identifier_id,
        connector_ids=body.connector_ids,
        force=body.force,
    )


@router.put("/rescan-policy")
async def upsert_rescan_policy(
    body: RescanPolicyUpsert,
    current_user: CurrentUser,
    svc: AlertService = Depends(_svc),
):
    return await svc.upsert_rescan_policy(
        current_user.id,
        body.identifier_id,
        body.enabled,
        body.interval_hours,
    )
```

---

## 18. UPDATE: `backend/app/main.py`

```python
from app.api.v1 import (
    health, auth, identifiers, connectors, scans, identity, scores,
    recommendations, alerts,
)

app.include_router(recommendations.router, prefix=settings.api_v1_prefix)
app.include_router(alerts.router, prefix=settings.api_v1_prefix)

# root message
"version": "0.6.0",
"message": "DigiZafe Sprint 6 Recommendations & Alerts — ready",
```

---

## 19. NEW: `backend/app/tasks/alert_tasks.py`

```python
from __future__ import annotations

import asyncio

from app.worker import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _reconcile_async() -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.alert_service import AlertService

    async with AsyncSessionLocal() as session:
        svc = AlertService(session)
        return await svc.reconcile_scheduled()


@celery_app.task(name="app.tasks.alert_tasks.reconcile_alerts_rescans_task")
def reconcile_alerts_rescans_task() -> dict:
    logger.info("reconcile_alerts_rescans_start")
    return _run_async(_reconcile_async()) or {}
```

---

## 20. UPDATE: `backend/app/worker.py` beat_schedule

```python
    include=[
        "app.tasks",
        "app.tasks.discovery_tasks",
        "app.tasks.alert_tasks",
    ],
...
    beat_schedule={
        "reconcile-scans": {
            "task": "app.tasks.discovery_tasks.reconcile_scans_task",
            "schedule": float(settings.scan_reconcile_interval_seconds),
        },
        "reconcile-alerts-rescans": {
            "task": "app.tasks.alert_tasks.reconcile_alerts_rescans_task",
            "schedule": float(settings.alert_reconcile_interval_seconds),
        },
    },
```

---

## 21. UPDATE: `backend/app/alembic/env.py`

Import `Recommendation`, `RecommendationPlan`, `Alert`, `RescanPolicy`.

---

## 22. Alembic migration `sprint6_recommendations_alerts`

```python
"""sprint6_recommendations_alerts"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "sprint6_rec_001"
down_revision: Union[str, None] = "sprint5_pdss_001"  # ← your Sprint 5 rev
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("score_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("freeze_recommended", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("dag_order", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_recommendation_plans_user_id", "recommendation_plans", ["user_id"])
    op.create_index("ix_recommendation_plans_created_at", "recommendation_plans", ["created_at"])

    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("lane", sa.String(32), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("urgency", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("effort_hours", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("roi", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("priority", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("depends_on", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("related_finding_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("links", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("playbook_key", sa.String(128), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("model_version", sa.String(64), nullable=False, server_default="rec-v1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_recommendations_user_id", "recommendations", ["user_id"])
    op.create_index("ix_recommendations_plan_id", "recommendations", ["plan_id"])
    op.create_index("ix_recommendations_code", "recommendations", ["code"])
    op.create_index("ix_recommendations_lane", "recommendations", ["lane"])
    op.create_index("ix_recommendations_status", "recommendations", ["status"])
    op.create_index("ix_recommendations_priority", "recommendations", ["priority"])

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False, server_default="info"),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("dismissed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])
    op.create_index("ix_alerts_kind", "alerts", ["kind"])
    op.create_index("ix_alerts_read", "alerts", ["read"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])

    op.create_table(
        "rescan_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("interval_hours", sa.Integer(), server_default="168", nullable=False),
        sa.Column("last_rescan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_eligible_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_rescan_policies_user_id", "rescan_policies", ["user_id"])
    op.create_index("ix_rescan_policies_identifier_id", "rescan_policies", ["identifier_id"])

    for table in ("recommendation_plans", "recommendations", "alerts", "rescan_policies"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    for pol, tbl in [
        ("recommendation_plans_self", "recommendation_plans"),
        ("recommendations_self", "recommendations"),
        ("alerts_self", "alerts"),
        ("rescan_policies_self", "rescan_policies"),
    ]:
        op.execute(f"""
            CREATE POLICY {pol} ON {tbl}
            FOR ALL
            USING (user_id::text = current_setting('app.current_user_id', true))
            WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
        """)


def downgrade() -> None:
    for pol, tbl in [
        ("rescan_policies_self", "rescan_policies"),
        ("alerts_self", "alerts"),
        ("recommendations_self", "recommendations"),
        ("recommendation_plans_self", "recommendation_plans"),
    ]:
        op.execute(f"DROP POLICY IF EXISTS {pol} ON {tbl}")
    for table in ("rescan_policies", "alerts", "recommendations", "recommendation_plans"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
```

---

## 23. Unit tests

### `backend/tests/unit/test_recommendation_dag.py`

```python
from app.domain.recommendation import (
    FindingLite,
    build_recommendations,
    topo_sort_codes,
    RecommendationDraft,
    recommend_freeze,
)


def _catalog():
    return {
        "priority_formula": {
            "urgency_weight": 0.45,
            "roi_weight": 0.4,
            "effort_penalty": 0.15,
            "pdss_marginal_boost": 0.35,
        },
        "freeze_recommend_rule": {
            "min_severity_hint": ["high", "critical"],
            "attribute_keywords": ["password", "ssn"],
        },
        "templates": [
            {
                "code": "change_password_breached",
                "lane": "guided",
                "title": "Change passwords",
                "summary": "x",
                "urgency_base": 0.95,
                "effort_hours": 0.5,
                "roi_weight": 1.0,
                "depends_on": [],
                "triggers": {"kinds": ["breach"], "min_severity": "medium"},
                "steps": ["a"],
                "playbook_key": "guided.password_reset",
            },
            {
                "code": "enable_mfa",
                "lane": "guided",
                "title": "Enable MFA",
                "summary": "y",
                "urgency_base": 0.85,
                "effort_hours": 0.25,
                "roi_weight": 0.85,
                "depends_on": ["change_password_breached"],
                "triggers": {"kinds": ["breach"], "min_severity": "low"},
                "steps": ["b"],
                "playbook_key": "guided.mfa",
            },
            {
                "code": "credit_freeze",
                "lane": "guided",
                "title": "Freeze",
                "summary": "z",
                "urgency_base": 0.9,
                "effort_hours": 1.0,
                "roi_weight": 0.95,
                "depends_on": [],
                "triggers": {
                    "kinds": ["breach"],
                    "min_severity": "high",
                    "attribute_contains": ["password"],
                },
                "steps": ["c"],
                "links": [],
                "playbook_key": "guided.credit_freeze",
            },
        ],
    }


def test_topo_mfa_after_password():
    findings = [
        FindingLite(
            id="1",
            kind="breach",
            source="xposedornot",
            title="Adobe",
            severity_hint="high",
            confidence=0.9,
            track="confirmed",
            attributes={"xposed_data": "Passwords", "password_risk": "easytocrack"},
        )
    ]
    drafts = build_recommendations(_catalog(), findings, score_combined=6.5)
    codes = [d.code for d in drafts]
    assert "change_password_breached" in codes
    assert "enable_mfa" in codes
    # password before mfa in DAG order
    assert codes.index("change_password_breached") < codes.index("enable_mfa")


def test_recommend_freeze_high():
    findings = [
        FindingLite(
            id="1",
            kind="breach",
            source="xposedornot",
            title="X",
            severity_hint="high",
            confidence=0.9,
            track="confirmed",
            attributes={"xposed_data": "Passwords"},
        )
    ]
    assert recommend_freeze(findings, _catalog()["freeze_recommend_rule"]) is True
```

### `backend/tests/unit/test_deltas.py`

```python
from app.domain.deltas import score_delta, finding_delta


def test_score_improved():
    d = score_delta(7.0, 5.5, "high", "medium")
    assert d.improved
    assert d.delta == -1.5


def test_finding_delta_new_and_resolved():
    fd = finding_delta({"a", "b"}, {"b", "c"}, prev_resolved_ids={"c"})
    assert "c" in fd.new_finding_ids
    assert "a" in fd.resolved_finding_ids
    assert "c" in fd.regressed_finding_ids
```

---

## 24. Docs

### `docs/runbooks/recommendations-alerts.md`

```markdown
# Recommendations & Alerts (Sprint 6)

## Two lanes
| Lane | Meaning | Sprint |
|------|---------|--------|
| guided | Always available user steps (password, MFA, freeze, know, SERP) | 6 |
| semi_automated | Green broker opt-outs | Planned 6, **executed 7** |

## Flow
1. Scan + PDSS (Sprint 4–5)
2. `POST /api/v1/recommendations/generate` `{ "identifier_id": "..." }`
3. Follow DAG order (`depends_on` / `dag_order`)
4. Mark done: `PATCH /api/v1/recommendations/{id}` `{ "status": "done" }`
5. Dispute FP: `POST /api/v1/recommendations/findings/{id}/dispute` → dismiss + rescore
6. Deltas: `GET /api/v1/alerts/deltas`
7. Rescan: `POST /api/v1/alerts/rescan` (quota + cooldown)

## AIDR mapping
| AIDR | DigiZafe Sprint 6 |
|------|-------------------|
| recommendFreeze | credit_freeze template + recommend_freeze() |
| freeze.js targets | recommendation links |
| right-to-know | right_to_know template (generator text Sprint 7/8 full) |
| diff.js | domain/deltas.py + alerts |
| breach severity | triggers on findings from XposedOrNot |

## Free path
No paid APIs. CapSolver not required. Semi-automated lane is queue-only until Sprint 7.
```

### UPDATE `docs/aidr-mapping.md`

```markdown
| aidr freeze / recommendFreeze | recommendations credit_freeze + freeze links | Sprint 6 plan; tracking state Sprint 7+ |
| aidr know | right_to_know recommendation template | Full generators Sprint 7–8 |
| aidr complaints | (not executed) | Sprint 7–8 generators |
| lib/diff.js | domain/deltas.py + AlertService.compute_deltas | Sprint 6 |
```

---

# PART C — Finish Sprint 6

```bash
# 1. Copy recommendation_catalog.json → shared/score_model/
# 2. Merge env, rebuild, migrate
docker compose build api worker beat
docker compose up -d
docker compose exec api alembic upgrade head

# 3. Ensure PDSS exists for identifier $ID
curl -s -X POST http://localhost:8000/api/v1/scores/compute \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d "{\"identifier_id\":\"$ID\"}" | jq .

# 4. Generate plan
curl -s -X POST http://localhost:8000/api/v1/recommendations/generate \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d "{\"identifier_id\":\"$ID\"}" | jq .

# 5. List open recs
curl -s "http://localhost:8000/api/v1/recommendations?identifier_id=$ID" \
  -H "Authorization: Bearer $ACCESS" | jq .

# 6. Deltas + alerts
curl -s "http://localhost:8000/api/v1/alerts/deltas?identifier_id=$ID" \
  -H "Authorization: Bearer $ACCESS" | jq .
curl -s http://localhost:8000/api/v1/alerts -H "Authorization: Bearer $ACCESS" | jq .

# 7. Dispute a finding (use a real finding uuid)
# curl -s -X POST .../recommendations/findings/$FID/dispute \
#   -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
#   -d '{"reason":"Not my account / false positive","rescore":true}' | jq .

# 8. Rescan (cooldown + quota)
curl -s -X POST http://localhost:8000/api/v1/alerts/rescan \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d "{\"identifier_id\":\"$ID\"}" | jq .

# 9. Unit tests
docker compose exec api pytest backend/tests/unit/test_recommendation_dag.py backend/tests/unit/test_deltas.py -v

git add .
git commit -m "feat(sprint-6): two-lane recommendations+DAG, dispute→rescore, deltas, alerts, quota rescans"
```

---

# Sprint 6 Definition of Done

- [ ] MASTER_ENGINEERING_CONTEXT respected  
- [ ] Pure `recommendation.py`: two-lane, urgency/ROI, **DAG topo order**  
- [ ] Catalog versioned at `shared/score_model/recommendation_catalog.json`  
- [ ] Freeze recommendation (AIDR recommendFreeze lineage) with public free bureau links  
- [ ] Plans + recommendations persisted with RLS  
- [ ] Dispute finding → dismissed → **rescore PDSS** → regenerate plan  
- [ ] Pure `deltas.py` + `/alerts/deltas`  
- [ ] Alerts: score_jump, severity_high, plan_ready, rescan  
- [ ] Quota-aware rescan + cooldown + optional schedule policy  
- [ ] Beat task for scheduled rescans + alert purge  
- [ ] Post-scan hook: deltas + plan generation  
- [ ] Semi-automated lane **queued only** (no Playwright yet)  
- [ ] Unit tests for DAG + deltas green  
- [ ] Zero paid keys  

→ **Sprint 6 complete.**  
Next: **Sprint 7 — Remediation Engine (AIDR core)** (Playwright runners, broker_optout_state, verify loop, free CAPTCHA path, freeze/know/complaints execution, closed-loop re-score).

---

## Endpoint quick reference

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /api/v1/recommendations/generate | Bearer | Build prioritized two-lane plan |
| GET | /api/v1/recommendations/latest | Bearer | Latest plan + items |
| GET | /api/v1/recommendations | Bearer | Open recommendations |
| PATCH | /api/v1/recommendations/{id} | Bearer | Update status |
| POST | /api/v1/recommendations/findings/{id}/dispute | Bearer | Dispute → rescore |
| GET | /api/v1/alerts | Bearer | List alerts |
| POST | /api/v1/alerts/{id}/read | Bearer | Mark read |
| POST | /api/v1/alerts/{id}/dismiss | Bearer | Dismiss |
| GET | /api/v1/alerts/deltas | Bearer | Score/finding deltas |
| POST | /api/v1/alerts/rescan | Bearer | Cooldown+quota rescan |
| PUT | /api/v1/alerts/rescan-policy | Bearer | Schedule policy |

---

## File checklist

| Action | Path |
|--------|------|
| UPDATE | `.env.example`, `config.py`, `main.py`, `worker.py`, `models/__init__.py`, `alembic/env.py` |
| NEW | `shared/score_model/recommendation_catalog.json` |
| NEW | `backend/app/domain/recommendation.py` |
| NEW | `backend/app/domain/deltas.py` |
| NEW | `backend/app/models/recommendation.py` |
| NEW | `backend/app/models/alert.py` |
| NEW | `backend/app/schemas/recommendations_alerts.py` |
| NEW | `backend/app/repositories/recommendation_repository.py` |
| NEW | `backend/app/repositories/alert_repository.py` |
| NEW | `backend/app/services/recommendation_service.py` |
| NEW | `backend/app/services/alert_service.py` |
| EXTEND | `catalog_loader.py` + discovery post-scan hook |
| NEW | `backend/app/api/v1/recommendations.py` |
| NEW | `backend/app/api/v1/alerts.py` |
| NEW | `backend/app/tasks/alert_tasks.py` |
| NEW | migration `sprint6_recommendations_alerts` |
| NEW | unit tests + runbook + aidr-mapping update |

---

**You are ready for Sprint 6.**  
Save as `Sprint6.md`, apply in order, set `down_revision` to Sprint 5, migrate, generate a plan on a scored identifier, dispute one finding, run a rescan, commit.

When Sprint 6 is green, ask for **Sprint 7** the same way.