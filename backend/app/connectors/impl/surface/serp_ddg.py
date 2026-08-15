from __future__ import annotations

from app.domain.exposure_layers import ExposureLayer

"""DuckDuckGo HTML lite SERP adapter (free, fragile — honest about limits)."""


import re
from datetime import UTC, datetime
from urllib.parse import quote_plus

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


class SerpDdgConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="serp_ddg",
            name="DuckDuckGo HTML SERP",
            layer=ExposureLayer.SURFACE,
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
                observed_at=datetime.now(UTC),
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
