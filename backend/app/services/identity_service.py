from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.linkage import IdentifierView, build_edges
from app.repositories.finding_repository import FindingRepository
from app.repositories.identifier_repository import IdentifierRepository
from app.repositories.identity_repository import IdentityRepository
from app.schemas.identity_score import IdentityEdgePublic, IdentityGraphPublic
from app.services.audit_service import AuditService
from app.services.catalog_loader import get_linkage_weights


class IdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.edges = IdentityRepository(session)
        self.identifiers = IdentifierRepository(session)
        self.findings = FindingRepository(session)
        self.audit = AuditService(session)
        self.settings = get_settings()

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def rebuild_graph(self, user_id: uuid.UUID) -> IdentityGraphPublic:
        await self._set_rls(user_id)
        idents = await self.identifiers.list_for_user(user_id)
        weights = get_linkage_weights()

        views: list[IdentifierView] = []
        for ident in idents:
            flist = await self.findings.list_findings(user_id, identifier_id=ident.id, limit=500)
            sources = sorted({f.source for f in flist})
            breaches = sorted({
                str((f.attributes or {}).get("breach_name") or f.raw_ref or "")
                for f in flist
                if f.kind == "breach"
            } - {""})
            urls = []
            for f in flist:
                u = (f.attributes or {}).get("html_url") or (f.attributes or {}).get("url")
                if u:
                    urls.append(str(u))
            views.append(
                IdentifierView(
                    id=str(ident.id),
                    type=ident.type,
                    value_canonical=ident.value_canonical,
                    is_verified=ident.is_verified,
                    finding_sources=sources,
                    breach_names=breaches,
                    profile_urls=urls,
                )
            )

        results = build_edges(
            views,
            weights,
            auto_link_prob=self.settings.linkage_auto_link_prob,
            review_prob=self.settings.linkage_review_prob,
            collision_flag_prob=self.settings.linkage_collision_flag_prob,
        )

        edge_rows = []
        collisions = []
        for r in results:
            if r.decision == "none":
                continue
            row = await self.edges.upsert_edge(
                user_id=user_id,
                left_id=uuid.UUID(r.left_id),
                right_id=uuid.UUID(r.right_id),
                match_weight=r.match_weight,
                match_prob=r.match_prob,
                decision=r.decision,
                evidence={"items": [e.__dict__ for e in r.evidence]},
                model_version=str(weights.get("model_version", "linkage-v1.0.0")),
            )
            edge_rows.append(row)
            if r.decision in {"review", "weak"}:
                col = await self.edges.add_collision(
                    user_id=user_id,
                    edge_id=row.id,
                    reason=f"linkage_{r.decision}",
                    details=r.to_dict(),
                )
                collisions.append({
                    "id": str(col.id),
                    "edge_id": str(row.id),
                    "reason": col.reason,
                    "details": col.details,
                })

        await self.audit.log(
            "identity.graph_rebuilt",
            user_id=user_id,
            details={"nodes": len(views), "edges": len(edge_rows), "collisions": len(collisions)},
        )
        await self.session.commit()

        nodes = [
            {
                "id": str(i.id),
                "type": i.type,
                "value_display": i.value_display,
                "is_verified": i.is_verified,
            }
            for i in idents
        ]
        return IdentityGraphPublic(
            nodes=nodes,
            edges=[IdentityEdgePublic.model_validate(e) for e in edge_rows],
            collisions=collisions,
            model_version=str(weights.get("model_version", "linkage-v1.0.0")),
        )

    async def get_graph(self, user_id: uuid.UUID) -> IdentityGraphPublic:
        await self._set_rls(user_id)
        idents = await self.identifiers.list_for_user(user_id)
        edges = await self.edges.list_edges(user_id)
        cols = await self.edges.list_collisions(user_id)
        weights = get_linkage_weights()
        return IdentityGraphPublic(
            nodes=[
                {
                    "id": str(i.id),
                    "type": i.type,
                    "value_display": i.value_display,
                    "is_verified": i.is_verified,
                }
                for i in idents
            ],
            edges=[IdentityEdgePublic.model_validate(e) for e in edges],
            collisions=[
                {"id": str(c.id), "edge_id": str(c.edge_id) if c.edge_id else None, "reason": c.reason, "details": c.details}
                for c in cols
            ],
            model_version=str(weights.get("model_version", "linkage-v1.0.0")),
        )

    async def review_edge(
        self, user_id: uuid.UUID, edge_id: uuid.UUID, status: str, note: str | None
    ) -> IdentityEdgePublic:
        await self._set_rls(user_id)
        edge = await self.edges.get_edge(edge_id, user_id)
        if not edge:
            raise HTTPException(status_code=404, detail="Edge not found")
        edge = await self.edges.set_review(edge, status, note)
        await self.audit.log(
            "identity.edge_reviewed",
            user_id=user_id,
            resource_type="identity_edge",
            resource_id=str(edge_id),
            details={"review_status": status},
        )
        await self.session.commit()
        return IdentityEdgePublic.model_validate(edge)

    async def accepted_edge_count(self, user_id: uuid.UUID) -> int:
        return await self.edges.count_accepted_edges(user_id)
