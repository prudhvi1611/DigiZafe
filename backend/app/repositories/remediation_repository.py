from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.remediation_states import (
    BrokerOptOutStatus,
    RemediationJobStatus,
    is_terminal_job,
    transition_job,
)
from app.models.remediation import (
    BrokerOptOutState,
    CaptchaQueueItem,
    FreezeChecklistItem,
    GeneratedRequest,
    RemediationJob,
    RemediationJobItem,
)


class RemediationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- state (AIDR state.json) ----
    async def get_state(self, user_id: uuid.UUID, broker_id: str) -> BrokerOptOutState | None:
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
        now = datetime.now(UTC)
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

    async def get_job(self, job_id: uuid.UUID, user_id: uuid.UUID) -> RemediationJob | None:
        r = await self.session.execute(
            select(RemediationJob)
            .options(selectinload(RemediationJob.items))
            .where(RemediationJob.id == job_id, RemediationJob.user_id == user_id)
        )
        return r.scalar_one_or_none()

    async def get_job_internal(self, job_id: uuid.UUID) -> RemediationJob | None:
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
        now = datetime.now(UTC)
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
        now = datetime.now(UTC)
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
            expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_captcha(self, captcha_id: uuid.UUID, user_id: uuid.UUID) -> CaptchaQueueItem | None:
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

    async def get_freeze(self, item_id: uuid.UUID, user_id: uuid.UUID) -> FreezeChecklistItem | None:
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

    async def get_generated(self, req_id: uuid.UUID, user_id: uuid.UUID) -> GeneratedRequest | None:
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
