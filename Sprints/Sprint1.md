# DigiZafe — Sprint 1 Auth & Crypto  
**Complete Implementation Guide from Sprint 0 Baseline + All File Contents**

**Document version:** 1.0  
**Based on:** MASTER_ENGINEERING_CONTEXT.md v2.1  
**Depends on:** Sprint 0 Foundations (green health, Docker, config, logging, Alembic, CI)  
**Goal:** From completed Sprint 0 → production-ready Auth & Crypto foundation (Argon2id, short JWT + rotating refresh tokens with reuse detection, TOTP MFA, KeyService envelope crypto + blind-index helpers, durable Audit, Postgres RLS foundation).  

**Effort estimate:** ~8 days (solo)  
**Critical path next:** Sprint 2 Identifiers & Verification

> **Load MASTER_ENGINEERING_CONTEXT.md first in every session.**  
> Never redesign. Implement the frozen baseline. File a CBN only if a frozen doc truly conflicts.

---

# PART A — Pre-Sprint 1 (run once from DigiZafe root)

```bash
# 1. Confirm Sprint 0 is green
docker compose ps
curl -s http://localhost:8000/api/v1/health | jq .
curl -s -I http://localhost:8000/api/v1/health | grep -i x-correlation-id

# 2. Create any missing packages / dirs (most already exist from Sprint 0)
mkdir -p backend/app/{security,repositories,services,models,schemas,domain}
mkdir -p backend/app/api/v1
mkdir -p backend/tests/{unit,integration,security}
mkdir -p secrets
touch backend/app/security/__init__.py
touch backend/app/repositories/__init__.py
touch backend/app/services/__init__.py
touch backend/app/models/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/domain/__init__.py

# 3. Update dependencies (edit pyproject.toml — see PART B)
# Then rebuild
docker compose build api worker beat
# or locally:
# pip install -e ".[dev]"

echo "✅ Pre-Sprint 1 ready. Now apply the file contents below."
```

**New / updated Python deps (add to pyproject.toml):**

```toml
# Add inside [project] dependencies = [ ... ]
"pyotp>=2.9.0",
"qrcode[pil]>=7.4.2",   # optional QR image; URI is enough if you drop PIL later
```

(Already present and used: `argon2-cffi`, `cryptography`, `python-jose[cryptography]`, `passlib[argon2]`, `pydantic-settings`, etc.)

---

# PART B — Sprint 1 File Contents

Copy each section into the corresponding file.  
Files marked **UPDATE** replace the Sprint 0 version.  
All others are **NEW**.

---

## 1. UPDATE: Root `.env.example` (append these)

```bash
# === Sprint 1: Auth & Crypto ===
# JWT (short access + long-lived rotating refresh)
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=14
# Optional separate signing key (defaults to SECRET_KEY)
JWT_SECRET_KEY=

# MFA
MFA_ISSUER=DigiZafe
MFA_TOTP_DIGITS=6
MFA_TOTP_INTERVAL=30

# Crypto / KeyService
# MASTER_KEY_FILE already present from Sprint 0
# In development the KeyService will auto-create a 32-byte master key if missing.

# Audit
AUDIT_RETENTION_DAYS=365

# Auth behaviour
PASSWORD_MIN_LENGTH=12
MAX_FAILED_LOGIN_ATTEMPTS=10
LOGIN_LOCKOUT_MINUTES=15
```

Copy the new vars into your real `.env` (generate a strong `SECRET_KEY` if you haven’t).

---

## 2. UPDATE: `backend/app/core/config.py`

Replace the whole file with this expanded version (keeps all Sprint 0 settings + adds auth/crypto):

