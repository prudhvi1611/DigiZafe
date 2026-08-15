# DigiZafe — Sprint 11 Deep + Constrained-Dark Free Amber

**Complete Implementation Guide from Sprint 10 Baseline + All File Contents**

**Document version:** 1.1 (final reviewed)  
**Based on:** `MASTER_ENGINEERING_CONTEXT.md` v2.1  
**Depends on:** Sprint 0–10 green  
**Goal:** Add carefully constrained, free Amber discovery layers without redesigning existing Sprint 0–10 contracts:

- Deep public-web/archive metadata discovery
- Common Crawl URL-index adapter
- Wayback availability metadata adapter
- Configurable public-index adapter for Constrained-Dark signals
- Explicit consent gates for Amber scans
- Layer-aware connector selection
- Honest `Surface / Deep / Constrained-Dark` tags
- Durable provenance and attribution
- No unrestricted crawling
- No Tor/onion crawling
- No credentialed marketplace access
- No raw breach dumps
- No paid API requirement
- Frontend layer selection and Amber consent UX

**Effort estimate:** ~8 days  
**Critical path next:** Sprint 12 Optional Free Residual ML

> Load `MASTER_ENGINEERING_CONTEXT.md` before every coding session.  
> Sprint 11 does not redesign the architecture.  
> Amber discovery is opt-in, rate-limited, metadata-first, and subject to explicit user consent.  
> Surface discovery remains the default and safest baseline.  
> **Preflight rule:** before creating any enum, DTO, consent purpose, registry type, or connector abstraction in this sprint, search the existing Sprint 0–10 codebase and reuse/extend the canonical implementation. Do not create parallel domain concepts.  
> **Networking rule:** Amber connectors never instantiate their own HTTP client and never perform direct DNS, redirect, or socket handling. Every outbound request must flow through the existing Connector SDK and centralized `EgressFetcher`.  
> **Scoring rule:** exposure layer is provenance/context, not severity. `deep` or `constrained_dark` must never automatically increase severity or PDSS.

---

# PART A — Sprint 11 Safety Boundary

## Included

| Area | Sprint 11 outcome |
|---|---|
| Deep layer | Free public archive/index metadata from Common Crawl and Wayback |
| Constrained-Dark layer | Configurable public JSON index adapter, disabled by default |
| Consent | Explicit layer consent plus connector/destination-aware egress authorization where identifiers are disclosed |
| Provenance | Every observation records source, layer, attribution, and query mode |
| UI | Layer selector, consent controls, honest Amber copy |
| Scoring | Existing PDSS pipeline receives evidence-quality-aware, layer-tagged observations/findings; layer alone never changes severity |
| Evidence | Existing TTL and durable metadata rules remain unchanged |
| Security | All HTTP remains behind `EgressFetcher` |
| Cost | No paid keys required |

## Explicitly excluded

- Direct Tor networking
- `.onion` crawling
- Dark-web marketplace access
- Credentialed services or leaked-account login
- Buying or downloading breach dumps
- Searching unrestricted third-party people databases
- Password-reset or account-recovery probing
- Credential stuffing
- CAPTCHA bypass
- Full archived-page body retention
- Storing raw HTML indefinitely
- Automated contact with illicit actors
- Any connector that cannot declare an approved host and purpose
- Any paid threat-intelligence dependency

## Amber layer meaning

Amber does **not** mean “anything on the dark web.”

Amber means:

1. The source is public or explicitly configured by the operator.
2. The source can be queried without authentication or illicit access.
3. The query is self-only and initiated for a verified identifier.
4. The result is metadata-first.
5. The user has explicitly consented to the relevant destination and layer.
6. Rate limits and cache rules are enforced.
7. Limitations are visible in the UI.

The Constrained-Dark adapter in this sprint is an integration boundary for an operator-approved public index. It has no default endpoint and remains disabled until configured.

---


# PART A.1 — Mandatory Preflight Against Sprint 0–10

Before applying any file content in this guide:

1. Search the existing repository for canonical definitions of:
   - `ExposureLayer` or equivalent layer enums/catalogs
   - connector metadata / legality classifications
   - scan scope DTOs
   - consent purpose/scope models
   - egress authorization and ledger fields
   - observation/finding provenance fields
2. **Reuse or extend existing definitions.** If an equivalent abstraction already exists, do not create the duplicate shown in this guide.
3. Confirm the existing `/api/v1` DTO contracts before changing frontend types.
4. Confirm the existing `EgressFetcher`, rate limiter, cache, connector base class, and registry interfaces before implementing connectors.
5. If a frozen Sprint 0 document conflicts with this guide, stop and file a Critical Blocker Note (CBN). The frozen document wins.
6. Plan tests alongside each implementation change. Do not defer tests until the end.

This sprint is an additive implementation sprint, not an architecture redesign.

---

# PART B — Pre-Sprint 11 Setup

Run from the DigiZafe repository root:

```bash
# 1. Confirm Sprint 10 frontend and backend are green
docker compose ps
curl -s http://localhost:8000/api/v1/health | jq .

cd frontend
npm run build
cd ..

# 2. Create Amber connector directories
mkdir -p backend/app/connectors/impl/{deep,dark_constrained}
mkdir -p backend/tests/unit/connectors
mkdir -p docs/{runbooks,adr,ethics}
mkdir -p shared/config

touch backend/app/connectors/impl/deep/__init__.py
touch backend/app/connectors/impl/dark_constrained/__init__.py

# 3. No new hard Python dependencies are required.
# Existing httpx, Redis, SQLAlchemy, FastAPI, and Pydantic are sufficient.

# 4. Rebuild
docker compose build api worker beat remediation-worker 2>/dev/null || \
docker compose build api worker beat

echo "✅ Pre-Sprint 11 ready."
```

---

# PART C — Configuration

## 1. UPDATE: `.env.example`

Append:

```bash
# === Sprint 11: Deep + Constrained-Dark Free Amber ===

# Amber feature flags
FEATURE_DEEP_AMBER=true
FEATURE_CONSTRAINED_DARK=false

# Amber consent is never auto-granted by the worker
AMBER_SCAN_REQUIRES_CONSENT=true
# Consent/egress authorization is evaluated against the existing ConsentService.
# A generic layer grant must not silently authorize a newly configured destination.

# Common Crawl
COMMON_CRAWL_ENABLED=true
COMMON_CRAWL_COLLECTION=
COMMON_CRAWL_INDEX_BASE_URL=https://index.commoncrawl.org
COMMON_CRAWL_MAX_RESULTS=50
COMMON_CRAWL_CACHE_TTL_SECONDS=21600
COMMON_CRAWL_RATE_PER_SECOND=0.2
COMMON_CRAWL_RATE_PER_HOUR=30
COMMON_CRAWL_RATE_PER_DAY=100

# Wayback metadata
WAYBACK_ENABLED=true
WAYBACK_AVAILABILITY_URL=https://archive.org/wayback/available
WAYBACK_MAX_RESULTS=10
WAYBACK_CACHE_TTL_SECONDS=21600
WAYBACK_RATE_PER_SECOND=0.2
WAYBACK_RATE_PER_HOUR=30
WAYBACK_RATE_PER_DAY=100

# Configurable public index for constrained-dark metadata.
# Empty by default: no constrained-dark connector will make an external request.
AMBER_PUBLIC_INDEX_URL=
AMBER_PUBLIC_INDEX_HOST_ALLOWLIST=
AMBER_PUBLIC_INDEX_QUERY_PARAM=q
AMBER_PUBLIC_INDEX_MAX_RESULTS=25
AMBER_PUBLIC_INDEX_CACHE_TTL_SECONDS=21600
AMBER_PUBLIC_INDEX_RATE_PER_SECOND=0.1
AMBER_PUBLIC_INDEX_RATE_PER_HOUR=10
AMBER_PUBLIC_INDEX_RATE_PER_DAY=30

# Amber UI and scan defaults
VITE_AMBER_ENABLED=true
VITE_CONSTRAINED_DARK_DEFAULT=false
```

Do not enable `FEATURE_CONSTRAINED_DARK` unless an approved public index endpoint and host allowlist have been reviewed.

---

## 2. UPDATE: `backend/app/core/config.py`

Add these fields to the existing `Settings` class:

```python
    # === Sprint 11: Deep + Constrained-Dark Amber ===
    feature_deep_amber: bool = True
    feature_constrained_dark: bool = False
    amber_scan_requires_consent: bool = True

    # Common Crawl
    common_crawl_enabled: bool = True
    common_crawl_collection: str = ""
    common_crawl_index_base_url: str = "https://index.commoncrawl.org"
    common_crawl_max_results: int = 50
    common_crawl_cache_ttl_seconds: int = 21_600
    common_crawl_rate_per_second: float = 0.2
    common_crawl_rate_per_hour: int = 30
    common_crawl_rate_per_day: int = 100

    # Wayback
    wayback_enabled: bool = True
    wayback_availability_url: str = "https://archive.org/wayback/available"
    wayback_max_results: int = 10
    wayback_cache_ttl_seconds: int = 21_600
    wayback_rate_per_second: float = 0.2
    wayback_rate_per_hour: int = 30
    wayback_rate_per_day: int = 100

    # Configured public constrained-dark index
    amber_public_index_url: str = ""
    amber_public_index_host_allowlist: str = ""
    amber_public_index_query_param: str = "q"
    amber_public_index_max_results: int = 25
    amber_public_index_cache_ttl_seconds: int = 21_600
    amber_public_index_rate_per_second: float = 0.1
    amber_public_index_rate_per_hour: int = 10
    amber_public_index_rate_per_day: int = 30

    @property
    def amber_public_index_hosts(self) -> set[str]:
        return {
            host.strip().lower()
            for host in self.amber_public_index_host_allowlist.split(",")
            if host.strip()
        }
```

---

# PART D — Amber Source Registry

## 3. NEW: `shared/config/amber_sources.json`

```json
{
  "registry_version": "1.0.0",
  "description": "DigiZafe free Amber discovery registry. Metadata-first, consented, rate-limited.",
  "policy": {
    "raw_html_storage": false,
    "raw_dump_storage": false,
    "direct_tor_access": false,
    "onion_crawling": false,
    "marketplace_access": false,
    "credentialed_access": false,
    "paid_dependency": false
  },
  "layers": {
    "deep": [
      {
        "id": "common_crawl",
        "name": "Common Crawl URL Index",
        "legality": "amber",
        "enabled_by_default": true,
        "supports": ["domain"],
        "metadata_only": true,
        "attribution": "Common Crawl public index",
        "limitations": [
          "URL-index metadata only",
          "Generic username searching is not enabled by default because string matches are ambiguous",
          "Coverage varies by crawl collection",
          "No claim that archived content is current",
          "No full archived page body is retained"
        ]
      },
      {
        "id": "wayback",
        "name": "Internet Archive Wayback Availability",
        "legality": "amber",
        "enabled_by_default": true,
        "supports": ["domain"],
        "metadata_only": true,
        "attribution": "Internet Archive Wayback Machine",
        "limitations": [
          "Availability metadata only",
          "A historical capture does not prove current exposure",
          "No archived page body is retained by DigiZafe"
        ]
      }
    ],
    "constrained_dark": [
      {
        "id": "public_index",
        "name": "Operator-approved public index",
        "legality": "amber",
        "enabled_by_default": false,
        "supports": ["domain"],
        "metadata_only": true,
        "attribution": "Configured public index",
        "limitations": [
          "No endpoint is configured by default",
          "Only operator-approved HTTPS hosts are allowed",
          "No .onion access",
          "No marketplace or credentialed access",
          "Results are best-effort and may be incomplete"
        ]
      }
    ]
  }
}
```

