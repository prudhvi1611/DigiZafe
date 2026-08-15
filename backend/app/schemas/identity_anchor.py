import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class IdentityAliasBase(BaseModel):
    alias_type: str = Field(..., max_length=32, description="Type of alias e.g. username, display_name")
    value: str = Field(..., max_length=512, description="The alias value")


class CreateIdentityAliasRequest(IdentityAliasBase):
    pass


class IdentityAliasResponse(BaseModel):
    id: uuid.UUID
    alias_type: str
    display_value: str
    status: str
    confirmation_method: str
    created_at: datetime
    revoked_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ConfirmedProfileBase(BaseModel):
    platform: str = Field(..., max_length=64, description="Platform identifier e.g. github, twitter")
    profile_url: HttpUrl = Field(..., description="The profile URL")
    username_hint: str | None = Field(None, max_length=255)


class CreateConfirmedProfileRequest(ConfirmedProfileBase):
    pass


class ConfirmedProfileResponse(BaseModel):
    id: uuid.UUID
    platform: str
    profile_url_display: str
    username_hint: str | None = None
    status: str
    confirmation_method: str
    created_at: datetime
    revoked_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class VerifiedIdentifierSummary(BaseModel):
    id: uuid.UUID
    type: str
    value_display: str
    verified_at: datetime | None = None


class IdentityAnchorSummaryResponse(BaseModel):
    id: uuid.UUID
    version: int
    verified_identifiers: list[VerifiedIdentifierSummary]
    active_aliases: list[IdentityAliasResponse]
    active_confirmed_profiles: list[ConfirmedProfileResponse]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
