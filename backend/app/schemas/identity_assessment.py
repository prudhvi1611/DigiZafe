from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ExplanationItem(BaseModel):
    rule_id: str
    message_key: str
    evidence_keys: list[str]
    message_text: str  # human readable rendering for UI


class IdentityEvidence(BaseModel):
    evidence_id: str
    evidence_type: str
    direction: str  # positive, negative, unknown, neutral
    strength_class: str  # strong, moderate, weak
    source_type: str
    source_reference: str
    source_reliability_class: str  # authoritative, high, medium, low, unknown
    canonical_fact_key: str
    independence_group: str
    derived_from: str | None = None
    status: str = "active"


class IdentityMatchAssessmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    anchor_id: UUID
    candidate_profile_id: UUID
    
    is_current: bool
    anchor_version: int
    candidate_revision: str
    
    engine_version: int
    policy_version: int
    
    score: int
    assessment_status: str
    confidence_band: str
    
    evidence_snapshot: list[IdentityEvidence]
    explanation_mapping: dict[str, list[ExplanationItem]]
    
    stale_state: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