---


# PART D.1 — Identifier and Attribution Policy

## Domain identifiers

Verified domains are the default supported identifier for Common Crawl and Wayback metadata queries because they provide the clearest bounded lookup semantics.

## Username and GitHub username identifiers

Generic username matching is **not enabled by default** for Common Crawl or archive-index discovery.

If username support is added later through an existing approved connector contract:

- the username must already be verified under DigiZafe's existing self-only rules;
- the query strategy must be bounded and documented;
- a string occurrence is not identity proof;
- results default to candidate/`possible` evidence;
- promotion to confirmed exposure requires independent identity-linkage evidence;
- the UI must communicate uncertainty;
- the connector must not broaden into unrestricted people-search behavior.

A verified GitHub username should preferentially use the existing verified GitHub identity context rather than arbitrary global string matching.

---

# PART E — Pure Amber Layer Domain

## 4. NEW OR EXTEND CANONICAL: `backend/app/domain/amber_layers.py`

> Create this file only if Sprint 0–10 does not already define the canonical exposure-layer abstraction. If an equivalent enum/catalog exists, extend and import it instead of creating a second source of truth.

```python
"""Pure Amber layer policy helpers."""

from __future__ import annotations

from enum import Enum
from typing import Any


class ExposureLayer(str, Enum):
    SURFACE = "surface"
    DEEP = "deep"
    CONSTRAINED_DARK = "constrained_dark"


class AmberPolicyError(ValueError):
    pass


LAYER_CONSENT_PURPOSE: dict[ExposureLayer, str | None] = {
    ExposureLayer.SURFACE: None,
    ExposureLayer.DEEP: "discovery.deep",
    ExposureLayer.CONSTRAINED_DARK: "discovery.constrained_dark",
}


LAYER_COPY: dict[ExposureLayer, dict[str, str]] = {
    ExposureLayer.SURFACE: {
        "label": "Surface",
        "description": "Public surface-web connectors and free breach metadata.",
        "warning": "Standard surface discovery.",
    },
    ExposureLayer.DEEP: {
        "label": "Deep",
        "description": "Public archive and index metadata that is not part of the ordinary live surface scan.",
        "warning": "Historical or indexed metadata may be incomplete or stale.",
    },
    ExposureLayer.CONSTRAINED_DARK: {
        "label": "Constrained-Dark",
        "description": "Operator-approved public index metadata only.",
        "warning": (
            "This is not unrestricted dark-web crawling. No Tor access, marketplace access, "
            "credentialed access, or raw dump retrieval is permitted."
        ),
    },
}


def parse_layer(value: ExposureLayer | str) -> ExposureLayer:
    try:
        return value if isinstance(value, ExposureLayer) else ExposureLayer(value)
    except ValueError as exc:
        raise AmberPolicyError(f"Unsupported exposure layer: {value}") from exc


def consent_purpose_for_layer(value: ExposureLayer | str) -> str | None:
    return LAYER_CONSENT_PURPOSE[parse_layer(value)]


def is_amber_layer(value: ExposureLayer | str) -> bool:
    return parse_layer(value) != ExposureLayer.SURFACE


def layer_matches_connector(
    requested_layer: ExposureLayer | str,
    connector_layer: str,
) -> bool:
    requested = parse_layer(requested_layer)
    return requested.value == connector_layer


def validate_layer_scope(
    value: ExposureLayer | str,
    *,
    feature_deep_amber: bool,
    feature_constrained_dark: bool,
) -> ExposureLayer:
    layer = parse_layer(value)

    if layer == ExposureLayer.DEEP and not feature_deep_amber:
        raise AmberPolicyError("Deep Amber discovery is disabled")

    if layer == ExposureLayer.CONSTRAINED_DARK and not feature_constrained_dark:
        raise AmberPolicyError("Constrained-Dark discovery is disabled")

    return layer


def public_layer_metadata(value: ExposureLayer | str) -> dict[str, Any]:
    layer = parse_layer(value)
    return {
        "layer": layer.value,
        **LAYER_COPY[layer],
        "requires_explicit_consent": is_amber_layer(layer),
    }
```

---

# PART F — Connector SDK Updates

## 5. UPDATE: `backend/app/connectors/sdk/types.py`

Replace the `ObservationKind` enum with:

```python
class ObservationKind(str, Enum):
    BREACH = "breach"
    PASSWORD_EXPOSURE = "password_exposure"
    CERTIFICATE = "certificate"
    DNS_RDAP = "dns_rdap"
    PROFILE = "profile"
    USERNAME_PRESENCE = "username_presence"
    SERP = "serp"
    ARCHIVED_METADATA = "archived_metadata"
    PUBLIC_INDEX_SIGNAL = "public_index_signal"
    OTHER = "other"
```

Update `ConnectorResult.skip_reason` documentation:

```python
    skip_reason: Optional[str] = None
    # rate_limited | disabled | no_consent | unsupported_type |
    # cache_only_error | not_configured | amber_policy_blocked |
    # red_excluded
```

No database model change is required because the existing `kind`, `source`, and `layer` fields are already string-based.

---

## 6. UPDATE: `backend/app/connectors/sdk/base.py`

Replace the feature mapping inside `is_enabled_by_config()` with:

```python
    def is_enabled_by_config(self) -> bool:
        """Environment-level feature flag. DB toggle is applied by the registry service."""
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

            # Sprint 11 Amber
            "common_crawl": (
                self.settings.feature_deep_amber
                and self.settings.common_crawl_enabled
            ),
            "wayback": (
                self.settings.feature_deep_amber
                and self.settings.wayback_enabled
            ),
            "public_index": self.settings.feature_constrained_dark,
        }

        return bool(mapping.get(cid, True))
```

Add this helper method to the `Connector` class:

```python
    def is_amber(self) -> bool:
        return self.capability.legality == LegalityTier.AMBER
```

---

# PART F.1 — Mandatory Networking Invariant

All connector examples in Parts G–I are subject to this rule:

```text
Amber connector
    ↓
Existing Connector SDK
    ↓
Verified-identifier gate
    ↓
Consent / destination authorization
    ↓
Rate limiter + cache
    ↓
Central EgressFetcher
    ↓
Approved HTTPS destination
```

Amber connector code must not instantiate `httpx.AsyncClient`, `requests`, raw sockets, custom DNS resolvers, or a parallel redirect/SSRF policy. The centralized `EgressFetcher` remains the only outbound HTTP boundary.

---

# PART G — Common Crawl Connector

