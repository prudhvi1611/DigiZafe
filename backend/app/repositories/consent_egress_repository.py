from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.correlation import get_correlation_id
from app.models.consent_egress import ConsentRecord, EgressLedger


class ConsentEgressRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def grant(
        self,
        *,
        user_id: uuid.UUID,
        purpose: str,
        scope: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> ConsentRecord:
        row = ConsentRecord(
            user_id=user_id,
            purpose=purpose,
            scope=scope,
            granted=True,
            details=details,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def has_active_consent(self, user_id: uuid.UUID, purpose: str) -> bool:
        result = await self.session.execute(
            select(ConsentRecord).where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.purpose == purpose,
                ConsentRecord.granted.is_(True),
                ConsentRecord.revoked_at.is_(None),
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def ledger(
        self,
        *,
        purpose: str,
        destination_host: str,
        method: str = "GET",
        status_code: int | None = None,
        success: bool = False,
        user_id: uuid.UUID | None = None,
        identifier_id: uuid.UUID | None = None,
        summary: dict[str, Any] | None = None,
    ) -> EgressLedger:
        row = EgressLedger(
            user_id=user_id,
            identifier_id=identifier_id,
            purpose=purpose,
            destination_host=destination_host,
            method=method,
            status_code=status_code,
            success=success,
            summary=summary,
            correlation_id=get_correlation_id(),
        )
        self.session.add(row)
        await self.session.flush()
        return row
