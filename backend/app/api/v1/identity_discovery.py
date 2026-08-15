from uuid import UUID
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import CurrentUser, get_db
from app.services.candidate_discovery_service import CandidateDiscoveryService
from app.tasks.identity_discovery_tasks import run_maigret_discovery
from app.models.candidate_profile import CandidateDiscoveryRun, CandidateProfile
from app.core.config import get_settings
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter(prefix="/identity/discovery", tags=["identity_discovery"])

class StartDiscoveryRequest(BaseModel):
    identity_input_ids: list[UUID] | None = None

class DiscoveryRunResponse(BaseModel):
    id: UUID
    status: str
    input_count: int
    candidate_count: int
    error_code: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CandidateProfileResponse(BaseModel):
    id: UUID
    platform: str
    profile_url: str
    canonical_profile_url: str
    username_observed: str
    candidate_status: str
    source_tool: str
    first_observed_at: datetime
    last_observed_at: datetime
    discovery_run_id: UUID
    model_config = ConfigDict(from_attributes=True)

def _svc(db: AsyncSession = Depends(get_db)) -> CandidateDiscoveryService:
    return CandidateDiscoveryService(db)

@router.post("/orchestrate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def start_orchestrated_discovery(
    body: StartDiscoveryRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    settings = get_settings()
    if not settings.feature_connector_orchestration:
        raise HTTPException(status_code=403, detail="Connector orchestration is disabled")
        
    svc = CandidateDiscoveryService(db)
    anchor = await svc.get_active_anchor(current_user.id)
    if not anchor:
        raise HTTPException(status_code=400, detail="No active identity anchor found.")
        
    aliases = await svc.get_eligible_inputs(current_user.id, anchor.id, body.identity_input_ids)
    if not aliases:
        raise HTTPException(status_code=400, detail="No eligible inputs found")
        
    from app.connectors.sdk.redis_clients import get_cache_redis
    from app.services.discovery.orchestration_service import ConnectorOrchestrationService, OrchestrationDecision
    from app.services.discovery.connectors.registry import ConnectorCapability, ConnectorRegistry
    
    redis = await get_cache_redis()
    orch_svc = ConnectorOrchestrationService(db, redis)
    
    try:
        run, created = await orch_svc.create_orchestration_run(
            user_id=current_user.id,
            anchor_id=anchor.id,
            aliases=list(aliases),
            requested_capabilities=[ConnectorCapability.PROFILE_LOOKUP]
        )
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))
        
    if created:
        plan_items = await orch_svc.plan_run(run, list(aliases))
        
        for item in plan_items:
            if item.decision == OrchestrationDecision.EXECUTE:
                input_ids = [item.input_alias_id] if item.input_alias_id else None
                descriptor = ConnectorRegistry.get_descriptor(item.connector_type)
                adapter_version = descriptor.adapter_version if descriptor else "unknown"
                
                child_run = await svc.create_discovery_run(
                    user_id=current_user.id,
                    input_ids=input_ids,
                    source_tool=item.connector_type,
                    source_tool_version=adapter_version,
                    orchestration_run_id=run.id,
                    plan_item_id=item.id
                )
                if child_run:
                    item.discovery_run_id = child_run.id
                    item.execution_status = "queued"
                    await db.commit()
                    
                    if item.connector_type == "maigret":
                        run_maigret_discovery.delay(str(child_run.id), [str(item.input_alias_id)])
                    elif item.connector_type == "osintgram":
                        from app.tasks.identity_discovery_tasks import run_osintgram_discovery
                        run_osintgram_discovery.delay(str(child_run.id))
                        
    return {"orchestration_run_id": str(run.id), "status": run.status, "planned_count": run.planned_connector_count}

@router.get("/runs", response_model=list[DiscoveryRunResponse])
async def list_discovery_runs(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(CandidateDiscoveryRun).where(CandidateDiscoveryRun.user_id == current_user.id).order_by(CandidateDiscoveryRun.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/runs/{run_id}", response_model=DiscoveryRunResponse)
async def get_discovery_run(
    run_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(CandidateDiscoveryRun).where(
        CandidateDiscoveryRun.id == run_id, 
        CandidateDiscoveryRun.user_id == current_user.id
    )
    result = await db.execute(stmt)
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.get("/orchestration/runs", response_model=list[dict])
async def list_orchestration_runs(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    from app.models.orchestration import IdentityOrchestrationRun
    stmt = select(IdentityOrchestrationRun).where(IdentityOrchestrationRun.user_id == current_user.id).order_by(IdentityOrchestrationRun.created_at.desc())
    result = await db.execute(stmt)
    runs = result.scalars().all()
    return [{"id": str(r.id), "status": r.status, "planned_count": r.planned_connector_count, "completed_count": r.completed_connector_count, "created_at": r.created_at} for r in runs]

@router.get("/orchestration/runs/{run_id}", response_model=dict)
async def get_orchestration_run(
    run_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    from app.models.orchestration import IdentityOrchestrationRun, ConnectorExecutionPlanItem
    stmt = select(IdentityOrchestrationRun).where(
        IdentityOrchestrationRun.id == run_id,
        IdentityOrchestrationRun.user_id == current_user.id
    )
    result = await db.execute(stmt)
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    items_stmt = select(ConnectorExecutionPlanItem).where(ConnectorExecutionPlanItem.orchestration_run_id == run.id)
    items = (await db.execute(items_stmt)).scalars().all()
    
    return {
        "id": str(run.id),
        "status": run.status,
        "planned_count": run.planned_connector_count,
        "completed_count": run.completed_connector_count,
        "created_at": run.created_at,
        "items": [
            {
                "id": str(i.id),
                "connector_type": i.connector_type,
                "decision": i.decision.value if hasattr(i.decision, "value") else str(i.decision),
                "execution_status": i.execution_status
            }
            for i in items
        ]
    }

@router.get("/candidates", response_model=list[CandidateProfileResponse])
async def list_candidates(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(CandidateProfile).where(CandidateProfile.user_id == current_user.id).order_by(CandidateProfile.last_observed_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/candidates/{candidate_id}/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_candidate(
    candidate_id: UUID,
    current_user: CurrentUser,
    svc: CandidateDiscoveryService = Depends(_svc)
):
    confirmed = await svc.confirm_candidate(current_user.id, candidate_id)
    if not confirmed:
        raise HTTPException(status_code=404, detail="Unreviewed candidate not found")
    return None

@router.post("/candidates/{candidate_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_candidate(
    candidate_id: UUID,
    current_user: CurrentUser,
    svc: CandidateDiscoveryService = Depends(_svc)
):
    dismissed = await svc.dismiss_candidate(current_user.id, candidate_id)
    if not dismissed:
        raise HTTPException(status_code=404, detail="Unreviewed candidate not found")
    return None
