# DigiZafe — Sprint 7 Remediation Engine (AIDR core)
**Complete Implementation Guide from Sprint 6 Baseline + All File Contents**

**Document version:** 1.0  
**Based on:** MASTER_ENGINEERING_CONTEXT.md v2.1  
**Depends on:** Sprint 0–6 green (Auth, Identifiers, Connectors, Discovery, Findings, PDSS, Recommendations & Alerts)  
**Goal:** From completed Sprint 6 → **AIDR-inspired remediation engine**: playbooks, **Playwright runners**, **`broker_optout_state`** (state.json lineage), **verify loop**, **free CAPTCHA / manual-first path** (CapSolver optional flag only), **freeze / know / complaints generators**, **update-brokers**, and **closed-loop re-score** fed by free XposedOrNot path.

**Effort estimate:** ~14 days (solo)  
**Critical path next:** Sprint 8 Privacy, Rights, Explain backend  

> **Load MASTER_ENGINEERING_CONTEXT.md first in every session.**  
> You implement; you do not re-decide architecture.  
> **Green brokers only for semi-automated path.** Free CAPTCHA path is default. Never require CapSolver or paid APIs.  
> **Attribute AIDR:** https://github.com/stephenlthorn/auto-identity-remove — re-implement under DigiZafe layering (DTO, RLS, consent, crypto-shred rules).  
> Playwright **never** runs in the API request path — only in `remediation_worker` / Celery tasks.

---

# PART A — Pre-Sprint 7 (run once from DigiZafe root)

```bash
# 1. Confirm Sprint 6 is green
docker compose ps
curl -s http://localhost:8000/api/v1/health | jq .
# Need: verified ID → scan → findings → PDSS → recommendations plan (incl. broker_optout_green)

# 2. Package dirs
mkdir -p backend/app/remediation/{runners,playbooks,verify,generators}
mkdir -p backend/app/{services,repositories,models,schemas,tasks,domain}
mkdir -p shared/config/broker_registry
mkdir -p shared/config/playbook
mkdir -p docs/{aidr-mapping,runbooks}
mkdir -p backend/tests/{unit,integration}
mkdir -p infrastructure/docker

touch backend/app/remediation/__init__.py
touch backend/app/remediation/runners/__init__.py
touch backend/app/remediation/playbooks/__init__.py
touch backend/app/remediation/verify/__init__.py
touch backend/app/remediation/generators/__init__.py

# 3. Dependencies — see PART B pyproject.toml adds
# Then rebuild with Playwright-capable image (or install in Dockerfile)
docker compose build api worker beat remediation-worker
echo "✅ Pre-Sprint 7 ready. Apply file contents below."
```

**Add to `pyproject.toml` → `[project] dependencies`:**

```toml
    "playwright>=1.47.0",
```

**Dockerfile note:** After `pip install`, run as root before USER digizafe (or use a remediation image):

```dockerfile
# In infrastructure/docker/Dockerfile (or Dockerfile.remediation):
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*
# After pip install -e ".[dev]":
RUN playwright install chromium && playwright install-deps chromium || true
```

Optional: separate `remediation-worker` service in docker-compose (see PART B).

---

# PART B — Sprint 7 File Contents

---

## 1. UPDATE: Root `.env.example` (append)

```bash
# === Sprint 7: Remediation Engine (AIDR core) ===
FEATURE_REMEDIATION=true
FEATURE_CAPSOLVER=false
CAPSOLVER_API_KEY=

# Broker opt-out state (AIDR state.json lineage)
BROKER_OPTOUT_RECHECK_DAYS=90
BROKER_EMAIL_CONFIRM_RETRY_DAYS=14
BROKER_MAX_CONCURRENT_JOBS_PER_USER=1
BROKER_JOB_DEADLINE_MINUTES=120
BROKER_RUNNER_TIMEOUT_SECONDS=90
BROKER_REGISTRY_PATH=./shared/config/broker_registry/brokers_green.json

# Playwright
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_SLOW_MO_MS=0
# Isolation: never share browser context across users
PLAYWRIGHT_USER_DATA_DIR=/tmp/digizafe-pw

# CAPTCHA free path
CAPTCHA_MODE=manual
# manual | open_in_browser | capsolver (capsolver only if FEATURE_CAPSOLVER=true)
CAPTCHA_QUEUE_TTL_HOURS=48

# Closed loop
REMEDIATION_AUTO_RESCORE=true
REMEDIATION_AUTO_RESCAN=false
# verify after opt-out before marking verified_removed
REMEDIATION_VERIFY_AFTER_SUBMIT=true

# update-brokers (free public registries — best-effort)
FEATURE_UPDATE_BROKERS=true
UPDATE_BROKERS_INTERVAL_HOURS=168
```

Merge into real `.env`. Keep `FEATURE_CAPSOLVER=false` for free path.

---

## 2. UPDATE: `backend/app/core/config.py`

Add to `Settings` (keep all prior fields):

```python
    # === Sprint 7: Remediation ===
    feature_remediation: bool = True
    # feature_capsolver already exists from Sprint 0 — keep default False
    # capsolver_api_key already exists

    broker_optout_recheck_days: int = 90
    broker_email_confirm_retry_days: int = 14
    broker_max_concurrent_jobs_per_user: int = 1
    broker_job_deadline_minutes: int = 120
    broker_runner_timeout_seconds: int = 90
    broker_registry_path: str = "./shared/config/broker_registry/brokers_green.json"

    playwright_headless: bool = True
    playwright_slow_mo_ms: int = 0
    playwright_user_data_dir: str = "/tmp/digizafe-pw"

    captcha_mode: str = "manual"  # manual | open_in_browser | capsolver
    captcha_queue_ttl_hours: int = 48

    remediation_auto_rescore: bool = True
    remediation_auto_rescan: bool = False
    remediation_verify_after_submit: bool = True

    feature_update_brokers: bool = True
    update_brokers_interval_hours: int = 168
```

---

## 3. NEW: `shared/config/broker_registry/brokers_green.json`

Green-only curated registry for MVP (AIDR brokers.js lineage — re-implemented subset; expand later via update-brokers).

```json
{
  "registry_version": "1.0.0",
  "source": "DigiZafe curated Green subset + AIDR lineage attribution",
  "attribution": "Broker strategies inspired by auto-identity-remove (AIDR). Re-implemented under DigiZafe rules.",
  "legality_tier": "green",
  "brokers": [
    {
      "id": "truepeoplesearch",
      "name": "TruePeopleSearch",
      "method": "direct_form",
      "legality": "green",
      "opt_out_url": "https://www.truepeoplesearch.com/removal",
      "requires_captcha": false,
      "requires_email_confirm": false,
      "form_field_map": {
        "email": "input[type='email'], input[name*='email' i]",
        "first_name": "input[name*='first' i]",
        "last_name": "input[name*='last' i]",
        "state": "select[name*='state' i], input[name*='state' i]"
      },
      "submit_selector": "button[type='submit'], input[type='submit']",
      "success_hints": ["removed", "opt-out", "request received", "thank you", "success"],
      "search_url_template": null,
      "enabled": true
    },
    {
      "id": "fastpeoplesearch",
      "name": "FastPeopleSearch",
      "method": "direct_form",
      "legality": "green",
      "opt_out_url": "https://www.fastpeoplesearch.com/removal",
      "requires_captcha": true,
      "requires_email_confirm": false,
      "form_field_map": {
        "email": "input[type='email']",
        "first_name": "input[name*='first' i]",
        "last_name": "input[name*='last' i]"
      },
      "submit_selector": "button[type='submit']",
      "success_hints": ["removed", "request", "thank"],
      "enabled": true
    },
    {
      "id": "familytreenow",
      "name": "FamilyTreeNow",
      "method": "direct_form",
      "legality": "green",
      "opt_out_url": "https://www.familytreenow.com/optout",
      "requires_captcha": false,
      "requires_email_confirm": false,
      "form_field_map": {
        "email": "input[type='email']",
        "first_name": "input[name*='first' i]",
        "last_name": "input[name*='last' i]"
      },
      "submit_selector": "button[type='submit'], input[type='submit']",
      "success_hints": ["success", "removed", "opt out", "thank"],
      "enabled": true
    },
    {
      "id": "thatsthem",
      "name": "ThatsThem",
      "method": "direct_form",
      "legality": "green",
      "opt_out_url": "https://thatsthem.com/optout",
      "requires_captcha": false,
      "requires_email_confirm": false,
      "form_field_map": {
        "email": "input[type='email']",
        "name": "input[name*='name' i]"
      },
      "submit_selector": "button[type='submit']",
      "success_hints": ["success", "removed", "request"],
      "enabled": true
    },
    {
      "id": "spokeo",
      "name": "Spokeo",
      "method": "manual",
      "legality": "green",
      "opt_out_url": "https://www.spokeo.com/optout",
      "requires_captcha": true,
      "requires_email_confirm": true,
      "form_field_map": {},
      "submit_selector": null,
      "success_hints": [],
      "enabled": true,
      "notes": "Often CAPTCHA + email confirm — free path = open_in_browser / manual queue"
    },
    {
      "id": "acxiom",
      "name": "Acxiom",
      "method": "direct_form",
      "legality": "green",
      "opt_out_url": "https://www.acxiom.com/optout/",
      "requires_captcha": false,
      "requires_email_confirm": false,
      "form_field_map": {
        "email": "input[type='email']",
        "first_name": "input[name*='first' i]",
        "last_name": "input[name*='last' i]"
      },
      "submit_selector": "button[type='submit']",
      "success_hints": ["request", "received", "thank", "submit"],
      "enabled": true
    }
  ],
  "generic_strategies": [
    "do_not_sell_click",
    "privacy_manager",
    "generic_form_fill",
    "dsar_link_capture"
  ],
  "freeze_targets": [
    {
      "id": "equifax",
      "label": "Equifax credit freeze",
      "url": "https://www.equifax.com/personal/credit-report-services/credit-freeze/"
    },
    {
      "id": "experian",
      "label": "Experian credit freeze",
      "url": "https://www.experian.com/freeze/center.html"
    },
    {
      "id": "transunion",
      "label": "TransUnion credit freeze",
      "url": "https://www.transunion.com/credit-freeze"
    },
    {
      "id": "chexsystems",
      "label": "ChexSystems security freeze",
      "url": "https://www.chexsystems.com/security-freeze/place-freeze"
    },
    {
      "id": "innovis",
      "label": "Innovis security freeze",
      "url": "https://www.innovis.com/personal/securityFreeze"
    },
    {
      "id": "optoutprescreen",
      "label": "OptOutPrescreen (pre-screened offers)",
      "url": "https://www.optoutprescreen.com/"
    }
  ]
}
```

---

## 4. NEW: `backend/app/domain/remediation_states.py`  
*(pure state machine)*

