# DigiZafe — Sprint 8 Privacy, Rights, Explain backend
**Complete Implementation Guide from Sprint 7 Baseline + All File Contents**

**Document version:** 1.0  
**Based on:** MASTER_ENGINEERING_CONTEXT.md v2.1  
**Depends on:** Sprint 0–7 green (Auth, Identifiers, Connectors, Discovery, PDSS, Recommendations, Remediation AIDR core)  
**Goal:** From completed Sprint 7 → **privacy rights backend**: machine-readable **data export**, **crypto-shred + purge**, **consent center**, **user-facing audit**, **counterfactual explainability API**, and **grounded narrative briefings** (local Ollama preferred; deterministic fallback).

**Effort estimate:** ~8 days (solo)  
**Critical path next:** Sprint 9 Frontend Core  

> **Load MASTER_ENGINEERING_CONTEXT.md first.**  
> G6 privacy by design: no raw dumps; short-TTL evidence; crypto-shred; consented egress only.  
> Grounded narratives must use only durable score/finding facts — no hallucinated breaches.  
> Zero paid keys. Ollama is free/local and optional.

---

# PART A — Pre-Sprint 8

```bash
# 1. Confirm Sprint 7 green
docker compose ps
curl -s http://localhost:8000/api/v1/health | jq .
# Need: auth, verified ID, scores, remediation endpoints

# 2. Package dirs
mkdir -p backend/app/{domain,services,repositories,models,schemas,tasks}
mkdir -p backend/app/services/privacy
mkdir -p docs/runbooks docs/ethics
mkdir -p backend/tests/unit
touch backend/app/services/privacy/__init__.py

# 3. Optional: ollama client (HTTP via httpx also fine — prefer httpx to avoid hard dep)
# Add to pyproject if you want the official client:
#   "ollama>=0.3.0",
# Core path uses httpx → http://ollama:11434 (or host.docker.internal)

docker compose build api worker beat
echo "✅ Pre-Sprint 8 ready"
```

**Optional docker-compose service for Ollama (profile):**

```yaml
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - digizafe
    profiles:
      - with-ollama
# volumes: ollama_data:
# docker compose --profile with-ollama up -d
# docker compose exec ollama ollama pull llama3.2:3b
```

---

# PART B — Sprint 8 File Contents

---

## 1. UPDATE: `.env.example` (append)

```bash
# === Sprint 8: Privacy, Rights, Explain ===
FEATURE_DATA_EXPORT=true
FEATURE_CRYPTO_SHRED=true
FEATURE_GROUNDED_NARRATIVE=true

# Export
EXPORT_MAX_BYTES=52428800
EXPORT_INCLUDE_AUDIT=true
EXPORT_INCLUDE_EGRESS=true

# Account deletion / crypto-shred
ACCOUNT_DELETE_GRACE_HOURS=24
# In development allow immediate shred with confirm phrase
ACCOUNT_DELETE_DEV_IMMEDIATE=true
ACCOUNT_DELETE_CONFIRM_PHRASE=DELETE MY DIGIZAFE ACCOUNT

# Groq grounded narrative (free/fast)
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
NARRATIVE_TIMEOUT_SECONDS=60
NARRATIVE_ENABLED=true
# If Groq unreachable → deterministic template narrative still returned

# Narrative policy
NARRATIVE_MAX_FINDINGS=15
NARRATIVE_MAX_TOKENS=800
NARRATIVE_TEMPERATURE=0.2
```

---

## 2. UPDATE: `backend/app/core/config.py`

Add to `Settings`:

```python
    # === Sprint 8: Privacy / Rights / Explain ===
    feature_data_export: bool = True
    feature_crypto_shred: bool = True
    feature_grounded_narrative: bool = True

    export_max_bytes: int = 52_428_800
    export_include_audit: bool = True
    export_include_egress: bool = True

    account_delete_grace_hours: int = 24
    account_delete_dev_immediate: bool = True
    account_delete_confirm_phrase: str = "DELETE MY DIGIZAFE ACCOUNT"

    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    narrative_timeout_seconds: float = 60.0
    narrative_enabled: bool = True

    narrative_max_findings: int = 15
    narrative_max_tokens: int = 800
    narrative_temperature: float = 0.2
```

---

## 3. NEW: `backend/app/domain/privacy_export.py`  
*(pure — shape export payload from DTOs)*

```python
"""Pure helpers to build machine-readable personal data export (portability)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def build_export_package(
    *,
    user: dict[str, Any],
    identifiers: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    remediation_state: list[dict[str, Any]],
    consent_records: list[dict[str, Any]],
    audit_logs: list[dict[str, Any]] | None = None,
    egress_ledger: list[dict[str, Any]] | None = None,
    identity_edges: list[dict[str, Any]] | None = None,
    generated_requests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Structured, commonly used, machine-readable format (JSON).
    Secrets (hashed passwords, MFA secrets, refresh tokens) MUST already be excluded by caller.
    """
    return {
        "export_version": "1.0.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "product": "DigiZafe",
        "notice": (
            "This package contains personal data associated with your DigiZafe account. "
            "Raw breach dumps and full HTML evidence are not retained. "
            "Third-party attributions (e.g. XposedOrNot, AIDR lineage) are preserved where present."
        ),
        "subject": {
            "user_id": user.get("id"),
            "email": user.get("email"),
            "is_active": user.get("is_active"),
            "mfa_enabled": user.get("mfa_enabled"),
            "created_at": user.get("created_at"),
            "last_login_at": user.get("last_login_at"),
        },
        "identifiers": identifiers,
        "findings": findings,
        "score_history": scores,
        "recommendations": recommendations,
        "broker_optout_state": remediation_state,
        "identity_edges": identity_edges or [],
        "generated_requests": generated_requests or [],
        "consent_records": consent_records,
        "audit_logs": audit_logs or [],
        "egress_ledger": egress_ledger or [],
        "rights": {
            "export": "GDPR Art.20 / CCPA portability-style machine-readable export",
            "erasure": "Use POST /privacy/account/delete → crypto-shred + purge",
            "consent": "Manage via /privacy/consent",
            "access_audit": "GET /privacy/audit",
        },
    }


def redacted_user_public(user_row: Any) -> dict[str, Any]:
    return {
        "id": str(user_row.id),
        "email": user_row.email,
        "is_active": user_row.is_active,
        "mfa_enabled": user_row.mfa_enabled,
        "created_at": user_row.created_at.isoformat() if user_row.created_at else None,
        "last_login_at": user_row.last_login_at.isoformat() if user_row.last_login_at else None,
    }
```

---

## 4. NEW: `backend/app/domain/narrative.py`  
*(pure — ground truth pack + deterministic fallback template)*

