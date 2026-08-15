from typing import Any

from pydantic import BaseModel, Field


class ConnectorToggle(BaseModel):
    enabled: bool
    notes: str | None = None


class ProbeRequest(BaseModel):
    connector_ids: list[str] | None = None
    # Optional password for pwned_passwords only — never stored
    password: str | None = Field(None, min_length=1, max_length=256)


class ProbeResponse(BaseModel):
    identifier_id: str
    identifier_type: str
    results: list[dict[str, Any]]
    attributions: list[str] = []
    note: str = ""
