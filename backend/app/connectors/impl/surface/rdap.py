from __future__ import annotations

from app.domain.exposure_layers import ExposureLayer

"""RDAP / public DNS-ish domain registration lookup (free)."""


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


class RdapConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="rdap",
            name="RDAP",
            layer=ExposureLayer.SURFACE,
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
                observed_at=datetime.now(UTC),
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
