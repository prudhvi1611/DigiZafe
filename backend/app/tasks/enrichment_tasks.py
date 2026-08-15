import uuid
import asyncio
import logging

from app.worker import celery_app
from app.core.database import get_db
from app.services.avatar_similarity_service import AvatarSimilarityService

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.enrichment_tasks.enrich_avatar_task")
def enrich_avatar_task(
    user_id_str: str,
    source_url: str,
    provenance: dict,
    candidate_id_str: str | None = None,
    confirmed_profile_id_str: str | None = None
) -> None:
    """
    Background task to fetch and fingerprint an avatar image safely on the identity_enrichment queue.
    """
    async def run():
        async for session in get_db():
            svc = AvatarSimilarityService(session)
            
            user_id = uuid.UUID(user_id_str)
            candidate_id = uuid.UUID(candidate_id_str) if candidate_id_str else None
            conf_id = uuid.UUID(confirmed_profile_id_str) if confirmed_profile_id_str else None
            
            await svc.fetch_and_fingerprint(
                user_id=user_id,
                candidate_id=candidate_id,
                confirmed_profile_id=conf_id,
                source_url=source_url,
                provenance=provenance
            )
            await session.commit()
            
    asyncio.run(run())

@celery_app.task(name="app.tasks.enrichment_tasks.sync_cluster_task")
def sync_cluster_task(anchor_id_str: str, user_id_str: str) -> None:
    async def run():
        async for session in get_db():
            from app.services.identity_cluster_service import IdentityClusterService
            svc = IdentityClusterService(session)
            await svc.sync_clusters(uuid.UUID(anchor_id_str), uuid.UUID(user_id_str))
            await session.commit()
            
    asyncio.run(run())

@celery_app.task(name="app.tasks.enrichment_tasks.extract_cross_links_task")
def extract_cross_links_task(user_id_str: str, candidate_id_str: str, target_url: str, source: str) -> None:
    async def run():
        async for session in get_db():
            from app.services.cross_link_evidence_service import CrossLinkEvidenceService
            svc = CrossLinkEvidenceService(session)
            await svc.record_observation(
                user_id=uuid.UUID(user_id_str),
                source_entity_id=uuid.UUID(candidate_id_str),
                source_entity_type="candidate_profile",
                target_url=target_url,
                observation_source=source
            )
            await session.commit()
            
    asyncio.run(run())
