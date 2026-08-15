from enum import Enum
import logging

logger = logging.getLogger(__name__)

class EvidenceTrustClass(str, Enum):
    TEST_ONLY = "test_only"
    LIVE_UNCERTIFIED = "live_uncertified"
    LIVE_CERTIFIED = "live_certified"
    USER_CONFIRMED = "user_confirmed"

class EvidenceTrustPolicy:
    """
    Evaluates the trust level of connector evidence.
    """
    
    @staticmethod
    def evaluate(certification_availability: str | None) -> EvidenceTrustClass:
        """
        Evaluate trust class based on certification status at the time of execution.
        """
        if certification_availability == "available":
            return EvidenceTrustClass.LIVE_CERTIFIED
        elif certification_availability == "installed_unverified":
            return EvidenceTrustClass.LIVE_UNCERTIFIED
        else:
            # test_only, None, or anything else
            return EvidenceTrustClass.TEST_ONLY