```python
"""Grounded narrative: facts pack + deterministic fallback (no LLM required)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


SYSTEM_PROMPT = """You are DigiZafe's privacy briefing writer.
You ONLY restate facts provided in the FACTS JSON.
Rules:
- Do NOT invent breaches, scores, brokers, or findings not present in FACTS.
- Do NOT claim removal completed unless FACTS say so.
- Prefer clear, calm, actionable language for a non-expert individual.
- Mention XposedOrNot attribution if FACTS include source xposedornot.
- Keep under ~400 words.
- Structure: Summary → Top drivers → What to do first → Closed-loop note.
"""


@dataclass
class FactsPack:
    score_combined: float
    severity: str
    score_confirmed: float
    score_possible: float
    vector: str
    explanation_summary: str
    model_version: str
    contributions: list[dict[str, Any]] = field(default_factory=list)
    counterfactuals: list[dict[str, Any]] = field(default_factory=list)
    attributions: list[str] = field(default_factory=list)
    open_recommendation_titles: list[str] = field(default_factory=list)
    broker_statuses: list[dict[str, str]] = field(default_factory=list)
    identifier_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_combined": self.score_combined,
            "severity": self.severity,
            "score_confirmed": self.score_confirmed,
            "score_possible": self.score_possible,
            "vector": self.vector,
            "explanation_summary": self.explanation_summary,
            "model_version": self.model_version,
            "contributions": self.contributions,
            "counterfactuals": self.counterfactuals,
            "attributions": self.attributions,
            "open_recommendation_titles": self.open_recommendation_titles,
            "broker_statuses": self.broker_statuses,
            "identifier_types": self.identifier_types,
        }


def build_deterministic_narrative(facts: FactsPack) -> str:
    lines: list[str] = []
    lines.append(
        f"## Personal exposure briefing\n\n"
        f"Your current PDSS is **{facts.score_combined:.1f}** ({facts.severity}). "
        f"Confirmed track: {facts.score_confirmed:.1f}; possible track: {facts.score_possible:.1f}. "
        f"Model: `{facts.model_version}`."
    )
    if facts.explanation_summary:
        lines.append(f"\n{facts.explanation_summary}")

    if facts.contributions:
        lines.append("\n### Top drivers")
        for c in facts.contributions[:5]:
            title = c.get("title") or c.get("finding_id")
            src = c.get("source", "?")
            w = c.get("weighted_score", c.get("raw_score", "?"))
            lines.append(f"- [{src}] {title} (weighted contribution ≈ {w})")

    if facts.counterfactuals:
        lines.append("\n### What-if (estimated impact of fixing top items)")
        for cf in facts.counterfactuals[:3]:
            lines.append(f"- {cf.get('narrative') or cf}")

    if facts.open_recommendation_titles:
        lines.append("\n### Suggested next steps (from your plan)")
        for t in facts.open_recommendation_titles[:5]:
            lines.append(f"- {t}")

    if facts.broker_statuses:
        lines.append("\n### Remediation state (sample)")
        for b in facts.broker_statuses[:5]:
            lines.append(f"- {b.get('broker_id')}: {b.get('status')}")

    if facts.attributions:
        lines.append("\n### Data attributions")
        for a in facts.attributions:
            lines.append(f"- {a}")

    lines.append(
        "\n### Closed loop\n"
        "After you change passwords, complete freezes, or finish Green broker opt-outs, "
        "run a rescan and recompute PDSS so the score reflects real-world change. "
        "This briefing uses only stored DigiZafe facts — no external invention."
    )
    return "\n".join(lines)


def user_prompt_from_facts(facts: FactsPack) -> str:
    import json
    return (
        "Write a grounded personal digital exposure briefing from FACTS only.\n\n"
        f"FACTS:\n{json.dumps(facts.to_dict(), default=str)[:12000]}\n"
    )
```

---

## 5. NEW: `backend/app/models/privacy.py`

```python
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DataExportJob(Base):
    __tablename__ = "data_export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    # pending | ready | failed | expired
    include_audit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    include_egress: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Short-lived package stored as JSONB (MVP). Large accounts → object storage later.
    package: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ready_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountDeletionRequest(Base):
    """Right to erasure — grace period then crypto-shred + purge."""

    __tablename__ = "account_deletion_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    # pending | cancelled | shredding | completed | failed
    confirm_phrase_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NarrativeBriefing(Base):
    """Cached grounded narrative for a score snapshot."""

    __tablename__ = "narrative_briefings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_snapshots.id", ondelete="SET NULL"), index=True, nullable=True
    )
    identifier_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)

    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="deterministic")
    # deterministic | ollama
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="Exposure briefing")
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    facts_used: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    grounded: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
```

---

## 6. UPDATE: `backend/app/models/__init__.py`

Add exports for `DataExportJob`, `AccountDeletionRequest`, `NarrativeBriefing`.

---

## 7. NEW: `backend/app/schemas/privacy.py`

```python
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ExportCreateRequest(BaseModel):
    include_audit: bool = True
    include_egress: bool = True


class ExportJobPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    include_audit: bool
    include_egress: bool
    size_bytes: int
    expires_at: datetime
    created_at: datetime
    ready_at: Optional[datetime] = None
    error: Optional[str] = None


class ExportPackageResponse(BaseModel):
    job: ExportJobPublic
    package: Optional[dict[str, Any]] = None


class ConsentItem(BaseModel):
    id: Optional[UUID] = None
    purpose: str
    scope: Optional[str] = None
    granted: bool
    created_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    details: Optional[dict[str, Any]] = None


class ConsentRevokeRequest(BaseModel):
    purpose: str


class ConsentGrantRequest(BaseModel):
    purpose: str
    scope: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class AuditEventPublic(BaseModel):
    id: UUID
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    created_at: datetime
    correlation_id: Optional[str] = None


class EgressEventPublic(BaseModel):
    id: UUID
    purpose: str
    destination_host: str
    method: str
    status_code: Optional[int] = None
    success: bool
    summary: Optional[dict[str, Any]] = None
    created_at: datetime


class AccountDeleteRequest(BaseModel):
    confirm_phrase: str = Field(..., min_length=5)
    immediate: bool = False  # only honored in dev when ACCOUNT_DELETE_DEV_IMMEDIATE


class AccountDeletePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    scheduled_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    error: Optional[str] = None


class NarrativeRequest(BaseModel):
    identifier_id: Optional[UUID] = None
    score_snapshot_id: Optional[UUID] = None
    prefer_ollama: bool = True
    persist: bool = True


class NarrativePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    score_snapshot_id: Optional[UUID] = None
    identifier_id: Optional[UUID] = None
    mode: str
    model_name: Optional[str] = None
    title: str
    body_markdown: str
    grounded: bool
    facts_used: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None


class CounterfactualPublic(BaseModel):
    score_snapshot_id: Optional[UUID] = None
    counterfactuals: list[dict[str, Any]] = []
    explanation_summary: str = ""
    vector: Optional[str] = None
    score_combined: Optional[float] = None


class Message(BaseModel):
    message: str
```

---

## 8. NEW: `backend/app/repositories/privacy_repository.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import select, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.privacy import DataExportJob, AccountDeletionRequest, NarrativeBriefing
from app.models.consent_egress import ConsentRecord, EgressLedger
from app.models.audit import AuditLog


class PrivacyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- export ----
    async def create_export_job(
        self,
        *,
        user_id: uuid.UUID,
        include_audit: bool,
        include_egress: bool,
        ttl_hours: int = 24,
    ) -> DataExportJob:
        row = DataExportJob(
            user_id=user_id,
            status="pending",
            include_audit=include_audit,
            include_egress=include_egress,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_export(self, job_id: uuid.UUID, user_id: uuid.UUID) -> Optional[DataExportJob]:
        r = await self.session.execute(
            select(DataExportJob).where(DataExportJob.id == job_id, DataExportJob.user_id == user_id)
        )
        return r.scalar_one_or_none()

    async def list_exports(self, user_id: uuid.UUID, limit: int = 20) -> Sequence[DataExportJob]:
        r = await self.session.execute(
            select(DataExportJob)
            .where(DataExportJob.user_id == user_id)
            .order_by(DataExportJob.created_at.desc())
            .limit(limit)
        )
        return r.scalars().all()

    async def mark_export_ready(
        self, job: DataExportJob, package: dict[str, Any], size_bytes: int
    ) -> DataExportJob:
        job.status = "ready"
        job.package = package
        job.size_bytes = size_bytes
        job.ready_at = datetime.now(timezone.utc)
        await self.session.flush()
        return job

    async def mark_export_failed(self, job: DataExportJob, error: str) -> None:
        job.status = "failed"
        job.error = error[:2000]
        await self.session.flush()

    # ---- consent ----
    async def list_consents(self, user_id: uuid.UUID) -> Sequence[ConsentRecord]:
        r = await self.session.execute(
            select(ConsentRecord)
            .where(ConsentRecord.user_id == user_id)
            .order_by(ConsentRecord.created_at.desc())
        )
        return r.scalars().all()

    async def revoke_consent(self, user_id: uuid.UUID, purpose: str) -> int:
        r = await self.session.execute(
            select(ConsentRecord).where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.purpose == purpose,
                ConsentRecord.granted.is_(True),
                ConsentRecord.revoked_at.is_(None),
            )
        )
        rows = r.scalars().all()
        now = datetime.now(timezone.utc)
        for row in rows:
            row.granted = False
            row.revoked_at = now
        await self.session.flush()
        return len(rows)

    # ---- audit / egress for user ----
    async def list_audit(
        self, user_id: uuid.UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[AuditLog]:
        r = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return r.scalars().all()

    async def list_egress(
        self, user_id: uuid.UUID, *, limit: int = 100
    ) -> Sequence[EgressLedger]:
        r = await self.session.execute(
            select(EgressLedger)
            .where(EgressLedger.user_id == user_id)
            .order_by(EgressLedger.created_at.desc())
            .limit(limit)
        )
        return r.scalars().all()

    # ---- deletion ----
    async def create_deletion(
        self,
        *,
        user_id: uuid.UUID,
        scheduled_at: datetime,
        confirm_phrase_ok: bool,
        meta: dict | None = None,
    ) -> AccountDeletionRequest:
        row = AccountDeletionRequest(
            user_id=user_id,
            status="pending",
            scheduled_at=scheduled_at,
            confirm_phrase_ok=confirm_phrase_ok,
            meta=meta,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_deletion(self, req_id: uuid.UUID, user_id: uuid.UUID) -> Optional[AccountDeletionRequest]:
        r = await self.session.execute(
            select(AccountDeletionRequest).where(
                AccountDeletionRequest.id == req_id,
                AccountDeletionRequest.user_id == user_id,
            )
        )
        return r.scalar_one_or_none()

    async def list_due_deletions(self, now: datetime) -> Sequence[AccountDeletionRequest]:
        r = await self.session.execute(
            select(AccountDeletionRequest)
            .where(
                AccountDeletionRequest.status == "pending",
                AccountDeletionRequest.scheduled_at <= now,
            )
            .limit(20)
        )
        return r.scalars().all()

    async def cancel_deletion(self, row: AccountDeletionRequest) -> None:
        row.status = "cancelled"
        await self.session.flush()

    # ---- narrative ----
    async def save_narrative(
        self,
        *,
        user_id: uuid.UUID,
        score_snapshot_id: uuid.UUID | None,
        identifier_id: uuid.UUID | None,
        mode: str,
        model_name: str | None,
        title: str,
        body_markdown: str,
        facts_used: dict | None,
    ) -> NarrativeBriefing:
        row = NarrativeBriefing(
            user_id=user_id,
            score_snapshot_id=score_snapshot_id,
            identifier_id=identifier_id,
            mode=mode,
            model_name=model_name,
            title=title,
            body_markdown=body_markdown,
            facts_used=facts_used,
            grounded=True,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def latest_narrative(
        self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None
    ) -> Optional[NarrativeBriefing]:
        q = select(NarrativeBriefing).where(NarrativeBriefing.user_id == user_id)
        if identifier_id:
            q = q.where(NarrativeBriefing.identifier_id == identifier_id)
        q = q.order_by(NarrativeBriefing.created_at.desc()).limit(1)
        r = await self.session.execute(q)
        return r.scalar_one_or_none()
```

---

## 9. NEW: `backend/app/services/privacy/groq_client.py`

```python
"""Groq client via httpx (free). Never required for core path."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GroqError(Exception):
    pass


async def groq_available() -> bool:
    settings = get_settings()
    if not settings.narrative_enabled or not settings.groq_api_key:
        return False
    return True


async def groq_chat(
    *,
    system: str,
    user: str,
    model: str | None = None,
) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        raise GroqError("No GROQ_API_KEY provided")
        
    model = model or settings.groq_model
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    payload = {
        "model": model,
        "temperature": settings.narrative_temperature,
        "max_tokens": settings.narrative_max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=settings.narrative_timeout_seconds) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code != 200:
                raise GroqError(f"HTTP {r.status_code}: {r.text[:300]}")
            data = r.json()
            choices = data.get("choices", [])
            if not choices:
                raise GroqError("Empty Groq response")
                
            msg = choices[0].get("message", {}).get("content", "")
            if not msg.strip():
                raise GroqError("Empty message content")
            return msg.strip()
    except GroqError:
        raise
    except Exception as e:
        logger.warning("groq_chat_failed", error=str(e))
        raise GroqError(str(e)) from e
```

---

## 10. NEW: `backend/app/services/privacy/export_service.py`

```python
from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.privacy_export import build_export_package, redacted_user_public
from app.repositories.privacy_repository import PrivacyRepository
from app.repositories.identifier_repository import IdentifierRepository
from app.repositories.finding_repository import FindingRepository
from app.repositories.score_repository import ScoreRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.remediation_repository import RemediationRepository
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService


class ExportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PrivacyRepository(session)
        self.settings = get_settings()
        self.audit = AuditService(session)

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def start_export(
        self,
        user_id: uuid.UUID,
        *,
        include_audit: bool = True,
        include_egress: bool = True,
    ):
        if not self.settings.feature_data_export:
            raise HTTPException(status_code=503, detail="Export disabled")
        await self._set_rls(user_id)
        job = await self.repo.create_export_job(
            user_id=user_id,
            include_audit=include_audit and self.settings.export_include_audit,
            include_egress=include_egress and self.settings.export_include_egress,
        )
        await self.audit.log(
            "privacy.export_started",
            user_id=user_id,
            resource_type="data_export_job",
            resource_id=str(job.id),
        )
        await self.session.commit()

        # Synchronous build for MVP (small accounts). Workerize if packages grow.
        try:
            package = await self._build_package(
                user_id,
                include_audit=job.include_audit,
                include_egress=job.include_egress,
            )
            raw = json.dumps(package, default=str)
            size = len(raw.encode("utf-8"))
            if size > self.settings.export_max_bytes:
                raise HTTPException(status_code=413, detail="Export exceeds size limit")
            await self.repo.mark_export_ready(job, package, size)
            await self.audit.log(
                "privacy.export_ready",
                user_id=user_id,
                resource_type="data_export_job",
                resource_id=str(job.id),
                details={"size_bytes": size},
            )
            await self.session.commit()
        except HTTPException:
            raise
        except Exception as e:
            await self.repo.mark_export_failed(job, str(e))
            await self.session.commit()
            raise HTTPException(status_code=500, detail="Export failed") from e

        return await self.repo.get_export(job.id, user_id)

    async def _build_package(
        self, user_id: uuid.UUID, *, include_audit: bool, include_egress: bool
    ) -> dict[str, Any]:
        users = UserRepository(self.session)
        user = await users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        idents = await IdentifierRepository(self.session).list_for_user(user_id)
        findings = await FindingRepository(self.session).list_findings(user_id, limit=1000)
        scores = await ScoreRepository(self.session).history(user_id, limit=50)
        try:
            recs = await RecommendationRepository(self.session).list_open(user_id)
        except Exception:
            recs = []
        try:
            states = await RemediationRepository(self.session).list_states(user_id)
        except Exception:
            states = []
        try:
            edges = await IdentityRepository(self.session).list_edges(user_id)
        except Exception:
            edges = []
        try:
            gens = await RemediationRepository(self.session).list_generated(user_id)
        except Exception:
            gens = []
        consents = await self.repo.list_consents(user_id)

        audit_logs = None
        if include_audit:
            rows = await self.repo.list_audit(user_id, limit=500)
            audit_logs = [
                {
                    "id": str(a.id),
                    "action": a.action,
                    "resource_type": a.resource_type,
                    "resource_id": a.resource_id,
                    "details": a.details,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "correlation_id": a.correlation_id,
                }
                for a in rows
            ]

        egress = None
        if include_egress:
            rows = await self.repo.list_egress(user_id, limit=500)
            egress = [
                {
                    "id": str(e.id),
                    "purpose": e.purpose,
                    "destination_host": e.destination_host,
                    "method": e.method,
                    "status_code": e.status_code,
                    "success": e.success,
                    "summary": e.summary,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in rows
            ]

        return build_export_package(
            user=redacted_user_public(user),
            identifiers=[
                {
                    "id": str(i.id),
                    "type": i.type,
                    "value_canonical": i.value_canonical,
                    "value_display": i.value_display,
                    "is_verified": i.is_verified,
                    "verified_at": i.verified_at.isoformat() if i.verified_at else None,
                    "verification_method": i.verification_method,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in idents
            ],
            findings=[
                {
                    "id": str(f.id),
                    "kind": f.kind,
                    "source": f.source,
                    "title": f.title,
                    "summary": f.summary,
                    "severity_hint": f.severity_hint,
                    "confidence": f.confidence,
                    "layer": f.layer,
                    "track": f.track,
                    "status": f.status,
                    "attribution": f.attribution,
                    "raw_ref": f.raw_ref,
                    "attributes": f.attributes,
                    "first_seen_at": f.first_seen_at.isoformat() if f.first_seen_at else None,
                    "last_seen_at": f.last_seen_at.isoformat() if f.last_seen_at else None,
                }
                for f in findings
            ],
            scores=[
                {
                    "id": str(s.id),
                    "score_combined": s.score_combined,
                    "severity": s.severity,
                    "vector": s.vector,
                    "model_version": s.model_version,
                    "trigger": s.trigger,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "explanation_summary": s.explanation_summary,
                }
                for s in scores
            ],
            recommendations=[
                {
                    "id": str(r.id),
                    "code": r.code,
                    "title": r.title,
                    "lane": r.lane,
                    "status": r.status,
                    "priority": r.priority,
                }
                for r in recs
            ],
            remediation_state=[
                {
                    "broker_id": s.broker_id,
                    "broker_name": s.broker_name,
                    "status": s.status,
                    "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
                    "detail": s.detail,
                }
                for s in states
            ],
            consent_records=[
                {
                    "purpose": c.purpose,
                    "scope": c.scope,
                    "granted": c.granted,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
                }
                for c in consents
            ],
            audit_logs=audit_logs,
            egress_ledger=egress,
            identity_edges=[
                {
                    "left": str(e.left_identifier_id),
                    "right": str(e.right_identifier_id),
                    "match_prob": e.match_prob,
                    "decision": e.decision,
                    "review_status": e.review_status,
                }
                for e in edges
            ],
            generated_requests=[
                {
                    "id": str(g.id),
                    "kind": g.kind,
                    "regime": g.regime,
                    "subject": g.subject,
                    "status": g.status,
                    "created_at": g.created_at.isoformat() if g.created_at else None,
                }
                for g in gens
            ],
        )

    async def get_export(self, user_id: uuid.UUID, job_id: uuid.UUID):
        await self._set_rls(user_id)
        job = await self.repo.get_export(job_id, user_id)
        if not job:
            raise HTTPException(status_code=404, detail="Export not found")
        return job
```

---

## 11. NEW: `backend/app/services/privacy/shred_service.py`

```python
"""
Crypto-shred + purge (G6).

Strategy:
1) Destroy user-specific secrets (MFA encrypted blob, refresh tokens, password hash randomized)
2) Hard-delete PII tables for the user (identifiers, findings, scores, remediation, etc.)
3) Keep anonymized audit rows with user_id NULL + action privacy.account_shredded
4) Mark user inactive / email scrambled so login fails permanently

