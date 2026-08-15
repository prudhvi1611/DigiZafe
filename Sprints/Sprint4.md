# DigiZafe — Sprint 4 Discovery & Evidence  
**Complete Implementation Guide from Sprint 3 Baseline + All File Contents**

**Document version:** 1.0  
**Based on:** MASTER_ENGINEERING_CONTEXT.md v2.1  
**Depends on:** Sprint 0–3 green (Auth, Identifiers, Verification, EgressFetcher, Connector SDK, free Surface Green incl. XposedOrNot primary)  
**Goal:** From completed Sprint 3 → **Postgres-backed scan state machine + reconciliation**, **3-layer evidence** with TTL/purge, **SSE** scan progress, **activate verified-only trigger (G1)** on scans/observations/findings, **XposedOrNot → findings normalization**, DiscoveryService that dispatches connectors asynchronously (never in request path), durable history of connector runs, honest skip/rate-limit status.

**Effort estimate:** ~10 days (solo)  
**Critical path next:** Sprint 5 Identity Graph & PDSS Scoring

> **Load MASTER_ENGINEERING_CONTEXT.md first in every session.**  
> You implement; you do not re-decide architecture. G1 self-only safety is non-negotiable.  
> Connectors never touch DB. Orchestration = Postgres state machine + reconcile sweep (not Celery chords).

---

# PART A — Pre-Sprint 4 (run once from DigiZafe root)

```bash
# 1. Confirm Sprint 3 is green
docker compose ps
curl -s http://localhost:8000/api/v1/health | jq .
# Probe a verified email with xposedornot must work (Sprint 3)

# 2. Package dirs
mkdir -p backend/app/{domain,services,repositories,models,schemas,tasks}
mkdir -p backend/tests/{unit,integration}
mkdir -p docs/runbooks
touch backend/app/tasks/__init__.py

# 3. Rebuild after env/config edits
docker compose build api worker beat
echo "✅ Pre-Sprint 4 ready. Apply file contents below."
```

**No new hard deps required** (`httpx`, `celery`, `redis`, `sqlalchemy` already present). SSE uses `StreamingResponse` (compatible with fastapi>=0.115).

---

# PART B — Sprint 4 File Contents

---

## 1. UPDATE: Root `.env.example` (append)

```bash
# === Sprint 4: Discovery & Evidence ===
# Scan state machine
SCAN_DEFAULT_DEADLINE_MINUTES=30
SCAN_MAX_CONCURRENT_PER_USER=2
SCAN_RECONCILE_INTERVAL_SECONDS=60
SCAN_STALE_RUNNING_MINUTES=45

# Per-user scan quota (daily full scans — separate from Sprint 3 probe quota)
DEFAULT_USER_SCAN_QUOTA_PER_DAY=20

# 3-layer evidence TTL
EVIDENCE_RAW_TTL_HOURS=24
EVIDENCE_SUMMARY_TTL_DAYS=30
# Layer 3 (durable finding metadata) — no auto-TTL; purge only on crypto-shred / user delete

# SSE
SSE_POLL_INTERVAL_SECONDS=1.5
SSE_HEARTBEAT_SECONDS=15
SSE_MAX_DURATION_SECONDS=1800
```

Merge into your real `.env`.

---

## 2. UPDATE: `backend/app/core/config.py`

Add these fields to `Settings` (keep all prior sprints):

```python
    # === Sprint 4: Discovery & Evidence ===
    scan_default_deadline_minutes: int = 30
    scan_max_concurrent_per_user: int = 2
    scan_reconcile_interval_seconds: int = 60
    scan_stale_running_minutes: int = 45

    # may already exist from Sprint 0:
    # default_user_scan_quota_per_day: int = 20

    evidence_raw_ttl_hours: int = 24
    evidence_summary_ttl_days: int = 30

    sse_poll_interval_seconds: float = 1.5
    sse_heartbeat_seconds: float = 15.0
    sse_max_duration_seconds: int = 1800
```

---

## 3. NEW: `backend/app/domain/scan_states.py`  
*(pure domain — valid transitions only)*

```python
"""Scan / connector-run state machine (pure)."""

from __future__ import annotations

from enum import Enum


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"  # finished with some connector failures/skips
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ConnectorRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


# Terminal scan statuses
TERMINAL_SCAN: frozenset[ScanStatus] = frozenset(
    {
        ScanStatus.COMPLETED,
        ScanStatus.PARTIAL,
        ScanStatus.FAILED,
        ScanStatus.CANCELLED,
        ScanStatus.TIMED_OUT,
    }
)

TERMINAL_RUN: frozenset[ConnectorRunStatus] = frozenset(
    {
        ConnectorRunStatus.SUCCEEDED,
        ConnectorRunStatus.SKIPPED,
        ConnectorRunStatus.FAILED,
        ConnectorRunStatus.TIMED_OUT,
    }
)

# Allowed transitions: from -> set of to
_SCAN_TRANSITIONS: dict[ScanStatus, set[ScanStatus]] = {
    ScanStatus.PENDING: {ScanStatus.RUNNING, ScanStatus.CANCELLED, ScanStatus.TIMED_OUT, ScanStatus.FAILED},
    ScanStatus.RUNNING: {
        ScanStatus.COMPLETED,
        ScanStatus.PARTIAL,
        ScanStatus.FAILED,
        ScanStatus.CANCELLED,
        ScanStatus.TIMED_OUT,
    },
    # Terminal states have no outgoing transitions
    ScanStatus.COMPLETED: set(),
    ScanStatus.PARTIAL: set(),
    ScanStatus.FAILED: set(),
    ScanStatus.CANCELLED: set(),
    ScanStatus.TIMED_OUT: set(),
}

_RUN_TRANSITIONS: dict[ConnectorRunStatus, set[ConnectorRunStatus]] = {
    ConnectorRunStatus.PENDING: {
        ConnectorRunStatus.RUNNING,
        ConnectorRunStatus.SKIPPED,
        ConnectorRunStatus.FAILED,
        ConnectorRunStatus.TIMED_OUT,
        ConnectorRunStatus.CANCELLED if False else ConnectorRunStatus.FAILED,  # noqa — keep simple
    },
    ConnectorRunStatus.RUNNING: {
        ConnectorRunStatus.SUCCEEDED,
        ConnectorRunStatus.SKIPPED,
        ConnectorRunStatus.FAILED,
        ConnectorRunStatus.TIMED_OUT,
    },
    ConnectorRunStatus.SUCCEEDED: set(),
    ConnectorRunStatus.SKIPPED: set(),
    ConnectorRunStatus.FAILED: set(),
    ConnectorRunStatus.TIMED_OUT: set(),
}


class InvalidTransition(ValueError):
    pass


def can_transition_scan(current: ScanStatus | str, new: ScanStatus | str) -> bool:
    cur = ScanStatus(current)
    nxt = ScanStatus(new)
    if cur == nxt:
        return True
    return nxt in _SCAN_TRANSITIONS.get(cur, set())


def transition_scan(current: ScanStatus | str, new: ScanStatus | str) -> ScanStatus:
    cur = ScanStatus(current)
    nxt = ScanStatus(new)
    if cur == nxt:
        return cur
    if nxt not in _SCAN_TRANSITIONS.get(cur, set()):
        raise InvalidTransition(f"Invalid scan transition {cur.value} → {nxt.value}")
    return nxt


def can_transition_run(current: ConnectorRunStatus | str, new: ConnectorRunStatus | str) -> bool:
    cur = ConnectorRunStatus(current)
    nxt = ConnectorRunStatus(new)
    if cur == nxt:
        return True
    allowed = _RUN_TRANSITIONS.get(cur, set())
    # PENDING can also go to SUCCEEDED directly in edge cases
    if cur == ConnectorRunStatus.PENDING:
        allowed = allowed | {
            ConnectorRunStatus.SUCCEEDED,
            ConnectorRunStatus.SKIPPED,
            ConnectorRunStatus.FAILED,
            ConnectorRunStatus.TIMED_OUT,
            ConnectorRunStatus.RUNNING,
        }
    return nxt in allowed


def transition_run(current: ConnectorRunStatus | str, new: ConnectorRunStatus | str) -> ConnectorRunStatus:
    cur = ConnectorRunStatus(current)
    nxt = ConnectorRunStatus(new)
    if cur == nxt:
        return cur
    if not can_transition_run(cur, nxt):
        raise InvalidTransition(f"Invalid connector-run transition {cur.value} → {nxt.value}")
    return nxt


def is_terminal_scan(status: ScanStatus | str) -> bool:
    return ScanStatus(status) in TERMINAL_SCAN


def is_terminal_run(status: ConnectorRunStatus | str) -> bool:
    return ConnectorRunStatus(status) in TERMINAL_RUN


def derive_scan_status_from_runs(
    run_statuses: list[ConnectorRunStatus | str],
) -> ScanStatus:
    """
    After all runs terminal:
    - all succeeded (or empty) → COMPLETED
    - mix of success + skip/fail → PARTIAL
    - all failed/timed_out (no success) → FAILED
    - any still non-terminal → RUNNING (caller should not finalize yet)
    """
    if not run_statuses:
        return ScanStatus.COMPLETED

    statuses = [ConnectorRunStatus(s) for s in run_statuses]
    if any(not is_terminal_run(s) for s in statuses):
        return ScanStatus.RUNNING

    successes = sum(1 for s in statuses if s == ConnectorRunStatus.SUCCEEDED)
    fails = sum(
        1
        for s in statuses
        if s in (ConnectorRunStatus.FAILED, ConnectorRunStatus.TIMED_OUT)
    )
    skips = sum(1 for s in statuses if s == ConnectorRunStatus.SKIPPED)

    if successes > 0 and (fails > 0 or skips > 0):
        return ScanStatus.PARTIAL
    if successes > 0 and fails == 0:
        return ScanStatus.COMPLETED
    if successes == 0 and skips > 0 and fails == 0:
        return ScanStatus.COMPLETED  # all intentionally skipped
    return ScanStatus.FAILED
```