```python
"""Remediation job + broker opt-out state transitions (pure). AIDR state.json lineage."""

from __future__ import annotations

from enum import Enum


class RemediationJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_CAPTCHA = "waiting_captcha"
    WAITING_EMAIL_CONFIRM = "waiting_email_confirm"
    WAITING_MANUAL = "waiting_manual"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class BrokerOptOutStatus(str, Enum):
    """Per-broker status — maps AIDR run outcomes."""
    PENDING = "pending"
    RUNNING = "running"
    SUBMITTED = "submitted"              # form accepted (≠ deleted)
    AWAITING_EMAIL_CONFIRM = "awaiting_email_confirm"
    SKIPPED_FRESH = "skipped_fresh"      # within recheck window
    NOT_LISTED = "not_listed"
    MANUAL_NEEDED = "manual_needed"
    CAPTCHA_NEEDED = "captcha_needed"
    VERIFIED_REMOVED = "verified_removed"
    STILL_LISTED = "still_listed"        # after verify
    ERROR = "error"
    DEAD = "dead"                        # stale URL
    CANCELLED = "cancelled"


class CaptchaItemStatus(str, Enum):
    PENDING = "pending"
    SOLVED = "solved"
    EXPIRED = "expired"
    SKIPPED = "skipped"


TERMINAL_JOB = frozenset({
    RemediationJobStatus.COMPLETED,
    RemediationJobStatus.PARTIAL,
    RemediationJobStatus.FAILED,
    RemediationJobStatus.CANCELLED,
    RemediationJobStatus.TIMED_OUT,
})

TERMINAL_BROKER = frozenset({
    BrokerOptOutStatus.SUBMITTED,
    BrokerOptOutStatus.SKIPPED_FRESH,
    BrokerOptOutStatus.NOT_LISTED,
    BrokerOptOutStatus.VERIFIED_REMOVED,
    BrokerOptOutStatus.STILL_LISTED,
    BrokerOptOutStatus.ERROR,
    BrokerOptOutStatus.DEAD,
    BrokerOptOutStatus.CANCELLED,
    BrokerOptOutStatus.MANUAL_NEEDED,  # terminal for auto runner; user may resume
    BrokerOptOutStatus.AWAITING_EMAIL_CONFIRM,  # semi-terminal until confirm
    BrokerOptOutStatus.CAPTCHA_NEEDED,
})


class InvalidTransition(ValueError):
    pass


_JOB_TRANSITIONS: dict[RemediationJobStatus, set[RemediationJobStatus]] = {
    RemediationJobStatus.PENDING: {
        RemediationJobStatus.RUNNING,
        RemediationJobStatus.CANCELLED,
        RemediationJobStatus.TIMED_OUT,
        RemediationJobStatus.FAILED,
    },
    RemediationJobStatus.RUNNING: {
        RemediationJobStatus.WAITING_CAPTCHA,
        RemediationJobStatus.WAITING_EMAIL_CONFIRM,
        RemediationJobStatus.WAITING_MANUAL,
        RemediationJobStatus.VERIFYING,
        RemediationJobStatus.COMPLETED,
        RemediationJobStatus.PARTIAL,
        RemediationJobStatus.FAILED,
        RemediationJobStatus.CANCELLED,
        RemediationJobStatus.TIMED_OUT,
    },
    RemediationJobStatus.WAITING_CAPTCHA: {
        RemediationJobStatus.RUNNING,
        RemediationJobStatus.WAITING_MANUAL,
        RemediationJobStatus.CANCELLED,
        RemediationJobStatus.TIMED_OUT,
        RemediationJobStatus.FAILED,
    },
    RemediationJobStatus.WAITING_EMAIL_CONFIRM: {
        RemediationJobStatus.RUNNING,
        RemediationJobStatus.VERIFYING,
        RemediationJobStatus.COMPLETED,
        RemediationJobStatus.PARTIAL,
        RemediationJobStatus.CANCELLED,
        RemediationJobStatus.TIMED_OUT,
    },
    RemediationJobStatus.WAITING_MANUAL: {
        RemediationJobStatus.RUNNING,
        RemediationJobStatus.COMPLETED,
        RemediationJobStatus.PARTIAL,
        RemediationJobStatus.CANCELLED,
        RemediationJobStatus.TIMED_OUT,
    },
    RemediationJobStatus.VERIFYING: {
        RemediationJobStatus.COMPLETED,
        RemediationJobStatus.PARTIAL,
        RemediationJobStatus.FAILED,
        RemediationJobStatus.TIMED_OUT,
    },
    RemediationJobStatus.COMPLETED: set(),
    RemediationJobStatus.PARTIAL: set(),
    RemediationJobStatus.FAILED: set(),
    RemediationJobStatus.CANCELLED: set(),
    RemediationJobStatus.TIMED_OUT: set(),
}


def transition_job(current: RemediationJobStatus | str, new: RemediationJobStatus | str) -> RemediationJobStatus:
    cur = RemediationJobStatus(current)
    nxt = RemediationJobStatus(new)
    if cur == nxt:
        return cur
    if nxt not in _JOB_TRANSITIONS.get(cur, set()):
        raise InvalidTransition(f"Invalid remediation job transition {cur.value} → {nxt.value}")
    return nxt


def is_terminal_job(status: RemediationJobStatus | str) -> bool:
    return RemediationJobStatus(status) in TERMINAL_JOB


def is_fresh_optout(last_success_iso: str | None, recheck_days: int, now_iso: str | None = None) -> bool:
    """AIDR skip-if-fresh within recheck window."""
    if not last_success_iso:
        return False
    from datetime import datetime, timezone, timedelta
    try:
        last = datetime.fromisoformat(last_success_iso.replace("Z", "+00:00"))
        now = datetime.fromisoformat(now_iso.replace("Z", "+00:00")) if now_iso else datetime.now(timezone.utc)
        return (now - last) < timedelta(days=recheck_days)
    except Exception:
        return False
```

---

## 5. NEW: `backend/app/domain/remediation_profile.py`  
*(pure profile for form fill — from verified identifiers only)*

```python
"""Build redacted remediation profile from verified identifiers (pure)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RemediationProfile:
    """Fields used to fill Green opt-out forms — never store plaintext long-term beyond job."""
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    zip: Optional[str] = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_safe_dict(self) -> dict[str, Any]:
        """For audit/logs — redacted."""
        def red_email(e: str | None) -> str | None:
            if not e or "@" not in e:
                return None
            local, _, dom = e.partition("@")
            return f"{local[:2]}***@{dom}"
        return {
            "email": red_email(self.email),
            "has_name": bool(self.full_name or self.first_name),
            "has_phone": bool(self.phone),
            "state": self.state,
            "city": self.city,
        }


def split_name(full: str) -> tuple[str, str]:
    parts = full.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def build_profile_from_identifiers(
    identifiers: list[dict[str, Any]],
    *,
    display_name: str | None = None,
    state: str | None = None,
    city: str | None = None,
    zip_code: str | None = None,
) -> RemediationProfile:
    """
    identifiers: list of {type, value_canonical, is_verified}
    Only verified identifiers contribute (G1).
    """
    email = phone = None
    for i in identifiers:
        if not i.get("is_verified"):
            continue
        t = i.get("type")
        v = i.get("value_canonical") or ""
        if t == "email" and not email:
            email = v
        elif t == "phone" and not phone:
            phone = v
    first, last = ("", "")
    if display_name:
        first, last = split_name(display_name)
    return RemediationProfile(
        email=email,
        first_name=first or None,
        last_name=last or None,
        full_name=display_name,
        phone=phone,
        state=state,
        city=city,
        zip=zip_code,
    )
```

---

## 6. NEW: `backend/app/models/remediation.py`

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


class BrokerOptOutState(Base):
    """
    AIDR state.json optOuts lineage — durable per-user per-broker status.
    Skips fresh opt-outs within BROKER_OPTOUT_RECHECK_DAYS.
    """

    __tablename__ = "broker_optout_state"
    __table_args__ = (
        UniqueConstraint("user_id", "broker_id", name="uq_broker_optout_user_broker"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    identifier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="SET NULL"), index=True, nullable=True
    )

    broker_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    broker_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(48), nullable=False, default="pending", index=True)

    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # listing_url, confirmation_hint, last_error, etc.

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RemediationJob(Base):
    """Batch remediation run (one or more brokers / playbooks)."""

    __tablename__ = "remediation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    identifier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="SET NULL"), index=True, nullable=True
    )
    recommendation_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    job_type: Mapped[str] = mapped_column(String(64), nullable=False, default="broker_optout")
    # broker_optout | freeze_checklist | know_request | complaint | verify_only

    status: Mapped[str] = mapped_column(String(48), nullable=False, default="pending", index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    broker_ids: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)

    progress_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Encrypted-at-rest optional profile snapshot for workers (short-lived fields in meta preferred)
    profile_meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    items: Mapped[list["RemediationJobItem"]] = relationship(
        "RemediationJobItem", back_populates="job", cascade="all, delete-orphan"
    )


class RemediationJobItem(Base):
    """Per-broker unit within a job."""

    __tablename__ = "remediation_job_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("remediation_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)

    broker_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    broker_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(48), nullable=False, default="pending", index=True)
    skip_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # open_url for manual, captcha_id, verify_result, etc.

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped["RemediationJob"] = relationship("RemediationJob", back_populates="items")


class CaptchaQueueItem(Base):
    """Free CAPTCHA path — user solves; optional CapSolver later."""

    __tablename__ = "captcha_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("remediation_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)

    broker_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    # pending | solved | expired | skipped

    page_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    captcha_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    sitekey: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    # User-provided token after manual solve
    solution_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    solved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FreezeChecklistItem(Base):
    """AIDR freeze.js lineage — user-tracked freeze status."""

    __tablename__ = "freeze_checklist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "target_id", name="uq_freeze_user_target"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="todo")
    # todo | in_progress | done | skipped
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class GeneratedRequest(Base):
    """DSAR / right-to-know / complaint letter bodies (AIDR know + complaints lineage)."""

    __tablename__ = "generated_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # right_to_know | deletion | complaint
    regime: Mapped[str] = mapped_column(String(32), nullable=False, default="ccpa")
    # ccpa | gdpr | other

    recipient_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    recipient_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    # draft | copied | sent_marked | deadline_passed
    deadline_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

---

## 7. UPDATE: `backend/app/models/__init__.py`

Add:

```python
from app.models.remediation import (
    BrokerOptOutState,
    RemediationJob,
    RemediationJobItem,
    CaptchaQueueItem,
    FreezeChecklistItem,
    GeneratedRequest,
)
# include in __all__
```

---

## 8. NEW: `backend/app/schemas/remediation.py`

```python
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, EmailStr


class RemediationProfileInput(BaseModel):
    """Optional profile fields for form fill (beyond verified identifiers)."""
    display_name: Optional[str] = Field(None, max_length=200)
    state: Optional[str] = Field(None, max_length=64)
    city: Optional[str] = Field(None, max_length=128)
    zip: Optional[str] = Field(None, max_length=20)


class BrokerOptOutStart(BaseModel):
    identifier_id: UUID  # verified email (or primary) — G1
    broker_ids: Optional[list[str]] = None  # default: all enabled green
    dry_run: bool = False
    profile: Optional[RemediationProfileInput] = None
    recommendation_id: Optional[UUID] = None


class JobItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    broker_id: str
    broker_name: str
    status: str
    skip_reason: Optional[str] = None
    error: Optional[str] = None
    detail: Optional[str] = None
    result_meta: Optional[dict[str, Any]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class RemediationJobPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: Optional[UUID] = None
    job_type: str
    status: str
    dry_run: bool
    broker_ids: Optional[list[Any]] = None
    progress_pct: float
    message: Optional[str] = None
    error: Optional[str] = None
    result_summary: Optional[dict[str, Any]] = None
    deadline_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    items: list[JobItemPublic] = []


class BrokerStatePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    broker_id: str
    broker_name: str
    status: str
    last_success_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    total_runs: int
    detail: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
    updated_at: datetime


class CaptchaPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    broker_id: str
    status: str
    page_url: Optional[str] = None
    captcha_type: str
    instructions: Optional[str] = None
    expires_at: datetime
    created_at: datetime


class CaptchaSolveRequest(BaseModel):
    solution_token: Optional[str] = Field(None, max_length=4000)
    # Or mark skipped / open_in_browser completed
    action: str = Field("solve", pattern="^(solve|skip|manual_done)$")


class ManualItemComplete(BaseModel):
    status: str = Field(..., pattern="^(submitted|manual_needed|skipped|error)$")
    detail: Optional[str] = None


class FreezeItemUpdate(BaseModel):
    status: str = Field(..., pattern="^(todo|in_progress|done|skipped)$")
    notes: Optional[str] = None


class FreezeItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_id: str
    label: str
    url: str
    status: str
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None


class KnowRequestCreate(BaseModel):
    regime: str = Field("ccpa", pattern="^(ccpa|gdpr|other)$")
    recipient_name: str = Field(..., min_length=1, max_length=256)
    recipient_email: Optional[EmailStr] = None
    identifier_id: Optional[UUID] = None
    include_deletion: bool = True


class ComplaintCreate(BaseModel):
    regime: str = Field("ccpa", pattern="^(ccpa|gdpr|other)$")
    recipient_name: str
    original_request_id: Optional[UUID] = None
    regulator: str = Field("ca_ag", max_length=64)
    # ca_ag | ico | other
    facts: str = Field(..., min_length=10, max_length=5000)


class GeneratedRequestPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    regime: str
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    subject: str
    body: str
    status: str
    deadline_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_at: datetime


class MarkSentRequest(BaseModel):
    sent: bool = True


class VerifyBrokersRequest(BaseModel):
    broker_ids: Optional[list[str]] = None  # default: those with last_success


class Message(BaseModel):
    message: str
```

