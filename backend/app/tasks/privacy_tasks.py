from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.worker import celery_app

logger = get_logger(__name__)


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _process_deletions() -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.privacy.privacy_service import PrivacyService

    async with AsyncSessionLocal() as session:
        svc = PrivacyService(session)
        return await svc.process_due_deletions()


@celery_app.task(name="app.tasks.privacy_tasks.process_account_deletions_task")
def process_account_deletions_task() -> dict:
    logger.info("process_account_deletions_start")
    return _run_async(_process_deletions()) or {}
