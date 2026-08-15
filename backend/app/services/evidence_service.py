from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.findings_normalize import (
    normalize_connector_result_observations,
)
from app.repositories.finding_repository import FindingRepository


class EvidenceService:
    """3-layer evidence + observation → finding pipeline."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FindingRepository(session)
        self.settings = get_settings()

    async def ingest_connector_observations(
        self,
        *,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        scan_id: uuid.UUID,
        connector_run_id: uuid.UUID,
        observations: list[dict[str, Any]],
        connector_id: str,
    ) -> tuple[int, int]:
        """
        Persist observations (layer raw), normalize → findings (durable),
        write summary evidence. Returns (obs_count, findings_created_or_updated).
        """
        if not observations:
            return 0, 0

        obs_count = 0
        finding_touches = 0
        normalized = normalize_connector_result_observations(observations)

        raw_ttl = datetime.now(UTC) + timedelta(hours=self.settings.evidence_raw_ttl_hours)
        summary_ttl = datetime.now(UTC) + timedelta(days=self.settings.evidence_summary_ttl_days)

        for o in observations:
            if not isinstance(o, dict):
                continue
            obs_row = await self.repo.add_observation(
                user_id=user_id,
                identifier_id=identifier_id,
                scan_id=scan_id,
                connector_run_id=connector_run_id,
                obs=o,
            )
            await self.repo.add_evidence(
                user_id=user_id,
                layer="raw",
                body={"observation": o, "connector_id": connector_id},
                identifier_id=identifier_id,
                scan_id=scan_id,
                observation_id=obs_row.id,
                expires_at=raw_ttl,
            )
            obs_count += 1

        for nf in normalized:
            finding, created = await self.repo.upsert_finding(
                user_id=user_id,
                identifier_id=identifier_id,
                scan_id=scan_id,
                nf=nf,
            )
            finding_touches += 1
            # summary layer
            await self.repo.add_evidence(
                user_id=user_id,
                layer="summary",
                body={
                    "finding_id": str(finding.id),
                    "kind": nf.kind,
                    "source": nf.source,
                    "title": nf.title,
                    "severity_hint": nf.severity_hint,
                    "confidence": nf.confidence,
                    "raw_ref": nf.raw_ref,
                    "attribution": nf.attribution,
                    "created": created,
                },
                identifier_id=identifier_id,
                scan_id=scan_id,
                finding_id=finding.id,
                expires_at=summary_ttl,
            )
            # durable layer (no TTL) — redacted metadata only
            await self.repo.add_evidence(
                user_id=user_id,
                layer="durable",
                body={
                    "finding_id": str(finding.id),
                    "fingerprint": nf.fingerprint,
                    "kind": nf.kind,
                    "source": nf.source,
                    "title": nf.title,
                    "severity_hint": nf.severity_hint,
                    "track": nf.track,
                    "layer": nf.layer,
                    "attributes_keys": list((nf.attributes or {}).keys()),
                    "attribution": nf.attribution,
                },
                identifier_id=identifier_id,
                scan_id=scan_id,
                finding_id=finding.id,
                expires_at=None,
            )

        return obs_count, finding_touches

    async def purge_expired(self) -> dict[str, int]:
        return await self.repo.purge_expired_evidence()
