import uuid
import logging
from celery import shared_task
from app.core.database import AsyncSessionLocal
from app.services.identity_change_detection_service import IdentityChangeDetectionService
import asyncio

logger = logging.getLogger(__name__)

async def _process_observation_async(observation_id: uuid.UUID):
    async with AsyncSessionLocal() as session:
        service = IdentityChangeDetectionService(session)
        await service.evaluate_observation(observation_id)
        await session.commit()

@shared_task(queue="default", bind=True, max_retries=3)
def process_temporal_observation(self, observation_id_str: str):
    """
    Celery task to evaluate a new provenance observation for temporal changes.
    """
    observation_id = uuid.UUID(observation_id_str)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_process_observation_async(observation_id))
