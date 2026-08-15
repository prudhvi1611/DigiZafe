from __future__ import annotations

from app.domain.exposure_layers import ExposureLayer

"""Operator-approved public index adapter for Constrained-Dark Amber.

This is not a Tor client and does not crawl onion services.
The endpoint must be configured by the operator and allowlisted explicitly.
"""


import ipaddress
import json
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.connectors.sdk.base import Connector
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
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
            layer=ExposureLayer.CONSTRAINED_DARK,
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
                    "layer": ExposureLayer.CONSTRAINED_DARK.value,
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
                    layer=ExposureLayer.CONSTRAINED_DARK,
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
                "layer": ExposureLayer.CONSTRAINED_DARK.value,
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
            layer=ExposureLayer(
                value.get(
                    "layer",
                    ExposureLayer.CONSTRAINED_DARK.value,
                )
            ),
            raw_ref=value.get("raw_ref"),
            attributes=value.get("attributes") or {},
            attribution=value.get("attribution"),
        )
