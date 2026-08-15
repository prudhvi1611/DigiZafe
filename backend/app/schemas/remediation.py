from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RemediationProfileInput(BaseModel):
    """Optional profile fields for form fill (beyond verified identifiers)."""
    display_name: str | None = Field(None, max_length=200)
    state: str | None = Field(None, max_length=64)
    city: str | None = Field(None, max_length=128)
    zip: str | None = Field(None, max_length=20)


class BrokerOptOutStart(BaseModel):
    identifier_id: UUID  # verified email (or primary) — G1
    broker_ids: list[str] | None = None  # default: all enabled green
    dry_run: bool = False
    profile: RemediationProfileInput | None = None
    recommendation_id: UUID | None = None


class JobItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    broker_id: str
    broker_name: str
    status: str
    skip_reason: str | None = None
    error: str | None = None
    detail: str | None = None
    result_meta: dict[str, Any] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RemediationJobPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: UUID | None = None
    job_type: str
    status: str
    dry_run: bool
    broker_ids: list[Any] | None = None
    progress_pct: float
    message: str | None = None
    error: str | None = None
    result_summary: dict[str, Any] | None = None
    deadline_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    items: list[JobItemPublic] = []


class BrokerStatePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    broker_id: str
    broker_name: str
    status: str
    last_success_at: datetime | None = None
    last_attempt_at: datetime | None = None
    last_verified_at: datetime | None = None
    total_runs: int
    detail: str | None = None
    meta: dict[str, Any] | None = None
    updated_at: datetime


class CaptchaPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    broker_id: str
    status: str
    page_url: str | None = None
    captcha_type: str
    instructions: str | None = None
    expires_at: datetime
    created_at: datetime


class CaptchaSolveRequest(BaseModel):
    solution_token: str | None = Field(None, max_length=4000)
    # Or mark skipped / open_in_browser completed
    action: str = Field("solve", pattern="^(solve|skip|manual_done)$")


class ManualItemComplete(BaseModel):
    status: str = Field(..., pattern="^(submitted|manual_needed|skipped|error)$")
    detail: str | None = None


class FreezeItemUpdate(BaseModel):
    status: str = Field(..., pattern="^(todo|in_progress|done|skipped)$")
    notes: str | None = None


class FreezeItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_id: str
    label: str
    url: str
    status: str
    notes: str | None = None
    completed_at: datetime | None = None


class KnowRequestCreate(BaseModel):
    regime: str = Field("ccpa", pattern="^(ccpa|gdpr|other)$")
    recipient_name: str = Field(..., min_length=1, max_length=256)
    recipient_email: EmailStr | None = None
    identifier_id: UUID | None = None
    include_deletion: bool = True


class ComplaintCreate(BaseModel):
    regime: str = Field("ccpa", pattern="^(ccpa|gdpr|other)$")
    recipient_name: str
    original_request_id: UUID | None = None
    regulator: str = Field("ca_ag", max_length=64)
    # ca_ag | ico | other
    facts: str = Field(..., min_length=10, max_length=5000)


class GeneratedRequestPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    regime: str
    recipient_name: str | None = None
    recipient_email: str | None = None
    subject: str
    body: str
    status: str
    deadline_at: datetime | None = None
    sent_at: datetime | None = None
    created_at: datetime


class MarkSentRequest(BaseModel):
    sent: bool = True


class VerifyBrokersRequest(BaseModel):
    broker_ids: list[str] | None = None  # default: those with last_success


class Message(BaseModel):
    message: str
