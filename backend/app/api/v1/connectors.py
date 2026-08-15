from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_active_superuser, get_db
from app.models.user import User
from app.schemas.connectors import ConnectorToggle, ProbeRequest
from app.services.connector_service import ConnectorService

router = APIRouter(prefix="/connectors", tags=["connectors"])


def _svc(db: AsyncSession = Depends(get_db)) -> ConnectorService:
    return ConnectorService(db)

def _conf_svc(db: AsyncSession = Depends(get_db)):
    from app.services.discovery.connectors.conformance_service import ConnectorConformanceService
    return ConnectorConformanceService(db)


@router.get("")
async def list_connectors(
    current_user: CurrentUser,
    svc: ConnectorService = Depends(_svc),
):
    """Catalog of free surface connectors + enablement state."""
    return await svc.list_catalog()

@router.get("/certification")
async def list_certification(
    current_user: CurrentUser,
    svc = Depends(_conf_svc)
):
    """Returns actual runtime descriptors and availability."""
    return await svc.get_connector_descriptors()


@router.patch("/{connector_id}")
async def toggle_connector(
    connector_id: str,
    body: ConnectorToggle,
    admin: User = Depends(get_current_active_superuser),
    svc: ConnectorService = Depends(_svc),
):
    """Admin-only enable/disable."""
    return await svc.set_enabled(connector_id, body.enabled, notes=body.notes)


@router.post("/probe/{identifier_id}")
async def probe_identifier(
    identifier_id: UUID,
    body: ProbeRequest | None = None,
    current_user: CurrentUser = None,  # type: ignore
    svc: ConnectorService = Depends(_svc),
):
    """
    Run free surface connectors against a **verified** identifier (G1).
    Does not persist findings yet (Sprint 4).
    """
    body = body or ProbeRequest()
    return await svc.probe(
        current_user.id,
        identifier_id,
        connector_ids=body.connector_ids,
        password_plaintext=body.password,
    )
