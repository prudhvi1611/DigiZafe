from __future__ import annotations

from app.domain.exposure_layers import ExposureLayer

"""Internet Archive Wayback availability metadata adapter."""


import json
from datetime import UTC, datetime
from typing import Any
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


class WaybackConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="wayback",
            name="Internet Archive Wayback Availability",
            layer=ExposureLayer.DEEP,
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
            observed_at = datetime.now(UTC)

            if timestamp:
                try:
                    observed_at = datetime.strptime(
                        str(timestamp),
                        "%Y%m%d%H%M%S",
                    ).replace(tzinfo=UTC)
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
                    layer=ExposureLayer.DEEP,
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
            layer=ExposureLayer(
                value.get("layer", ExposureLayer.DEEP.value)
            ),
            raw_ref=value.get("raw_ref"),
            attributes=value.get("attributes") or {},
            attribution=value.get("attribution"),
        )