---

## 9. NEW: `backend/app/remediation/broker_registry.py`

```python
"""Load Green broker registry from shared/config."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _candidates(path: str) -> list[Path]:
    p = Path(path)
    return [
        p,
        Path("/app") / p,
        Path("/app/shared/config/broker_registry") / p.name,
        Path("shared/config/broker_registry") / p.name,
        Path("shared/config/broker_registry/brokers_green.json"),
    ]


@lru_cache
def load_broker_registry() -> dict[str, Any]:
    settings = get_settings()
    for c in _candidates(settings.broker_registry_path):
        if c.exists():
            with c.open("r", encoding="utf-8") as f:
                return json.load(f)
    return {
        "registry_version": "empty",
        "brokers": [],
        "freeze_targets": [],
        "generic_strategies": [],
    }


def list_green_brokers(*, enabled_only: bool = True) -> list[dict[str, Any]]:
    reg = load_broker_registry()
    out = []
    for b in reg.get("brokers") or []:
        if b.get("legality", "green") != "green":
            continue
        if enabled_only and not b.get("enabled", True):
            continue
        out.append(b)
    return out


def get_broker(broker_id: str) -> dict[str, Any] | None:
    for b in list_green_brokers(enabled_only=False):
        if b.get("id") == broker_id:
            return b
    return None


def freeze_targets() -> list[dict[str, Any]]:
    return list(load_broker_registry().get("freeze_targets") or [])


def clear_registry_cache() -> None:
    load_broker_registry.cache_clear()
```

---

## 10. NEW: `backend/app/remediation/runners/playwright_runner.py`

```python
"""
Playwright Green broker runner (AIDR watcher/brokers lineage — Python re-impl).

Rules:
- Only Green brokers
- dry_run fills but does not submit
- CAPTCHA → return captcha_needed (never require CapSolver)
- Timeouts hard-enforced
- No cross-user browser context reuse
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.remediation_profile import RemediationProfile
from app.domain.remediation_states import BrokerOptOutStatus

logger = get_logger(__name__)


@dataclass
class RunnerResult:
    status: str  # BrokerOptOutStatus value
    detail: str = ""
    open_url: Optional[str] = None
    captcha_type: Optional[str] = None
    sitekey: Optional[str] = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "detail": self.detail,
            "open_url": self.open_url,
            "captcha_type": self.captcha_type,
            "sitekey": self.sitekey,
            "meta": self.meta,
        }


class PlaywrightBrokerRunner:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def run_broker(
        self,
        broker: dict[str, Any],
        profile: RemediationProfile,
        *,
        dry_run: bool = False,
        captcha_token: str | None = None,
        user_scope: str = "anon",
    ) -> RunnerResult:
        method = (broker.get("method") or "direct_form").lower()
        if method == "manual":
            return RunnerResult(
                status=BrokerOptOutStatus.MANUAL_NEEDED.value,
                detail="Broker requires manual / open-in-browser path (free CAPTCHA path)",
                open_url=broker.get("opt_out_url"),
                meta={"aidr_lineage": "manual"},
            )

        if broker.get("requires_captcha") and not captcha_token:
            mode = (self.settings.captcha_mode or "manual").lower()
            if mode in {"manual", "open_in_browser"} or not self.settings.feature_capsolver:
                return RunnerResult(
                    status=BrokerOptOutStatus.CAPTCHA_NEEDED.value,
                    detail="CAPTCHA required — free path: solve manually or open_in_browser",
                    open_url=broker.get("opt_out_url"),
                    captcha_type="recaptcha_or_unknown",
                    meta={"captcha_mode": mode},
                )
            # CapSolver optional path (feature flag)
            token = await self._try_capsolver(broker)
            if not token:
                return RunnerResult(
                    status=BrokerOptOutStatus.CAPTCHA_NEEDED.value,
                    detail="CapSolver unavailable or failed — falling back to manual",
                    open_url=broker.get("opt_out_url"),
                )
            captcha_token = token

        try:
            return await self._playwright_direct_form(
                broker, profile, dry_run=dry_run, captcha_token=captcha_token, user_scope=user_scope
            )
        except Exception as e:
            logger.exception("playwright_broker_failed", broker=broker.get("id"), error=str(e))
            msg = str(e).lower()
            if "err_name_not_resolved" in msg or "net::" in msg:
                return RunnerResult(status=BrokerOptOutStatus.DEAD.value, detail=str(e)[:500])
            return RunnerResult(status=BrokerOptOutStatus.ERROR.value, detail=str(e)[:500])

    async def _try_capsolver(self, broker: dict[str, Any]) -> str | None:
        if not self.settings.feature_capsolver or not self.settings.capsolver_api_key:
            return None
        # Optional paid path — stub that does not hard-depend
        logger.info("capsolver_skipped_or_unimplemented", broker=broker.get("id"))
        return None

    async def _playwright_direct_form(
        self,
        broker: dict[str, Any],
        profile: RemediationProfile,
        *,
        dry_run: bool,
        captcha_token: str | None,
        user_scope: str,
    ) -> RunnerResult:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return RunnerResult(
                status=BrokerOptOutStatus.ERROR.value,
                detail="playwright not installed in this worker image",
            )

        url = broker.get("opt_out_url")
        if not url or not str(url).startswith("https://"):
            return RunnerResult(status=BrokerOptOutStatus.DEAD.value, detail="Invalid opt_out_url")

        timeout_ms = int(self.settings.broker_runner_timeout_seconds * 1000)
        field_map = broker.get("form_field_map") or {}
        submit_sel = broker.get("submit_selector")
        success_hints = [h.lower() for h in (broker.get("success_hints") or [])]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.settings.playwright_headless)
            context = await browser.new_context(
                user_agent="DigiZafe-Remediation/0.7 (personal self-only opt-out; +local)",
                locale="en-US",
            )
            page = await context.new_page()
            page.set_default_timeout(timeout_ms)
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                if resp and resp.status == 404:
                    return RunnerResult(status=BrokerOptOutStatus.DEAD.value, detail="404")

                # Detect obvious captcha widgets
                content = (await page.content()).lower()
                if "recaptcha" in content or "hcaptcha" in content or "cf-turnstile" in content:
                    if not captcha_token:
                        sitekey = None
                        m = re.search(r'data-sitekey=["\']([^"\']+)', content)
                        if m:
                            sitekey = m.group(1)
                        return RunnerResult(
                            status=BrokerOptOutStatus.CAPTCHA_NEEDED.value,
                            detail="CAPTCHA widget detected on page",
                            open_url=url,
                            captcha_type="detected",
                            sitekey=sitekey,
                        )

                # Fill fields
                value_for = {
                    "email": profile.email or "",
                    "first_name": profile.first_name or "",
                    "last_name": profile.last_name or "",
                    "name": profile.full_name or f"{profile.first_name or ''} {profile.last_name or ''}".strip(),
                    "phone": profile.phone or "",
                    "state": profile.state or "",
                    "city": profile.city or "",
                    "zip": profile.zip or "",
                }
                filled = 0
                for logical, selector in field_map.items():
                    val = value_for.get(logical, "")
                    if not val or not selector:
                        continue
                    try:
                        loc = page.locator(selector).first
                        if await loc.count() == 0:
                            continue
                        tag = await loc.evaluate("el => el.tagName.toLowerCase()")
                        if tag == "select":
                            await loc.select_option(label=val)
                        else:
                            await loc.fill(val)
                        filled += 1
                    except Exception as fe:
                        logger.info("field_fill_skip", field=logical, error=str(fe))

                if captcha_token:
                    # Best-effort inject token into common textarea
                    try:
                        await page.evaluate(
                            """(token) => {
                              const el = document.querySelector('[name="g-recaptcha-response"], #g-recaptcha-response');
                              if (el) { el.value = token; }
                            }""",
                            captcha_token,
                        )
                    except Exception:
                        pass

                if dry_run:
                    return RunnerResult(
                        status=BrokerOptOutStatus.SUBMITTED.value,
                        detail=f"dry_run: filled {filled} fields, submit skipped",
                        meta={"dry_run": True, "filled": filled, "url": url},
                    )

                if submit_sel:
                    try:
                        await page.locator(submit_sel).first.click(timeout=5000)
                        await page.wait_for_timeout(1500)
                    except Exception as se:
                        return RunnerResult(
                            status=BrokerOptOutStatus.MANUAL_NEEDED.value,
                            detail=f"Submit failed: {se}",
                            open_url=url,
                        )
                else:
                    return RunnerResult(
                        status=BrokerOptOutStatus.MANUAL_NEEDED.value,
                        detail="No submit selector",
                        open_url=url,
                    )

                body = (await page.content()).lower()
                if any(h in body for h in success_hints):
                    return RunnerResult(
                        status=BrokerOptOutStatus.SUBMITTED.value,
                        detail="Form submitted; success hints matched",
                        meta={"filled": filled, "url": url},
                    )
                # Heuristic accept
                if filled > 0:
                    return RunnerResult(
                        status=BrokerOptOutStatus.SUBMITTED.value,
                        detail="Form submitted (heuristic — verify separately)",
                        meta={"filled": filled, "url": url, "confidence": "low"},
                    )
                return RunnerResult(
                    status=BrokerOptOutStatus.MANUAL_NEEDED.value,
                    detail="Could not fill/submit confidently",
                    open_url=url,
                )
            finally:
                await context.close()
                await browser.close()

    async def verify_not_listed(
        self,
        broker: dict[str, Any],
        profile: RemediationProfile,
        *,
        user_scope: str = "anon",
    ) -> RunnerResult:
        """
        Best-effort re-check (AIDR verify lineage).
        Without a reliable public search API per broker, open opt-out/search page
        and look for name/email absence — honest low confidence.
        """
        search_tpl = broker.get("search_url_template")
        url = search_tpl.format(
            name=(profile.full_name or "").replace(" ", "+"),
            state=profile.state or "",
        ) if search_tpl else broker.get("opt_out_url")
        if not url:
            return RunnerResult(
                status=BrokerOptOutStatus.STILL_LISTED.value,
                detail="No verify URL — cannot confirm",
                meta={"confidence": "none"},
            )
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return RunnerResult(status=BrokerOptOutStatus.ERROR.value, detail="playwright missing")

        needle = (profile.email or profile.full_name or "").lower()
        if not needle:
            return RunnerResult(
                status=BrokerOptOutStatus.NOT_LISTED.value,
                detail="No needle to search — treating as N/A",
                meta={"confidence": "none"},
            )

        timeout_ms = int(self.settings.broker_runner_timeout_seconds * 1000)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                body = (await page.content()).lower()
                if needle in body:
                    return RunnerResult(
                        status=BrokerOptOutStatus.STILL_LISTED.value,
                        detail="Needle still present on page (low-confidence verify)",
                        open_url=url,
                        meta={"confidence": "low"},
                    )
                return RunnerResult(
                    status=BrokerOptOutStatus.VERIFIED_REMOVED.value,
                    detail="Needle not found on page (low-confidence verify)",
                    open_url=url,
                    meta={"confidence": "low"},
                )
            except Exception as e:
                return RunnerResult(status=BrokerOptOutStatus.ERROR.value, detail=str(e)[:500])
            finally:
                await browser.close()
```

---

## 11. NEW: `backend/app/remediation/generators/templates.py`

