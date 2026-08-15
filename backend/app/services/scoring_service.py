from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.pdss import FindingScoreInput, PDSSEngine
from app.ml.contracts import ResidualFeatureContext
from app.ml.residual_service import evaluate_residual
from app.repositories.finding_repository import FindingRepository
from app.repositories.identifier_repository import IdentifierRepository
from app.repositories.score_repository import ScoreRepository
from app.schemas.identity_score import ResidualMLPublic, ScorePublic
from app.services.audit_service import AuditService
from app.services.catalog_loader import get_pdss_catalog
from app.services.identity_service import IdentityService


class ScoringService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.scores = ScoreRepository(session)
        self.findings = FindingRepository(session)
        self.identifiers = IdentifierRepository(session)
        self.identity = IdentityService(session)
        self.audit = AuditService(session)
        self.settings = get_settings()
        self.engine = PDSSEngine(get_pdss_catalog())

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def _load_finding_inputs(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID | None,
    ) -> tuple[list[FindingScoreInput], str, int]:
        if identifier_id:
            ident = await self.identifiers.get(identifier_id, user_id)
            if not ident:
                raise HTTPException(status_code=404, detail="Identifier not found")
            rows = await self.findings.list_findings(user_id, identifier_id=identifier_id, limit=500)
            id_type = ident.type
        else:
            rows = await self.findings.list_findings(user_id, limit=1000)
            id_type = "email"  # aggregate default criticality baseline

        edge_count = await self.identity.accepted_edge_count(user_id)

        inputs = [
            FindingScoreInput(
                id=str(f.id),
                kind=f.kind,
                source=f.source,
                title=f.title,
                confidence=float(f.confidence or 0.5),
                layer=f.layer or "surface",
                track=f.track or "confirmed",
                severity_hint=f.severity_hint or "info",
                raw_ref=f.raw_ref,
                attributes=f.attributes or {},
                observed_at=f.last_seen_at or f.first_seen_at,
                attribution=f.attribution,
            )
            for f in rows
            if f.status != "dismissed"
        ]
        return inputs, id_type, edge_count

    async def compute(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        persist: bool = True,
        trigger: str = "manual",
        exclude_finding_ids: set[str] | None = None,
        exclude_sources: set[str] | None = None,
        exclude_kinds: set[str] | None = None,
    ) -> ScorePublic:
        await self._set_rls(user_id)
        inputs, id_type, edge_count = await self._load_finding_inputs(user_id, identifier_id)

        excl = set(exclude_finding_ids or set())
        if exclude_sources or exclude_kinds:
            for f in inputs:
                if exclude_sources and f.source in exclude_sources:
                    excl.add(f.id)
                if exclude_kinds and f.kind in exclude_kinds:
                    excl.add(f.id)

        result = self.engine.score(
            inputs,
            identifier_type=id_type,
            identity_edge_count=edge_count,
            exclude_finding_ids=excl,
        )
        payload = result.to_dict()

        snapshot_id = None
        created_at = None
        if persist and not excl:
            # only persist real scores, not pure what-if exclusions (what-if can persist with trigger=whatif if desired)
            snap = await self.scores.create_snapshot(
                user_id=user_id,
                identifier_id=identifier_id,
                payload=payload,
                trigger=trigger,
            )
            snapshot_id = snap.id
            created_at = snap.created_at

            # G3 durable explanation records
            await self.scores.add_explanation(
                user_id=user_id,
                score_snapshot_id=snap.id,
                kind="summary",
                title="PDSS summary",
                body={
                    "explanation_summary": result.explanation_summary,
                    "vector": result.vector,
                    "severity": result.severity,
                    "scores": {
                        "confirmed": result.score_confirmed,
                        "possible": result.score_possible,
                        "combined": result.score_combined,
                    },
                    "attributions": result.attributions,
                },
            )
            for c in result.contributions[:30]:
                fid = None
                try:
                    fid = uuid.UUID(c.finding_id)
                except Exception:
                    pass
                await self.scores.add_explanation(
                    user_id=user_id,
                    score_snapshot_id=snap.id,
                    kind="contribution",
                    title=c.title[:512],
                    finding_id=fid,
                    body=c.to_dict(),
                )
            for cf in result.counterfactuals:
                await self.scores.add_explanation(
                    user_id=user_id,
                    score_snapshot_id=snap.id,
                    kind="counterfactual",
                    title=cf.get("narrative", "counterfactual")[:512],
                    body=cf,
                )

            await self.audit.log(
                "score.computed",
                user_id=user_id,
                resource_type="score_snapshot",
                resource_id=str(snap.id),
                details={
                    "score_combined": result.score_combined,
                    "severity": result.severity,
                    "identifier_id": str(identifier_id) if identifier_id else None,
                    "model_version": result.model_version,
                },
            )
            await self.session.commit()
        elif persist and excl:
            snap = await self.scores.create_snapshot(
                user_id=user_id,
                identifier_id=identifier_id,
                payload={**payload, "meta": {**(payload.get("meta") or {}), "whatif": True, "excluded": list(excl)}},
                trigger="whatif",
            )
            snapshot_id = snap.id
            created_at = snap.created_at
            await self.session.commit()

        residual_ml_resp = None
        if persist and snapshot_id and self.settings.feature_residual_ml:
            ml_ctx = ResidualFeatureContext(
                pdss_score_confirmed=result.score_confirmed,
                pdss_score_possible=result.score_possible,
                findings=inputs
            )
            ml_result = evaluate_residual(ml_ctx)
            await self.scores.create_residual(
                user_id=user_id,
                score_snapshot_id=snapshot_id,
                payload={
                    "status": ml_result.status,
                    "model_version": ml_result.model_version,
                    "feature_schema_version": ml_result.feature_schema_version,
                    "raw_delta": ml_result.raw_delta,
                    "bounded_delta": ml_result.bounded_delta,
                    "confidence": ml_result.confidence,
                    "abstained": ml_result.abstained,
                    "reason": ml_result.reason
                }
            )
            await self.session.commit()
            residual_ml_resp = ResidualMLPublic(
                status=ml_result.status,
                model_version=ml_result.model_version,
                feature_schema_version=ml_result.feature_schema_version,
                bounded_delta=ml_result.bounded_delta,
                confidence=ml_result.confidence,
                abstained=ml_result.abstained,
                reason=ml_result.reason
            )

        return ScorePublic(
            id=snapshot_id,
            identifier_id=identifier_id,
            model_version=result.model_version,
            score_confirmed=result.score_confirmed,
            score_possible=result.score_possible,
            score_combined=result.score_combined,
            severity=result.severity,
            vector=result.vector,
            metrics=result.metrics,
            contributions=[c.to_dict() for c in result.contributions],
            counterfactuals=result.counterfactuals,
            attributions=result.attributions,
            explanation_summary=result.explanation_summary,
            finding_count=result.input_finding_count,
            trigger=trigger if not excl else "whatif",
            created_at=created_at,
            meta=result.meta,
            residual_ml=residual_ml_resp,
        )

    async def latest(self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None) -> ScorePublic:
        await self._set_rls(user_id)
        snap = await self.scores.latest(user_id, identifier_id)
        if not snap:
            raise HTTPException(status_code=404, detail="No score yet — POST /scores/compute first")
            
        residual_ml_resp = None
        if self.settings.feature_residual_ml:
            ml_rec = await self.scores.get_residual(snap.id)
            if ml_rec:
                residual_ml_resp = ResidualMLPublic(
                    status=ml_rec.status,
                    model_version=ml_rec.model_version,
                    feature_schema_version=ml_rec.feature_schema_version,
                    bounded_delta=ml_rec.bounded_delta,
                    confidence=ml_rec.confidence,
                    abstained=ml_rec.abstained,
                    reason=ml_rec.abstention_reason
                )
                
        return ScorePublic(
            id=snap.id,
            identifier_id=snap.identifier_id,
            model_version=snap.model_version,
            score_confirmed=snap.score_confirmed,
            score_possible=snap.score_possible,
            score_combined=snap.score_combined,
            severity=snap.severity,
            vector=snap.vector,
            metrics=snap.metrics,
            contributions=snap.contributions,
            counterfactuals=snap.counterfactuals,
            attributions=snap.attributions,
            explanation_summary=snap.explanation_summary,
            finding_count=snap.finding_count,
            trigger=snap.trigger,
            created_at=snap.created_at,
            meta=snap.meta,
            residual_ml=residual_ml_resp,
        )

    async def history(self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None, limit: int = 50):
        await self._set_rls(user_id)
        return await self.scores.history(user_id, identifier_id=identifier_id, limit=limit)

    async def get_snapshot(self, user_id: uuid.UUID, snapshot_id: uuid.UUID) -> ScorePublic:
        await self._set_rls(user_id)
        snap = await self.scores.get(snapshot_id, user_id)
        if not snap:
            raise HTTPException(status_code=404, detail="Snapshot not found")
            
        residual_ml_resp = None
        if self.settings.feature_residual_ml:
            ml_rec = await self.scores.get_residual(snap.id)
            if ml_rec:
                residual_ml_resp = ResidualMLPublic(
                    status=ml_rec.status,
                    model_version=ml_rec.model_version,
                    feature_schema_version=ml_rec.feature_schema_version,
                    bounded_delta=ml_rec.bounded_delta,
                    confidence=ml_rec.confidence,
                    abstained=ml_rec.abstained,
                    reason=ml_rec.abstention_reason
                )
                
        return ScorePublic(
            id=snap.id,
            identifier_id=snap.identifier_id,
            model_version=snap.model_version,
            score_confirmed=snap.score_confirmed,
            score_possible=snap.score_possible,
            score_combined=snap.score_combined,
            severity=snap.severity,
            vector=snap.vector,
            metrics=snap.metrics,
            contributions=snap.contributions,
            counterfactuals=snap.counterfactuals,
            attributions=snap.attributions,
            explanation_summary=snap.explanation_summary,
            finding_count=snap.finding_count,
            trigger=snap.trigger,
            created_at=snap.created_at,
            meta=snap.meta,
        )

    async def explanations(self, user_id: uuid.UUID, snapshot_id: uuid.UUID) -> list[dict[str, Any]]:
        await self._set_rls(user_id)
        rows = await self.scores.list_explanations(snapshot_id, user_id)
        return [
            {
                "id": str(r.id),
                "kind": r.kind,
                "title": r.title,
                "finding_id": str(r.finding_id) if r.finding_id else None,
                "body": r.body,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
