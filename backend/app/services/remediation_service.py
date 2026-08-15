from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.remediation_profile import build_profile_from_identifiers
from app.domain.remediation_states import (
    BrokerOptOutStatus,
    RemediationJobStatus,
    is_fresh_optout,
    is_terminal_job,
)
from app.remediation.broker_registry import freeze_targets, get_broker, list_green_brokers
from app.remediation.generators.templates import generate_complaint, generate_right_to_know
from app.remediation.runners.playwright_runner import PlaywrightBrokerRunner
from app.repositories.identifier_repository import IdentifierRepository
from app.repositories.remediation_repository import RemediationRepository
from app.services.audit_service import AuditService
from app.services.consent_service import ConsentService

logger = get_logger(__name__)


class RemediationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RemediationRepository(session)
        self.identifiers = IdentifierRepository(session)
        self.audit = AuditService(session)
        self.consent = ConsentService(session)
        self.settings = get_settings()
        self.runner = PlaywrightBrokerRunner()

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def _require_verified_identifier(self, user_id: uuid.UUID, identifier_id: uuid.UUID):
        row = await self.identifiers.get(identifier_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Identifier not found")
        if not row.is_verified:
            raise HTTPException(status_code=403, detail="G1: identifier must be verified before remediation")
        return row

    async def start_broker_optout(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID,
        broker_ids: list[str] | None,
        dry_run: bool = False,
        display_name: str | None = None,
        state: str | None = None,
        city: str | None = None,
        zip_code: str | None = None,
        recommendation_id: uuid.UUID | None = None,
    ):
        if not self.settings.feature_remediation:
            raise HTTPException(status_code=503, detail="Remediation disabled")

        await self._set_rls(user_id)
        ident = await self._require_verified_identifier(user_id, identifier_id)

        active = await self.repo.count_active_jobs(user_id)
        if active >= self.settings.broker_max_concurrent_jobs_per_user:
            raise HTTPException(status_code=429, detail="Max concurrent remediation jobs reached")

        await self.consent.ensure_consent(
            user_id,
            purpose="remediation.broker_optout",
            auto_grant=True,
            scope=str(identifier_id),
        )

        greens = list_green_brokers(enabled_only=True)
        if broker_ids:
            selected = [b for b in greens if b["id"] in set(broker_ids)]
        else:
            selected = greens
        if not selected:
            raise HTTPException(status_code=400, detail="No Green brokers selected")

        idents = await self.identifiers.list_for_user(user_id)
        profile = build_profile_from_identifiers(
            [
                {
                    "type": i.type,
                    "value_canonical": i.value_canonical,
                    "is_verified": i.is_verified,
                }
                for i in idents
            ],
            display_name=display_name,
            state=state,
            city=city,
            zip_code=zip_code,
        )
        if not profile.email and ident.type == "email":
            profile.email = ident.value_canonical
        if not profile.email:
            raise HTTPException(
                status_code=400,
                detail="Verified email required on account for broker opt-out forms",
            )

        deadline = datetime.now(UTC) + timedelta(
            minutes=self.settings.broker_job_deadline_minutes
        )
        job = await self.repo.create_job(
            user_id=user_id,
            identifier_id=identifier_id,
            job_type="broker_optout",
            broker_ids=[b["id"] for b in selected],
            deadline_at=deadline,
            dry_run=dry_run,
            recommendation_id=recommendation_id,
            profile_meta={
                "profile_safe": profile.to_safe_dict(),
                # Worker reloads identifiers; store non-secret profile hints only
                "display_name": display_name,
                "state": state,
                "city": city,
                "zip": zip_code,
            },
            items=[(b["id"], b["name"]) for b in selected],
        )
        await self.audit.log(
            "remediation.job_created",
            user_id=user_id,
            resource_type="remediation_job",
            resource_id=str(job.id),
            details={"brokers": [b["id"] for b in selected], "dry_run": dry_run},
        )
        await self.session.commit()

        from app.tasks.remediation_tasks import execute_remediation_job_task

        execute_remediation_job_task.delay(str(job.id))
        return await self.repo.get_job(job.id, user_id)

    async def get_job(self, user_id: uuid.UUID, job_id: uuid.UUID):
        await self._set_rls(user_id)
        job = await self.repo.get_job(job_id, user_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    async def list_jobs(self, user_id: uuid.UUID):
        await self._set_rls(user_id)
        return await self.repo.list_jobs(user_id)

    async def list_broker_states(self, user_id: uuid.UUID):
        await self._set_rls(user_id)
        return await self.repo.list_states(user_id)

    async def cancel_job(self, user_id: uuid.UUID, job_id: uuid.UUID):
        await self._set_rls(user_id)
        job = await self.repo.get_job(job_id, user_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if is_terminal_job(job.status):
            raise HTTPException(status_code=400, detail="Job already terminal")
        await self.repo.set_job_status(job, RemediationJobStatus.CANCELLED.value, message="Cancelled by user")
        for item in job.items or []:
            if item.status in {
                BrokerOptOutStatus.PENDING.value,
                BrokerOptOutStatus.RUNNING.value,
                BrokerOptOutStatus.CAPTCHA_NEEDED.value,
            }:
                await self.repo.set_item_status(item, BrokerOptOutStatus.CANCELLED.value)
        await self.session.commit()
        return job

    # ---------- Worker ----------
    async def execute_job(self, job_id: uuid.UUID) -> None:
        job = await self.repo.get_job_internal(job_id)
        if not job:
            return
        await self._set_rls(job.user_id)

        if is_terminal_job(job.status) or job.status == RemediationJobStatus.CANCELLED.value:
            return

        now = datetime.now(UTC)
        if job.deadline_at < now:
            await self.repo.set_job_status(
                job, RemediationJobStatus.TIMED_OUT.value, message="Deadline exceeded", error="deadline"
            )
            await self.session.commit()
            return

        await self.repo.set_job_status(job, RemediationJobStatus.RUNNING.value, message="Running brokers")
        await self.session.commit()

        job = await self.repo.get_job_internal(job_id)
        assert job

        # Rebuild profile from DB identifiers
        idents = await self.identifiers.list_for_user(job.user_id)
        pm = job.profile_meta or {}
        profile = build_profile_from_identifiers(
            [
                {"type": i.type, "value_canonical": i.value_canonical, "is_verified": i.is_verified}
                for i in idents
            ],
            display_name=pm.get("display_name"),
            state=pm.get("state"),
            city=pm.get("city"),
            zip_code=pm.get("zip"),
        )

        for item in list(job.items or []):
            await self.session.refresh(job)
            if job.status == RemediationJobStatus.CANCELLED.value:
                break
            if job.deadline_at < datetime.now(UTC):
                await self.repo.set_job_status(job, RemediationJobStatus.TIMED_OUT.value, message="Deadline")
                break
            if item.status != BrokerOptOutStatus.PENDING.value:
                continue

            broker = get_broker(item.broker_id)
            if not broker:
                await self.repo.set_item_status(
                    item, BrokerOptOutStatus.ERROR.value, error="unknown_broker"
                )
                await self.repo.recompute_job_progress(job)
                await self.session.commit()
                continue

            # Fresh skip (AIDR state.json)
            st = await self.repo.get_state(job.user_id, item.broker_id)
            if st and st.last_success_at:
                if is_fresh_optout(
                    st.last_success_at.isoformat(),
                    self.settings.broker_optout_recheck_days,
                ):
                    await self.repo.set_item_status(
                        item,
                        BrokerOptOutStatus.SKIPPED_FRESH.value,
                        skip_reason="fresh",
                        detail=f"Last success {st.last_success_at.isoformat()}",
                    )
                    await self.repo.recompute_job_progress(job)
                    await self.session.commit()
                    continue

            await self.repo.set_item_status(item, BrokerOptOutStatus.RUNNING.value)
            await self.session.commit()

            result = await self.runner.run_broker(
                broker,
                profile,
                dry_run=job.dry_run,
                user_scope=str(job.user_id),
            )
            status = result.status
            success = status == BrokerOptOutStatus.SUBMITTED.value and not job.dry_run

            if status == BrokerOptOutStatus.CAPTCHA_NEEDED.value:
                cap = await self.repo.create_captcha(
                    user_id=job.user_id,
                    job_id=job.id,
                    job_item_id=item.id,
                    broker_id=item.broker_id,
                    page_url=result.open_url or broker.get("opt_out_url"),
                    captcha_type=result.captcha_type or "unknown",
                    sitekey=result.sitekey,
                    instructions=(
                        f"Open {result.open_url or broker.get('opt_out_url')} and complete the CAPTCHA / form. "
                        "Then mark manual_done or submit solution_token if applicable."
                    ),
                    ttl_hours=self.settings.captcha_queue_ttl_hours,
                )
                await self.repo.set_item_status(
                    item,
                    BrokerOptOutStatus.CAPTCHA_NEEDED.value,
                    detail=result.detail,
                    result_meta={**result.to_dict(), "captcha_id": str(cap.id)},
                )
                await self.repo.set_job_status(
                    job,
                    RemediationJobStatus.WAITING_CAPTCHA.value,
                    message="Waiting for CAPTCHA / manual action",
                )
                await self.repo.upsert_state(
                    user_id=job.user_id,
                    broker_id=item.broker_id,
                    broker_name=item.broker_name,
                    status=BrokerOptOutStatus.CAPTCHA_NEEDED.value,
                    identifier_id=job.identifier_id,
                    detail=result.detail,
                    meta=result.to_dict(),
                )
                await self.repo.recompute_job_progress(job)
                await self.session.commit()
                continue  # process other brokers; job may stay waiting_captcha

            if status == BrokerOptOutStatus.MANUAL_NEEDED.value:
                await self.repo.set_item_status(
                    item,
                    BrokerOptOutStatus.MANUAL_NEEDED.value,
                    detail=result.detail,
                    result_meta=result.to_dict(),
                )
                await self.repo.upsert_state(
                    user_id=job.user_id,
                    broker_id=item.broker_id,
                    broker_name=item.broker_name,
                    status=BrokerOptOutStatus.MANUAL_NEEDED.value,
                    identifier_id=job.identifier_id,
                    detail=result.detail,
                    meta=result.to_dict(),
                )
            else:
                await self.repo.set_item_status(
                    item,
                    status,
                    detail=result.detail,
                    error=result.detail if status == BrokerOptOutStatus.ERROR.value else None,
                    result_meta=result.to_dict(),
                )
                await self.repo.upsert_state(
                    user_id=job.user_id,
                    broker_id=item.broker_id,
                    broker_name=item.broker_name,
                    status=status,
                    identifier_id=job.identifier_id,
                    detail=result.detail,
                    meta=result.to_dict(),
                    success=success,
                )

                # Optional verify loop
                if (
                    success
                    and self.settings.remediation_verify_after_submit
                    and not job.dry_run
                ):
                    v = await self.runner.verify_not_listed(broker, profile, user_scope=str(job.user_id))
                    await self.repo.upsert_state(
                        user_id=job.user_id,
                        broker_id=item.broker_id,
                        broker_name=item.broker_name,
                        status=v.status,
                        identifier_id=job.identifier_id,
                        detail=v.detail,
                        meta=v.to_dict(),
                        success=True,
                        verified=v.status == BrokerOptOutStatus.VERIFIED_REMOVED.value,
                    )
                    await self.repo.set_item_status(
                        item,
                        v.status,
                        detail=v.detail,
                        result_meta={**(item.result_meta or {}), "verify": v.to_dict()},
                    )

            await self.consent.record_egress(
                purpose="remediation.broker_optout",
                destination_host=(broker.get("opt_out_url") or "")[:255],
                method="BROWSER",
                success=success or status in {
                    BrokerOptOutStatus.SKIPPED_FRESH.value,
                    BrokerOptOutStatus.NOT_LISTED.value,
                },
                user_id=job.user_id,
                identifier_id=job.identifier_id,
                summary={"broker_id": item.broker_id, "status": status, "dry_run": job.dry_run},
            )
            await self.repo.recompute_job_progress(job)
            await self.session.commit()

        # Finalize if no waiting items
        job = await self.repo.get_job_internal(job_id)
        if not job or is_terminal_job(job.status):
            return
        items = job.items or []
        waiting = [
            i
            for i in items
            if i.status
            in {
                BrokerOptOutStatus.CAPTCHA_NEEDED.value,
                BrokerOptOutStatus.AWAITING_EMAIL_CONFIRM.value,
                BrokerOptOutStatus.MANUAL_NEEDED.value,
                BrokerOptOutStatus.PENDING.value,
                BrokerOptOutStatus.RUNNING.value,
            }
        ]
        if waiting:
            # If only manual/captcha left, leave waiting status
            if any(i.status == BrokerOptOutStatus.CAPTCHA_NEEDED.value for i in waiting):
                await self.repo.set_job_status(
                    job, RemediationJobStatus.WAITING_CAPTCHA.value, message="Waiting CAPTCHA/manual"
                )
            elif any(i.status == BrokerOptOutStatus.MANUAL_NEEDED.value for i in waiting):
                await self.repo.set_job_status(
                    job, RemediationJobStatus.WAITING_MANUAL.value, message="Waiting manual"
                )
            await self.session.commit()
            return

        submitted = sum(
            1
            for i in items
            if i.status
            in {
                BrokerOptOutStatus.SUBMITTED.value,
                BrokerOptOutStatus.VERIFIED_REMOVED.value,
                BrokerOptOutStatus.SKIPPED_FRESH.value,
                BrokerOptOutStatus.NOT_LISTED.value,
            }
        )
        errors = sum(1 for i in items if i.status in {BrokerOptOutStatus.ERROR.value, BrokerOptOutStatus.DEAD.value})
        if errors and submitted:
            final = RemediationJobStatus.PARTIAL.value
        elif errors and not submitted:
            final = RemediationJobStatus.FAILED.value
        else:
            final = RemediationJobStatus.COMPLETED.value

        summary = {
            "submitted_or_ok": submitted,
            "errors": errors,
            "total": len(items),
            "attribution": "Remediation strategies inspired by AIDR (auto-identity-remove)",
        }
        await self.repo.set_job_status(
            job, final, message=f"Finished: {final}", result_summary=summary, progress_pct=100.0
        )
        await self.audit.log(
            "remediation.job_finished",
            user_id=job.user_id,
            resource_type="remediation_job",
            resource_id=str(job.id),
            details=summary,
        )
        await self.session.commit()

        # Closed-loop re-score
        if self.settings.remediation_auto_rescore and not job.dry_run:
            try:
                from app.services.recommendation_service import RecommendationService
                from app.services.scoring_service import ScoringService

                scoring = ScoringService(self.session)
                await scoring.compute(
                    job.user_id,
                    identifier_id=job.identifier_id,
                    persist=True,
                    trigger="post_remediation",
                )
                recs = RecommendationService(self.session)
                await recs.generate(job.user_id, identifier_id=job.identifier_id, persist=True)
            except Exception:
                logger.exception("post_remediation_rescore_failed", job_id=str(job.id))

    async def solve_captcha(
        self,
        user_id: uuid.UUID,
        captcha_id: uuid.UUID,
        *,
        action: str,
        solution_token: str | None = None,
    ):
        await self._set_rls(user_id)
        cap = await self.repo.get_captcha(captcha_id, user_id)
        if not cap:
            raise HTTPException(status_code=404, detail="Captcha item not found")
        if cap.status != "pending":
            raise HTTPException(status_code=400, detail="Captcha not pending")
        if cap.expires_at < datetime.now(UTC):
            cap.status = "expired"
            await self.session.flush()
            await self.session.commit()
            raise HTTPException(status_code=400, detail="Captcha expired")

        if action == "skip":
            cap.status = "skipped"
            await self.session.flush()
            await self.session.commit()
            return {"message": "Skipped"}

        cap.status = "solved"
        cap.solution_token = solution_token
        cap.solved_at = datetime.now(UTC)
        await self.session.flush()

        # Resume item as pending for re-run with token (token stored on captcha row)
        job = await self.repo.get_job(cap.job_id, user_id)
        if job and cap.job_item_id:
            for item in job.items or []:
                if item.id == cap.job_item_id:
                    # Re-queue item
                    item.status = BrokerOptOutStatus.PENDING.value
                    item.finished_at = None
                    if solution_token:
                        item.result_meta = {**(item.result_meta or {}), "captcha_token_present": True}
                    break
            await self.repo.set_job_status(job, RemediationJobStatus.PENDING.value, message="Resuming after captcha")
            await self.session.commit()
            from app.tasks.remediation_tasks import execute_remediation_job_task

            execute_remediation_job_task.delay(str(job.id))
        else:
            await self.session.commit()
        return {"message": "Captcha recorded; job re-queued"}

    async def complete_manual_item(
        self, user_id: uuid.UUID, job_id: uuid.UUID, item_id: uuid.UUID, status: str, detail: str | None
    ):
        await self._set_rls(user_id)
        job = await self.repo.get_job(job_id, user_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        item = next((i for i in (job.items or []) if i.id == item_id), None)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        map_status = {
            "submitted": BrokerOptOutStatus.SUBMITTED.value,
            "manual_needed": BrokerOptOutStatus.MANUAL_NEEDED.value,
            "skipped": BrokerOptOutStatus.SKIPPED_FRESH.value,
            "error": BrokerOptOutStatus.ERROR.value,
        }[status]
        await self.repo.set_item_status(item, map_status, detail=detail)
        await self.repo.upsert_state(
            user_id=user_id,
            broker_id=item.broker_id,
            broker_name=item.broker_name,
            status=map_status,
            identifier_id=job.identifier_id,
            detail=detail,
            success=map_status == BrokerOptOutStatus.SUBMITTED.value,
        )
        await self.repo.recompute_job_progress(job)
        await self.session.commit()
        # Try finalize via re-execute finalize path
        await self.execute_job(job_id)
        return await self.repo.get_job(job_id, user_id)

    async def ensure_freeze_checklist(self, user_id: uuid.UUID):
        await self._set_rls(user_id)
        rows = await self.repo.upsert_freeze_seed(user_id, freeze_targets())
        await self.session.commit()
        return rows

    async def update_freeze(self, user_id: uuid.UUID, item_id: uuid.UUID, status: str, notes: str | None):
        await self._set_rls(user_id)
        row = await self.repo.get_freeze(item_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Freeze item not found")
        row.status = status
        if notes is not None:
            row.notes = notes
        if status == "done":
            row.completed_at = datetime.now(UTC)
        await self.session.flush()
        await self.audit.log(
            "remediation.freeze_updated",
            user_id=user_id,
            resource_type="freeze_item",
            resource_id=str(item_id),
            details={"status": status},
        )
        await self.session.commit()
        return row

    async def create_know_request(
        self,
        user_id: uuid.UUID,
        *,
        regime: str,
        recipient_name: str,
        recipient_email: str | None,
        identifier_id: uuid.UUID | None,
        include_deletion: bool,
    ):
        await self._set_rls(user_id)
        idents = await self.identifiers.list_for_user(user_id)
        email = next((i.value_canonical for i in idents if i.type == "email" and i.is_verified), None)
        if identifier_id:
            ident = await self._require_verified_identifier(user_id, identifier_id)
            if ident.type == "email":
                email = ident.value_canonical
        if not email:
            raise HTTPException(status_code=400, detail="Verified email required")
        name = (await self.repo.list_freeze(user_id) and "User") or "User"
        # Prefer profile from freeze notes — use email local as fallback name
        full_name = email.split("@")[0]
        gen = generate_right_to_know(
            regime=regime,
            full_name=full_name,
            email=email,
            recipient_name=recipient_name,
            include_deletion=include_deletion,
        )
        row = await self.repo.create_generated(
            user_id=user_id,
            kind="right_to_know" if not include_deletion else "deletion",
            regime=regime,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            subject=gen["subject"],
            body=gen["body"],
            meta=gen["meta"],
            status="draft",
            deadline_at=gen["deadline_at"],
        )
        await self.session.commit()
        return row

    async def create_complaint(
        self,
        user_id: uuid.UUID,
        *,
        regime: str,
        recipient_name: str,
        regulator: str,
        facts: str,
        original_request_id: uuid.UUID | None,
    ):
        await self._set_rls(user_id)
        idents = await self.identifiers.list_for_user(user_id)
        email = next((i.value_canonical for i in idents if i.type == "email" and i.is_verified), "user@example.com")
        full_name = email.split("@")[0]
        if original_request_id:
            orig = await self.repo.get_generated(original_request_id, user_id)
            if orig and orig.deadline_at and orig.deadline_at > datetime.now(UTC):
                # still allow generate but flag
                facts = facts + "\n\n[Note: original request deadline may not have passed yet.]"
        gen = generate_complaint(
            regime=regime,
            full_name=full_name,
            email=email,
            recipient_name=recipient_name,
            regulator=regulator,
            facts=facts,
        )
        row = await self.repo.create_generated(
            user_id=user_id,
            kind="complaint",
            regime=regime,
            recipient_name=recipient_name,
            recipient_email=None,
            subject=gen["subject"],
            body=gen["body"],
            meta=gen["meta"],
            status="draft",
        )
        await self.session.commit()
        return row

    async def mark_request_sent(self, user_id: uuid.UUID, req_id: uuid.UUID):
        await self._set_rls(user_id)
        row = await self.repo.get_generated(req_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Request not found")
        row.status = "sent_marked"
        row.sent_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.commit()
        return row

    async def verify_brokers(self, user_id: uuid.UUID, broker_ids: list[str] | None = None):
        """AIDR verify — re-check selected brokers."""
        await self._set_rls(user_id)
        states = await self.repo.list_states(user_id)
        if broker_ids:
            states = [s for s in states if s.broker_id in set(broker_ids)]
        else:
            states = [s for s in states if s.last_success_at is not None]
        idents = await self.identifiers.list_for_user(user_id)
        profile = build_profile_from_identifiers(
            [
                {"type": i.type, "value_canonical": i.value_canonical, "is_verified": i.is_verified}
                for i in idents
            ]
        )
        results = []
        for st in states:
            broker = get_broker(st.broker_id)
            if not broker:
                continue
            v = await self.runner.verify_not_listed(broker, profile, user_scope=str(user_id))
            await self.repo.upsert_state(
                user_id=user_id,
                broker_id=st.broker_id,
                broker_name=st.broker_name,
                status=v.status,
                detail=v.detail,
                meta=v.to_dict(),
                verified=True,
            )
            results.append({"broker_id": st.broker_id, **v.to_dict()})
        await self.session.commit()
        return {"results": results}

    async def list_brokers_catalog(self):
        return {
            "brokers": list_green_brokers(enabled_only=False),
            "attribution": "Green subset; strategies inspired by AIDR auto-identity-remove",
        }