```python
"""Right-to-know / deletion / complaint letter generators (AIDR know + complaints lineage)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def generate_right_to_know(
    *,
    regime: str,
    full_name: str,
    email: str,
    recipient_name: str,
    include_deletion: bool = True,
) -> dict[str, Any]:
    regime = regime.lower()
    if regime == "gdpr":
        subject = f"Subject Access Request (GDPR Art. 15) — {full_name}"
        rights = (
            "I am making a subject access request under Article 15 of the GDPR. "
            "Please confirm whether you process my personal data and provide a copy of all "
            "personal data you hold about me, the purposes, categories, recipients, and retention."
        )
        deletion = (
            "\n\nI also request erasure under Article 17 GDPR of all personal data you hold about me, "
            "except where a lawful exemption applies. Please confirm completion within one month."
            if include_deletion
            else ""
        )
        deadline_days = 30
    else:
        subject = f"California Consumer Privacy Act Request — {full_name}"
        rights = (
            "I am a consumer submitting a request under the California Consumer Privacy Act (CCPA/CPRA). "
            "Please disclose the categories and specific pieces of personal information you have collected "
            "about me, sources, business/commercial purposes, and third parties with whom it was shared/sold."
        )
        deletion = (
            "\n\nI also request deletion of my personal information under CCPA/CPRA, and that you "
            "direct service providers to delete my information where required. "
            "Please confirm within 45 days (extendable as permitted by law)."
            if include_deletion
            else ""
        )
        deadline_days = 45

    body = f"""{recipient_name}

{rights}{deletion}

Identifiers to locate my records:
- Full name: {full_name}
- Email: {email}

Please respond to: {email}

Sincerely,
{full_name}
Generated by DigiZafe (user-directed). Templates inspired by AIDR right-to-know lineage.
"""
    deadline = datetime.now(timezone.utc) + timedelta(days=deadline_days)
    return {
        "subject": subject,
        "body": body.strip(),
        "deadline_at": deadline,
        "meta": {"regime": regime, "deadline_days": deadline_days, "aidr_lineage": "lib/right-to-know.js"},
    }


def generate_complaint(
    *,
    regime: str,
    full_name: str,
    email: str,
    recipient_name: str,
    regulator: str,
    facts: str,
) -> dict[str, Any]:
    if regulator == "ico":
        subject = f"Complaint regarding data controller {recipient_name} — {full_name}"
        intro = "I wish to raise a complaint with the Information Commissioner's Office regarding the following."
    else:
        subject = f"CCPA complaint — failure to respond by {recipient_name}"
        intro = (
            "I am submitting a complaint regarding a business's failure to timely respond to my "
            "CCPA/CPRA consumer request."
        )
    body = f"""{intro}

Consumer: {full_name}
Contact email: {email}
Business / broker: {recipient_name}

Facts:
{facts}

I request that the regulator investigate and require the business to comply with applicable privacy law.

Sincerely,
{full_name}
Generated by DigiZafe (user-directed). Templates inspired by AIDR complaints lineage.
"""
    return {
        "subject": subject,
        "body": body.strip(),
        "deadline_at": None,
        "meta": {"regime": regime, "regulator": regulator, "aidr_lineage": "lib/complaints"},
    }
```

---

## 12. NEW: `backend/app/repositories/remediation_repository.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.remediation import (
    BrokerOptOutState,
    RemediationJob,
    RemediationJobItem,
    CaptchaQueueItem,
    FreezeChecklistItem,
    GeneratedRequest,
)
from app.domain.remediation_states import (
    RemediationJobStatus,
    BrokerOptOutStatus,
    transition_job,
    is_terminal_job,
)


class RemediationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- state (AIDR state.json) ----
    async def get_state(self, user_id: uuid.UUID, broker_id: str) -> Optional[BrokerOptOutState]:
        r = await self.session.execute(
            select(BrokerOptOutState).where(
                BrokerOptOutState.user_id == user_id,
                BrokerOptOutState.broker_id == broker_id,
            )
        )
        return r.scalar_one_or_none()

    async def list_states(self, user_id: uuid.UUID) -> Sequence[BrokerOptOutState]:
        r = await self.session.execute(
            select(BrokerOptOutState)
            .where(BrokerOptOutState.user_id == user_id)
            .order_by(BrokerOptOutState.updated_at.desc())
        )
        return r.scalars().all()

    async def upsert_state(
        self,
        *,
        user_id: uuid.UUID,
        broker_id: str,
        broker_name: str,
        status: str,
        identifier_id: uuid.UUID | None = None,
        detail: str | None = None,
        meta: dict | None = None,
        success: bool = False,
        verified: bool = False,
    ) -> BrokerOptOutState:
        row = await self.get_state(user_id, broker_id)
        now = datetime.now(timezone.utc)
        if not row:
            row = BrokerOptOutState(
                user_id=user_id,
                broker_id=broker_id,
                broker_name=broker_name,
                identifier_id=identifier_id,
                status=status,
                total_runs=1,
                last_attempt_at=now,
                detail=detail,
                meta=meta,
            )
            if success:
                row.last_success_at = now
            if verified:
                row.last_verified_at = now
            self.session.add(row)
        else:
            row.status = status
            row.last_attempt_at = now
            row.total_runs = (row.total_runs or 0) + 1
            if detail is not None:
                row.detail = detail
            if meta is not None:
                row.meta = {**(row.meta or {}), **meta}
            if identifier_id:
                row.identifier_id = identifier_id
            if success:
                row.last_success_at = now
            if verified:
                row.last_verified_at = now
        await self.session.flush()
        return row

    # ---- jobs ----
    async def create_job(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID | None,
        job_type: str,
        broker_ids: list[str],
        deadline_at: datetime,
        dry_run: bool = False,
        recommendation_id: uuid.UUID | None = None,
        profile_meta: dict | None = None,
        items: list[tuple[str, str]],  # (broker_id, broker_name)
    ) -> RemediationJob:
        job = RemediationJob(
            user_id=user_id,
            identifier_id=identifier_id,
            recommendation_id=recommendation_id,
            job_type=job_type,
            status=RemediationJobStatus.PENDING.value,
            dry_run=dry_run,
            broker_ids=broker_ids,
            deadline_at=deadline_at,
            profile_meta=profile_meta,
            message="Queued",
            progress_pct=0.0,
        )
        self.session.add(job)
        await self.session.flush()
        for bid, bname in items:
            self.session.add(
                RemediationJobItem(
                    job_id=job.id,
                    user_id=user_id,
                    broker_id=bid,
                    broker_name=bname,
                    status=BrokerOptOutStatus.PENDING.value,
                )
            )
        await self.session.flush()
        return job

    async def get_job(self, job_id: uuid.UUID, user_id: uuid.UUID) -> Optional[RemediationJob]:
        r = await self.session.execute(
            select(RemediationJob)
            .options(selectinload(RemediationJob.items))
            .where(RemediationJob.id == job_id, RemediationJob.user_id == user_id)
        )
        return r.scalar_one_or_none()

    async def get_job_internal(self, job_id: uuid.UUID) -> Optional[RemediationJob]:
        r = await self.session.execute(
            select(RemediationJob)
            .options(selectinload(RemediationJob.items))
            .where(RemediationJob.id == job_id)
        )
        return r.scalar_one_or_none()

    async def list_jobs(self, user_id: uuid.UUID, limit: int = 50) -> Sequence[RemediationJob]:
        r = await self.session.execute(
            select(RemediationJob)
            .where(RemediationJob.user_id == user_id)
            .order_by(RemediationJob.created_at.desc())
            .limit(limit)
        )
        return r.scalars().all()

    async def count_active_jobs(self, user_id: uuid.UUID) -> int:
        r = await self.session.execute(
            select(RemediationJob).where(
                RemediationJob.user_id == user_id,
                RemediationJob.status.in_(
                    [
                        RemediationJobStatus.PENDING.value,
                        RemediationJobStatus.RUNNING.value,
                        RemediationJobStatus.WAITING_CAPTCHA.value,
                        RemediationJobStatus.WAITING_EMAIL_CONFIRM.value,
                        RemediationJobStatus.WAITING_MANUAL.value,
                        RemediationJobStatus.VERIFYING.value,
                    ]
                ),
            )
        )
        return len(r.scalars().all())

    async def set_job_status(
        self,
        job: RemediationJob,
        status: str,
        *,
        message: str | None = None,
        error: str | None = None,
        progress_pct: float | None = None,
        result_summary: dict | None = None,
    ) -> RemediationJob:
        nxt = transition_job(job.status, status)
        job.status = nxt.value
        if message is not None:
            job.message = message
        if error is not None:
            job.error = error
        if progress_pct is not None:
            job.progress_pct = progress_pct
        if result_summary is not None:
            job.result_summary = result_summary
        now = datetime.now(timezone.utc)
        if nxt == RemediationJobStatus.RUNNING and job.started_at is None:
            job.started_at = now
        if is_terminal_job(nxt):
            job.finished_at = now
            if progress_pct is None:
                job.progress_pct = 100.0
        await self.session.flush()
        return job

    async def set_item_status(
        self,
        item: RemediationJobItem,
        status: str,
        *,
        skip_reason: str | None = None,
        error: str | None = None,
        detail: str | None = None,
        result_meta: dict | None = None,
    ) -> RemediationJobItem:
        item.status = status
        if skip_reason is not None:
            item.skip_reason = skip_reason
        if error is not None:
            item.error = error
        if detail is not None:
            item.detail = detail
        if result_meta is not None:
            item.result_meta = result_meta
        now = datetime.now(timezone.utc)
        if status == BrokerOptOutStatus.RUNNING.value and item.started_at is None:
            item.started_at = now
        if status not in {BrokerOptOutStatus.PENDING.value, BrokerOptOutStatus.RUNNING.value}:
            item.finished_at = now
        await self.session.flush()
        return item

    async def recompute_job_progress(self, job: RemediationJob) -> None:
        items = job.items or []
        if not items:
            job.progress_pct = 100.0
            await self.session.flush()
            return
        done = sum(
            1
            for i in items
            if i.status
            not in {
                BrokerOptOutStatus.PENDING.value,
                BrokerOptOutStatus.RUNNING.value,
            }
        )
        job.progress_pct = round(100.0 * done / len(items), 1)
        await self.session.flush()

    # ---- captcha ----
    async def create_captcha(
        self,
        *,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        job_item_id: uuid.UUID | None,
        broker_id: str,
        page_url: str | None,
        captcha_type: str,
        sitekey: str | None,
        instructions: str,
        ttl_hours: int,
    ) -> CaptchaQueueItem:
        row = CaptchaQueueItem(
            user_id=user_id,
            job_id=job_id,
            job_item_id=job_item_id,
            broker_id=broker_id,
            status="pending",
            page_url=page_url,
            captcha_type=captcha_type,
            sitekey=sitekey,
            instructions=instructions,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_captcha(self, captcha_id: uuid.UUID, user_id: uuid.UUID) -> Optional[CaptchaQueueItem]:
        r = await self.session.execute(
            select(CaptchaQueueItem).where(
                CaptchaQueueItem.id == captcha_id, CaptchaQueueItem.user_id == user_id
            )
        )
        return r.scalar_one_or_none()

    async def list_pending_captchas(self, user_id: uuid.UUID) -> Sequence[CaptchaQueueItem]:
        r = await self.session.execute(
            select(CaptchaQueueItem)
            .where(
                CaptchaQueueItem.user_id == user_id,
                CaptchaQueueItem.status == "pending",
            )
            .order_by(CaptchaQueueItem.created_at.asc())
        )
        return r.scalars().all()

    # ---- freeze ----
    async def list_freeze(self, user_id: uuid.UUID) -> Sequence[FreezeChecklistItem]:
        r = await self.session.execute(
            select(FreezeChecklistItem).where(FreezeChecklistItem.user_id == user_id)
        )
        return r.scalars().all()

    async def upsert_freeze_seed(
        self, user_id: uuid.UUID, targets: list[dict[str, Any]]
    ) -> list[FreezeChecklistItem]:
        existing = {x.target_id: x for x in await self.list_freeze(user_id)}
        out: list[FreezeChecklistItem] = []
        for t in targets:
            tid = t["id"]
            if tid in existing:
                out.append(existing[tid])
                continue
            row = FreezeChecklistItem(
                user_id=user_id,
                target_id=tid,
                label=t["label"],
                url=t["url"],
                status="todo",
            )
            self.session.add(row)
            out.append(row)
        await self.session.flush()
        return out

    async def get_freeze(self, item_id: uuid.UUID, user_id: uuid.UUID) -> Optional[FreezeChecklistItem]:
        r = await self.session.execute(
            select(FreezeChecklistItem).where(
                FreezeChecklistItem.id == item_id, FreezeChecklistItem.user_id == user_id
            )
        )
        return r.scalar_one_or_none()

    # ---- generated requests ----
    async def create_generated(self, **kwargs: Any) -> GeneratedRequest:
        row = GeneratedRequest(**kwargs)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_generated(self, req_id: uuid.UUID, user_id: uuid.UUID) -> Optional[GeneratedRequest]:
        r = await self.session.execute(
            select(GeneratedRequest).where(
                GeneratedRequest.id == req_id, GeneratedRequest.user_id == user_id
            )
        )
        return r.scalar_one_or_none()

    async def list_generated(self, user_id: uuid.UUID, kind: str | None = None) -> Sequence[GeneratedRequest]:
        q = select(GeneratedRequest).where(GeneratedRequest.user_id == user_id)
        if kind:
            q = q.where(GeneratedRequest.kind == kind)
        q = q.order_by(GeneratedRequest.created_at.desc())
        r = await self.session.execute(q)
        return r.scalars().all()
```

---

## 13. NEW: `backend/app/services/remediation_service.py`

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
from app.domain.remediation_states import (
    RemediationJobStatus,
    BrokerOptOutStatus,
    is_fresh_optout,
    is_terminal_job,
)
from app.domain.remediation_profile import build_profile_from_identifiers, RemediationProfile
from app.repositories.remediation_repository import RemediationRepository
from app.repositories.identifier_repository import IdentifierRepository
from app.services.audit_service import AuditService
from app.services.consent_service import ConsentService
from app.remediation.broker_registry import list_green_brokers, get_broker, freeze_targets
from app.remediation.runners.playwright_runner import PlaywrightBrokerRunner
from app.remediation.generators.templates import generate_right_to_know, generate_complaint

logger = get_logger(__name__)


class RemediationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RemediationRepository(session)
        self.identifiers = IdentifierRepository(session)
        self.audit = AuditService(session)
        self.consent = ConsentService(session)
        self.settings = get_settings()
        self.runner = PlaywrightBrokerRunner()

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def _require_verified_identifier(self, user_id: uuid.UUID, identifier_id: uuid.UUID):
        row = await self.identifiers.get(identifier_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Identifier not found")
        if not row.is_verified:
            raise HTTPException(status_code=403, detail="G1: identifier must be verified before remediation")
        return row

    async def start_broker_optout(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID,
        broker_ids: list[str] | None,
        dry_run: bool = False,
        display_name: str | None = None,
        state: str | None = None,
        city: str | None = None,
        zip_code: str | None = None,
        recommendation_id: uuid.UUID | None = None,
    ):
        if not self.settings.feature_remediation:
            raise HTTPException(status_code=503, detail="Remediation disabled")

        await self._set_rls(user_id)
        ident = await self._require_verified_identifier(user_id, identifier_id)

        active = await self.repo.count_active_jobs(user_id)
        if active >= self.settings.broker_max_concurrent_jobs_per_user:
            raise HTTPException(status_code=429, detail="Max concurrent remediation jobs reached")

        await self.consent.ensure_consent(
            user_id,
            purpose="remediation.broker_optout",
            auto_grant=True,
            scope=str(identifier_id),
        )

        greens = list_green_brokers(enabled_only=True)
        if broker_ids:
            selected = [b for b in greens if b["id"] in set(broker_ids)]
        else:
            selected = greens
        if not selected:
            raise HTTPException(status_code=400, detail="No Green brokers selected")

        idents = await self.identifiers.list_for_user(user_id)
        profile = build_profile_from_identifiers(
            [
                {
                    "type": i.type,
                    "value_canonical": i.value_canonical,
                    "is_verified": i.is_verified,
                }
                for i in idents
            ],
            display_name=display_name,
            state=state,
            city=city,
            zip_code=zip_code,
        )
        if not profile.email and ident.type == "email":
            profile.email = ident.value_canonical
        if not profile.email:
            raise HTTPException(
                status_code=400,
                detail="Verified email required on account for broker opt-out forms",
            )

        deadline = datetime.now(timezone.utc) + timedelta(
            minutes=self.settings.broker_job_deadline_minutes
        )
        job = await self.repo.create_job(
            user_id=user_id,
            identifier_id=identifier_id,
            job_type="broker_optout",
            broker_ids=[b["id"] for b in selected],
            deadline_at=deadline,
            dry_run=dry_run,
            recommendation_id=recommendation_id,
            profile_meta={
                "profile_safe": profile.to_safe_dict(),
                # Worker reloads identifiers; store non-secret profile hints only
                "display_name": display_name,
                "state": state,
                "city": city,
                "zip": zip_code,
            },
            items=[(b["id"], b["name"]) for b in selected],
        )
        await self.audit.log(
            "remediation.job_created",
            user_id=user_id,
            resource_type="remediation_job",
            resource_id=str(job.id),
            details={"brokers": [b["id"] for b in selected], "dry_run": dry_run},
        )
        await self.session.commit()

        from app.tasks.remediation_tasks import execute_remediation_job_task

        execute_remediation_job_task.delay(str(job.id))
        return await self.repo.get_job(job.id, user_id)

    async def get_job(self, user_id: uuid.UUID, job_id: uuid.UUID):
        await self._set_rls(user_id)
        job = await self.repo.get_job(job_id, user_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    async def list_jobs(self, user_id: uuid.UUID):
        await self._set_rls(user_id)
        return await self.repo.list_jobs(user_id)

    async def list_broker_states(self, user_id: uuid.UUID):
        await self._set_rls(user_id)
        return await self.repo.list_states(user_id)

    async def cancel_job(self, user_id: uuid.UUID, job_id: uuid.UUID):
        await self._set_rls(user_id)
        job = await self.repo.get_job(job_id, user_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if is_terminal_job(job.status):
            raise HTTPException(status_code=400, detail="Job already terminal")
        await self.repo.set_job_status(job, RemediationJobStatus.CANCELLED.value, message="Cancelled by user")
        for item in job.items or []:
            if item.status in {
                BrokerOptOutStatus.PENDING.value,
                BrokerOptOutStatus.RUNNING.value,
                BrokerOptOutStatus.CAPTCHA_NEEDED.value,
            }:
                await self.repo.set_item_status(item, BrokerOptOutStatus.CANCELLED.value)
        await self.session.commit()
        return job

    # ---------- Worker ----------
    async def execute_job(self, job_id: uuid.UUID) -> None:
        job = await self.repo.get_job_internal(job_id)
        if not job:
            return
        await self._set_rls(job.user_id)

        if is_terminal_job(job.status) or job.status == RemediationJobStatus.CANCELLED.value:
            return

        now = datetime.now(timezone.utc)
        if job.deadline_at < now:
            await self.repo.set_job_status(
                job, RemediationJobStatus.TIMED_OUT.value, message="Deadline exceeded", error="deadline"
            )
            await self.session.commit()
            return

        await self.repo.set_job_status(job, RemediationJobStatus.RUNNING.value, message="Running brokers")
        await self.session.commit()

        job = await self.repo.get_job_internal(job_id)
        assert job

        # Rebuild profile from DB identifiers
        idents = await self.identifiers.list_for_user(job.user_id)
        pm = job.profile_meta or {}
        profile = build_profile_from_identifiers(
            [
                {"type": i.type, "value_canonical": i.value_canonical, "is_verified": i.is_verified}
                for i in idents
            ],
            display_name=pm.get("display_name"),
            state=pm.get("state"),
            city=pm.get("city"),
            zip_code=pm.get("zip"),
        )

        for item in list(job.items or []):
            await self.session.refresh(job)
            if job.status == RemediationJobStatus.CANCELLED.value:
                break
            if job.deadline_at < datetime.now(timezone.utc):
                await self.repo.set_job_status(job, RemediationJobStatus.TIMED_OUT.value, message="Deadline")
                break
            if item.status != BrokerOptOutStatus.PENDING.value:
                continue

            broker = get_broker(item.broker_id)
            if not broker:
                await self.repo.set_item_status(
                    item, BrokerOptOutStatus.ERROR.value, error="unknown_broker"
                )
                await self.repo.recompute_job_progress(job)
                await self.session.commit()
                continue

            # Fresh skip (AIDR state.json)
            st = await self.repo.get_state(job.user_id, item.broker_id)
            if st and st.last_success_at:
                if is_fresh_optout(
                    st.last_success_at.isoformat(),
                    self.settings.broker_optout_recheck_days,
                ):
                    await self.repo.set_item_status(
                        item,
                        BrokerOptOutStatus.SKIPPED_FRESH.value,
                        skip_reason="fresh",
                        detail=f"Last success {st.last_success_at.isoformat()}",
                    )
                    await self.repo.recompute_job_progress(job)
                    await self.session.commit()
                    continue

            await self.repo.set_item_status(item, BrokerOptOutStatus.RUNNING.value)
            await self.session.commit()

            result = await self.runner.run_broker(
                broker,
                profile,
                dry_run=job.dry_run,
                user_scope=str(job.user_id),
            )
            status = result.status
            success = status == BrokerOptOutStatus.SUBMITTED.value and not job.dry_run

            if status == BrokerOptOutStatus.CAPTCHA_NEEDED.value:
                cap = await self.repo.create_captcha(
                    user_id=job.user_id,
                    job_id=job.id,
                    job_item_id=item.id,
                    broker_id=item.broker_id,
                    page_url=result.open_url or broker.get("opt_out_url"),
                    captcha_type=result.captcha_type or "unknown",
                    sitekey=result.sitekey,
                    instructions=(
                        f"Open {result.open_url or broker.get('opt_out_url')} and complete the CAPTCHA / form. "
                        "Then mark manual_done or submit solution_token if applicable."
                    ),
                    ttl_hours=self.settings.captcha_queue_ttl_hours,
                )
                await self.repo.set_item_status(
                    item,
                    BrokerOptOutStatus.CAPTCHA_NEEDED.value,
                    detail=result.detail,
                    result_meta={**result.to_dict(), "captcha_id": str(cap.id)},
                )
                await self.repo.set_job_status(
                    job,
                    RemediationJobStatus.WAITING_CAPTCHA.value,
                    message="Waiting for CAPTCHA / manual action",
                )
                await self.repo.upsert_state(
                    user_id=job.user_id,
                    broker_id=item.broker_id,
                    broker_name=item.broker_name,
                    status=BrokerOptOutStatus.CAPTCHA_NEEDED.value,
                    identifier_id=job.identifier_id,
                    detail=result.detail,
                    meta=result.to_dict(),
                )
                await self.repo.recompute_job_progress(job)
                await self.session.commit()
                continue  # process other brokers; job may stay waiting_captcha

            if status == BrokerOptOutStatus.MANUAL_NEEDED.value:
                await self.repo.set_item_status(
                    item,
                    BrokerOptOutStatus.MANUAL_NEEDED.value,
                    detail=result.detail,
                    result_meta=result.to_dict(),
                )
                await self.repo.upsert_state(
                    user_id=job.user_id,
                    broker_id=item.broker_id,
                    broker_name=item.broker_name,
                    status=BrokerOptOutStatus.MANUAL_NEEDED.value,
                    identifier_id=job.identifier_id,
                    detail=result.detail,
                    meta=result.to_dict(),
                )
            else:
                await self.repo.set_item_status(
                    item,
                    status,
                    detail=result.detail,
                    error=result.detail if status == BrokerOptOutStatus.ERROR.value else None,
                    result_meta=result.to_dict(),
                )
                await self.repo.upsert_state(
                    user_id=job.user_id,
                    broker_id=item.broker_id,
                    broker_name=item.broker_name,
                    status=status,
                    identifier_id=job.identifier_id,
                    detail=result.detail,
                    meta=result.to_dict(),
                    success=success,
                )

                # Optional verify loop
                if (
                    success
                    and self.settings.remediation_verify_after_submit
                    and not job.dry_run
                ):
                    v = await self.runner.verify_not_listed(broker, profile, user_scope=str(job.user_id))
                    await self.repo.upsert_state(
                        user_id=job.user_id,
                        broker_id=item.broker_id,
                        broker_name=item.broker_name,
                        status=v.status,
                        identifier_id=job.identifier_id,
                        detail=v.detail,
                        meta=v.to_dict(),
                        success=True,
                        verified=v.status == BrokerOptOutStatus.VERIFIED_REMOVED.value,
                    )
                    await self.repo.set_item_status(
                        item,
                        v.status,
                        detail=v.detail,
                        result_meta={**(item.result_meta or {}), "verify": v.to_dict()},
                    )

            await self.consent.record_egress(
                purpose="remediation.broker_optout",
                destination_host=(broker.get("opt_out_url") or "")[:255],
                method="BROWSER",
                success=success or status in {
                    BrokerOptOutStatus.SKIPPED_FRESH.value,
                    BrokerOptOutStatus.NOT_LISTED.value,
                },
                user_id=job.user_id,
                identifier_id=job.identifier_id,
                summary={"broker_id": item.broker_id, "status": status, "dry_run": job.dry_run},
            )
            await self.repo.recompute_job_progress(job)
            await self.session.commit()

        # Finalize if no waiting items
        job = await self.repo.get_job_internal(job_id)
        if not job or is_terminal_job(job.status):
            return
        items = job.items or []
        waiting = [
            i
            for i in items
            if i.status
            in {
                BrokerOptOutStatus.CAPTCHA_NEEDED.value,
                BrokerOptOutStatus.AWAITING_EMAIL_CONFIRM.value,
                BrokerOptOutStatus.MANUAL_NEEDED.value,
                BrokerOptOutStatus.PENDING.value,
                BrokerOptOutStatus.RUNNING.value,
            }
        ]
        if waiting:
            # If only manual/captcha left, leave waiting status
            if any(i.status == BrokerOptOutStatus.CAPTCHA_NEEDED.value for i in waiting):
                await self.repo.set_job_status(
                    job, RemediationJobStatus.WAITING_CAPTCHA.value, message="Waiting CAPTCHA/manual"
                )
            elif any(i.status == BrokerOptOutStatus.MANUAL_NEEDED.value for i in waiting):
                await self.repo.set_job_status(
                    job, RemediationJobStatus.WAITING_MANUAL.value, message="Waiting manual"
                )
            await self.session.commit()
            return

        submitted = sum(
            1
            for i in items
            if i.status
            in {
                BrokerOptOutStatus.SUBMITTED.value,
                BrokerOptOutStatus.VERIFIED_REMOVED.value,
                BrokerOptOutStatus.SKIPPED_FRESH.value,
                BrokerOptOutStatus.NOT_LISTED.value,
            }
        )
        errors = sum(1 for i in items if i.status in {BrokerOptOutStatus.ERROR.value, BrokerOptOutStatus.DEAD.value})
        if errors and submitted:
            final = RemediationJobStatus.PARTIAL.value
        elif errors and not submitted:
            final = RemediationJobStatus.FAILED.value
        else:
            final = RemediationJobStatus.COMPLETED.value

        summary = {
            "submitted_or_ok": submitted,
            "errors": errors,
            "total": len(items),
            "attribution": "Remediation strategies inspired by AIDR (auto-identity-remove)",
        }
        await self.repo.set_job_status(
            job, final, message=f"Finished: {final}", result_summary=summary, progress_pct=100.0
        )
        await self.audit.log(
            "remediation.job_finished",
            user_id=job.user_id,
            resource_type="remediation_job",
            resource_id=str(job.id),
            details=summary,
        )
        await self.session.commit()

        # Closed-loop re-score
        if self.settings.remediation_auto_rescore and not job.dry_run:
            try:
                from app.services.scoring_service import ScoringService
                from app.services.recommendation_service import RecommendationService

                scoring = ScoringService(self.session)
                await scoring.compute(
                    job.user_id,
                    identifier_id=job.identifier_id,
                    persist=True,
                    trigger="post_remediation",
                )
                recs = RecommendationService(self.session)
                await recs.generate(job.user_id, identifier_id=job.identifier_id, persist=True)
            except Exception:
                logger.exception("post_remediation_rescore_failed", job_id=str(job.id))

    async def solve_captcha(
        self,
        user_id: uuid.UUID,
        captcha_id: uuid.UUID,
        *,
        action: str,
        solution_token: str | None = None,
    ):
        await self._set_rls(user_id)
        cap = await self.repo.get_captcha(captcha_id, user_id)
        if not cap:
            raise HTTPException(status_code=404, detail="Captcha item not found")
        if cap.status != "pending":
            raise HTTPException(status_code=400, detail="Captcha not pending")
        if cap.expires_at < datetime.now(timezone.utc):
            cap.status = "expired"
            await self.session.flush()
            await self.session.commit()
            raise HTTPException(status_code=400, detail="Captcha expired")

        if action == "skip":
            cap.status = "skipped"
            await self.session.flush()
            await self.session.commit()
            return {"message": "Skipped"}

        cap.status = "solved"
        cap.solution_token = solution_token
        cap.solved_at = datetime.now(timezone.utc)
        await self.session.flush()

        # Resume item as pending for re-run with token (token stored on captcha row)
        job = await self.repo.get_job(cap.job_id, user_id)
        if job and cap.job_item_id:
            for item in job.items or []:
                if item.id == cap.job_item_id:
                    # Re-queue item
                    item.status = BrokerOptOutStatus.PENDING.value
                    item.finished_at = None
                    if solution_token:
                        item.result_meta = {**(item.result_meta or {}), "captcha_token_present": True}
                    break
            await self.repo.set_job_status(job, RemediationJobStatus.PENDING.value, message="Resuming after captcha")
            await self.session.commit()
            from app.tasks.remediation_tasks import execute_remediation_job_task

            execute_remediation_job_task.delay(str(job.id))
        else:
            await self.session.commit()
        return {"message": "Captcha recorded; job re-queued"}

    async def complete_manual_item(
        self, user_id: uuid.UUID, job_id: uuid.UUID, item_id: uuid.UUID, status: str, detail: str | None
    ):
        await self._set_rls(user_id)
        job = await self.repo.get_job(job_id, user_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        item = next((i for i in (job.items or []) if i.id == item_id), None)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        map_status = {
            "submitted": BrokerOptOutStatus.SUBMITTED.value,
            "manual_needed": BrokerOptOutStatus.MANUAL_NEEDED.value,
            "skipped": BrokerOptOutStatus.SKIPPED_FRESH.value,
            "error": BrokerOptOutStatus.ERROR.value,
        }[status]
        await self.repo.set_item_status(item, map_status, detail=detail)
        await self.repo.upsert_state(
            user_id=user_id,
            broker_id=item.broker_id,
            broker_name=item.broker_name,
            status=map_status,
            identifier_id=job.identifier_id,
            detail=detail,
            success=map_status == BrokerOptOutStatus.SUBMITTED.value,
        )
        await self.repo.recompute_job_progress(job)
        await self.session.commit()
        # Try finalize via re-execute finalize path
        await self.execute_job(job_id)
        return await self.repo.get_job(job_id, user_id)

    async def ensure_freeze_checklist(self, user_id: uuid.UUID):
        await self._set_rls(user_id)
        rows = await self.repo.upsert_freeze_seed(user_id, freeze_targets())
        await self.session.commit()
        return rows

    async def update_freeze(self, user_id: uuid.UUID, item_id: uuid.UUID, status: str, notes: str | None):
        await self._set_rls(user_id)
        row = await self.repo.get_freeze(item_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Freeze item not found")
        row.status = status
        if notes is not None:
            row.notes = notes
        if status == "done":
            row.completed_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.audit.log(
            "remediation.freeze_updated",
            user_id=user_id,
            resource_type="freeze_item",
            resource_id=str(item_id),
            details={"status": status},
        )
        await self.session.commit()
        return row

    async def create_know_request(
        self,
        user_id: uuid.UUID,
        *,
        regime: str,
        recipient_name: str,
        recipient_email: str | None,
        identifier_id: uuid.UUID | None,
        include_deletion: bool,
    ):
        await self._set_rls(user_id)
        idents = await self.identifiers.list_for_user(user_id)
        email = next((i.value_canonical for i in idents if i.type == "email" and i.is_verified), None)
        if identifier_id:
            ident = await self._require_verified_identifier(user_id, identifier_id)
            if ident.type == "email":
                email = ident.value_canonical
        if not email:
            raise HTTPException(status_code=400, detail="Verified email required")
        name = (await self.repo.list_freeze(user_id) and "User") or "User"
        # Prefer profile from freeze notes — use email local as fallback name
        full_name = email.split("@")[0]
        gen = generate_right_to_know(
            regime=regime,
            full_name=full_name,
            email=email,
            recipient_name=recipient_name,
            include_deletion=include_deletion,
        )
        row = await self.repo.create_generated(
            user_id=user_id,
            kind="right_to_know" if not include_deletion else "deletion",
            regime=regime,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            subject=gen["subject"],
            body=gen["body"],
            meta=gen["meta"],
            status="draft",
            deadline_at=gen["deadline_at"],
        )
        await self.session.commit()
        return row

    async def create_complaint(
        self,
        user_id: uuid.UUID,
        *,
        regime: str,
        recipient_name: str,
        regulator: str,
        facts: str,
        original_request_id: uuid.UUID | None,
    ):
        await self._set_rls(user_id)
        idents = await self.identifiers.list_for_user(user_id)
        email = next((i.value_canonical for i in idents if i.type == "email" and i.is_verified), "user@example.com")
        full_name = email.split("@")[0]
        if original_request_id:
            orig = await self.repo.get_generated(original_request_id, user_id)
            if orig and orig.deadline_at and orig.deadline_at > datetime.now(timezone.utc):
                # still allow generate but flag
                facts = facts + "\n\n[Note: original request deadline may not have passed yet.]"
        gen = generate_complaint(
            regime=regime,
            full_name=full_name,
            email=email,
            recipient_name=recipient_name,
            regulator=regulator,
            facts=facts,
        )
        row = await self.repo.create_generated(
            user_id=user_id,
            kind="complaint",
            regime=regime,
            recipient_name=recipient_name,
            recipient_email=None,
            subject=gen["subject"],
            body=gen["body"],
            meta=gen["meta"],
            status="draft",
        )
        await self.session.commit()
        return row

    async def mark_request_sent(self, user_id: uuid.UUID, req_id: uuid.UUID):
        await self._set_rls(user_id)
        row = await self.repo.get_generated(req_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Request not found")
        row.status = "sent_marked"
        row.sent_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.commit()
        return row

    async def verify_brokers(self, user_id: uuid.UUID, broker_ids: list[str] | None = None):
        """AIDR verify — re-check selected brokers."""
        await self._set_rls(user_id)
        states = await self.repo.list_states(user_id)
        if broker_ids:
            states = [s for s in states if s.broker_id in set(broker_ids)]
        else:
            states = [s for s in states if s.last_success_at is not None]
        idents = await self.identifiers.list_for_user(user_id)
        profile = build_profile_from_identifiers(
            [
                {"type": i.type, "value_canonical": i.value_canonical, "is_verified": i.is_verified}
                for i in idents
            ]
        )
        results = []
        for st in states:
            broker = get_broker(st.broker_id)
            if not broker:
                continue
            v = await self.runner.verify_not_listed(broker, profile, user_scope=str(user_id))
            await self.repo.upsert_state(
                user_id=user_id,
                broker_id=st.broker_id,
                broker_name=st.broker_name,
                status=v.status,
                detail=v.detail,
                meta=v.to_dict(),
                verified=True,
            )
            results.append({"broker_id": st.broker_id, **v.to_dict()})
        await self.session.commit()
        return {"results": results}

    async def list_brokers_catalog(self):
        return {
            "brokers": list_green_brokers(enabled_only=False),
            "attribution": "Green subset; strategies inspired by AIDR auto-identity-remove",
        }
```

---

## 14. NEW: `backend/app/tasks/remediation_tasks.py`

```python
from __future__ import annotations

import asyncio
import uuid

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


async def _execute_job_async(job_id: str) -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.remediation_service import RemediationService

    async with AsyncSessionLocal() as session:
        svc = RemediationService(session)
        try:
            await svc.execute_job(uuid.UUID(job_id))
        except Exception:
            logger.exception("remediation_job_failed", job_id=job_id)
            await session.rollback()
            raise


@celery_app.task(
    name="app.tasks.remediation_tasks.execute_remediation_job_task",
    bind=True,
    max_retries=1,
    time_limit=7200,
)
def execute_remediation_job_task(self, job_id: str) -> str:
    logger.info("execute_remediation_job_start", job_id=job_id)
    _run_async(_execute_job_async(job_id))
    return f"done:{job_id}"


@celery_app.task(name="app.tasks.remediation_tasks.update_brokers_task")
def update_brokers_task() -> dict:
    """
    Best-effort refresh of public broker registry notes.
    Full CA SB 362 / Vermont scrape can be expanded; MVP logs intent + clears cache.
    """
    from app.remediation.broker_registry import clear_registry_cache, load_broker_registry

    clear_registry_cache()
    reg = load_broker_registry()
    logger.info(
        "update_brokers_done",
        version=reg.get("registry_version"),
        count=len(reg.get("brokers") or []),
    )
    return {
        "registry_version": reg.get("registry_version"),
        "broker_count": len(reg.get("brokers") or []),
        "note": "MVP: reloaded local Green registry. Extend with CA SB 362 / Vermont free pulls later.",
    }
```

---

## 15. UPDATE: `backend/app/worker.py`

```python
    include=[
        "app.tasks",
        "app.tasks.discovery_tasks",
        "app.tasks.alert_tasks",
        "app.tasks.remediation_tasks",
    ],
...
    beat_schedule={
        "reconcile-scans": { ... },
        "reconcile-alerts-rescans": { ... },
        "update-brokers": {
            "task": "app.tasks.remediation_tasks.update_brokers_task",
            "schedule": float(settings.update_brokers_interval_hours * 3600),
        },
    },
```

Also add optional docker-compose service:

```yaml
  remediation-worker:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile
    command: celery -A app.worker.celery_app worker --loglevel=INFO --concurrency=1 -Q celery
    env_file: [.env]
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-digizafe}:${POSTGRES_PASSWORD:-digizafe_dev_password}@postgres:5432/${POSTGRES_DB:-digizafe}
      REDIS_BROKER_URL: redis://redis-broker:6379/0
      REDIS_CACHE_URL: redis://redis-cache:6379/0
      CELERY_BROKER_URL: redis://redis-broker:6379/0
      CELERY_RESULT_BACKEND: redis://redis-broker:6379/1
      PLAYWRIGHT_HEADLESS: "true"
    volumes:
      - ./backend:/app/backend
      - ./shared:/app/shared
      - ./secrets:/app/secrets
    depends_on:
      postgres:
        condition: service_healthy
      redis-broker:
        condition: service_healthy
    networks: [digizafe]
    # same image as worker if Playwright installed in Dockerfile
```

---

## 16. NEW: `backend/app/api/v1/remediation.py`

```python
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.remediation import (
    BrokerOptOutStart,
    RemediationJobPublic,
    BrokerStatePublic,
    CaptchaPublic,
    CaptchaSolveRequest,
    ManualItemComplete,
    FreezeItemUpdate,
    FreezeItemPublic,
    KnowRequestCreate,
    ComplaintCreate,
    GeneratedRequestPublic,
    MarkSentRequest,
    VerifyBrokersRequest,
    Message,
)
from app.services.remediation_service import RemediationService

router = APIRouter(prefix="/remediation", tags=["remediation"])


def _svc(db: AsyncSession = Depends(get_db)) -> RemediationService:
    return RemediationService(db)


@router.get("/brokers")
async def catalog(current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    return await svc.list_brokers_catalog()


@router.get("/state", response_model=list[BrokerStatePublic])
async def broker_state(current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    """AIDR state.json equivalent — per-broker opt-out history."""
    rows = await svc.list_broker_states(current_user.id)
    return [BrokerStatePublic.model_validate(r) for r in rows]


@router.post("/jobs/broker-optout", response_model=RemediationJobPublic, status_code=201)
async def start_optout(
    body: BrokerOptOutStart,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    """
    Start Green broker opt-out job (Playwright in worker).
    Free CAPTCHA path: waiting_captcha → user solves → resume.
    """
    p = body.profile
    job = await svc.start_broker_optout(
        current_user.id,
        identifier_id=body.identifier_id,
        broker_ids=body.broker_ids,
        dry_run=body.dry_run,
        display_name=p.display_name if p else None,
        state=p.state if p else None,
        city=p.city if p else None,
        zip_code=p.zip if p else None,
        recommendation_id=body.recommendation_id,
    )
    return RemediationJobPublic.model_validate(job)


@router.get("/jobs", response_model=list[RemediationJobPublic])
async def list_jobs(current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    rows = await svc.list_jobs(current_user.id)
    # items not always loaded — return without nested if needed
    return [
        RemediationJobPublic.model_validate(r) if getattr(r, "items", None) is not None else RemediationJobPublic(
            id=r.id,
            identifier_id=r.identifier_id,
            job_type=r.job_type,
            status=r.status,
            dry_run=r.dry_run,
            broker_ids=r.broker_ids,
            progress_pct=r.progress_pct,
            message=r.message,
            error=r.error,
            result_summary=r.result_summary,
            deadline_at=r.deadline_at,
            started_at=r.started_at,
            finished_at=r.finished_at,
            created_at=r.created_at,
            items=[],
        )
        for r in rows
    ]


@router.get("/jobs/{job_id}", response_model=RemediationJobPublic)
async def get_job(job_id: UUID, current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    job = await svc.get_job(current_user.id, job_id)
    return RemediationJobPublic.model_validate(job)


@router.post("/jobs/{job_id}/cancel", response_model=RemediationJobPublic)
async def cancel_job(job_id: UUID, current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    job = await svc.cancel_job(current_user.id, job_id)
    return RemediationJobPublic.model_validate(job)


@router.post("/jobs/{job_id}/items/{item_id}/manual", response_model=RemediationJobPublic)
async def complete_manual(
    job_id: UUID,
    item_id: UUID,
    body: ManualItemComplete,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    job = await svc.complete_manual_item(
        current_user.id, job_id, item_id, body.status, body.detail
    )
    return RemediationJobPublic.model_validate(job)


@router.get("/captcha", response_model=list[CaptchaPublic])
async def list_captcha(current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    from app.repositories.remediation_repository import RemediationRepository

    await svc._set_rls(current_user.id)
    rows = await RemediationRepository(svc.session).list_pending_captchas(current_user.id)
    return [CaptchaPublic.model_validate(r) for r in rows]


@router.post("/captcha/{captcha_id}")
async def solve_captcha(
    captcha_id: UUID,
    body: CaptchaSolveRequest,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    return await svc.solve_captcha(
        current_user.id,
        captcha_id,
        action=body.action,
        solution_token=body.solution_token,
    )


@router.get("/freeze", response_model=list[FreezeItemPublic])
async def get_freeze(current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    rows = await svc.ensure_freeze_checklist(current_user.id)
    return [FreezeItemPublic.model_validate(r) for r in rows]


@router.patch("/freeze/{item_id}", response_model=FreezeItemPublic)
async def patch_freeze(
    item_id: UUID,
    body: FreezeItemUpdate,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    row = await svc.update_freeze(current_user.id, item_id, body.status, body.notes)
    return FreezeItemPublic.model_validate(row)


@router.post("/know", response_model=GeneratedRequestPublic, status_code=201)
async def create_know(
    body: KnowRequestCreate,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    row = await svc.create_know_request(
        current_user.id,
        regime=body.regime,
        recipient_name=body.recipient_name,
        recipient_email=str(body.recipient_email) if body.recipient_email else None,
        identifier_id=body.identifier_id,
        include_deletion=body.include_deletion,
    )
    return GeneratedRequestPublic.model_validate(row)


@router.post("/complaints", response_model=GeneratedRequestPublic, status_code=201)
async def create_complaint(
    body: ComplaintCreate,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    row = await svc.create_complaint(
        current_user.id,
        regime=body.regime,
        recipient_name=body.recipient_name,
        regulator=body.regulator,
        facts=body.facts,
        original_request_id=body.original_request_id,
    )
    return GeneratedRequestPublic.model_validate(row)


@router.get("/requests", response_model=list[GeneratedRequestPublic])
async def list_requests(
    current_user: CurrentUser,
    kind: Optional[str] = None,
    svc: RemediationService = Depends(_svc),
):
    from app.repositories.remediation_repository import RemediationRepository

    await svc._set_rls(current_user.id)
    rows = await RemediationRepository(svc.session).list_generated(current_user.id, kind=kind)
    return [GeneratedRequestPublic.model_validate(r) for r in rows]


@router.post("/requests/{req_id}/mark-sent", response_model=GeneratedRequestPublic)
async def mark_sent(
    req_id: UUID,
    body: MarkSentRequest,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    row = await svc.mark_request_sent(current_user.id, req_id)
    return GeneratedRequestPublic.model_validate(row)


@router.post("/verify")
async def verify(
    body: VerifyBrokersRequest,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    return await svc.verify_brokers(current_user.id, broker_ids=body.broker_ids)
```

---

## 17. UPDATE: `backend/app/main.py`

```python
from app.api.v1 import (
    health, auth, identifiers, connectors, scans, identity, scores,
    recommendations, alerts, remediation,
)

app.include_router(remediation.router, prefix=settings.api_v1_prefix)

# root
"version": "0.7.0",
"message": "DigiZafe Sprint 7 Remediation Engine (AIDR core) — ready",
```

---

## 18. Alembic migration `sprint7_remediation_engine`

```python
"""sprint7_remediation_engine"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "sprint7_rem_001"
down_revision: Union[str, None] = "sprint6_rec_001"  # ← your Sprint 6 rev
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broker_optout_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("broker_id", sa.String(64), nullable=False),
        sa.Column("broker_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(48), nullable=False, server_default="pending"),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "broker_id", name="uq_broker_optout_user_broker"),
    )
    op.create_index("ix_broker_optout_state_user_id", "broker_optout_state", ["user_id"])
    op.create_index("ix_broker_optout_state_broker_id", "broker_optout_state", ["broker_id"])
    op.create_index("ix_broker_optout_state_status", "broker_optout_state", ["status"])

    op.create_table(
        "remediation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_type", sa.String(64), nullable=False, server_default="broker_optout"),
        sa.Column("status", sa.String(48), nullable=False, server_default="pending"),
        sa.Column("dry_run", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("broker_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("progress_pct", sa.Float(), server_default="0", nullable=False),
        sa.Column("message", sa.String(512), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("profile_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_remediation_jobs_user_id", "remediation_jobs", ["user_id"])
    op.create_index("ix_remediation_jobs_status", "remediation_jobs", ["status"])

    op.create_table(
        "remediation_job_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("remediation_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("broker_id", sa.String(64), nullable=False),
        sa.Column("broker_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(48), nullable=False, server_default="pending"),
        sa.Column("skip_reason", sa.String(64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("result_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_remediation_job_items_job_id", "remediation_job_items", ["job_id"])
    op.create_index("ix_remediation_job_items_status", "remediation_job_items", ["status"])

    op.create_table(
        "captcha_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("remediation_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("broker_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("page_url", sa.String(1024), nullable=True),
        sa.Column("captcha_type", sa.String(64), nullable=False, server_default="unknown"),
        sa.Column("sitekey", sa.String(256), nullable=True),
        sa.Column("solution_token", sa.Text(), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_captcha_queue_user_id", "captcha_queue", ["user_id"])
    op.create_index("ix_captcha_queue_status", "captcha_queue", ["status"])

    op.create_table(
        "freeze_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=False),
        sa.Column("label", sa.String(256), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="todo"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "target_id", name="uq_freeze_user_target"),
    )

    op.create_table(
        "generated_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("regime", sa.String(32), nullable=False, server_default="ccpa"),
        sa.Column("recipient_name", sa.String(256), nullable=True),
        sa.Column("recipient_email", sa.String(320), nullable=True),
        sa.Column("subject", sa.String(512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_generated_requests_user_id", "generated_requests", ["user_id"])
    op.create_index("ix_generated_requests_kind", "generated_requests", ["kind"])

    for table in (
        "broker_optout_state",
        "remediation_jobs",
        "remediation_job_items",
        "captcha_queue",
        "freeze_checklist_items",
        "generated_requests",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_self ON {table}
            FOR ALL
            USING (user_id::text = current_setting('app.current_user_id', true))
            WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
        """)


def downgrade() -> None:
    for table in (
        "generated_requests",
        "freeze_checklist_items",
        "captcha_queue",
        "remediation_job_items",
        "remediation_jobs",
        "broker_optout_state",
    ):
        op.execute(f"DROP POLICY IF EXISTS {table}_self ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
```

Update `alembic/env.py` to import remediation models.

---

## 19. Unit tests

### `backend/tests/unit/test_remediation_states.py`

```python
import pytest
from app.domain.remediation_states import (
    transition_job,
    RemediationJobStatus,
    InvalidTransition,
    is_fresh_optout,
)


def test_job_running_to_completed():
    assert transition_job(RemediationJobStatus.RUNNING, RemediationJobStatus.COMPLETED) == RemediationJobStatus.COMPLETED


def test_invalid_terminal():
    with pytest.raises(InvalidTransition):
        transition_job(RemediationJobStatus.COMPLETED, RemediationJobStatus.RUNNING)


def test_fresh_optout():
    from datetime import datetime, timezone, timedelta
    last = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    assert is_fresh_optout(last, 90) is True
    old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    assert is_fresh_optout(old, 90) is False
```

### `backend/tests/unit/test_know_templates.py`

```python
from app.remediation.generators.templates import generate_right_to_know, generate_complaint


def test_ccpa_know():
    g = generate_right_to_know(
        regime="ccpa",
        full_name="Ada Lovelace",
        email="ada@example.com",
        recipient_name="Example Broker",
        include_deletion=True,
    )
    assert "CCPA" in g["subject"] or "California" in g["subject"]
    assert "ada@example.com" in g["body"]
    assert g["deadline_at"] is not None


def test_complaint():
    g = generate_complaint(
        regime="ccpa",
        full_name="Ada",
        email="a@b.com",
        recipient_name="BrokerCo",
        regulator="ca_ag",
        facts="No response after 45 days.",
    )
    assert "complaint" in g["subject"].lower() or "CCPA" in g["subject"]
```

### `backend/tests/unit/test_remediation_profile.py`

```python
from app.domain.remediation_profile import build_profile_from_identifiers


def test_only_verified_email():
    p = build_profile_from_identifiers(
        [
            {"type": "email", "value_canonical": "a@b.com", "is_verified": True},
            {"type": "email", "value_canonical": "x@y.com", "is_verified": False},
        ],
        display_name="Jane Doe",
        state="CA",
    )
    assert p.email == "a@b.com"
    assert p.first_name == "Jane"
    assert p.state == "CA"
```

---

## 20. Docs

### `docs/runbooks/remediation.md`

```markdown
# Remediation Engine (Sprint 7) — AIDR core

## AIDR → DigiZafe map

| AIDR | DigiZafe |
|------|----------|
| state.json optOuts | `broker_optout_state` (+ RLS) |
| brokers.js | `shared/config/broker_registry/brokers_green.json` + Playwright runner |
| CapSolver | Optional FEATURE_CAPSOLVER; default **manual / open_in_browser** |
| aidr verify | `POST /remediation/verify` |
| aidr freeze | `GET/PATCH /remediation/freeze` |
| aidr know | `POST /remediation/know` |
| aidr complaints | `POST /remediation/complaints` |
| aidr update-brokers | beat `update_brokers_task` |
| aidr run / preview | `POST /remediation/jobs/broker-optout` (`dry_run=true` = preview) |
| Closed loop score | post-job PDSS + recommendations regenerate |

## Free CAPTCHA path
1. Job item → `captcha_needed`
2. `GET /remediation/captcha` for instructions + page_url
3. User completes form in browser OR posts token
4. `POST /remediation/captcha/{id}` `{ "action": "manual_done" }` or `solve`
5. Job resumes in worker

## Flow
1. Verify email (Sprint 2)
2. Generate plan (Sprint 6) → `broker_optout_green`
3. `POST /remediation/jobs/broker-optout` with verified `identifier_id` + profile name/state
4. Poll job; handle captcha/manual
5. `GET /remediation/state` for durable opt-out history (90-day fresh skip)
6. Auto re-score when job completes

## Safety
- G1 verified identifier only
- Green brokers only for automation
- Playwright only in worker
- Consent + egress ledger on broker runs
- CapSolver never required
```

### UPDATE `docs/aidr-mapping.md`

```markdown
| AIDR Component | DigiZafe Sprint 7 |
|----------------|-------------------|
| state.json | broker_optout_state |
| brokers.js + generic runner | brokers_green.json + playwright_runner.py |
| CapSolver | optional feature flag; free manual path default |
| aidr verify | RemediationService.verify_brokers |
| aidr freeze | freeze_checklist_items |
| aidr know / complaints | generated_requests + templates.py |
| aidr update-brokers | update_brokers_task |
| Closed loop | post_remediation PDSS + plan regenerate |
| HIBP in AIDR | XposedOrNot primary (already Sprint 3–5) |
```

---

# PART C — How to finish Sprint 7

```bash
# 1. Copy brokers_green.json → shared/config/broker_registry/
# 2. Add playwright to pyproject + Dockerfile install chromium
# 3. Merge .env (FEATURE_CAPSOLVER=false)
# 4. Rebuild workers with Playwright deps
docker compose build api worker beat
docker compose up -d
docker compose exec api alembic upgrade head

# 5. Install playwright browsers inside container if needed
docker compose exec worker playwright install chromium

# 6. Smoke — verified email $ID
export ACCESS=...
export ID=...

# Catalog
curl -s http://localhost:8000/api/v1/remediation/brokers -H "Authorization: Bearer $ACCESS" | jq .

# Dry-run preview (AIDR preview lineage)
curl -s -X POST http://localhost:8000/api/v1/remediation/jobs/broker-optout \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d "{\"identifier_id\":\"$ID\",\"dry_run\":true,\"broker_ids\":[\"familytreenow\",\"thatsthem\"],\"profile\":{\"display_name\":\"Test User\",\"state\":\"CA\"}}" | jq .

# Real job (small set)
curl -s -X POST http://localhost:8000/api/v1/remediation/jobs/broker-optout \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d "{\"identifier_id\":\"$ID\",\"broker_ids\":[\"familytreenow\"],\"profile\":{\"display_name\":\"Test User\",\"state\":\"CA\"}}" | jq .

# State + freeze + know
curl -s http://localhost:8000/api/v1/remediation/state -H "Authorization: Bearer $ACCESS" | jq .
curl -s http://localhost:8000/api/v1/remediation/freeze -H "Authorization: Bearer $ACCESS" | jq .
curl -s -X POST http://localhost:8000/api/v1/remediation/know \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d '{"regime":"ccpa","recipient_name":"Example Broker Inc","include_deletion":true}' | jq .

# Unit tests
docker compose exec api pytest backend/tests/unit/test_remediation_states.py \
  backend/tests/unit/test_know_templates.py \
  backend/tests/unit/test_remediation_profile.py -v

git add .
git commit -m "feat(sprint-7): AIDR remediation — Playwright runners, broker_optout_state, captcha free path, freeze/know/complaints, verify, closed-loop rescore"
```

---

# Sprint 7 Definition of Done Checklist

- [ ] MASTER_ENGINEERING_CONTEXT.md respected  
- [ ] AIDR attributed; re-implemented under DigiZafe layering  
- [ ] `broker_optout_state` with 90-day fresh skip (state.json lineage)  
- [ ] Green broker registry JSON + catalog API  
- [ ] Remediation jobs + items state machine; worker-only Playwright  
- [ ] Free CAPTCHA path: queue + manual_done / open_in_browser (CapSolver optional only)  
- [ ] dry_run = AIDR preview (fill, no submit)  
- [ ] Verify loop (`POST /remediation/verify`)  
- [ ] Freeze checklist (AIDR freeze targets)  
- [ ] Right-to-know + complaint generators  
- [ ] update-brokers beat task (local registry reload MVP)  
- [ ] Consent + egress ledger on broker runs  
- [ ] G1: verified identifier required  
- [ ] Closed-loop: post-job PDSS recompute + recommendation regenerate  
- [ ] RLS on all new tables  
- [ ] Unit tests green for states / templates / profile  
- [ ] Zero paid keys required for core path  

→ **Sprint 7 complete.**  
Next: **Sprint 8 — Privacy, Rights, Explain backend** (export, crypto-shred+purge, consent center, audit, counterfactual + grounded narrative Ollama).

---

## Endpoint quick reference

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | /api/v1/remediation/brokers | Bearer | Green broker catalog |
| GET | /api/v1/remediation/state | Bearer | Opt-out state (AIDR state.json) |
| POST | /api/v1/remediation/jobs/broker-optout | Bearer | Start job (`dry_run` = preview) |
| GET | /api/v1/remediation/jobs | Bearer | List jobs |
| GET | /api/v1/remediation/jobs/{id} | Bearer | Job + items |
| POST | /api/v1/remediation/jobs/{id}/cancel | Bearer | Cancel |
| POST | /api/v1/remediation/jobs/{id}/items/{item_id}/manual | Bearer | Complete manual item |
| GET | /api/v1/remediation/captcha | Bearer | Pending CAPTCHA/manual queue |
| POST | /api/v1/remediation/captcha/{id} | Bearer | Solve / skip / manual_done |
| GET | /api/v1/remediation/freeze | Bearer | Freeze checklist |
| PATCH | /api/v1/remediation/freeze/{id} | Bearer | Update freeze item |
| POST | /api/v1/remediation/know | Bearer | Generate right-to-know / deletion letter |
| POST | /api/v1/remediation/complaints | Bearer | Generate complaint |
| GET | /api/v1/remediation/requests | Bearer | List generated letters |
| POST | /api/v1/remediation/requests/{id}/mark-sent | Bearer | Mark sent (deadline tracking) |
| POST | /api/v1/remediation/verify | Bearer | Re-verify broker removals |

---

## File checklist (create/update)

| Action | Path |
|--------|------|
| UPDATE | `.env.example`, `config.py`, `main.py`, `worker.py`, `models/__init__.py`, `alembic/env.py`, `pyproject.toml`, `Dockerfile` |
| NEW | `shared/config/broker_registry/brokers_green.json` |
| NEW | `backend/app/domain/remediation_states.py` |
| NEW | `backend/app/domain/remediation_profile.py` |
| NEW | `backend/app/models/remediation.py` |
| NEW | `backend/app/schemas/remediation.py` |
| NEW | `backend/app/remediation/broker_registry.py` |
| NEW | `backend/app/remediation/runners/playwright_runner.py` |
| NEW | `backend/app/remediation/generators/templates.py` |
| NEW | `backend/app/repositories/remediation_repository.py` |
| NEW | `backend/app/services/remediation_service.py` |
| NEW | `backend/app/tasks/remediation_tasks.py` |
| NEW | `backend/app/api/v1/remediation.py` |
| NEW | migration `sprint7_remediation_engine` |
| NEW | unit tests + `docs/runbooks/remediation.md` + aidr-mapping update |
| OPTIONAL | `remediation-worker` compose service |

---

**You are ready for Sprint 7.**  
1. Save this file as `Sprint7.md` next to Sprint0–6.  
2. Apply files in order; set `down_revision` to your Sprint 6 revision id.  
3. Install Playwright Chromium in the worker image.  
4. Dry-run opt-out → real job → handle captcha/manual → check state + post-job score.  
5. Commit when DoD is green.

When Sprint 7 is green, ask for **Sprint 8** the same way.