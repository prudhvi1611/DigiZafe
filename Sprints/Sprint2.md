# DigiZafe — Sprint 2 Identifiers & Verification  
**Complete Implementation Guide from Sprint 1 Baseline + All File Contents**

**Document version:** 1.0  
**Based on:** MASTER_ENGINEERING_CONTEXT.md v2.1  
**Depends on:** Sprint 0 Foundations + Sprint 1 Auth & Crypto (green)  
**Goal:** From completed Sprint 1 → identifiers owned by verified users only, pure canonicalization, single SSRF-guarded `EgressFetcher`, multi-method verification (email code, DNS TXT, GitHub proof), revalidation, consent + egress ledger, and **verified-only trigger design** (activated fully when scan tables land in Sprint 4).

**Effort estimate:** ~9 days (solo)  
**Critical path next:** Sprint 3 Connector SDK & Free Surface Green (XposedOrNot primary, …)

> **Load MASTER_ENGINEERING_CONTEXT.md first in every session.**  
> You implement; you do not re-decide architecture. G1 self-only safety is non-negotiable.

---

# PART A — Pre-Sprint 2 (run once from DigiZafe root)

```bash
# 1. Confirm Sprint 1 is green
docker compose ps
curl -s http://localhost:8000/api/v1/health | jq .
# Register + login + /me must work from Sprint 1

# 2. Package dirs (most exist)
mkdir -p backend/app/{domain,connectors/sdk,services,repositories,models,schemas,security,tasks}
mkdir -p backend/tests/{unit,integration,security}
mkdir -p docs/runbooks
touch backend/app/domain/__init__.py
touch backend/app/connectors/sdk/__init__.py

# 3. Dependencies — edit pyproject.toml (see PART B) then:
docker compose build api worker beat
# or: pip install -e ".[dev]"

echo "✅ Pre-Sprint 2 ready. Apply file contents below."
```

**Add to `pyproject.toml` → `[project] dependencies`:**

```toml
    "dnspython>=2.6.0",
    "idna>=3.7",
```

(`httpx`, `cryptography`, etc. already present.)

---

# PART B — Sprint 2 File Contents

---

## 1. UPDATE: Root `.env.example` (append)

```bash
# === Sprint 2: Identifiers & Verification & Egress ===
EGRESS_TIMEOUT_SECONDS=15
EGRESS_MAX_RESPONSE_BYTES=2097152
EGRESS_MAX_REDIRECTS=0
EGRESS_ALLOWED_SCHEMES=http,https
# Comma-separated host allowlist empty = any public host (still private-IP blocked)
EGRESS_HOST_ALLOWLIST=
# Optional free personal GitHub token for higher rate limits (never required)
GITHUB_TOKEN=

# Verification
VERIFICATION_TOKEN_TTL_MINUTES=30
VERIFICATION_EMAIL_CODE_LENGTH=6
# In development, email verification codes are returned in API response + logs (no SMTP required)
VERIFICATION_DEV_EXPOSE_CODE=true

# Revalidation
IDENTIFIER_REVALIDATION_DAYS=90
```

Merge into your real `.env`.

---

## 2. UPDATE: `backend/app/core/config.py`

Add these fields to the `Settings` class (keep everything from Sprint 1):

```python
    # === Sprint 2: Identifiers / Egress / Verification ===
    egress_timeout_seconds: float = 15.0
    egress_max_response_bytes: int = 2_097_152  # 2 MiB
    egress_max_redirects: int = 0
    egress_allowed_schemes: str = "http,https"
    egress_host_allowlist: str = ""  # comma-separated; empty = public internet
    github_token: str | None = None

    verification_token_ttl_minutes: int = 30
    verification_email_code_length: int = 6
    verification_dev_expose_code: bool = True

    identifier_revalidation_days: int = 90

    @property
    def egress_schemes(self) -> set[str]:
        return {s.strip().lower() for s in self.egress_allowed_schemes.split(",") if s.strip()}

    @property
    def egress_allowlist_hosts(self) -> set[str]:
        return {h.strip().lower() for h in self.egress_host_allowlist.split(",") if h.strip()}
```

---

## 3. NEW: `backend/app/domain/canonicalize.py`  
*(pure domain — no I/O, no DB)*

