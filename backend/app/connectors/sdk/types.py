from __future__ import annotations

from app.domain.exposure_layers import ExposureLayer

"""Shared connector types (no I/O)."""


from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID


class LegalityTier(str, Enum):
    GREEN = "green"  # free, public, ToS-friendly, self-only consented
    AMBER = "amber"  # gated deep / extra consent
    RED = "red"  # excluded from MVP




class ObservationKind(str, Enum):
    BREACH = "breach"
    PASSWORD_EXPOSURE = "password_exposure"
    CERTIFICATE = "certificate"
    DNS_RDAP = "dns_rdap"
    PROFILE = "profile"
    USERNAME_PRESENCE = "username_presence"
    SERP = "serp"
    ARCHIVED_METADATA = "archived_metadata"
    PUBLIC_INDEX_SIGNAL = "public_index_signal"
    OTHER = "other"


@dataclass
class ConnectorCapability:
    id: str
    name: str
    layer: ExposureLayer
    legality: LegalityTier
    requires_paid_key: bool
    sends_identifier: bool  # if True → consent + egress ledger mandatory
    supported_identifier_types: list[str]
    attribution: str | None = None
    description: str = ""


@dataclass
class ConnectorContext:
    """Injected runtime context — connectors never open their own clients/DB."""

    user_id: UUID
    identifier_id: UUID
    identifier_type: str
    identifier_canonical: str
    correlation_id: str | None = None
    consent_purpose: str | None = None  # e.g. discovery.xposedornot


@dataclass
class RawObservation:
    """Normalized unit returned by connectors (Sprint 4 maps → findings)."""

    kind: ObservationKind
    source: str  # connector id
    title: str
    summary: str
    confidence: float  # 0..1
    observed_at: datetime | None = None
    layer: ExposureLayer = ExposureLayer.SURFACE
    raw_ref: str | None = None  # non-PII handle / breach name
    attributes: dict[str, Any] = field(default_factory=dict)
    attribution: str | None = None
    # Never store full HTML dumps here long-term; Sprint 4 evidence layers handle TTL

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "confidence": self.confidence,
            "observed_at": (self.observed_at or datetime.now(UTC)).isoformat(),
            "layer": self.layer.value,
            "raw_ref": self.raw_ref,
            "attributes": self.attributes,
            "attribution": self.attribution,
        }


@dataclass
class ConnectorResult:
    connector_id: str
    success: bool
    observations: list[RawObservation] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None  # rate_limited | disabled | no_consent | unsupported_type | cache_only_error
    error: str | None = None
    cache_hit: bool = False
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "success": self.success,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "error": self.error,
            "cache_hit": self.cache_hit,
            "observation_count": len(self.observations),
            "observations": [o.to_dict() for o in self.observations],
            "meta": self.meta,
        }
