from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.identity_score import (
    ScoreHistoryItem,
    ScorePublic,
    ScoreRequest,
    WhatIfRequest,
)
from app.services.scoring_service import ScoringService

router = APIRouter(prefix="/scores", tags=["scores"])


def _svc(db: AsyncSession = Depends(get_db)) -> ScoringService:
    return ScoringService(db)


@router.post("/compute", response_model=ScorePublic)
async def compute_score(
    body: ScoreRequest,
    current_user: CurrentUser,
    svc: ScoringService = Depends(_svc),
):
    """
    Compute hybrid PDSS (Base/Temporal/Environmental + surprisal, two-track).
    Includes XposedOrNot drivers from finding attributes when present.
    """
    return await svc.compute(
        current_user.id,
        identifier_id=body.identifier_id,
        persist=body.persist,
        trigger=body.trigger,
    )


@router.get("/latest", response_model=ScorePublic)
async def latest_score(
    current_user: CurrentUser,
    identifier_id: UUID | None = None,
    svc: ScoringService = Depends(_svc),
):
    return await svc.latest(current_user.id, identifier_id)


@router.get("/history", response_model=list[ScoreHistoryItem])
async def score_history(
    current_user: CurrentUser,
    identifier_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    svc: ScoringService = Depends(_svc),
):
    rows = await svc.history(current_user.id, identifier_id=identifier_id, limit=limit)
    return [ScoreHistoryItem.model_validate(r) for r in rows]


@router.get("/{snapshot_id}", response_model=ScorePublic)
async def get_snapshot(
    snapshot_id: UUID,
    current_user: CurrentUser,
    svc: ScoringService = Depends(_svc),
):
    return await svc.get_snapshot(current_user.id, snapshot_id)


@router.get("/{snapshot_id}/explanations")
async def get_explanations(
    snapshot_id: UUID,
    current_user: CurrentUser,
    svc: ScoringService = Depends(_svc),
):
    """Durable G3 explanation records for a snapshot."""
    return await svc.explanations(current_user.id, snapshot_id)


@router.post("/whatif", response_model=ScorePublic)
async def whatif(
    body: WhatIfRequest,
    current_user: CurrentUser,
    svc: ScoringService = Depends(_svc),
):
    """
    What-if simulator: recompute PDSS excluding selected findings/sources/kinds.
    Persists with trigger=whatif for history/comparison.
    """
    return await svc.compute(
        current_user.id,
        identifier_id=body.identifier_id,
        persist=True,
        trigger="whatif",
        exclude_finding_ids={str(x) for x in body.exclude_finding_ids},
        exclude_sources=set(body.exclude_sources or []),
        exclude_kinds=set(body.exclude_kinds or []),
    )
