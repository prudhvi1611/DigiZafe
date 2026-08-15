from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.services.discovery_service import DiscoveryService

router = APIRouter(prefix="/layers", tags=["layers"])


def _svc(db: AsyncSession = Depends(get_db)) -> DiscoveryService:
    return DiscoveryService(db)


@router.get("")
async def list_layers(
    current_user: CurrentUser,
    svc: DiscoveryService = Depends(_svc),
):
    """Return layer definitions and consent requirements."""
    return await svc.layer_catalog()