Note: App-wide MASTER_KEY is NOT destroyed (would shred all users).
User-bound ciphertext (MFA) becomes undecryptable after secret wipe + row delete.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.user import User, RefreshToken
from app.models.audit import AuditLog
from app.models.identifier import Identifier, VerificationChallenge
from app.models.consent_egress import ConsentRecord, EgressLedger
from app.models.scan import Scan, ScanConnectorRun
from app.models.observation_finding import Observation, Finding, EvidenceBlob
from app.models.identity import IdentityEdge, IdentityCollision
from app.models.score import ScoreSnapshot, ExplanationRecord
from app.models.recommendation import Recommendation, RecommendationPlan
from app.models.alert import Alert, RescanPolicy
from app.models.privacy import DataExportJob, NarrativeBriefing, AccountDeletionRequest
from app.security.password import hash_password
from app.services.audit_service import AuditService

logger = get_logger(__name__)


class ShredService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.audit = AuditService(session)

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def execute_shred(self, user_id: uuid.UUID, *, deletion_request_id: uuid.UUID | None = None) -> dict[str, Any]:
        if not self.settings.feature_crypto_shred:
            raise HTTPException(status_code=503, detail="Crypto-shred disabled")

        # Workers may need elevated path — set RLS to user then delete own rows
        await self._set_rls(user_id)

        counts: dict[str, int] = {}

        async def _del(model, extra=None) -> int:
            q = delete(model).where(model.user_id == user_id)  # type: ignore[attr-defined]
            r = await self.session.execute(q)
            return r.rowcount or 0

        # Order: children-ish first where FK allows cascade; explicit deletes for safety
        tables_models = [
            ("narrative_briefings", NarrativeBriefing),
            ("data_export_jobs", DataExportJob),
            ("explanation_records", ExplanationRecord),
            ("score_snapshots", ScoreSnapshot),
            ("identity_collisions", IdentityCollision),
            ("identity_edges", IdentityEdge),
            ("evidence_blobs", EvidenceBlob),
            ("observations", Observation),
            ("findings", Finding),
            ("scan_connector_runs", ScanConnectorRun),
            ("scans", Scan),
            ("recommendations", Recommendation),
            ("recommendation_plans", RecommendationPlan),
            ("alerts", Alert),
            ("rescan_policies", RescanPolicy),
            ("verification_challenges", VerificationChallenge),
            ("identifiers", Identifier),
            ("consent_records", ConsentRecord),
            ("egress_ledger", EgressLedger),
            ("refresh_tokens", RefreshToken),
        ]

        # Remediation models if present
        try:
            from app.models.remediation import (
                BrokerOptOutState,
                RemediationJobItem,
                RemediationJob,
                CaptchaQueueItem,
                FreezeChecklistItem,
                GeneratedRequest,
            )
            tables_models = [
                ("captcha_queue", CaptchaQueueItem),
                ("remediation_job_items", RemediationJobItem),
                ("remediation_jobs", RemediationJob),
                ("broker_optout_state", BrokerOptOutState),
                ("freeze_checklist_items", FreezeChecklistItem),
                ("generated_requests", GeneratedRequest),
            ] + tables_models
        except Exception:
            pass

        for name, model in tables_models:
            try:
                counts[name] = await _del(model)
            except Exception as e:
                logger.warning("shred_table_failed", table=name, error=str(e))
                counts[name] = -1

        # Crypto-shred user credentials
        r = await self.session.execute(select_user := __import__("sqlalchemy", fromlist=["select"]).select(User).where(User.id == user_id))
        from sqlalchemy import select as sa_select
        r = await self.session.execute(sa_select(User).where(User.id == user_id))
        user = r.scalar_one_or_none()
        if user:
            # Destroy MFA secret (ciphertext discarded)
            user.mfa_secret_encrypted = None
            user.mfa_enabled = False
            # Unusable password
            user.hashed_password = hash_password(secrets.token_urlsafe(48))
            # Scramble email (preserve uniqueness)
            user.email = f"shredded+{user_id.hex[:16]}@invalid.local"
            user.email_blind = None
            user.is_active = False
            user.is_verified = False
            counts["user_credential_shred"] = 1

        # Anonymize remaining audit logs for this user (keep actions for integrity research, drop link)
        try:
            await self.session.execute(
                update(AuditLog)
                .where(AuditLog.user_id == user_id)
                .values(user_id=None, details={"redacted": True, "reason": "crypto_shred"})
            )
            counts["audit_anonymized"] = 1
        except Exception as e:
            logger.warning("audit_anonymize_failed", error=str(e))

        # Mark deletion request completed
        if deletion_request_id:
            r = await self.session.execute(
                sa_select(AccountDeletionRequest).where(AccountDeletionRequest.id == deletion_request_id)
            )
            req = r.scalar_one_or_none()
            if req:
                req.status = "completed"
                req.completed_at = datetime.now(timezone.utc)
                req.meta = {**(req.meta or {}), "counts": counts}

        # Final audit (user_id null after anonymize — log with resource)
        try:
            self.session.add(
                AuditLog(
                    user_id=None,
                    action="privacy.account_shredded",
                    resource_type="user",
                    resource_id=str(user_id),
                    details={"counts": counts},
                )
            )
        except Exception:
            pass

        await self.session.commit()
        logger.info("crypto_shred_completed", user_id=str(user_id), counts=counts)
        return {"user_id": str(user_id), "status": "completed", "counts": counts}
