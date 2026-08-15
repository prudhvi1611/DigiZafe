from enum import Enum
from pydantic import BaseModel

class ConnectorCapability(str, Enum):
    PROFILE_LOOKUP = "profile_lookup"
    PUBLIC_PROFILE_METADATA = "public_profile_metadata"
    EXTERNAL_LINKS = "external_links"
    AVATAR_OBSERVATION = "avatar_observation"
    RELATIONSHIP_OBSERVATION = "relationship_observation"

class CapabilityPolicy(BaseModel):
    enabled: bool
    requires_session: bool
    requires_explicit_consent: bool
    max_targets_per_run: int
    timeout: int
    output_limit: int

class CapabilityRegistry:
    # OSINTgram specific policies for Sprint 19
    _osintgram_policies = {
        ConnectorCapability.PROFILE_LOOKUP: CapabilityPolicy(
            enabled=True,
            requires_session=True,
            requires_explicit_consent=True,
            max_targets_per_run=10,
            timeout=30,
            output_limit=1024 * 1024
        ),
        ConnectorCapability.PUBLIC_PROFILE_METADATA: CapabilityPolicy(
            enabled=True,
            requires_session=True,
            requires_explicit_consent=True,
            max_targets_per_run=10,
            timeout=30,
            output_limit=1024 * 1024
        ),
        ConnectorCapability.EXTERNAL_LINKS: CapabilityPolicy(
            enabled=True,
            requires_session=True,
            requires_explicit_consent=True,
            max_targets_per_run=10,
            timeout=30,
            output_limit=1024 * 1024
        ),
        ConnectorCapability.AVATAR_OBSERVATION: CapabilityPolicy(
            enabled=True,
            requires_session=True,
            requires_explicit_consent=True,
            max_targets_per_run=10,
            timeout=30,
            output_limit=1024 * 1024
        ),
        ConnectorCapability.RELATIONSHIP_OBSERVATION: CapabilityPolicy(
            enabled=False,
            requires_session=True,
            requires_explicit_consent=True,
            max_targets_per_run=0,
            timeout=0,
            output_limit=0
        )
    }

    @classmethod
    def get_policy(cls, connector: str, capability: ConnectorCapability) -> CapabilityPolicy | None:
        if connector == "osintgram":
            return cls._osintgram_policies.get(capability)
        return None

    @classmethod
    def is_enabled(cls, connector: str, capability: ConnectorCapability) -> bool:
        policy = cls.get_policy(connector, capability)
        return policy is not None and policy.enabled
