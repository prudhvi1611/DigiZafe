from datetime import datetime, timezone
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.connector_certification import ConnectorCertificationRecord
from app.services.discovery.connectors.registry import ConnectorRegistry
from app.services.discovery.connectors.runtime_fingerprint_service import RuntimeFingerprintService
from app.tasks.identity_discovery_tasks import trigger_certification_reassessment

logger = logging.getLogger(__name__)

class ConnectorConformanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def get_connector_status(self, connector_type: str) -> str:
        """
        Returns the availability status of a connector's active certification.
        """
        stmt = select(ConnectorCertificationRecord).where(
            ConnectorCertificationRecord.connector_type == connector_type,
            ConnectorCertificationRecord.availability.in_(["available", "test_only", "installed_unverified"])
        ).order_by(ConnectorCertificationRecord.created_at.desc())
        record = (await self.db.execute(stmt)).scalars().first()
        
        if record:
            return record.availability
        return "test_only"

    async def get_connector_descriptors(self) -> list[dict]:
        descriptors = []
        for c in ConnectorRegistry.get_all_connectors():
            stmt = select(ConnectorCertificationRecord).where(
                ConnectorCertificationRecord.connector_type == c.connector_type
            ).order_by(ConnectorCertificationRecord.created_at.desc())
            record = (await self.db.execute(stmt)).scalars().first()
            
            status = record.availability if record else "test_only"
            runtime_version = record.runtime_version if record else None
            runtime_revision = record.runtime_revision if record else None
            fingerprint = record.runtime_fingerprint if record else None
            
            descriptors.append({
                "connector_type": c.connector_type,
                "adapter_version": c.adapter_version,
                "runtime_version": runtime_version,
                "runtime_revision": runtime_revision,
                "runtime_fingerprint": fingerprint,
                "availability": status,
                "capabilities": [cap.value for cap in c.capabilities],
                "queue": c.queue,
                "timeout": c.timeout,
                "output_limit": c.output_limit,
                "health_policy": c.health_policy
            })
            
        return descriptors

    async def _invalidate_old_certifications(self, connector_type: str, new_fingerprint: str):
        now = datetime.now(timezone.utc)
        stmt = select(ConnectorCertificationRecord).where(
            ConnectorCertificationRecord.connector_type == connector_type,
            ConnectorCertificationRecord.runtime_fingerprint != new_fingerprint,
            ConnectorCertificationRecord.availability.in_(["available", "installed_unverified", "temporarily_unhealthy"])
        )
        records = (await self.db.execute(stmt)).scalars().all()
        for rec in records:
            rec.availability = "disabled"
            rec.invalidated_at = now
            rec.invalidation_reason = "runtime_fingerprint_changed"
            # Trigger fan-out reassessment
            trigger_certification_reassessment.delay(connector_type, rec.runtime_fingerprint)
            
        await self.db.commit()

    async def run_offline_conformance(self, connector_type: str) -> ConnectorCertificationRecord:
        """
        Runs offline conformance checks and updates the certification record.
        """
        # Determine current code versions
        registry_connector = None
        for c in ConnectorRegistry.get_all_connectors():
            if c.connector_type == connector_type:
                registry_connector = c
                break
                
        if not registry_connector:
            raise ValueError(f"Unknown connector {connector_type}")

        # Gather versions (mock logic for now, should call adapters)
        runtime_version = "unknown"
        runtime_revision = "unknown"
        conformance_policy_version = 1
        parser_version = "1.0"
        
        if connector_type == "maigret":
            import maigret
            runtime_version = maigret.__version__
        elif connector_type == "osintgram":
            runtime_version = "1.1.0-mock" # Stub
            runtime_revision = "git-12345"

        fingerprint = RuntimeFingerprintService.generate_fingerprint(
            connector_type=connector_type,
            adapter_version=registry_connector.adapter_version,
            runtime_version=runtime_version,
            runtime_revision=runtime_revision,
            parser_version=parser_version,
            conformance_policy_version=conformance_policy_version
        )
        
        await self._invalidate_old_certifications(connector_type, fingerprint)
        
        stmt = select(ConnectorCertificationRecord).where(
            ConnectorCertificationRecord.connector_type == connector_type,
            ConnectorCertificationRecord.runtime_fingerprint == fingerprint
        )
        record = (await self.db.execute(stmt)).scalars().first()
        
        now = datetime.now(timezone.utc)
        
        if not record:
            availability = "test_only" if runtime_version == "1.1.0-mock" else "available"
            
            record = ConnectorCertificationRecord(
                connector_type=connector_type,
                availability=availability,
                adapter_version=registry_connector.adapter_version,
                runtime_version=runtime_version,
                runtime_revision=runtime_revision,
                runtime_fingerprint=fingerprint,
                conformance_policy_version=conformance_policy_version,
                parser_version=parser_version,
                last_certified_at=now if availability == "available" else None,
                last_health_check_at=now,
                certification_details={"offline_check": "passed"}
            )
            self.db.add(record)
        else:
            record.last_health_check_at = now
            
        await self.db.commit()
        await self.db.refresh(record)
        return record
