from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import IdentityCollision, IdentityEdge


def _ordered_pair(a: uuid.UUID, b: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    return (a, b) if str(a) <= str(b) else (b, a)


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_edges(self, user_id: uuid.UUID) -> Sequence[IdentityEdge]:
        result = await self.session.execute(
            select(IdentityEdge).where(IdentityEdge.user_id == user_id).order_by(IdentityEdge.match_prob.desc())
        )
        return result.scalars().all()

    async def upsert_edge(
        self,
        *,
        user_id: uuid.UUID,
        left_id: uuid.UUID,
        right_id: uuid.UUID,
        match_weight: float,
        match_prob: float,
        decision: str,
        evidence: dict[str, Any] | None,
        model_version: str,
    ) -> IdentityEdge:
        left_id, right_id = _ordered_pair(left_id, right_id)
        result = await self.session.execute(
            select(IdentityEdge).where(
                IdentityEdge.user_id == user_id,
                IdentityEdge.left_identifier_id == left_id,
                IdentityEdge.right_identifier_id == right_id,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.match_weight = match_weight
            row.match_prob = match_prob
            row.decision = decision
            row.evidence = evidence
            row.model_version = model_version
            await self.session.flush()
            return row
        row = IdentityEdge(
            user_id=user_id,
            left_identifier_id=left_id,
            right_identifier_id=right_id,
            match_weight=match_weight,
            match_prob=match_prob,
            decision=decision,
            evidence=evidence,
            model_version=model_version,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_edge(self, edge_id: uuid.UUID, user_id: uuid.UUID) -> IdentityEdge | None:
        result = await self.session.execute(
            select(IdentityEdge).where(IdentityEdge.id == edge_id, IdentityEdge.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def set_review(
        self, edge: IdentityEdge, status: str, note: str | None
    ) -> IdentityEdge:
        edge.review_status = status
        edge.review_note = note
        if status == "accepted":
            edge.decision = "auto_link"
        elif status == "rejected":
            edge.decision = "none"
        await self.session.flush()
        return edge

    async def count_accepted_edges(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(IdentityEdge).where(
                IdentityEdge.user_id == user_id,
                or_(
                    IdentityEdge.decision == "auto_link",
                    IdentityEdge.review_status == "accepted",
                ),
            )
        )
        return len(result.scalars().all())

    async def add_collision(
        self,
        *,
        user_id: uuid.UUID,
        edge_id: uuid.UUID | None,
        reason: str,
        details: dict | None,
    ) -> IdentityCollision:
        row = IdentityCollision(
            user_id=user_id, edge_id=edge_id, reason=reason, details=details
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_collisions(self, user_id: uuid.UUID, unresolved_only: bool = True) -> Sequence[IdentityCollision]:
        q = select(IdentityCollision).where(IdentityCollision.user_id == user_id)
        if unresolved_only:
            q = q.where(IdentityCollision.resolved.is_(False))
        result = await self.session.execute(q.order_by(IdentityCollision.created_at.desc()))
        return result.scalars().all()
