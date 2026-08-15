from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.identity_score import (
    EdgeReviewRequest,
    IdentityEdgePublic,
    IdentityGraphPublic,
)
from app.schemas.identity_anchor import (
    ConfirmedProfileResponse,
    CreateConfirmedProfileRequest,
    CreateIdentityAliasRequest,
    IdentityAliasResponse,
    IdentityAnchorSummaryResponse,
)
from app.services.identity_service import IdentityService
from app.services.identity_anchor_service import IdentityAnchorService
from fastapi import status

router = APIRouter(prefix="/identity", tags=["identity"])


def _svc(db: AsyncSession = Depends(get_db)) -> IdentityService:
    return IdentityService(db)


@router.get("/graph", response_model=IdentityGraphPublic)
async def get_graph(current_user: CurrentUser, svc: IdentityService = Depends(_svc)):
    return await svc.get_graph(current_user.id)


@router.post("/graph/rebuild", response_model=IdentityGraphPublic)
async def rebuild_graph(current_user: CurrentUser, svc: IdentityService = Depends(_svc)):
    """Recompute pairwise deciban/F–S links across the user's identifiers."""
    return await svc.rebuild_graph(current_user.id)


@router.post("/edges/{edge_id}/review", response_model=IdentityEdgePublic)
async def review_edge(
    edge_id: UUID,
    body: EdgeReviewRequest,
    current_user: CurrentUser,
    svc: IdentityService = Depends(_svc),
):
    return await svc.review_edge(current_user.id, edge_id, body.review_status, body.review_note)


def _anchor_svc(db: AsyncSession = Depends(get_db)) -> IdentityAnchorService:
    return IdentityAnchorService(db)


@router.get("/anchor", response_model=IdentityAnchorSummaryResponse)
async def get_identity_anchor(
    current_user: CurrentUser,
    svc: IdentityAnchorService = Depends(_anchor_svc),
) -> IdentityAnchorSummaryResponse:
    """Get the current user's verified identity anchor summary."""
    return await svc.get_anchor_summary(current_user.id)


@router.post("/aliases", response_model=IdentityAliasResponse, status_code=status.HTTP_201_CREATED)
async def add_identity_alias(
    request: CreateIdentityAliasRequest,
    current_user: CurrentUser,
    svc: IdentityAnchorService = Depends(_anchor_svc),
) -> IdentityAliasResponse:
    """Add a user-confirmed alias to the identity anchor."""
    return await svc.add_alias(current_user.id, request)


@router.post("/aliases/{alias_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_identity_alias(
    alias_id: UUID,
    current_user: CurrentUser,
    svc: IdentityAnchorService = Depends(_anchor_svc),
) -> None:
    """Revoke an active alias."""
    await svc.revoke_alias(current_user.id, alias_id)


@router.post("/profiles", response_model=ConfirmedProfileResponse, status_code=status.HTTP_201_CREATED)
async def add_confirmed_profile(
    request: CreateConfirmedProfileRequest,
    current_user: CurrentUser,
    svc: IdentityAnchorService = Depends(_anchor_svc),
) -> ConfirmedProfileResponse:
    """Add a user-confirmed profile URL to the identity anchor."""
    return await svc.add_confirmed_profile(current_user.id, request)


@router.post("/profiles/{profile_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_confirmed_profile(
    profile_id: UUID,
    current_user: CurrentUser,
    svc: IdentityAnchorService = Depends(_anchor_svc),
) -> None:
    """Revoke an active confirmed profile."""
    await svc.revoke_profile(current_user.id, profile_id)
