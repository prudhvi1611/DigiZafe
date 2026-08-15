import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint

from app.core.database import Base


class IdentityCrossLinkObservation(Base):
    """
    Bounded cross-link evidence representing observed relationships between
    profiles or recognized domains.
    """

    __tablename__ = "identity_cross_link_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # The source entity that contains the link
    source_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String(32), nullable=False) # candidate_profile | confirmed_profile
    
    # The target entity (if internally resolvable)
    target_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    target_entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    
    # The canonical external URL representation
    target_url_canonical: Mapped[str | None] = mapped_column(String(2048), index=True, nullable=True)
    
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="outbound") # outbound | mutual
    
    observation_source: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    provenance: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint('source_entity_id', 'target_url_canonical', name='uq_cross_link_observation'),
    )