Common Crawl exposes a public URL index and CDXJ-style query interface. DigiZafe uses only index metadata and does not retrieve or store full WARC/page bodies. ([commoncrawl.org](https://commoncrawl.org/cdxj-index))

## 7. NEW: `backend/app/connectors/impl/deep/common_crawl.py`

```python
"""Common Crawl URL-index adapter for Deep Amber metadata discovery."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorLayer,
    ConnectorResult,
    LegalityTier,
    ObservationKind,
    RawObservation,
)
from app.connectors.sdk.rate_limiter import RateLimitExceeded
from app.security.egress import EgressError


def build_common_crawl_pattern(identifier_type: str, canonical: str) -> str:
    """
    Build a constrained URL-index pattern.

    Email identifiers are intentionally unsupported because sending a full email
    to an archive index is unnecessary for this adapter. Email exposure remains
    handled by the dedicated free breach connector.
    """
    if identifier_type == "domain":
        return f"*.{canonical}/*"

    if identifier_type in {"username", "github_username"}:
        # Best-effort public URL metadata search.
        # Results are capped and never followed automatically.
        return f"*{canonical}*"

    raise ValueError(
        "Common Crawl supports domain, username, and github_username only"
    )


def parse_cdx_json_lines(
    body: bytes,
    *,
    max_results: int,
) -> list[dict[str, Any]]:
    """Parse newline-delimited JSON returned by Common Crawl index queries."""
    rows: list[dict[str, Any]] = []

    for line in body.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue

        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue

        if isinstance(value, dict):
            rows.append(value)

        if len(rows) >= max_results:
            break

    return rows


class CommonCrawlConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="common_crawl",
            name="Common Crawl URL Index",
            layer=ConnectorLayer.DEEP,
            legality=LegalityTier.AMBER,
            requires_paid_key=False,
            sends_identifier=True,
            supported_identifier_types=[
                "domain",
                "username",
                "github_username",
            ],
            attribution="Common Crawl public index",
            description=(
                "Deep Amber metadata lookup against a public crawl index. "
                "Only URL-index metadata is retained."
            ),
        )

    async def _resolve_collection(self) -> str | None:
        configured = self.settings.common_crawl_collection.strip()
        if configured:
            return configured

        cache_key = self.cache.make_key(
            "common_crawl",
            "collection",
            "latest",
        )
        cached = await self.cache.get_json(cache_key)
        if isinstance(cached, dict) and cached.get("collection"):
            return str(cached["collection"])

        url = (
            f"{self.settings.common_crawl_index_base_url.rstrip('/')}"
            "/collinfo.json"
        )

        try:
            response = await self.egress.fetch(
                url,
                purpose="discovery.deep.common_crawl.collection",
            )
        except EgressError:
            return None

        if response.status_code != 200:
            return None

        try:
            data = json.loads(
                response.body.decode("utf-8", errors="replace")
            )
        except json.JSONDecodeError:
            return None

        if not isinstance(data,           return None

        collection_id = first.get("id")
        if not collection_id:
            return None

        collection = str(collection_id)
        await self.cache.set_json(
            cache_key,
            {"collection": collection},
            self.settings.common_crawl_cache_ttl_seconds,
        )
        return collection

    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        try:
            pattern = build_common_crawl_pattern(
                ctx.identifier_type,
                ctx.identifier_canonical,
            )
        except ValueError as exc:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                skipped=True,
                skip_reason="unsupported_type",
                error=str(exc),
            )

        cache_key = self.cache.make_key(
            "common_crawl",
            ctx.identifier_type,
                cache_key = self.cache.make_key(
            "common_crawl",
            ctx.identifier_type,
            pattern,
        )

        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            observations = [
                self._observation_from_dict(item)
                for item in cached.get("observations", [])
                if isinstance(item, dict)
            ]
            return ConnectorResult(
                connector_id=self.capability.id,
                success=True,
                observations=observations,
                cache_hit=True,
                meta={
                    "layer": ConnectorLayer.DEEP.value,
                    "metadata_only": True,
                    "attribution": self.capability.attribution,
                },
            )

        await self.rate_limiter.acquire(
            "common_crawl",
            per_second=self.settings.common_crawl_rate_per_second,
            per_hour=self.settings.common_crawl_rate_per_hour,
            per_day=self.settings.common_crawl_rate_per_day,
        )

        collection = await self._resolve_collection()
        if not collection:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                skipped=True,
                skip_reason="cache_only_error",
                error="Unable to resolve a Common Crawl collection",
            )

        base = self.settings.common_crawl_index_base_url.rstrip("/")
        url = (
            f"{base}/{quote(collection, safe='')}-index"
            f"?url={quote(pattern, safe='')}"
            "&output=json"
            "&filter=status:200"
            f"&pageSize={self.settings.common_crawl_max_results}"
        )

        try:
            response = await self.egress.fetch(
                url,
                purpose="discovery.deep.common_crawl",
                timeout=30.0,
            )
        except EgressError as exc:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error=str(exc),
            )

        if response.status_code == 404:
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
                    "collection": collection,
                    "result_count": 0,
                    "metadata_only": True,
                },
            )

        if response.status_code != 200:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error=f"Common Crawl HTTP {response.status_code}",
            )

        rows = parse_cdx_json_lines(
            response.body,
            max_results=self.settings.common_crawl_max_results,
        )

        observations: list[RawObservation] = []

        for row in rows:
            observed_url = str(row.get("url") or "")
            if not observed_url:
                continue

            timestamp = row.get("timestamp")
            observed_at = None

            if timestamp:
                try:
                    observed_at = datetime.strptime(
                        str(timestamp),
                        "%Y%m%d%H%M%S",
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    observed_at = None

            observations.append(
                RawObservation(
                    kind=ObservationKind.ARCHIVED_METADATA,
                    source=self.capability.id,
                    title="Archived URL metadata match",
                    summary=(
                        "A public crawl index contains URL metadata matching the "
                        "verified identifier query. The archived page was not "
                        "retrieved or stored."
                    ),
                    confidence=0.45,
                    observed_at=observed_at or datetime.now(timezone.utc),
                    layer=ConnectorLayer.DEEP,
                    raw_ref=observed_url[:512],
                    attributes={
                        "url": observed_url[:512],
                        "status": row.get("status"),
                        "mime": row.get("mime"),
                        "timestamp": timestamp,
                        "digest_present": bool(row.get("digest")),
                        "length": row.get("length"),
                        "collection": collection,
                        "metadata_only": True,
                    },
                    attribution=self.capability.attribution,
                )
            )

        ttl = (
            self.settings.common_crawl_cache_ttl_seconds
            if observations
            else self.settings.connector_negative_cache_ttl_seconds
        )

        await self.cache.set_json(
            cache_key,
            {
                "observations": [
                    observation.to_dict()
                    for observation in observations
                ]
            },
            ttl,
        )

        return ConnectorResult(
            connector_id=self.capability.id,
            success=True,
            observations=observations,
            meta={
                "collection": collection,
                "result_count": len(observations),
                "metadata_only": True,
                "attribution": self.capability.attribution,
            },
        )

    @staticmethod
    def _observation_from_dict(
        value: dict[str, Any],
    ) -> RawObservation:
        observed_at = None
        raw_observed_at = value.get("observed_at")

        if raw_observed_at:
            try:
                observed_at = datetime.fromisoformat(
                    str(raw_observed_at).replace("Z", "+00:00")
                )
            except ValueError:
                observed_at = None

        return RawObservation(
            kind=ObservationKind(
                value.get("kind", ObservationKind.ARCHIVED_METADATA.value)
            ),
            source=str(value.get("source", "common_crawl")),
            title=str(value.get("title", "Archived URL metadata match")),
            summary=str(value.get("summary", "")),
            confidence=float(value.get("confidence", 0.45)),
            observed_at=observed_at,
            layer=ConnectorLayer(
                value.get("layer", ConnectorLayer.DEEP.value)
            ),
            raw_ref=value.get("raw_ref"),
            attributes=value.get("attributes") or {},
            attribution=value.get("attribution"),
        )
```

---

# PART G.1 — Common Crawl Collection and Provenance Rules

If `COMMON_CRAWL_COLLECTION` is configured, use that pinned collection.

If it is empty, collection discovery must:

1. use an approved Common Crawl metadata endpoint through `EgressFetcher`;
2. select the latest supported collection using a deterministic rule;
3. cache the selected collection;
4. record the selected collection identifier in observation provenance;
5. never silently hardcode a collection that will become stale.

Every Common Crawl observation must retain durable redacted provenance equivalent to:

```text
source       = common_crawl
layer        = deep
collection   = CC-MAIN-...
query_mode   = domain_index
retrieved_at = ...
attribution  = Common Crawl
```

The collection identifier is part of reproducibility and explainability.

---

# PART H — Wayback Metadata Connector

The Wayback connector uses availability metadata only. A historical capture does not prove that the information is currently public, and DigiZafe does not retain the archived page body.

## 8. NEW: `backend/app/connectors/impl/deep/wayback.py`

```python
"""Internet Archive Wayback availability metadata adapter."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorLayer,
    ConnectorResult,
    LegalityTier,
    ObservationKind,
    RawObservation,
)
from app.security.egress import EgressError


class WaybackConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="wayback",
            name="Internet Archive Wayback Availability",
            layer=ConnectorLayer.DEEP,
            legality=LegalityTier.AMBER,
            requires_paid_key=False,
            sends_identifier=True,
            supported_identifier_types=["domain"],
            attribution="Internet Archive Wayback Machine",
            description=(
                "Historical availability metadata for a verified domain. "
                "Archived page bodies are not stored."
            ),
        )

    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        domain = ctx.identifier_canonical

        cache_key = self.cache.make_key(
            "wayback",
            "availability",
            domain,
        )

        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            observations = [
                self._from_dict(item)
                for item in cached.get("observations", [])
                if isinstance(item, dict)
            ]
            return ConnectorResult(
                connector_id=self.capability.id,
                success=True,
                observations=observations,
                cache_hit=True,
                meta={
                    "metadata_only": True,
                    "attribution": self.capability.attribution,
                },
            )

        await self.rate_limiter.acquire(
            "wayback",
            per_second=self.settings.wayback_rate_per_second,
            per_hour=self.settings.wayback_rate_per_hour,
            per_day=self.settings.wayback_rate_per_day,
        )

        target = f"https://{domain}/"
        url = (
            f"{self.settings.wayback_availability_url}"
            f"?url={quote(target, safe='')}"
        )

        try:
            response = await self.egress.fetch(
                url,
                purpose="discovery.deep.wayback",
                timeout=30.0,
            )
        except EgressError as exc:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error=str(exc),
            )

        if response.status_code != 200:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error=f"Wayback HTTP {response.status_code}",
            )

        try:
            payload = json.loads(
                response.body.decode("utf-8", errors="replace")
            )
        except json.JSONDecodeError:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error="Invalid JSON from Wayback availability endpoint",
            )

        closest = (
            payload.get("archived_snapshots", {}).get("closest")
            if isinstance(payload, dict)
            else None
        )

        observations: list[RawObservation] = []

        if isinstance(closest, dict) and closest.get("available"):
            timestamp = closest.get("timestamp")
            observed_at = datetime.now(timezone.utc)

            if timestamp:
                try:
                    observed_at = datetime.strptime(
                        str(timestamp),
                        "%Y%m%d%H%M%S",
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            observations.append(
                RawObservation(
                    kind=ObservationKind.ARCHIVED_METADATA,
                    source=self.capability.id,
                    title="Wayback capture available",
                    summary=(
                        "The verified domain has a historical Wayback capture. "
                        "This is historical metadata and does not prove current exposure."
                    ),
                    confidence=0.5,
                    observed_at=observed_at,
                    layer=ConnectorLayer.DEEP,
                    raw_ref=str(closest.get("url") or target)[:512],
                    attributes={
                        "domain": domain,
                        "timestamp": timestamp,
                        "status": closest.get("status"),
                        "archived_url_present": bool(closest.get("url")),
                        "metadata_only": True,
                    },
                    attribution=self.capability.attribution,
                )
            )

        ttl = (
            self.settings.wayback_cache_ttl_seconds
            if observations
            else self.settings.connector_negative_cache_ttl_seconds
        )

        await self.cache.set_json(
            cache_key,
            {
                "observations": [
                    observation.to_dict()
                    for observation in observations
                ]
            },
            ttl,
        )

        return ConnectorResult(
            connector_id=self.capability.id,
            success=True,
            observations=observations,
            meta={
                "result_count": len(observations),
                "metadata_only": True,
                "attribution": self.capability.attribution,
            },
        )

    @staticmethod
    def _from_dict(value: dict[str, Any]) -> RawObservation:
        observed_at = None
        raw_observed_at = value.get("observed_at")

        if raw_observed_at:
            try:
                observed_at = datetime.fromisoformat(
                    str(raw_observed_at).replace("Z", "+00:00")
                )
            except ValueError:
                observed_at = None

        return RawObservation(
            kind=ObservationKind(
                value.get("kind", ObservationKind.ARCHIVED_METADATA.value)
            ),
            source=str(value.get("source", "wayback")),
            title=str(value.get("title", "Wayback capture available")),
            summary=str(value.get("summary", "")),
            confidence=float(value.get("confidence", 0.5)),
            observed_at=observed_at,
            layer=ConnectorLayer(
                value.get("layer", ConnectorLayer.DEEP.value)
            ),
            raw_ref=value.get("raw_ref"),
            attributes=value.get("attributes") or {},
            attribution=value.get("attribution"),
        )
```

---

# PART H.1 — Wayback Evidence Semantics

A Wayback availability response means only that an archive snapshot appears to exist. Snapshot existence is not, by itself, proof of sensitive personal exposure.

Default handling:

```text
archive availability only
→ observation / context

archive metadata linked to a verified identifier
→ possible finding only when the existing normalization policy supports it

confirmed sensitive exposure
→ requires stronger evidence than snapshot existence
```

Do not inflate PDSS merely because a domain has historical snapshots. Do not retrieve or retain archived page bodies in Sprint 11.

---

# PART I — Constrained-Dark Public Index Connector

This adapter is intentionally inert unless `AMBER_PUBLIC_INDEX_URL` is configured and `FEATURE_CONSTRAINED_DARK=true`.

It only supports:

- HTTPS
- Explicit host allowlisting
- Public unauthenticated JSON responses
- Metadata-only result extraction
- Small result limits
- No `.onion` hostnames
- No direct IP endpoints
- No redirects
- No raw dump retrieval

## 9. NEW: `backend/app/connectors/impl/dark_constrained/public_index.py`

```python
"""Operator-approved public index adapter for Constrained-Dark Amber.

This is not a Tor client and does not crawl onion services.
The endpoint must be configured by the operator and allowlisted explicitly.
"""

from __future__ import annotations

import ipaddress
import json
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorLayer,
    ConnectorResult,
    LegalityTier,
    ObservationKind,
    RawObservation,
)
from app.security.egress import EgressBlockedError, EgressError


def validate_public_index_endpoint(
    endpoint: str,
    allowlisted_hosts: set[str],
) -> tuple[str, str]:
    parsed = urlparse(endpoint)

    if parsed.scheme.lower() != "https":
        raise EgressBlockedError(
            "Constrained-Dark public index must use HTTPS"
        )

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise EgressBlockedError(
            "Constrained-Dark public index is missing a hostname"
        )

    if hostname.endswith(".onion") or hostname == "onion":
        raise EgressBlockedError(
            "Direct .onion access is prohibited"
        )

    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise EgressBlockedError(
            "Direct IP endpoints are prohibited for Constrained-Dark"
        )

    if not allowlisted_hosts:
        raise EgressBlockedError(
            "Constrained-Dark endpoint requires an explicit host allowlist"
        )

    if hostname not in allowlisted_hosts:
        raise EgressBlockedError(
            f"Host is not allowlisted: {hostname}"
        )

    return hostname, endpoint


def append_query(endpoint: str, query_param: str, value: str) -> str:
    parsed = urlparse(endpoint)
    pairs = list(parse_qsl(parsed.query, keep_blank_values=True))
    pairs.append((query_param, value))

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(pairs),
            parsed.fragment,
        )
    )


def parse_public_index_payload(
    payload: Any,
    *,
    max_results: int,
) -> list[dict[str, Any]]:
    """
    Accept conservative JSON shapes:
    - {"results": [...]}
    - {"items": [...]}
    - [...]
    """
    if isinstance(payload, dict):
        values = payload.get("results")
        if values is None:
            values = payload.get("items")
    else:
        values = payload

    if not isinstance(values, list):
        return []

    output: list[dict[str, Any]] = []

    for item in values[:max_results]:
        if isinstance(item, dict):
            output.append(item)

    return output


class PublicIndexConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="public_index",
            name="Operator-approved Public Index",
            layer=ConnectorLayer.CONSTRAINED_DARK,
            legality=LegalityTier.AMBER,
            requires_paid_key=False,
            sends_identifier=True,
            supported_identifier_types=[
                "domain",
                "username",
                "github_username",
            ],
            attribution="Configured operator-approved public index",
            description=(
                "Metadata-only adapter for one explicitly configured HTTPS public index. "
                "No Tor or onion access."
            ),
        )

    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        endpoint = self.settings.amber_public_index_url.strip()

        if not endpoint:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                skipped=True,
                skip_reason="not_configured",
                error=(
                    "AMBER_PUBLIC_INDEX_URL is empty. "
                    "No Constrained-Dark endpoint is configured."
                ),
            )

        try:
            host, _ = validate_public_index_endpoint(
                endpoint,
                self.settings.amber_public_index_hosts,
            )
        except EgressBlockedError as exc:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                skipped=True,
                skip_reason="amber_policy_blocked",
                error=str(exc),
            )

        query_value = ctx.identifier_canonical

        cache_key = self.cache.make_key(
            "public_index",
            ctx.identifier_type,
            query_value,
            host,
        )

        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            observations = [
                self._from_dict(item)
                for item in cached.get("observations", [])
                if isinstance(item, dict)
            ]
            return ConnectorResult(
                connector_id=self.capability.id,
                success=True,
                observations=observations,
                cache_hit=True,
                meta={
                    "layer": ConnectorLayer.CONSTRAINED_DARK.value,
                    "metadata_only": True,
                    "endpoint_host": host,
                    "attribution": self.capability.attribution,
                },
            )

        await self.rate_limiter.acquire(
            "public_index",
            per_second=self.settings.amber_public_index_rate_per_second,
            per_hour=self.settings.amber_public_index_rate_per_hour,
            per_day=self.settings.amber_public_index_rate_per_day,
        )

        url = append_query(
            endpoint,
            self.settings.amber_public_index_query_param,
            query_value,
        )

        try:
            response = await self.egress.fetch(
                url,
                headers={"Accept": "application/json"},
                purpose="discovery.constrained_dark.public_index",
                timeout=30.0,
            )
        except EgressError as exc:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error=str(exc),
            )

        if response.status_code != 200:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error=f"Configured public index HTTP {response.status_code}",
            )

        try:
            payload = json.loads(
                response.body.decode("utf-8", errors="replace")
            )
        except json.JSONDecodeError:
            return ConnectorResult(
                connector_id=self.capability.id,
                success=False,
                error="Configured public index did not return JSON",
            )

        rows = parse_public_index_payload(
            payload,
            max_results=self.settings.amber_public_index_max_results,
        )

        observations: list[RawObservation] = []

        for row in rows:
            # Keep only conservative metadata fields.
            reference = (
                row.get("id")
                or row.get("url")
                or row.get("reference")
                or row.get("title")
                or "public-index-result"
            )

            observations.append(
                RawObservation(
                    kind=ObservationKind.PUBLIC_INDEX_SIGNAL,
                    source=self.capability.id,
                    title="Configured public-index metadata match",
                    summary=(
                        "The configured public index returned a metadata match. "
                        "DigiZafe does not retrieve, store, or display raw dump content."
                    ),
                    confidence=0.35,
                    layer=ConnectorLayer.CONSTRAINED_DARK,
                    raw_ref=str(reference)[:512],
                    attributes={
                        "index_host": host,
                        "record_type": row.get("type"),
                        "record_id": str(row.get("id"))[:256]
                        if row.get("id") is not None
                        else None,
                        "reference": str(row.get("reference"))[:512]
                        if row.get("reference") is not None
                        else None,
                        "date": row.get("date") or row.get("timestamp"),
                        "metadata_only": True,
                        "raw_content_retrieved": False,
                    },
                    attribution=self.capability.attribution,
                )
            )

        ttl = (
            self.settings.amber_public_index_cache_ttl_seconds
            if observations
            else self.settings.connector_negative_cache_ttl_seconds
        )

        await self.cache.set_json(
            cache_key,
            {
                "observations": [
                    observation.to_dict()
                    for observation in observations
                ]
            },
            ttl,
        )

        return ConnectorResult(
            connector_id=self.capability.id,
            success=True,
            observations=observations,
            meta={
                "layer": ConnectorLayer.CONSTRAINED_DARK.value,
                "endpoint_host": host,
                "result_count": len(observations),
                "metadata_only": True,
                "attribution": self.capability.attribution,
            },
        )

    @staticmethod
    def _from_dict(value: dict[str, Any]) -> RawObservation:
        return RawObservation(
            kind=ObservationKind(
                value.get(
                    "kind",
                    ObservationKind.PUBLIC_INDEX_SIGNAL.value,
                )
            ),
            source=str(value.get("source", "public_index")),
            title=str(
                value.get(
                    "title",
                    "Configured public-index metadata match",
                )
            ),
            summary=str(value.get("summary", "")),
            confidence=float(value.get("confidence", 0.35)),
            layer=ConnectorLayer(
                value.get(
                    "layer",
                    ConnectorLayer.CONSTRAINED_DARK.value,
                )
            ),
            raw_ref=value.get("raw_ref"),
            attributes=value.get("attributes") or {},
            attribution=value.get("attribution"),
        )
```

---

# PART I.1 — Constrained-Dark Fail-Closed Rules

The public-index connector may dispatch only when **all** of the following are true:

- the identifier is verified;
- `FEATURE_CONSTRAINED_DARK=true`;
- an endpoint is configured;
- the destination host is present in the approved allowlist;
- the connector is enabled in the canonical registry;
- required layer consent exists;
- connector/destination-aware egress authorization exists where identifier disclosure occurs;
- the request can be executed through `EgressFetcher`.

If the endpoint is blank, the connector is inert even if the feature flag is accidentally enabled.

A generic consent record for `discovery.constrained_dark` must not silently authorize a newly configured host. Reuse the existing ConsentService model and bind authorization to the most specific supported combination of purpose, scope, connector, destination, and policy version.

---

# PART J — Connector Registry

## 10. UPDATE: `backend/app/connectors/registry.py`

Replace the file with:

```python
"""Build all DigiZafe connectors."""

from __future__ import annotations

from typing import Dict, List

from app.connectors.impl.deep.common_crawl import CommonCrawlConnector
from app.connectors.impl.deep.wayback import WaybackConnector
from app.connectors.impl.dark_constrained.public_index import (
    PublicIndexConnector,
)
from app.connectors.impl.surface.crtsh import CrtShConnector
from app.connectors.impl.surface.github_connector import GitHubConnector
from app.connectors.impl.surface.gravatar import GravatarConnector
from app.connectors.impl.surface.pwned_passwords import (
    PwnedPasswordsConnector,
)
from app.connectors.impl.surface.rdap import RdapConnector
from app.connectors.impl.surface.serp_ddg import SerpDdgConnector
from app.connectors.impl.surface.username_presence import (
    UsernamePresenceConnector,
)
from app.connectors.impl.surface.xposedornot import XposedOrNotConnector
from app.connectors.sdk.base import Connector
from app.connectors.sdk.cache import ConnectorCache
from app.connectors.sdk.rate_limiter import RateLimiter
from app.connectors.sdk.redis_clients import get_cache_redis
from app.security.egress import get_egress_fetcher


async def build_connectors() -> Dict[str, Connector]:
    redis = await get_cache_redis()
    egress = get_egress_fetcher()
    rate_limiter = RateLimiter(redis)
    cache = ConnectorCache(redis)

    common = {
        "egress": egress,
        "rate_limiter": rate_limiter,
        "cache": cache,
    }

    instances: List[Connector] = [
        # Surface
        XposedOrNotConnector(**common),
        PwnedPasswordsConnector(**common),
        CrtShConnector(**common),
        RdapConnector(**common),
        GitHubConnector(**common),
        GravatarConnector(**common),
        UsernamePresenceConnector(**common),
        SerpDdgConnector(**common),

        # Deep Amber
        CommonCrawlConnector(**common),
        WaybackConnector(**common),

        # Constrained-Dark Amber
        PublicIndexConnector(**common),
    ]

    return {
        connector.capability.id: connector
        for connector in instances
    }
```

---

# PART K — Finding Normalization Updates

## 11. UPDATE: `backend/app/domain/findings_normalize.py`

Inside `normalize_observation()`, add this branch before the final `else`:

```python
    elif kind == "archived_metadata":
        severity = "info"
        track = "possible"
        attrs.setdefault("historical_or_indexed", True)
        attrs.setdefault("current_exposure_unproven", True)

    elif kind == "public_index_signal":
        severity = "medium" if confidence >= 0.6 else "low"
        track = "possible"
        attrs.setdefault("metadata_only", True)
        attrs.setdefault("raw_content_retrieved", False)
        attrs.setdefault("current_exposure_unproven", True)
```

Update the return documentation:

```python
# kind values include:
# breach | password_exposure | certificate | dns_rdap | profile |
# username_presence | serp | archived_metadata | public_index_signal | other
```

Update `_fingerprint()` to include the layer:

```python
def _fingerprint(
    source: str,
    kind: str,
    raw_ref: str | None,
    title: str,
    layer: str = "surface",
) -> str:
    import hashlib

    base = (
        f"{source}|{kind}|{layer}|"
        f"{(raw_ref or title).strip().lower()}"
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:40]
```

Update its call site:

```python
    fp = _fingerprint(
        source,
        kind,
        str(raw_ref) if raw_ref else None,
        title,
        layer,
    )
```

This prevents an identical reference from a Surface connector and a Deep connector being silently merged.

---

# PART K.1 — Layer Is Not Severity

Normalization and scoring must preserve this invariant:

```text
surface / deep / constrained_dark
= provenance and discovery context

severity / confidence / PDSS contribution
= evidence-driven risk assessment
```

Never implement a rule equivalent to:

```text
constrained_dark => critical
deep => higher severity
```

A low-confidence public-index mention must not outrank a confirmed high-impact credential exposure merely because of its layer label. Existing sensitivity, discoverability, linkability, impact, temporal, confidence, and evidence-quality rules remain authoritative.

---

# PART L — PDSS Catalog Update

## 12. UPDATE: `shared/score_model/pdss_catalog.json`

Add these entries under `kind_base_weights`:

```json
"archived_metadata": {
  "sensitivity": 0.25,
  "discoverability": 0.65,
  "linkability": 0.45,
  "impact": 0.20
},
"public_index_signal": {
  "sensitivity": 0.55,
  "discoverability": 0.70,
  "linkability": 0.65,
  "impact": 0.50
}
```

Update `layer_multipliers`:

```json
"layer_multipliers": {
  "surface": 1.0,
  "deep": 1.08,
  "constrained_dark": 1.15
}
```

Add this explanatory metadata at the root:

```json
"amber_policy": {
  "deep_is_historical_or_indexed": true,
  "constrained_dark_is_metadata_only": true,
  "current_exposure_requires_confirmation": true,
  "raw_dump_content_is_never_required": true
}
```

The PDSS engine already reads `layer` from each finding, so no formula rewrite is required.

---

# PART M — Scan Schema and Amber Gating

## 13. UPDATE: `backend/app/schemas/scan.py`

Replace `ScanCreate` with:

```python
class ScanCreate(BaseModel):
    identifier_id: UUID
    connector_ids: Optional[list[str]] = None

    layer_scope: str = Field(
        default="surface",
        pattern="^(surface|deep|constrained_dark)$",
    )
```

Add:

```python
class LayerMetadataPublic(BaseModel):
    layer: str
    label: str
    description: str
    warning: str
    requires_explicit_consent: bool
```

---

## 14. UPDATE: `backend/app/services/discovery_service.py`

Add imports:

```python
from app.domain.amber_layers import (
    AmberPolicyError,
    ExposureLayer,
    consent_purpose_for_layer,
    layer_matches_connector,
    public_layer_metadata,
    validate_layer_scope,
)
from app.connectors.sdk.types import LegalityTier
```

Add this method to `DiscoveryService`:

```python
    async def _validate_amber_consent(
        self,
        user_id: uuid.UUID,
        layer_scope: ExposureLayer,
    ) -> None:
        purpose = consent_purpose_for_layer(layer_scope)

        if not purpose:
            return

        if not self.settings.amber_scan_requires_consent:
            return

        granted = await self.consent.ensure_consent(
            user_id,
            purpose=purpose,
            auto_grant=False,
            scope=layer_scope.value,
        )

        if not granted:
            raise HTTPException(
                status_code=428,
                detail={
                    "code": "AMBER_CONSENT_REQUIRED",
                    "purpose": purpose,
                    "layer": layer_scope.value,
                    "message": (
                        f"Explicit consent is required for {layer_scope.value} "
                        "discovery before the scan can be queued."
                    ),
                },
            )
```

Add this method:

```python
    async def layer_catalog(self) -> list[dict[str, Any]]:
        return [
            public_layer_metadata(ExposureLayer.SURFACE),
            public_layer_metadata(ExposureLayer.DEEP),
            public_layer_metadata(ExposureLayer.CONSTRAINED_DARK),
        ]
```

Inside `create_scan()`, replace the initial layer handling with:

```python
        try:
            requested_layer = validate_layer_scope(
                layer_scope,
                feature_deep_amber=self.settings.feature_deep_amber,
                feature_constrained_dark=self.settings.feature_constrained_dark,
            )
        except AmberPolicyError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        await self._validate_amber_consent(user_id, requested_layer)
```

Replace connector selection logic with:

```python
        if connector_ids:
            selected = []

            for connector_id in connector_ids:
                connector = connectors.get(connector_id)

                if not connector:
                    continue

                if not layer_matches_connector(
                    requested_layer,
                    connector.capability.layer.value,
                ):
                    continue

                if connector.capability.legality == LegalityTier.RED:
                    continue

                if not connector.is_enabled_by_config():
                    continue

                if not connector.supports(ident.type):
                    continue

                selected.append(connector_id)
        else:
            selected = [
                connector_id
                for connector_id, connector in connectors.items()
                if connector.supports(ident.type)
                and layer_matches_connector(
                    requested_layer,
                    connector.capability.layer.value,
                )
                and connector.capability.legality != LegalityTier.RED
                and connector.is_enabled_by_config()
                and (db_flags.get(connector_id) is not False)
            ]
```

Update the empty selection error:

```python
        if not selected:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "NO_CONNECTORS_FOR_LAYER",
                    "layer": requested_layer.value,
                    "message": (
                        "No enabled connectors support this identifier type "
                        "for the requested layer."
                    ),
                },
            )
```

Store the layer metadata in the scan audit:

```python
        await self.audit.log(
            "scan.created",
            user_id=user_id,
            resource_type="scan",
            resource_id=str(scan.id),
            details={
                "identifier_id": str(ident.id),
                "connectors": selected,
                "layer_scope": requested_layer.value,
                "amber": requested_layer != ExposureLayer.SURFACE,
            },
        )
```

In `execute_scan()`, before the connector is run, add:

```python
            connector_layer = connector.capability.layer.value
            requested_layer = scan.layer_scope

            if connector_layer != requested_layer:
                await self.scans.set_run_status(
                    run,
                    ConnectorRunStatus.SKIPPED,
                    skip_reason="amber_policy_blocked",
                    error=(
                        f"Connector layer {connector_layer} does not match "
                        f"scan layer {requested_layer}"
                    ),
                )
                await self.scans.recompute_progress(scan)
                await self.session.commit()
                continue

            if connector.capability.legality == LegalityTier.AMBER:
                try:
                    await self._validate_amber_consent(
                        scan.user_id,
                        ExposureLayer(requested_layer),
                    )
                except HTTPException:
                    await self.scans.set_run_status(
                        run,
                        ConnectorRunStatus.SKIPPED,
                        skip_reason="no_consent",
                        error="Amber consent was revoked before worker execution",
                    )
                    await self.scans.recompute_progress(scan)
                    await self.session.commit()
                    continue
```

Add the layer to connector egress summaries:

```python
                    summary={
                        "connector": cid,
                        "scan_id": str(scan.id),
                        "layer": scan.layer_scope,
                        "cache_hit": result.cache_hit,
                        "skipped": result.skipped,
                        "observation_count": len(result.observations),
                    },
```

Update the host mapping:

```python
                host = {
                    "xposedornot": "api.xposedornot.com",
                    "crtsh": "crt.sh",
                    "rdap": "rdap.org",
                    "github": "api.github.com",
                    "username_presence": "multi",
                    "serp_ddg": "html.duckduckgo.com",
                    "gravatar": "www.gravatar.com",
                    "common_crawl": "index.commoncrawl.org",
                    "wayback": "archive.org",
                    "public_index": (
                        self.settings.amber_public_index_hosts.pop()
                        if self.settings.amber_public_index_hosts
                        else "configured-public-index"
                    ),
                }.get(cid, cid)
```

Use a local copy instead of mutating the settings property:

```python
                elif cid == "public_index":
                    configured_hosts = self.settings.amber_public_index_hosts
                    host = (
                        sorted(configured_hosts)[0]
                        if configured_hosts
                        else "configured-public-index"
                    )
```

Recommended final form:

```python
                host_map = {
                    "xposedornot": "api.xposedornot.com",
                    "crtsh": "crt.sh",
                    "rdap": "rdap.org",
                    "github": "api.github.com",
                    "username_presence": "multi",
                    "serp_ddg": "html.duckduckgo.com",
                    "gravatar": "www.gravatar.com",
                    "common_crawl": "index.commoncrawl.org",
                    "wayback": "archive.org",
                }

                host = host_map.get(cid)

                if cid == "public_index":
                    configured_hosts = self.settings.amber_public_index_hosts
                    host = (
                        sorted(configured_hosts)[0]
                        if configured_hosts
                        else "configured-public-index"
                    )

                host = host or cid
```

---

## 15. NEW: `backend/app/api/v1/layers.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.services.discovery_service import DiscoveryService

router = APIRouter(prefix="/layers", tags=["layers"])


def _svc(db: AsyncSession = Depends(get_db)) -> DiscoveryService:
    return DiscoveryService(db)


@router.get("")
async def list_layers(
    current_user: CurrentUser,
    svc: DiscoveryService = Depends(_svc),
):
    """Return layer definitions and consent requirements."""
    return await svc.layer_catalog()
```

---

## 16. UPDATE: `backend/app/main.py`

Add `layers` to the imports:

```python
from app.api.v1 import (
    health,
    auth,
    identifiers,
    connectors,
    scans,
    identity,
    scores,
    recommendations,
    alerts,
    remediation,
    privacy,
    layers,
)
```

Register the router:

```python
app.include_router(layers.router, prefix=settings.api_v1_prefix)
```

Update root metadata:

```python
"version": "0.11.0",
"message": "DigiZafe Sprint 11 Deep + Constrained-Dark Free Amber — ready",
```

No Alembic migration is required for Sprint 11. The existing `scans.layer_scope`, `observations.layer`, `findings.layer`, consent records, and egress ledger already support this scope.

---

# PART M.1 — Consent and Egress Authorization Contract

Amber scans require explicit consent, but consent must remain honest about the actual outbound destination.

At minimum, the UI/backend contract should expose or derive:

```text
layer
connector_id
purpose
destination_host
data/query shape disclosed
policy/registry version
```

Example disclosure:

```text
Layer: Deep — Public Archives
Source: Common Crawl
Destination: index.commoncrawl.org
Data sent: verified domain query
Purpose: archive-index discovery
Retention: DigiZafe stores metadata/provenance only
```

Reuse the existing ConsentService and egress ledger. Do not introduce a second consent database or bypass the existing egress authorization path.

---

# PART N — Frontend Amber UX

## Frontend terminology

Keep canonical API values:

```text
surface
deep
constrained_dark
```

Use explanatory user-facing labels:

```text
Surface
Public web and standard exposure sources

Deep — Public Archives
Historical and indexed public metadata

Constrained-Dark — Public Indexes
Operator-approved public metadata indexes only
```

Do not imply unrestricted dark-web coverage.

## 17. UPDATE: `frontend/src/lib/types.ts`

Append:

```typescript
export type ExposureLayer = "surface" | "deep" | "constrained_dark";

export interface LayerMetadata {
  layer: ExposureLayer;
  label: string;
  description: string;
  warning: string;
  requires_explicit_consent: boolean;
}

export interface LayerCatalogResponse extends Array<LayerMetadata> {}

export interface ScanCreateRequest {
  identifier_id: string;
  connector_ids?: string[];
  layer_scope: ExposureLayer;
}
```

Update `ScanPublic`:

```typescript
export interface ScanPublic {
  id: string;
  identifier_id: string;
  status: string;
  layer_scope: ExposureLayer;
  connector_ids?: string[] | null;
  progress_pct: number;
  message?: string | null;
  error?: string | null;
  observation_count: number;
  finding_count: number;
  deadline_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  meta?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  connector_runs?: ScanConnectorRun[];
}
```

Update `FindingPublic`:

```typescript
export interface FindingPublic {
  id: string;
  identifier_id: string;
  kind: string;
  source: string;
  title: string;
  summary: string;
  severity_hint: string;
  confidence: number;
  layer: ExposureLayer;
  track: string;
  raw_ref?: string | null;
  attributes?: Record<string, unknown> | null;
  attribution?: string | null;
  first_seen_at: string;
  last_seen_at: string;
  times_seen: number;
  status: string;
  created_at: string;
}
```

---

## 18. NEW: `frontend/src/features/scans/layers-api.ts`

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { LayerMetadata } from "@/lib/types";

export function useLayerCatalog() {
  return useQuery({
    queryKey: ["layers"],
    queryFn: () => api.get<LayerMetadata[]>("/layers"),
  });
}
```

---

## 19. NEW: `frontend/src/features/scans/LayerScopeControl.tsx`

```tsx
import { AlertTriangle, CheckCircle2, LockKeyhole } from "lucide-react";
import { useLayerCatalog } from "./layers-api";
import type { ExposureLayer } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface LayerScopeControlProps {
  value: ExposureLayer;
  onChange: (value: ExposureLayer) => void;
  hasConsent: (layer: ExposureLayer) => boolean;
}

export function LayerScopeControl({
  value,
  onChange,
  hasConsent,
}: LayerScopeControlProps) {
  const layers = useLayerCatalog();

  return (
    <div className="grid gap-3 md:grid-cols-3">
      {(layers.data || []).map((layer) => {
        const selected = value === layer.layer;
        const consented = hasConsent(layer.layer);

        return (
          <button
            key={layer.layer}
            type="button"
            onClick={() => onChange(layer.layer)}
            className={`text-left transition-colors ${
              selected ? "ring-2 ring-primary" : ""
            }`}
            aria-pressed={selected}
          >
            <Card className={selected ? "border-primary bg-primary/10" : ""}>
              <CardContent className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-medium">{layer.label}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {layer.layer}
                    </div>
                  </div>

                  {selected && (
                    <CheckCircle2
                      className="h-5 w-5 text-primary"
                      aria-label="Selected"
                    />
                  )}
                </div>

                <p className="text-xs text-muted-foreground">
                  {layer.description}
                </p>

                {layer.requires_explicit_consent ? (
                  <Badge
                    variant={consented ? "default" : "secondary"}
                    className="gap-1"
                  >
                    <LockKeyhole className="h-3 w-3" />
                    {consented ? "Consent granted" : "Consent required"}
                  </Badge>
                ) : (
                  <Badge variant="outline">Default layer</Badge>
                )}

                {layer.layer !== "surface" && (
                  <div className="flex gap-2 rounded-md border border-amber-400/20 bg-amber-400/5 p-2 text-xs text-amber-100">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <span>{layer.warning}</span>
                  </div>
                )}
              </PDATE: `frontend/src/features/scans/api.ts`

Update `useCreateScan()`:

```typescript
import type {
  ScanCreateRequest,
  ScanPublic,
} from "@/lib/types";

export function useCreateScan() {ript
import type {
  ScanCreateRequest,
  ScanPublic,
} from "@/lib/types";

export function useCreateScan() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (body: ScanCreateRequest) =>
      api.post<ScanPublic>("/scans", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scans"] });
    },
  });
}
```

---

## 21. UPDATE: `frontend/src/features/scans/ScansPage.tsx`

Replace the existing page with:

```tsx
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, LockKeyhole, ShieldCheck } from "lucide-react";

