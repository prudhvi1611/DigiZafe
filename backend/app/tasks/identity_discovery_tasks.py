import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy import update, select
from celery import shared_task
from app.core.database import AsyncSessionLocal
from app.models.candidate_profile import CandidateDiscoveryRun, CandidateProfile
from app.models.identity_anchor import IdentityAlias
from app.services.candidate_discovery_service import CandidateDiscoveryService
from app.connectors.maigret_adapter import MaigretAdapter
from app.connectors.sdk.redis_clients import get_broker_redis
from app.services.discovery.connector_budget_service import ConnectorBudgetService
from app.models.orchestration import ConnectorExecutionPlanItem
from app.models.connector_certification import ConnectorCertificationRecord
import asyncio

logger = logging.getLogger(__name__)

async def _run_maigret_discovery_async(run_id: uuid.UUID, input_ids: list[uuid.UUID] | None):
    async with AsyncSessionLocal() as session:
        run_stmt = select(CandidateDiscoveryRun).where(CandidateDiscoveryRun.id == run_id)
        result = await session.execute(run_stmt)
        run = result.scalars().first()
        
        if not run:
            logger.error(f"Discovery run {run_id} not found")
            return

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        await session.commit()

        service = CandidateDiscoveryService(session)
        inputs = await service.get_eligible_inputs(run.user_id, run.anchor_id, input_ids)

        if not inputs:
            run.status = "failed"
            run.error_code = "invalid_input"
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return

        adapter = MaigretAdapter()
        total_candidates = 0
        has_errors = False
        
        redis_client = await get_broker_redis()
        budget_svc = ConnectorBudgetService(redis_client)
        
        for identity_input in inputs:
            username = identity_input.value_canonical
            
            # Find the plan item for this execution
            plan_stmt = select(ConnectorExecutionPlanItem).where(
                ConnectorExecutionPlanItem.discovery_run_id == run.id,
                ConnectorExecutionPlanItem.input_alias_id == identity_input.id,
                ConnectorExecutionPlanItem.connector_type == "maigret"
            )
            plan_item = (await session.execute(plan_stmt)).scalars().first()
            
            # Fetch active certification for execution context
            cert_stmt = select(ConnectorCertificationRecord).where(
                ConnectorCertificationRecord.connector_type == "maigret",
                ConnectorCertificationRecord.availability.in_(["available", "test_only", "installed_unverified"])
            ).order_by(ConnectorCertificationRecord.created_at.desc())
            cert_record = (await session.execute(cert_stmt)).scalars().first()

            if plan_item:
                plan_item.execution_status = "running"
                if cert_record:
                    plan_item.certification_id = cert_record.id
                    plan_item.runtime_fingerprint = cert_record.runtime_fingerprint
                    plan_item.execution_mode = "mock" if cert_record.availability == "test_only" else "live"
                await session.commit()
            
            lease_id = str(uuid.uuid4())
            acquired = await budget_svc.acquire_connector_lease("maigret", lease_id)
            if not acquired:
                logger.error(f"Failed to acquire maigret concurrency lease for {username} (fail closed)")
                has_errors = True
                if plan_item:
                    plan_item.execution_status = "failed"
                    plan_item.outcome = "failure"
                    plan_item.error_category = "concurrency_limit_exceeded"
                    await session.commit()
                continue
                
            try:
                result = adapter.run_discovery(username, timeout=120)
            finally:
                await budget_svc.release_connector_lease("maigret", lease_id)
            
            if result.get("error"):
                logger.error(f"Maigret failed for {username}: {result}")
                has_errors = True
                if plan_item:
                    plan_item.execution_status = "failed"
                    plan_item.outcome = "failure"
                    plan_item.error_category = result.get("error_category", "unknown_error")
                    plan_item.timeout_occurred = result.get("error_category") == "timeout"
                    await session.commit()
                continue
            
            data = result.get("data", {})
            
            if plan_item:
                plan_item.execution_status = "completed"
                plan_item.outcome = "success"
                plan_item.normalized_result_count = 1 if data else 0
                await session.commit()

            if not data:
                continue

            count = await service.persist_candidates(
                run, 
                identity_input, 
                data, 
                execution_mode=plan_item.execution_mode if plan_item else "mock",
                certification_id=cert_record.id if cert_record else None,
                runtime_fingerprint=cert_record.runtime_fingerprint if cert_record else None,
                adapter_version=cert_record.adapter_version if cert_record else None,
                runtime_version=cert_record.runtime_version if cert_record else None
            )
            total_candidates += count

        run.candidate_count = total_candidates
        run.completed_at = datetime.now(timezone.utc)
        run.status = "partially_completed" if has_errors else "completed"
        
        await session.commit()

@shared_task(queue="osint_discovery", bind=True, max_retries=1)
def run_maigret_discovery(self, run_id_str: str, input_ids_str: list[str] | None = None):
    """
    Celery task to run maigret discovery asynchronously.
    """
    run_id = uuid.UUID(run_id_str)
    input_ids = [uuid.UUID(i) for i in input_ids_str] if input_ids_str else None
    
    # Run the async loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_run_maigret_discovery_async(run_id, input_ids))


async def _run_osintgram_discovery_async(run_id: uuid.UUID):
    async with AsyncSessionLocal() as session:
        service = CandidateDiscoveryService(session)
        await service.execute_osintgram_run(run_id)

@shared_task(queue="osint_connectors", bind=True, max_retries=1)
def run_osintgram_discovery(self, run_id_str: str):
    run_id = uuid.UUID(run_id_str)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_run_osintgram_discovery_async(run_id))

async def _trigger_certification_reassessment_async(connector_type: str, runtime_fingerprint: str):
    from app.services.identity_reassessment_coordinator import IdentityReassessmentCoordinator
    async with AsyncSessionLocal() as session:
        coordinator = IdentityReassessmentCoordinator(session)
        await coordinator.process_certification_change(connector_type, runtime_fingerprint)

@shared_task(queue="identity_processing", bind=True, max_retries=3)
def trigger_certification_reassessment(self, connector_type: str, runtime_fingerprint: str):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_trigger_certification_reassessment_async(connector_type, runtime_fingerprint))
