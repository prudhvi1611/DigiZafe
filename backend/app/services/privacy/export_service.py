from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.privacy_export import build_export_package, redacted_user_public
from app.repositories.finding_repository import FindingRepository
from app.repositories.identifier_repository import IdentifierRepository
from app.repositories.identity_repository import IdentityRepository
from app.repositories.privacy_repository import PrivacyRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.remediation_repository import RemediationRepository
from app.repositories.score_repository import ScoreRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService


class ExportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PrivacyRepository(session)
        self.settings = get_settings()
        self.audit = AuditService(session)

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def start_export(
        self,
        user_id: uuid.UUID,
        *,
        include_audit: bool = True,
        include_egress: bool = True,
    ):
        if not self.settings.feature_data_export:
            raise HTTPException(status_code=503, detail="Export disabled")
        await self._set_rls(user_id)
        job = await self.repo.create_export_job(
            user_id=user_id,
            include_audit=include_audit and self.settings.export_include_audit,
            include_egress=include_egress and self.settings.export_include_egress,
        )
        await self.audit.log(
            "privacy.export_started",
            user_id=user_id,
            resource_type="data_export_job",
            resource_id=str(job.id),
        )
        await self.session.commit()

        # Synchronous build for MVP (small accounts). Workerize if packages grow.
        try:
            package = await self._build_package(
                user_id,
                include_audit=job.include_audit,
                include_egress=job.include_egress,
            )
            raw = json.dumps(package, default=str)
            size = len(raw.encode("utf-8"))
            if size > self.settings.export_max_bytes:
                raise HTTPException(status_code=413, detail="Export exceeds size limit")
            await self.repo.mark_export_ready(job, package, size)
            await self.audit.log(
                "privacy.export_ready",
                user_id=user_id,
                resource_type="data_export_job",
                resource_id=str(job.id),
                details={"size_bytes": size},
            )
            await self.session.commit()
        except HTTPException:
            raise
        except Exception as e:
            await self.repo.mark_export_failed(job, str(e))
            await self.session.commit()
            raise HTTPException(status_code=500, detail="Export failed") from e

        return await self.repo.get_export(job.id, user_id)

    async def _build_package(
        self, user_id: uuid.UUID, *, include_audit: bool, include_egress: bool
    ) -> dict[str, Any]:
        users = UserRepository(self.session)
        user = await users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        idents = await IdentifierRepository(self.session).list_for_user(user_id)
        findings = await FindingRepository(self.session).list_findings(user_id, limit=1000)
        scores = await ScoreRepository(self.session).history(user_id, limit=50)
        try:
            recs = await RecommendationRepository(self.session).list_open(user_id)
        except Exception:
            recs = []
        try:
            states = await RemediationRepository(self.session).list_states(user_id)
        except Exception:
            states = []
        try:
            edges = await IdentityRepository(self.session).list_edges(user_id)
        except Exception:
            edges = []
        try:
            gens = await RemediationRepository(self.session).list_generated(user_id)
        except Exception:
            gens = []
        
        try:
            from app.models.candidate_profile import CandidateDiscoveryRun, CandidateProfile
            from sqlalchemy import select
            
            runs_stmt = select(CandidateDiscoveryRun).where(CandidateDiscoveryRun.user_id == user_id)
            c_runs = (await self.session.execute(runs_stmt)).scalars().all()
            
            profiles_stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
            c_profiles = (await self.session.execute(profiles_stmt)).scalars().all()
            
            from app.models.identity_match_assessment import IdentityMatchAssessment
            assess_stmt = select(IdentityMatchAssessment).where(IdentityMatchAssessment.user_id == user_id)
            assessments = (await self.session.execute(assess_stmt)).scalars().all()
            
            from app.models.candidate_provenance import CandidateProvenanceObservation
            prov_stmt = select(CandidateProvenanceObservation).where(CandidateProvenanceObservation.user_id == user_id)
            provenances = (await self.session.execute(prov_stmt)).scalars().all()

            from app.models.temporal import IdentityChangeEvent, IdentityReviewItem
            change_stmt = select(IdentityChangeEvent).where(IdentityChangeEvent.user_id == user_id)
            change_events = (await self.session.execute(change_stmt)).scalars().all()

            review_stmt = select(IdentityReviewItem).where(IdentityReviewItem.user_id == user_id)
            review_items = (await self.session.execute(review_stmt)).scalars().all()
            
            from app.models.orchestration import IdentityOrchestrationRun, ConnectorExecutionPlanItem
            orch_runs_stmt = select(IdentityOrchestrationRun).where(IdentityOrchestrationRun.user_id == user_id)
            orch_runs = (await self.session.execute(orch_runs_stmt)).scalars().all()
            
            plan_items_stmt = select(ConnectorExecutionPlanItem).join(IdentityOrchestrationRun).where(IdentityOrchestrationRun.user_id == user_id)
            plan_items = (await self.session.execute(plan_items_stmt)).scalars().all()
        except Exception:
            c_runs = []
            c_profiles = []
            assessments = []
            provenances = []
            orch_runs = []
            plan_items = []
            
        consents = await self.repo.list_consents(user_id)
        
        from app.services.identity_anchor_service import IdentityAnchorService
        try:
            anchor_summary = await IdentityAnchorService(self.session).get_anchor_summary(user_id)
            anchor_data = anchor_summary.model_dump(mode="json")
        except Exception:
            anchor_data = None

        audit_logs = None
        if include_audit:
            rows = await self.repo.list_audit(user_id, limit=500)
            audit_logs = [
                {
                    "id": str(a.id),
                    "action": a.action,
                    "resource_type": a.resource_type,
                    "resource_id": a.resource_id,
                    "details": a.details,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "correlation_id": a.correlation_id,
                }
                for a in rows
            ]

        egress = None
        if include_egress:
            rows = await self.repo.list_egress(user_id, limit=500)
            egress = [
                {
                    "id": str(e.id),
                    "purpose": e.purpose,
                    "destination_host": e.destination_host,
                    "method": e.method,
                    "status_code": e.status_code,
                    "success": e.success,
                    "summary": e.summary,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in rows
            ]

        return build_export_package(
            user=redacted_user_public(user),
            identifiers=[
                {
                    "id": str(i.id),
                    "type": i.type,
                    "value_canonical": i.value_canonical,
                    "value_display": i.value_display,
                    "is_verified": i.is_verified,
                    "verified_at": i.verified_at.isoformat() if i.verified_at else None,
                    "verification_method": i.verification_method,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in idents
            ],
            findings=[
                {
                    "id": str(f.id),
                    "kind": f.kind,
                    "source": f.source,
                    "title": f.title,
                    "summary": f.summary,
                    "severity_hint": f.severity_hint,
                    "confidence": f.confidence,
                    "layer": f.layer,
                    "track": f.track,
                    "status": f.status,
                    "attribution": f.attribution,
                    "raw_ref": f.raw_ref,
                    "attributes": f.attributes,
                    "first_seen_at": f.first_seen_at.isoformat() if f.first_seen_at else None,
                    "last_seen_at": f.last_seen_at.isoformat() if f.last_seen_at else None,
                }
                for f in findings
            ],
            scores=[
                {
                    "id": str(s.id),
                    "score_combined": s.score_combined,
                    "severity": s.severity,
                    "vector": s.vector,
                    "model_version": s.model_version,
                    "trigger": s.trigger,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "explanation_summary": s.explanation_summary,
                }
                for s in scores
            ],
            recommendations=[
                {
                    "id": str(r.id),
                    "code": r.code,
                    "title": r.title,
                    "lane": r.lane,
                    "status": r.status,
                    "priority": r.priority,
                }
                for r in recs
            ],
            remediation_state=[
                {
                    "broker_id": s.broker_id,
                    "broker_name": s.broker_name,
                    "status": s.status,
                    "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
                    "detail": s.detail,
                }
                for s in states
            ],
            consent_records=[
                {
                    "purpose": c.purpose,
                    "scope": c.scope,
                    "granted": c.granted,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
                }
                for c in consents
            ],
            audit_logs=audit_logs,
            egress_ledger=egress,
            identity_edges=[
                {
                    "left": str(e.left_identifier_id),
                    "right": str(e.right_identifier_id),
                    "match_prob": e.match_prob,
                    "decision": e.decision,
                    "review_status": e.review_status,
                }
                for e in edges
            ],
            generated_requests=[
                {
                    "id": str(g.id),
                    "kind": g.kind,
                    "regime": g.regime,
                    "subject": g.subject,
                    "status": g.status,
                    "created_at": g.created_at.isoformat() if g.created_at else None,
                }
                for g in gens
            ],
            candidate_discovery_runs=[
                {
                    "id": str(r.id),
                    "status": r.status,
                    "input_count": r.input_count,
                    "candidate_count": r.candidate_count,
                    "source_tool": r.source_tool,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                }
                for r in c_runs
            ],
            candidate_profiles=[
                {
                    "id": str(p.id),
                    "platform": p.platform,
                    "profile_url": p.profile_url,
                    "canonical_profile_url": p.canonical_profile_url,
                    "candidate_status": p.candidate_status,
                    "source_input_type": p.source_input_type,
                    "source_input_value": p.source_input_value_reference,
                    "first_observed_at": p.first_observed_at.isoformat() if p.first_observed_at else None,
                }
                for p in c_profiles
            ],
            candidate_provenance_observations=[
                {
                    "id": str(p.id),
                    "candidate_profile_id": str(p.candidate_profile_id),
                    "discovery_run_id": str(p.discovery_run_id),
                    "connector_type": p.connector_type,
                    "connector_version": p.connector_version,
                    "capability": p.capability,
                    "input_alias_id": str(p.input_alias_id) if p.input_alias_id else None,
                    "observation_type": p.observation_type,
                    "canonical_fact_key": p.canonical_fact_key,
                    "observed_at": p.observed_at.isoformat() if p.observed_at else None,
                }
                for p in provenances
            ],
            identity_match_assessments=[
                {
                    "id": str(a.id),
                    "candidate_profile_id": str(a.candidate_profile_id),
                    "is_current": a.is_current,
                    "engine_version": a.engine_version,
                    "policy_version": a.policy_version,
                    "assessment_status": a.assessment_status,
                    "score": a.score,
                    "confidence_band": a.confidence_band,
                    "evidence_snapshot": a.evidence_snapshot,
                    "explanation_mapping": a.explanation_mapping,
                    "stale_state": a.stale_state,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in assessments
            ],
            identity_orchestration_runs=[
                {
                    "id": str(r.id),
                    "anchor_id": str(r.anchor_id),
                    "input_fingerprint": r.input_fingerprint,
                    "status": r.status,
                    "planned_connector_count": r.planned_connector_count,
                    "completed_connector_count": r.completed_connector_count,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                }
                for r in orch_runs
            ],
            connector_execution_plan_items=[
                {
                    "id": str(p.id),
                    "orchestration_run_id": str(p.orchestration_run_id),
                    "input_alias_id": str(p.input_alias_id) if p.input_alias_id else None,
                    "connector_type": p.connector_type,
                    "capability_requested": p.capability_requested,
                    "decision": p.decision.value if hasattr(p.decision, "value") else str(p.decision),
                    "execution_status": p.execution_status,
                    "budget_consumed": p.budget_consumed,
                    "discovery_run_id": str(p.discovery_run_id) if p.discovery_run_id else None,
                }
                for p in plan_items
            ],
            identity_anchor=anchor_data,
        )

    async def get_export(self, user_id: uuid.UUID, job_id: uuid.UUID):
        await self._set_rls(user_id)
        job = await self.repo.get_export(job_id, user_id)
        if not job:
            raise HTTPException(status_code=404, detail="Export not found")
        return job
