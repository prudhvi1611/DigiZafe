from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExportCreateRequest(BaseModel):
    include_audit: bool = True
    include_egress: bool = True


class ExportJobPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    include_audit: bool
    include_egress: bool
    size_bytes: int
    expires_at: datetime
    created_at: datetime
    ready_at: datetime | None = None
    error: str | None = None


class ExportPackageResponse(BaseModel):
    job: ExportJobPublic
    package: dict[str, Any] | None = None


class ConsentItem(BaseModel):
    id: UUID | None = None
    purpose: str
    scope: str | None = None
    granted: bool
    created_at: datetime | None = None
    revoked_at: datetime | None = None
    details: dict[str, Any] | None = None


class ConsentRevokeRequest(BaseModel):
    purpose: str


class ConsentGrantRequest(BaseModel):
    purpose: str
    scope: str | None = None
    details: dict[str, Any] | None = None


class AuditEventPublic(BaseModel):
    id: UUID
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict[str, Any] | None = None
    created_at: datetime
    correlation_id: str | None = None


class EgressEventPublic(BaseModel):
    id: UUID
    purpose: str
    destination_host: str
    method: str
    status_code: int | None = None
    success: bool
    summary: dict[str, Any] | None = None
    created_at: datetime


class AccountDeleteRequest(BaseModel):
    confirm_phrase: str = Field(..., min_length=5)
    immediate: bool = False  # only honored in dev when ACCOUNT_DELETE_DEV_IMMEDIATE


class AccountDeletePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    scheduled_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
    error: str | None = None


class NarrativeRequest(BaseModel):
    identifier_id: UUID | None = None
    score_snapshot_id: UUID | None = None
    prefer_ollama: bool = True
    persist: bool = True


class NarrativePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    score_snapshot_id: UUID | None = None
    identifier_id: UUID | None = None
    mode: str
    model_name: str | None = None
    title: str
    body_markdown: str
    grounded: bool
    facts_used: dict[str, Any] | None = None
    created_at: datetime | None = None


class CounterfactualPublic(BaseModel):
    score_snapshot_id: UUID | None = None
    counterfactuals: list[dict[str, Any]] = []
    explanation_summary: str = ""
    vector: str | None = None
    score_combined: float | None = None


class Message(BaseModel):
    message: str
