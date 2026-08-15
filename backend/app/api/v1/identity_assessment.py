import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import CurrentUser, get_db
from app.models.identity_match_assessment import IdentityMatchAssessment
from app.models.user import User
from app.schemas.identity_assessment import IdentityMatchAssessmentResponse, IdentityEvidence
from app.services.identity_match_engine import IdentityMatchEngine

router = APIRouter(prefix="/identity", tags=["identity_assessment"])

@router.get("/candidates/{candidate_id}/assessment", response_model=IdentityMatchAssessmentResponse)
async def get_candidate_assessment(
    candidate_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(IdentityMatchAssessment).where(
        IdentityMatchAssessment.candidate_profile_id == candidate_id,
        IdentityMatchAssessment.user_id == current_user.id,
        IdentityMatchAssessment.is_current == True
    )
    result = await db.execute(stmt)
    assessment = result.scalars().first()
    
    if not assessment:
        # If there's no assessment yet, calculate it (lazy evaluation)
        engine = IdentityMatchEngine(db)
        try:
            assessment = await engine.assess_candidate(current_user.id, candidate_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
            
    return assessment

@router.post("/candidates/{candidate_id}/assessment/recalculate", response_model=IdentityMatchAssessmentResponse)
async def recalculate_candidate_assessment(
    candidate_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    engine = IdentityMatchEngine(db)
    try:
        assessment = await engine.assess_candidate(current_user.id, candidate_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    return assessment

@router.get("/candidates/{candidate_id}/evidence", response_model=list[IdentityEvidence])
async def get_candidate_evidence(
    candidate_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(IdentityMatchAssessment).where(
        IdentityMatchAssessment.candidate_profile_id == candidate_id,
        IdentityMatchAssessment.user_id == current_user.id,
        IdentityMatchAssessment.is_current == True
    )
    result = await db.execute(stmt)
    assessment = result.scalars().first()
    
    if not assessment:
        raise HTTPException(status_code=404, detail="No assessment found")
        
    return assessment.evidence_snapshot
