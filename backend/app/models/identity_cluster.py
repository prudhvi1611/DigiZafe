import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IdentityCluster(Base):
    """
    Algorithmic grouping of candidates that are deterministically assessed to
    represent the same identity.
    """

    __tablename__ = "identity_clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    anchor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_anchors.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # supported | ambiguous | conflicting
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="supported")
    
    cluster_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Deterministic hash of inputs used to build the cluster (for idempotency)
    input_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class IdentityClusterMember(Base):
    """
    Mapping between an IdentityCluster and a CandidateProfile.
    """

    __tablename__ = "identity_cluster_members"

    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_clusters.id", ondelete="CASCADE"), primary_key=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
