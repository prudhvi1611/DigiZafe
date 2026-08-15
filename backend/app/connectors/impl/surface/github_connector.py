from __future__ import annotations

from app.domain.exposure_layers import ExposureLayer

"""GitHub public profile / presence (free API; optional token)."""


import json
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


class GitHubConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="github",
            name="GitHub public profile",
            layer=ExposureLayer.SURFACE,
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
                observed_at=datetime.now(UTC),
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
