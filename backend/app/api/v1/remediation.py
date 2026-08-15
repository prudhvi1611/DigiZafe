from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.schemas.remediation import (
    BrokerOptOutStart,
    BrokerStatePublic,
    CaptchaPublic,
    CaptchaSolveRequest,
    ComplaintCreate,
    FreezeItemPublic,
    FreezeItemUpdate,
    GeneratedRequestPublic,
    KnowRequestCreate,
    ManualItemComplete,
    MarkSentRequest,
    RemediationJobPublic,
    VerifyBrokersRequest,
)
from app.services.remediation_service import RemediationService

router = APIRouter(prefix="/remediation", tags=["remediation"])


def _svc(db: AsyncSession = Depends(get_db)) -> RemediationService:
    return RemediationService(db)


@router.get("/brokers")
async def catalog(current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    return await svc.list_brokers_catalog()


@router.get("/state", response_model=list[BrokerStatePublic])
async def broker_state(current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    """AIDR state.json equivalent — per-broker opt-out history."""
    rows = await svc.list_broker_states(current_user.id)
    return [BrokerStatePublic.model_validate(r) for r in rows]


@router.post("/jobs/broker-optout", response_model=RemediationJobPublic, status_code=201)
async def start_optout(
    body: BrokerOptOutStart,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    """
    Start Green broker opt-out job (Playwright in worker).
    Free CAPTCHA path: waiting_captcha → user solves → resume.
    """
    p = body.profile
    job = await svc.start_broker_optout(
        current_user.id,
        identifier_id=body.identifier_id,
        broker_ids=body.broker_ids,
        dry_run=body.dry_run,
        display_name=p.display_name if p else None,
        state=p.state if p else None,
        city=p.city if p else None,
        zip_code=p.zip if p else None,
        recommendation_id=body.recommendation_id,
    )
    return RemediationJobPublic.model_validate(job)


@router.get("/jobs", response_model=list[RemediationJobPublic])
async def list_jobs(current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    rows = await svc.list_jobs(current_user.id)
    # items not always loaded — return without nested if needed
    return [
        RemediationJobPublic.model_validate(r) if getattr(r, "items", None) is not None else RemediationJobPublic(
            id=r.id,
            identifier_id=r.identifier_id,
            job_type=r.job_type,
            status=r.status,
            dry_run=r.dry_run,
            broker_ids=r.broker_ids,
            progress_pct=r.progress_pct,
            message=r.message,
            error=r.error,
            result_summary=r.result_summary,
            deadline_at=r.deadline_at,
            started_at=r.started_at,
            finished_at=r.finished_at,
            created_at=r.created_at,
            items=[],
        )
        for r in rows
    ]


@router.get("/jobs/{job_id}", response_model=RemediationJobPublic)
async def get_job(job_id: UUID, current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    job = await svc.get_job(current_user.id, job_id)
    return RemediationJobPublic.model_validate(job)


@router.post("/jobs/{job_id}/cancel", response_model=RemediationJobPublic)
async def cancel_job(job_id: UUID, current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    job = await svc.cancel_job(current_user.id, job_id)
    return RemediationJobPublic.model_validate(job)


@router.post("/jobs/{job_id}/items/{item_id}/manual", response_model=RemediationJobPublic)
async def complete_manual(
    job_id: UUID,
    item_id: UUID,
    body: ManualItemComplete,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    job = await svc.complete_manual_item(
        current_user.id, job_id, item_id, body.status, body.detail
    )
    return RemediationJobPublic.model_validate(job)


@router.get("/captcha", response_model=list[CaptchaPublic])
async def list_captcha(current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    from app.repositories.remediation_repository import RemediationRepository

    await svc._set_rls(current_user.id)
    rows = await RemediationRepository(svc.session).list_pending_captchas(current_user.id)
    return [CaptchaPublic.model_validate(r) for r in rows]


@router.post("/captcha/{captcha_id}")
async def solve_captcha(
    captcha_id: UUID,
    body: CaptchaSolveRequest,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    return await svc.solve_captcha(
        current_user.id,
        captcha_id,
        action=body.action,
        solution_token=body.solution_token,
    )


@router.get("/freeze", response_model=list[FreezeItemPublic])
async def get_freeze(current_user: CurrentUser, svc: RemediationService = Depends(_svc)):
    rows = await svc.ensure_freeze_checklist(current_user.id)
    return [FreezeItemPublic.model_validate(r) for r in rows]


@router.patch("/freeze/{item_id}", response_model=FreezeItemPublic)
async def patch_freeze(
    item_id: UUID,
    body: FreezeItemUpdate,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    row = await svc.update_freeze(current_user.id, item_id, body.status, body.notes)
    return FreezeItemPublic.model_validate(row)


@router.post("/know", response_model=GeneratedRequestPublic, status_code=201)
async def create_know(
    body: KnowRequestCreate,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    row = await svc.create_know_request(
        current_user.id,
        regime=body.regime,
        recipient_name=body.recipient_name,
        recipient_email=str(body.recipient_email) if body.recipient_email else None,
        identifier_id=body.identifier_id,
        include_deletion=body.include_deletion,
    )
    return GeneratedRequestPublic.model_validate(row)


@router.post("/complaints", response_model=GeneratedRequestPublic, status_code=201)
async def create_complaint(
    body: ComplaintCreate,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    row = await svc.create_complaint(
        current_user.id,
        regime=body.regime,
        recipient_name=body.recipient_name,
        regulator=body.regulator,
        facts=body.facts,
        original_request_id=body.original_request_id,
    )
    return GeneratedRequestPublic.model_validate(row)


@router.get("/requests", response_model=list[GeneratedRequestPublic])
async def list_requests(
    current_user: CurrentUser,
    kind: str | None = None,
    svc: RemediationService = Depends(_svc),
):
    from app.repositories.remediation_repository import RemediationRepository

    await svc._set_rls(current_user.id)
    rows = await RemediationRepository(svc.session).list_generated(current_user.id, kind=kind)
    return [GeneratedRequestPublic.model_validate(r) for r in rows]


@router.post("/requests/{req_id}/mark-sent", response_model=GeneratedRequestPublic)
async def mark_sent(
    req_id: UUID,
    body: MarkSentRequest,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    row = await svc.mark_request_sent(current_user.id, req_id)
    return GeneratedRequestPublic.model_validate(row)


@router.post("/verify")
async def verify(
    body: VerifyBrokersRequest,
    current_user: CurrentUser,
    svc: RemediationService = Depends(_svc),
):
    return await svc.verify_brokers(current_user.id, broker_ids=body.broker_ids)
