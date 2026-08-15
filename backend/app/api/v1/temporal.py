import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.temporal import IdentityChangeEvent, IdentityReviewItem
from app.schemas.temporal import (
    IdentityChangeEventResponse,
    IdentityReviewItemResponse,
    IdentityReviewResolutionRequest
)
from app.services.identity_review_queue_service import IdentityReviewQueueService
from app.services.identity_revalidation_service import IdentityRevalidationService

router = APIRouter()

@router.get("/timeline", response_model=list[IdentityChangeEventResponse])
async def get_identity_timeline(
    anchor_id: uuid.UUID | None = None,
    candidate_profile_id: uuid.UUID | None = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Retrieve the temporal identity timeline events.
    """
    stmt = select(IdentityChangeEvent).where(IdentityChangeEvent.user_id == current_user.id)
    
    if anchor_id:
        stmt = stmt.where(IdentityChangeEvent.anchor_id == anchor_id)
    if candidate_profile_id:
        stmt = stmt.where(IdentityChangeEvent.candidate_profile_id == candidate_profile_id)
        
    stmt = stmt.order_by(IdentityChangeEvent.detected_at.desc()).limit(limit).offset(offset)
    
    events = (await db.execute(stmt)).scalars().all()
    return events


@router.get("/reviews", response_model=list[IdentityReviewItemResponse])
async def list_review_queue(
    status_filter: str | None = None,
    priority: str | None = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List items in the identity review queue.
    """
    stmt = select(IdentityReviewItem).where(IdentityReviewItem.user_id == current_user.id)
    
    if status_filter:
        stmt = stmt.where(IdentityReviewItem.status == status_filter)
    if priority:
        stmt = stmt.where(IdentityReviewItem.priority == priority)
        
    stmt = stmt.order_by(IdentityReviewItem.created_at.desc()).limit(limit).offset(offset)
    
    reviews = (await db.execute(stmt)).scalars().all()
    return reviews


@router.post("/reviews/{review_id}/resolve", response_model=IdentityReviewItemResponse)
async def resolve_review_item(
    review_id: uuid.UUID,
    request: IdentityReviewResolutionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Resolve an item in the review queue.
    """
    review_service = IdentityReviewQueueService(db)
    try:
        review = await review_service.resolve_review(
            review_id=review_id,
            user_id=current_user.id,
            resolution=request.resolution,
            note=request.note
        )
        await db.commit()
        return review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reviews/{review_id}/revalidate")
async def request_explicit_revalidation(
    review_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Explicitly request revalidation for a review item.
    """
    from app.connectors.sdk.redis_clients import get_cache_redis
    redis = await get_cache_redis()
    service = IdentityRevalidationService(db, redis)
    try:
        run = await service.request_revalidation_for_review(
            user_id=current_user.id,
            review_id=review_id,
            is_automatic=False
        )
        await db.commit()
        return {"orchestration_run_id": run.id if run else None, "status": "requested"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
