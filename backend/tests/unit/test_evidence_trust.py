import pytest
from app.services.discovery.evidence_trust_policy import EvidenceTrustPolicy, EvidenceTrustClass

def test_evidence_trust_policy():
    # If connector is verified and available
    assert EvidenceTrustPolicy.evaluate("available") == EvidenceTrustClass.LIVE_CERTIFIED
    
    # If connector is installed but unverified
    assert EvidenceTrustPolicy.evaluate("installed_unverified") == EvidenceTrustClass.LIVE_UNCERTIFIED
    
    # If disabled
    assert EvidenceTrustPolicy.evaluate("disabled") == EvidenceTrustClass.TEST_ONLY
    
    # If test_only
    assert EvidenceTrustPolicy.evaluate("test_only") == EvidenceTrustClass.TEST_ONLY
    
    # If no certification
    assert EvidenceTrustPolicy.evaluate(None) == EvidenceTrustClass.TEST_ONLY