```

Fix the accidental bad line in shred — use clean select:

```python
        from sqlalchemy import select as sa_select
        r = await self.session.execute(sa_select(User).where(User.id == user_id))
        user = r.scalar_one_or_none()
```

(Remove the broken `select_user := __import__...` line when pasting.)

---

## 12. NEW: `backend/app/services/privacy/narrative_service.py`

```python
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.narrative import (
    FactsPack,
    SYSTEM_PROMPT,
    build_deterministic_narrative,
    user_prompt_from_facts,
)
from app.repositories.privacy_repository import PrivacyRepository
from app.repositories.score_repository import ScoreRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.remediation_repository import RemediationRepository
from app.repositories.identifier_repository import IdentifierRepository
from app.services.privacy.groq_client import groq_available, groq_chat, GroqError
from app.services.audit_service import AuditService


class NarrativeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PrivacyRepository(session)
        self.scores = ScoreRepository(session)
        self.settings = get_settings()
        self.audit = AuditService(session)

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def _facts(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None,
        score_snapshot_id: uuid.UUID | None,
    ) -> tuple[FactsPack, uuid.UUID | None]:
        snap = None
        if score_snapshot_id:
            snap = await self.scores.get(score_snapshot_id, user_id)
        else:
            snap = await self.scores.latest(user_id, identifier_id)
        if not snap:
            raise HTTPException(status_code=404, detail="No score snapshot — compute PDSS first")

        contribs = list(snap.contributions or [])[: self.settings.narrative_max_findings]
        cfs = list(snap.counterfactuals or [])[:5]

        rec_titles: list[str] = []
        try:
            recs = await RecommendationRepository(self.session).list_open(user_id, identifier_id)
            rec_titles = [r.title for r in recs[:8]]
        except Exception:
            pass

        broker_statuses: list[dict[str, str]] = []
        try:
            states = await RemediationRepository(self.session).list_states(user_id)
            broker_statuses = [{"broker_id": s.broker_id, "status": s.status} for s in states[:10]]
        except Exception:
            pass

        id_types: list[str] = []
        try:
            idents = await IdentifierRepository(self.session).list_for_user(user_id)
            id_types = sorted({i.type for i in idents if i.is_verified})
        except Exception:
            pass

        facts = FactsPack(
            score_combined=float(snap.score_combined),
            severity=snap.severity,
            score_confirmed=float(snap.score_confirmed),
            score_possible=float(snap.score_possible),
            vector=snap.vector,
            explanation_summary=snap.explanation_summary or "",
            model_version=snap.model_version,
            contributions=contribs,
            counterfactuals=cfs,
            attributions=list(snap.attributions or []),
            open_recommendation_titles=rec_titles,
            broker_statuses=broker_statuses,
            identifier_types=id_types,
        )
        return facts, snap.id

    async def generate(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        score_snapshot_id: uuid.UUID | None = None,
        prefer_llm: bool = True,
        persist: bool = True,
    ):
        if not self.settings.feature_grounded_narrative:
            raise HTTPException(status_code=503, detail="Narrative feature disabled")

        await self._set_rls(user_id)
        facts, snap_id = await self._facts(
            user_id, identifier_id=identifier_id, score_snapshot_id=score_snapshot_id
        )

        user_prompt = user_prompt_from_facts(facts)

        narrative_text = ""
        engine = "deterministic"
        
        if prefer_llm and await groq_available():
            try:
                narrative_text = await groq_chat(
                    system=SYSTEM_PROMPT,
                    user=user_prompt,
                )
                engine = "groq"
            except GroqError:
                narrative_text = build_deterministic_narrative(facts)
        else:
            narrative_text = build_deterministic_narrative(facts)

        title = f"Exposure briefing — PDSS {facts.score_combined:.1f} ({facts.severity})"
        row = None
        if persist:
            row = await self.repo.save_narrative(
                user_id=user_id,
                score_snapshot_id=snap_id,
                identifier_id=identifier_id,
                mode=engine,
                model_name=self.settings.groq_model if engine == "groq" else None,
                title=title,
                body_markdown=narrative_text,
                facts_used=facts.to_dict(),
            )
            await self.audit.log(
                "privacy.narrative_generated",
                user_id=user_id,
                resource_type="narrative_briefing",
                resource_id=str(row.id),
                details={"mode": mode, "model": model_name},
            )
            await self.session.commit()

        return {
            "id": row.id if row else None,
            "score_snapshot_id": snap_id,
            "identifier_id": identifier_id,
            "mode": mode,
            "model_name": model_name,
            "title": title,
            "body_markdown": body,
            "grounded": True,
            "facts_used": facts.to_dict(),
            "created_at": row.created_at if row else None,
        }

    async def get_counterfactuals(
        self, user_id: uuid.UUID, *, identifier_id: uuid.UUID | None = None, snapshot_id: uuid.UUID | None = None
    ):
        await self._set_rls(user_id)
        if snapshot_id:
            snap = await self.scores.get(snapshot_id, user_id)
        else:
            snap = await self.scores.latest(user_id, identifier_id)
        if not snap:
            raise HTTPException(status_code=404, detail="No score snapshot")
        return {
            "score_snapshot_id": snap.id,
            "counterfactuals": snap.counterfactuals or [],
            "explanation_summary": snap.explanation_summary or "",
            "vector": snap.vector,
            "score_combined": snap.score_combined,
        }