import { useIdentifiers } from "@/features/identifiers/api";
import { useConsent, useGrantConsent } from "@/features/privacy/api";
import { useCreateScan, useScans, useCancelScan } from "./api";
import { LayerScopeControl } from "./LayerScopeControl";
import { openScanSse } from "@/lib/sse";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

import type {
  ExposureLayer,
  ScanPublic,
} from "@/lib/types";

const TERMINAL_STATUSES = [
  "completed",
  "partial",
  "failed",
  "cancelled",
  "timed_out",
];

function consentPurpose(layer: ExposureLayer): string | null {
  if (layer === "deep") return "discovery.deep";
  if (layer === "constrained_dark") return "discovery.constrained_dark";
  return null;
}

export function ScansPage() {
  const ids = useIdentifiers();
  const consents = useConsent();
  const scans = useScans();
  const create = useCreateScan();
  const cancel = useCancelScan();
  const grantConsent = useGrantConsent();

  const verified = (ids.data || []).filter((item) => item.is_verified);

  const [selectedIdentifier, setSelectedIdentifier] = useState("");
  const [layerScope, setLayerScope] = useState<ExposureLayer>("surface");
  const [live, setLive] = useState<ScanPublic | null>(null);
  const [sseNote, setSseNote] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const requiredPurpose = consentPurpose(layerScope);

  const hasConsent = useMemo(
    () => (layer: ExposureLayer) => {
      const purpose = consentPurpose(layer);
      if (!purpose) return true;

      return Boolean(
        (consents.data || []).some(
          (item) => item.purpose === purpose && item.granted
        )
      );
    },
    [consents.data]
  );

  const selectedHasConsent = hasConsent(layerScope);

  useEffect(() => {
    if (!live?.id || TERMINAL_STATUSES.includes(live.status)) {
      return;
    }

    const stop = openScanSse(live.id, {
      onEvent: (event, data) => {
        if (
          event !== "scan" &&
          event !== "done" &&
          event !== "message"
        ) {
          return;
        }

        const payload = data as Partial<ScanPublic> & {
          scan_id?: string;
        };

        setLive((previous) =>
          previous
            ? {
                ...previous,
                status: payload.status || previous.status,
                progress_pct:
                  payload.progress_pct ?? previous.progress_pct,
                message: payload.message ?? previous.message,
                observation_count:
                  payload.observation_count ??
                  previous.observation_count,
                finding_count:
                  payload.finding_count ?? previous.finding_count,
                connector_runs:
                  payload.connector_runs ||
                  previous.connector_runs,
                meta: payload.meta ?? previous.meta,
              }
            : previous
        );

        if (event === "done") {
          setSseNote("Scan finished.");
        }
      },
      onError: (error) => setSseNote(error.message),
    });

    return stop;
  }, [live?.id, live?.status]);

  const grantAmberConsent = async () => {
    if (!requiredPurpose) return;

    await grantConsent.mutateAsync({
      purpose: requiredPurpose,
      scope: layerScope,
      details: {
        source: "scan_layer_control",
        layer: layerScope,
      },
    });

    setMessage(`Consent granted for ${layerScope} discovery.`);
  };

  const startScan = async () => {
    setMessage(null);

    if (!selectedIdentifier) {
      setMessage("Select a verified identifier.");
      return;
    }

    if (!selectedHasConsent) {
      setMessage(
        `Grant explicit consent for ${layerScope} before starting this scan.`
      );
      return;
    }

    try {
      const scan = await create.mutateAsync({
        identifier_id: selectedIdentifier,
        layer_scope: layerScope,
      });

      setLive(scan);
      setSseNote("SSE connected.");
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold">Scans</h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">
          Start with Surface discovery. Deep and Constrained-Dark scans are
          optional Amber layers requiring explicit consent and provide
          metadata-only, best-effort coverage.
        </p>
      </header>

      <Card className="glass-panel gradient-border">
        <CardHeader>
          <CardTitle>Choose discovery layer</CardTitle>
          <CardDescription>
            Amber scans never perform unrestricted crawling or direct onion access.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-5">
          <LayerScopeControl
            value={layerScope}
            onChange={setLayerScope}
            hasConsent={hasConsent}
          />

          {layerScope !== "surface" && !selectedHasConsent && (
            <div className="flex flex-col gap-3 rounded-lg border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100 md:flex-row md:items-center md:justify-between">
              <div className="flex gap-2">
                <LockKeyhole className="h-5 w-5 shrink-0" />
                <span>
                  This layer requires explicit consent for{" "}
                  <code>{requiredPurpose}</code>.
                </span>
              </div>

              <Button
                variant="secondary"
                onClick={grantAmberConsent}
                disabled={grantConsent.isPending}
              >
                Grant consent
              </Button>
            </div>
          )}

          <div className="grid gap-3 md:grid-cols-[1fr_auto]">
            <select
              aria-label="Verified identifier"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={selectedIdentifier}
              onChange={(event) =>
                setSelectedIdentifier(event.target.value)
              }
            >
              <option value="">
                Select verified identifier…
              </option>

              {verified.map((identifier) => (
                <option key={identifier.id} value={identifier.id}>
                  {identifier.type}: {identifier.value_display}
                </option>
              ))}
            </select>

            <Button
              onClick={startScan}
              disabled={
                !selectedIdentifier ||
                !selectedHasConsent ||
                create.isPending
              }
            >
              {create.isPending ? "Queueing…" : "Start scan"}
            </Button>
          </div>

          {message && (
            <p className="text-sm text-amber-200" role="status">
              {message}
            </p>
          )}

          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <ShieldCheck className="h-4 w-4 text-emerald-300" />
              Verified-only
            </span>
            <span className="inline-flex items-center gap-1">
              <LockKeyhole className="h-4 w-4 text-cyan-300" />
              Consent logged
            </span>
            <span className="inline-flex items-center gap-1">
              <AlertTriangle className="h-4 w-4 text-amber-300" />
              Amber results may be historical or incomplete
            </span>
          </div>
        </CardContent>
      </Card>

      {live && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Live scan
              <Badge variant="outline">{live.status}</Badge>
              <Badge variant="secondary">{live.layer_scope}</Badge>
            </CardTitle>
            <CardDescription>
              {live.message || "—"}
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-3">
            <Progress value={live.progress_pct || 0} />

            <div className="text-sm text-muted-foreground">
              {live.progress_pct?.toFixed?.(0) ?? live.progress_pct}% ·
              observations {live.observation_count} · findings{" "}
              {live.finding_count}
            </div>

            <ul className="space-y-1 text-sm">
              {(live.connector_runs || []).map((run) => (
                <li
                  key={run.connector_id}
                  className="flex justify-between rounded border px-2 py-1"
                >
                  <span>{run.connector_id}</span>
                  <span className="text-muted-foreground">
                    {run.status}
                    {run.skip_reason
                      ? ` (${run.skip_reason})`
                      : ""}
                    {run.cache_hit ? " · cache" : ""}
                  </span>
                </li>
              ))}
            </ul>

            {sseNote && (
              <p className="text-xs text-muted-foreground" role="status">
                {sseNote}
              </p>
            )}

            {!TERMINAL_STATUSES.includes(live.status) && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => cancel.mutate(live.id)}
              >
                Cancel
              </Button>
            )}

            <Button asChild size="sm" variant="secondary">
              <Link to={`/app/scans/${live.id}`}>
                Open detail
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="space-y-2">
        <h2 className="text-lg font-medium">History</h2>

        {(scans.data || []).map((scan) => (
          <Link
            key={scan.id}
            to={`/app/scans/${scan.id}`}
            className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm hover:bg-accent/40"
          >
            <span>
              <Badge variant="outline" className="mr-2">
                {scan.layer_scope}
              </Badge>
              <Badge variant="secondary" className="mr-2">
                {scan.status}
              </Badge>
              {scan.finding_count} findings
            </span>

            <span className="text-muted-foreground">
              {formatDate(scan.created_at)}
            </span>
          </Link>
        ))}

        {!scans.isLoading && !(scans.data || []).length && (
          <p className="text-sm text-muted-foreground">
            No scans yet.
          </p>
        )}
      </div>
    </div>
  );
}
```

---

## 22. UPDATE: `frontend/src/features/findings/FindingsPage.tsx`

Add the layer badge inside each finding card:

```tsx
<Badge variant="outline">{f.layer}</Badge>
```

Add this note below the page description:

```tsx
<p className="text-xs text-muted-foreground">
  Deep and Constrained-Dark findings are metadata-only and may be historical,
  incomplete, or unable to prove current exposure.
