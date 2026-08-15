"""Connector ABC + registry helpers."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.connectors.sdk.cache import ConnectorCache
from app.connectors.sdk.rate_limiter import RateLimiter, RateLimitExceeded
from app.connectors.sdk.types import (
    ConnectorCapability,
    ConnectorContext,
    ConnectorResult,
    LegalityTier,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.security.egress import EgressFetcher


class Connector(ABC):
    """
    Rules (MASTER):
    - Never touch DB
    - Never raw HTTP — only injected EgressFetcher
    - Always RateLimiter + Cache for free APIs
    - Declare Green/Amber/Red; Red must not run
    - If sends_identifier: caller must ensure consent; connector may re-check purpose string
    """

    def __init__(
        self,
        *,
        egress: EgressFetcher,
        rate_limiter: RateLimiter,
        cache: ConnectorCache,
        logger_name: str | None = None,
    ) -> None:
        self.egress = egress
        self.rate_limiter = rate_limiter
        self.cache = cache
        self.settings = get_settings()
        self.log = get_logger(logger_name or self.capability.id)

    @property
    @abstractmethod
    def capability(self) -> ConnectorCapability:
        ...

    @abstractmethod
    async def _run(self, ctx: ConnectorContext) -> ConnectorResult:
        """Implement actual work (after rate limit + type checks)."""

    def supports(self, identifier_type: str) -> bool:
        return identifier_type in self.capability.supported_identifier_types

    def is_enabled_by_config(self) -> bool:
        """Environment-level feature flag. DB toggle is applied by the registry service."""
        cid = self.capability.id

        mapping = {
            "xposedornot": self.settings.feature_xposedornot,
            "pwned_passwords": self.settings.feature_pwned_passwords,
            "crtsh": self.settings.feature_crtsh,
            "rdap": self.settings.feature_rdap,
            "github": self.settings.feature_github_connector,
            "gravatar": self.settings.feature_gravatar,
            "username_presence": self.settings.feature_username_presence,
            "serp_ddg": self.settings.feature_serp_ddg,

            # Sprint 11 Amber
            "common_crawl": (
                self.settings.feature_deep_amber
                and self.settings.common_crawl_enabled
            ),
            "wayback": (
                self.settings.feature_deep_amber
                and self.settings.wayback_enabled
            ),
            "public_index": self.settings.feature_constrained_dark,
        }

        return bool(mapping.get(cid, True))


    async def run(
        self,
        ctx: ConnectorContext,
        *,
        enabled_override: bool | None = None,
    ) -> ConnectorResult:
        cap = self.capability
        if cap.legality == LegalityTier.RED:
            return ConnectorResult(
                connector_id=cap.id,
                success=False,
                skipped=True,
                skip_reason="red_excluded",
            )

        enabled = self.is_enabled_by_config() if enabled_override is None else enabled_override
        if not enabled:
            return ConnectorResult(
                connector_id=cap.id,
                success=False,
                skipped=True,
                skip_reason="disabled",
            )

        if not self.supports(ctx.identifier_type):
            return ConnectorResult(
                connector_id=cap.id,
                success=False,
                skipped=True,
                skip_reason="unsupported_type",
            )

        if cap.requires_paid_key:
            return ConnectorResult(
                connector_id=cap.id,
                success=False,
                skipped=True,
                skip_reason="paid_key_required",
                error="Paid connectors are feature-flagged only and not load-bearing",
            )

        try:
            return await self._run(ctx)
        except RateLimitExceeded as e:
            self.log.warning("connector_rate_limited", connector=cap.id, key=e.key)
            return ConnectorResult(
                connector_id=cap.id,
                success=False,
                skipped=True,
                skip_reason="rate_limited",
                error=str(e),
                meta={"retry_after": e.retry_after},
            )
        except Exception as e:
            self.log.exception("connector_failed", connector=cap.id, error=str(e))
            return ConnectorResult(
                connector_id=cap.id,
                success=False,
                error=str(e),
            )
