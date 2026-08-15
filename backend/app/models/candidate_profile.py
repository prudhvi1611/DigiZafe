import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
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


class CandidateDiscoveryRun(Base):
    __tablename__ = "candidate_discovery_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    anchor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_anchors.id", ondelete="CASCADE"), index=True, nullable=False
    )
    anchor_version: Mapped[int] = mapped_column(Integer, nullable=False)

    orchestration_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_orchestration_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    plan_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connector_execution_plan_items.id", ondelete="SET NULL"), index=True, nullable=True
    )

    source_tool: Mapped[str] = mapped_column(String(64), nullable=False)
    source_tool_version: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    # queued, running, completed, partially_completed, failed, cancelled, timed_out

    input_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    discovery_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_discovery_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    anchor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_anchors.id", ondelete="CASCADE"), index=True, nullable=False
    )
    anchor_version: Mapped[int] = mapped_column(Integer, nullable=False)

    source_input_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    source_input_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_input_value_reference: Mapped[str] = mapped_column(String(512), nullable=False)

    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    canonical_profile_url: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    username_observed: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name_observed: Mapped[str | None] = mapped_column(String(512), nullable=True)

    candidate_status: Mapped[str] = mapped_column(String(32), default="unreviewed", nullable=False, index=True)
    # unreviewed, confirmed_by_user, dismissed

    source_tool: Mapped[str] = mapped_column(String(64), nullable=False)
    source_tool_version: Mapped[str] = mapped_column(String(64), nullable=False)

    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
