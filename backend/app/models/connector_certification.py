import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class ConnectorCertificationRecord(Base):
    __tablename__ = "connector_certification_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connector_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    
    # "test_only", "installed_unverified", "certification_failed", "available", "temporarily_unhealthy", "disabled"
    availability: Mapped[str] = mapped_column(String(32), nullable=False, default="test_only")
    
    adapter_version: Mapped[str] = mapped_column(String(64), nullable=False)
    runtime_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    runtime_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    runtime_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    
    conformance_policy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # "NOT_RUN", "PASSED", "FAILED", "NOT_REQUIRED"
    live_smoke_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NOT_RUN")
    live_smoke_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    last_certified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Details of certification or failure
    certification_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
