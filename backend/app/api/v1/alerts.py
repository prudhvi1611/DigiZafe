from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.recommendations_alerts import (
    AlertPublic,
    DeltaResponse,
    Message,
    RescanPolicyUpsert,
    RescanRequest,
)
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _svc(db: AsyncSession = Depends(get_db)) -> AlertService:
    return AlertService(db)


@router.get("", response_model=list[AlertPublic])
async def list_alerts(
    current_user: CurrentUser,
    unread_only: bool = False,
    svc: AlertService = Depends(_svc),
):
    return await svc.list_alerts(current_user.id, unread_only=unread_only)


@router.post("/{alert_id}/read", response_model=AlertPublic)
async def mark_read(
    alert_id: UUID,
    current_user: CurrentUser,
    svc: AlertService = Depends(_svc),
):
    return await svc.mark_read(current_user.id, alert_id)


@router.post("/{alert_id}/dismiss", response_model=Message)
async def dismiss_alert(
    alert_id: UUID,
    current_user: CurrentUser,
    svc: AlertService = Depends(_svc),
):
    return await svc.dismiss(current_user.id, alert_id)


@router.get("/deltas", response_model=DeltaResponse)
async def get_deltas(
    current_user: CurrentUser,
    identifier_id: UUID | None = None,
    svc: AlertService = Depends(_svc),
):
    data = await svc.compute_deltas(current_user.id, identifier_id)
    return DeltaResponse(**data)


@router.post("/rescan")
async def start_rescan(
    body: RescanRequest,
    current_user: CurrentUser,
    svc: AlertService = Depends(_svc),
):
    """Quota + cooldown aware rescan of a verified identifier."""
    return await svc.request_rescan(
        current_user.id,
        body.identifier_id,
        connector_ids=body.connector_ids,
        force=body.force,
    )


@router.put("/rescan-policy")
async def upsert_rescan_policy(
    body: RescanPolicyUpsert,
    current_user: CurrentUser,
    svc: AlertService = Depends(_svc),
):
    return await svc.upsert_rescan_policy(
        current_user.id,
        body.identifier_id,
        body.enabled,
        body.interval_hours,
    )
