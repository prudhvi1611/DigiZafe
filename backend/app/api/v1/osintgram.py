from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any
import uuid

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.candidate_discovery_service import CandidateDiscoveryService
from app.services.discovery.connectors.osintgram_adapter import OSINTgramAdapter
from app.tasks.osint_tasks import execute_osintgram_task
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/status", response_model=dict[str, Any])
async def get_connector_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    adapter = OSINTgramAdapter()
    return {"status": await adapter.check_availability()}

@router.post("/run", response_model=dict[str, Any])
async def launch_osintgram_discovery(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    svc = CandidateDiscoveryService(db)
    
    # Check if OSINTgram is enabled and available
    adapter = OSINTgramAdapter()
    status_str = await adapter.check_availability()
    if status_str != "available":
        raise HTTPException(status_code=400, detail=f"OSINTgram connector is {status_str}")
        
    run = await svc.create_discovery_run(current_user.id)
    if not run:
        raise HTTPException(status_code=400, detail="Cannot create discovery run")
        
    run.source_tool = adapter.CONNECTOR_NAME
    run.source_tool_version = adapter.CONNECTOR_VERSION
    await db.commit()
    
    # Dispatch task
    execute_osintgram_task.delay(str(run.id))
    
    return {"run_id": str(run.id), "status": "queued"}
