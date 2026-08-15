from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.scan_states import (
    ConnectorRunStatus,
    ScanStatus,
    derive_scan_status_from_runs,
    is_terminal_scan,
    transition_run,
    transition_scan,
)
from app.models.scan import Scan, ScanConnectorRun


class ScanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, scan_id: uuid.UUID, user_id: uuid.UUID) -> Scan | None:
        result = await self.session.execute(
            select(Scan)
            .options(selectinload(Scan.connector_runs))
            .where(Scan.id == scan_id, Scan.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_internal(self, scan_id: uuid.UUID) -> Scan | None:
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
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
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
        now = datetime.now(UTC)
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
        now = datetime.now(UTC)
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
