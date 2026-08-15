import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    identifier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    lane: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    urgency: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    effort_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    roi: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    priority: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    depends_on: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    related_finding_ids: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    steps: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    links: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    playbook_key: Mapped[str] = mapped_column(String(128), nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    # open | in_progress | done | dismissed | blocked

    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="rec-v1.0.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecommendationPlan(Base):
    """One generation of a prioritized plan for a scope."""

    __tablename__ = "recommendation_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    identifier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    score_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    freeze_recommended: Mapped[bool] = mapped_column(default=False, nullable=False)
    dag_order: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