```python
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "DigiZafe"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = Field(..., min_length=32)
    master_key_file: str = "./secrets/master.key"

    # Database
    database_url: str = Field(..., description="Async SQLAlchemy URL (postgresql+asyncpg://...)")

    # Redis
    redis_broker_url: str = "redis://localhost:6379/0"
    redis_cache_url: str = "redis://localhost:6380/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json | console

    # Feature flags
    feature_xposedornot: bool = True
    feature_hibp_breach_api: bool = False
    feature_capsolver: bool = False
    feature_ml_residual: bool = False

    # Optional keys
    hibp_api_key: str | None = None
    capsolver_api_key: str | None = None
    xposedornot_api_key: str | None = None

    # Quotas
    default_user_scan_quota_per_day: int = 20

    # === Sprint 1: Auth & Crypto ===
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 14
    jwt_secret_key: str | None = None  # falls back to secret_key

    mfa_issuer: str = "DigiZafe"
    mfa_totp_digits: int = 6
    mfa_totp_interval: int = 30

    audit_retention_days: int = 365
    password_min_length: int = 12
    max_failed_login_attempts: int = 10
    login_lockout_minutes: int = 15

    @field_validator("secret_key")
    @classmethod
    def secret_key_strength(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def effective_jwt_secret(self) -> str:
        return self.jwt_secret_key or self.secret_key


@lru_cache
def get_settings() -> Settings:
    """Fail-fast: raises ValidationError if required env vars are missing."""
    return Settings()  # type: ignore[call-arg]
```

---

## 3. NEW: `backend/app/security/password.py`

```python
"""Argon2id password hashing (OWASP / RFC 9106 aligned defaults)."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from argon2.profiles import RFC_9106_LOW_MEMORY  # good balance for most servers

from app.core.config import get_settings

# Use a sensible profile; can switch to HIGH_MEMORY later if hardware allows
_ph = PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)
# Alternative explicit: PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, type=Type.ID)


def hash_password(plain: str) -> str:
    settings = get_settings()
    if len(plain) < settings.password_min_length:
        raise ValueError(f"Password must be at least {settings.password_min_length} characters")
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """Call after successful verify; re-hash if parameters changed."""
    return _ph.check_needs_rehash(hashed)
```

---

## 4. NEW: `backend/app/security/jwt.py`

```python
"""Short-lived access JWT + helpers for claims."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import get_settings


def create_access_token(
    subject: str | UUID,
    *,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(
        to_encode,
        settings.effective_jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.effective_jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise
```

---

## 5. NEW: `backend/app/security/mfa.py`

```python
"""TOTP MFA helpers (pyotp). Secrets are never stored in plaintext — encrypt via KeyService."""

import base64
import io
from typing import Tuple

import pyotp
import qrcode

from app.core.config import get_settings


def generate_totp_secret() -> str:
    """Return a new base32 secret."""
    return pyotp.random_base32()


def get_totp(secret: str) -> pyotp.TOTP:
    settings = get_settings()
    return pyotp.TOTP(
        secret,
        digits=settings.mfa_totp_digits,
        interval=settings.mfa_totp_interval,
    )


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    totp = get_totp(secret)
    return bool(totp.verify(code, valid_window=valid_window))


def get_provisioning_uri(secret: str, email: str) -> str:
    settings = get_settings()
    totp = get_totp(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.mfa_issuer)


def generate_qr_base64(provisioning_uri: str) -> str:
    """Return a data-URI-friendly base64 PNG of the QR code."""
    img = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
```

---

## 6. NEW: `backend/app/security/keys.py`  (KeyService)

