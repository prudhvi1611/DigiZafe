from app.domain.temporal_states import (
    MATERIALITY_LOW,
    MATERIALITY_MEDIUM,
    MATERIALITY_HIGH,
    MATERIALITY_CRITICAL_REVIEW,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_HIGH,
    PRIORITY_CRITICAL,
    FACT_APPEARED,
    FACT_VALUE_CHANGED,
    FACT_DISAPPEARED,
    FACT_ABSENCE_SUSPECTED,
    FACT_REAPPEARED,
    CONTRADICTION_ADDED,
    CONTRADICTION_RESOLVED,
)

class IdentityChangeMaterialityPolicy:
    """
    Evaluates the materiality and review priority of identity change events.
    """

    def __init__(self, policy_version: int = 1):
        self.policy_version = policy_version

    def evaluate(self, change_type: str, fact_key: str, is_confirmed_profile: bool = False, is_likely_match: bool = False) -> tuple[str, str]:
        """
        Returns (materiality, review_priority).
        """
        # Default fallback
        materiality = MATERIALITY_LOW
        priority = PRIORITY_LOW

        if change_type == CONTRADICTION_ADDED:
            if is_confirmed_profile:
                return MATERIALITY_CRITICAL_REVIEW, PRIORITY_CRITICAL
            if is_likely_match:
                return MATERIALITY_HIGH, PRIORITY_HIGH
            return MATERIALITY_MEDIUM, PRIORITY_MEDIUM

        if fact_key.startswith("avatar"):
            materiality, priority = MATERIALITY_LOW, PRIORITY_LOW
        elif fact_key.startswith("bio"):
            materiality, priority = MATERIALITY_LOW, PRIORITY_LOW
        elif fact_key.startswith("name") or fact_key.startswith("display_name"):
            materiality, priority = MATERIALITY_LOW, PRIORITY_LOW
        elif fact_key.startswith("username"):
            if is_confirmed_profile:
                materiality, priority = MATERIALITY_HIGH, PRIORITY_HIGH
            else:
                materiality, priority = MATERIALITY_MEDIUM, PRIORITY_MEDIUM
        elif fact_key.startswith("link"):
            if change_type == FACT_APPEARED:
                materiality, priority = MATERIALITY_MEDIUM, PRIORITY_MEDIUM
            elif change_type == FACT_DISAPPEARED:
                materiality, priority = MATERIALITY_MEDIUM, PRIORITY_MEDIUM
        
        # Confirmed profile disappearance is high materiality
        if change_type == FACT_DISAPPEARED and is_confirmed_profile and not fact_key.startswith("link"):
            materiality, priority = MATERIALITY_HIGH, PRIORITY_HIGH
            
        # Absence suspected does not warrant high priority immediately
        if change_type == FACT_ABSENCE_SUSPECTED:
            if is_confirmed_profile:
                priority = PRIORITY_MEDIUM
            else:
                priority = PRIORITY_LOW

        return materiality, priority
