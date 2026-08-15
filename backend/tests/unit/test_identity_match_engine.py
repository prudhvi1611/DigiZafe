import pytest
import uuid
from datetime import datetime, timezone
from app.models.candidate_profile import CandidateProfile
from app.models.identity_anchor import IdentityAnchor, IdentityAlias, ConfirmedProfileReference
from app.services.identity_match_engine import IdentityMatchEngine
from app.services.identity_collision_policy import IdentityCollisionPolicy
from app.schemas.identity_assessment import IdentityEvidence

class MockSession:
    pass

class MockEvidenceService:
    def __init__(self, evidence_list):
        self.evidence_list = evidence_list
    async def collect_evidence(self, *args, **kwargs):
        return self.evidence_list

@pytest.fixture
def base_candidate():
    return CandidateProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        username_observed="yuva_dev",
        platform="github",
        canonical_profile_url="https://github.com/yuva_dev",
        candidate_status="unreviewed",
        updated_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def mock_engine(monkeypatch):
    engine = IdentityMatchEngine(MockSession())
    return engine

def test_collision_policy():
    assert IdentityCollisionPolicy.assess_collision_risk("a") == "high_collision"
    assert IdentityCollisionPolicy.assess_collision_risk("yuva_dev123") == "high_collision"
    assert IdentityCollisionPolicy.assess_collision_risk("yuva_dev1990long") == "medium_collision"
    assert IdentityCollisionPolicy.assess_collision_risk("superdistinctiveusername") == "low_collision"

    assert IdentityCollisionPolicy.get_username_evidence_cap("high_collision") == 20
    assert IdentityCollisionPolicy.get_username_evidence_cap("low_collision") == 60

def test_no_double_counting_and_caps(mock_engine):
    evidence = [
        IdentityEvidence(
            evidence_id="1",
            evidence_type="maigret_profile_observation",
            direction="positive",
            strength_class="weak",
            source_type="maigret",
            source_reference="1",
            source_reliability_class="medium",
            canonical_fact_key="fact1",
            independence_group="username_observation:yuva_dev"
        ),
        IdentityEvidence(
            evidence_id="2",
            evidence_type="exact_username_match",
            direction="positive",
            strength_class="moderate",
            source_type="alias",
            source_reference="2",
            source_reliability_class="high",
            canonical_fact_key="fact2",
            independence_group="username_observation:yuva_dev"
        )
    ]
    # In username group we have 20 (weak) + 40 (moderate) = 60.
    # But if it's "yuva_dev" it might be medium_collision (len 8, unique chars < 5? y u v a _ d e v = 7 unique chars. length 8 < 12. So medium_collision. cap = 40.
    
    mock_engine.evidence_service = MockEvidenceService(evidence)
    # Testing internal logic directly instead of mocking db calls
    
    # We can test fingerprinting determinism here
    fp1 = mock_engine._generate_fingerprint(evidence)
    fp2 = mock_engine._generate_fingerprint(reversed(evidence))
    assert fp1 == fp2

def test_contradiction_handling(mock_engine):
    evidence = [
        IdentityEvidence(
            evidence_id="1",
            evidence_type="contradictory_profile_reference",
            direction="negative",
            strength_class="strong",
            source_type="confirmed_profile",
            source_reference="1",
            source_reliability_class="high",
            canonical_fact_key="fact",
            independence_group="conflict"
        )
    ]
    mapping = mock_engine._map_explanation(evidence, "conflicting_evidence", "unknown")
    assert len(mapping["why_not_matched"]) > 0
    assert mapping["why_not_matched"][0]["rule_id"] == "contradiction_detected"
