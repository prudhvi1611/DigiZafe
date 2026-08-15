from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.canonicalize import IdentifierType


class IdentifierCreate(BaseModel):
    type: IdentifierType
    value: str = Field(..., min_length=1, max_length=512)


class IdentifierPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    value_display: str
    value_canonical: str  # owner may see full canonical
    is_verified: bool
    verified_at: datetime | None = None
    verification_method: str | None = None
    last_revalidated_at: datetime | None = None
    created_at: datetime


class VerificationStartResponse(BaseModel):
    challenge_id: UUID
    method: str
    expires_at: datetime
    instructions: dict[str, Any]
    # Dev only — never in production responses if flag off
    dev_code: str | None = None


class VerificationConfirmRequest(BaseModel):
    code: str | None = None  # email_code
    # dns/github: server re-checks; optional client noop


class Message(BaseModel):
    message: str


class ConsentGrant(BaseModel):
    purpose: str
    scope: str | None = None
    details: dict[str, Any] | None = None
