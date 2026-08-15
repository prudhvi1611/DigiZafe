from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Any

class IdentityChangeEventResponse(BaseModel):
    id: UUID
    anchor_id: UUID
    candidate_profile_id: UUID | None
    canonical_fact_key: str
    change_type: str
    previous_value_fingerprint: str | None
    new_value_fingerprint: str | None
    previous_state: str | None
    new_state: str
    materiality: str
    review_priority: str
    confidence_state: str
    detected_at: datetime
    effective_at: datetime | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class IdentityReviewItemResponse(BaseModel):
    id: UUID
    anchor_id: UUID
    candidate_profile_id: UUID | None
    review_type: str
    priority: str
    status: str
    reason_code: str
    grouping_key: str | None
    reviewed_at: datetime | None
    resolution: str | None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class IdentityReviewResolutionRequest(BaseModel):
    resolution: str
    note: str | None = None
