from __future__ import annotations

from app.domain.exposure_layers import ExposureLayer

"""XposedOrNot — primary free breach source (keyless personal email checks)."""


import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from app.connectors.sdk.base import Connector
from app.connectors.sdk.rate_limiter import RateLimitExceeded
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorResult,
    LegalityTier,
    ObservationKind,
    RawObservation,
)
from app.security.egress import EgressError


class XposedOrNotConnector(Connector):
    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="xposedornot",
            name="XposedOrNot",
            layer=ExposureLayer.SURFACE,
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
                    observed_at=datetime.now(UTC),
                    layer=ExposureLayer.SURFACE,
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
            layer=ExposureLayer(d.get("layer", "surface")),
            raw_ref=d.get("raw_ref"),
            attributes=d.get("attributes") or {},
            attribution=d.get("attribution"),
        )
