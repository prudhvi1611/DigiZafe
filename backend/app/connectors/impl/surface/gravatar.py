from __future__ import annotations

from app.domain.exposure_layers import ExposureLayer

"""Gravatar existence check (public hash of email)."""


import hashlib
from datetime import UTC, datetime

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


class GravatarConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="gravatar",
            name="Gravatar",
            layer=ExposureLayer.SURFACE,
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
                    observed_at=datetime.now(UTC),
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
