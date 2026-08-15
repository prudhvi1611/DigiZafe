from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecommendationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    identifier_id: UUID | None = None
    code: str
    lane: str
    title: str
    summary: str
    urgency: float
    effort_hours: float
    roi: float
    priority: float
    sort_order: int
    depends_on: list[Any] | None = None
    related_finding_ids: list[Any] | None = None
    steps: list[Any] | None = None
    links: list[Any] | None = None
    playbook_key: str
    meta: dict[str, Any] | None = None
    status: str
    model_version: str
    created_at: datetime
    completed_at: datetime | None = None


class PlanPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: UUID | None = None
    model_version: str
    score_snapshot_id: UUID | None = None
    freeze_recommended: bool
    dag_order: list[Any] | None = None
    summary: str
    meta: dict[str, Any] | None = None
    created_at: datetime
    recommendations: list[RecommendationPublic] = []


class PlanGenerateRequest(BaseModel):
    identifier_id: UUID | None = None
    persist: bool = True


class RecommendationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|in_progress|done|dismissed|blocked)$")


class DisputeRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)
    rescore: bool = True


class AlertPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: UUID | None = None
    kind: str
    severity: str
    title: str
    body: str
    payload: dict[str, Any] | None = None
    read: bool
    dismissed: bool
    created_at: datetime


class RescanRequest(BaseModel):
    identifier_id: UUID
    connector_ids: list[str] | None = None
    force: bool = False  # ignore cooldown if True (still enforces daily quota)


class RescanPolicyUpsert(BaseModel):
    identifier_id: UUID
    enabled: bool = True
    interval_hours: int = Field(168, ge=24, le=720)


class DeltaResponse(BaseModel):
    score: dict[str, Any] | None = None
    findings: dict[str, Any] | None = None
    summary: str = ""


class Message(BaseModel):
    message: str
