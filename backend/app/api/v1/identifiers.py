from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.identifier import (
    ConsentGrant,
    IdentifierCreate,
    IdentifierPublic,
    Message,
    VerificationConfirmRequest,
    VerificationStartResponse,
)
from app.services.consent_service import ConsentService
from app.services.identifier_service import IdentifierService
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/identifiers", tags=["identifiers"])


def _id_svc(db: AsyncSession = Depends(get_db)) -> IdentifierService:
    return IdentifierService(db)


def _ver_svc(db: AsyncSession = Depends(get_db)) -> VerificationService:
    return VerificationService(db)


def _consent_svc(db: AsyncSession = Depends(get_db)) -> ConsentService:
    return ConsentService(db)


@router.get("", response_model=list[IdentifierPublic])
async def list_identifiers(
    current_user: CurrentUser,
    svc: IdentifierService = Depends(_id_svc),
):
    return await svc.list(current_user.id)


@router.post("", response_model=IdentifierPublic, status_code=status.HTTP_201_CREATED)
async def create_identifier(
    body: IdentifierCreate,
    current_user: CurrentUser,
    svc: IdentifierService = Depends(_id_svc),
):
    return await svc.add(current_user.id, body.type, body.value)


@router.get("/{identifier_id}", response_model=IdentifierPublic)
async def get_identifier(
    identifier_id: UUID,
    current_user: CurrentUser,
    svc: IdentifierService = Depends(_id_svc),
):
    return await svc.get(current_user.id, identifier_id)


@router.delete("/{identifier_id}", response_model=Message)
async def delete_identifier(
    identifier_id: UUID,
    current_user: CurrentUser,
    svc: IdentifierService = Depends(_id_svc),
):
    await svc.delete(current_user.id, identifier_id)
    return Message(message="Deleted")


@router.post(
    "/{identifier_id}/verify/start",
    response_model=VerificationStartResponse,
)
async def start_verification(
    identifier_id: UUID,
    current_user: CurrentUser,
    method: str | None = Query(None, description="email_code | dns_txt | github_proof"),
    svc: VerificationService = Depends(_ver_svc),
):
    return await svc.start(current_user.id, identifier_id, method=method)


@router.post("/{identifier_id}/verify/confirm")
async def confirm_verification(
    identifier_id: UUID,
    body: VerificationConfirmRequest,
    current_user: CurrentUser,
    challenge_id: UUID = Query(...),
    svc: VerificationService = Depends(_ver_svc),
):
    return await svc.confirm(
        current_user.id,
        identifier_id,
        challenge_id,
        code=body.code,
    )


@router.post("/{identifier_id}/revalidate")
async def revalidate_identifier(
    identifier_id: UUID,
    current_user: CurrentUser,
    svc: VerificationService = Depends(_ver_svc),
):
    return await svc.revalidate(current_user.id, identifier_id)


@router.post("/consent", response_model=Message)
async def grant_consent(
    body: ConsentGrant,
    current_user: CurrentUser,
    svc: ConsentService = Depends(_consent_svc),
):
    await svc.grant(current_user.id, body.purpose, scope=body.scope, details=body.details)
    return Message(message="Consent recorded")