```

---

## 13. NEW: `backend/app/services/privacy/privacy_service.py`  
*(consent + delete orchestration)*

```python
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.privacy_repository import PrivacyRepository
from app.services.consent_service import ConsentService
from app.services.audit_service import AuditService
from app.services.privacy.shred_service import ShredService


class PrivacyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PrivacyRepository(session)
        self.consent = ConsentService(session)
        self.audit = AuditService(session)
        self.settings = get_settings()

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def list_consent(self, user_id: uuid.UUID):
        await self._set_rls(user_id)
        rows = await self.repo.list_consents(user_id)
        return [
            {
                "id": r.id,
                "purpose": r.purpose,
                "scope": r.scope,
                "granted": r.granted and r.revoked_at is None,
                "created_at": r.created_at,
                "revoked_at": r.revoked_at,
                "details": r.details,
            }
            for r in rows
        ]

    async def grant(self, user_id: uuid.UUID, purpose: str, scope: str | None, details: dict | None):
        await self._set_rls(user_id)
        await self.consent.grant(user_id, purpose, scope=scope, details=details)
        await self.session.commit()
        return {"message": "Consent granted", "purpose": purpose}

    async def revoke(self, user_id: uuid.UUID, purpose: str):
        await self._set_rls(user_id)
        n = await self.repo.revoke_consent(user_id, purpose)
        await self.audit.log(
            "consent.revoked",
            user_id=user_id,
            details={"purpose": purpose, "count": n},
        )
        await self.session.commit()
        return {"message": "Consent revoked", "purpose": purpose, "records_updated": n}

    async def list_audit(self, user_id: uuid.UUID, limit: int = 100, offset: int = 0):
        await self._set_rls(user_id)
        return await self.repo.list_audit(user_id, limit=limit, offset=offset)

    async def list_egress(self, user_id: uuid.UUID, limit: int = 100):
        await self._set_rls(user_id)
        return await self.repo.list_egress(user_id, limit=limit)

    async def request_deletion(
        self,
        user_id: uuid.UUID,
        confirm_phrase: str,
        *,
        immediate: bool = False,
    ):
        await self._set_rls(user_id)
        if confirm_phrase.strip() != self.settings.account_delete_confirm_phrase:
            raise HTTPException(
                status_code=400,
                detail=f"confirm_phrase must be exactly: {self.settings.account_delete_confirm_phrase}",
            )
        now = datetime.now(timezone.utc)
        do_immediate = (
            immediate
            and self.settings.account_delete_dev_immediate
            and self.settings.is_development
        )
        scheduled = now if do_immediate else now + timedelta(hours=self.settings.account_delete_grace_hours)
        req = await self.repo.create_deletion(
            user_id=user_id,
            scheduled_at=scheduled,
            confirm_phrase_ok=True,
            meta={"immediate": do_immediate},
        )
        await self.audit.log(
            "privacy.deletion_requested",
            user_id=user_id,
            resource_type="account_deletion_request",
            resource_id=str(req.id),
            details={"scheduled_at": scheduled.isoformat(), "immediate": do_immediate},
        )
        await self.session.commit()

        if do_immediate:
            shred = ShredService(self.session)
            await shred.execute_shred(user_id, deletion_request_id=req.id)
            return await self.repo.get_deletion(req.id, user_id)

        return req

    async def cancel_deletion(self, user_id: uuid.UUID, req_id: uuid.UUID):
        await self._set_rls(user_id)
        req = await self.repo.get_deletion(req_id, user_id)
        if not req:
            raise HTTPException(status_code=404, detail="Deletion request not found")
        if req.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending requests can be cancelled")
        await self.repo.cancel_deletion(req)
        await self.audit.log("privacy.deletion_cancelled", user_id=user_id, resource_id=str(req_id))
        await self.session.commit()
        return req

    async def process_due_deletions(self) -> dict[str, int]:
        now = datetime.now(timezone.utc)
        due = await self.repo.list_due_deletions(now)
        done = 0
        failed = 0
        shred = ShredService(self.session)
        for req in due:
            try:
                req.status = "shredding"
                await self.session.flush()
                await shred.execute_shred(req.user_id, deletion_request_id=req.id)
                done += 1
            except Exception:
                req.status = "failed"
                req.error = "shred_failed"
                await self.session.commit()
                failed += 1
        return {"completed": done, "failed": failed}
```

---

## 14. NEW: `backend/app/api/v1/privacy.py`

```python
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.privacy import (
    ExportCreateRequest,
    ExportJobPublic,
    ExportPackageResponse,
    ConsentGrantRequest,
    ConsentRevokeRequest,
    ConsentItem,
    AuditEventPublic,
    EgressEventPublic,
    AccountDeleteRequest,
    AccountDeletePublic,
    NarrativeRequest,
    NarrativePublic,
    CounterfactualPublic,
    Message,
)
from app.services.privacy.export_service import ExportService
from app.services.privacy.privacy_service import PrivacyService
from app.services.privacy.narrative_service import NarrativeService

router = APIRouter(prefix="/privacy", tags=["privacy"])


def _export(db: AsyncSession = Depends(get_db)) -> ExportService:
    return ExportService(db)


def _privacy(db: AsyncSession = Depends(get_db)) -> PrivacyService:
    return PrivacyService(db)


def _narrative(db: AsyncSession = Depends(get_db)) -> NarrativeService:
    return NarrativeService(db)


# ---------- Export ----------
@router.post("/export", response_model=ExportJobPublic, status_code=201)
async def create_export(
    body: ExportCreateRequest,
    current_user: CurrentUser,
    svc: ExportService = Depends(_export),
):
    """GDPR/CCPA-style machine-readable personal data export (JSON)."""
    job = await svc.start_export(
        current_user.id,
        include_audit=body.include_audit,
        include_egress=body.include_egress,
    )
    return ExportJobPublic.model_validate(job)


@router.get("/export/{job_id}", response_model=ExportPackageResponse)
async def get_export(
    job_id: UUID,
    current_user: CurrentUser,
    svc: ExportService = Depends(_export),
):
    job = await svc.get_export(current_user.id, job_id)
    return ExportPackageResponse(
        job=ExportJobPublic.model_validate(job),
        package=job.package if job.status == "ready" else None,
    )


# ---------- Consent center ----------
@router.get("/consent", response_model=list[ConsentItem])
async def list_consent(current_user: CurrentUser, svc: PrivacyService = Depends(_privacy)):
    rows = await svc.list_consent(current_user.id)
    return [ConsentItem.model_validate(r) for r in rows]


@router.post("/consent", response_model=Message)
async def grant_consent(
    body: ConsentGrantRequest,
    current_user: CurrentUser,
    svc: PrivacyService = Depends(_privacy),
):
    return await svc.grant(current_user.id, body.purpose, body.scope, body.details)


