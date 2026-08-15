import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IdentityOrchestrationRun(Base):
    __tablename__ = "identity_orchestration_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    anchor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_anchors.id", ondelete="CASCADE"), index=True, nullable=True
    )

    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False, index=True)
    # planned, queued, running, completed, partial_result, failed, cancelled, no_action

    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    requested_capabilities: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    planned_connector_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    executed_connector_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_connector_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    plan_items: Mapped[list["ConnectorExecutionPlanItem"]] = relationship(
        "ConnectorExecutionPlanItem", back_populates="orchestration_run", cascade="all, delete-orphan"
    )


class ConnectorExecutionPlanItem(Base):
    __tablename__ = "connector_execution_plan_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    orchestration_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_orchestration_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    connector_type: Mapped[str] = mapped_column(String(64), nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    input_alias_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_aliases.id", ondelete="CASCADE"), index=True, nullable=True
    )
    
    decision: Mapped[str] = mapped_column(String(64), nullable=False)
    # execute, skip_fresh, skip_disabled, skip_no_consent, skip_budget, skip_unavailable, skip_test_only, skip_unhealthy, skip_ineligible, skip_duplicate, defer_runtime_control_unavailable
    
    decision_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    freshness_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    health_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    budget_state: Mapped[str | None] = mapped_column(String(32), nullable=True)

    discovery_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_discovery_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )

    execution_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    # pending, running, completed, failed, cancelled, skipped
    
    runtime_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    certification_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connector_certification_records.id", ondelete="SET NULL"), index=True, nullable=True
    )
    execution_mode: Mapped[str | None] = mapped_column(String(16), nullable=True) # mock, fixture, live
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True) # success, failure
    normalized_result_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timeout_occurred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    output_truncated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    orchestration_run: Mapped["IdentityOrchestrationRun"] = relationship(
        "IdentityOrchestrationRun", back_populates="plan_items"
    )
