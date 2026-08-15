from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import Recommendation, RecommendationPlan


class RecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_plan(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID | None,
        model_version: str,
        score_snapshot_id: uuid.UUID | None,
        freeze_recommended: bool,
        dag_order: list[str],
        summary: str,
        meta: dict | None,
        drafts: list[dict[str, Any]],
    ) -> tuple[RecommendationPlan, list[Recommendation]]:
        plan = RecommendationPlan(
            user_id=user_id,
            identifier_id=identifier_id,
            model_version=model_version,
            score_snapshot_id=score_snapshot_id,
            freeze_recommended=freeze_recommended,
            dag_order=dag_order,
            summary=summary,
            meta=meta,
        )
        self.session.add(plan)
        await self.session.flush()

        rows: list[Recommendation] = []
        for i, d in enumerate(drafts):
            row = Recommendation(
                user_id=user_id,
                identifier_id=identifier_id,
                plan_id=plan.id,
                code=d["code"],
                lane=d["lane"],
                title=d["title"],
                summary=d["summary"],
                urgency=d["urgency"],
                effort_hours=d["effort_hours"],
                roi=d["roi"],
                priority=d["priority"],
                sort_order=i,
                depends_on=d.get("depends_on"),
                related_finding_ids=d.get("related_finding_ids"),
                steps=d.get("steps"),
                links=d.get("links"),
                playbook_key=d["playbook_key"],
                meta=d.get("meta"),
                status="open",
                model_version=model_version,
            )
            self.session.add(row)
            rows.append(row)
        await self.session.flush()
        return plan, rows

    async def latest_plan(
        self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None
    ) -> RecommendationPlan | None:
        q = select(RecommendationPlan).where(RecommendationPlan.user_id == user_id)
        if identifier_id is not None:
            q = q.where(RecommendationPlan.identifier_id == identifier_id)
        else:
            q = q.where(RecommendationPlan.identifier_id.is_(None))
        q = q.order_by(RecommendationPlan.created_at.desc()).limit(1)
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_for_plan(self, plan_id: uuid.UUID, user_id: uuid.UUID) -> Sequence[Recommendation]:
        result = await self.session.execute(
            select(Recommendation)
            .where(Recommendation.plan_id == plan_id, Recommendation.user_id == user_id)
            .order_by(Recommendation.sort_order.asc())
        )
        return result.scalars().all()

    async def list_open(self, user_id: uuid.UUID, identifier_id: uuid.UUID | None = None) -> Sequence[Recommendation]:
        q = select(Recommendation).where(
            Recommendation.user_id == user_id,
            Recommendation.status.in_(["open", "in_progress", "blocked"]),
        )
        if identifier_id:
            q = q.where(Recommendation.identifier_id == identifier_id)
        q = q.order_by(Recommendation.priority.desc())
        result = await self.session.execute(q)
        return result.scalars().all()

    async def get(self, rec_id: uuid.UUID, user_id: uuid.UUID) -> Recommendation | None:
        result = await self.session.execute(
            select(Recommendation).where(Recommendation.id == rec_id, Recommendation.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def set_status(self, row: Recommendation, status: str) -> Recommendation:
        row.status = status
        if status == "done":
            row.completed_at = datetime.now(UTC)
        await self.session.flush()
        return row