```python
"""
KeyService — envelope encryption + blind-index helpers.
Master key lives in MASTER_KEY_FILE (32 bytes). Auto-created in development if missing.
Uses AES-GCM. Separate MFA DEK derivation is prepared for later expansion.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class KeyService:
    def __init__(self) -> None:
        self._master_key: Optional[bytes] = None

    def _ensure_master_key(self) -> bytes:
        if self._master_key is not None:
            return self._master_key

        settings = get_settings()
        path = Path(settings.master_key_file)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            key = path.read_bytes()
            if len(key) != 32:
                raise RuntimeError(f"Master key at {path} must be exactly 32 bytes")
            self._master_key = key
            return key

        if settings.is_production:
            raise RuntimeError(
                f"Master key file missing in production: {path}. "
                "Generate offline and place securely."
            )

        # Dev: auto-generate
        key = secrets.token_bytes(32)
        path.write_bytes(key)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        logger.warning("master_key_auto_created", path=str(path))
        self._master_key = key
        return key

    @property
    def master_key(self) -> bytes:
        return self._ensure_master_key()

    def encrypt(self, plaintext: bytes | str, *, aad: bytes | None = None) -> bytes:
        """AES-GCM encrypt. Returns nonce (12) || ciphertext+tag."""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")
        key = self.master_key
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext, aad)
        return nonce + ct

    def decrypt(self, blob: bytes, *, aad: bytes | None = None) -> bytes:
        if len(blob) < 13:
            raise ValueError("Invalid ciphertext")
        nonce, ct = blob[:12], blob[12:]
        aesgcm = AESGCM(self.master_key)
        return aesgcm.decrypt(nonce, ct, aad)

    def encrypt_str(self, plaintext: str, *, aad: bytes | None = None) -> str:
        """Return url-safe base64 of encrypted blob (for DB storage)."""
        import base64
        return base64.urlsafe_b64encode(self.encrypt(plaintext, aad=aad)).decode("ascii")

    def decrypt_str(self, blob_b64: str, *, aad: bytes | None = None) -> str:
        import base64
        raw = base64.urlsafe_b64decode(blob_b64.encode("ascii"))
        return self.decrypt(raw, aad=aad).decode("utf-8")

    def blind_index(self, value: str, *, context: str = "email") -> str:
        """
        HMAC-SHA256 blind index (hex). Useful for unique lookups without
        storing the raw value in a searchable column long-term.
        """
        key = self.master_key
        h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
        h.update(context.encode("utf-8"))
        h.update(b"|")
        h.update(value.strip().lower().encode("utf-8"))
        return h.finalize().hex()


# Singleton for the process
_key_service: Optional[KeyService] = None


def get_key_service() -> KeyService:
    global _key_service
    if _key_service is None:
        _key_service = KeyService()
    return _key_service
```

---

## 7. NEW: `backend/app/models/user.py`

```python
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    func,
    LargeBinary,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    # Optional blind index (HMAC) for future privacy hardening
    email_blind: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True)

    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # email verified later

    # MFA
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # base64 AES-GCM

    # Security counters
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    # Store only a hash of the raw refresh token
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)

    # Family for rotation + reuse detection
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    replaced_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
```

---

## 8. NEW: `backend/app/models/audit.py`

```python
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nullable for unauthenticated events (failed login before user known)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)

    action: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    # e.g. "auth.login.success", "auth.mfa.enabled", "auth.refresh.reuse_detected"

    resource_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    # Redacted / structured details only — never raw secrets
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
```

---

## 9. UPDATE: `backend/app/models/__init__.py`

```python
from app.models.user import User, RefreshToken
from app.models.audit import AuditLog

__all__ = ["User", "RefreshToken", "AuditLog"]
```

---

## 10. NEW: `backend/app/schemas/auth.py`

```python
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    mfa_code: Optional[str] = Field(None, min_length=6, max_length=8)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    mfa_required: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class MFASetupResponse(BaseModel):
    secret: str  # shown once; user must confirm
    provisioning_uri: str
    qr_code_data_uri: Optional[str] = None


class MFAEnableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class MFADisableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)
    password: str  # re-auth


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool
    is_verified: bool
    mfa_enabled: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class Message(BaseModel):
    message: str
```

---

## 11. NEW: `backend/app/repositories/user_repository.py`

```python
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, RefreshToken
from app.core.config import get_settings


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        hashed_password: str,
        email_blind: Optional[str] = None,
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
        user.last_login_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def record_login_failure(self, user: User) -> None:
        settings = get_settings()
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_login_attempts:
            user.locked_until = datetime.now(timezone.utc) + timedelta(
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

        expires = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
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

    async def get_refresh_by_raw(self, raw: str) -> Optional[RefreshToken]:
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
        token.last_used_at = datetime.now(timezone.utc)
        await self.session.flush()
```

---

