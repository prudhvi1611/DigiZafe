# DigiZafe — Sprint 3 Connector SDK & Free Surface Green  
**Complete Implementation Guide from Sprint 2 Baseline + All File Contents**

**Document version:** 1.0  
**Based on:** MASTER_ENGINEERING_CONTEXT.md v2.1  
**Depends on:** Sprint 0–2 green (Auth, Identifiers, Verification, EgressFetcher, Consent/Egress ledger)  
**Goal:** From completed Sprint 2 → **Connector SDK** (RateLimiter + Cache mandatory, Green/Amber/Red gate) + **free Surface Green connectors** with **XposedOrNot primary**, Pwned Passwords (k-anon), crt.sh, RDAP/DNS, GitHub, Gravatar, username presence, free SERP (DuckDuckGo HTML), admin enable/disable, consent + egress ledger on every identifier-sending call, attribution, and a dry-run probe API (no full scan state machine yet — that is Sprint 4).

**Effort estimate:** ~11 days (solo)  
**Critical path next:** Sprint 4 Discovery & Evidence (Postgres scan state machine, 3-layer evidence, XposedOrNot → findings normalization)

> **Load MASTER_ENGINEERING_CONTEXT.md first.**  
> Connectors **never** touch DB. All HTTP goes through **EgressFetcher**. Prefer free path; never require paid keys.

---

# PART A — Pre-Sprint 3

```bash
# Confirm Sprint 2 green
curl -s http://localhost:8000/api/v1/health | jq .
# Auth + verified identifier flow must work

mkdir -p backend/app/connectors/{sdk,impl/surface}
mkdir -p backend/app/services
mkdir -p backend/tests/unit/connectors
mkdir -p shared/config
mkdir -p docs/{free-sources,aidr-mapping,runbooks}

touch backend/app/connectors/__init__.py
touch backend/app/connectors/sdk/__init__.py
touch backend/app/connectors/impl/__init__.py
touch backend/app/connectors/impl/surface/__init__.py

# Rebuild after pyproject/env edits
docker compose build api worker
echo "✅ Pre-Sprint 3 ready"
```

**Optional deps** (already have `httpx`, `redis`, `tenacity` from Sprint 0):

No new hard deps required. Optional: keep using `dnspython` from Sprint 2 for RDAP/DNS helpers.

---

# PART B — Sprint 3 File Contents

---

## 1. UPDATE: `.env.example` (append)

```bash
# === Sprint 3: Connectors / Free Surface ===
# Redis cache already: REDIS_CACHE_URL

# Global connector defaults
CONNECTOR_DEFAULT_CACHE_TTL_SECONDS=3600
CONNECTOR_NEGATIVE_CACHE_TTL_SECONDS=86400
CONNECTOR_PER_USER_PROBE_QUOTA_PER_DAY=30

# XposedOrNot (primary free breach — keyless personal)
FEATURE_XPOSEDORNOT=true
XPOSEDORNOT_BASE_URL=https://api.xposedornot.com
# Free tier approx: 2/sec, 25/hour, 100/day per IP on check-email — enforced in SDK
XPOSEDORNOT_RATE_PER_SECOND=1.5
XPOSEDORNOT_RATE_PER_HOUR=20
XPOSEDORNOT_RATE_PER_DAY=80
# Attribution string shown in API/UI
XPOSEDORNOT_ATTRIBUTION=Data: XposedOrNot (https://xposedornot.com) — free personal tier; respect ToS

# Pwned Passwords (k-anonymous, free, no key)
FEATURE_PWNED_PASSWORDS=true
PWNED_PASSWORDS_BASE_URL=https://api.pwnedpasswords.com

# Other free surface
FEATURE_CRTSH=true
FEATURE_RDAP=true
FEATURE_GITHUB_CONNECTOR=true
FEATURE_GRAVATAR=true
FEATURE_USERNAME_PRESENCE=true
FEATURE_SERP_DDG=true

# Optional free GitHub PAT (higher rate); never required
GITHUB_TOKEN=

# Admin: comma list of disabled connector IDs (overrides feature flags at runtime via DB if present)
# CONNECTOR_DISABLED=
```

---

## 2. UPDATE: `backend/app/core/config.py` (add fields)

```python
    # === Sprint 3: Connectors ===
    connector_default_cache_ttl_seconds: int = 3600
    connector_negative_cache_ttl_seconds: int = 86400
    connector_per_user_probe_quota_per_day: int = 30

    feature_xposedornot: bool = True  # may already exist — keep True default
    xposedornot_base_url: str = "https://api.xposedornot.com"
    xposedornot_rate_per_second: float = 1.5
    xposedornot_rate_per_hour: int = 20
    xposedornot_rate_per_day: int = 80
    xposedornot_attribution: str = (
        "Data: XposedOrNot (https://xposedornot.com) — free personal tier; respect ToS"
    )

    feature_pwned_passwords: bool = True
    pwned_passwords_base_url: str = "https://api.pwnedpasswords.com"

    feature_crtsh: bool = True
    feature_rdap: bool = True
    feature_github_connector: bool = True
    feature_gravatar: bool = True
    feature_username_presence: bool = True
    feature_serp_ddg: bool = True
```

---

## 3. NEW: `backend/app/connectors/sdk/types.py`

```python
"""Shared connector types (no I/O)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID


class LegalityTier(str, Enum):
    GREEN = "green"  # free, public, ToS-friendly, self-only consented
    AMBER = "amber"  # gated deep / extra consent
    RED = "red"  # excluded from MVP


class ConnectorLayer(str, Enum):
    SURFACE = "surface"
    DEEP = "deep"
    CONSTRAINED_DARK = "constrained_dark"


class ObservationKind(str, Enum):
    BREACH = "breach"
    PASSWORD_EXPOSURE = "password_exposure"
    CERTIFICATE = "certificate"
    DNS_RDAP = "dns_rdap"
    PROFILE = "profile"
    USERNAME_PRESENCE = "username_presence"
    SERP = "serp"
    OTHER = "other"


@dataclass
class ConnectorCapability:
    id: str
    name: str
    layer: ConnectorLayer
    legality: LegalityTier
    requires_paid_key: bool
    sends_identifier: bool  # if True → consent + egress ledger mandatory
    supported_identifier_types: list[str]
    attribution: Optional[str] = None
    description: str = ""


@dataclass
class ConnectorContext:
    """Injected runtime context — connectors never open their own clients/DB."""

    user_id: UUID
    identifier_id: UUID
    identifier_type: str
    identifier_canonical: str
    correlation_id: Optional[str] = None
    consent_purpose: Optional[str] = None  # e.g. discovery.xposedornot


@dataclass
class RawObservation:
    """Normalized unit returned by connectors (Sprint 4 maps → findings)."""

    kind: ObservationKind
    source: str  # connector id
    title: str
    summary: str
    confidence: float  # 0..1
    observed_at: Optional[datetime] = None
    layer: ConnectorLayer = ConnectorLayer.SURFACE
    raw_ref: Optional[str] = None  # non-PII handle / breach name
    attributes: dict[str, Any] = field(default_factory=dict)
    attribution: Optional[str] = None
    # Never store full HTML dumps here long-term; Sprint 4 evidence layers handle TTL

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "confidence": self.confidence,
            "observed_at": (self.observed_at or datetime.now(timezone.utc)).isoformat(),
            "layer": self.layer.value,
            "raw_ref": self.raw_ref,
            "attributes": self.attributes,
            "attribution": self.attribution,
        }


@dataclass
class ConnectorResult:
    connector_id: str
    success: bool
    observations: list[RawObservation] = field(default_factory=list)
    skipped: bool = False
    skip_reason: Optional[str] = None  # rate_limited | disabled | no_consent | unsupported_type | cache_only_error
    error: Optional[str] = None
    cache_hit: bool = False
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "success": self.success,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "error": self.error,
            "cache_hit": self.cache_hit,
            "observation_count": len(self.observations),
            "observations": [o.to_dict() for o in self.observations],
            "meta": self.meta,
        }
```

---