</p>
```

Recommended heading block:

```tsx
<div>
  <h1 className="text-2xl font-semibold">Findings</h1>
  <p className="text-muted-foreground">
    Normalized findings across Surface, Deep, and carefully constrained Amber layers.
  </p>
  <p className="text-xs text-muted-foreground">
    Deep and Constrained-Dark findings are metadata-only and may be historical,
    incomplete, or unable to prove current exposure.
  </p>
</div>
```

---

## 23. UPDATE: `frontend/src/features/scans/ScanDetailPage.tsx`

Add layer display beside the scan status:

```tsx
<CardTitle className="flex flex-wrap gap-2">
  <Badge>{scan.status}</Badge>
  <Badge variant="secondary">{scan.layer_scope}</Badge>
  <span className="text-base font-normal text-muted-foreground">
    {scan.id}
  </span>
</CardTitle>
```

Add this warning below the scan message:

```tsx
{scan.layer_scope !== "surface" && (
  <div className="rounded-md border border-amber-400/20 bg-amber-400/5 p-3 text-xs text-amber-100">
    Amber limitation: this scan uses historical, indexed, or configured
    public-index metadata. It does not prove current exposure and does not
    retrieve raw dump content.
  </div>
)}
```

---

# PART O — Tests

Sprint 11 tests are security and contract gates, not optional examples. In addition to connector parsing tests, prove the absence of outbound requests when policy denies dispatch.

Required invariants:

- unverified identifier → zero Amber outbound requests;
- missing consent → zero Amber outbound requests;
- revoked consent → zero Amber outbound requests;
- disabled Deep feature → zero Deep outbound requests;
- disabled constrained-dark feature → zero constrained-dark outbound requests;
- blank constrained-dark endpoint → zero outbound requests even when feature flag is true;
- host not in allowlist → zero outbound requests;
- newly configured destination without destination-aware authorization → zero outbound requests;
- all allowed requests pass through `EgressFetcher`;
- no connector creates a direct HTTP client;
- Wayback availability alone does not become confirmed sensitive exposure;
- generic username string matches cannot become confirmed exposure without linkage evidence;
- layer alone does not increase severity or PDSS;
- Common Crawl provenance records the selected collection;
- Surface remains the default and Sprint 0–10 behavior regresses neither functionally nor contractually.



## 24. NEW: `backend/tests/unit/test_amber_layers.py`

```python
import pytest