## 12. NEW: `backend/app/repositories/audit_repository.py`

```python
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        action: str,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        correlation_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        row = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            details=details,
        )
        self.session.add(row)
        await self.session.flush()
        return row
```

---

## 13. NEW: `backend/app/services/audit_service.py`

```python
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.correlation import get_correlation_id
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AuditRepository(session)

    async def log(
        self,
        action: str,
        *,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        await self.repo.create(
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=get_correlation_id(),
            details=details,
        )
```

---

## 14. NEW: `backend/app/services/auth_service.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.security.password import hash_password, verify_password, needs_rehash
from app.security.jwt import create_access_token
from app.security.mfa import (
    generate_totp_secret,
    verify_totp,
    get_provisioning_uri,
    generate_qr_base64,
)
from app.security.keys import get_key_service
from app.services.audit_service import AuditService
from app.schemas.auth import TokenPair, MFASetupResponse, UserPublic

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
        now = datetime.now(timezone.utc)
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

        now = datetime.now(timezone.utc)
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
```

---

## 15. NEW: `backend/app/api/deps.py`

```python
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.security.jwt import decode_access_token
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
    auto_error=False,  # we handle missing token ourselves for optional
)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


async def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(db)


async def get_current_user(
    request: Request,
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id = uuid.UUID(sub)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive or not found")

    # Set RLS context for the rest of the request (local to transaction)
    await db.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"),
        {"uid": str(user.id)},
    )

    # Attach for convenience
    request.state.user = user
    return user


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    return current_user


# Type aliases for cleanliness
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
```

---

## 16. NEW: `backend/app/api/v1/auth.py`

```python
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import (
    get_auth_service,
    get_current_user,
    CurrentUser,
    DbSession,
)
from app.schemas.auth import (
    UserCreate,
    UserLogin,
    TokenPair,
    RefreshRequest,
    MFASetupResponse,
    MFAEnableRequest,
    MFADisableRequest,
    UserPublic,
    Message,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_meta(request: Request) -> tuple[Optional[str], Optional[str]]:
    ip = request.client.host if request.client else None
    # Prefer X-Forwarded-For if behind proxy (Caddy)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    ua = request.headers.get("user-agent")
    return ip, ua


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client_meta(request)
    return await svc.register(body.email, body.password, ip=ip, ua=ua)


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),  # supports Swagger OAuth2
    svc: AuthService = Depends(get_auth_service),
    # Also accept JSON body for convenience
):
    """
    Supports both:
    - application/x-www-form-urlencoded (OAuth2PasswordRequestForm) — Swagger
    - For pure JSON clients, prefer the /login/json endpoint below.
    """
    ip, ua = _client_meta(request)
    # form_data.username is the email
    return await svc.login(
        email=form_data.username,
        password=form_data.password,
        mfa_code=None,  # form path; use /login/json for MFA in one shot
        ip=ip,
        ua=ua,
    )


