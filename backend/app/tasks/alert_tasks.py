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


async def _reconcile_async() -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.alert_service import AlertService

    async with AsyncSessionLocal() as session:
        svc = AlertService(session)
        return await svc.reconcile_scheduled()


@celery_app.task(name="app.tasks.alert_tasks.reconcile_alerts_rescans_task")
def reconcile_alerts_rescans_task() -> dict:
    logger.info("reconcile_alerts_rescans_start")
    return _run_async(_reconcile_async()) or {}
