from __future__ import annotations

from app.domain.exposure_layers import ExposureLayer

"""HIBP Pwned Passwords — k-anonymous range API (free, no key)."""


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


class PwnedPasswordsConnector(Connector):
    """
    Note: identifier_type should be a special probe type or password hash prefix flow.
    For Sprint 3 we accept type 'password' where canonical is the plaintext password
    ONLY held in memory for hashing — never logged. Prefer caller passes sha1 already
    via attributes in later sprints; here we hash in-process and send only 5-char prefix.
    """

    @property
    def capability(self) -> ConnectorCapability:
        return ConnectorCapability(
            id="pwned_passwords",
            name="Pwned Passwords (HIBP k-anonymity)",
            layer=ExposureLayer.SURFACE,
            legality=LegalityTier.GREEN,
            requires_paid_key=False,
            sends_identifier=False,  # only 5-char hash prefix — k-anonymous
            supported_identifier_types=["password"],
            attribution="Pwned Passwords by Have I Been Pwned (k-anonymity range API)",
            description="Checks password exposure without sending full password/hash.",
        )

    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        # ctx.identifier_canonical is the password string for this probe only
        password = ctx.identifier_canonical
        sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]

        cache_key = self.cache.make_key("pwned_passwords", prefix)  # range cacheable
        # We still need suffix match — cache full range text
        cached_range = await self.cache.get_json(cache_key)

        if cached_range is None:
            await self.rate_limiter.acquire("pwned_passwords", per_second=5, per_hour=1000, per_day=10000)
            url = f"{self.settings.pwned_passwords_base_url.rstrip('/')}/range/{prefix}"
            try:
                resp = await self.egress.fetch(
                    url,
                    headers={"Add-Padding": "true", "User-Agent": "DigiZafe"},
                    purpose="discovery.pwned_passwords",
                )
            except EgressError as e:
                return ConnectorResult(connector_id=self.capability.id, success=False, error=str(e))

            if resp.status_code != 200:
                return ConnectorResult(
                    connector_id=self.capability.id,
                    success=False,
                    error=f"HTTP {resp.status_code}",
                )
            text = resp.body.decode("utf-8", errors="replace")
            await self.cache.set_json(cache_key, {"range": text}, 3600)
        else:
            text = cached_range.get("range", "")
            return self._match(suffix, text, cache_hit=True)

        return self._match(suffix, text, cache_hit=False)

    def _match(self, suffix: str, range_text: str, cache_hit: bool) -> ConnectorResult:
        count = 0
        for line in range_text.splitlines():
            parts = line.strip().split(":")
            if len(parts) != 2:
                continue
            if parts[0].upper() == suffix.upper():
                try:
                    count = int(parts[1].strip())
                except ValueError:
                    count = 1
                break

        observations: list[RawObservation] = []
        if count > 0:
            observations.append(
                RawObservation(
                    kind=ObservationKind.PASSWORD_EXPOSURE,
                    source="pwned_passwords",
                    title="Password seen in breach corpus",
                    summary=f"This password appears approximately {count} times in Pwned Passwords.",
                    confidence=0.95,
                    observed_at=datetime.now(UTC),
                    attributes={"count": count, "k_anonymous": True},
                    attribution=self.capability.attribution,
                )
            )

        return ConnectorResult(
            connector_id=self.capability.id,
            success=True,
            observations=observations,
            cache_hit=cache_hit,
            meta={"pwned_count": count, "attribution": self.capability.attribution},
        )
