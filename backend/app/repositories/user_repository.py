from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import RefreshToken, User


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        hashed_password: str,
        email_blind: str | None = None,
    ) -> User:
        user = User(
            email=email.lower().strip(),
            hashed_password=hashed_password,
            email_blind=email_blind,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_password(self, user: User, new_hashed: str) -> None:
        user.hashed_password = new_hashed
        await self.session.flush()

    async def set_mfa_secret(self, user: User, encrypted_secret: str | None, enabled: bool) -> None:
        user.mfa_secret_encrypted = encrypted_secret
        user.mfa_enabled = enabled
        await self.session.flush()

    async def record_login_success(self, user: User) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(UTC)
        await self.session.flush()

    async def record_login_failure(self, user: User) -> None:
        settings = get_settings()
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_login_attempts:
            user.locked_until = datetime.now(UTC) + timedelta(
                minutes=settings.login_lockout_minutes
            )
        await self.session.flush()

    # ---------- Refresh tokens ----------
    async def create_refresh_token(
        self,
        *,
        user_id: uuid.UUID,
        family_id: uuid.UUID | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, RefreshToken]:
        """Returns (raw_token, db_row). Store only the hash."""
        settings = get_settings()
        raw = secrets.token_urlsafe(48)
        token_hash = _hash_token(raw)
        if family_id is None:
            family_id = uuid.uuid4()

        expires = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
        row = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.session.add(row)
        await self.session.flush()
        return raw, row

    async def get_refresh_by_raw(self, raw: str) -> RefreshToken | None:
        th = _hash_token(raw)
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == th)
        )
        return result.scalar_one_or_none()

    async def revoke_family(self, family_id: uuid.UUID) -> int:
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        return result.rowcount or 0

    async def revoke_token(self, token: RefreshToken, replaced_by: uuid.UUID | None = None) -> None:
        token.revoked = True
        if replaced_by:
            token.replaced_by = replaced_by
        await self.session.flush()

    async def mark_used(self, token: RefreshToken) -> None:
        token.last_used_at = datetime.now(UTC)
        await self.session.flush()