from app.domain.amber_layers import (
    AmberPolicyError,
    ExposureLayer,
    consent_purpose_for_layer,
    layer_matches_connector,
    validate_layer_scope,
)


def test_surface_has_no_extra_consent():
    assert consent_purpose_for_layer(ExposureLayer.SURFACE) is None


def test_deep_requires_consent():
    assert (
        consent_purpose_for_layer(ExposureLayer.DEEP)
        == "discovery.deep"
    )


def test_constrained_dark_requires_consent():
    assert (
        consent_purpose_for_layer(ExposureLayer.CONSTRAINED_DARK)
        == "discovery.constrained_dark"
    )


def test_deep_disabled():
    with pytest.raises(AmberPolicyError):
        validate_layer_scope(
            "deep",
            feature_deep_amber=False,
            feature_constrained_dark=False,
        )


def test_constrained_dark_disabled():
    with pytest.raises(AmberPolicyError):
        validate_layer_scope(
            "constrained_dark",
            feature_deep_amber=True,
            feature_constrained_dark=False,
        )


def test_layer_matches_connector():
    assert layer_matches_connector("deep", "deep") is True
    assert layer_matches_connector("deep", "surface") is False
```

---

## 25. NEW: `backend/tests/unit/connectors/test_common_crawl.py`

```python
from app.connectors.impl.deep.common_crawl import (
    build_common_crawl_pattern,
    parse_cdx_json_lines,
)


