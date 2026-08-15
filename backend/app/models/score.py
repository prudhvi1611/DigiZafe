import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScoreSnapshot(Base):
    """Durable PDSS result for a user scope (per identifier or whole identity)."""

    __tablename__ = "score_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # null identifier_id = whole-user / identity-graph aggregate
    identifier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=True
    )

    model_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    score_confirmed: Mapped[float] = mapped_column(Float, nullable=False)
    score_possible: Mapped[float] = mapped_column(Float, nullable=False)
    score_combined: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    vector: Mapped[str] = mapped_column(String(512), nullable=False)

    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    contributions: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    counterfactuals: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    attributions: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    explanation_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    # manual | post_scan | whatif | revalidate

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )


class ExplanationRecord(Base):
    """Durable explainability record (G3) — redacted drivers only."""

    __tablename__ = "explanation_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_snapshots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    finding_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)

    kind: Mapped[str] = mapped_column(String(64), nullable=False)  # contribution | counterfactual | summary
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # drivers, vector_fragment, narrative, etc.

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

class ResidualInferenceRecord(Base):
    """Durable record of residual ML inference for a score snapshot."""

    __tablename__ = "residual_inference_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_snapshots.id", ondelete="CASCADE"), index=True, nullable=False, unique=True
    )
    
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    feature_schema_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    raw_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    bounded_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    abstained: Mapped[bool] = mapped_column(nullable=False, default=False)
    abstention_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
