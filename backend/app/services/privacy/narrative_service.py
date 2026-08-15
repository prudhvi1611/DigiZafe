from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.narrative import (
    SYSTEM_PROMPT,
    FactsPack,
    build_deterministic_narrative,
    user_prompt_from_facts,
)
from app.repositories.identifier_repository import IdentifierRepository
from app.repositories.privacy_repository import PrivacyRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.remediation_repository import RemediationRepository
from app.repositories.score_repository import ScoreRepository
from app.services.audit_service import AuditService
from app.services.privacy.groq_client import GroqError, groq_available, groq_chat


class NarrativeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PrivacyRepository(session)
        self.scores = ScoreRepository(session)
        self.settings = get_settings()
        self.audit = AuditService(session)

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def _facts(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None,
        score_snapshot_id: uuid.UUID | None,
    ) -> tuple[FactsPack, uuid.UUID]:
        if score_snapshot_id:
            snapshot = await self.scores.get(score_snapshot_id, user_id)
        else:
            snapshot = await self.scores.latest(user_id, identifier_id)

        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail="No score snapshot — compute PDSS first",
            )

        contributions = list(snapshot.contributions or [])[
            : self.settings.narrative_max_findings
        ]
        counterfactuals = list(snapshot.counterfactuals or [])[:5]

        recommendation_titles: list[str] = []
        try:
            recommendations = await RecommendationRepository(self.session).list_open(
                user_id,
                identifier_id,
            )
            recommendation_titles = [
                recommendation.title for recommendation in recommendations[:8]
            ]
        except Exception:
            recommendation_titles = []

        broker_statuses: list[dict[str, str]] = []
        try:
            states = await RemediationRepository(self.session).list_states(user_id)
            broker_statuses = [
                {
                    "broker_id": state.broker_id,
                    "status": state.status,
                }
                for state in states[:10]
            ]
        except Exception:
            broker_statuses = []

        identifier_types: list[str] = []
        try:
            identifiers = await IdentifierRepository(self.session).list_for_user(user_id)
            identifier_types = sorted(
                {
                    identifier.type
                    for identifier in identifiers
                    if identifier.is_verified
                }
            )
        except Exception:
            identifier_types = []

        facts = FactsPack(
            score_combined=float(snapshot.score_combined),
            severity=snapshot.severity,
            score_confirmed=float(snapshot.score_confirmed),
            score_possible=float(snapshot.score_possible),
            vector=snapshot.vector,
            explanation_summary=snapshot.explanation_summary or "",
            model_version=snapshot.model_version,
            contributions=contributions,
            counterfactuals=counterfactuals,
            attributions=list(snapshot.attributions or []),
            open_recommendation_titles=recommendation_titles,
            broker_statuses=broker_statuses,
            identifier_types=identifier_types,
        )

        return facts, snapshot.id

    async def generate(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        score_snapshot_id: uuid.UUID | None = None,
        prefer_llm: bool = True,
        persist: bool = True,
    ) -> dict[str, Any]:
        if not self.settings.feature_grounded_narrative:
            raise HTTPException(
                status_code=503,
                detail="Narrative feature disabled",
            )

        await self._set_rls(user_id)

        facts, snapshot_id = await self._facts(
            user_id,
            identifier_id=identifier_id,
            score_snapshot_id=score_snapshot_id,
        )

        mode = "deterministic"
        model_name: str | None = None
        body = build_deterministic_narrative(facts)

        if prefer_llm and await groq_available():
            try:
                body = await groq_chat(
                    system=SYSTEM_PROMPT,
                    user=user_prompt_from_facts(facts),
                )
                mode = "groq"
                model_name = self.settings.groq_model
            except GroqError:
                body = build_deterministic_narrative(facts)

        title = (
            f"Exposure briefing — PDSS "
            f"{facts.score_combined:.1f} ({facts.severity})"
        )

        row = None

        if persist:
            row = await self.repo.save_narrative(
                user_id=user_id,
                score_snapshot_id=snapshot_id,
                identifier_id=identifier_id,
                mode=mode,
                model_name=model_name,
                title=title,
                body_markdown=body,
                facts_used=facts.to_dict(),
            )

            await self.audit.log(
                "privacy.narrative_generated",
                user_id=user_id,
                resource_type="narrative_briefing",
                resource_id=str(row.id),
                details={
                    "mode": mode,
                    "model": model_name,
                    "grounded": True,
                },
            )

            await self.session.commit()

        return {
            "id": row.id if row else None,
            "score_snapshot_id": snapshot_id,
            "identifier_id": identifier_id,
            "mode": mode,
            "model_name": model_name,
            "title": title,
            "body_markdown": body,
            "grounded": True,
            "facts_used": facts.to_dict(),
            "created_at": row.created_at if row else None,
        }

    async def get_counterfactuals(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        snapshot_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        await self._set_rls(user_id)

        snapshot = (
            await self.scores.get(snapshot_id, user_id)
            if snapshot_id
            else await self.scores.latest(user_id, identifier_id)
        )

        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail="No score snapshot",
            )

        return {
            "score_snapshot_id": snapshot.id,
            "counterfactuals": snapshot.counterfactuals or [],
            "explanation_summary": snapshot.explanation_summary or "",
            "vector": snapshot.vector,
            "score_combined": snapshot.score_combined,
        }
