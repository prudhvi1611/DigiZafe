from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
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

    async def get(self, alert_id: uuid.UUID, user_id: uuid.UUID) -> Alert | None:
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
        cutoff = datetime.now(UTC) - timedelta(days=days)
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
    ) -> RescanPolicy | None:
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
