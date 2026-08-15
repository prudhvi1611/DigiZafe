import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.connector_certification import ConnectorCertificationRecord
from app.services.discovery.connectors.conformance_service import ConnectorConformanceService

@pytest.mark.asyncio
async def test_historical_certification_preserved(db_session: AsyncSession):
    # Insert an old certification
    old_cert = ConnectorCertificationRecord(
        connector_type="identity_enrichment",
        availability="available",
        runtime_fingerprint="old_fp",
        adapter_version="1.0",
        runtime_version="1.0"
    )
    db_session.add(old_cert)
    await db_session.commit()
    
    # Now simulate a new certification via ConformanceService mock
    svc = ConnectorConformanceService(db_session)
    
    # Mock registry so it doesn't fail
    from unittest.mock import patch
    
    class DummyConnector:
        connector_type = "identity_enrichment"
        adapter_version = "1.0"
        
    with patch("app.services.discovery.connectors.conformance_service.ConnectorRegistry.get_all_connectors") as mock_reg:
        mock_reg.return_value = [DummyConnector()]
        # Actually run offline conformance which triggers invalidation
        await svc.run_offline_conformance("identity_enrichment")
    
    # Verify both records exist, old one is disabled
    all_certs = (await db_session.execute(
        select(ConnectorCertificationRecord).where(ConnectorCertificationRecord.connector_type == "identity_enrichment")
    )).scalars().all()
    
    assert len(all_certs) >= 2
    
    old_db_cert = next(c for c in all_certs if c.id == old_cert.id)
    assert old_db_cert.availability == "disabled"
    assert old_db_cert.invalidated_at is not None
    
    new_db_cert = next(c for c in all_certs if c.id != old_cert.id)
    assert new_db_cert.availability in ["available", "installed_unverified"]
