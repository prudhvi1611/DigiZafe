import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IdentityMatchAssessment(Base):
    __tablename__ = "identity_match_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    anchor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_anchors.id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )

    input_fingerprint: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)


    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    anchor_version: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_revision: Mapped[str] = mapped_column(String(255), nullable=False)
    
    engine_version: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    assessment_input_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    score: Mapped[int] = mapped_column(Integer, nullable=False)
    assessment_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # likely_match, possible_match, insufficient_evidence, unlikely_match, conflicting_evidence
    confidence_band: Mapped[str] = mapped_column(String(128), nullable=False)

    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list, nullable=False)
    explanation_mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    stale_state: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    # active, stale_anchor, stale_candidate, stale_policy, stale_recalculated

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
