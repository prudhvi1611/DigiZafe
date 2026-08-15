from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.privacy import (
    AccountDeletePublic,
    AccountDeleteRequest,
    AuditEventPublic,
    ConsentGrantRequest,
    ConsentItem,
    ConsentRevokeRequest,
    CounterfactualPublic,
    EgressEventPublic,
    ExportCreateRequest,
    ExportJobPublic,
    ExportPackageResponse,
    Message,
    NarrativePublic,
    NarrativeRequest,
)
from app.services.privacy.export_service import ExportService
from app.services.privacy.narrative_service import NarrativeService
from app.services.privacy.privacy_service import PrivacyService

router = APIRouter(prefix="/privacy", tags=["privacy"])


def _export(db: AsyncSession = Depends(get_db)) -> ExportService:
    return ExportService(db)


def _privacy(db: AsyncSession = Depends(get_db)) -> PrivacyService:
    return PrivacyService(db)


def _narrative(db: AsyncSession = Depends(get_db)) -> NarrativeService:
    return NarrativeService(db)


# ---------- Export ----------
@router.post("/export", response_model=ExportJobPublic, status_code=201)
async def create_export(
    body: ExportCreateRequest,
    current_user: CurrentUser,
    svc: ExportService = Depends(_export),
):
    """GDPR/CCPA-style machine-readable personal data export (JSON)."""
    job = await svc.start_export(
        current_user.id,
        include_audit=body.include_audit,
        include_egress=body.include_egress,
    )
    return ExportJobPublic.model_validate(job)


@router.get("/export/{job_id}", response_model=ExportPackageResponse)
async def get_export(
    job_id: UUID,
    current_user: CurrentUser,
    svc: ExportService = Depends(_export),
):
    job = await svc.get_export(current_user.id, job_id)
    return ExportPackageResponse(
        job=ExportJobPublic.model_validate(job),
        package=job.package if job.status == "ready" else None,
    )


# ---------- Consent center ----------
@router.get("/consent", response_model=list[ConsentItem])
async def list_consent(current_user: CurrentUser, svc: PrivacyService = Depends(_privacy)):
    rows = await svc.list_consent(current_user.id)
    return [ConsentItem.model_validate(r) for r in rows]


@router.post("/consent", response_model=Message)
async def grant_consent(
    body: ConsentGrantRequest,
    current_user: CurrentUser,
    svc: PrivacyService = Depends(_privacy),
):
    return await svc.grant(current_user.id, body.purpose, body.scope, body.details)


@router.post("/consent/revoke", response_model=Message)
async def revoke_consent(
    body: ConsentRevokeRequest,
    current_user: CurrentUser,
    svc: PrivacyService = Depends(_privacy),
):
    return await svc.revoke(current_user.id, body.purpose)


# ---------- Audit + egress transparency ----------
@router.get("/audit", response_model=list[AuditEventPublic])
async def my_audit(
    current_user: CurrentUser,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: PrivacyService = Depends(_privacy),
):
    rows = await svc.list_audit(current_user.id, limit=limit, offset=offset)
    return [
        AuditEventPublic(
            id=r.id,
            action=r.action,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            details=r.details,
            created_at=r.created_at,
            correlation_id=r.correlation_id,
        )
        for r in rows
    ]


@router.get("/egress", response_model=list[EgressEventPublic])
async def my_egress(
    current_user: CurrentUser,
    limit: int = Query(100, ge=1, le=500),
    svc: PrivacyService = Depends(_privacy),
):
    rows = await svc.list_egress(current_user.id, limit=limit)
    return [
        EgressEventPublic(
            id=r.id,
            purpose=r.purpose,
            destination_host=r.destination_host,
            method=r.method,
            status_code=r.status_code,
            success=r.success,
            summary=r.summary,
            created_at=r.created_at,
        )
        for r in rows
    ]


# ---------- Erasure ----------
@router.post("/account/delete", response_model=AccountDeletePublic)
async def request_delete(
    body: AccountDeleteRequest,
    current_user: CurrentUser,
    svc: PrivacyService = Depends(_privacy),
):
    """
    Right to erasure. Schedules crypto-shred + purge after grace period
    (or immediate in development when allowed).
    """
    req = await svc.request_deletion(
        current_user.id, body.confirm_phrase, immediate=body.immediate
    )
    return AccountDeletePublic.model_validate(req)


@router.post("/account/delete/{req_id}/cancel", response_model=AccountDeletePublic)
async def cancel_delete(
    req_id: UUID,
    current_user: CurrentUser,
    svc: PrivacyService = Depends(_privacy),
):
    req = await svc.cancel_deletion(current_user.id, req_id)
    return AccountDeletePublic.model_validate(req)


# ---------- Explain ----------
@router.post("/narrative", response_model=NarrativePublic)
async def generate_narrative(
    body: NarrativeRequest,
    current_user: CurrentUser,
    svc: NarrativeService = Depends(_narrative),
):
    """Grounded exposure briefing (Ollama if available; deterministic fallback)."""
    data = await svc.generate(
        current_user.id,
        identifier_id=body.identifier_id,
        score_snapshot_id=body.score_snapshot_id,
        prefer_ollama=body.prefer_ollama,
        persist=body.persist,
    )
    return NarrativePublic.model_validate(data)


@router.get("/narrative/latest", response_model=NarrativePublic)
async def latest_narrative(
    current_user: CurrentUser,
    identifier_id: UUID | None = None,
    svc: NarrativeService = Depends(_narrative),
):
    await svc._set_rls(current_user.id)
    row = await svc.repo.latest_narrative(current_user.id, identifier_id)
    if not row:
        raise HTTPException(status_code=404, detail="No narrative yet")  # noqa: F821
    return NarrativePublic.model_validate(row)


@router.get("/counterfactuals", response_model=CounterfactualPublic)
async def counterfactuals(
    current_user: CurrentUser,
    identifier_id: UUID | None = None,
    snapshot_id: UUID | None = None,
    svc: NarrativeService = Depends(_narrative),
):
    data = await svc.get_counterfactuals(
        current_user.id, identifier_id=identifier_id, snapshot_id=snapshot_id
    )
    return CounterfactualPublic.model_validate(data)

