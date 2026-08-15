from datetime import datetime, timedelta, timezone
from enum import Enum

from app.core.config import get_settings


class FreshnessState(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"
    UNKNOWN = "unknown"
    SUPERSEDED = "superseded"


class EvidenceFreshnessService:
    """Service to determine if an observation is fresh, stale, or expired."""

    # Default TTLs before observation becomes STALE
    _stale_ttls_days = {
        "profile_existence": 30,
        "username": 30,
        "display_name": 14,
        "bio": 7,
        "external_link": 7,
        "avatar_observation": 14,
        "cross_link": 14,
        "relationship_context": 7,
    }

    @classmethod
    def get_stale_ttl_days(cls, observation_type: str) -> int:
        return cls._stale_ttls_days.get(observation_type, 30)

    @classmethod
    def get_expire_ttl_days(cls, observation_type: str) -> int:
        # Expiry is set to 2x the stale TTL as a reasonable operational policy
        return cls.get_stale_ttl_days(observation_type) * 2

    @classmethod
    def calculate_stale_after(cls, valid_from: datetime, observation_type: str) -> datetime:
        return valid_from + timedelta(days=cls.get_stale_ttl_days(observation_type))

    @classmethod
    def calculate_expires_at(cls, valid_from: datetime, observation_type: str) -> datetime:
        return valid_from + timedelta(days=cls.get_expire_ttl_days(observation_type))

    @classmethod
    def evaluate(cls, valid_from: datetime, observation_type: str, now: datetime | None = None) -> FreshnessState:
        if now is None:
            now = datetime.now(timezone.utc)
            
        stale_after = cls.calculate_stale_after(valid_from, observation_type)
        expires_at = cls.calculate_expires_at(valid_from, observation_type)
        
        if now > expires_at:
            return FreshnessState.EXPIRED
        if now > stale_after:
            return FreshnessState.STALE
            
        return FreshnessState.FRESH
