import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.domain.temporal_states import (
    REVIEW_STATUS_OPEN,
    REVIEW_STATUS_IN_REVIEW,
    REVIEW_STATUS_RESOLVED,
    REVIEW_STATUS_DISMISSED,
    REVIEW_STATUS_SUPERSEDED,
    REVIEW_IDENTITY_CHANGE,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
    RESOLUTION_ACKNOWLEDGED,
    RESOLUTION_THIS_IS_STILL_MINE,
    RESOLUTION_THIS_IS_NOT_MINE,
    RESOLUTION_EXPECTED_CHANGE,
    RESOLUTION_REQUEST_REVALIDATION,
    RESOLUTION_DISMISS_ALERT,
    MATERIALITY_CRITICAL_REVIEW,
    MATERIALITY_HIGH,
    MATERIALITY_MEDIUM
)
from app.models.temporal import IdentityReviewItem, IdentityChangeEvent, IdentityReviewItemEvent


class IdentityReviewQueueService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.config = get_settings()

    def generate_grouping_key(self, user_id: uuid.UUID, candidate_profile_id: uuid.UUID | None, review_type: str, timestamp: datetime) -> str:
        window_minutes = self.config.change_burst_window_minutes
        bucket = int(timestamp.timestamp() // (window_minutes * 60))
        prof = str(candidate_profile_id) if candidate_profile_id else "anchor"
        return f"{user_id}:{prof}:{review_type}:{bucket}"

    async def enqueue_from_event(self, event: IdentityChangeEvent) -> IdentityReviewItem | None:
        if not self.config.feature_identity_review_queue:
            return None

        if event.materiality not in (MATERIALITY_CRITICAL_REVIEW, MATERIALITY_HIGH, MATERIALITY_MEDIUM):
            return None

        review_type = REVIEW_IDENTITY_CHANGE

        grouping_key = self.generate_grouping_key(
            user_id=event.user_id,
            candidate_profile_id=event.candidate_profile_id,
            review_type=review_type,
            timestamp=event.detected_at
        )

        stmt = select(IdentityReviewItem).where(
            IdentityReviewItem.grouping_key == grouping_key,
            IdentityReviewItem.status.in_([REVIEW_STATUS_OPEN, REVIEW_STATUS_IN_REVIEW])
        )
        existing = (await self.db.execute(stmt)).scalars().first()

        if existing:
            link_stmt = select(IdentityReviewItemEvent).where(
                IdentityReviewItemEvent.review_id == existing.id,
                IdentityReviewItemEvent.event_id == event.id
            )
            link = (await self.db.execute(link_stmt)).scalars().first()
            if not link:
                new_link = IdentityReviewItemEvent(review_id=existing.id, event_id=event.id)
                self.db.add(new_link)
                priorities = {PRIORITY_LOW: 1, PRIORITY_MEDIUM: 2, PRIORITY_HIGH: 3, PRIORITY_CRITICAL: 4}
                if priorities.get(event.review_priority, 0) > priorities.get(existing.priority, 0):
                    existing.priority = event.review_priority
            return existing

        new_review = IdentityReviewItem(
            user_id=event.user_id,
            anchor_id=event.anchor_id,
            candidate_profile_id=event.candidate_profile_id,
            review_type=review_type,
            priority=event.review_priority,
            status=REVIEW_STATUS_OPEN,
            reason_code=f"CHANGE_{event.change_type}",
            grouping_key=grouping_key
        )
        self.db.add(new_review)
        await self.db.flush()

        link = IdentityReviewItemEvent(review_id=new_review.id, event_id=event.id)
        self.db.add(link)

        return new_review
    
    async def resolve_review(
        self,
        review_id: uuid.UUID,
        user_id: uuid.UUID,
        resolution: str,
        note: str | None = None
    ) -> IdentityReviewItem:
        stmt = select(IdentityReviewItem).where(
            IdentityReviewItem.id == review_id,
            IdentityReviewItem.user_id == user_id
        ).with_for_update()
        review = (await self.db.execute(stmt)).scalars().first()
        
        if not review:
            raise ValueError("Review not found or unauthorized")
        
        if review.status in (REVIEW_STATUS_RESOLVED, REVIEW_STATUS_DISMISSED, REVIEW_STATUS_SUPERSEDED):
            return review 

        valid_resolutions = {
            RESOLUTION_ACKNOWLEDGED,
            RESOLUTION_THIS_IS_STILL_MINE,
            RESOLUTION_THIS_IS_NOT_MINE,
            RESOLUTION_EXPECTED_CHANGE,
            RESOLUTION_REQUEST_REVALIDATION,
            RESOLUTION_DISMISS_ALERT,
        }
        if resolution not in valid_resolutions:
            raise ValueError(f"Invalid resolution: {resolution}")

        if resolution in (RESOLUTION_DISMISS_ALERT, RESOLUTION_THIS_IS_NOT_MINE):
            review.status = REVIEW_STATUS_DISMISSED
        elif resolution == RESOLUTION_REQUEST_REVALIDATION:
            # Might keep it in a waiting state, or mark resolved and track revalidation
            review.status = REVIEW_STATUS_RESOLVED 
        else:
            review.status = REVIEW_STATUS_RESOLVED

        review.resolution = resolution
        review.resolution_note = note
        review.reviewed_at = datetime.now(timezone.utc)
        review.reviewed_by_user_id = user_id

        return review
