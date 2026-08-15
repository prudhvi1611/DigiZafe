from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.recommendations_alerts import (
    DisputeRequest,
    PlanGenerateRequest,
    PlanPublic,
    RecommendationPublic,
    RecommendationStatusUpdate,
)
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _svc(db: AsyncSession = Depends(get_db)) -> RecommendationService:
    return RecommendationService(db)


@router.post("/generate", response_model=PlanPublic)
async def generate_plan(
    body: PlanGenerateRequest,
    current_user: CurrentUser,
    svc: RecommendationService = Depends(_svc),
):
    """Build two-lane prioritized plan (urgency + ROI + DAG) from findings + PDSS."""
    return await svc.generate(
        current_user.id,
        identifier_id=body.identifier_id,
        persist=body.persist,
    )


@router.get("/latest", response_model=PlanPublic)
async def latest_plan(
    current_user: CurrentUser,
    identifier_id: UUID | None = None,
    svc: RecommendationService = Depends(_svc),
):
    return await svc.latest_plan(current_user.id, identifier_id)


@router.get("", response_model=list[RecommendationPublic])
async def list_open_recommendations(
    current_user: CurrentUser,
    identifier_id: UUID | None = None,
    svc: RecommendationService = Depends(_svc),
):
    return await svc.list_open(current_user.id, identifier_id)


@router.patch("/{rec_id}", response_model=RecommendationPublic)
async def update_recommendation_status(
    rec_id: UUID,
    body: RecommendationStatusUpdate,
    current_user: CurrentUser,
    svc: RecommendationService = Depends(_svc),
):
    return await svc.update_status(current_user.id, rec_id, body.status)


@router.post("/findings/{finding_id}/dispute")
async def dispute_finding(
    finding_id: UUID,
    body: DisputeRequest,
    current_user: CurrentUser,
    svc: RecommendationService = Depends(_svc),
):
    """Dismiss disputed finding and rescore PDSS (closed loop)."""
    return await svc.dispute_finding(
        current_user.id, finding_id, body.reason, rescore=body.rescore
    )
