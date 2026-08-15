from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.deltas import finding_delta, score_delta
from app.repositories.alert_repository import AlertRepository
from app.repositories.finding_repository import FindingRepository
from app.repositories.score_repository import ScoreRepository
from app.schemas.recommendations_alerts import AlertPublic
from app.services.audit_service import AuditService
from app.services.discovery_service import DiscoveryService

logger = get_logger(__name__)


class AlertService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AlertRepository(session)
        self.scores = ScoreRepository(session)
        self.findings = FindingRepository(session)
        self.audit = AuditService(session)
        self.settings = get_settings()

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def list_alerts(self, user_id: uuid.UUID, unread_only: bool = False) -> list[AlertPublic]:
        await self._set_rls(user_id)
        rows = await self.repo.list(user_id, unread_only=unread_only)
        return [AlertPublic.model_validate(r) for r in rows]

    async def mark_read(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> AlertPublic:
        await self._set_rls(user_id)
        row = await self.repo.get(alert_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        await self.repo.mark_read(row)
        await self.session.commit()
        return AlertPublic.model_validate(row)

    async def dismiss(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> dict:
        await self._set_rls(user_id)
        row = await self.repo.get(alert_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        await self.repo.dismiss(row)
        await self.session.commit()
        return {"message": "Dismissed"}

    async def emit(
        self,
        user_id: uuid.UUID,
        *,
        kind: str,
        title: str,
        body: str,
        severity: str = "info",
        identifier_id: uuid.UUID | None = None,
        payload: dict | None = None,
    ) -> Alert:
        row = await self.repo.create(
            user_id=user_id,
            kind=kind,
            title=title,
            body=body,
            severity=severity,
            identifier_id=identifier_id,
            payload=payload,
        )
        return row

    async def compute_deltas(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        await self._set_rls(user_id)
        history = await self.scores.history(user_id, identifier_id=identifier_id, limit=2)
        score_part = None
        if len(history) >= 2:
            newer, older = history[0], history[1]
            sd = score_delta(
                float(older.score_combined),
                float(newer.score_combined),
                older.severity,
                newer.severity,
            )
            score_part = sd.to_dict()
            # alert on jump up
            if sd.delta >= self.settings.alert_score_jump_threshold:
                await self.emit(
                    user_id,
                    kind="score_jump",
                    title=f"PDSS increased by {sd.delta:.1f}",
                    body=sd.to_dict()["summary"],
                    severity="high" if sd.delta >= 2 else "medium",
                    identifier_id=identifier_id,
                    payload=sd.to_dict(),
                )

        # finding delta: compare open set fingerprint via times_seen / status — simplified
        findings = await self.findings.list_findings(user_id, identifier_id=identifier_id, limit=500)
        open_ids = {str(f.id) for f in findings if f.status == "open"}
        # Without full previous snapshot, use first_seen_scan heuristic: new if times_seen==1 and recent
        now = datetime.now(UTC)
        new_ids = [
            str(f.id)
            for f in findings
            if f.status == "open"
            and f.times_seen == 1
            and f.first_seen_at
            and (now - f.first_seen_at).total_seconds() < 86400
        ]
        high_new = [
            f
            for f in findings
            if str(f.id) in set(new_ids) and f.severity_hint in {"high", "critical"}
        ]
        if self.settings.alert_new_high_severity and high_new:
            for f in high_new[:5]:
                await self.emit(
                    user_id,
                    kind="severity_high",
                    title=f"New high-severity finding: {f.title[:80]}",
                    body=f.summary[:500],
                    severity="high",
                    identifier_id=f.identifier_id,
                    payload={"finding_id": str(f.id), "source": f.source, "kind": f.kind},
                )

        fd = finding_delta(set(), open_ids)  # baseline-lite
        fd.new_finding_ids = new_ids
        finding_part = fd.to_dict()

        await self.session.commit()
        summary = " | ".join(
            filter(
                None,
                [
                    score_part["summary"] if score_part else None,
                    finding_part["summary"],
                ],
            )
        )
        return {"score": score_part, "findings": finding_part, "summary": summary or "No deltas"}

    async def request_rescan(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        *,
        connector_ids: list[str] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Quota-aware rescan — wraps DiscoveryService.create_scan with cooldown."""
        await self._set_rls(user_id)
        now = datetime.now(UTC)
        policy = await self.repo.get_policy(user_id, identifier_id)
        cooldown = timedelta(hours=self.settings.rescan_cooldown_hours)

        if not force and policy and policy.last_rescan_at:
            elapsed = now - policy.last_rescan_at
            if elapsed < cooldown:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rescan cooldown active. Retry after {policy.last_rescan_at + cooldown}",
                )

        discovery = DiscoveryService(self.session)
        scan = await discovery.create_scan(
            user_id,
            identifier_id,
            connector_ids=connector_ids,
            layer_scope="surface",
        )

        # update policy timestamps
        interval = (
            policy.interval_hours
            if policy
            else self.settings.scheduled_rescan_interval_hours
        )
        if not policy:
            policy = await self.repo.upsert_policy(
                user_id=user_id,
                identifier_id=identifier_id,
                enabled=self.settings.feature_scheduled_rescans,
                interval_hours=interval,
            )
        await self.repo.touch_policy(policy, now, interval)

        await self.emit(
            user_id,
            kind="rescan_available",
            title="Rescan started",
            body=f"Scan {scan.id} queued for identifier {identifier_id}",
            severity="info",
            identifier_id=identifier_id,
            payload={"scan_id": str(scan.id)},
        )
        await self.session.commit()
        return {
            "message": "Rescan started",
            "scan_id": str(scan.id),
            "status": scan.status,
        }

    async def upsert_rescan_policy(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        enabled: bool,
        interval_hours: int,
    ) -> dict[str, Any]:
        await self._set_rls(user_id)
        now = datetime.now(UTC)
        row = await self.repo.upsert_policy(
            user_id=user_id,
            identifier_id=identifier_id,
            enabled=enabled,
            interval_hours=interval_hours,
        )
        if enabled and not row.next_eligible_at:
            row.next_eligible_at = now + timedelta(hours=interval_hours)
            await self.session.flush()
        await self.session.commit()
        return {
            "identifier_id": str(identifier_id),
            "enabled": row.enabled,
            "interval_hours": row.interval_hours,
            "last_rescan_at": row.last_rescan_at.isoformat() if row.last_rescan_at else None,
            "next_eligible_at": row.next_eligible_at.isoformat() if row.next_eligible_at else None,
        }

    async def reconcile_scheduled(self) -> dict[str, int]:
        """Beat: due policies → rescan if quota allows; purge old alerts."""
        now = datetime.now(UTC)
        due = await self.repo.list_due_policies(now)
        started = 0
        skipped = 0
        for pol in due:
            if not self.settings.feature_scheduled_rescans:
                skipped += 1
                continue
            try:
                await self._set_rls(pol.user_id)
                await self.request_rescan(pol.user_id, pol.identifier_id, force=False)
                started += 1
            except HTTPException:
                skipped += 1
            except Exception:
                logger.exception("scheduled_rescan_failed", policy_id=str(pol.id))
                skipped += 1
        purged = await self.repo.purge_old(self.settings.alert_retention_days)
        await self.session.commit()
        return {"started": started, "skipped": skipped, "alerts_purged": purged}