```python
"""Identifier canonicalization (pure functions)."""

from __future__ import annotations

import re
import unicodedata
from enum import Enum

import idna


class IdentifierType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    USERNAME = "username"
    DOMAIN = "domain"
    GITHUB_USERNAME = "github_username"
    # Future: url, ip, etc. — not in Sprint 2 verification set


_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)
_PHONE_RE = re.compile(r"^\+[1-9]\d{6,14}$")  # E.164-ish
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]{0,38}[a-zA-Z0-9])?$")
_DOMAIN_LABEL_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", re.I)


class CanonicalizationError(ValueError):
    pass


def normalize_unicode(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip()


def canonicalize_email(raw: str) -> str:
    v = normalize_unicode(raw).lower()
    if not _EMAIL_RE.match(v) or len(v) > 320:
        raise CanonicalizationError("Invalid email format")
    local, _, domain = v.partition("@")
    # Gmail-style optional normalization (dots + plus) for common providers
    if domain in {"gmail.com", "googlemail.com"}:
        local = local.split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    else:
        local = local.split("+", 1)[0]  # strip plus-tags generically
    # IDNA domain
    try:
        domain_idna = idna.encode(domain).decode("ascii")
    except idna.IDNAError as e:
        raise CanonicalizationError(f"Invalid email domain: {e}") from e
    return f"{local}@{domain_idna}"


def canonicalize_phone(raw: str) -> str:
    v = normalize_unicode(raw)
    # Strip spaces, dashes, parens
    digits = re.sub(r"[\s\-().]", "", v)
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if not digits.startswith("+"):
        # Assume needs country code — refuse bare local numbers for self-only safety
        raise CanonicalizationError("Phone must be E.164 with leading +country code")
    if not _PHONE_RE.match(digits):
        raise CanonicalizationError("Invalid phone (E.164 expected)")
    return digits


def canonicalize_username(raw: str) -> str:
    v = normalize_unicode(raw).lstrip("@").lower()
    if not _USERNAME_RE.match(v) or len(v) > 40:
        raise CanonicalizationError("Invalid username")
    return v


def canonicalize_domain(raw: str) -> str:
    v = normalize_unicode(raw).lower().rstrip(".")
    # Strip scheme/path if user pasted URL
    v = re.sub(r"^https?://", "", v)
    v = v.split("/")[0].split("?")[0].split("#")[0]
    if ":" in v:  # strip port
        host, _, port = v.rpartition(":")
        if port.isdigit():
            v = host
    if not v or len(v) > 253:
        raise CanonicalizationError("Invalid domain")
    labels = v.split(".")
    if len(labels) < 2:
        raise CanonicalizationError("Domain must include a public suffix (e.g. example.com)")
    for label in labels:
        if not _DOMAIN_LABEL_RE.match(label) and not label.startswith("xn--"):
            # allow punycode labels after idna
            pass
    try:
        return idna.encode(v).decode("ascii")
    except idna.IDNAError as e:
        raise CanonicalizationError(f"Invalid domain: {e}") from e


def canonicalize_github_username(raw: str) -> str:
    v = canonicalize_username(raw)
    # GitHub rules: max 39, alphanumeric/hyphen, no leading/trailing hyphen
    if v.startswith("-") or v.endswith("-") or "--" in v or len(v) > 39:
        raise CanonicalizationError("Invalid GitHub username")
    return v


def canonicalize(identifier_type: IdentifierType | str, raw: str) -> str:
    t = IdentifierType(identifier_type) if isinstance(identifier_type, str) else identifier_type
    if t == IdentifierType.EMAIL:
        return canonicalize_email(raw)
    if t == IdentifierType.PHONE:
        return canonicalize_phone(raw)
    if t == IdentifierType.USERNAME:
        return canonicalize_username(raw)
    if t == IdentifierType.DOMAIN:
        return canonicalize_domain(raw)
    if t == IdentifierType.GITHUB_USERNAME:
        return canonicalize_github_username(raw)
    raise CanonicalizationError(f"Unsupported type: {t}")


def display_redacted(identifier_type: IdentifierType | str, canonical: str) -> str:
    """Safe display form (partial redact) for UI/logs."""
    t = IdentifierType(identifier_type) if isinstance(identifier_type, str) else identifier_type
    if t == IdentifierType.EMAIL:
        local, _, domain = canonical.partition("@")
        if len(local) <= 2:
            return f"{local[0]}***@{domain}"
        return f"{local[:2]}***@{domain}"
    if t == IdentifierType.PHONE:
        return canonical[:4] + "****" + canonical[-2:]
    if t in (IdentifierType.USERNAME, IdentifierType.GITHUB_USERNAME):
        if len(canonical) <= 3:
            return canonical[0] + "***"
        return canonical[:2] + "***" + canonical[-1:]
    if t == IdentifierType.DOMAIN:
        return canonical
    return "***"
```

---

## 4. NEW: `backend/app/security/egress.py`  
**Single SSRF-guarded EgressFetcher (resolve → block private → fetch)**

```python
"""
EgressFetcher — the ONLY outbound HTTP path for DigiZafe.

Policy (MASTER §9 / G1 / free-first):
- http/https only
- Resolve hostname first
- Reject private, loopback, link-local, metadata, CGNAT, etc.
- Optional host allowlist
- No redirects by default (prevents redirect-to-internal)
- Timeouts + response size cap
- Records to egress_ledger via caller (Consent/Egress service)

Residual risk: DNS rebinding TOCTOU between resolve and connect is mitigated by
no-redirects + short timeout + re-resolve optional pin. Full IP-pin + SNI for
HTTPS can be hardened further in Sprint 13; this is production-usable for MVP.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Networks we never connect to
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local + cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
    ipaddress.ip_network("2001:db8::/32"),
]


class EgressError(Exception):
    def __init__(self, message: str, code: str = "EGRESS-001") -> None:
        super().__init__(message)
        self.code = code


class EgressBlockedError(EgressError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="EGRESS-BLOCKED")


@dataclass
class EgressResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    url: str
    resolved_ips: list[str]
    elapsed_ms: float


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
        return True
    if ip.is_unspecified:
        return True
    for net in _BLOCKED_NETWORKS:
        try:
            if ip in net:
                return True
        except Exception:
            continue
    # Explicit metadata
    if str(ip) in {"169.254.169.254", "metadata.google.internal"}:
        return True
    return False


def resolve_host(hostname: str) -> list[str]:
    """Resolve A/AAAA; raise if any address is blocked or none found."""
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise EgressError(f"DNS resolution failed for {hostname}: {e}", code="EGRESS-DNS") from e

    ips: list[str] = []
    for info in infos:
        addr = info[4][0]
        try:
            ip_obj = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _is_blocked_ip(ip_obj):
            raise EgressBlockedError(
                f"Resolved IP {addr} for {hostname} is not allowed (private/reserved/metadata)"
            )
        if addr not in ips:
            ips.append(addr)

    if not ips:
        raise EgressError(f"No usable addresses for {hostname}", code="EGRESS-DNS")
    return ips


class EgressFetcher:
    """Inject this into connectors / verification services. Never raw httpx elsewhere for user URLs."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._global_sem = asyncio.Semaphore(20)

    def _host_sem(self, host: str) -> asyncio.Semaphore:
        if host not in self._semaphores:
            self._semaphores[host] = asyncio.Semaphore(4)
        return self._semaphores[host]

    def _validate_url(self, url: str) -> tuple[str, str, str]:
        parsed = urlparse(url)
        scheme = (parsed.scheme or "").lower()
        if scheme not in self.settings.egress_schemes:
            raise EgressBlockedError(f"Scheme not allowed: {scheme}")
        host = (parsed.hostname or "").lower()
        if not host:
            raise EgressError("URL missing hostname")
        # Block literal IPs that are private without DNS
        try:
            ip_obj = ipaddress.ip_address(host)
            if _is_blocked_ip(ip_obj):
                raise EgressBlockedError(f"Direct IP not allowed: {host}")
        except ValueError:
            pass  # hostname, not IP

        allow = self.settings.egress_allowlist_hosts
        if allow and host not in allow and not any(host.endswith("." + a) for a in allow):
            raise EgressBlockedError(f"Host not in allowlist: {host}")

        return scheme, host, url

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: Optional[dict[str, str]] = None,
        body: Optional[bytes] = None,
        timeout: Optional[float] = None,
        purpose: str = "generic",
    ) -> EgressResponse:
        import time

        scheme, host, url = self._validate_url(url)
        resolved = await asyncio.to_thread(resolve_host, host)

        timeout = timeout or self.settings.egress_timeout_seconds
        req_headers = {"User-Agent": f"DigiZafe-Egress/0.1 (+{purpose})"}
        if headers:
            # Prevent host override tricks
            headers = {k: v for k, v in headers.items() if k.lower() != "host"}
            req_headers.update(headers)

        t0 = time.perf_counter()
        async with self._global_sem, self._host_sem(host):
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout),
                follow_redirects=False,  # critical
                max_redirects=0,
                verify=True,
                http2=False,
            ) as client:
                try:
                    resp = await client.request(method.upper(), url, headers=req_headers, content=body)
                except httpx.HTTPError as e:
                    logger.warning("egress_http_error", url=url, host=host, error=str(e), purpose=purpose)
                    raise EgressError(f"HTTP error: {e}", code="EGRESS-HTTP") from e

        # Cap body
        content = resp.content
        max_b = self.settings.egress_max_response_bytes
        if len(content) > max_b:
            content = content[:max_b]
            logger.warning("egress_body_truncated", url=url, max=max_b)

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(
            "egress_fetch",
            purpose=purpose,
            host=host,
            status=resp.status_code,
            resolved=resolved,
            elapsed_ms=round(elapsed, 2),
        )
        return EgressResponse(
            status_code=resp.status_code,
            headers={k: v for k, v in resp.headers.items()},
            body=content,
            url=str(resp.url),
            resolved_ips=resolved,
            elapsed_ms=elapsed,
        )

    async def get_text(self, url: str, **kwargs: Any) -> str:
        r = await self.fetch(url, **kwargs)
        return r.body.decode("utf-8", errors="replace")


_fetcher: Optional[EgressFetcher] = None


def get_egress_fetcher() -> EgressFetcher:
    global _fetcher
    if _fetcher is None:
        _fetcher = EgressFetcher()
    return _fetcher
```

