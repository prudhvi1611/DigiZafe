from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScanCreate(BaseModel):
    identifier_id: UUID
    connector_ids: list[str] | None = None

    layer_scope: str = Field(
        default="surface",
        pattern="^(surface|deep|constrained_dark)$",
    )


class ScanConnectorRunPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    connector_id: str
    status: str
    skip_reason: str | None = None
    error: str | None = None
    cache_hit: bool
    observation_count: int
    finding_count: int
    result_meta: dict[str, Any] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ScanPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: UUID
    status: str
    layer_scope: str
    connector_ids: list[Any] | None = None
    progress_pct: float
    message: str | None = None
    error: str | None = None
    observation_count: int
    finding_count: int
    deadline_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    meta: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    connector_runs: list[ScanConnectorRunPublic] = []


class ScanListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: UUID
    status: str
    progress_pct: float
    finding_count: int
    observation_count: int
    created_at: datetime
    finished_at: datetime | None = None


class FindingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_id: UUID
    kind: str
    source: str
    title: str
    summary: str
    severity_hint: str
    confidence: float
    layer: str
    track: str
    raw_ref: str | None = None
    attributes: dict[str, Any] | None = None
    attribution: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    times_seen: int
    status: str
    created_at: datetime


class Message(BaseModel):
    message: str

class LayerMetadataPublic(BaseModel):
    layer: str
    label: str
    description: str
    requires_consent: bool
    enabled: bool
