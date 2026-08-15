from __future__ import annotations

from app.domain.exposure_layers import ExposureLayer

"""Curated ethical username presence — only a few public endpoints (Green)."""


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
            layer=ExposureLayer.SURFACE,
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
                        observed_at=datetime.now(UTC),
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