def test_domain_pattern():
    assert build_common_crawl_pattern(
        "domain",
        "example.com",
    ) == "*.example.com/*"


def test_username_pattern():
    assert build_common_crawl_pattern(
        "username",
        "alice",
    ) == "*alice*"


def test_email_is_not_sent_to_archive_adapter():
    try:
        build_common_crawl_pattern("email", "alice@example.com")
    except ValueError as exc:
        assert "unsupported" in str(exc).lower()
    else:
        raise AssertionError("Email should not be supported by Common Crawl adapter")


def test_parse_cdx_json_lines():
    body = (
        b'{"url":"https://example.com/a","status":"200"}\n'
        b'not-json\n'
        b'{"url":"https://example.com/b","status":"200"}\n'
    )

    rows = parse_cdx_json_lines(body, max_results=10)

    assert len(rows) == 2
    assert rows[0]["url"] == "https://example.com/a"
```

---

## 26. NEW: `backend/tests/unit/connectors/test_public_index_policy.py`

```python
import pytest

from app.connectors.impl.dark_constrained.public_index import (
    append_query,
    parse_public_index_payload,
    validate_public_index_endpoint,
)
from app.security.egress import EgressBlockedError


def test_public_index_requires_https():
    with pytest.raises(EgressBlockedError):
        validate_public_index_endpoint(
            "http://index.example/search",
            {"index.example"},
        )


def test_public_index_rejects_onion():
    with pytest.raises(EgressBlockedError):
        validate_public_index_endpoint(
            "https://example.onion/search",
            {"example.onion"},
        )


def test_public_index_requires_allowlist():
    with pytest.raises(EgressBlockedError):
        validate_public_index_endpoint(
            "https://index.example/search",
            set(),
        )


def test_public_index_allowlisted():
    host, endpoint = validate_public_index_endpoint(
        "https://index.example/search",
        {"index.example"},
    )

    assert host == "index.example"
    assert endpoint.startswith("https://")


def test_append_query():
    result = append_query(
        "https://index.example/search?format=json",
        "q",
        "alice",
    )

    assert "format=json" in result
    assert "q=alice" in result


def test_parse_public_index_payload():
    payload = {
        "results": [
            {"id": "1", "type": "metadata"},
            {"id": "2", "type": "metadata"},
        ]
    }

    rows = parse_public_index_payload(payload, max_results=10)

    assert len(rows) == 2
```

---

## 27. UPDATE: `backend/tests/unit/test_findings_normalize.py`

Add:

```python
def test_archived_metadata_is_possible_and_deep():
    from app.domain.findings_normalize import normalize_observation

    finding = normalize_observation(
        {
            "kind": "archived_metadata",
            "source": "common_crawl",
            "title": "Archived URL metadata match",
            "summary": "Historical URL index metadata",
            "confidence": 0.45,
            "layer": "deep",
            "raw_ref": "https://example.com/archive",
            "attributes": {
                "metadata_only": True,
                "current_exposure_unproven": True,
            },
        }
    )

    assert finding.layer == "deep"
    assert finding.track == "possible"
    assert finding.severity_hint == "info"


def test_public_index_signal_is_metadata_only():
    from app.domain.findings_normalize import normalize_observation

    finding = normalize_observation(
        {
            "kind": "public_index_signal",
            "source": "public_index",
            "title": "Configured public-index metadata match",
            "summary": "Metadata only",
            "confidence": 0.35,
            "layer": "constrained_dark",
            "attributes": {
                "metadata_only": True,
                "raw_content_retrieved": False,
            },
        }
    )

    assert finding.layer == "constrained_dark"
    assert finding.track == "possible"
    assert finding.attributes["metadata_only"] is True
```

---

# PART P — Documentation

## 28. NEW: `docs/runbooks/deep-constrained-dark.md`

```markdown
# Deep + Constrained-Dark Amber Runbook

## Purpose

Sprint 11 adds optional Amber discovery layers without changing the DigiZafe
modular-monolith architecture.

## Layers

| Layer | Default | Consent | Examples |
|---|---:|---:|---|
| surface | enabled | normal connector consent | XposedOrNot, crt.sh, RDAP, GitHub |
| deep | enabled | explicit `discovery.deep` | Common Crawl metadata, Wayback availability |
| constrained_dark | disabled | explicit `discovery.constrained_dark` | operator-approved public index metadata |

## Deep scan flow

1. User owns and verifies an identifier.
2. User opens the scan layer selector.
3. User selects `Deep`.
4. User grants `discovery.deep` consent.
5. User starts the scan.
6. Worker runs only Deep connectors.
7. Results are tagged `layer=deep`.
8. Findings are normalized as `archived_metadata`.
9. PDSS applies the Deep layer multiplier.
10. UI states that historical/index metadata does not prove current exposure.

## Constrained-Dark configuration

Constrained-Dark is disabled by default.

Required environment variables:

```bash
FEATURE_CONSTRAINED_DARK=true
AMBER_PUBLIC_INDEX_URL=https://approved.example/index
AMBER_PUBLIC_INDEX_HOST_ALLOWLIST=approved.example
```

The endpoint must:

- use HTTPS;
- return public JSON;
- require no credentials;
- be approved by the operator;
- not be a `.onion` service;
- not expose marketplace or credentialed access;
- return metadata rather than raw dump content.

## Prohibited behavior

DigiZafe must not:

- connect directly to Tor;
- crawl `.onion` sites;
- buy or download dumps;
- log into marketplaces;
- use leaked credentials;
- bypass CAPTCHAs;
- perform password resets;
- store raw HTML or raw leak rows indefinitely.

## Honest result language

Use:

- "metadata match";
- "historical capture available";
- "indexed URL observed";
- "current exposure unproven";
- "best-effort coverage";
- "source coverage may be incomplete".

Do not use:

- "confirmed dark-web exposure";
- "your data is currently for sale";
- "your account was compromised" unless a verified connector supports that claim;
- "removed" unless a remediation verification loop says so.
```

---

## 29. NEW: `docs/adr/0015-amber-layer-gating.md`

```markdown
# ADR 0015 — Deep and Constrained-Dark Amber Layer Gating

## Status

Accepted — Sprint 11

## Context

DigiZafe must expand beyond Surface discovery while preserving:

- self-only ownership verification;
- free-first operation;
- explicit provenance;
- no unrestricted dark-web crawling;
- no raw dumps;
- no paid hard dependency;
- honest limitations.

## Decision

Amber discovery is implemented as a layer-scoped scan:

- `surface`
- `deep`
- `constrained_dark`

Each Amber layer:

1. Requires explicit user consent.
2. Uses only connectors whose declared capability matches the scan layer.
3. Runs through the existing Connector SDK.
4. Uses `EgressFetcher` for all external HTTP.
5. Uses cache and rate limits.
6. Persists metadata-only observations.
7. Preserves source attribution.
8. Marks findings as `possible` unless stronger evidence exists.
9. Exposes limitations in API and frontend copy.

## Deep connectors

- Common Crawl URL-index metadata.
- Internet Archive Wayback availability metadata.

## Constrained-Dark connector

A configurable operator-approved public JSON index adapter is included but
disabled by default. It requires an HTTPS endpoint and explicit host allowlist.

## Rejected

- Direct Tor access.
- `.onion` crawling.
- Credentialed marketplaces.
- Raw dump retrieval.
- Unrestricted third-party search.
- Paid threat feeds as a core dependency.

## Consequences

Amber coverage is narrower than commercial threat intelligence products, but
the behavior is safer, explainable, free-first, and aligned with the frozen
DigiZafe architecture.
```

---

## 30. NEW: `docs/ethics/amber-layer-policy.md`

```markdown
# Ethics Policy — Amber Discovery

## User autonomy

Amber scans are never silently enabled. The user must see:

- the layer name;
- the destination purpose;
- the type of data sent;
- the limitations;
- the fact that results may be historical or incomplete.

## Data minimization

DigiZafe stores:

- source;
- layer;
- timestamp;
- redacted metadata;
- stable reference;
- attribution;
- confidence.

DigiZafe does not require or retain:

- full breach dumps;
- full archived page bodies;
- illicit marketplace content;
- credential material;
- raw HTML indefinitely.

## Self-only safety

Every Amber scan requires:

- authenticated user;
- verified identifier;
- user-scoped RLS;
- explicit Amber consent;
- audit event;
- egress ledger entry.

## Constrained-Dark boundary

Constrained-Dark is limited to an operator-approved public index over HTTPS.
It is not a Tor client and is not a marketplace crawler.

## Uncertainty language

Amber findings should be described as:

- historical;
- indexed;
- possible;
- metadata-only;
- requiring confirmation.

They should not be presented as definitive proof of current criminal exposure.
```

---

## 31. UPDATE: `docs/free-sources.md`

Append:

```markdown
## Sprint 11 Amber Sources

### Common Crawl

- Public URL-index metadata adapter.
- Deep Amber only.
- No archived page body retrieval.
- Cache + Redis rate limiting required.
- Results are historical/index metadata and do not prove current exposure.
- Attribution: Common Crawl public index.

### Internet Archive Wayback

- Availability metadata adapter for verified domains.
- Deep Amber only.
- No archived page body retention.
- Historical captures do not prove current exposure.
- Attribution: Internet Archive Wayback Machine.

### Configured Public Index