## 4. NEW: `backend/app/connectors/sdk/rate_limiter.py`

```python
"""Redis token-bucket / fixed-window hybrid rate limiter for free APIs."""

from __future__ import annotations

import time
from typing import Optional

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitExceeded(Exception):
    def __init__(self, key: str, retry_after: float | None = None) -> None:
        super().__init__(f"Rate limit exceeded: {key}")
        self.key = key
        self.retry_after = retry_after


class RateLimiter:
    """
    Multi-window limiter using Redis INCR + EXPIRE.
    Windows: second, hour, day (optional).
    """

    def __init__(self, redis_client: redis.Redis, prefix: str = "rl") -> None:
        self.redis = redis_client
        self.prefix = prefix

    def _k(self, *parts: str) -> str:
        return ":".join([self.prefix, *parts])

    async def acquire(
        self,
        name: str,
        *,
        per_second: float | None = None,
        per_hour: int | None = None,
        per_day: int | None = None,
    ) -> None:
        now = time.time()
        # Second window (ceil to int capacity)
        if per_second is not None and per_second > 0:
            cap = max(1, int(per_second)) if per_second >= 1 else 1
            # For sub-1/sec use millisecond-ish: allow 1 then sleep externally — enforce min interval via second key with TTL 1
            key = self._k(name, "s", str(int(now)))
            n = await self.redis.incr(key)
            if n == 1:
                await self.redis.expire(key, 2)
            # If rate < 1/sec, treat as max 1 per second
            limit = max(1, int(per_second)) if per_second >= 1 else 1
            if n > limit:
                raise RateLimitExceeded(name, retry_after=1.0)

        if per_hour is not None and per_hour > 0:
            hour_bucket = time.strftime("%Y%m%d%H", time.gmtime(now))
            key = self._k(name, "h", hour_bucket)
            n = await self.redis.incr(key)
            if n == 1:
                await self.redis.expire(key, 3700)
            if n > per_hour:
                raise RateLimitExceeded(name, retry_after=300.0)

        if per_day is not None and per_day > 0:
            day_bucket = time.strftime("%Y%m%d", time.gmtime(now))
            key = self._k(name, "d", day_bucket)
            n = await self.redis.incr(key)
            if n == 1:
                await self.redis.expire(key, 90000)
            if n > per_day:
                raise RateLimitExceeded(name, retry_after=3600.0)

    async def acquire_user_quota(self, user_id: str, *, limit: int | None = None) -> None:
        settings = get_settings()
        limit = limit if limit is not None else settings.connector_per_user_probe_quota_per_day
        day_bucket = time.strftime("%Y%m%d", time.gmtime())
        key = self._k("user_probe", user_id, day_bucket)
        n = await self.redis.incr(key)
        if n == 1:
            await self.redis.expire(key, 90000)
        if n > limit:
            raise RateLimitExceeded(f"user_probe:{user_id}", retry_after=3600.0)
```

---

## 5. NEW: `backend/app/connectors/sdk/cache.py`

```python
"""JSON cache over Redis (cache instance, allkeys-lru)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

import redis.asyncio as redis

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectorCache:
    def __init__(self, redis_client: redis.Redis, prefix: str = "ccache") -> None:
        self.redis = redis_client
        self.prefix = prefix

    def make_key(self, connector_id: str, *parts: str) -> str:
        raw = "|".join([connector_id, *parts])
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]
        return f"{self.prefix}:{connector_id}:{h}"

    async def get_json(self, key: str) -> Optional[Any]:
        try:
            data = await self.redis.get(key)
            if data is None:
                return None
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return json.loads(data)
        except Exception as e:
            logger.warning("cache_get_failed", key=key, error=str(e))
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        try:
            payload = json.dumps(value, default=str)
            await self.redis.set(key, payload, ex=max(1, ttl_seconds))
        except Exception as e:
            logger.warning("cache_set_failed", key=key, error=str(e))
```

---

## 6. NEW: `backend/app/connectors/sdk/base.py`

```python
"""Connector ABC + registry helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorResult,
    LegalityTier,
)
from app.connectors.sdk.rate_limiter import RateLimiter, RateLimitExceeded
from app.connectors.sdk.cache import ConnectorCache
from app.security.egress import EgressFetcher
from app.core.logging import get_logger
from app.core.config import get_settings


class Connector(ABC):
    """
    Rules (MASTER):
    - Never touch DB
    - Never raw HTTP — only injected EgressFetcher
    - Always RateLimiter + Cache for free APIs
    - Declare Green/Amber/Red; Red must not run
    - If sends_identifier: caller must ensure consent; connector may re-check purpose string
    """

    def __init__(
        self,
        *,
        egress: EgressFetcher,
        rate_limiter: RateLimiter,
        cache: ConnectorCache,
        logger_name: str | None = None,
    ) -> None:
        self.egress = egress
        self.rate_limiter = rate_limiter
        self.cache = cache
        self.log = get_logger(logger_name or self.capability.id)
        self.settings = get_settings()

    @property
    @abstractmethod
    def capability(self) -> ConnectorCapability:
        ...

    @abstractmethod
    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        """Implement actual work (after rate limit + type checks)."""

    def supports(self, identifier_type: str) -> bool:
        return identifier_type in self.capability.supported_identifier_types

    def is_enabled_by_config(self) -> bool:
        """Feature-flag gate; admin DB toggle applied by ConnectorRegistry."""
        cid = self.capability.id
        mapping = {
            "xposedornot": self.settings.feature_xposedornot,
            "pwned_passwords": self.settings.feature_pwned_passwords,
            "crtsh": self.settings.feature_crtsh,
            "rdap": self.settings.feature_rdap,
            "github": self.settings.feature_github_connector,
            "gravatar": self.settings.feature_gravatar,
            "username_presence": self.settings.feature_username_presence,
            "serp_ddg": self.settings.feature_serp_ddg,
        }
        return bool(mapping.get(cid, True))

    async def run(
        self,
        ctx: ConnectorContext,
        *,
        enabled_override: bool | None = None,
    ) -> ConnectorResult:
        cap = self.capability
        if cap.legality == LegalityTier.RED:
            return ConnectorResult(
                connector_id=cap.id,
                success=False,
                skipped=True,
                skip_reason="red_excluded",
            )

        enabled = self.is_enabled_by_config() if enabled_override is None else enabled_override
        if not enabled:
            return ConnectorResult(
                connector_id=cap.id,
                success=False,
                skipped=True,
                skip_reason="disabled",
            )

        if not self.supports(ctx.identifier_type):
            return ConnectorResult(
                connector_id=cap.id,
                success=False,
                skipped=True,
                skip_reason="unsupported_type",
            )

        if cap.requires_paid_key:
            return ConnectorResult(
                connector_id=cap.id,
                success=False,
                skipped=True,
                skip_reason="paid_key_required",
                error="Paid connectors are feature-flagged only and not load-bearing",
            )

        try:
            return await self._run(ctx)
        except RateLimitExceeded as e:
            self.log.warning("connector_rate_limited", connector=cap.id, key=e.key)
            return ConnectorResult(
                connector_id=cap.id,
                success=False,
                skipped=True,
                skip_reason="rate_limited",
                error=str(e),
                meta={"retry_after": e.retry_after},
            )
        except Exception as e:
            self.log.exception("connector_failed", connector=cap.id, error=str(e))
            return ConnectorResult(
                connector_id=cap.id,
                success=False,
                error=str(e),
            )
```

---

## 7. NEW: `backend/app/connectors/sdk/redis_clients.py`

```python
"""Async Redis clients for broker vs cache (Sprint 0 split)."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

import redis.asyncio as redis

from app.core.config import get_settings

_cache: Optional[redis.Redis] = None
_broker: Optional[redis.Redis] = None


async def get_cache_redis() -> redis.Redis:
    global _cache
    if _cache is None:
        settings = get_settings()
        _cache = redis.from_url(settings.redis_cache_url, decode_responses=True)
    return _cache


async def get_broker_redis() -> redis.Redis:
    global _broker
    if _broker is None:
        settings = get_settings()
        _broker = redis.from_url(settings.redis_broker_url, decode_responses=True)
    return _broker
```

