from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IdentityEdgePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    left_identifier_id: UUID
    right_identifier_id: UUID
    match_weight: float
    match_prob: float
    decision: str
    evidence: dict[str, Any] | None = None
    review_status: str
    review_note: str | None = None
    model_version: str
    created_at: datetime


class IdentityGraphPublic(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[IdentityEdgePublic]
    collisions: list[dict[str, Any]] = []
    model_version: str


class EdgeReviewRequest(BaseModel):
    review_status: str = Field(..., pattern="^(accepted|rejected)$")
    review_note: str | None = None


class ScoreRequest(BaseModel):
    identifier_id: UUID | None = None  # null = whole identity
    persist: bool = True
    trigger: str = "manual"


class WhatIfRequest(BaseModel):
    identifier_id: UUID | None = None
    exclude_finding_ids: list[UUID] = Field(default_factory=list)
    # optional: simulate removing kinds/sources
    exclude_sources: list[str] = Field(default_factory=list)
    exclude_kinds: list[str] = Field(default_factory=list)


class ResidualMLPublic(BaseModel):
    status: str
    model_version: str | None = None
    feature_schema_version: str | None = None
    bounded_delta: float | None = None
    confidence: float | None = None
    abstained: bool = False
    reason: str | None = None


class ScorePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    identifier_id: UUID | None = None
    model_version: str
    score_confirmed: float
    score_possible: float
    score_combined: float
    severity: str
    vector: str
    metrics: dict[str, Any] | None = None
    contributions: list[Any] | None = None
    counterfactuals: list[Any] | None = None
    attributions: list[Any] | None = None
    explanation_summary: str
    finding_count: int = 0
    trigger: str = "manual"
    created_at: datetime | None = None
    meta: dict[str, Any] | None = None
    residual_ml: ResidualMLPublic | None = None


class ScoreHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: UUID | None = None
    score_combined: float
    severity: str
    model_version: str
    trigger: str
    finding_count: int
    created_at: datetime


class Message(BaseModel):
    message: str
