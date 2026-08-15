from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import MFASetupResponse, TokenPair, UserPublic
from app.security.jwt import create_access_token
from app.security.keys import get_key_service
from app.security.mfa import (
    generate_qr_base64,
    generate_totp_secret,
    get_provisioning_uri,
    verify_totp,
)
from app.security.password import hash_password, needs_rehash, verify_password
from app.services.audit_service import AuditService

logger = get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.audit = AuditService(session)
        self.keys = get_key_service()
        self.settings = get_settings()

    async def register(
        self,
        email: str,
        password: str,
        *,
        ip: str | None = None,
        ua: str | None = None,
    ) -> UserPublic:
        existing = await self.users.get_by_email(email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = hash_password(password)
        blind = self.keys.blind_index(email, context="email")
        user = await self.users.create(email=email, hashed_password=hashed, email_blind=blind)

        await self.audit.log(
            "auth.register",
            user_id=user.id,
            ip_address=ip,
            user_agent=ua,
            details={"email_domain": email.split("@")[-1]},
        )
        return UserPublic.model_validate(user)

    async def login(
        self,
        email: str,
        password: str,
        mfa_code: str | None = None,
        *,
        ip: str | None = None,
        ua: str | None = None,
    ) -> TokenPair:
        user = await self.users.get_by_email(email)
        if not user or not user.is_active:
            await self.audit.log(
                "auth.login.failure",
                ip_address=ip,
                user_agent=ua,
                details={"reason": "unknown_or_inactive", "email": email[:3] + "***"},
            )
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Lockout check
        now = datetime.now(UTC)
        if user.locked_until and user.locked_until > now:
            raise HTTPException(
                status_code=423,
                detail=f"Account temporarily locked until {user.locked_until.isoformat()}",
            )

        if not verify_password(password, user.hashed_password):
            await self.users.record_login_failure(user)
            await self.audit.log(
                "auth.login.failure",
                user_id=user.id,
                ip_address=ip,
                user_agent=ua,
                details={"reason": "bad_password"},
            )
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Optional rehash
        if needs_rehash(user.hashed_password):
            user.hashed_password = hash_password(password)
            await self.session.flush()

        # MFA gate
        if user.mfa_enabled:
            if not mfa_code:
                # Client should re-submit with code
                return TokenPair(
                    access_token="",
                    refresh_token="",
                    expires_in=0,
                    mfa_required=True,
                )
            secret = self._decrypt_mfa_secret(user)
            if not secret or not verify_totp(secret, mfa_code):
                await self.audit.log(
                    "auth.mfa.failure",
                    user_id=user.id,
                    ip_address=ip,
                    user_agent=ua,
                )
                raise HTTPException(status_code=401, detail="Invalid MFA code")

        await self.users.record_login_success(user)

        access = create_access_token(
            user.id,
            extra_claims={"email": user.email, "mfa": user.mfa_enabled},
        )
        raw_refresh, _ = await self.users.create_refresh_token(
            user_id=user.id, user_agent=ua, ip_address=ip
        )

        await self.audit.log(
            "auth.login.success",
            user_id=user.id,
            ip_address=ip,
            user_agent=ua,
        )

        return TokenPair(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=self.settings.jwt_access_token_expire_minutes * 60,
            mfa_required=False,
        )

    async def refresh(
        self,
        raw_refresh: str,
        *,
        ip: str | None = None,
        ua: str | None = None,
    ) -> TokenPair:
        token = await self.users.get_refresh_by_raw(raw_refresh)
        if not token:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        now = datetime.now(UTC)
        if token.revoked or token.expires_at < now:
            # Possible reuse of an already-rotated token
            if token.revoked:
                await self.users.revoke_family(token.family_id)
                await self.audit.log(
                    "auth.refresh.reuse_detected",
                    user_id=token.user_id,
                    ip_address=ip,
                    user_agent=ua,
                    details={"family_id": str(token.family_id)},
                )
            raise HTTPException(status_code=401, detail="Refresh token invalid or expired")

        user = await self.users.get_by_id(token.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User inactive")

        # Rotate: revoke old, issue new in same family
        await self.users.revoke_token(token)
        await self.users.mark_used(token)

        new_raw, new_row = await self.users.create_refresh_token(
            user_id=user.id,
            family_id=token.family_id,
            user_agent=ua,
            ip_address=ip,
        )
        # Link for audit trail
        token.replaced_by = new_row.id
        await self.session.flush()

        access = create_access_token(
            user.id,
            extra_claims={"email": user.email, "mfa": user.mfa_enabled},
        )

        await self.audit.log(
            "auth.refresh.success",
            user_id=user.id,
            ip_address=ip,
            user_agent=ua,
        )

        return TokenPair(
            access_token=access,
            refresh_token=new_raw,
            expires_in=self.settings.jwt_access_token_expire_minutes * 60,
        )

    async def logout(self, raw_refresh: str | None, user_id: uuid.UUID | None = None) -> None:
        if raw_refresh:
            token = await self.users.get_refresh_by_raw(raw_refresh)
            if token:
                await self.users.revoke_family(token.family_id)
                await self.audit.log(
                    "auth.logout",
                    user_id=token.user_id,
                )
        elif user_id:
            # Optional: revoke all families for user (implement if needed)
            pass

    async def setup_mfa(self, user: User) -> MFASetupResponse:
        if user.mfa_enabled:
            raise HTTPException(status_code=400, detail="MFA already enabled")

        secret = generate_totp_secret()
        # Temporarily store encrypted so enable can verify without re-sending secret
        encrypted = self.keys.encrypt_str(secret, aad=str(user.id).encode())
        user.mfa_secret_encrypted = encrypted
        # not enabled yet
        await self.session.flush()

        uri = get_provisioning_uri(secret, user.email)
        qr = generate_qr_base64(uri)

        await self.audit.log("auth.mfa.setup_started", user_id=user.id)
        return MFASetupResponse(secret=secret, provisioning_uri=uri, qr_code_data_uri=qr)

    async def enable_mfa(self, user: User, code: str) -> None:
        if user.mfa_enabled:
            raise HTTPException(status_code=400, detail="MFA already enabled")
        if not user.mfa_secret_encrypted:
            raise HTTPException(status_code=400, detail="Call /mfa/setup first")

        secret = self._decrypt_mfa_secret(user)
        if not secret or not verify_totp(secret, code):
            raise HTTPException(status_code=400, detail="Invalid MFA code")

        user.mfa_enabled = True
        await self.session.flush()
        await self.audit.log("auth.mfa.enabled", user_id=user.id)

    async def disable_mfa(self, user: User, code: str, password: str) -> None:
        if not user.mfa_enabled:
            raise HTTPException(status_code=400, detail="MFA not enabled")
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid password")
        secret = self._decrypt_mfa_secret(user)
        if not secret or not verify_totp(secret, code):
            raise HTTPException(status_code=400, detail="Invalid MFA code")

        user.mfa_enabled = False
        user.mfa_secret_encrypted = None
        await self.session.flush()
        await self.audit.log("auth.mfa.disabled", user_id=user.id)

    def _decrypt_mfa_secret(self, user: User) -> str | None:
        if not user.mfa_secret_encrypted:
            return None
        try:
            return self.keys.decrypt_str(
                user.mfa_secret_encrypted, aad=str(user.id).encode()
            )
        except Exception:
            logger.exception("mfa_secret_decrypt_failed", user_id=str(user.id))
            return None
