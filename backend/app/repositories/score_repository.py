from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.score import ExplanationRecord, ResidualInferenceRecord, ScoreSnapshot


class ScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_snapshot(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID | None,
        payload: dict[str, Any],
        trigger: str,
    ) -> ScoreSnapshot:
        row = ScoreSnapshot(
            user_id=user_id,
            identifier_id=identifier_id,
            model_version=payload["model_version"],
            score_confirmed=payload["score_confirmed"],
            score_possible=payload["score_possible"],
            score_combined=payload["score_combined"],
            severity=payload["severity"],
            vector=payload["vector"],
            metrics=payload.get("metrics"),
            contributions=payload.get("contributions"),
            counterfactuals=payload.get("counterfactuals"),
            attributions=payload.get("attributions"),
            explanation_summary=payload.get("explanation_summary") or "",
            meta=payload.get("meta"),
            finding_count=payload.get("input_finding_count") or 0,
            trigger=trigger,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_explanation(
        self,
        *,
        user_id: uuid.UUID,
        score_snapshot_id: uuid.UUID,
        kind: str,
        title: str,
        body: dict[str, Any],
        finding_id: uuid.UUID | None = None,
    ) -> ExplanationRecord:
        row = ExplanationRecord(
            user_id=user_id,
            score_snapshot_id=score_snapshot_id,
            finding_id=finding_id,
            kind=kind,
            title=title,
            body=body,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def latest(
        self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None
    ) -> ScoreSnapshot | None:
        q = select(ScoreSnapshot).where(ScoreSnapshot.user_id == user_id)
        if identifier_id is None:
            q = q.where(ScoreSnapshot.identifier_id.is_(None))
        else:
            q = q.where(ScoreSnapshot.identifier_id == identifier_id)
        q = q.order_by(ScoreSnapshot.created_at.desc()).limit(1)
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def history(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> Sequence[ScoreSnapshot]:
        q = select(ScoreSnapshot).where(ScoreSnapshot.user_id == user_id)
        if identifier_id is not None:
            q = q.where(ScoreSnapshot.identifier_id == identifier_id)
        q = q.order_by(ScoreSnapshot.created_at.desc()).limit(limit)
        result = await self.session.execute(q)
        return result.scalars().all()

    async def get(self, snapshot_id: uuid.UUID, user_id: uuid.UUID) -> ScoreSnapshot | None:
        result = await self.session.execute(
            select(ScoreSnapshot).where(
                ScoreSnapshot.id == snapshot_id, ScoreSnapshot.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_explanations(
        self, snapshot_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[ExplanationRecord]:
        result = await self.session.execute(
            select(ExplanationRecord).where(
                ExplanationRecord.score_snapshot_id == snapshot_id,
                ExplanationRecord.user_id == user_id,
            )
        )
        return result.scalars().all()

    async def get_residual(self, snapshot_id: uuid.UUID) -> ResidualInferenceRecord | None:
        result = await self.session.execute(
            select(ResidualInferenceRecord).where(
                ResidualInferenceRecord.score_snapshot_id == snapshot_id
            )
        )
        return result.scalar_one_or_none()

    async def create_residual(
        self,
        *,
        user_id: uuid.UUID,
        score_snapshot_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> ResidualInferenceRecord:
        row = ResidualInferenceRecord(
            user_id=user_id,
            score_snapshot_id=score_snapshot_id,
            status=payload.get("status", "abstained"),
            model_version=payload.get("model_version"),
            feature_schema_version=payload.get("feature_schema_version"),
            raw_delta=payload.get("raw_delta"),
            bounded_delta=payload.get("bounded_delta"),
            confidence=payload.get("confidence"),
            abstained=payload.get("abstained", True),
            abstention_reason=payload.get("reason"),
        )
        self.session.add(row)
        await self.session.flush()
        return row