- Constrained-Dark adapter is disabled by default.
- Requires `FEATURE_CONSTRAINED_DARK=true`.
- Requires `AMBER_PUBLIC_INDEX_URL`.
- Requires `AMBER_PUBLIC_INDEX_HOST_ALLOWLIST`.
- HTTPS only.
- No `.onion`, Tor, marketplace, credentialed, or raw dump access.
- Metadata-only JSON responses.
```

---

## 32. UPDATE: `docs/model-cards/pdss-v1.md`

Append:

```markdown
## Sprint 11 Layer Handling

PDSS preserves the finding layer:

- `surface`
- `deep`
- `constrained_dark`

The catalog applies layer multipliers:

- Surface: `1.00`
- Deep: `1.08`
- Constrained-Dark: `1.15`

Amber findings are normally placed on the Possible track because:

- archived metadata may be stale;
- URL-index presence does not prove page content;
- a public-index result does not prove current exposure;
- connector coverage is incomplete.

Amber findings must preserve:

- source;
- layer;
- attribution;
- metadata-only status;
- current-exposure uncertainty.

The score must not describe historical or indexed metadata as a confirmed
current breach without an independent confirmed finding.
```

---

# PART Q — API Quick Reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/layers` | List Surface, Deep, and Constrained-Dark layer policies |
| POST | `/api/v1/privacy/consent` | Grant `discovery.deep` or `discovery.constrained_dark` |
| POST | `/api/v1/privacy/consent/revoke` | Revoke Amber consent |
| POST | `/api/v1/scans` | Start a layer-scoped scan |
| GET | `/api/v1/scans/{id}` | View scan status and layer |
| GET | `/api/v1/scans/{id}/events` | Stream scan progress |
| GET | `/api/v1/findings` | View layer-tagged findings |
| GET | `/api/v1/connectors` | View connector capabilities and legality |
| POST | `/api/v1/scores/compute` | Compute PDSS with layer multipliers |
| GET | `/api/v1/privacy/egress` | Review Amber destination ledger |

Example Deep consent:

```bash
curl -s -X POST http://localhost:8000/api/v1/privacy/consent \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
    "purpose": "discovery.deep",
    "scope": "deep",
    "details": {
      "layer": "deep",
      "reason": "User requested historical/index metadata discovery"
    }
  } | jq .
```

Example Deep scan:

```bash
curl -s -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d "{
    \"identifier_id\": \"$DOMAIN_ID\",
    \"layer_scope\": \"deep\"
  }" | jq .
```

Example Constrained-Dark configuration:

```bash
FEATURE_CONSTRAINED_DARK=true
AMBER_PUBLIC_INDEX_URL=https://approved.example/public-index
AMBER_PUBLIC_INDEX_HOST_ALLOWLIST=approved.example
```

Example Constrained-Dark consent:

```bash
curl -s -X POST http://localhost:8000/api/v1/privacy/consent \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
    "purpose": "discovery.constrained_dark",
    "scope": "constrained_dark",
    "details": {
      "layer": "constrained_dark",
      "metadata_only": true,
      "no_onion_access": true
    }
  }' | jq .
```

---

# PART R — Validation

## 1. Backend unit tests

```bash
docker compose exec api pytest \
  backend/tests/unit/test_amber_layers.py \
  backend/tests/unit/connectors/test_common_crawl.py \
  backend/tests/unit/connectors/test_public_index_policy.py \
  backend/tests/unit/test_findings_normalize.py \
  -v
```

## 2. Backend lint

```bash
docker compose exec api ruff check backend
docker compose exec api ruff format --check backend
```

## 3. Frontend build

```bash
cd frontend
npm run build
cd ..
```

## 4. Surface regression test

```bash
# Surface remains the default
curl -s -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d "{\"identifier_id\":\"$VERIFIED_EMAIL_ID\"}" | jq .
```

Expected:

```text
layer_scope = surface
```

## 5. Deep scan test

Use a verified domain identifier:

```bash
curl -s -X POST http://localhost:8000/api/v1/privacy/consent \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"purpose":"discovery.deep","scope":"deep"}' | jq .

curl -s -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d "{\"identifier_id\":\"$VERIFIED_DOMAIN_ID\",\"layer_scope\":\"deep\"}" | jq .
```

Verify:

- scan is queued;
- only Deep connectors run;
- findings have `layer=deep`;
- egress ledger contains `index.commoncrawl.org` and/or `archive.org`;
- attribution is preserved;
- no archived page body is stored.

## 6. Consent denial test

```bash
curl -s -X POST http://localhost:8000/api/v1/privacy/consent/revoke \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"purpose":"discovery.deep"}' | jq .

curl -s -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d "{\"identifier_id\":\"$VERIFIED_DOMAIN_ID\",\"layer_scope\":\"deep\"}" | jq .
```

Expected:

```text
HTTP 428
code = AMBER_CONSENT_REQUIRED
```

## 7. Constrained-Dark policy test

With no endpoint configured:

```bash
FEATURE_CONSTRAINED_DARK=true
AMBER_PUBLIC_INDEX_URL=
```

Expected:

```text
No external request is made.
Connector result is skipped with not_configured.
```

With a non-allowlisted endpoint:

```bash
AMBER_PUBLIC_INDEX_URL=https://unapproved.example/index
AMBER_PUBLIC_INDEX_HOST_ALLOWLIST=approved.example
```

Expected:

```text
Connector result is skipped with amber_policy_blocked.
```

With a `.onion` endpoint:

```bash
AMBER_PUBLIC_INDEX_URL=https://example.onion/index
AMBER_PUBLIC_INDEX_HOST_ALLOWLIST=example.onion
```

Expected:

```text
Direct .onion access is rejected.
```

---

# PART S — Definition of Done

- [ ] Sprint 10 remains green.
- [ ] `GET /api/v1/layers` returns all three layer definitions.
- [ ] Surface remains the default scan layer.
- [ ] Deep scans require `discovery.deep` consent.
- [ ] Constrained-Dark scans require `discovery.constrained_dark` consent.
- [ ] Amber consent is never silently auto-granted.
- [ ] Common Crawl connector is implemented.
- [ ] Common Crawl uses index metadata only.
- [ ] Common Crawl results are cached and rate-limited.
- [ ] Wayback availability connector is implemented.
- [ ] Wayback results are cached and rate-limited.
- [ ] Constrained-Dark public index connector is disabled by default.
- [ ] Constrained-Dark requires an HTTPS endpoint.
- [ ] Constrained-Dark requires an explicit host allowlist.
- [ ] `.onion` endpoints are rejected.
- [ ] Direct IP endpoints are rejected.
- [ ] No direct Tor networking exists.
- [ ] No marketplace or credentialed access exists.
- [ ] No raw dump retrieval exists.
- [ ] No raw archive page body is stored.
- [ ] All outbound HTTP uses `EgressFetcher`.
- [ ] Amber connector legality is declared as `amber`.
- [ ] Connector selection is layer-aware.
- [ ] Worker re-checks Amber consent before execution.
- [ ] Scan status exposes the selected layer.
- [ ] Findings preserve `surface`, `deep`, or `constrained_dark`.
- [ ] Archived metadata findings are placed on the Possible track.
- [ ] PDSS applies layer multipliers.
- [ ] XposedOrNot attribution remains unchanged.
- [ ] Egress ledger records Amber destinations.
- [ ] Frontend provides layer selector.
- [ ] Frontend explains Amber limitations.
- [ ] Frontend provides explicit consent action.
- [ ] Findings display layer badges.
- [ ] Scan detail displays layer warnings.
- [ ] Unit tests pass.
- [ ] Frontend production build passes.
- [ ] No paid API key is required.
- [ ] No `localStorage` or `sessionStorage` is introduced.
- [ ] No frozen architecture document is modified.

---


## Additional mandatory acceptance gates

- [ ] Existing Sprint 0–10 layer/consent/connector abstractions were searched before new abstractions were created.
- [ ] No duplicate canonical `ExposureLayer`, consent-purpose, or connector-policy source of truth exists.
- [ ] Generic username searching is disabled by default for archive-index connectors.
- [ ] Any future username result defaults to candidate/possible evidence until independently linked.
- [ ] Common Crawl collection selection is deterministic, cached, and recorded in provenance.
- [ ] Wayback snapshot availability alone is not treated as confirmed sensitive exposure.
- [ ] Layer labels do not directly increase severity or PDSS.
- [ ] Every Amber outbound request uses the existing `EgressFetcher`.
- [ ] No Amber connector instantiates a direct HTTP client.
- [ ] Consent/egress authorization is destination-aware where identifier disclosure occurs.
- [ ] A newly configured constrained-dark host is not authorized by an unrelated historical layer grant.
- [ ] Blank constrained-dark endpoint is fail-closed even if the feature flag is enabled.
- [ ] Unverified identifier, missing/revoked consent, disabled feature, blank endpoint, and unapproved host each produce zero outbound requests.
- [ ] Surface remains the default scan layer and all Sprint 0–10 regression tests remain green.

---

# PART T — File Checklist

## New files

```text
shared/config/amber_sources.json

backend/app/domain/amber_layers.py

backend/app/connectors/impl/deep/__init__.py
backend/app/connectors/impl/deep/common_crawl.py
backend/app/connectors/impl/deep/wayback.py

backend/app/connectors/impl/dark_constrained/__init__.py
backend/app/connectors/impl/dark_constrained/public_index.py

backend/app/api/v1/layers.py

frontend/src/features/scans/layers-api.ts
frontend/src/features/scans/LayerScopeControl.tsx

backend/tests/unit/test_amber_layers.py
backend/tests/unit/connectors/test_common_crawl.py
backend/tests/unit/connectors/test_public_index_policy.py

docs/runbooks/deep-constrained-dark.md
docs/adr/0015-amber-layer-gating.md
docs/ethics/amber-layer-policy.md
```

- `backend/tests/security/test_amber_verified_only.py`
- `backend/tests/security/test_amber_consent_egress.py`
- `backend/tests/security/test_constrained_dark_fail_closed.py`
- `backend/tests/unit/connectors/test_wayback_evidence_semantics.py`
- `backend/tests/unit/test_layer_not_severity.py`
- `backend/tests/contract/test_amber_scan_contract.py`

## Updated files

```text
.env.example
backend/app/core/config.py
backend/app/connectors/sdk/types.py
backend/app/connectors/sdk/base.py
backend/app/connectors/registry.py
backend/app/domain/findings_normalize.py
shared/score_model/pdss_catalog.json
backend/app/schemas/scan.py
backend/app/services/discovery_service.py
backend/app/main.py
frontend/src/lib/types.ts
frontend/src/features/scans/api.ts
frontend/src/features/scans/ScansPage.tsx
frontend/src/features/scans/ScanDetailPage.tsx
frontend/src/features/findings/FindingsPage.tsx
backend/tests/unit/test_findings_normalize.py
docs/free-sources.md
docs/model-cards/pdss-v1.md
```

## Migration

```text
No new Alembic migration required.
```

---

# PART U — Commit

From the repository root:

```bash
git add .
git commit -m "feat(sprint-11): deep and constrained-dark free Amber discovery with consent gates, archive metadata, layer-aware findings, and honest UX"
```

---

# Sprint 11 Completion Statement

Sprint 11 is complete when DigiZafe supports:

```text
Verified identifier
→ Surface scan by default
→ Optional explicit Deep consent
→ Common Crawl / Wayback metadata scan
→ Optional operator-configured Constrained-Dark consent
→ Layer-aware observations
→ Layer-aware findings
→ Explainable PDSS multiplier
→ Honest historical/index limitations
→ Full egress and attribution records
```

The approved operating boundary remains:

```text
No direct Tor
No onion crawling
No marketplace access
No credentials
No raw dumps
No unrestricted scraping
No paid hard dependency
```

Next sprint:

```text
Sprint 12 — Optional Free Residual ML
```