from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.canonicalize import (
    CanonicalizationError,
    IdentifierType,
    canonicalize,
    display_redacted,
)
from app.repositories.identifier_repository import IdentifierRepository
from app.schemas.identifier import IdentifierPublic
from app.security.keys import get_key_service
from app.services.audit_service import AuditService


class IdentifierService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = IdentifierRepository(session)
        self.audit = AuditService(session)
        self.keys = get_key_service()

    async def list(self, user_id: uuid.UUID) -> list[IdentifierPublic]:
        rows = await self.repo.list_for_user(user_id)
        return [IdentifierPublic.model_validate(r) for r in rows]

    async def add(
        self,
        user_id: uuid.UUID,
        type_: IdentifierType,
        raw_value: str,
    ) -> IdentifierPublic:
        try:
            canonical = canonicalize(type_, raw_value)
        except CanonicalizationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        existing = await self.repo.get_by_canonical(user_id, type_.value, canonical)
        if existing:
            raise HTTPException(status_code=409, detail="Identifier already exists")

        blind = self.keys.blind_index(f"{type_.value}:{canonical}", context="identifier")
        display = raw_value.strip()  # keep user-facing form; canonical stored separately
        row = await self.repo.create(
            user_id=user_id,
            type_=type_.value,
            value_canonical=canonical,
            value_display=display,
            value_blind=blind,
        )
        await self.audit.log(
            "identifier.created",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(row.id),
            details={
                "type": type_.value,
                "redacted": display_redacted(type_, canonical),
            },
        )
        return IdentifierPublic.model_validate(row)

    async def get(self, user_id: uuid.UUID, identifier_id: uuid.UUID) -> IdentifierPublic:
        row = await self.repo.get(identifier_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Identifier not found")
        return IdentifierPublic.model_validate(row)

    async def delete(self, user_id: uuid.UUID, identifier_id: uuid.UUID) -> None:
        row = await self.repo.get(identifier_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Identifier not found")
        await self.repo.delete(row)
        await self.audit.log(
            "identifier.deleted",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(identifier_id),
        )

    async def require_verified(self, user_id: uuid.UUID, identifier_id: uuid.UUID):
        """Used by future discovery — hard gate."""
        row = await self.repo.get(identifier_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Identifier not found")
        if not row.is_verified:
            raise HTTPException(
                status_code=403,
                detail="Identifier is not verified. Verify ownership before scanning (G1).",
            )
        return row