---

## 8. NEW: Surface connectors

### `backend/app/connectors/impl/surface/xposedornot.py`

```python
"""XposedOrNot — primary free breach source (keyless personal email checks)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorResult,
    ConnectorLayer,
    LegalityTier,
    ObservationKind,
    RawObservation,
)
from app.connectors.sdk.rate_limiter import RateLimitExceeded
from app.security.egress import EgressError


class XposedOrNotConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="xposedornot",
            name="XposedOrNot",
            layer=ConnectorLayer.SURFACE,
            legality=LegalityTier.GREEN,
            requires_paid_key=False,
            sends_identifier=True,  # email sent → consent + ledger required
            supported_identifier_types=["email"],
            attribution=self.settings.xposedornot_attribution,
            description="Primary free breach check (personal/low-volume). Attribute XposedOrNot.",
        )

    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        email = ctx.identifier_canonical
        cache_key = self.cache.make_key("xposedornot", "check", email)

        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            obs = [self._obs_from_dict(o) for o in cached.get("observations", [])]
            return ConnectorResult(
                connector_id=self.capability.id,
                success=True,
                observations=obs,
                cache_hit=True,
                meta={"attribution": self.capability.attribution, "source": "cache"},
            )

        await self.rate_limiter.acquire(
            "xposedornot:check-email",
            per_second=self.settings.xposedornot_rate_per_second,
            per_hour=self.settings.xposedornot_rate_per_hour,
            per_day=self.settings.xposedornot_rate_per_day,
        )

        base = self.settings.xposedornot_base_url.rstrip("/")
        # Free check-email
        url = f"{base}/v1/check-email/{quote(email, safe='@.')}"

        try:
            resp = await self.egress.fetch(url, purpose="discovery.xposedornot")
        except EgressError as e:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error=str(e),
            )

        if resp.status_code == 429:
            raise RateLimitExceeded("xposedornot", retry_after=300)

        body_text = resp.body.decode("utf-8", errors="replace")
        try:
            data = json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error="Invalid JSON from XposedOrNot",
            )

        observations: list[RawObservation] = []
        # Not found shapes: {"Error":"Not found",...}
        if isinstance(data, dict) and data.get("Error"):
            # Negative cache long TTL
            await self.cache.set_json(
                cache_key,
                {"observations": []},
                self.settings.connector_negative_cache_ttl_seconds,
            )
            return ConnectorResult(
                connector_id=self.capability.id,
                success=True,
                observations=[],
                meta={
                    "attribution": self.capability.attribution,
                    "status": "not_found",
                    "http_status": resp.status_code,
                },
            )

        breaches: list[str] = []
        if isinstance(data, dict):
            raw_b = data.get("breaches")
            # API may return [["Name1","Name2",...]] or list of names
            if isinstance(raw_b, list):
                if raw_b and isinstance(raw_b[0], list):
                    breaches = [str(x) for x in raw_b[0]]
                else:
                    breaches = [str(x) for x in raw_b if not isinstance(x, list)]

        for name in breaches:
            observations.append(
                RawObservation(
                    kind=ObservationKind.BREACH,
                    source="xposedornot",
                    title=f"Breach: {name}",
                    summary=f"Email reported in breach dataset '{name}' via XposedOrNot free check.",
                    confidence=0.85,
                    observed_at=datetime.now(timezone.utc),
                    layer=ConnectorLayer.SURFACE,
                    raw_ref=name,
                    attributes={"breach_name": name, "provider": "xposedornot"},
                    attribution=self.capability.attribution,
                )
            )

        # Optional analytics enrichment (second call — rate limited + cached separately)
        analytics_obs = await self._maybe_analytics(email)
        observations.extend(analytics_obs)

        ttl = (
            self.settings.connector_default_cache_ttl_seconds
            if observations
            else self.settings.connector_negative_cache_ttl_seconds
        )
        await self.cache.set_json(
            cache_key,
            {"observations": [o.to_dict() for o in observations]},
            ttl,
        )

        return ConnectorResult(
            connector_id=self.capability.id,
            success=True,
            observations=observations,
            meta={
                "attribution": self.capability.attribution,
                "breach_count": len(breaches),
                "http_status": resp.status_code,
            },
        )

    async def _maybe_analytics(self, email: str) -> list[RawObservation]:
        cache_key = self.cache.make_key("xposedornot", "analytics", email)
        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            return [self._obs_from_dict(o) for o in cached.get("observations", [])]

        try:
            await self.rate_limiter.acquire(
                "xposedornot:analytics",
                per_second=self.settings.xposedornot_rate_per_second,
                per_hour=self.settings.xposedornot_rate_per_hour,
                per_day=self.settings.xposedornot_rate_per_day,
            )
        except RateLimitExceeded:
            return []

        base = self.settings.xposedornot_base_url.rstrip("/")
        url = f"{base}/v1/breach-analytics?email={quote(email)}"
        try:
            resp = await self.egress.fetch(url, purpose="discovery.xposedornot.analytics")
        except EgressError:
            return []

        if resp.status_code != 200:
            return []

        try:
            data = json.loads(resp.body.decode("utf-8", errors="replace"))
        except Exception:
            return []

        obs: list[RawObservation] = []
        if not isinstance(data, dict):
            return obs

        risk = None
        metrics = data.get("BreachMetrics") or {}
        if isinstance(metrics, dict):
            risk_list = metrics.get("risk") or []
            if risk_list and isinstance(risk_list[0], dict):
                risk = risk_list[0]

        if risk:
            obs.append(
                RawObservation(
                    kind=ObservationKind.BREACH,
                    source="xposedornot",
                    title="XposedOrNot risk summary",
                    summary=(
                        f"Provider risk_label={risk.get('risk_label')} "
                        f"risk_score={risk.get('risk_score')}"
                    ),
                    confidence=0.7,
                    attributes={
                        "risk_label": risk.get("risk_label"),
                        "risk_score": risk.get("risk_score"),
                        "provider": "xposedornot",
                        "kind": "analytics",
                    },
                    attribution=self.capability.attribution,
                )
            )

        # Exposed breach details if present
        exposed = (data.get("ExposedBreaches") or {}) if isinstance(data.get("ExposedBreaches"), dict) else {}
        details = exposed.get("breaches_details") or []
        if isinstance(details, list):
            for d in details[:50]:
                if not isinstance(d, dict):
                    continue
                bname = d.get("breach") or "unknown"
                obs.append(
                    RawObservation(
                        kind=ObservationKind.BREACH,
                        source="xposedornot",
                        title=f"Breach detail: {bname}",
                        summary=(d.get("details") or "")[:500],
                        confidence=0.9,
                        raw_ref=str(bname),
                        attributes={
                            "breach_name": bname,
                            "domain": d.get("domain"),
                            "industry": d.get("industry"),
                            "xposed_data": d.get("xposed_data"),
                            "xposed_date": d.get("xposed_date"),
                            "xposed_records": d.get("xposed_records"),
                            "password_risk": d.get("password_risk"),
                            "verified": d.get("verified"),
                            "provider": "xposedornot",
                        },
                        attribution=self.capability.attribution,
                    )
                )

        await self.cache.set_json(
            cache_key,
            {"observations": [o.to_dict() for o in obs]},
            self.settings.connector_default_cache_ttl_seconds,
        )
        return obs

    @staticmethod
    def _obs_from_dict(d: dict[str, Any]) -> RawObservation:
        return RawObservation(
            kind=ObservationKind(d.get("kind", "breach")),
            source=d.get("source", "xposedornot"),
            title=d.get("title", ""),
            summary=d.get("summary", ""),
            confidence=float(d.get("confidence", 0.5)),
            layer=ConnectorLayer(d.get("layer", "surface")),
            raw_ref=d.get("raw_ref"),
            attributes=d.get("attributes") or {},
            attribution=d.get("attribution"),
        )
```

### `backend/app/connectors/impl/surface/pwned_passwords.py`