---

## 5. NEW: `backend/app/models/identifier.py`

```python
import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    String,
    Text,
    ForeignKey,
    UniqueConstraint,
    func,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.canonicalize import IdentifierType


class Identifier(Base):
    __tablename__ = "identifiers"
    __table_args__ = (
        UniqueConstraint("user_id", "type", "value_canonical", name="uq_identifiers_user_type_value"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    value_canonical: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    value_display: Mapped[str] = mapped_column(String(512), nullable=False)  # original-ish for UI
    value_blind: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_revalidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Soft metadata (never raw secrets)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class VerificationChallenge(Base):
    __tablename__ = "verification_challenges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identifier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)

    method: Mapped[str] = mapped_column(String(32), nullable=False)  # email_code | dns_txt | github_gist
    # Store only hash of secret token/code
    secret_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    # Public instructions payload (TXT name, gist URL hint, etc.)
    public_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

---

## 6. NEW: `backend/app/models/consent_egress.py`

```python
import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import Boolean, DateTime, String, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConsentRecord(Base):
    """User consent for processing / sending identifiers to third parties."""

    __tablename__ = "consent_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # e.g. "verification.dns", "discovery.xposedornot", "egress.github"
    scope: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    granted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class EgressLedger(Base):
    """Every outbound call that may send or derive from an identifier."""

    __tablename__ = "egress_ledger"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    identifier_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)

    purpose: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    destination_host: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False, default="GET")
    status_code: Mapped[Optional[int]] = mapped_column(nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Redacted summary only
    summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
```

---

## 7. UPDATE: `backend/app/models/__init__.py`

```python
from app.models.user import User, RefreshToken
from app.models.audit import AuditLog
from app.models.identifier import Identifier, VerificationChallenge
from app.models.consent_egress import ConsentRecord, EgressLedger

__all__ = [
    "User",
    "RefreshToken",
    "AuditLog",
    "Identifier",
    "VerificationChallenge",
    "ConsentRecord",
    "EgressLedger",
]
```

---

## 8. NEW: `backend/app/schemas/identifier.py`

```python
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.domain.canonicalize import IdentifierType


class IdentifierCreate(BaseModel):
    type: IdentifierType
    value: str = Field(..., min_length=1, max_length=512)


class IdentifierPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    value_display: str
    value_canonical: str  # owner may see full canonical
    is_verified: bool
    verified_at: Optional[datetime] = None
    verification_method: Optional[str] = None
    last_revalidated_at: Optional[datetime] = None
    created_at: datetime


class VerificationStartResponse(BaseModel):
    challenge_id: UUID
    method: str
    expires_at: datetime
    instructions: dict[str, Any]
    # Dev only — never in production responses if flag off
    dev_code: Optional[str] = None


class VerificationConfirmRequest(BaseModel):
    code: Optional[str] = None  # email_code
    # dns/github: server re-checks; optional client noop


class Message(BaseModel):
    message: str


class ConsentGrant(BaseModel):
    purpose: str
    scope: Optional[str] = None
    details: Optional[dict[str, Any]] = None
```

---

## 9. NEW: `backend/app/repositories/identifier_repository.py`

```python
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import select, update
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

    async def get(self, identifier_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Identifier]:
        result = await self.session.execute(
            select(Identifier).where(
                Identifier.id == identifier_id,
                Identifier.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_canonical(
        self, user_id: uuid.UUID, type_: str, value_canonical: str
    ) -> Optional[Identifier]:
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
        now = datetime.now(timezone.utc)
        row.is_verified = True
        row.verified_at = now
        row.verification_method = method
        row.last_revalidated_at = now
        await self.session.flush()

    async def mark_revalidated(self, row: Identifier) -> None:
        row.last_revalidated_at = datetime.now(timezone.utc)
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
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
        )
        self.session.add(ch)
        await self.session.flush()
        return ch

    async def get_challenge(
        self, challenge_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[VerificationChallenge]:
        result = await self.session.execute(
            select(VerificationChallenge).where(
                VerificationChallenge.id == challenge_id,
                VerificationChallenge.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def consume_challenge(self, ch: VerificationChallenge) -> None:
        ch.consumed_at = datetime.now(timezone.utc)
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
```

---

## 10. NEW: `backend/app/repositories/consent_egress_repository.py`

```python
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent_egress import ConsentRecord, EgressLedger
from app.core.correlation import get_correlation_id


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
```

---

## 11. NEW: `backend/app/services/consent_service.py`

```python
from __future__ import annotations

import uuid
from typing import Any, Optional

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
```

---

## 12. NEW: `backend/app/services/identifier_service.py`

```python
from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.canonicalize import (
    IdentifierType,
    canonicalize,
    display_redacted,
    CanonicalizationError,
)
from app.repositories.identifier_repository import IdentifierRepository
from app.security.keys import get_key_service
from app.services.audit_service import AuditService
from app.schemas.identifier import IdentifierPublic


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
```

---

## 13. NEW: `backend/app/services/verification_service.py`

```python
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.canonicalize import IdentifierType
from app.repositories.identifier_repository import IdentifierRepository
from app.security.egress import get_egress_fetcher, EgressError, EgressBlockedError
from app.services.audit_service import AuditService
from app.services.consent_service import ConsentService
from app.schemas.identifier import VerificationStartResponse

logger = get_logger(__name__)


class VerificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = IdentifierRepository(session)
        self.audit = AuditService(session)
        self.consent = ConsentService(session)
        self.egress = get_egress_fetcher()
        self.settings = get_settings()

    async def start(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        method: str | None = None,
    ) -> VerificationStartResponse:
        ident = await self.repo.get(identifier_id, user_id)
        if not ident:
            raise HTTPException(status_code=404, detail="Identifier not found")
        if ident.is_verified:
            raise HTTPException(status_code=400, detail="Already verified")

        itype = IdentifierType(ident.type)
        method = (method or self._default_method(itype)).lower()

        if method == "email_code":
            if itype != IdentifierType.EMAIL:
                raise HTTPException(status_code=400, detail="email_code only for email identifiers")
            return await self._start_email_code(user_id, ident)
        if method == "dns_txt":
            if itype != IdentifierType.DOMAIN:
                raise HTTPException(status_code=400, detail="dns_txt only for domain identifiers")
            return await self._start_dns_txt(user_id, ident)
        if method == "github_proof":
            if itype != IdentifierType.GITHUB_USERNAME:
                raise HTTPException(status_code=400, detail="github_proof only for github_username")
            return await self._start_github_proof(user_id, ident)

        raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")

    def _default_method(self, itype: IdentifierType) -> str:
        return {
            IdentifierType.EMAIL: "email_code",
            IdentifierType.DOMAIN: "dns_txt",
            IdentifierType.GITHUB_USERNAME: "github_proof",
            IdentifierType.USERNAME: "email_code",  # not auto — will fail type check
            IdentifierType.PHONE: "email_code",
        }.get(itype, "email_code")

    async def _start_email_code(self, user_id: uuid.UUID, ident) -> VerificationStartResponse:
        code = self.repo.new_numeric_code(self.settings.verification_email_code_length)
        ch = await self.repo.create_challenge(
            identifier_id=ident.id,
            user_id=user_id,
            method="email_code",
            raw_secret=code,
            public_payload={"channel": "email", "hint": "Enter the code (dev: returned in response)"},
            ttl_minutes=self.settings.verification_token_ttl_minutes,
        )
        # MVP free path: no SMTP required — log + optional expose
        logger.info(
            "verification_email_code_issued",
            user_id=str(user_id),
            identifier_id=str(ident.id),
            # never log full email in prod pipelines if avoidable
        )
        await self.audit.log(
            "verification.started",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(ident.id),
            details={"method": "email_code"},
        )
        dev_code = code if self.settings.verification_dev_expose_code and self.settings.is_development else None
        return VerificationStartResponse(
            challenge_id=ch.id,
            method="email_code",
            expires_at=ch.expires_at,
            instructions={
                "message": "Enter the verification code sent to your email.",
                "dev_note": "In development the code is returned in dev_code when VERIFICATION_DEV_EXPOSE_CODE=true",
            },
            dev_code=dev_code,
        )

    async def _start_dns_txt(self, user_id: uuid.UUID, ident) -> VerificationStartResponse:
        token = self.repo.new_token()
        record_name = f"_digizafe-verify.{ident.value_canonical}"
        record_value = f"digizafe-verification={token}"
        ch = await self.repo.create_challenge(
            identifier_id=ident.id,
            user_id=user_id,
            method="dns_txt",
            raw_secret=token,
            public_payload={
                "record_type": "TXT",
                "record_name": record_name,
                "record_value": record_value,
            },
            ttl_minutes=self.settings.verification_token_ttl_minutes,
        )
        await self.audit.log(
            "verification.started",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(ident.id),
            details={"method": "dns_txt"},
        )
        return VerificationStartResponse(
            challenge_id=ch.id,
            method="dns_txt",
            expires_at=ch.expires_at,
            instructions={
                "message": "Create the following DNS TXT record, wait for propagation, then confirm.",
                "record_type": "TXT",
                "record_name": record_name,
                "record_value": record_value,
                "also_accepted_on_apex": f"TXT on {ident.value_canonical} containing digizafe-verification={token}",
            },
        )

    async def _start_github_proof(self, user_id: uuid.UUID, ident) -> VerificationStartResponse:
        token = self.repo.new_token()
        # User creates a public gist OR puts token in a public repo README — we check via API
        # Simple free proof: create a public gist named digizafe-verify.txt containing the token
        ch = await self.repo.create_challenge(
            identifier_id=ident.id,
            user_id=user_id,
            method="github_proof",
            raw_secret=token,
            public_payload={
                "username": ident.value_canonical,
                "token": token,  # public by design — ownership proof
                "instruction": (
                    f"Create a public gist owned by {ident.value_canonical} "
                    f"with filename digizafe-verify.txt containing exactly: {token}"
                ),
            },
            ttl_minutes=self.settings.verification_token_ttl_minutes,
        )
        await self.audit.log(
            "verification.started",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(ident.id),
            details={"method": "github_proof"},
        )
        return VerificationStartResponse(
            challenge_id=ch.id,
            method="github_proof",
            expires_at=ch.expires_at,
            instructions=ch.public_payload or {},
        )

    async def confirm(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        challenge_id: uuid.UUID,
        code: str | None = None,
    ) -> dict[str, Any]:
        ident = await self.repo.get(identifier_id, user_id)
        if not ident:
            raise HTTPException(status_code=404, detail="Identifier not found")
        ch = await self.repo.get_challenge(challenge_id, user_id)
        if not ch or ch.identifier_id != ident.id:
            raise HTTPException(status_code=404, detail="Challenge not found")
        if ch.consumed_at is not None:
            raise HTTPException(status_code=400, detail="Challenge already used")
        if ch.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Challenge expired")

        ch.attempts += 1
        await self.session.flush()
        if ch.attempts > 10:
            raise HTTPException(status_code=429, detail="Too many attempts")

        ok = False
        if ch.method == "email_code":
            if not code:
                raise HTTPException(status_code=400, detail="code required")
            ok = self.repo.verify_secret(code.strip(), ch.secret_hash)
        elif ch.method == "dns_txt":
            ok = await self._check_dns_txt(ident, ch)
        elif ch.method == "github_proof":
            ok = await self._check_github_proof(user_id, ident, ch)
        else:
            raise HTTPException(status_code=400, detail="Unknown method")

        if not ok:
            await self.audit.log(
                "verification.failed",
                user_id=user_id,
                resource_type="identifier",
                resource_id=str(ident.id),
                details={"method": ch.method},
            )
            raise HTTPException(status_code=400, detail="Verification failed")

        await self.repo.consume_challenge(ch)
        await self.repo.mark_verified(ident, method=ch.method)
        await self.audit.log(
            "verification.succeeded",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(ident.id),
            details={"method": ch.method},
        )
        return {"message": "Identifier verified", "identifier_id": str(ident.id), "method": ch.method}

    async def _check_dns_txt(self, ident, ch) -> bool:
        """Resolve TXT via public DNS (dnspython) — no EgressFetcher HTTP needed."""
        import dns.asyncresolver
        import dns.rdatatype

        token = None
        # Recover token from public payload (it's ownership proof material)
        payload = ch.public_payload or {}
        record_value = payload.get("record_value", "")
        if "digizafe-verification=" in record_value:
            token = record_value.split("digizafe-verification=", 1)[-1].strip()
        if not token:
            return False

        names = [
            payload.get("record_name") or f"_digizafe-verify.{ident.value_canonical}",
            ident.value_canonical,
        ]
        resolver = dns.asyncresolver.Resolver()
        resolver.nameservers = ["1.1.1.1", "8.8.8.8"]  # public free resolvers
        resolver.lifetime = 10.0

        for name in names:
            try:
                answers = await resolver.resolve(name, "TXT")
            except Exception as e:
                logger.info("dns_txt_lookup_failed", name=name, error=str(e))
                continue
            for rdata in answers:
                # rdata.strings is list of bytes
                texts = []
                if hasattr(rdata, "strings"):
                    texts = [s.decode("utf-8", errors="replace") if isinstance(s, bytes) else str(s) for s in rdata.strings]
                else:
                    texts = [str(rdata).strip('"')]
                for t in texts:
                    if f"digizafe-verification={token}" in t or t.strip() == token:
                        # Also verify hash matches challenge
                        if self.repo.verify_secret(token, ch.secret_hash):
                            return True
        return False

    async def _check_github_proof(self, user_id: uuid.UUID, ident, ch) -> bool:
        """List public gists for user via GitHub API (free, rate-limited) through EgressFetcher."""
        payload = ch.public_payload or {}
        token = payload.get("token")
        username = ident.value_canonical
        if not token or not self.repo.verify_secret(token, ch.secret_hash):
            return False

        # Consent for sending username to GitHub
        await self.consent.ensure_consent(
            user_id,
            purpose="verification.github",
            auto_grant=True,  # explicit user action of starting verification
            scope=username,
        )

        url = f"https://api.github.com/users/{username}/gists?per_page=30"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"

        try:
            resp = await self.egress.fetch(
                url,
                headers=headers,
                purpose="verification.github",
            )
            await self.consent.record_egress(
                purpose="verification.github",
                destination_host="api.github.com",
                method="GET",
                status_code=resp.status_code,
                success=resp.status_code == 200,
                user_id=user_id,
                identifier_id=ident.id,
                summary={"username": username},
            )
        except (EgressError, EgressBlockedError) as e:
            logger.warning("github_egress_failed", error=str(e))
            return False

        if resp.status_code != 200:
            return False

        try:
            gists = json.loads(resp.body.decode("utf-8"))
        except Exception:
            return False

        if not isinstance(gists, list):
            return False

        for gist in gists:
            files = gist.get("files") or {}
            for fname, meta in files.items():
                if fname != "digizafe-verify.txt":
                    continue
                # Prefer raw_url fetch via egress
                raw_url = meta.get("raw_url")
                if not raw_url:
                    continue
                try:
                    raw_resp = await self.egress.fetch(
                        raw_url,
                        purpose="verification.github.raw",
                    )
                    await self.consent.record_egress(
                        purpose="verification.github.raw",
                        destination_host=urlparse(raw_url).hostname or "githubusercontent.com",
                        method="GET",
                        status_code=raw_resp.status_code,
                        success=raw_resp.status_code == 200,
                        user_id=user_id,
                        identifier_id=ident.id,
                    )
                    body = raw_resp.body.decode("utf-8", errors="replace").strip()
                    if token in body:
                        # Optional: ensure gist owner matches
                        owner = (gist.get("owner") or {}).get("login", "").lower()
                        if owner and owner != username.lower():
                            continue
                        return True
                except Exception as e:
                    logger.info("gist_raw_fetch_failed", error=str(e))
                    continue
        return False

    async def revalidate(self, user_id: uuid.UUID, identifier_id: uuid.UUID) -> dict[str, Any]:
        """
        Re-check ownership for already-verified identifiers.
        Email: requires new challenge (user in loop).
        Domain: re-query TXT if we stored method dns_txt — for MVP mark revalidated only if still verified flag.
        Full re-proof can re-run start/confirm.
        """
        ident = await self.repo.get(identifier_id, user_id)
        if not ident:
            raise HTTPException(status_code=404, detail="Identifier not found")
        if not ident.is_verified:
            raise HTTPException(status_code=400, detail="Not verified yet")

        # Policy: domain revalidation can re-check last DNS method if we keep token — we don't.
        # Sprint 2: touch last_revalidated_at and audit; deep re-proof via new challenge.
        await self.repo.mark_revalidated(ident)
        await self.audit.log(
            "verification.revalidated",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(ident.id),
            details={"method": ident.verification_method, "mode": "touch"},
        )
        return {
            "message": "Revalidation timestamp updated",
            "last_revalidated_at": ident.last_revalidated_at.isoformat() if ident.last_revalidated_at else None,
            "note": "For cryptographic re-proof, start a new verification challenge.",
        }
```

---

## 14. NEW: `backend/app/api/v1/identifiers.py`

```python
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, get_db
from app.domain.canonicalize import IdentifierType
from app.schemas.identifier import (
    IdentifierCreate,
    IdentifierPublic,
    VerificationStartResponse,
    VerificationConfirmRequest,
    Message,
    ConsentGrant,
)
from app.services.identifier_service import IdentifierService
from app.services.verification_service import VerificationService
from app.services.consent_service import ConsentService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/identifiers", tags=["identifiers"])


def _id_svc(db: AsyncSession = Depends(get_db)) -> IdentifierService:
    return IdentifierService(db)


def _ver_svc(db: AsyncSession = Depends(get_db)) -> VerificationService:
    return VerificationService(db)


def _consent_svc(db: AsyncSession = Depends(get_db)) -> ConsentService:
    return ConsentService(db)


@router.get("", response_model=list[IdentifierPublic])
async def list_identifiers(
    current_user: CurrentUser,
    svc: IdentifierService = Depends(_id_svc),
):
    return await svc.list(current_user.id)


@router.post("", response_model=IdentifierPublic, status_code=status.HTTP_201_CREATED)
async def create_identifier(
    body: IdentifierCreate,
    current_user: CurrentUser,
    svc: IdentifierService = Depends(_id_svc),
):
    return await svc.add(current_user.id, body.type, body.value)


@router.get("/{identifier_id}", response_model=IdentifierPublic)
async def get_identifier(
    identifier_id: UUID,
    current_user: CurrentUser,
    svc: IdentifierService = Depends(_id_svc),
):
    return await svc.get(current_user.id, identifier_id)


@router.delete("/{identifier_id}", response_model=Message)
async def delete_identifier(
    identifier_id: UUID,
    current_user: CurrentUser,
    svc: IdentifierService = Depends(_id_svc),
):
    await svc.delete(current_user.id, identifier_id)
    return Message(message="Deleted")


@router.post(
    "/{identifier_id}/verify/start",
    response_model=VerificationStartResponse,
)
async def start_verification(
    identifier_id: UUID,
    current_user: CurrentUser,
    method: str | None = Query(None, description="email_code | dns_txt | github_proof"),
    svc: VerificationService = Depends(_ver_svc),
):
    return await svc.start(current_user.id, identifier_id, method=method)


@router.post("/{identifier_id}/verify/confirm")
async def confirm_verification(
    identifier_id: UUID,
    body: VerificationConfirmRequest,
    current_user: CurrentUser,
    challenge_id: UUID = Query(...),
    svc: VerificationService = Depends(_ver_svc),
):
    return await svc.confirm(
        current_user.id,
        identifier_id,
        challenge_id,
        code=body.code,
    )


@router.post("/{identifier_id}/revalidate")
async def revalidate_identifier(
    identifier_id: UUID,
    current_user: CurrentUser,
    svc: VerificationService = Depends(_ver_svc),
):
    return await svc.revalidate(current_user.id, identifier_id)


@router.post("/consent", response_model=Message)
async def grant_consent(
    body: ConsentGrant,
    current_user: CurrentUser,
    svc: ConsentService = Depends(_consent_svc),
):
    await svc.grant(current_user.id, body.purpose, scope=body.scope, details=body.details)
    return Message(message="Consent recorded")
```

---

## 15. UPDATE: `backend/app/main.py`

```python
# ... existing imports ...
from app.api.v1 import health, auth, identifiers  # add identifiers

# ... lifespan unchanged ...

# Routers
app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(identifiers.router, prefix=settings.api_v1_prefix)

@app.get("/")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.2.0",
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
        "message": "DigiZafe Sprint 2 Identifiers & Verification — ready",
    }
```

Ensure `backend/app/api/v1/__init__.py` imports cleanly.

---

## 16. UPDATE: `backend/app/api/deps.py`

Add helpers (optional convenience):

```python
from app.services.identifier_service import IdentifierService
from app.services.verification_service import VerificationService
from app.services.consent_service import ConsentService


async def get_identifier_service(db: AsyncSession = Depends(get_db)) -> IdentifierService:
    return IdentifierService(db)


async def get_verification_service(db: AsyncSession = Depends(get_db)) -> VerificationService:
    return VerificationService(db)


async def get_consent_service(db: AsyncSession = Depends(get_db)) -> ConsentService:
    return ConsentService(db)
```

(`get_current_user` already sets `app.current_user_id` for RLS.)

---

## 17. UPDATE: `backend/app/alembic/env.py`

```python
from app.models.user import User, RefreshToken  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.identifier import Identifier, VerificationChallenge  # noqa: F401
from app.models.consent_egress import ConsentRecord, EgressLedger  # noqa: F401
```

---

## 18. Alembic migration: `sprint2_identifiers_verification`

```bash
docker compose exec api alembic revision -m "sprint2_identifiers_verification_egress"
```

Replace upgrade/downgrade with:

```python
"""sprint2_identifiers_verification_egress"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "sprint2_id_001"
down_revision: Union[str, None] = "sprint1_auth_001"  # ← set to your Sprint 1 revision id
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("value_canonical", sa.String(512), nullable=False),
        sa.Column("value_display", sa.String(512), nullable=False),
        sa.Column("value_blind", sa.String(64), nullable=True),
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_method", sa.String(64), nullable=True),
        sa.Column("last_revalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "type", "value_canonical", name="uq_identifiers_user_type_value"),
    )
    op.create_index("ix_identifiers_user_id", "identifiers", ["user_id"])
    op.create_index("ix_identifiers_type", "identifiers", ["type"])
    op.create_index("ix_identifiers_value_canonical", "identifiers", ["value_canonical"])
    op.create_index("ix_identifiers_is_verified", "identifiers", ["is_verified"])
    op.create_index("ix_identifiers_value_blind", "identifiers", ["value_blind"])

    op.create_table(
        "verification_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method", sa.String(32), nullable=False),
        sa.Column("secret_hash", sa.String(128), nullable=False),
        sa.Column("public_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_verification_challenges_identifier_id", "verification_challenges", ["identifier_id"])
    op.create_index("ix_verification_challenges_user_id", "verification_challenges", ["user_id"])

    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(128), nullable=False),
        sa.Column("scope", sa.String(256), nullable=True),
        sa.Column("granted", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_consent_records_user_id", "consent_records", ["user_id"])
    op.create_index("ix_consent_records_purpose", "consent_records", ["purpose"])

    op.create_table(
        "egress_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("purpose", sa.String(128), nullable=False),
        sa.Column("destination_host", sa.String(255), nullable=False),
        sa.Column("method", sa.String(16), server_default="GET", nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_egress_ledger_user_id", "egress_ledger", ["user_id"])
    op.create_index("ix_egress_ledger_identifier_id", "egress_ledger", ["identifier_id"])
    op.create_index("ix_egress_ledger_purpose", "egress_ledger", ["purpose"])
    op.create_index("ix_egress_ledger_created_at", "egress_ledger", ["created_at"])
    op.create_index("ix_egress_ledger_correlation_id", "egress_ledger", ["correlation_id"])

    # RLS
    for table in ("identifiers", "verification_challenges", "consent_records", "egress_ledger"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY identifiers_self ON identifiers
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    # Allow insert when setting is present (request path sets it after auth)
    op.execute("""
        CREATE POLICY verification_challenges_self ON verification_challenges
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY consent_self ON consent_records
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY egress_self_select ON egress_ledger
        FOR SELECT
        USING (
            user_id IS NULL
            OR user_id::text = current_setting('app.current_user_id', true)
        );
    """)
    op.execute("""
        CREATE POLICY egress_insert ON egress_ledger
        FOR INSERT
        WITH CHECK (true);
    """)

    # ---------- Verified-only trigger DESIGN (ready for Sprint 4 scan tables) ----------
    # Function lives now; trigger attaches when observations/findings/scans exist.
    op.execute("""
        CREATE OR REPLACE FUNCTION digizafe_enforce_verified_identifier()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_ok boolean;
        BEGIN
            -- Expect NEW.identifier_id to reference identifiers(id)
            SELECT is_verified INTO v_ok
            FROM identifiers
            WHERE id = NEW.identifier_id;

            IF v_ok IS DISTINCT FROM TRUE THEN
                RAISE EXCEPTION 'G1_VIOLATION: scans/findings only allowed for verified identifiers (identifier_id=%)',
                    NEW.identifier_id
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    # Example (commented until scans table exists in Sprint 4):
    # CREATE TRIGGER trg_scans_verified_only
    #   BEFORE INSERT OR UPDATE ON scans
    #   FOR EACH ROW EXECUTE FUNCTION digizafe_enforce_verified_identifier();


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS digizafe_enforce_verified_identifier() CASCADE")
    for pol, tbl in [
        ("egress_insert", "egress_ledger"),
        ("egress_self_select", "egress_ledger"),
        ("consent_self", "consent_records"),
        ("verification_challenges_self", "verification_challenges"),
        ("identifiers_self", "identifiers"),
    ]:
        op.execute(f"DROP POLICY IF EXISTS {pol} ON {tbl}")
    for table in ("egress_ledger", "consent_records", "verification_challenges", "identifiers"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
```

---

## 19. NEW: Unit tests

### `backend/tests/unit/test_canonicalize.py`

```python
import pytest
from app.domain.canonicalize import (
    canonicalize_email,
    canonicalize_domain,
    canonicalize_phone,
    canonicalize_github_username,
    CanonicalizationError,
    display_redacted,
    IdentifierType,
)


def test_email_gmail_dots_plus():
    assert canonicalize_email("F.O.O+tag@Gmail.com") == "foo@gmail.com"


def test_email_invalid():
    with pytest.raises(CanonicalizationError):
        canonicalize_email("not-an-email")


def test_domain():
    assert canonicalize_domain("https://WWW.Example.COM/path") == "www.example.com"


def test_phone_e164():
    assert canonicalize_phone("+1 (415) 555-2671") == "+14155552671"


def test_github():
    assert canonicalize_github_username("@Octocat") == "octocat"


def test_redact_email():
    r = display_redacted(IdentifierType.EMAIL, "ab@example.com")
    assert "***" in r
```

### `backend/tests/unit/test_egress_block.py`

```python
import pytest
from app.security.egress import resolve_host, EgressBlockedError, EgressFetcher, EgressError


def test_blocks_localhost_literal():
    f = EgressFetcher()
    with pytest.raises(EgressBlockedError):
        f._validate_url("http://127.0.0.1/")


def test_blocks_metadata_host_resolve(monkeypatch):
    # resolve_host should block 169.254.169.254 if somehow returned
    import app.security.egress as eg

    def fake_getaddrinfo(host, *a, **k):
        return [(None, None, None, None, ("169.254.169.254", 0))]

    monkeypatch.setattr(eg.socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(EgressBlockedError):
        resolve_host("evil.example")


def test_scheme_file_blocked():
    f = EgressFetcher()
    with pytest.raises(EgressBlockedError):
        f._validate_url("file:///etc/passwd")
```

---

## 20. Docs

### `docs/runbooks/identifiers-verification.md`

```markdown
# Identifiers & Verification (Sprint 2)

## G1 Self-only
- Discovery/remediation must call `IdentifierService.require_verified`.
- DB function `digizafe_enforce_verified_identifier()` is installed; attach trigger on scans/findings in Sprint 4.

## Methods
| Type | Method | How |
|------|--------|-----|
| email | email_code | Dev exposes code; prod SMTP later |
| domain | dns_txt | TXT `_digizafe-verify.<domain>` = digizafe-verification=&lt;token&gt; |
| github_username | github_proof | Public gist `digizafe-verify.txt` with token |

## Egress
- All external HTTP via `app.security.egress.EgressFetcher` only.
- Consent + `egress_ledger` for GitHub (and later XposedOrNot).

## API
- `POST /api/v1/identifiers`
- `POST /api/v1/identifiers/{id}/verify/start?method=`
- `POST /api/v1/identifiers/{id}/verify/confirm?challenge_id=`
- `POST /api/v1/identifiers/{id}/revalidate`
```

### `docs/adr/0014-egress-fetcher-ssrf.md` (stub)

```markdown
# ADR 0014 — Single SSRF-guarded EgressFetcher

## Decision
All non-browser egress uses one fetcher: scheme allowlist, DNS resolve, private/metadata IP block, no redirects, timeouts, size cap, per-host semaphore, ledger.

## Status
Accepted (Sprint 2)
```

---

# PART C — How to finish Sprint 2

```bash
# 1. Merge .env keys + rebuild
docker compose build api worker
docker compose up -d

# 2. Migrate (fix down_revision with your Sprint 1 rev)
docker compose exec api alembic upgrade head

# 3. Smoke flow
# Login first, export ACCESS=...

# Add email
curl -s -X POST http://localhost:8000/api/v1/identifiers \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d '{"type":"email","value":"you@example.com"}' | jq .

# Start verify (dev returns dev_code)
curl -s -X POST "http://localhost:8000/api/v1/identifiers/$ID/verify/start?method=email_code" \
  -H "Authorization: Bearer $ACCESS" | jq .

# Confirm
curl -s -X POST "http://localhost:8000/api/v1/identifiers/$ID/verify/confirm?challenge_id=$CH" \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d '{"code":"123456"}' | jq .

# Domain + DNS (set real TXT then confirm)
# GitHub: create public gist digizafe-verify.txt then confirm

# 4. Unit tests
docker compose exec api pytest backend/tests/unit/test_canonicalize.py backend/tests/unit/test_egress_block.py -v

# 5. Commit
git add .
git commit -m "feat(sprint-2): identifiers, canonicalize, EgressFetcher SSRF, verify email/dns/github, consent+egress ledger, verified-only trigger design"
```

---

# Sprint 2 Definition of Done Checklist

- [ ] MASTER_ENGINEERING_CONTEXT.md still respected  
- [ ] Canonicalization pure unit tests pass (email/domain/phone/github)  
- [ ] `EgressFetcher` blocks localhost, private ranges, metadata, file://  
- [ ] No raw `httpx` for user-influenced URLs outside EgressFetcher  
- [ ] CRUD identifiers under auth + RLS policies  
- [ ] Email verification (dev code path) end-to-end  
- [ ] DNS TXT verification path implemented (public resolvers)  
- [ ] GitHub gist proof via EgressFetcher + ledger  
- [ ] Consent records + egress_ledger written on third-party calls  
- [ ] Secrets in challenges stored hashed only  
- [ ] `digizafe_enforce_verified_identifier()` function exists for Sprint 4  
- [ ] `require_verified()` service gate ready for discovery  
- [ ] Audit events for create/delete/verify  
- [ ] Zero paid keys required  
- [ ] CI / unit tests green for new modules  

Once checked → **Sprint 2 complete**.  
Next: **Sprint 3 — Connector SDK & Free Surface Green** (SDK RateLimiter+Cache, **xposedornot primary**, pwned_passwords, crt.sh, RDAP, GitHub, Gravatar, consent/egress wired, admin toggle).

---

## Endpoint quick reference

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | /api/v1/identifiers | Bearer | List |
| POST | /api/v1/identifiers | Bearer | Add (unverified) |
| GET | /api/v1/identifiers/{id} | Bearer | Get |
| DELETE | /api/v1/identifiers/{id} | Bearer | Delete |
| POST | /api/v1/identifiers/{id}/verify/start | Bearer | Start challenge |
| POST | /api/v1/identifiers/{id}/verify/confirm | Bearer | Confirm |
| POST | /api/v1/identifiers/{id}/revalidate | Bearer | Touch revalidation |
| POST | /api/v1/identifiers/consent | Bearer | Grant consent |

---

**You are ready for Sprint 2.**  
Apply files in order, fix `down_revision`, migrate, smoke-test email verify, then commit.  

If you hit import/migration/RLS/DNS issues, paste the error for a surgical fix.  
When Sprint 2 is green, ask for **Sprint 3** the same way.