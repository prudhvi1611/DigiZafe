import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Observation(Base):
    """
    Layer-1-ish raw connector observation (short TTL).
    May hold a redacted snapshot; full HTML dumps are NOT stored.
    """

    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    identifier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), index=True, nullable=True
    )
    connector_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_connector_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )

    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    layer: Mapped[str] = mapped_column(String(32), nullable=False, default="surface")
    raw_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    attribution: Mapped[str | None] = mapped_column(String(512), nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # redacted observation dict only — never full breach dumps / HTML

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Finding(Base):
    """
    Durable normalized finding (layer-3 metadata).
    Deduped by (user_id, identifier_id, source, fingerprint).
    """

    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "identifier_id",
            "source",
            "fingerprint",
            name="uq_findings_user_ident_source_fp",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    identifier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # G1: identifier must be verified — enforced by DB trigger

    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity_hint: Mapped[str] = mapped_column(String(32), nullable=False, default="info", index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    layer: Mapped[str] = mapped_column(String(32), nullable=False, default="surface", index=True)
    track: Mapped[str] = mapped_column(String(32), nullable=False, default="confirmed")  # confirmed | possible
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_ref: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    attribution: Mapped[str | None] = mapped_column(String(512), nullable=True)

    first_seen_scan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_seen_scan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    times_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Soft status for remediation later
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    # open | acknowledged | remediating | resolved | dismissed

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EvidenceBlob(Base):
    """
    Explicit 3-layer evidence store.
    layer: raw | summary | durable
    raw = short TTL, summary = medium TTL, durable = finding-linked metadata (no auto purge)
    """

    __tablename__ = "evidence_blobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    identifier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    scan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), index=True, nullable=True
    )
    observation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)

    layer: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # raw | summary | durable
    content_type: Mapped[str] = mapped_column(String(64), nullable=False, default="application/json")
    # Always JSON-redacted structured data — never raw HTML dumps long-term
    body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    # null for durable

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