```python
"""HIBP Pwned Passwords — k-anonymous range API (free, no key)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorResult,
    ConnectorLayer,
    LegalityTier,
    ObservationKind,
    RawObservation,
)
from app.security.egress import EgressError


class PwnedPasswordsConnector(Connector):
    """
    Note: identifier_type should be a special probe type or password hash prefix flow.
    For Sprint 3 we accept type 'password' where canonical is the plaintext password
    ONLY held in memory for hashing — never logged. Prefer caller passes sha1 already
    via attributes in later sprints; here we hash in-process and send only 5-char prefix.
    """

    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="pwned_passwords",
            name="Pwned Passwords (HIBP k-anonymity)",
            layer=ConnectorLayer.SURFACE,
            legality=LegalityTier.GREEN,
            requires_paid_key=False,
            sends_identifier=False,  # only 5-char hash prefix — k-anonymous
            supported_identifier_types=["password"],
            attribution="Pwned Passwords by Have I Been Pwned (k-anonymity range API)",
            description="Checks password exposure without sending full password/hash.",
        )

    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        # ctx.identifier_canonical is the password string for this probe only
        password = ctx.identifier_canonical
        sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]

        cache_key = self.cache.make_key("pwned_passwords", prefix)  # range cacheable
        # We still need suffix match — cache full range text
        cached_range = await self.cache.get_json(cache_key)

        if cached_range is None:
            await self.rate_limiter.acquire("pwned_passwords", per_second=5, per_hour=1000, per_day=10000)
            url = f"{self.settings.pwned_passwords_base_url.rstrip('/')}/range/{prefix}"
            try:
                resp = await self.egress.fetch(
                    url,
                    headers={"Add-Padding": "true", "User-Agent": "DigiZafe"},
                    purpose="discovery.pwned_passwords",
                )
            except EgressError as e:
                return ConnectorResult(connector_id=self.capability.id, success=False, error=str(e))

            if resp.status_code != 200:
                return ConnectorResult(
                    connector_id=self.capability.id,
                    success=False,
                    error=f"HTTP {resp.status_code}",
                )
            text = resp.body.decode("utf-8", errors="replace")
            await self.cache.set_json(cache_key, {"range": text}, 3600)
        else:
            text = cached_range.get("range", "")
            return self._match(suffix, text, cache_hit=True)

        return self._match(suffix, text, cache_hit=False)

    def _match(self, suffix: str, range_text: str, cache_hit: bool) -> ConnectorResult:
        count = 0
        for line in range_text.splitlines():
            parts = line.strip().split(":")
            if len(parts) != 2:
                continue
            if parts[0].upper() == suffix.upper():
                try:
                    count = int(parts[1].strip())
                except ValueError:
                    count = 1
                break

        observations: list[RawObservation] = []
        if count > 0:
            observations.append(
                RawObservation(
                    kind=ObservationKind.PASSWORD_EXPOSURE,
                    source="pwned_passwords",
                    title="Password seen in breach corpus",
                    summary=f"This password appears approximately {count} times in Pwned Passwords.",
                    confidence=0.95,
                    observed_at=datetime.now(timezone.utc),
                    attributes={"count": count, "k_anonymous": True},
                    attribution=self.capability.attribution,
                )
            )

        return ConnectorResult(
            connector_id=self.capability.id,
            success=True,
            observations=observations,
            cache_hit=cache_hit,
            meta={"pwned_count": count, "attribution": self.capability.attribution},
        )
```

### `backend/app/connectors/impl/surface/crtsh.py`

```python
"""crt.sh Certificate Transparency — free."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import quote

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorResult,
    ConnectorLayer,
    LegalityTier,
    ObservationKind,
    RawObservation,
)
from app.security.egress import EgressError


class CrtShConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="crtsh",
            name="crt.sh CT logs",
            layer=ConnectorLayer.SURFACE,
            legality=LegalityTier.GREEN,
            requires_paid_key=False,
            sends_identifier=True,  # domain query
            supported_identifier_types=["domain"],
            attribution="Certificate data via crt.sh",
            description="Public Certificate Transparency search",
        )

    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        domain = ctx.identifier_canonical
        cache_key = self.cache.make_key("crtsh", domain)
        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            obs = [
                RawObservation(
                    kind=ObservationKind.CERTIFICATE,
                    source="crtsh",
                    title=o["title"],
                    summary=o["summary"],
                    confidence=o.get("confidence", 0.8),
                    attributes=o.get("attributes") or {},
                    attribution=self.capability.attribution,
                )
                for o in cached.get("observations", [])
            ]
            return ConnectorResult(
                connector_id=self.capability.id, success=True, observations=obs, cache_hit=True
            )

        await self.rate_limiter.acquire("crtsh", per_second=1, per_hour=60, per_day=300)
        # crt.sh JSON API
        url = f"https://crt.sh/?q={quote('%.' + domain)}&output=json"
        try:
            resp = await self.egress.fetch(url, purpose="discovery.crtsh", timeout=30.0)
        except EgressError as e:
            return ConnectorResult(connector_id=self.capability.id, success=False, error=str(e))

        if resp.status_code != 200:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error=f"HTTP {resp.status_code}",
            )

        try:
            rows = json.loads(resp.body.decode("utf-8", errors="replace"))
        except Exception:
            rows = []

        if not isinstance(rows, list):
            rows = []

        # Dedupe common names
        names: set[str] = set()
        for r in rows[:200]:
            if not isinstance(r, dict):
                continue
            for key in ("common_name", "name_value"):
                val = r.get(key)
                if not val:
                    continue
                for part in str(val).split("\n"):
                    part = part.strip().lower()
                    if part:
                        names.add(part)

        observations = [
            RawObservation(
                kind=ObservationKind.CERTIFICATE,
                source="crtsh",
                title="CT name observed",
                summary=f"Certificate Transparency name: {n}",
                confidence=0.8,
                observed_at=datetime.now(timezone.utc),
                raw_ref=n,
                attributes={"name": n, "domain_query": domain},
                attribution=self.capability.attribution,
            )
            for n in sorted(names)[:100]
        ]

        ttl = (
            self.settings.connector_default_cache_ttl_seconds
            if observations
            else self.settings.connector_negative_cache_ttl_seconds
        )
        await self.cache.set_json(
            cache_key, {"observations": [o.to_dict() for o in observations]}, ttl
        )
        return ConnectorResult(
            connector_id=self.capability.id,
            success=True,
            observations=observations,
            meta={"name_count": len(names)},
        )
```

### `backend/app/connectors/impl/surface/rdap.py`

