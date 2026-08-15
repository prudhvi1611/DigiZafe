from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identifier import Identifier, VerificationChallenge


def _hash_secret(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class IdentifierRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[Identifier]:
        result = await self.session.execute(
            select(Identifier).where(Identifier.user_id == user_id).order_by(Identifier.created_at.desc())
        )
        return result.scalars().all()

    async def get(self, identifier_id: uuid.UUID, user_id: uuid.UUID) -> Identifier | None:
        result = await self.session.execute(
            select(Identifier).where(
                Identifier.id == identifier_id,
                Identifier.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_canonical(
        self, user_id: uuid.UUID, type_: str, value_canonical: str
    ) -> Identifier | None:
        result = await self.session.execute(
            select(Identifier).where(
                Identifier.user_id == user_id,
                Identifier.type == type_,
                Identifier.value_canonical == value_canonical,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        type_: str,
        value_canonical: str,
        value_display: str,
        value_blind: str | None = None,
    ) -> Identifier:
        row = Identifier(
            user_id=user_id,
            type=type_,
            value_canonical=value_canonical,
            value_display=value_display,
            value_blind=value_blind,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def delete(self, row: Identifier) -> None:
        await self.session.delete(row)
        await self.session.flush()

    async def mark_verified(
        self,
        row: Identifier,
        *,
        method: str,
    ) -> None:
        now = datetime.now(UTC)
        row.is_verified = True
        row.verified_at = now
        row.verification_method = method
        row.last_revalidated_at = now
        await self.session.flush()

    async def mark_revalidated(self, row: Identifier) -> None:
        row.last_revalidated_at = datetime.now(UTC)
        await self.session.flush()

    async def clear_verification(self, row: Identifier) -> None:
        row.is_verified = False
        row.verified_at = None
        row.verification_method = None
        await self.session.flush()

    # ---- challenges ----
    async def create_challenge(
        self,
        *,
        identifier_id: uuid.UUID,
        user_id: uuid.UUID,
        method: str,
        raw_secret: str,
        public_payload: dict | None,
        ttl_minutes: int,
    ) -> VerificationChallenge:
        ch = VerificationChallenge(
            identifier_id=identifier_id,
            user_id=user_id,
            method=method,
            secret_hash=_hash_secret(raw_secret),
            public_payload=public_payload,
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
        )
        self.session.add(ch)
        await self.session.flush()
        return ch

    async def get_challenge(
        self, challenge_id: uuid.UUID, user_id: uuid.UUID
    ) -> VerificationChallenge | None:
        result = await self.session.execute(
            select(VerificationChallenge).where(
                VerificationChallenge.id == challenge_id,
                VerificationChallenge.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def consume_challenge(self, ch: VerificationChallenge) -> None:
        ch.consumed_at = datetime.now(UTC)
        await self.session.flush()

    @staticmethod
    def verify_secret(raw: str, secret_hash: str) -> bool:
        return _hash_secret(raw) == secret_hash

    @staticmethod
    def new_numeric_code(length: int = 6) -> str:
        # cryptographically ok for short codes with rate limits
        upper = 10**length
        return str(secrets.randbelow(upper)).zfill(length)

    @staticmethod
    def new_token() -> str:
        return secrets.token_urlsafe(24)
