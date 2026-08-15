from enum import Enum
from pydantic import BaseModel
from typing import Any

from app.core.config import get_settings
from app.services.discovery.connectors.capability_registry import ConnectorCapability

class ConnectorAvailability(str, Enum):
    AVAILABLE = "available"
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"
    TEST_ONLY = "test_only"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    UNAVAILABLE = "unavailable"

class ConnectorDescriptor(BaseModel):
    connector_type: str
    adapter_version: str
    runtime_version: str | None
    enabled: bool
    availability: ConnectorAvailability
    capabilities: list[ConnectorCapability]
    queue: str
    timeout: int
    cost_weight: int

class ConnectorRegistry:
    @classmethod
    def get_descriptor(cls, connector_type: str) -> ConnectorDescriptor | None:
        settings = get_settings()
        if connector_type == "osintgram":
            # For Sprint 20, OSINTgram runtime is mocked
            return ConnectorDescriptor(
                connector_type="osintgram",
                adapter_version="1.1.0-mock",
                runtime_version=None,
                enabled=settings.feature_osintgram_discovery,
                availability=ConnectorAvailability.TEST_ONLY if settings.feature_osintgram_discovery else ConnectorAvailability.DISABLED,
                capabilities=[
                    ConnectorCapability.PROFILE_LOOKUP,
                    ConnectorCapability.PUBLIC_PROFILE_METADATA,
                    ConnectorCapability.EXTERNAL_LINKS,
                    ConnectorCapability.AVATAR_OBSERVATION,
                ],
                queue="osint_connectors",
                timeout=30,
                cost_weight=2
            )
        elif connector_type == "maigret":
            # For Sprint 20, Maigret runtime is also mocked/test-only
            return ConnectorDescriptor(
                connector_type="maigret",
                adapter_version="0.4.4-adapter",
                runtime_version=None,
                enabled=settings.feature_maigret_discovery,
                availability=ConnectorAvailability.TEST_ONLY if settings.feature_maigret_discovery else ConnectorAvailability.DISABLED,
                capabilities=[
                    ConnectorCapability.PROFILE_LOOKUP,
                ],
                queue="discovery", # existing discovery queue
                timeout=60,
                cost_weight=1
            )
        return None

    @classmethod
    def get_all_connectors(cls) -> list[ConnectorDescriptor]:
        return [
            cls.get_descriptor("maigret"),
            cls.get_descriptor("osintgram")
        ]