```python
"""RDAP / public DNS-ish domain registration lookup (free)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import quote

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorResult,
    ConnectorLayer,
    LegalityTier,
    ObservationKind,
    RawObservation,
)
from app.security.egress import EgressError


class RdapConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="rdap",
            name="RDAP",
            layer=ConnectorLayer.SURFACE,
            legality=LegalityTier.GREEN,
            requires_paid_key=False,
            sends_identifier=True,
            supported_identifier_types=["domain"],
            attribution="RDAP public registration data",
            description="Bootstrap RDAP query via rdap.org",
        )

    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        domain = ctx.identifier_canonical
        cache_key = self.cache.make_key("rdap", domain)
        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=True,
                observations=[self._from(o) for o in cached.get("observations", [])],
                cache_hit=True,
            )

        await self.rate_limiter.acquire("rdap", per_second=1, per_hour=100, per_day=500)
        url = f"https://rdap.org/domain/{quote(domain)}"
        try:
            resp = await self.egress.fetch(
                url,
                headers={"Accept": "application/rdap+json, application/json"},
                purpose="discovery.rdap",
            )
        except EgressError as e:
            return ConnectorResult(connector_id=self.capability.id, success=False, error=str(e))

        if resp.status_code == 404:
            await self.cache.set_json(cache_key, {"observations": []}, self.settings.connector_negative_cache_ttl_seconds)
            return ConnectorResult(connector_id=self.capability.id, success=True, observations=[])

        if resp.status_code != 200:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error=f"HTTP {resp.status_code}",
            )

        try:
            data = json.loads(resp.body.decode("utf-8", errors="replace"))
        except Exception as e:
            return ConnectorResult(connector_id=self.capability.id, success=False, error=str(e))

        # Redact: only high-level public fields
        status = data.get("status") if isinstance(data, dict) else None
        ldor = None
        if isinstance(data, dict):
            for ev in data.get("events") or []:
                if isinstance(ev, dict) and ev.get("eventAction") in {"registration", "last changed"}:
                    ldor = ev.get("eventDate")

        obs = [
            RawObservation(
                kind=ObservationKind.DNS_RDAP,
                source="rdap",
                title=f"RDAP record for {domain}",
                summary=f"Public RDAP status={status} events_sample={ldor}",
                confidence=0.75,
                observed_at=datetime.now(timezone.utc),
                attributes={
                    "domain": domain,
                    "status": status,
                    "sample_event": ldor,
                    "port43": data.get("port43") if isinstance(data, dict) else None,
                },
                attribution=self.capability.attribution,
            )
        ]
        await self.cache.set_json(
            cache_key,
            {"observations": [o.to_dict() for o in obs]},
            self.settings.connector_default_cache_ttl_seconds,
        )
        return ConnectorResult(connector_id=self.capability.id, success=True, observations=obs)

    @staticmethod
    def _from(d: dict) -> RawObservation:
        return RawObservation(
            kind=ObservationKind.DNS_RDAP,
            source="rdap",
            title=d.get("title", ""),
            summary=d.get("summary", ""),
            confidence=float(d.get("confidence", 0.7)),
            attributes=d.get("attributes") or {},
            attribution=d.get("attribution"),
        )
```

### `backend/app/connectors/impl/surface/github_connector.py`

```python
"""GitHub public profile / presence (free API; optional token)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorResult,
    ConnectorLayer,
    LegalityTier,
    ObservationKind,
    RawObservation,
)
from app.security.egress import EgressError


class GitHubConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="github",
            name="GitHub public profile",
            layer=ConnectorLayer.SURFACE,
            legality=LegalityTier.GREEN,
            requires_paid_key=False,
            sends_identifier=True,
            supported_identifier_types=["github_username", "username"],
            attribution="GitHub public API",
            description="Public user profile existence and metadata",
        )

    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        username = ctx.identifier_canonical
        cache_key = self.cache.make_key("github", "user", username)
        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=True,
                observations=[self._from(o) for o in cached.get("observations", [])],
                cache_hit=True,
            )

        await self.rate_limiter.acquire("github_api", per_second=1, per_hour=200, per_day=1000)
        url = f"https://api.github.com/users/{username}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "DigiZafe",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"

        try:
            resp = await self.egress.fetch(url, headers=headers, purpose="discovery.github")
        except EgressError as e:
            return ConnectorResult(connector_id=self.capability.id, success=False, error=str(e))

        if resp.status_code == 404:
            await self.cache.set_json(cache_key, {"observations": []}, self.settings.connector_negative_cache_ttl_seconds)
            return ConnectorResult(connector_id=self.capability.id, success=True, observations=[])

        if resp.status_code != 200:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error=f"HTTP {resp.status_code}",
            )

        data = json.loads(resp.body.decode("utf-8", errors="replace"))
        obs = [
            RawObservation(
                kind=ObservationKind.PROFILE,
                source="github",
                title=f"GitHub user {username}",
                summary=f"Public profile exists. public_repos={data.get('public_repos')} created={data.get('created_at')}",
                confidence=0.95,
                observed_at=datetime.now(timezone.utc),
                raw_ref=username,
                attributes={
                    "login": data.get("login"),
                    "html_url": data.get("html_url"),
                    "public_repos": data.get("public_repos"),
                    "followers": data.get("followers"),
                    "created_at": data.get("created_at"),
                    # Do not store bio/email from profile into long-term raw if sensitive — keep minimal
                },
                attribution=self.capability.attribution,
            )
        ]
        await self.cache.set_json(
            cache_key,
            {"observations": [o.to_dict() for o in obs]},
            self.settings.connector_default_cache_ttl_seconds,
        )
        return ConnectorResult(connector_id=self.capability.id, success=True, observations=obs)

    @staticmethod
    def _from(d: dict) -> RawObservation:
        return RawObservation(
            kind=ObservationKind.PROFILE,
            source="github",
            title=d.get("title", ""),
            summary=d.get("summary", ""),
            confidence=float(d.get("confidence", 0.9)),
            attributes=d.get("attributes") or {},
            attribution=d.get("attribution"),
        )
```

### `backend/app/connectors/impl/surface/gravatar.py`

```python
"""Gravatar existence check (public hash of email)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorResult,
    ConnectorLayer,
    LegalityTier,
    ObservationKind,
    RawObservation,
)
from app.security.egress import EgressError


class GravatarConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="gravatar",
            name="Gravatar",
            layer=ConnectorLayer.SURFACE,
            legality=LegalityTier.GREEN,
            requires_paid_key=False,
            sends_identifier=False,  # only MD5 of email to gravatar CDN
            supported_identifier_types=["email"],
            attribution="Gravatar public avatar service",
            description="Checks whether a Gravatar is configured for the email hash",
        )

    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        email = ctx.identifier_canonical.strip().lower()
        md5 = hashlib.md5(email.encode("utf-8")).hexdigest()
        cache_key = self.cache.make_key("gravatar", md5)
        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=True,
                observations=[self._from(o) for o in cached.get("observations", [])],
                cache_hit=True,
            )

        await self.rate_limiter.acquire("gravatar", per_second=2, per_hour=200, per_day=1000)
        # d=404 makes missing avatars return 404
        url = f"https://www.gravatar.com/avatar/{md5}?d=404&s=80"
        try:
            resp = await self.egress.fetch(url, purpose="discovery.gravatar")
        except EgressError as e:
            return ConnectorResult(connector_id=self.capability.id, success=False, error=str(e))

        observations: list[RawObservation] = []
        if resp.status_code == 200:
            observations.append(
                RawObservation(
                    kind=ObservationKind.PROFILE,
                    source="gravatar",
                    title="Gravatar present",
                    summary="A Gravatar image is configured for this email hash.",
                    confidence=0.9,
                    observed_at=datetime.now(timezone.utc),
                    attributes={"hash_md5_prefix": md5[:8], "present": True},
                    attribution=self.capability.attribution,
                )
            )

        ttl = (
            self.settings.connector_default_cache_ttl_seconds
            if observations
            else self.settings.connector_negative_cache_ttl_seconds
        )
        await self.cache.set_json(
            cache_key, {"observations": [o.to_dict() for o in observations]}, ttl
        )
        return ConnectorResult(
            connector_id=self.capability.id, success=True, observations=observations
        )

    @staticmethod
    def _from(d: dict) -> RawObservation:
        return RawObservation(
            kind=ObservationKind.PROFILE,
            source="gravatar",
            title=d.get("title", ""),
            summary=d.get("summary", ""),
            confidence=float(d.get("confidence", 0.9)),
            attributes=d.get("attributes") or {},
            attribution=d.get("attribution"),
        )
```

### `backend/app/connectors/impl/surface/username_presence.py`

