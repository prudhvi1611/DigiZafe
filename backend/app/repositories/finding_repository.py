from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.findings_normalize import NormalizedFinding
from app.models.observation_finding import EvidenceBlob, Finding, Observation


class FindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def add_observation(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        scan_id: uuid.UUID | None,
        connector_run_id: uuid.UUID | None,
        obs: dict[str, Any],
    ) -> Observation:
        ttl_h = self.settings.evidence_raw_ttl_hours
        expires = datetime.now(UTC) + timedelta(hours=ttl_h)
        row = Observation(
            user_id=user_id,
            identifier_id=identifier_id,
            scan_id=scan_id,
            connector_run_id=connector_run_id,
            kind=str(obs.get("kind") or "other"),
            source=str(obs.get("source") or "unknown"),
            title=str(obs.get("title") or "")[:512],
            summary=str(obs.get("summary") or "")[:4000],
            confidence=float(obs.get("confidence") or 0.5),
            layer=str(obs.get("layer") or "surface"),
            raw_ref=(str(obs["raw_ref"])[:512] if obs.get("raw_ref") else None),
            attributes=obs.get("attributes"),
            attribution=obs.get("attribution"),
            payload=obs,  # already redacted observation dict
            expires_at=expires,
            observed_at=None,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def upsert_finding(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        scan_id: uuid.UUID | None,
        nf: NormalizedFinding,
    ) -> tuple[Finding, bool]:
        """Returns (finding, created)."""
        result = await self.session.execute(
            select(Finding).where(
                Finding.user_id == user_id,
                Finding.identifier_id == identifier_id,
                Finding.source == nf.source,
                Finding.fingerprint == nf.fingerprint,
            )
        )
        existing = result.scalar_one_or_none()
        now = nf.observed_at or datetime.now(UTC)
        if existing:
            existing.last_seen_at = now
            existing.last_seen_scan_id = scan_id
            existing.times_seen = (existing.times_seen or 1) + 1
            existing.confidence = max(existing.confidence, nf.confidence)
            # Merge attributes lightly
            if nf.attributes:
                existing.attributes = {**(existing.attributes or {}), **nf.attributes}
            if nf.summary and len(nf.summary) > len(existing.summary or ""):
                existing.summary = nf.summary
            existing.severity_hint = nf.severity_hint or existing.severity_hint
            await self.session.flush()
            return existing, False

        row = Finding(
            user_id=user_id,
            identifier_id=identifier_id,
            kind=nf.kind,
            source=nf.source,
            title=nf.title,
            summary=nf.summary,
            severity_hint=nf.severity_hint,
            confidence=nf.confidence,
            layer=nf.layer,
            track=nf.track,
            fingerprint=nf.fingerprint,
            raw_ref=nf.raw_ref,
            attributes=nf.attributes,
            attribution=nf.attribution,
            first_seen_scan_id=scan_id,
            last_seen_scan_id=scan_id,
            first_seen_at=now,
            last_seen_at=now,
            times_seen=1,
            status="open",
        )
        self.session.add(row)
        await self.session.flush()
        return row, True

    async def add_evidence(
        self,
        *,
        user_id: uuid.UUID,
        layer: str,
        body: dict[str, Any],
        identifier_id: uuid.UUID | None = None,
        scan_id: uuid.UUID | None = None,
        finding_id: uuid.UUID | None = None,
        observation_id: uuid.UUID | None = None,
        expires_at: datetime | None = None,
    ) -> EvidenceBlob:
        import json

        raw = json.dumps(body, default=str)
        row = EvidenceBlob(
            user_id=user_id,
            identifier_id=identifier_id,
            scan_id=scan_id,
            finding_id=finding_id,
            observation_id=observation_id,
            layer=layer,
            content_type="application/json",
            body=body,
            size_bytes=len(raw.encode("utf-8")),
            expires_at=expires_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_findings(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        source: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Finding]:
        q = select(Finding).where(Finding.user_id == user_id)
        if identifier_id:
            q = q.where(Finding.identifier_id == identifier_id)
        if source:
            q = q.where(Finding.source == source)
        q = q.order_by(Finding.last_seen_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(q)
        return result.scalars().all()

    async def get_finding(
        self, finding_id: uuid.UUID, user_id: uuid.UUID
    ) -> Finding | None:
        result = await self.session.execute(
            select(Finding).where(Finding.id == finding_id, Finding.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def purge_expired_evidence(self, now: datetime | None = None) -> dict[str, int]:
        now = now or datetime.now(UTC)
        # observations
        r1 = await self.session.execute(
            delete(Observation).where(Observation.expires_at < now)
        )
        # evidence raw/summary with expires_at
        r2 = await self.session.execute(
            delete(EvidenceBlob).where(
                EvidenceBlob.expires_at.is_not(None),
                EvidenceBlob.expires_at < now,
            )
        )
        await self.session.flush()
        return {
            "observations_deleted": r1.rowcount or 0,
            "evidence_blobs_deleted": r2.rowcount or 0,
        }