@router.post("/consent/revoke", response_model=Message)
async def revoke_consent(
    body: ConsentRevokeRequest,
    current_user: CurrentUser,
    svc: PrivacyService = Depends(_privacy),
):
    return await svc.revoke(current_user.id, body.purpose)


# ---------- Audit + egress transparency ----------
@router.get("/audit", response_model=list[AuditEventPublic])
async def my_audit(
    current_user: CurrentUser,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: PrivacyService = Depends(_privacy),
):
    rows = await svc.list_audit(current_user.id, limit=limit, offset=offset)
    return [
        AuditEventPublic(
            id=r.id,
            action=r.action,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            details=r.details,
            created_at=r.created_at,
            correlation_id=r.correlation_id,
        )
        for r in rows
    ]


@router.get("/egress", response_model=list[EgressEventPublic])
async def my_egress(
    current_user: CurrentUser,
    limit: int = Query(100, ge=1, le=500),
    svc: PrivacyService = Depends(_privacy),
):
    rows = await svc.list_egress(current_user.id, limit=limit)
    return [
        EgressEventPublic(
            id=r.id,
            purpose=r.purpose,
            destination_host=r.destination_host,
            method=r.method,
            status_code=r.status_code,
            success=r.success,
            summary=r.summary,
            created_at=r.created_at,
        )
        for r in rows
    ]


# ---------- Erasure ----------
@router.post("/account/delete", response_model=AccountDeletePublic)
async def request_delete(
    body: AccountDeleteRequest,
    current_user: CurrentUser,
    svc: PrivacyService = Depends(_privacy),
):
    """
    Right to erasure. Schedules crypto-shred + purge after grace period
    (or immediate in development when allowed).
    """
    req = await svc.request_deletion(
        current_user.id, body.confirm_phrase, immediate=body.immediate
    )
    return AccountDeletePublic.model_validate(req)


@router.post("/account/delete/{req_id}/cancel", response_model=AccountDeletePublic)
async def cancel_delete(
    req_id: UUID,
    current_user: CurrentUser,
    svc: PrivacyService = Depends(_privacy),
):
    req = await svc.cancel_deletion(current_user.id, req_id)
    return AccountDeletePublic.model_validate(req)


# ---------- Explain ----------
@router.post("/narrative", response_model=NarrativePublic)
async def generate_narrative(
    body: NarrativeRequest,
    current_user: CurrentUser,
    svc: NarrativeService = Depends(_narrative),
):
    """Grounded exposure briefing (Ollama if available; deterministic fallback)."""
    data = await svc.generate(
        current_user.id,
        identifier_id=body.identifier_id,
        score_snapshot_id=body.score_snapshot_id,
        prefer_ollama=body.prefer_ollama,
        persist=body.persist,
    )
    return NarrativePublic.model_validate(data)


@router.get("/narrative/latest", response_model=NarrativePublic)
async def latest_narrative(
    current_user: CurrentUser,
    identifier_id: Optional[UUID] = None,
    svc: NarrativeService = Depends(_narrative),
):
    await svc._set_rls(current_user.id)
    row = await svc.repo.latest_narrative(current_user.id, identifier_id)
    if not row:
        raise HTTPException(status_code=404, detail="No narrative yet")  # noqa: F821
    return NarrativePublic.model_validate(row)


@router.get("/counterfactuals", response_model=CounterfactualPublic)
async def counterfactuals(
    current_user: CurrentUser,
    identifier_id: Optional[UUID] = None,
    snapshot_id: Optional[UUID] = None,
    svc: NarrativeService = Depends(_narrative),
):
    data = await svc.get_counterfactuals(
        current_user.id, identifier_id=identifier_id, snapshot_id=snapshot_id
    )
    return CounterfactualPublic.model_validate(data)
```

Fix the missing import in latest_narrative:

```python
from fastapi import HTTPException
```

at top of privacy.py (already have Depends etc. — add HTTPException).

---

## 15. NEW: `backend/app/tasks/privacy_tasks.py`

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


async def _process_deletions() -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.privacy.privacy_service import PrivacyService

    async with AsyncSessionLocal() as session:
        svc = PrivacyService(session)
        return await svc.process_due_deletions()


@celery_app.task(name="app.tasks.privacy_tasks.process_account_deletions_task")
def process_account_deletions_task() -> dict:
    logger.info("process_account_deletions_start")
    return _run_async(_process_deletions()) or {}
```

---

## 16. UPDATE: `backend/app/worker.py`

```python
    include=[
        "app.tasks",
        "app.tasks.discovery_tasks",
        "app.tasks.alert_tasks",
        "app.tasks.remediation_tasks",
        "app.tasks.privacy_tasks",
    ],
...
        "process-account-deletions": {
            "task": "app.tasks.privacy_tasks.process_account_deletions_task",
            "schedule": 300.0,  # every 5 minutes
        },
```

---

## 17. UPDATE: `backend/app/main.py`

```python
from app.api.v1 import (
    health, auth, identifiers, connectors, scans, identity, scores,
    recommendations, alerts, remediation, privacy,
)

app.include_router(privacy.router, prefix=settings.api_v1_prefix)

# root
"version": "0.8.0",
"message": "DigiZafe Sprint 8 Privacy, Rights, Explain backend — ready",
```

---

## 18. Alembic migration `sprint8_privacy_rights_explain`

```python
"""sprint8_privacy_rights_explain"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "sprint8_priv_001"
down_revision: Union[str, None] = "sprint7_rem_001"  # ← your Sprint 7 rev
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("include_audit", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("include_egress", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("size_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("package", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_data_export_jobs_user_id", "data_export_jobs", ["user_id"])
    op.create_index("ix_data_export_jobs_status", "data_export_jobs", ["status"])

    op.create_table(
        "account_deletion_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("confirm_phrase_ok", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_account_deletion_requests_user_id", "account_deletion_requests", ["user_id"])
    op.create_index("ix_account_deletion_requests_status", "account_deletion_requests", ["status"])

    op.create_table(
        "narrative_briefings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score_snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("score_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mode", sa.String(32), nullable=False, server_default="deterministic"),
        sa.Column("model_name", sa.String(128), nullable=True),
        sa.Column("title", sa.String(256), nullable=False, server_default="Exposure briefing"),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("facts_used", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("grounded", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_narrative_briefings_user_id", "narrative_briefings", ["user_id"])
    op.create_index("ix_narrative_briefings_created_at", "narrative_briefings", ["created_at"])

    for table in ("data_export_jobs", "account_deletion_requests", "narrative_briefings"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_self ON {table}
            FOR ALL
            USING (user_id::text = current_setting('app.current_user_id', true))
            WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
        """)


def downgrade() -> None:
    for table in ("narrative_briefings", "account_deletion_requests", "data_export_jobs"):
        op.execute(f"DROP POLICY IF EXISTS {table}_self ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
```

Update `alembic/env.py` imports for privacy models.

---

## 19. Unit tests

### `backend/tests/unit/test_privacy_export.py`

```python
from app.domain.privacy_export import build_export_package


def test_export_shape():
    pkg = build_export_package(
        user={"id": "u1", "email": "a@b.com", "is_active": True, "mfa_enabled": False,
              "created_at": None, "last_login_at": None},
        identifiers=[{"type": "email", "value_canonical": "a@b.com"}],
        findings=[],
        scores=[],
        recommendations=[],
        remediation_state=[],
        consent_records=[{"purpose": "discovery.xposedornot", "granted": True}],
    )
    assert pkg["export_version"] == "1.0.0"
    assert pkg["subject"]["email"] == "a@b.com"
    assert "rights" in pkg
```

