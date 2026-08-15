from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.consent_egress import ConsentRecord, EgressLedger
from app.models.privacy import AccountDeletionRequest, DataExportJob, NarrativeBriefing


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
            expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_export(self, job_id: uuid.UUID, user_id: uuid.UUID) -> DataExportJob | None:
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
        job.ready_at = datetime.now(UTC)
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
        now = datetime.now(UTC)
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

    async def get_deletion(self, req_id: uuid.UUID, user_id: uuid.UUID) -> AccountDeletionRequest | None:
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
    ) -> NarrativeBriefing | None:
        q = select(NarrativeBriefing).where(NarrativeBriefing.user_id == user_id)
        if identifier_id:
            q = q.where(NarrativeBriefing.identifier_id == identifier_id)
        q = q.order_by(NarrativeBriefing.created_at.desc()).limit(1)
        r = await self.session.execute(q)
        return r.scalar_one_or_none()