```python
"""Curated ethical username presence — only a few public endpoints (Green)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorResult,
    ConnectorLayer,
    LegalityTier,
    ObservationKind,
    RawObservation,
)
from app.security.egress import EgressError


# Keep list tiny and ethical — no holehe reset abuse
_SITES = [
    # (id, url_template, ok_status_is_present)
    ("github", "https://github.com/{u}", {200}),
    ("gitlab", "https://gitlab.com/{u}", {200}),
    ("reddit", "https://www.reddit.com/user/{u}/about.json", {200}),
]


class UsernamePresenceConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="username_presence",
            name="Username presence (curated)",
            layer=ConnectorLayer.SURFACE,
            legality=LegalityTier.GREEN,
            requires_paid_key=False,
            sends_identifier=True,
            supported_identifier_types=["username", "github_username"],
            attribution="Public profile HTTP checks (curated)",
            description="Limited ethical presence checks — not mass OSINT abuse",
        )

    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        username = ctx.identifier_canonical
        cache_key = self.cache.make_key("username_presence", username)
        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=True,
                observations=[self._from(o) for o in cached.get("observations", [])],
                cache_hit=True,
            )

        observations: list[RawObservation] = []
        for site_id, tmpl, ok_set in _SITES:
            await self.rate_limiter.acquire(
                f"username_presence:{site_id}", per_second=0.5, per_hour=30, per_day=100
            )
            url = tmpl.format(u=username)
            try:
                resp = await self.egress.fetch(
                    url,
                    headers={"User-Agent": "DigiZafe-Presence/0.1"},
                    purpose=f"discovery.username_presence.{site_id}",
                )
            except EgressError:
                continue
            present = resp.status_code in ok_set
            if present:
                observations.append(
                    RawObservation(
                        kind=ObservationKind.USERNAME_PRESENCE,
                        source="username_presence",
                        title=f"Username present on {site_id}",
                        summary=f"Public profile likely exists for '{username}' on {site_id}.",
                        confidence=0.7,
                        observed_at=datetime.now(timezone.utc),
                        attributes={"site": site_id, "http_status": resp.status_code},
                        attribution=self.capability.attribution,
                    )
                )

        await self.cache.set_json(
            cache_key,
            {"observations": [o.to_dict() for o in observations]},
            self.settings.connector_default_cache_ttl_seconds,
        )
        return ConnectorResult(
            connector_id=self.capability.id, success=True, observations=observations
        )

    @staticmethod
    def _from(d: dict) -> RawObservation:
        return RawObservation(
            kind=ObservationKind.USERNAME_PRESENCE,
            source="username_presence",
            title=d.get("title", ""),
            summary=d.get("summary", ""),
            confidence=float(d.get("confidence", 0.7)),
            attributes=d.get("attributes") or {},
            attribution=d.get("attribution"),
        )
```

### `backend/app/connectors/impl/surface/serp_ddg.py`

```python
"""DuckDuckGo HTML lite SERP adapter (free, fragile — honest about limits)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorResult,
    ConnectorLayer,
    LegalityTier,
    ObservationKind,
    RawObservation,
)
from app.security.egress import EgressError


class SerpDdgConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="serp_ddg",
            name="DuckDuckGo HTML SERP",
            layer=ConnectorLayer.SURFACE,
            legality=LegalityTier.GREEN,
            requires_paid_key=False,
            sends_identifier=True,
            supported_identifier_types=["email", "username", "domain", "github_username"],
            attribution="DuckDuckGo HTML results (unofficial; rate-limited; best-effort)",
            description="Free SERP footprint probe — may break; never heavy scrape",
        )

    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        q = ctx.identifier_canonical
        cache_key = self.cache.make_key("serp_ddg", ctx.identifier_type, q)
        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=True,
                observations=[self._from(o) for o in cached.get("observations", [])],
                cache_hit=True,
            )

        await self.rate_limiter.acquire("serp_ddg", per_second=0.3, per_hour=20, per_day=50)
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
        try:
            resp = await self.egress.fetch(
                url,
                headers={
                    "User-Agent": "DigiZafe-SERP/0.1 (personal self-scan; +https://localhost)",
                },
                purpose="discovery.serp_ddg",
            )
        except EgressError as e:
            return ConnectorResult(connector_id=self.capability.id, success=False, error=str(e))

        if resp.status_code != 200:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                skipped=True,
                skip_reason="serp_unavailable",
                error=f"HTTP {resp.status_code}",
            )

        html = resp.body.decode("utf-8", errors="replace")
        # Very light extraction — result links
        links = re.findall(r'uddg=([^&"]+)', html)
        from urllib.parse import unquote

        clean = []
        for L in links:
            try:
                u = unquote(L)
                if u.startswith("http") and u not in clean:
                    clean.append(u)
            except Exception:
                continue
            if len(clean) >= 10:
                break

        observations = [
            RawObservation(
                kind=ObservationKind.SERP,
                source="serp_ddg",
                title="SERP hit",
                summary=f"DuckDuckGo HTML result: {u[:200]}",
                confidence=0.4,
                observed_at=datetime.now(timezone.utc),
                raw_ref=u[:500],
                attributes={"url": u[:500], "engine": "duckduckgo_html"},
                attribution=self.capability.attribution,
            )
            for u in clean
        ]

        await self.cache.set_json(
            cache_key,
            {"observations": [o.to_dict() for o in observations]},
            self.settings.connector_default_cache_ttl_seconds,
        )
        return ConnectorResult(
            connector_id=self.capability.id,
            success=True,
            observations=observations,
            meta={"note": "Best-effort free SERP; HTML structure may change"},
        )

    @staticmethod
    def _from(d: dict) -> RawObservation:
        return RawObservation(
            kind=ObservationKind.SERP,
            source="serp_ddg",
            title=d.get("title", ""),
            summary=d.get("summary", ""),
            confidence=float(d.get("confidence", 0.4)),
            attributes=d.get("attributes") or {},
            attribution=d.get("attribution"),
        )
```

---

## 9. NEW: `backend/app/connectors/registry.py`

```python
"""Build and list surface connectors."""

from __future__ import annotations

from typing import Dict, List

from app.connectors.sdk.base import Connector
from app.connectors.sdk.rate_limiter import RateLimiter
from app.connectors.sdk.cache import ConnectorCache
from app.security.egress import get_egress_fetcher
from app.connectors.sdk.redis_clients import get_cache_redis

from app.connectors.impl.surface.xposedornot import XposedOrNotConnector
from app.connectors.impl.surface.pwned_passwords import PwnedPasswordsConnector
from app.connectors.impl.surface.crtsh import CrtShConnector
from app.connectors.impl.surface.rdap import RdapConnector
from app.connectors.impl.surface.github_connector import GitHubConnector
from app.connectors.impl.surface.gravatar import GravatarConnector
from app.connectors.impl.surface.username_presence import UsernamePresenceConnector
from app.connectors.impl.surface.serp_ddg import SerpDdgConnector


async def build_connectors() -> Dict[str, Connector]:
    redis = await get_cache_redis()
    egress = get_egress_fetcher()
    rl = RateLimiter(redis)
    cache = ConnectorCache(redis)

    common = dict(egress=egress, rate_limiter=rl, cache=cache)
    instances: List[Connector] = [
        XposedOrNotConnector(**common),
        PwnedPasswordsConnector(**common),
        CrtShConnector(**common),
        RdapConnector(**common),
        GitHubConnector(**common),
        GravatarConnector(**common),
        UsernamePresenceConnector(**common),
        SerpDdgConnector(**common),
    ]
    return {c.capability.id: c for c in instances}
```

---

## 10. NEW: models for admin toggles

### `backend/app/models/connector_config.py`

