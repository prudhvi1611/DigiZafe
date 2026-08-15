from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.privacy_repository import PrivacyRepository
from app.services.audit_service import AuditService
from app.services.consent_service import ConsentService
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
        now = datetime.now(UTC)
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
        now = datetime.now(UTC)
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
