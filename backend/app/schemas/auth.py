from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    mfa_code: str | None = Field(None, min_length=6, max_length=8)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    mfa_required: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class MFASetupResponse(BaseModel):
    secret: str  # shown once; user must confirm
    provisioning_uri: str
    qr_code_data_uri: str | None = None


class MFAEnableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class MFADisableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)
    password: str  # re-auth


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool
    is_verified: bool
    mfa_enabled: bool
    created_at: datetime
    last_login_at: datetime | None = None


class Message(BaseModel):
    message: str
