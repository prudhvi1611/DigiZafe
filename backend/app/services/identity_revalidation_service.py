import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.core.config import get_settings
from app.models.temporal import IdentityReviewItem
from app.models.identity_anchor import IdentityAlias
from app.services.discovery.connectors.capability_registry import ConnectorCapability
from app.services.discovery.orchestration_service import ConnectorOrchestrationService


class IdentityRevalidationService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.config = get_settings()
        self.orchestration_service = ConnectorOrchestrationService(db, redis)

    async def request_revalidation_for_review(
        self,
        user_id: uuid.UUID,
        review_id: uuid.UUID,
        is_automatic: bool = False
    ):
        stmt = select(IdentityReviewItem).where(
            IdentityReviewItem.id == review_id,
            IdentityReviewItem.user_id == user_id
        )
        review = (await self.db.execute(stmt)).scalars().first()
        
        if not review:
            raise ValueError("Review not found or unauthorized")

        if is_automatic and not self.config.feature_automatic_revalidation:
            return None

        capabilities = [ConnectorCapability.PROFILE_LOOKUP]

        alias_stmt = select(IdentityAlias).where(
            IdentityAlias.anchor_id == review.anchor_id,
            IdentityAlias.status == "active"
        )
        aliases = list((await self.db.execute(alias_stmt)).scalars().all())
        
        if review.candidate_profile_id:
            from app.models.candidate_profile import CandidateProfile
            cp_stmt = select(CandidateProfile).where(CandidateProfile.id == review.candidate_profile_id)
            cp = (await self.db.execute(cp_stmt)).scalars().first()
            if cp:
                aliases = [a for a in aliases if a.id == cp.source_input_id]

        if is_automatic:
            # Check cooldown logic using redis
            cooldown_key = f"reval_cooldown:{user_id}:{review.anchor_id}"
            if await self.redis.get(cooldown_key):
                return None
            
            # Set cooldown
            cooldown_seconds = self.config.automatic_revalidation_cooldown_hours * 3600
            await self.redis.setex(cooldown_key, cooldown_seconds, "1")

        try:
            run, created = await self.orchestration_service.create_orchestration_run(
                user_id=user_id,
                anchor_id=review.anchor_id,
                aliases=aliases,
                requested_capabilities=capabilities,
                force_refresh=True,
                purpose="temporal_revalidation"
            )

            if created:
                await self.orchestration_service.plan_run(run.id, aliases, capabilities)
                
            return run
        except ValueError as e:
            if is_automatic:
                return None
            raise e