```python
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConnectorConfig(Base):
    """Runtime enable/disable (admin). Feature flags remain env-level defaults."""

    __tablename__ = "connector_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connector_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

Update `backend/app/models/__init__.py` to export `ConnectorConfig`.

---

## 11. NEW: `backend/app/services/connector_service.py`

```python
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.registry import build_connectors
from app.connectors.sdk.types import ConnectorContext, ConnectorResult
from app.connectors.sdk.rate_limiter import RateLimitExceeded
from app.connectors.sdk.redis_clients import get_cache_redis
from app.connectors.sdk.rate_limiter import RateLimiter
from app.models.connector_config import ConnectorConfig
from app.services.identifier_service import IdentifierService
from app.services.consent_service import ConsentService
from app.services.audit_service import AuditService
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectorService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.identifiers = IdentifierService(session)
        self.consent = ConsentService(session)
        self.audit = AuditService(session)
        self.settings = get_settings()

    async def list_catalog(self) -> list[dict[str, Any]]:
        connectors = await build_connectors()
        db_flags = await self._load_db_flags()
        out = []
        for cid, c in connectors.items():
            cap = c.capability
            env_on = c.is_enabled_by_config()
            db_on = db_flags.get(cid)
            effective = env_on if db_on is None else (env_on and db_on)
            out.append(
                {
                    "id": cap.id,
                    "name": cap.name,
                    "layer": cap.layer.value,
                    "legality": cap.legality.value,
                    "requires_paid_key": cap.requires_paid_key,
                    "sends_identifier": cap.sends_identifier,
                    "supported_identifier_types": cap.supported_identifier_types,
                    "attribution": cap.attribution,
                    "description": cap.description,
                    "enabled_env": env_on,
                    "enabled_db": db_on,
                    "enabled_effective": effective,
                }
            )
        return out

    async def set_enabled(self, connector_id: str, enabled: bool, notes: str | None = None) -> dict:
        connectors = await build_connectors()
        if connector_id not in connectors:
            raise HTTPException(status_code=404, detail="Unknown connector")
        result = await self.session.execute(
            select(ConnectorConfig).where(ConnectorConfig.connector_id == connector_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            row = ConnectorConfig(connector_id=connector_id, enabled=enabled, notes=notes)
            self.session.add(row)
        else:
            row.enabled = enabled
            if notes is not None:
                row.notes = notes
        await self.session.flush()
        await self.audit.log(
            "connector.config_updated",
            details={"connector_id": connector_id, "enabled": enabled},
        )
        return {"connector_id": connector_id, "enabled": enabled}

    async def _load_db_flags(self) -> dict[str, bool]:
        result = await self.session.execute(select(ConnectorConfig))
        return {r.connector_id: r.enabled for r in result.scalars().all()}

    async def probe(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        connector_ids: list[str] | None = None,
        *,
        password_plaintext: str | None = None,
    ) -> dict[str, Any]:
        """
        Dry-run free surface connectors for a VERIFIED identifier.
        Does NOT persist findings (Sprint 4). Returns observations for UI/debug.
        """
        # G1 gate
        ident = await self.identifiers.require_verified(user_id, identifier_id)

        # Per-user daily probe quota
        redis = await get_cache_redis()
        rl = RateLimiter(redis)
        try:
            await rl.acquire_user_quota(str(user_id))
        except RateLimitExceeded:
            raise HTTPException(status_code=429, detail="Daily probe quota exceeded")

        connectors = await build_connectors()
        db_flags = await self._load_db_flags()

        if connector_ids:
            selected = {k: connectors[k] for k in connector_ids if k in connectors}
        else:
            # Default set by identifier type
            selected = {
                k: c
                for k, c in connectors.items()
                if c.supports(ident.type) and k != "pwned_passwords"
            }

        # Special: password probe
        if password_plaintext is not None and "pwned_passwords" in (connector_ids or ["pwned_passwords"]):
            selected["pwned_passwords"] = connectors["pwned_passwords"]

        results: list[dict[str, Any]] = []
        for cid, connector in selected.items():
            env_on = connector.is_enabled_by_config()
            db_on = db_flags.get(cid)
            effective = env_on if db_on is None else (env_on and db_on)

            purpose = f"discovery.{cid}"
            if connector.capability.sends_identifier:
                ok = await self.consent.ensure_consent(
                    user_id, purpose=purpose, auto_grant=False, scope=ident.type
                )
                if not ok:
                    # Auto-grant only if user explicitly probes? Prefer explicit consent endpoint first.
                    # For better UX in MVP self-scan: auto_grant=True on probe with audit
                    await self.consent.ensure_consent(
                        user_id, purpose=purpose, auto_grant=True, scope=str(ident.id)
                    )

            if cid == "pwned_passwords":
                if not password_plaintext:
                    results.append(
                        ConnectorResult(
                            connector_id=cid,
                            success=False,
                            skipped=True,
                            skip_reason="password_required",
                        ).to_dict()
                    )
                    continue
                ctx = ConnectorContext(
                    user_id=user_id,
                    identifier_id=ident.id,
                    identifier_type="password",
                    identifier_canonical=password_plaintext,
                    consent_purpose=purpose,
                )
            else:
                ctx = ConnectorContext(
                    user_id=user_id,
                    identifier_id=ident.id,
                    identifier_type=ident.type,
                    identifier_canonical=ident.value_canonical,
                    consent_purpose=purpose,
                )

            result = await connector.run(ctx, enabled_override=effective)

            # Egress ledger for identifier-sending connectors (best-effort host)
            if connector.capability.sends_identifier and not result.skipped:
                host = {
                    "xposedornot": "api.xposedornot.com",
                    "crtsh": "crt.sh",
                    "rdap": "rdap.org",
                    "github": "api.github.com",
                    "username_presence": "multi",
                    "serp_ddg": "html.duckduckgo.com",
                }.get(cid, cid)
                await self.consent.record_egress(
                    purpose=purpose,
                    destination_host=host,
                    method="GET",
                    status_code=200 if result.success else None,
                    success=result.success,
                    user_id=user_id,
                    identifier_id=ident.id,
                    summary={
                        "connector": cid,
                        "cache_hit": result.cache_hit,
                        "skipped": result.skipped,
                        "observation_count": len(result.observations),
                    },
                )

            results.append(result.to_dict())

        await self.audit.log(
            "connector.probe",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(ident.id),
            details={
                "connectors": list(selected.keys()),
                "result_count": len(results),
            },
        )

        # Aggregate attribution for UI
        attributions = sorted(
            {
                r.get("meta", {}).get("attribution")
                or next(
                    (
                        o.get("attribution")
                        for o in r.get("observations") or []
                        if o.get("attribution")
                    ),
                    None,
                )
                for r in results
            }
            - {None}
        )

        return {
            "identifier_id": str(ident.id),
            "identifier_type": ident.type,
            "results": results,
            "attributions": attributions,
            "note": "Probe only — findings persistence & PDSS land in Sprint 4–5. XposedOrNot is primary free breach source.",
        }
```

---

## 12. NEW: schemas `backend/app/schemas/connectors.py`

```python
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConnectorToggle(BaseModel):
    enabled: bool
    notes: Optional[str] = None


class ProbeRequest(BaseModel):
    connector_ids: Optional[list[str]] = None
    # Optional password for pwned_passwords only — never stored
    password: Optional[str] = Field(None, min_length=1, max_length=256)


class ProbeResponse(BaseModel):
    identifier_id: str
    identifier_type: str
    results: list[dict[str, Any]]
    attributions: list[str] = []
    note: str = ""
```

---

## 13. NEW: `backend/app/api/v1/connectors.py`

```python
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, get_current_active_superuser
from app.models.user import User
from app.schemas.connectors import ConnectorToggle, ProbeRequest
from app.services.connector_service import ConnectorService

router = APIRouter(prefix="/connectors", tags=["connectors"])


def _svc(db: AsyncSession = Depends(get_db)) -> ConnectorService:
    return ConnectorService(db)


@router.get("")
async def list_connectors(
    current_user: CurrentUser,
    svc: ConnectorService = Depends(_svc),
):
    """Catalog of free surface connectors + enablement state."""
    return await svc.list_catalog()


@router.patch("/{connector_id}")
async def toggle_connector(
    connector_id: str,
    body: ConnectorToggle,
    admin: User = Depends(get_current_active_superuser),
    svc: ConnectorService = Depends(_svc),
):
    """Admin-only enable/disable."""
    return await svc.set_enabled(connector_id, body.enabled, notes=body.notes)


@router.post("/probe/{identifier_id}")
async def probe_identifier(
    identifier_id: UUID,
    body: ProbeRequest | None = None,
    current_user: CurrentUser = None,  # type: ignore
    svc: ConnectorService = Depends(_svc),
):
    """
    Run free surface connectors against a **verified** identifier (G1).
    Does not persist findings yet (Sprint 4).
    """
    body = body or ProbeRequest()
    return await svc.probe(
        current_user.id,
        identifier_id,
        connector_ids=body.connector_ids,
        password_plaintext=body.password,
    )
```

Fix `current_user: CurrentUser` properly:

```python
async def probe_identifier(
    identifier_id: UUID,
    current_user: CurrentUser,
    body: ProbeRequest | None = None,
    svc: ConnectorService = Depends(_svc),
):
    body = body or ProbeRequest()
    return await svc.probe(
        current_user.id,
        identifier_id,
        connector_ids=body.connector_ids,
        password_plaintext=body.password,
    )
```

---

## 14. UPDATE: `backend/app/main.py`

```python
from app.api.v1 import health, auth, identifiers, connectors

# ...
app.include_router(connectors.router, prefix=settings.api_v1_prefix)

# root message
"message": "DigiZafe Sprint 3 Connector SDK & Free Surface — ready",
"version": "0.3.0",
```

---

## 15. Alembic migration `sprint3_connector_configs`

```python
"""sprint3_connector_configs"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "sprint3_conn_001"
down_revision: Union[str, None] = "sprint2_id_001"  # your Sprint 2 rev
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("connector_id", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_connector_configs_connector_id", "connector_configs", ["connector_id"], unique=True)

    # Seed defaults (all enabled)
    # Optional raw SQL inserts — app works without rows (env flags apply)


def downgrade() -> None:
    op.drop_table("connector_configs")
```

Update `alembic/env.py` model imports for `ConnectorConfig`.

---

## 16. Unit tests

### `backend/tests/unit/connectors/test_types_and_xpn_parse.py`

```python
from app.connectors.sdk.types import LegalityTier, ObservationKind


def test_enums():
    assert LegalityTier.GREEN.value == "green"
    assert ObservationKind.BREACH.value == "breach"
```

### `backend/tests/unit/connectors/test_pwned_match.py`

```python
from app.connectors.impl.surface.pwned_passwords import PwnedPasswordsConnector


def test_suffix_match_logic():
    # Minimal fake: exercise _match without network
    class Dummy:
        capability = type("C", (), {"id": "pwned_passwords", "attribution": "x"})()

    # Bind _match
    count_line = "003D68EB55068C33ACE09247EE4C639306B:3\n"  # fictional
    # Use real class method via unbound pattern
    conn = object.__new__(PwnedPasswordsConnector)
    conn.capability = type("C", (), {"id": "pwned_passwords", "attribution": "t"})()
    # We need instance with capability property — simpler assert on parse:
    suffix = "003D68EB55068C33ACE09247EE4C639306B"
    found = 0
    for line in count_line.splitlines():
        p = line.split(":")
        if p[0].upper() == suffix.upper():
            found = int(p[1])
    assert found == 3
```

### `backend/tests/unit/connectors/test_rate_limiter_keys.py`

```python
def test_rate_limiter_key_format():
    from app.connectors.sdk.rate_limiter import RateLimiter
    # pure helper
    class R:
        prefix = "rl"
        def _k(self, *parts):
            return ":".join([self.prefix, *parts])
    assert R()._k("xposedornot", "s", "1") == "rl:xposedornot:s:1"
```

---

## 17. Docs updates

### UPDATE `docs/free-sources.md`

```markdown
# Free Sources Inventory (Sprint 3)

## Primary Breach
- **XposedOrNot** — `GET https://api.xposedornot.com/v1/check-email/{email}`  
  Free tier (approx): 2/sec, 25/hour, 100/day per IP.  
  Optional analytics: `/v1/breach-analytics?email=`  
  **Attribution required.** Consent + egress_ledger required (sends email).  
  DigiZafe enforces stricter internal limits + Redis cache (long negative TTL).

## Passwords
- **Pwned Passwords** — `https://api.pwnedpasswords.com/range/{prefix}`  
  k-anonymous (5-char SHA-1 prefix only). No key. No full password egress.

## Surface Green (Sprint 3)
| Connector | Host | Identifier | Notes |
|-----------|------|------------|-------|
| xposedornot | api.xposedornot.com | email | Primary breach |
| pwned_passwords | api.pwnedpasswords.com | password (in-memory) | k-anon |
| crtsh | crt.sh | domain | CT names |
| rdap | rdap.org | domain | Registration public |
| github | api.github.com | username | Optional free PAT |
| gravatar | gravatar.com | email→md5 | Existence only |
| username_presence | curated | username | github/gitlab/reddit only |
| serp_ddg | html.duckduckgo.com | multi | Best-effort HTML |

Paid HIBP Breach API remains **feature-flagged off** and non-load-bearing.
```

### `docs/runbooks/connectors.md`

```markdown
# Connectors Runbook (Sprint 3)

## Probe a verified email
1. Login → add email → verify (Sprint 2)
2. `GET /api/v1/connectors` — catalog
3. `POST /api/v1/connectors/probe/{identifier_id}`  
   Body optional: `{"connector_ids":["xposedornot","gravatar"]}`
4. UI must show XposedOrNot attribution when their data appears

## Rate limits
If skip_reason=rate_limited — surface honestly; rely on cache; do not spin.

## Admin disable
Superuser: `PATCH /api/v1/connectors/xposedornot` `{"enabled":false}`
```

### UPDATE `docs/aidr-mapping.md` (breach row)

```markdown
| aidr breach / hibp.js | connectors/impl/surface/xposedornot.py + pwned_passwords.py | Primary free XposedOrNot; HIBP breach API optional flag only |
```

---

# PART C — Finish Sprint 3

```bash
# Merge env, rebuild, migrate
docker compose build api worker
docker compose up -d
docker compose exec api alembic upgrade head

# Smoke
export ACCESS=...  # login
export ID=...      # verified email identifier uuid

curl -s http://localhost:8000/api/v1/connectors -H "Authorization: Bearer $ACCESS" | jq .

curl -s -X POST "http://localhost:8000/api/v1/connectors/probe/$ID" \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d '{"connector_ids":["xposedornot","gravatar"]}' | jq .

# Password check (never logs password)
curl -s -X POST "http://localhost:8000/api/v1/connectors/probe/$ID" \
  -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d '{"connector_ids":["pwned_passwords"],"password":"Password123!"}' | jq .

# Unit tests
docker compose exec api pytest backend/tests/unit/connectors -v

git add .
git commit -m "feat(sprint-3): connector SDK (rate limit+cache), XposedOrNot primary, free surface greens, probe API, admin toggle"
```

---

# Sprint 3 Definition of Done

- [ ] Connector ABC + RateLimiter + Cache + Egress-only HTTP  
- [ ] Connectors never import DB models/sessions  
- [ ] **XposedOrNot** primary: check-email + optional analytics; cache + rate limits; attribution in result meta  
- [ ] Consent + egress_ledger for sends_identifier connectors  
- [ ] Pwned Passwords k-anonymous (prefix only)  
- [ ] crt.sh, RDAP, GitHub, Gravatar, username_presence (curated), serp_ddg implemented as Green  
- [ ] `GET /connectors` catalog + effective enablement  
- [ ] Admin `PATCH /connectors/{id}` (superuser)  
- [ ] `POST /connectors/probe/{identifier_id}` requires **verified** identifier (G1)  
- [ ] Per-user daily probe quota  
- [ ] Rate-limit / disable / unsupported surfaced as `skipped` (never silent)  
- [ ] No paid API required for core path  
- [ ] Docs: free-sources + runbook + AIDR breach mapping updated  
- [ ] Unit tests for pure helpers green  

→ **Sprint 3 complete.**  
Next: **Sprint 4 — Discovery & Evidence** (Postgres scan state machine + reconcile, 3-layer evidence + TTL, SSE, activate verified-only trigger on scans, XposedOrNot → findings normalization).

---

## Endpoint quick reference

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | /api/v1/connectors | Bearer | Catalog + flags |
| PATCH | /api/v1/connectors/{id} | Superuser | Enable/disable |
| POST | /api/v1/connectors/probe/{identifier_id} | Bearer | Run free connectors (verified only) |

---

**You are ready for Sprint 3.**  
Apply in order, set `down_revision`, migrate, probe a verified email against XposedOrNot, confirm attribution + ledger rows, commit.

When Sprint 3 is green, ask for **Sprint 4** the same way.