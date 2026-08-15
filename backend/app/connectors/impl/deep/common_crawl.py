from __future__ import annotations

from app.domain.exposure_layers import ExposureLayer

"""Common Crawl URL-index adapter for Deep Amber metadata discovery."""


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
            layer=ExposureLayer.DEEP,
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

        if not isinstance(data, list) or not data:
            return None
        first = data[0]
        if not isinstance(first, dict):
            return None

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
                    "layer": ExposureLayer.DEEP.value,
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
                    ).replace(tzinfo=UTC)
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
                    observed_at=observed_at or datetime.now(UTC),
                    layer=ExposureLayer.DEEP,
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
            layer=ExposureLayer(
                value.get("layer", ExposureLayer.DEEP.value)
            ),
            raw_ref=value.get("raw_ref"),
            attributes=value.get("attributes") or {},
            attribution=value.get("attribution"),
        )