---

## 4. NEW: `backend/app/domain/findings_normalize.py`  
*(pure — map RawObservation / connector dicts → finding DTOs)*

```python
"""Normalize connector observations into durable finding shapes (pure)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID


@dataclass
class NormalizedFinding:
    """Ready to persist as Finding row."""

    kind: str  # breach | password_exposure | certificate | dns_rdap | profile | username_presence | serp | other
    source: str  # connector id e.g. xposedornot
    title: str
    summary: str
    severity_hint: str  # low | medium | high | critical | info
    confidence: float
    layer: str  # surface | deep | constrained_dark
    fingerprint: str  # stable dedupe key within (user, identifier, source)
    raw_ref: Optional[str] = None
    attributes: dict[str, Any] = field(default_factory=dict)
    attribution: Optional[str] = None
    observed_at: Optional[datetime] = None
    track: str = "confirmed"  # confirmed | possible — for two-track PDSS later


def _severity_for_breach(attrs: dict[str, Any], confidence: float) -> str:
    risk = str(attrs.get("risk_label") or attrs.get("password_risk") or "").lower()
    if risk in {"high", "critical", "plaintext", "easytocrack"}:
        return "high"
    if risk in {"medium", "moderate"}:
        return "medium"
    if "password" in str(attrs.get("xposed_data") or "").lower():
        return "high"
    if confidence >= 0.9:
        return "medium"
    return "low"


def _fingerprint(source: str, kind: str, raw_ref: str | None, title: str) -> str:
    import hashlib

    base = f"{source}|{kind}|{(raw_ref or title).strip().lower()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:40]


def normalize_observation(obs: dict[str, Any]) -> NormalizedFinding:
    """
    Accepts RawObservation.to_dict() or equivalent.
    XposedOrNot drivers: breach_name, risk_label, xposed_data, xposed_date, etc.
    """
    kind = str(obs.get("kind") or "other")
    source = str(obs.get("source") or "unknown")
    title = str(obs.get("title") or "Finding")
    summary = str(obs.get("summary") or "")
    confidence = float(obs.get("confidence") or 0.5)
    layer = str(obs.get("layer") or "surface")
    raw_ref = obs.get("raw_ref")
    attrs = dict(obs.get("attributes") or {})
    attribution = obs.get("attribution")

    observed_at = None
    if obs.get("observed_at"):
        try:
            raw = obs["observed_at"]
            if isinstance(raw, datetime):
                observed_at = raw
            else:
                observed_at = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            observed_at = datetime.now(timezone.utc)
    else:
        observed_at = datetime.now(timezone.utc)

    if kind == "breach":
        severity = _severity_for_breach(attrs, confidence)
        # Prefer structured breach name
        if attrs.get("breach_name") and not raw_ref:
            raw_ref = str(attrs["breach_name"])
        track = "confirmed" if confidence >= 0.8 else "possible"
    elif kind == "password_exposure":
        severity = "critical" if int(attrs.get("count") or 0) > 10 else "high"
        track = "confirmed"
    elif kind in {"certificate", "dns_rdap"}:
        severity = "info"
        track = "confirmed" if confidence >= 0.7 else "possible"
    elif kind in {"profile", "username_presence"}:
        severity = "low"
        track = "possible" if confidence < 0.85 else "confirmed"
    elif kind == "serp":
        severity = "info"
        track = "possible"
    else:
        severity = "info"
        track = "possible"

    fp = _fingerprint(source, kind, str(raw_ref) if raw_ref else None, title)

    return NormalizedFinding(
        kind=kind,
        source=source,
        title=title[:512],
        summary=summary[:4000],
        severity_hint=severity,
        confidence=max(0.0, min(1.0, confidence)),
        layer=layer,
        fingerprint=fp,
        raw_ref=str(raw_ref)[:512] if raw_ref else None,
        attributes=attrs,
        attribution=str(attribution)[:512] if attribution else None,
        observed_at=observed_at,
        track=track,
    )


def normalize_connector_result_observations(
    observations: list[dict[str, Any]],
) -> list[NormalizedFinding]:
    out: list[NormalizedFinding] = []
    seen: set[str] = set()
    for o in observations:
        if not isinstance(o, dict):
            continue
        nf = normalize_observation(o)
        if nf.fingerprint in seen:
            continue
        seen.add(nf.fingerprint)
        out.append(nf)
    return out
```

---

## 5. NEW: `backend/app/models/scan.py`

```python
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Scan(Base):
    """Postgres-backed discovery scan (state machine root)."""

    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    identifier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=False
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    # pending | running | completed | partial | failed | cancelled | timed_out

    layer_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="surface")
    # MVP: surface only; deep / constrained_dark later

    connector_ids: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    # null = auto-select by identifier type

    progress_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # attributions, skip reasons summary, etc.

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    connector_runs: Mapped[list["ScanConnectorRun"]] = relationship(
        "ScanConnectorRun", back_populates="scan", cascade="all, delete-orphan"
    )


class ScanConnectorRun(Base):
    """Per-connector unit of work within a scan."""

    __tablename__ = "scan_connector_runs"
    __table_args__ = (
        UniqueConstraint("scan_id", "connector_id", name="uq_scan_connector_run"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    identifier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)

    connector_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    # pending | running | succeeded | skipped | failed | timed_out

    skip_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finding_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    result_meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    scan: Mapped["Scan"] = relationship("Scan", back_populates="connector_runs")
```

---

## 6. NEW: `backend/app/models/observation_finding.py`

```python
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Observation(Base):
    """
    Layer-1-ish raw connector observation (short TTL).
    May hold a redacted snapshot; full HTML dumps are NOT stored.
    """

    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    identifier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), index=True, nullable=True
    )
    connector_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_connector_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )

    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    layer: Mapped[str] = mapped_column(String(32), nullable=False, default="surface")
    raw_ref: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    attributes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    attribution: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # redacted observation dict only — never full breach dumps / HTML

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Finding(Base):
    """
    Durable normalized finding (layer-3 metadata).
    Deduped by (user_id, identifier_id, source, fingerprint).
    """

    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "identifier_id",
            "source",
            "fingerprint",
            name="uq_findings_user_ident_source_fp",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    identifier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # G1: identifier must be verified — enforced by DB trigger

    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity_hint: Mapped[str] = mapped_column(String(32), nullable=False, default="info", index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    layer: Mapped[str] = mapped_column(String(32), nullable=False, default="surface", index=True)
    track: Mapped[str] = mapped_column(String(32), nullable=False, default="confirmed")  # confirmed | possible
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_ref: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, index=True)
    attributes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    attribution: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    first_seen_scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_seen_scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    times_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Soft status for remediation later
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    # open | acknowledged | remediating | resolved | dismissed

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EvidenceBlob(Base):
    """
    Explicit 3-layer evidence store.
    layer: raw | summary | durable
    raw = short TTL, summary = medium TTL, durable = finding-linked metadata (no auto purge)
    """

    __tablename__ = "evidence_blobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    identifier_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    finding_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), index=True, nullable=True
    )
    observation_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)

    layer: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # raw | summary | durable
    content_type: Mapped[str] = mapped_column(String(64), nullable=False, default="application/json")
    # Always JSON-redacted structured data — never raw HTML dumps long-term
    body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    # null for durable

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

---

## 7. UPDATE: `backend/app/models/__init__.py`

```python
from app.models.user import User, RefreshToken
from app.models.audit import AuditLog
from app.models.identifier import Identifier, VerificationChallenge
from app.models.consent_egress import ConsentRecord, EgressLedger
from app.models.connector_config import ConnectorConfig
from app.models.scan import Scan, ScanConnectorRun
from app.models.observation_finding import Observation, Finding, EvidenceBlob

__all__ = [
    "User",
    "RefreshToken",
    "AuditLog",
    "Identifier",
    "VerificationChallenge",
    "ConsentRecord",
    "EgressLedger",
    "ConnectorConfig",
    "Scan",
    "ScanConnectorRun",
    "Observation",
    "Finding",
    "EvidenceBlob",
]
```

---

## 8. NEW: `backend/app/schemas/scan.py`

```python
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ScanCreate(BaseModel):
    identifier_id: UUID
    connector_ids: Optional[list[str]] = None  # default: auto by type (excl. password)
    layer_scope: str = Field(default="surface", pattern="^(surface)$")  # MVP surface only


class ScanConnectorRunPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    connector_id: str
    status: str
    skip_reason: Optional[str] = None
    error: Optional[str] = None
    cache_hit: bool
    observation_count: int
    finding_count: int
    result_meta: Optional[dict[str, Any]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class ScanPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: UUID
    status: str
    layer_scope: str
    connector_ids: Optional[list[Any]] = None
    progress_pct: float
    message: Optional[str] = None
    error: Optional[str] = None
    observation_count: int
    finding_count: int
    deadline_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    meta: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    connector_runs: list[ScanConnectorRunPublic] = []


class ScanListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: UUID
    status: str
    progress_pct: float
    finding_count: int
    observation_count: int
    created_at: datetime
    finished_at: Optional[datetime] = None


class FindingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: UUID
    kind: str
    source: str
    title: str
    summary: str
    severity_hint: str
    confidence: float
    layer: str
    track: str
    raw_ref: Optional[str] = None
    attributes: Optional[dict[str, Any]] = None
    attribution: Optional[str] = None
    first_seen_at: datetime
    last_seen_at: datetime
    times_seen: int
    status: str
    created_at: datetime


class Message(BaseModel):
    message: str
```

---

## 9. NEW: `backend/app/repositories/scan_repository.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.scan import Scan, ScanConnectorRun
from app.domain.scan_states import (
    ScanStatus,
    ConnectorRunStatus,
    transition_scan,
    transition_run,
    is_terminal_scan,
    derive_scan_status_from_runs,
)


class ScanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, scan_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Scan]:
        result = await self.session.execute(
            select(Scan)
            .options(selectinload(Scan.connector_runs))
            .where(Scan.id == scan_id, Scan.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_internal(self, scan_id: uuid.UUID) -> Optional[Scan]:
        """Worker path — no user filter (worker sets RLS context separately)."""
        result = await self.session.execute(
            select(Scan)
            .options(selectinload(Scan.connector_runs))
            .where(Scan.id == scan_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> Sequence[Scan]:
        result = await self.session.execute(
            select(Scan)
            .where(Scan.user_id == user_id)
            .order_by(Scan.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def count_active_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Scan)
            .where(
                Scan.user_id == user_id,
                Scan.status.in_([ScanStatus.PENDING.value, ScanStatus.RUNNING.value]),
            )
        )
        return int(result.scalar_one() or 0)

    async def count_today_for_user(self, user_id: uuid.UUID) -> int:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(func.count())
            .select_from(Scan)
            .where(Scan.user_id == user_id, Scan.created_at >= start)
        )
        return int(result.scalar_one() or 0)

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        connector_ids: list[str] | None,
        deadline_at: datetime,
        layer_scope: str = "surface",
    ) -> Scan:
        scan = Scan(
            user_id=user_id,
            identifier_id=identifier_id,
            status=ScanStatus.PENDING.value,
            layer_scope=layer_scope,
            connector_ids=connector_ids,
            deadline_at=deadline_at,
            message="Queued",
            progress_pct=0.0,
        )
        self.session.add(scan)
        await self.session.flush()
        return scan

    async def add_connector_run(
        self,
        *,
        scan: Scan,
        connector_id: str,
    ) -> ScanConnectorRun:
        run = ScanConnectorRun(
            scan_id=scan.id,
            user_id=scan.user_id,
            identifier_id=scan.identifier_id,
            connector_id=connector_id,
            status=ConnectorRunStatus.PENDING.value,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def set_scan_status(
        self,
        scan: Scan,
        new_status: ScanStatus | str,
        *,
        message: str | None = None,
        error: str | None = None,
        progress_pct: float | None = None,
    ) -> Scan:
        nxt = transition_scan(scan.status, new_status)
        scan.status = nxt.value
        if message is not None:
            scan.message = message
        if error is not None:
            scan.error = error
        if progress_pct is not None:
            scan.progress_pct = progress_pct
        now = datetime.now(timezone.utc)
        if nxt == ScanStatus.RUNNING and scan.started_at is None:
            scan.started_at = now
        if is_terminal_scan(nxt):
            scan.finished_at = now
            if progress_pct is None:
                scan.progress_pct = 100.0
        await self.session.flush()
        return scan

    async def set_run_status(
        self,
        run: ScanConnectorRun,
        new_status: ConnectorRunStatus | str,
        *,
        skip_reason: str | None = None,
        error: str | None = None,
        cache_hit: bool | None = None,
        observation_count: int | None = None,
        finding_count: int | None = None,
        result_meta: dict | None = None,
    ) -> ScanConnectorRun:
        nxt = transition_run(run.status, new_status)
        run.status = nxt.value
        if skip_reason is not None:
            run.skip_reason = skip_reason
        if error is not None:
            run.error = error
        if cache_hit is not None:
            run.cache_hit = cache_hit
        if observation_count is not None:
            run.observation_count = observation_count
        if finding_count is not None:
            run.finding_count = finding_count
        if result_meta is not None:
            run.result_meta = result_meta
        now = datetime.now(timezone.utc)
        if nxt == ConnectorRunStatus.RUNNING and run.started_at is None:
            run.started_at = now
        if nxt.value in {
            ConnectorRunStatus.SUCCEEDED.value,
            ConnectorRunStatus.SKIPPED.value,
            ConnectorRunStatus.FAILED.value,
            ConnectorRunStatus.TIMED_OUT.value,
        }:
            run.finished_at = now
        await self.session.flush()
        return run

    async def recompute_progress(self, scan: Scan) -> None:
        runs = scan.connector_runs or []
        if not runs:
            scan.progress_pct = 100.0 if is_terminal_scan(scan.status) else 0.0
            await self.session.flush()
            return
        terminal = sum(
            1
            for r in runs
            if r.status
            in {
                ConnectorRunStatus.SUCCEEDED.value,
                ConnectorRunStatus.SKIPPED.value,
                ConnectorRunStatus.FAILED.value,
                ConnectorRunStatus.TIMED_OUT.value,
            }
        )
        scan.progress_pct = round(100.0 * terminal / len(runs), 1)
        scan.observation_count = sum(r.observation_count for r in runs)
        scan.finding_count = sum(r.finding_count for r in runs)
        await self.session.flush()

    async def try_finalize(self, scan: Scan) -> bool:
        """If all runs terminal, set derived scan status. Returns True if finalized."""
        runs = scan.connector_runs or []
        if not runs:
            await self.set_scan_status(scan, ScanStatus.COMPLETED, message="No connectors", progress_pct=100.0)
            return True
        statuses = [r.status for r in runs]
        derived = derive_scan_status_from_runs(statuses)
        if derived == ScanStatus.RUNNING:
            return False
        msg = {
            ScanStatus.COMPLETED: "Scan completed",
            ScanStatus.PARTIAL: "Scan completed with skips/failures",
            ScanStatus.FAILED: "Scan failed",
        }.get(derived, derived.value)
        await self.set_scan_status(scan, derived, message=msg, progress_pct=100.0)
        # Aggregate attributions into meta
        attributions: set[str] = set()
        for r in runs:
            meta = r.result_meta or {}
            if meta.get("attribution"):
                attributions.add(str(meta["attribution"]))
        scan.meta = {**(scan.meta or {}), "attributions": sorted(attributions)}
        await self.session.flush()
        return True

    async def list_stale_running(self, older_than: datetime) -> Sequence[Scan]:
        result = await self.session.execute(
            select(Scan)
            .options(selectinload(Scan.connector_runs))
            .where(
                Scan.status.in_([ScanStatus.PENDING.value, ScanStatus.RUNNING.value]),
                Scan.deadline_at < older_than,
            )
            .limit(100)
        )
        return result.scalars().all()

    async def list_runs_pending_or_running(self, limit: int = 50) -> Sequence[ScanConnectorRun]:
        result = await self.session.execute(
            select(ScanConnectorRun)
            .where(
                ScanConnectorRun.status.in_(
                    [ConnectorRunStatus.PENDING.value, ConnectorRunStatus.RUNNING.value]
                )
            )
            .order_by(ScanConnectorRun.created_at.asc())
            .limit(limit)
        )
        return result.scalars().all()
```

---

## 10. NEW: `backend/app/repositories/finding_repository.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.observation_finding import Observation, Finding, EvidenceBlob
from app.domain.findings_normalize import NormalizedFinding
from app.core.config import get_settings


class FindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def add_observation(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        scan_id: uuid.UUID | None,
        connector_run_id: uuid.UUID | None,
        obs: dict[str, Any],
    ) -> Observation:
        ttl_h = self.settings.evidence_raw_ttl_hours
        expires = datetime.now(timezone.utc) + timedelta(hours=ttl_h)
        row = Observation(
            user_id=user_id,
            identifier_id=identifier_id,
            scan_id=scan_id,
            connector_run_id=connector_run_id,
            kind=str(obs.get("kind") or "other"),
            source=str(obs.get("source") or "unknown"),
            title=str(obs.get("title") or "")[:512],
            summary=str(obs.get("summary") or "")[:4000],
            confidence=float(obs.get("confidence") or 0.5),
            layer=str(obs.get("layer") or "surface"),
            raw_ref=(str(obs["raw_ref"])[:512] if obs.get("raw_ref") else None),
            attributes=obs.get("attributes"),
            attribution=obs.get("attribution"),
            payload=obs,  # already redacted observation dict
            expires_at=expires,
            observed_at=None,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def upsert_finding(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        scan_id: uuid.UUID | None,
        nf: NormalizedFinding,
    ) -> tuple[Finding, bool]:
        """Returns (finding, created)."""
        result = await self.session.execute(
            select(Finding).where(
                Finding.user_id == user_id,
                Finding.identifier_id == identifier_id,
                Finding.source == nf.source,
                Finding.fingerprint == nf.fingerprint,
            )
        )
        existing = result.scalar_one_or_none()
        now = nf.observed_at or datetime.now(timezone.utc)
        if existing:
            existing.last_seen_at = now
            existing.last_seen_scan_id = scan_id
            existing.times_seen = (existing.times_seen or 1) + 1
            existing.confidence = max(existing.confidence, nf.confidence)
            # Merge attributes lightly
            if nf.attributes:
                existing.attributes = {**(existing.attributes or {}), **nf.attributes}
            if nf.summary and len(nf.summary) > len(existing.summary or ""):
                existing.summary = nf.summary
            existing.severity_hint = nf.severity_hint or existing.severity_hint
            await self.session.flush()
            return existing, False

        row = Finding(
            user_id=user_id,
            identifier_id=identifier_id,
            kind=nf.kind,
            source=nf.source,
            title=nf.title,
            summary=nf.summary,
            severity_hint=nf.severity_hint,
            confidence=nf.confidence,
            layer=nf.layer,
            track=nf.track,
            fingerprint=nf.fingerprint,
            raw_ref=nf.raw_ref,
            attributes=nf.attributes,
            attribution=nf.attribution,
            first_seen_scan_id=scan_id,
            last_seen_scan_id=scan_id,
            first_seen_at=now,
            last_seen_at=now,
            times_seen=1,
            status="open",
        )
        self.session.add(row)
        await self.session.flush()
        return row, True

    async def add_evidence(
        self,
        *,
        user_id: uuid.UUID,
        layer: str,
        body: dict[str, Any],
        identifier_id: uuid.UUID | None = None,
        scan_id: uuid.UUID | None = None,
        finding_id: uuid.UUID | None = None,
        observation_id: uuid.UUID | None = None,
        expires_at: datetime | None = None,
    ) -> EvidenceBlob:
        import json

        raw = json.dumps(body, default=str)
        row = EvidenceBlob(
            user_id=user_id,
            identifier_id=identifier_id,
            scan_id=scan_id,
            finding_id=finding_id,
            observation_id=observation_id,
            layer=layer,
            content_type="application/json",
            body=body,
            size_bytes=len(raw.encode("utf-8")),
            expires_at=expires_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_findings(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        source: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Finding]:
        q = select(Finding).where(Finding.user_id == user_id)
        if identifier_id:
            q = q.where(Finding.identifier_id == identifier_id)
        if source:
            q = q.where(Finding.source == source)
        q = q.order_by(Finding.last_seen_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(q)
        return result.scalars().all()

    async def get_finding(
        self, finding_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Finding]:
        result = await self.session.execute(
            select(Finding).where(Finding.id == finding_id, Finding.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def purge_expired_evidence(self, now: datetime | None = None) -> dict[str, int]:
        now = now or datetime.now(timezone.utc)
        # observations
        r1 = await self.session.execute(
            delete(Observation).where(Observation.expires_at < now)
        )
        # evidence raw/summary with expires_at
        r2 = await self.session.execute(
            delete(EvidenceBlob).where(
                EvidenceBlob.expires_at.is_not(None),
                EvidenceBlob.expires_at < now,
            )
        )
        await self.session.flush()
        return {
            "observations_deleted": r1.rowcount or 0,
            "evidence_blobs_deleted": r2.rowcount or 0,
        }
```

---

## 11. NEW: `backend/app/services/evidence_service.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.finding_repository import FindingRepository
from app.domain.findings_normalize import (
    NormalizedFinding,
    normalize_connector_result_observations,
)


class EvidenceService:
    """3-layer evidence + observation → finding pipeline."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FindingRepository(session)
        self.settings = get_settings()

    async def ingest_connector_observations(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        scan_id: uuid.UUID,
        connector_run_id: uuid.UUID,
        observations: list[dict[str, Any]],
        connector_id: str,
    ) -> tuple[int, int]:
        """
        Persist observations (layer raw), normalize → findings (durable),
        write summary evidence. Returns (obs_count, findings_created_or_updated).
        """
        if not observations:
            return 0, 0

        obs_count = 0
        finding_touches = 0
        normalized = normalize_connector_result_observations(observations)

        raw_ttl = datetime.now(timezone.utc) + timedelta(hours=self.settings.evidence_raw_ttl_hours)
        summary_ttl = datetime.now(timezone.utc) + timedelta(days=self.settings.evidence_summary_ttl_days)

        for o in observations:
            if not isinstance(o, dict):
                continue
            obs_row = await self.repo.add_observation(
                user_id=user_id,
                identifier_id=identifier_id,
                scan_id=scan_id,
                connector_run_id=connector_run_id,
                obs=o,
            )
            await self.repo.add_evidence(
                user_id=user_id,
                layer="raw",
                body={"observation": o, "connector_id": connector_id},
                identifier_id=identifier_id,
                scan_id=scan_id,
                observation_id=obs_row.id,
                expires_at=raw_ttl,
            )
            obs_count += 1

        for nf in normalized:
            finding, created = await self.repo.upsert_finding(
                user_id=user_id,
                identifier_id=identifier_id,
                scan_id=scan_id,
                nf=nf,
            )
            finding_touches += 1
            # summary layer
            await self.repo.add_evidence(
                user_id=user_id,
                layer="summary",
                body={
                    "finding_id": str(finding.id),
                    "kind": nf.kind,
                    "source": nf.source,
                    "title": nf.title,
                    "severity_hint": nf.severity_hint,
                    "confidence": nf.confidence,
                    "raw_ref": nf.raw_ref,
                    "attribution": nf.attribution,
                    "created": created,
                },
                identifier_id=identifier_id,
                scan_id=scan_id,
                finding_id=finding.id,
                expires_at=summary_ttl,
            )
            # durable layer (no TTL) — redacted metadata only
            await self.repo.add_evidence(
                user_id=user_id,
                layer="durable",
                body={
                    "finding_id": str(finding.id),
                    "fingerprint": nf.fingerprint,
                    "kind": nf.kind,
                    "source": nf.source,
                    "title": nf.title,
                    "severity_hint": nf.severity_hint,
                    "track": nf.track,
                    "layer": nf.layer,
                    "attributes_keys": list((nf.attributes or {}).keys()),
                    "attribution": nf.attribution,
                },
                identifier_id=identifier_id,
                scan_id=scan_id,
                finding_id=finding.id,
                expires_at=None,
            )

        return obs_count, finding_touches

    async def purge_expired(self) -> dict[str, int]:
        return await self.repo.purge_expired_evidence()
```

---

## 12. NEW: `backend/app/services/discovery_service.py`

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
from app.domain.scan_states import ScanStatus, ConnectorRunStatus
from app.repositories.scan_repository import ScanRepository
from app.repositories.finding_repository import FindingRepository
from app.services.identifier_service import IdentifierService
from app.services.consent_service import ConsentService
from app.services.audit_service import AuditService
from app.services.evidence_service import EvidenceService
from app.connectors.registry import build_connectors
from app.connectors.sdk.types import ConnectorContext
from app.connectors.sdk.rate_limiter import RateLimiter, RateLimitExceeded
from app.connectors.sdk.redis_clients import get_cache_redis
from app.models.connector_config import ConnectorConfig
from sqlalchemy import select

logger = get_logger(__name__)


class DiscoveryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.scans = ScanRepository(session)
        self.findings = FindingRepository(session)
        self.identifiers = IdentifierService(session)
        self.consent = ConsentService(session)
        self.audit = AuditService(session)
        self.evidence = EvidenceService(session)
        self.settings = get_settings()

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def create_scan(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        connector_ids: list[str] | None = None,
        layer_scope: str = "surface",
    ) -> Any:
        await self._set_rls(user_id)

        # G1 hard gate
        ident = await self.identifiers.require_verified(user_id, identifier_id)

        # Quotas
        active = await self.scans.count_active_for_user(user_id)
        if active >= self.settings.scan_max_concurrent_per_user:
            raise HTTPException(
                status_code=429,
                detail=f"Max concurrent scans ({self.settings.scan_max_concurrent_per_user}) reached",
            )
        today = await self.scans.count_today_for_user(user_id)
        if today >= self.settings.default_user_scan_quota_per_day:
            raise HTTPException(
                status_code=429,
                detail="Daily scan quota exceeded",
            )

        connectors = await build_connectors()
        db_flags = await self._load_db_flags()

        if connector_ids:
            selected = [c for c in connector_ids if c in connectors and c != "pwned_passwords"]
        else:
            selected = [
                cid
                for cid, c in connectors.items()
                if c.supports(ident.type)
                and cid != "pwned_passwords"
                and c.is_enabled_by_config()
                and (db_flags.get(cid) is not False)
            ]

        if not selected:
            raise HTTPException(status_code=400, detail="No connectors available for this identifier type")

        deadline = datetime.now(timezone.utc) + timedelta(
            minutes=self.settings.scan_default_deadline_minutes
        )
        scan = await self.scans.create(
            user_id=user_id,
            identifier_id=ident.id,
            connector_ids=selected,
            deadline_at=deadline,
            layer_scope=layer_scope,
        )
        for cid in selected:
            await self.scans.add_connector_run(scan=scan, connector_id=cid)

        await self.audit.log(
            "scan.created",
            user_id=user_id,
            resource_type="scan",
            resource_id=str(scan.id),
            details={"identifier_id": str(ident.id), "connectors": selected},
        )
        await self.session.commit()

        # Enqueue worker (import late to avoid circular)
        from app.tasks.discovery_tasks import execute_scan_task

        execute_scan_task.delay(str(scan.id))

        # Reload with runs
        return await self.scans.get(scan.id, user_id)

    async def get_scan(self, user_id: uuid.UUID, scan_id: uuid.UUID):
        await self._set_rls(user_id)
        scan = await self.scans.get(scan_id, user_id)
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        return scan

    async def list_scans(self, user_id: uuid.UUID, limit: int = 50, offset: int = 0):
        await self._set_rls(user_id)
        return await self.scans.list_for_user(user_id, limit=limit, offset=offset)

    async def cancel_scan(self, user_id: uuid.UUID, scan_id: uuid.UUID):
        await self._set_rls(user_id)
        scan = await self.scans.get(scan_id, user_id)
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        if scan.status in {ScanStatus.COMPLETED.value, ScanStatus.PARTIAL.value, ScanStatus.FAILED.value, ScanStatus.CANCELLED.value, ScanStatus.TIMED_OUT.value}:
            raise HTTPException(status_code=400, detail="Scan already terminal")
        await self.scans.set_scan_status(scan, ScanStatus.CANCELLED, message="Cancelled by user")
        for run in scan.connector_runs or []:
            if run.status in {ConnectorRunStatus.PENDING.value, ConnectorRunStatus.RUNNING.value}:
                await self.scans.set_run_status(
                    run, ConnectorRunStatus.SKIPPED, skip_reason="cancelled"
                )
        await self.audit.log("scan.cancelled", user_id=user_id, resource_type="scan", resource_id=str(scan_id))
        await self.session.commit()
        return scan

    async def list_findings(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        source: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        await self._set_rls(user_id)
        return await self.findings.list_findings(
            user_id, identifier_id=identifier_id, source=source, limit=limit, offset=offset
        )

    async def get_finding(self, user_id: uuid.UUID, finding_id: uuid.UUID):
        await self._set_rls(user_id)
        row = await self.findings.get_finding(finding_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Finding not found")
        return row

    async def _load_db_flags(self) -> dict[str, bool]:
        result = await self.session.execute(select(ConnectorConfig))
        return {r.connector_id: r.enabled for r in result.scalars().all()}

    # ---------- Worker entry ----------
    async def execute_scan(self, scan_id: uuid.UUID) -> None:
        """
        Run all pending connector runs for a scan.
        Called from Celery worker. Self-healing: reconcile will recover stuck scans.
        """
        scan = await self.scans.get_by_id_internal(scan_id)
        if not scan:
            logger.warning("scan_not_found", scan_id=str(scan_id))
            return

        await self._set_rls(scan.user_id)

        if scan.status == ScanStatus.CANCELLED.value:
            return
        if scan.status in {
            ScanStatus.COMPLETED.value,
            ScanStatus.PARTIAL.value,
            ScanStatus.FAILED.value,
            ScanStatus.TIMED_OUT.value,
        }:
            return

        # Deadline check
        now = datetime.now(timezone.utc)
        if scan.deadline_at < now:
            await self.scans.set_scan_status(scan, ScanStatus.TIMED_OUT, message="Deadline exceeded", error="deadline")
            for run in scan.connector_runs or []:
                if run.status in {ConnectorRunStatus.PENDING.value, ConnectorRunStatus.RUNNING.value}:
                    await self.scans.set_run_status(run, ConnectorRunStatus.TIMED_OUT, error="scan_deadline")
            await self.session.commit()
            return

        await self.scans.set_scan_status(scan, ScanStatus.RUNNING, message="Running connectors")
        await self.session.commit()

        # Reload
        scan = await self.scans.get_by_id_internal(scan_id)
        assert scan

        connectors = await build_connectors()
        db_flags = await self._load_db_flags()

        # Load identifier
        from app.repositories.identifier_repository import IdentifierRepository

        id_repo = IdentifierRepository(self.session)
        ident = await id_repo.get(scan.identifier_id, scan.user_id)
        if not ident or not ident.is_verified:
            await self.scans.set_scan_status(
                scan, ScanStatus.FAILED, message="Identifier not verified", error="G1_VIOLATION"
            )
            await self.session.commit()
            return

        for run in list(scan.connector_runs or []):
            # Re-check cancel / deadline between connectors
            await self.session.refresh(scan)
            if scan.status == ScanStatus.CANCELLED.value:
                break
            if scan.deadline_at < datetime.now(timezone.utc):
                await self.scans.set_scan_status(scan, ScanStatus.TIMED_OUT, message="Deadline exceeded")
                if run.status == ConnectorRunStatus.PENDING.value:
                    await self.scans.set_run_status(run, ConnectorRunStatus.TIMED_OUT)
                break

            if run.status != ConnectorRunStatus.PENDING.value:
                continue

            cid = run.connector_id
            connector = connectors.get(cid)
            if not connector:
                await self.scans.set_run_status(
                    run, ConnectorRunStatus.SKIPPED, skip_reason="unknown_connector"
                )
                await self.scans.recompute_progress(scan)
                await self.session.commit()
                continue

            env_on = connector.is_enabled_by_config()
            db_on = db_flags.get(cid)
            effective = env_on if db_on is None else (env_on and db_on)
            if not effective:
                await self.scans.set_run_status(run, ConnectorRunStatus.SKIPPED, skip_reason="disabled")
                await self.scans.recompute_progress(scan)
                await self.session.commit()
                continue

            purpose = f"discovery.{cid}"
            if connector.capability.sends_identifier:
                await self.consent.ensure_consent(
                    scan.user_id, purpose=purpose, auto_grant=True, scope=str(ident.id)
                )

            await self.scans.set_run_status(run, ConnectorRunStatus.RUNNING)
            await self.scans.recompute_progress(scan)
            await self.session.commit()

            ctx = ConnectorContext(
                user_id=scan.user_id,
                identifier_id=ident.id,
                identifier_type=ident.type,
                identifier_canonical=ident.value_canonical,
                consent_purpose=purpose,
            )

            try:
                result = await connector.run(ctx, enabled_override=True)
            except Exception as e:
                logger.exception("connector_run_exception", connector=cid, scan_id=str(scan_id))
                await self.scans.set_run_status(
                    run, ConnectorRunStatus.FAILED, error=str(e)[:2000]
                )
                await self.scans.recompute_progress(scan)
                await self.session.commit()
                continue

            # Ledger
            if connector.capability.sends_identifier and not result.skipped:
                host = {
                    "xposedornot": "api.xposedornot.com",
                    "crtsh": "crt.sh",
                    "rdap": "rdap.org",
                    "github": "api.github.com",
                    "username_presence": "multi",
                    "serp_ddg": "html.duckduckgo.com",
                    "gravatar": "www.gravatar.com",
                }.get(cid, cid)
                await self.consent.record_egress(
                    purpose=purpose,
                    destination_host=host,
                    method="GET",
                    status_code=200 if result.success else None,
                    success=result.success and not result.skipped,
                    user_id=scan.user_id,
                    identifier_id=ident.id,
                    summary={
                        "connector": cid,
                        "scan_id": str(scan.id),
                        "cache_hit": result.cache_hit,
                        "skipped": result.skipped,
                        "observation_count": len(result.observations),
                    },
                )

            if result.skipped:
                await self.scans.set_run_status(
                    run,
                    ConnectorRunStatus.SKIPPED,
                    skip_reason=result.skip_reason,
                    error=result.error,
                    cache_hit=result.cache_hit,
                    result_meta=result.to_dict().get("meta") or {"skip_reason": result.skip_reason},
                )
            elif not result.success:
                await self.scans.set_run_status(
                    run,
                    ConnectorRunStatus.FAILED,
                    error=result.error or "connector_failed",
                    cache_hit=result.cache_hit,
                    result_meta=result.meta,
                )
            else:
                obs_dicts = [o.to_dict() for o in result.observations]
                obs_n, find_n = await self.evidence.ingest_connector_observations(
                    user_id=scan.user_id,
                    identifier_id=ident.id,
                    scan_id=scan.id,
                    connector_run_id=run.id,
                    observations=obs_dicts,
                    connector_id=cid,
                )
                meta = dict(result.meta or {})
                if result.observations:
                    # carry attribution
                    for o in result.observations:
                        if o.attribution:
                            meta.setdefault("attribution", o.attribution)
                            break
                if not meta.get("attribution") and connector.capability.attribution:
                    meta["attribution"] = connector.capability.attribution

                await self.scans.set_run_status(
                    run,
                    ConnectorRunStatus.SUCCEEDED,
                    cache_hit=result.cache_hit,
                    observation_count=obs_n,
                    finding_count=find_n,
                    result_meta=meta,
                )

            await self.scans.recompute_progress(scan)
            await self.session.commit()

        # Finalize
        scan = await self.scans.get_by_id_internal(scan_id)
        if scan and not (
            scan.status
            in {
                ScanStatus.CANCELLED.value,
                ScanStatus.TIMED_OUT.value,
            }
        ):
            await self.scans.try_finalize(scan)
            await self.audit.log(
                "scan.finished",
                user_id=scan.user_id,
                resource_type="scan",
                resource_id=str(scan.id),
                details={
                    "status": scan.status,
                    "observation_count": scan.observation_count,
                    "finding_count": scan.finding_count,
                },
            )
            await self.session.commit()

    async def reconcile(self) -> dict[str, int]:
        """
        Self-healing sweep:
        - Timeout past-deadline scans
        - Re-enqueue pending scans with no progress
        - Purge expired evidence
        """
        now = datetime.now(timezone.utc)
        timed_out = 0
        requeued = 0

        stale = await self.scans.list_stale_running(now)
        for scan in stale:
            await self._set_rls(scan.user_id)
            if scan.deadline_at < now:
                await self.scans.set_scan_status(
                    scan, ScanStatus.TIMED_OUT, message="Reconcile: deadline exceeded", error="reconcile_timeout"
                )
                for run in scan.connector_runs or []:
                    if run.status in {
                        ConnectorRunStatus.PENDING.value,
                        ConnectorRunStatus.RUNNING.value,
                    }:
                        await self.scans.set_run_status(
                            run, ConnectorRunStatus.TIMED_OUT, error="reconcile_timeout"
                        )
                timed_out += 1
            elif scan.status == ScanStatus.PENDING.value:
                from app.tasks.discovery_tasks import execute_scan_task

                execute_scan_task.delay(str(scan.id))
                requeued += 1

        purged = await self.evidence.purge_expired()
        await self.session.commit()
        logger.info("scan_reconcile", timed_out=timed_out, requeued=requeued, **purged)
        return {"timed_out": timed_out, "requeued": requeued, **purged}
```

---

## 13. NEW: `backend/app/tasks/discovery_tasks.py`

```python
"""Celery tasks for discovery — pass IDs only, never ORM objects."""

from __future__ import annotations

import asyncio
import uuid

from app.worker import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


def _run_async(coro):
    """Run async service code inside sync Celery worker."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # nested — create new loop in thread (rare)
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _execute_scan_async(scan_id: str) -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.discovery_service import DiscoveryService

    async with AsyncSessionLocal() as session:
        svc = DiscoveryService(session)
        try:
            await svc.execute_scan(uuid.UUID(scan_id))
        except Exception:
            logger.exception("execute_scan_failed", scan_id=scan_id)
            await session.rollback()
            raise
        else:
            # commits happen inside service; ensure clean
            try:
                await session.commit()
            except Exception:
                pass


async def _reconcile_async() -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.discovery_service import DiscoveryService

    async with AsyncSessionLocal() as session:
        svc = DiscoveryService(session)
        return await svc.reconcile()


@celery_app.task(name="app.tasks.discovery_tasks.execute_scan_task", bind=True, max_retries=2)
def execute_scan_task(self, scan_id: str) -> str:
    logger.info("execute_scan_task_start", scan_id=scan_id)
    _run_async(_execute_scan_async(scan_id))
    return f"done:{scan_id}"


@celery_app.task(name="app.tasks.discovery_tasks.reconcile_scans_task")
def reconcile_scans_task() -> dict:
    logger.info("reconcile_scans_task_start")
    result = _run_async(_reconcile_async())
    return result or {}
```

---

## 14. UPDATE: `backend/app/worker.py`

```python
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "digizafe",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks",
        "app.tasks.discovery_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "reconcile-scans": {
            "task": "app.tasks.discovery_tasks.reconcile_scans_task",
            "schedule": float(settings.scan_reconcile_interval_seconds),
        },
    },
)


@celery_app.task(name="app.tasks.health_ping")
def health_ping() -> str:
    return "pong"
```

---

## 15. UPDATE: `backend/app/tasks/__init__.py`

```python
from app.worker import health_ping  # noqa: F401
from app.tasks import discovery_tasks  # noqa: F401
```

---

## 16. NEW: `backend/app/api/v1/scans.py`

```python
import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.core.config import get_settings
from app.domain.scan_states import is_terminal_scan
from app.schemas.scan import (
    ScanCreate,
    ScanPublic,
    ScanListItem,
    FindingPublic,
    Message,
)
from app.services.discovery_service import DiscoveryService

router = APIRouter(tags=["scans"])


def _svc(db: AsyncSession = Depends(get_db)) -> DiscoveryService:
    return DiscoveryService(db)


@router.post("/scans", response_model=ScanPublic, status_code=status.HTTP_201_CREATED)
async def create_scan(
    body: ScanCreate,
    current_user: CurrentUser,
    svc: DiscoveryService = Depends(_svc),
):
    """
    Start a discovery scan for a **verified** identifier (G1).
    Work runs in Celery worker — not in the request path.
    """
    scan = await svc.create_scan(
        current_user.id,
        body.identifier_id,
        connector_ids=body.connector_ids,
        layer_scope=body.layer_scope,
    )
    return ScanPublic.model_validate(scan)


@router.get("/scans", response_model=list[ScanListItem])
async def list_scans(
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: DiscoveryService = Depends(_svc),
):
    rows = await svc.list_scans(current_user.id, limit=limit, offset=offset)
    return [ScanListItem.model_validate(r) for r in rows]


@router.get("/scans/{scan_id}", response_model=ScanPublic)
async def get_scan(
    scan_id: UUID,
    current_user: CurrentUser,
    svc: DiscoveryService = Depends(_svc),
):
    scan = await svc.get_scan(current_user.id, scan_id)
    return ScanPublic.model_validate(scan)


@router.post("/scans/{scan_id}/cancel", response_model=ScanPublic)
async def cancel_scan(
    scan_id: UUID,
    current_user: CurrentUser,
    svc: DiscoveryService = Depends(_svc),
):
    scan = await svc.cancel_scan(current_user.id, scan_id)
    return ScanPublic.model_validate(scan)


@router.get("/scans/{scan_id}/events")
async def scan_events_sse(
    scan_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Server-Sent Events stream of scan progress.
    Polls DB (Postgres is source of truth). Compatible with EventSource.
    """
    settings = get_settings()
    svc = DiscoveryService(db)
    # ownership check
    await svc.get_scan(current_user.id, scan_id)

    async def event_generator() -> AsyncIterator[str]:
        started = datetime.now(timezone.utc)
        last_payload = None
        last_heartbeat = datetime.now(timezone.utc)
        event_id = 0

        while True:
            now = datetime.now(timezone.utc)
            if (now - started).total_seconds() > settings.sse_max_duration_seconds:
                event_id += 1
                yield f"id: {event_id}\nevent: timeout\ndata: {json.dumps({'message': 'SSE max duration'})}\n\n"
                break

            # Fresh session read — reuse service with same session (refresh)
            try:
                scan = await svc.get_scan(current_user.id, scan_id)
            except Exception as e:
                event_id += 1
                yield f"id: {event_id}\nevent: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                break

            payload = {
                "scan_id": str(scan.id),
                "status": scan.status,
                "progress_pct": scan.progress_pct,
                "message": scan.message,
                "observation_count": scan.observation_count,
                "finding_count": scan.finding_count,
                "error": scan.error,
                "connector_runs": [
                    {
                        "connector_id": r.connector_id,
                        "status": r.status,
                        "skip_reason": r.skip_reason,
                        "observation_count": r.observation_count,
                        "finding_count": r.finding_count,
                        "cache_hit": r.cache_hit,
                    }
                    for r in (scan.connector_runs or [])
                ],
                "meta": scan.meta,
                "finished_at": scan.finished_at.isoformat() if scan.finished_at else None,
            }
            serialized = json.dumps(payload, default=str)

            if serialized != last_payload:
                last_payload = serialized
                event_id += 1
                yield f"id: {event_id}\nevent: scan\ndata: {serialized}\n\n"

                if is_terminal_scan(scan.status):
                    event_id += 1
                    yield f"id: {event_id}\nevent: done\ndata: {serialized}\n\n"
                    break

            # heartbeat
            if (now - last_heartbeat).total_seconds() >= settings.sse_heartbeat_seconds:
                last_heartbeat = now
                yield f": ping {now.isoformat()}\n\n"

            await asyncio.sleep(settings.sse_poll_interval_seconds)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/findings", response_model=list[FindingPublic])
async def list_findings(
    current_user: CurrentUser,
    identifier_id: Optional[UUID] = None,
    source: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: DiscoveryService = Depends(_svc),
):
    rows = await svc.list_findings(
        current_user.id,
        identifier_id=identifier_id,
        source=source,
        limit=limit,
        offset=offset,
    )
    return [FindingPublic.model_validate(r) for r in rows]


@router.get("/findings/{finding_id}", response_model=FindingPublic)
async def get_finding(
    finding_id: UUID,
    current_user: CurrentUser,
    svc: DiscoveryService = Depends(_svc),
):
    row = await svc.get_finding(current_user.id, finding_id)
    return FindingPublic.model_validate(row)
```

---

## 17. UPDATE: `backend/app/main.py`

```python
# ... existing imports ...
from app.api.v1 import health, auth, identifiers, connectors, scans  # add scans

# Routers
app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(identifiers.router, prefix=settings.api_v1_prefix)
app.include_router(connectors.router, prefix=settings.api_v1_prefix)
app.include_router(scans.router, prefix=settings.api_v1_prefix)

@app.get("/")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.4.0",
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
        "message": "DigiZafe Sprint 4 Discovery & Evidence — ready",
    }
```

Ensure `backend/app/api/v1/__init__.py` exists.

---

## 18. UPDATE: `backend/app/alembic/env.py` model imports

```python
from app.models.user import User, RefreshToken  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.identifier import Identifier, VerificationChallenge  # noqa: F401
from app.models.consent_egress import ConsentRecord, EgressLedger  # noqa: F401
from app.models.connector_config import ConnectorConfig  # noqa: F401
from app.models.scan import Scan, ScanConnectorRun  # noqa: F401
from app.models.observation_finding import Observation, Finding, EvidenceBlob  # noqa: F401
```

---

## 19. Alembic migration: `sprint4_discovery_evidence`

```bash
docker compose exec api alembic revision -m "sprint4_discovery_evidence"
```

Replace contents with:

```python
"""sprint4_discovery_evidence

Revision ID: sprint4_disc_001
Revises: sprint3_conn_001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "sprint4_disc_001"
down_revision: Union[str, None] = "sprint3_conn_001"  # ← set to your Sprint 3 rev
branch_labels = None
depends_on = None


def upgrade() -> None:
    # scans
    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("layer_scope", sa.String(32), nullable=False, server_default="surface"),
        sa.Column("connector_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("progress_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("message", sa.String(512), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("observation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finding_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_scans_user_id", "scans", ["user_id"])
    op.create_index("ix_scans_identifier_id", "scans", ["identifier_id"])
    op.create_index("ix_scans_status", "scans", ["status"])

    # scan_connector_runs
    op.create_table(
        "scan_connector_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("skip_reason", sa.String(64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("observation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finding_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("scan_id", "connector_id", name="uq_scan_connector_run"),
    )
    op.create_index("ix_scan_connector_runs_scan_id", "scan_connector_runs", ["scan_id"])
    op.create_index("ix_scan_connector_runs_user_id", "scan_connector_runs", ["user_id"])
    op.create_index("ix_scan_connector_runs_status", "scan_connector_runs", ["status"])
    op.create_index("ix_scan_connector_runs_connector_id", "scan_connector_runs", ["connector_id"])

    # observations
    op.create_table(
        "observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("connector_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scan_connector_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("layer", sa.String(32), nullable=False, server_default="surface"),
        sa.Column("raw_ref", sa.String(512), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attribution", sa.String(512), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_observations_user_id", "observations", ["user_id"])
    op.create_index("ix_observations_identifier_id", "observations", ["identifier_id"])
    op.create_index("ix_observations_scan_id", "observations", ["scan_id"])
    op.create_index("ix_observations_source", "observations", ["source"])
    op.create_index("ix_observations_expires_at", "observations", ["expires_at"])
    op.create_index("ix_observations_kind", "observations", ["kind"])

    # findings
    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity_hint", sa.String(32), nullable=False, server_default="info"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("layer", sa.String(32), nullable=False, server_default="surface"),
        sa.Column("track", sa.String(32), nullable=False, server_default="confirmed"),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("raw_ref", sa.String(512), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attribution", sa.String(512), nullable=True),
        sa.Column("first_seen_scan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_seen_scan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("times_seen", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "identifier_id", "source", "fingerprint", name="uq_findings_user_ident_source_fp"),
    )
    op.create_index("ix_findings_user_id", "findings", ["user_id"])
    op.create_index("ix_findings_identifier_id", "findings", ["identifier_id"])
    op.create_index("ix_findings_kind", "findings", ["kind"])
    op.create_index("ix_findings_source", "findings", ["source"])
    op.create_index("ix_findings_severity_hint", "findings", ["severity_hint"])
    op.create_index("ix_findings_layer", "findings", ["layer"])
    op.create_index("ix_findings_status", "findings", ["status"])
    op.create_index("ix_findings_raw_ref", "findings", ["raw_ref"])

    # evidence_blobs
    op.create_table(
        "evidence_blobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=True),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("layer", sa.String(16), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False, server_default="application/json"),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_evidence_blobs_user_id", "evidence_blobs", ["user_id"])
    op.create_index("ix_evidence_blobs_identifier_id", "evidence_blobs", ["identifier_id"])
    op.create_index("ix_evidence_blobs_scan_id", "evidence_blobs", ["scan_id"])
    op.create_index("ix_evidence_blobs_finding_id", "evidence_blobs", ["finding_id"])
    op.create_index("ix_evidence_blobs_layer", "evidence_blobs", ["layer"])
    op.create_index("ix_evidence_blobs_expires_at", "evidence_blobs", ["expires_at"])

    # ---------- RLS ----------
    for table in ("scans", "scan_connector_runs", "observations", "findings", "evidence_blobs"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY scans_self ON scans
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY scan_runs_self ON scan_connector_runs
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY observations_self ON observations
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY findings_self ON findings
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY evidence_self ON evidence_blobs
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ---------- ACTIVATE verified-only G1 triggers (function from Sprint 2) ----------
    # Ensure function exists (idempotent recreate)
    op.execute("""
        CREATE OR REPLACE FUNCTION digizafe_enforce_verified_identifier()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_ok boolean;
        BEGIN
            SELECT is_verified INTO v_ok
            FROM identifiers
            WHERE id = NEW.identifier_id;

            IF v_ok IS DISTINCT FROM TRUE THEN
                RAISE EXCEPTION 'G1_VIOLATION: only verified identifiers allowed (identifier_id=%)',
                    NEW.identifier_id
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_scans_verified_only ON scans;
        CREATE TRIGGER trg_scans_verified_only
            BEFORE INSERT OR UPDATE OF identifier_id ON scans
            FOR EACH ROW EXECUTE FUNCTION digizafe_enforce_verified_identifier();
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_observations_verified_only ON observations;
        CREATE TRIGGER trg_observations_verified_only
            BEFORE INSERT OR UPDATE OF identifier_id ON observations
            FOR EACH ROW EXECUTE FUNCTION digizafe_enforce_verified_identifier();
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_findings_verified_only ON findings;
        CREATE TRIGGER trg_findings_verified_only
            BEFORE INSERT OR UPDATE OF identifier_id ON findings
            FOR EACH ROW EXECUTE FUNCTION digizafe_enforce_verified_identifier();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_findings_verified_only ON findings")
    op.execute("DROP TRIGGER IF EXISTS trg_observations_verified_only ON observations")
    op.execute("DROP TRIGGER IF EXISTS trg_scans_verified_only ON scans")
    # keep function — may be shared

    for pol, tbl in [
        ("evidence_self", "evidence_blobs"),
        ("findings_self", "findings"),
        ("observations_self", "observations"),
        ("scan_runs_self", "scan_connector_runs"),
        ("scans_self", "scans"),
    ]:
        op.execute(f"DROP POLICY IF EXISTS {pol} ON {tbl}")

    for table in ("evidence_blobs", "findings", "observations", "scan_connector_runs", "scans"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("evidence_blobs")
    op.drop_table("findings")
    op.drop_table("observations")
    op.drop_table("scan_connector_runs")
    op.drop_table("scans")
```

---

## 20. Unit tests

### `backend/tests/unit/test_scan_states.py`

```python
import pytest
from app.domain.scan_states import (
    ScanStatus,
    ConnectorRunStatus,
    transition_scan,
    transition_run,
    InvalidTransition,
    is_terminal_scan,
    derive_scan_status_from_runs,
)


def test_scan_happy_path():
    assert transition_scan(ScanStatus.PENDING, ScanStatus.RUNNING) == ScanStatus.RUNNING
    assert transition_scan(ScanStatus.RUNNING, ScanStatus.COMPLETED) == ScanStatus.COMPLETED
    assert is_terminal_scan(ScanStatus.COMPLETED)


def test_invalid_scan_transition():
    with pytest.raises(InvalidTransition):
        transition_scan(ScanStatus.COMPLETED, ScanStatus.RUNNING)


def test_derive_partial():
    s = derive_scan_status_from_runs(
        [ConnectorRunStatus.SUCCEEDED, ConnectorRunStatus.SKIPPED, ConnectorRunStatus.FAILED]
    )
    assert s == ScanStatus.PARTIAL


def test_derive_all_success():
    s = derive_scan_status_from_runs([ConnectorRunStatus.SUCCEEDED, ConnectorRunStatus.SUCCEEDED])
    assert s == ScanStatus.COMPLETED


def test_derive_still_running():
    s = derive_scan_status_from_runs([ConnectorRunStatus.SUCCEEDED, ConnectorRunStatus.PENDING])
    assert s == ScanStatus.RUNNING
```

### `backend/tests/unit/test_findings_normalize.py`

```python
from app.domain.findings_normalize import normalize_observation, normalize_connector_result_observations


def test_xposedornot_breach_normalize():
    obs = {
        "kind": "breach",
        "source": "xposedornot",
        "title": "Breach: Adobe",
        "summary": "Email reported in breach dataset 'Adobe' via XposedOrNot free check.",
        "confidence": 0.85,
        "layer": "surface",
        "raw_ref": "Adobe",
        "attributes": {
            "breach_name": "Adobe",
            "provider": "xposedornot",
            "xposed_data": "Email addresses;Passwords",
            "password_risk": "hardtocrack",
        },
        "attribution": "Data: XposedOrNot",
    }
    nf = normalize_observation(obs)
    assert nf.source == "xposedornot"
    assert nf.kind == "breach"
    assert nf.raw_ref == "Adobe"
    assert nf.fingerprint
    assert nf.severity_hint in {"low", "medium", "high", "critical"}
    assert nf.attribution


def test_dedupe_fingerprints():
    obs = [
        {
            "kind": "breach",
            "source": "xposedornot",
            "title": "Breach: Adobe",
            "summary": "a",
            "confidence": 0.9,
            "raw_ref": "Adobe",
            "attributes": {"breach_name": "Adobe"},
        },
        {
            "kind": "breach",
            "source": "xposedornot",
            "title": "Breach: Adobe",
            "summary": "b",
            "confidence": 0.9,
            "raw_ref": "Adobe",
            "attributes": {"breach_name": "Adobe"},
        },
    ]
    out = normalize_connector_result_observations(obs)
    assert len(out) == 1
```

---

## 21. Docs

### `docs/runbooks/discovery-evidence.md`

```markdown
# Discovery & Evidence (Sprint 4)

## Flow
1. Verify identifier (Sprint 2) — **required** (G1)
2. `POST /api/v1/scans` `{ "identifier_id": "..." }`
3. Worker runs connectors (XposedOrNot primary for email)
4. Observations (TTL) → Findings (durable, deduped)
5. SSE: `GET /api/v1/scans/{id}/events`
6. List findings: `GET /api/v1/findings?identifier_id=`

## State machine
- Scan: pending → running → completed | partial | failed | cancelled | timed_out
- Per-connector run: pending → running → succeeded | skipped | failed | timed_out
- Reconcile beat task self-heals stale/deadline scans

## 3-layer evidence
| Layer | Store | TTL |
|-------|-------|-----|
| raw | observations + evidence_blobs.layer=raw | EVIDENCE_RAW_TTL_HOURS (24h) |
| summary | evidence_blobs.layer=summary | EVIDENCE_SUMMARY_TTL_DAYS (30d) |
| durable | findings + evidence_blobs.layer=durable | no auto-TTL |

## G1
- Service: `require_verified`
- DB triggers on scans / observations / findings
- Unverified insert → `G1_VIOLATION`

## XposedOrNot
- Findings source=`xposedornot`, kind=`breach`
- Attribution in finding.attribution + scan.meta.attributions
- Consent + egress_ledger on every email send
```

### UPDATE `docs/free-sources.md` (append)

```markdown
## Sprint 4 persistence
XposedOrNot observations normalize to `findings` with fingerprint dedupe.
Negative results are not findings; they are cached at connector layer only.
```

---

# PART C — How to finish Sprint 4

```bash
# 1. Merge .env keys
# 2. Rebuild & migrate
docker compose build api worker beat
docker compose up -d
docker compose exec api alembic upgrade head

# 3. Ensure worker + beat running
docker compose ps
docker compose logs -f worker beat

# 4. Smoke flow
# Login → verified email ID
export ACCESS=...
export ID=...   # verified email identifier

# Start scan
curl -s -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d "{\"identifier_id\":\"$ID\"}" | jq .
# → note scan_id

# Poll
curl -s http://localhost:8000/api/v1/scans/$SCAN_ID \
  -H "Authorization: Bearer $ACCESS" | jq .

# SSE (Ctrl+C when done)
curl -N http://localhost:8000/api/v1/scans/$SCAN_ID/events \
  -H "Authorization: Bearer $ACCESS"

# Findings (after complete)
curl -s "http://localhost:8000/api/v1/findings?identifier_id=$ID" \
  -H "Authorization: Bearer $ACCESS" | jq .

# G1 check: create unverified identifier, attempt scan → 403 / DB trigger

# Unit tests
docker compose exec api pytest backend/tests/unit/test_scan_states.py backend/tests/unit/test_findings_normalize.py -v

# 5. Commit
git add .
git commit -m "feat(sprint-4): discovery state machine, 3-layer evidence, SSE, G1 triggers, XposedOrNot→findings"
```

---

# Sprint 4 Definition of Done Checklist

- [ ] MASTER_ENGINEERING_CONTEXT.md respected  
- [ ] Postgres scan + scan_connector_runs with explicit status transitions  
- [ ] Celery `execute_scan_task` runs connectors **outside** request path  
- [ ] Beat reconcile task times out deadline scans + requeues stuck pending + purges evidence  
- [ ] G1: `require_verified` + **DB triggers** on scans/observations/findings active  
- [ ] Observations short-TTL; findings durable with fingerprint dedupe  
- [ ] 3-layer evidence_blobs: raw / summary / durable  
- [ ] XposedOrNot observations → normalized findings (source=xposedornot, attribution)  
- [ ] Skips/rate-limits honest on connector_runs (never silent)  
- [ ] Consent + egress_ledger on sends_identifier connectors during scan  
- [ ] SSE `/scans/{id}/events` streams progress until terminal  
- [ ] Per-user concurrent + daily scan quotas  
- [ ] RLS policies on all new tables  
- [ ] No paid keys required; free path complete for surface discovery  
- [ ] Unit tests for state machine + normalize green  
- [ ] API: create/list/get/cancel scan, list/get findings  

Once checked → **Sprint 4 complete**.  
Next: **Sprint 5 — Identity Graph & PDSS Scoring** (deciban linkage, full PDSS vector + surprisal two-track, explanation records incl. XposedOrNot drivers, history, what-if).

---

## Endpoint quick reference

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /api/v1/scans | Bearer | Start scan (verified identifier only) |
| GET | /api/v1/scans | Bearer | List scans |
| GET | /api/v1/scans/{id} | Bearer | Get scan + connector runs |
| POST | /api/v1/scans/{id}/cancel | Bearer | Cancel |
| GET | /api/v1/scans/{id}/events | Bearer | SSE progress |
| GET | /api/v1/findings | Bearer | List findings (`?identifier_id=&source=`) |
| GET | /api/v1/findings/{id} | Bearer | Get finding |

---

## File checklist (create/update)

| Action | Path |
|--------|------|
| UPDATE | `.env.example` |
| UPDATE | `backend/app/core/config.py` |
| NEW | `backend/app/domain/scan_states.py` |
| NEW | `backend/app/domain/findings_normalize.py` |
| NEW | `backend/app/models/scan.py` |
| NEW | `backend/app/models/observation_finding.py` |
| UPDATE | `backend/app/models/__init__.py` |
| NEW | `backend/app/schemas/scan.py` |
| NEW | `backend/app/repositories/scan_repository.py` |
| NEW | `backend/app/repositories/finding_repository.py` |
| NEW | `backend/app/services/evidence_service.py` |
| NEW | `backend/app/services/discovery_service.py` |
| NEW | `backend/app/tasks/discovery_tasks.py` |
| UPDATE | `backend/app/tasks/__init__.py` |
| UPDATE | `backend/app/worker.py` |
| NEW | `backend/app/api/v1/scans.py` |
| UPDATE | `backend/app/main.py` |
| UPDATE | `backend/app/alembic/env.py` |
| NEW | `backend/app/alembic/versions/*_sprint4_discovery_evidence.py` |
| NEW | `backend/tests/unit/test_scan_states.py` |
| NEW | `backend/tests/unit/test_findings_normalize.py` |
| NEW | `docs/runbooks/discovery-evidence.md` |

---

**You are ready for Sprint 4.**  
Apply files in order, set `down_revision` to your Sprint 3 revision id, migrate, start a scan on a verified email, watch SSE + findings (XposedOrNot attribution), then commit.

If you hit migration/RLS/async-Celery/import issues, paste the error for a surgical fix.  
When Sprint 4 is green, ask for **Sprint 5** the same way.