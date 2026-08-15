from __future__ import annotations

from app.domain.exposure_layers import ExposureLayer

"""crt.sh Certificate Transparency — free."""


import json
from datetime import UTC, datetime
from urllib.parse import quote

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorResult,
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
            layer=ExposureLayer.SURFACE,
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
                observed_at=datetime.now(UTC),
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
