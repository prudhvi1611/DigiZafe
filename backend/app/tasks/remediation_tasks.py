from __future__ import annotations

import asyncio
import uuid

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


async def _execute_job_async(job_id: str) -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.remediation_service import RemediationService

    async with AsyncSessionLocal() as session:
        svc = RemediationService(session)
        try:
            await svc.execute_job(uuid.UUID(job_id))
        except Exception:
            logger.exception("remediation_job_failed", job_id=job_id)
            await session.rollback()
            raise


@celery_app.task(
    name="app.tasks.remediation_tasks.execute_remediation_job_task",
    bind=True,
    max_retries=1,
    time_limit=7200,
)
def execute_remediation_job_task(self, job_id: str) -> str:
    logger.info("execute_remediation_job_start", job_id=job_id)
    _run_async(_execute_job_async(job_id))
    return f"done:{job_id}"


@celery_app.task(name="app.tasks.remediation_tasks.update_brokers_task")
def update_brokers_task() -> dict:
    """
    Best-effort refresh of public broker registry notes.
    Full CA SB 362 / Vermont scrape can be expanded; MVP logs intent + clears cache.
    """
    from app.remediation.broker_registry import clear_registry_cache, load_broker_registry

    clear_registry_cache()
    reg = load_broker_registry()
    logger.info(
        "update_brokers_done",
        version=reg.get("registry_version"),
        count=len(reg.get("brokers") or []),
    )
    return {
        "registry_version": reg.get("registry_version"),
        "broker_count": len(reg.get("brokers") or []),
        "note": "MVP: reloaded local Green registry. Extend with CA SB 362 / Vermont free pulls later.",
    }