### `backend/tests/unit/test_narrative_fallback.py`

```python
from app.domain.narrative import FactsPack, build_deterministic_narrative


def test_deterministic_mentions_score():
    facts = FactsPack(
        score_combined=6.4,
        severity="medium",
        score_confirmed=6.0,
        score_possible=1.2,
        vector="PDSS:pdss-v1.0.0/SC:6.4/SV:medium",
        explanation_summary="Top driver: Breach Adobe",
        model_version="pdss-v1.0.0",
        contributions=[{"source": "xposedornot", "title": "Breach: Adobe", "weighted_score": 2.1}],
        counterfactuals=[{"narrative": "If Adobe remediated, score would drop."}],
        attributions=["Data: XposedOrNot"],
        open_recommendation_titles=["Change passwords on breached accounts"],
    )
    text = build_deterministic_narrative(facts)
    assert "6.4" in text
    assert "Adobe" in text or "xposedornot" in text.lower()
    assert "Closed loop" in text or "closed loop" in text.lower()
```

---

## 20. Docs

### `docs/runbooks/privacy-rights.md`

```markdown
# Privacy, Rights, Explain (Sprint 8)

## Export
`POST /api/v1/privacy/export` → `GET /api/v1/privacy/export/{id}`  
JSON package: identifiers, findings, scores, consent, audit/egress (optional).  
No password hashes, MFA secrets, or refresh tokens.

## Consent center
`GET/POST /privacy/consent`, `POST /privacy/consent/revoke`  
Purposes e.g. `discovery.xposedornot`, `remediation.broker_optout`, `verification.github`.

## Audit + egress transparency
`GET /privacy/audit`, `GET /privacy/egress`

## Erasure (crypto-shred)
Confirm phrase: `DELETE MY DIGIZAFE ACCOUNT`  
`POST /privacy/account/delete` → grace (or immediate in dev) → shred secrets + purge PII tables.

## Grounded narrative
`POST /privacy/narrative` — Ollama if up, else deterministic template from PDSS facts only.  
`GET /privacy/counterfactuals` — durable what-if from score snapshot.

## Ollama (optional)
```bash
docker compose --profile with-ollama up -d
docker compose exec ollama ollama pull llama3.2:3b
# OLLAMA_BASE_URL=http://ollama:11434 inside compose network
```
```

### `docs/ethics/privacy-rights.md` (stub)

```markdown
# Ethics notes — Sprint 8
- Export is self-only (RLS + auth).
- Crypto-shred does not destroy global master key.
- Narratives are grounded; refuse invented exposure claims.
- Honest about free-tier third parties (XposedOrNot) in consent + egress ledger.
```

---

# PART C — Finish Sprint 8

```bash
# Merge env, rebuild, migrate
docker compose build api worker beat
docker compose up -d
docker compose exec api alembic upgrade head

# Export
curl -s -X POST http://localhost:8000/api/v1/privacy/export \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d '{"include_audit":true,"include_egress":true}' | jq .
# GET package with job id

# Consent list
curl -s http://localhost:8000/api/v1/privacy/consent -H "Authorization: Bearer $ACCESS" | jq .

# Audit
curl -s "http://localhost:8000/api/v1/privacy/audit?limit=20" -H "Authorization: Bearer $ACCESS" | jq .

# Narrative (needs PDSS snapshot)
curl -s -X POST http://localhost:8000/api/v1/privacy/narrative \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d "{\"identifier_id\":\"$ID\",\"prefer_llm\":true}" | jq .

# Counterfactuals
curl -s "http://localhost:8000/api/v1/privacy/counterfactuals?identifier_id=$ID" \
  -H "Authorization: Bearer $ACCESS" | jq .

# Deletion (dev immediate — careful)
# curl -s -X POST http://localhost:8000/api/v1/privacy/account/delete \
#   -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
#   -d '{"confirm_phrase":"DELETE MY DIGIZAFE ACCOUNT","immediate":true}' | jq .

docker compose exec api pytest backend/tests/unit/test_privacy_export.py backend/tests/unit/test_narrative_fallback.py -v

git add .
git commit -m "feat(sprint-8): privacy export, crypto-shred+purge, consent center, audit/egress, grounded narrative (Ollama+fallback)"
```

---

# Sprint 8 Definition of Done

- [ ] MASTER_ENGINEERING_CONTEXT respected  
- [ ] JSON data export (no secrets) + job API  
- [ ] Consent center list/grant/revoke  
- [ ] User audit + egress transparency APIs  
- [ ] Account deletion request + grace + crypto-shred/purge  
- [ ] MFA secret wipe + password destroy + email scramble + PII table purge  
- [ ] Grounded narrative: deterministic always; Ollama optional  
- [ ] Counterfactuals API from durable score snapshot (G3)  
- [ ] Beat task processes due deletions  
- [ ] RLS on new tables  
- [ ] Unit tests for export shape + narrative fallback  
- [ ] Zero paid keys; Ollama free/local only  

→ **Sprint 8 complete.**  
Next: **Sprint 9 Frontend Core** (Auth, identifiers, scan SSE, findings, PDSS breakdown + vector, recommendations, basic graph).

---

## Endpoint quick reference

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /api/v1/privacy/export | Bearer | Start data export |
| GET | /api/v1/privacy/export/{id} | Bearer | Download package |
| GET | /api/v1/privacy/consent | Bearer | Consent center |
| POST | /api/v1/privacy/consent | Bearer | Grant |
| POST | /api/v1/privacy/consent/revoke | Bearer | Revoke |
| GET | /api/v1/privacy/audit | Bearer | Own audit trail |
| GET | /api/v1/privacy/egress | Bearer | Egress ledger |
| POST | /api/v1/privacy/account/delete | Bearer | Request erasure |
| POST | /api/v1/privacy/account/delete/{id}/cancel | Bearer | Cancel pending |
| POST | /api/v1/privacy/narrative | Bearer | Grounded briefing |
| GET | /api/v1/privacy/narrative/latest | Bearer | Latest briefing |
| GET | /api/v1/privacy/counterfactuals | Bearer | What-if from PDSS |

---

## File checklist

| Action | Path |
|--------|------|
| UPDATE | `.env.example`, `config.py`, `main.py`, `worker.py`, `models/__init__.py`, `alembic/env.py` |
| NEW | `backend/app/domain/privacy_export.py` |
| NEW | `backend/app/domain/narrative.py` |
| NEW | `backend/app/models/privacy.py` |
| NEW | `backend/app/schemas/privacy.py` |
| NEW | `backend/app/repositories/privacy_repository.py` |
| NEW | `backend/app/services/privacy/ollama_client.py` |
| NEW | `backend/app/services/privacy/export_service.py` |
| NEW | `backend/app/services/privacy/shred_service.py` |
| NEW | `backend/app/services/privacy/narrative_service.py` |
| NEW | `backend/app/services/privacy/privacy_service.py` |
| NEW | `backend/app/api/v1/privacy.py` |
| NEW | `backend/app/tasks/privacy_tasks.py` |
| NEW | migration `sprint8_privacy_rights_explain` |
| NEW | unit tests + runbooks |
| OPTIONAL | Ollama compose profile |

