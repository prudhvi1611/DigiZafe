"""Celery tasks for discovery — pass IDs only, never ORM objects."""
from __future__ import annotations

import asyncio
import uuid

from app.core.logging import get_logger
from app.worker import celery_app

logger = get_logger(__name__)


def _run_async(coro):
    """Run async service code inside sync Celery worker."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # nested — create new loop in thread (rare)
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _execute_scan_async(scan_id: str) -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.discovery_service import DiscoveryService

    async with AsyncSessionLocal() as session:
        svc = DiscoveryService(session)
        try:
            await svc.execute_scan(uuid.UUID(scan_id))
        except Exception:
            logger.exception("execute_scan_failed", scan_id=scan_id)
            await session.rollback()
            raise
        else:
            # commits happen inside service; ensure clean
            try:
                await session.commit()
            except Exception:
                pass


async def _reconcile_async() -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.discovery_service import DiscoveryService

    async with AsyncSessionLocal() as session:
        svc = DiscoveryService(session)
        return await svc.reconcile()


@celery_app.task(name="app.tasks.discovery_tasks.execute_scan_task", bind=True, max_retries=2)
def execute_scan_task(self, scan_id: str) -> str:
    logger.info("execute_scan_task_start", scan_id=scan_id)
    _run_async(_execute_scan_async(scan_id))
    return f"done:{scan_id}"


@celery_app.task(name="app.tasks.discovery_tasks.reconcile_scans_task")
def reconcile_scans_task() -> dict:
    logger.info("reconcile_scans_task_start")
    result = _run_async(_reconcile_async())
    return result or {}
