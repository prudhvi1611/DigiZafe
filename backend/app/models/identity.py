import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IdentityEdge(Base):
    """Pairwise link between two identifiers of the same user."""

    __tablename__ = "identity_edges"
    __table_args__ = (
        UniqueConstraint("user_id", "left_identifier_id", "right_identifier_id", name="uq_identity_edge_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    left_identifier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    right_identifier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identifiers.id", ondelete="CASCADE"), index=True, nullable=False
    )

    match_weight: Mapped[float] = mapped_column(Float, nullable=False)
    match_prob: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # auto_link | review | weak | none | accepted | rejected

    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="linkage-v1.0.0")

    # Human review
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    # open | accepted | rejected
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class IdentityCollision(Base):
    """Flagged potential collisions for manual review."""

    __tablename__ = "identity_collisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    edge_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_edges.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
