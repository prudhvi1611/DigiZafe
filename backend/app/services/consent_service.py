from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.consent_egress_repository import ConsentEgressRepository
from app.services.audit_service import AuditService


class ConsentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ConsentEgressRepository(session)
        self.audit = AuditService(session)

    async def ensure_consent(
        self,
        user_id: uuid.UUID,
        purpose: str,
        *,
        auto_grant: bool = False,
        scope: str | None = None,
    ) -> bool:
        if await self.repo.has_active_consent(user_id, purpose):
            return True
        if auto_grant:
            await self.repo.grant(user_id=user_id, purpose=purpose, scope=scope)
            await self.audit.log(
                "consent.granted",
                user_id=user_id,
                details={"purpose": purpose, "auto": True},
            )
            return True
        return False

    async def grant(
        self,
        user_id: uuid.UUID,
        purpose: str,
        scope: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        await self.repo.grant(user_id=user_id, purpose=purpose, scope=scope, details=details)
        await self.audit.log(
            "consent.granted",
            user_id=user_id,
            details={"purpose": purpose},
        )

    async def record_egress(self, **kwargs: Any) -> None:
        await self.repo.ledger(**kwargs)
