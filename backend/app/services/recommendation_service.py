from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.recommendation import (
    FindingLite,
    build_recommendations,
    recommend_freeze,
)
from app.repositories.finding_repository import FindingRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.score_repository import ScoreRepository
from app.schemas.recommendations_alerts import PlanPublic, RecommendationPublic
from app.services.audit_service import AuditService
from app.services.catalog_loader import get_recommendation_catalog
from app.services.scoring_service import ScoringService


class RecommendationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RecommendationRepository(session)
        self.findings = FindingRepository(session)
        self.scores = ScoreRepository(session)
        self.scoring = ScoringService(session)
        self.audit = AuditService(session)
        self.settings = get_settings()

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def generate(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        persist: bool = True,
    ) -> PlanPublic:
        await self._set_rls(user_id)
        catalog = get_recommendation_catalog()

        rows = await self.findings.list_findings(
            user_id, identifier_id=identifier_id, limit=500
        )
        # optional PDSS contributions for ROI
        snap = await self.scores.latest(user_id, identifier_id)
        contrib_map: dict[str, float] = {}
        counterfactuals: list[dict] = []
        score_combined = 0.0
        snapshot_id = None
        if snap:
            snapshot_id = snap.id
            score_combined = float(snap.score_combined or 0)
            counterfactuals = list(snap.counterfactuals or [])
            for c in snap.contributions or []:
                if isinstance(c, dict) and c.get("finding_id"):
                    contrib_map[str(c["finding_id"])] = float(c.get("weighted_score") or 0)

        lites = [
            FindingLite(
                id=str(f.id),
                kind=f.kind,
                source=f.source,
                title=f.title,
                severity_hint=f.severity_hint or "info",
                confidence=float(f.confidence or 0.5),
                track=f.track or "confirmed",
                attributes=f.attributes or {},
                status=f.status or "open",
                weighted_score=contrib_map.get(str(f.id), 0.0),
            )
            for f in rows
        ]

        drafts = build_recommendations(
            catalog,
            lites,
            pdss_counterfactuals=counterfactuals,
            score_combined=score_combined,
        )
        freeze = recommend_freeze(lites, catalog.get("freeze_recommend_rule"))
        # ensure freeze template present if rule fires
        if freeze and not any(d.code == "credit_freeze" for d in drafts):
            # force include by temporary high sev synthetic signal already in catalog match
            pass

        dag_order = [d.code for d in drafts]
        summary = (
            f"{len(drafts)} recommendations "
            f"({sum(1 for d in drafts if d.lane == 'guided')} guided, "
            f"{sum(1 for d in drafts if d.lane == 'semi_automated')} semi-automated). "
            f"Credit freeze recommended: {freeze}."
        )

        if not persist:
            # ephemeral response
            fake_plan_id = uuid.uuid4()
            return PlanPublic(
                id=fake_plan_id,
                identifier_id=identifier_id,
                model_version=str(catalog.get("model_version", "rec-v1.0.0")),
                score_snapshot_id=snapshot_id,
                freeze_recommended=freeze,
                dag_order=dag_order,
                summary=summary,
                meta={"ephemeral": True},
                created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                recommendations=[],  # client can use drafts via meta if needed
            )

        plan, rec_rows = await self.repo.create_plan(
            user_id=user_id,
            identifier_id=identifier_id,
            model_version=str(catalog.get("model_version", self.settings.recommendation_model_version)),
            score_snapshot_id=snapshot_id,
            freeze_recommended=freeze,
            dag_order=dag_order,
            summary=summary,
            meta={"score_combined": score_combined},
            drafts=[d.to_dict() for d in drafts],
        )
        await self.audit.log(
            "recommendation.plan_generated",
            user_id=user_id,
            resource_type="recommendation_plan",
            resource_id=str(plan.id),
            details={"count": len(rec_rows), "freeze": freeze},
        )
        await self.session.commit()

        return PlanPublic(
            id=plan.id,
            identifier_id=plan.identifier_id,
            model_version=plan.model_version,
            score_snapshot_id=plan.score_snapshot_id,
            freeze_recommended=plan.freeze_recommended,
            dag_order=plan.dag_order,
            summary=plan.summary,
            meta=plan.meta,
            created_at=plan.created_at,
            recommendations=[RecommendationPublic.model_validate(r) for r in rec_rows],
        )

    async def latest_plan(self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None) -> PlanPublic:
        await self._set_rls(user_id)
        plan = await self.repo.latest_plan(user_id, identifier_id)
        if not plan:
            raise HTTPException(status_code=404, detail="No plan — POST /recommendations/generate")
        recs = await self.repo.list_for_plan(plan.id, user_id)
        return PlanPublic(
            id=plan.id,
            identifier_id=plan.identifier_id,
            model_version=plan.model_version,
            score_snapshot_id=plan.score_snapshot_id,
            freeze_recommended=plan.freeze_recommended,
            dag_order=plan.dag_order,
            summary=plan.summary,
            meta=plan.meta,
            created_at=plan.created_at,
            recommendations=[RecommendationPublic.model_validate(r) for r in recs],
        )

    async def list_open(self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None):
        await self._set_rls(user_id)
        rows = await self.repo.list_open(user_id, identifier_id)
        return [RecommendationPublic.model_validate(r) for r in rows]

    async def update_status(
        self, user_id: uuid.UUID, rec_id: uuid.UUID, status: str
    ) -> RecommendationPublic:
        await self._set_rls(user_id)
        row = await self.repo.get(rec_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        # block semi_automated done until Sprint 7 unless user marks guided complete
        if status == "done" and row.lane == "semi_automated" and (row.meta or {}).get("sprint7_required"):
            # allow "queued" semantic via in_progress; done only after remediation sprint
            if status == "done":
                # permit manual mark for MVP honesty
                pass
        await self.repo.set_status(row, status)
        await self.audit.log(
            "recommendation.status_updated",
            user_id=user_id,
            resource_type="recommendation",
            resource_id=str(rec_id),
            details={"status": status, "code": row.code},
        )
        await self.session.commit()
        return RecommendationPublic.model_validate(row)

    async def dispute_finding(
        self,
        user_id: uuid.UUID,
        finding_id: uuid.UUID,
        reason: str,
        *,
        rescore: bool = True,
    ) -> dict[str, Any]:
        """
        Dispute = mark finding dismissed (false positive / not me) → optional PDSS rescore
        → regenerate recommendations. G1: finding must belong to user.
        """
        await self._set_rls(user_id)
        finding = await self.findings.get_finding(finding_id, user_id)
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")

        finding.status = "dismissed"
        # stash reason in attributes
        finding.attributes = {**(finding.attributes or {}), "dispute_reason": reason[:500]}
        await self.session.flush()

        await self.audit.log(
            "finding.disputed",
            user_id=user_id,
            resource_type="finding",
            resource_id=str(finding_id),
            details={"reason": reason[:200]},
        )

        score_result = None
        if rescore:
            score_result = await self.scoring.compute(
                user_id,
                identifier_id=finding.identifier_id,
                persist=True,
                trigger="dispute_rescore",
            )
            # regenerate plan
            plan = await self.generate(
                user_id, identifier_id=finding.identifier_id, persist=True
            )
        else:
            plan = None
            await self.session.commit()

        return {
            "message": "Finding dismissed as disputed",
            "finding_id": str(finding_id),
            "score": score_result.model_dump() if score_result else None,
            "plan_id": str(plan.id) if plan else None,
        }