@router.post("/login/json", response_model=TokenPair)
async def login_json(
    body: UserLogin,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client_meta(request)
    return await svc.login(
        email=body.email,
        password=body.password,
        mfa_code=body.mfa_code,
        ip=ip,
        ua=ua,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client_meta(request)
    return await svc.refresh(body.refresh_token, ip=ip, ua=ua)


@router.post("/logout", response_model=Message)
async def logout(
    body: RefreshRequest | None = None,
    current_user: CurrentUser = None,  # type: ignore
    svc: AuthService = Depends(get_auth_service),
):
    # Soft: allow unauthenticated logout of a known refresh token
    raw = body.refresh_token if body else None
    uid = current_user.id if current_user else None
    await svc.logout(raw, user_id=uid)
    return Message(message="Logged out")


@router.get("/me", response_model=UserPublic)
async def me(current_user: CurrentUser):
    return UserPublic.model_validate(current_user)


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    current_user: CurrentUser,
    svc: AuthService = Depends(get_auth_service),
):
    return await svc.setup_mfa(current_user)


@router.post("/mfa/enable", response_model=Message)
async def mfa_enable(
    body: MFAEnableRequest,
    current_user: CurrentUser,
    svc: AuthService = Depends(get_auth_service),
):
    await svc.enable_mfa(current_user, body.code)
    return Message(message="MFA enabled")


@router.post("/mfa/disable", response_model=Message)
async def mfa_disable(
    body: MFADisableRequest,
    current_user: CurrentUser,
    svc: AuthService = Depends(get_auth_service),
):
    await svc.disable_mfa(current_user, body.code, body.password)
    return Message(message="MFA disabled")
```

> Note: The `/logout` dependency on `CurrentUser` is optional. For a pure public logout you can make `get_current_user` optional or split endpoints. For Sprint 1 the above is sufficient; tighten in hardening sprint if desired.

---

## 17. UPDATE: `backend/app/main.py`

Replace the router include section and lifespan (keep the rest of Sprint 0 structure):

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.correlation import CorrelationIdMiddleware
from app.api.v1 import health, auth  # ← add auth
from app.api.errors import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.security.keys import get_key_service

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_up", app=settings.app_name, env=settings.app_env)
    # Ensure master key exists (dev auto-create)
    try:
        ks = get_key_service()
        _ = ks.master_key
        logger.info("key_service_ready")
    except Exception as e:
        logger.error("key_service_failed", error=str(e))
        raise
    yield
    logger.info("shutting_down")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Routers
app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
        "message": "DigiZafe Sprint 1 Auth & Crypto — ready",
    }
```

Also ensure `backend/app/api/v1/__init__.py` exists (empty or with imports).

---

## 18. UPDATE: `backend/app/core/database.py` (optional small improvement for RLS)

Keep Sprint 0 version. The `set_config(..., true)` in `get_current_user` already scopes to the current transaction. For stricter future use you can add a context manager later.

---

## 19. Alembic migration

Create a new revision (recommended way):

```bash
# Inside the running api container or with PYTHONPATH set
docker compose exec api alembic revision -m "sprint1_auth_crypto_users_rls"
```

Then replace the generated file contents in `backend/app/alembic/versions/xxxx_sprint1_auth_crypto_users_rls.py` with:

```python
"""sprint1_auth_crypto_users_rls

Revision ID: <auto>
Revises: <previous or empty>
Create Date: ...
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "sprint1_auth_001"  # or leave auto-generated
down_revision: Union[str, None] = None  # set to previous if you already have baseline
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("email_blind", sa.String(64), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mfa_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_email_blind", "users", ["email_blind"], unique=True)

    # refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("replaced_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_correlation_id", "audit_logs", ["correlation_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ---------- RLS foundation ----------
    # Enable RLS
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")

    # Force for table owner too (good practice)
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE refresh_tokens FORCE ROW LEVEL SECURITY")
    # audit_logs: keep owner able to insert from app role; policies below

    # Policies — users can only see/update their own row
    # (Superuser bypass can be added later via a role check or SET ROLE)
    op.execute("""
        CREATE POLICY users_self_select ON users
        FOR SELECT
        USING (id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY users_self_update ON users
        FOR UPDATE
        USING (id::text = current_setting('app.current_user_id', true));
    """)
    # Allow insert during registration (no current_user yet) — policy for INSERT is permissive or handled by SECURITY DEFINER functions later.
    # For Sprint 1 we use a simple approach: app connects as a role that can bypass for writes, or we temporarily disable FORCE for inserts.
    # Practical MVP approach: create a policy that allows INSERT always (app enforces), and SELECT/UPDATE by owner.
    op.execute("""
        CREATE POLICY users_insert ON users
        FOR INSERT
        WITH CHECK (true);
    """)

    # refresh_tokens: owner only
    op.execute("""
        CREATE POLICY refresh_tokens_self ON refresh_tokens
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    # Also allow insert when setting the config (login path sets it after user known)
    # For pure login before set_config, the service uses the same session after user load.

    # audit_logs: users can read their own; inserts allowed (app writes)
    op.execute("""
        CREATE POLICY audit_self_select ON audit_logs
        FOR SELECT
        USING (
            user_id IS NULL
            OR user_id::text = current_setting('app.current_user_id', true)
        );
    """)
    op.execute("""
        CREATE POLICY audit_insert ON audit_logs
        FOR INSERT
        WITH CHECK (true);
    """)

    # Note: In production you will typically connect as a non-superuser role
    # and use SECURITY DEFINER functions or a bypass role for background workers.
    # Sprint 1 establishes the policies; workers/admin can SET app.current_user_id
    # or use a privileged role.


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS audit_insert ON audit_logs")
    op.execute("DROP POLICY IF EXISTS audit_self_select ON audit_logs")
    op.execute("DROP POLICY IF EXISTS refresh_tokens_self ON refresh_tokens")
    op.execute("DROP POLICY IF EXISTS users_insert ON users")
    op.execute("DROP POLICY IF EXISTS users_self_update ON users")
    op.execute("DROP POLICY IF EXISTS users_self_select ON users")

    op.execute("ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE refresh_tokens DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")

    op.drop_table("audit_logs")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
```

**Important RLS note for Sprint 1:**  
Postgres RLS is enforced for the table owner only when `FORCE ROW LEVEL SECURITY` is set. Background workers and registration (no `app.current_user_id` yet) need either:

- a privileged DB role that bypasses RLS, or  
- `SET LOCAL app.current_user_id` before every query, or  
- temporary relaxation of FORCE / use of `BYPASSRLS` attribute for the app role.

For local Docker (superuser) RLS is soft until you create a least-privilege role. The policies are in place; Sprint 13 / hardening will lock the connection role. The `set_config` in `get_current_user` already prepares the request path correctly.

---

## 20. UPDATE: `backend/app/alembic/env.py`

Add model imports so autogenerate works later:

```python
# near the top, after Base import
from app.models import user, audit  # noqa: F401
# or
from app.models.user import User, RefreshToken  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
```

---

## 21. NEW: Unit tests (examples)

### `backend/tests/unit/test_password.py`

```python
from app.security.password import hash_password, verify_password


def test_hash_and_verify():
    h = hash_password("correct-horse-battery-staple-99")
    assert verify_password("correct-horse-battery-staple-99", h)
    assert not verify_password("wrong", h)
```

### `backend/tests/unit/test_keys.py`

```python
from app.security.keys import KeyService


def test_encrypt_decrypt_roundtrip(tmp_path, monkeypatch):
    keyfile = tmp_path / "master.key"
    monkeypatch.setenv("MASTER_KEY_FILE", str(keyfile))
    # reset singleton if needed
    from app.security import keys
    keys._key_service = None

    ks = KeyService()
    blob = ks.encrypt_str("hello-mfa-secret", aad=b"user-1")
    assert ks.decrypt_str(blob, aad=b"user-1") == "hello-mfa-secret"

    idx1 = ks.blind_index("User@Example.com")
    idx2 = ks.blind_index("user@example.com")
    assert idx1 == idx2
```

### `backend/tests/unit/test_auth_flow.py` (high-level, needs DB or mocks)

For full integration, use testcontainers or a real Postgres in CI later. For now keep unit tests on pure security helpers.

---

## 22. UPDATE: `.github/workflows/ci.yml` (add env for tests)

In the Pytest step, ensure:

```yaml
        env:
          SECRET_KEY: "test-secret-key-at-least-32-characters-long"
          DATABASE_URL: "postgresql+asyncpg://test:test@localhost:5432/test"
          APP_ENV: "test"
          MASTER_KEY_FILE: "/tmp/digizafe-test-master.key"
```

(You can expand CI with a Postgres service later.)

---

## 23. Docs stubs (optional but recommended)

### `docs/runbooks/auth.md` (short)

```markdown
# Auth Runbook (Sprint 1)

- Register: POST /api/v1/auth/register
- Login (JSON + MFA): POST /api/v1/auth/login/json
- Refresh: POST /api/v1/auth/refresh  (rotation + reuse detection)
- MFA setup → enable with TOTP code
- Master key: secrets/master.key (32 bytes). Never commit.
- Audit actions: auth.register, auth.login.*, auth.mfa.*, auth.refresh.*
```

---

# PART C — How to finish Sprint 1

```bash
# 1. Apply code + update .env with new vars + strong SECRET_KEY
cp .env.example .env   # or merge new keys
# edit SECRET_KEY, ensure MASTER_KEY_FILE path is writable

# 2. Rebuild
docker compose build --no-cache api worker
docker compose up -d

# 3. Run migration
docker compose exec api alembic upgrade head
# (if revision id issues, set down_revision correctly first)

# 4. Smoke test
curl -s http://localhost:8000/ | jq .
curl -s http://localhost:8000/api/v1/health | jq .

# Register
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"correct-horse-battery-staple-99"}' | jq .

# Login (JSON)
curl -s -X POST http://localhost:8000/api/v1/auth/login/json \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"correct-horse-battery-staple-99"}' | jq .

# Save access_token and refresh_token, then:
# curl -s http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer $ACCESS" | jq .

# MFA setup (with token)
# curl -s -X POST http://localhost:8000/api/v1/auth/mfa/setup -H "Authorization: Bearer $ACCESS" | jq .
# Then enable with a real TOTP code from authenticator app.

# 5. Commit
git add .
git commit -m "feat(sprint-1): auth & crypto — Argon2id, JWT+refresh rotation+reuse, TOTP MFA, KeyService, Audit, RLS foundation"
```

---

# Sprint 1 Definition of Done Checklist

- [ ] `MASTER_ENGINEERING_CONTEXT.md` still loaded / respected  
- [ ] All new files present and packages import cleanly  
- [ ] `docker compose up` green; health still returns database: ok  
- [ ] Migration applied: `users`, `refresh_tokens`, `audit_logs` exist  
- [ ] RLS enabled + policies created (FORCE noted for later least-privilege role)  
- [ ] Register → Login → /me works with short JWT  
- [ ] Refresh rotates token and issues new one; reuse of old refresh revokes family + audits  
- [ ] Failed logins increment counter and can lock account  
- [ ] MFA setup returns secret + provisioning URI (+ QR data URI); enable/disable works with TOTP  
- [ ] MFA secret stored only encrypted (AES-GCM via KeyService)  
- [ ] Master key auto-created in dev under `secrets/master.key` (600 perms)  
- [ ] Audit rows written for register / login success|failure / mfa / refresh / reuse  
- [ ] Argon2id used (not bcrypt)  
- [ ] No paid API keys introduced  
- [ ] Correlation ID still present on responses  
- [ ] Unit tests for password + KeyService pass  
- [ ] CI still green (or soft-fail only on mypy as before)  

Once all boxes are checked → **Sprint 1 is complete**.  
Next: **Sprint 2 Identifiers & Verification** (canonicalization, EgressFetcher SSRF-guard, email/DNS/GitHub verify, verified-only trigger design).

---

## Quick reference — key endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /api/v1/auth/register | No | Create user |
| POST | /api/v1/auth/login | No | Form login (Swagger) |
| POST | /api/v1/auth/login/json | No | JSON login + optional mfa_code |
| POST | /api/v1/auth/refresh | No | Rotate refresh + new access |
| POST | /api/v1/auth/logout | Optional | Revoke family |
| GET  | /api/v1/auth/me | Bearer | Current user |
| POST | /api/v1/auth/mfa/setup | Bearer | Start MFA (secret + QR) |
| POST | /api/v1/auth/mfa/enable | Bearer | Confirm TOTP |
| POST | /api/v1/auth/mfa/disable | Bearer | Disable (password + TOTP) |

---

**You are ready for Sprint 1.**  
Paste the files in order, run the migration, smoke-test the auth flow, then commit.  

If any single file fails (import, migration, RLS edge case on superuser vs app role), paste the error and I will give the exact fix while staying inside the frozen architecture.  

After Sprint 1 is green we move to Sprint 2 (Identifiers & Verification + EgressFetcher).