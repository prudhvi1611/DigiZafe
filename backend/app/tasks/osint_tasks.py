import asyncio
import logging
import uuid
from typing import Any

from app.worker import celery_app
from app.core.database import AsyncSessionLocal
from app.services.candidate_discovery_service import CandidateDiscoveryService

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.osint_tasks.execute_osintgram_task")
def execute_osintgram_task(run_id_str: str) -> None:
    """
    Background task to execute OSINTgram connector on the osint_connectors queue.
    Receives only the run_id string; reads configuration securely inside the worker.
    """
    async def run():
        async with AsyncSessionLocal() as session:
            svc = CandidateDiscoveryService(session)
            await svc.execute_osintgram_run(uuid.UUID(run_id_str))
            await session.commit()
            
    asyncio.run(run())
