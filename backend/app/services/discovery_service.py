from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.registry import build_connectors
from app.connectors.sdk.types import ConnectorContext
from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.scan_states import ConnectorRunStatus, ScanStatus
from app.models.connector_config import ConnectorConfig
from app.repositories.finding_repository import FindingRepository
from app.repositories.scan_repository import ScanRepository
from app.services.audit_service import AuditService
from app.services.consent_service import ConsentService
from app.services.evidence_service import EvidenceService
from app.services.identifier_service import IdentifierService

logger = get_logger(__name__)


class DiscoveryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.scans = ScanRepository(session)
        self.findings = FindingRepository(session)
        self.identifiers = IdentifierService(session)
        self.consent = ConsentService(session)
        self.audit = AuditService(session)
        self.evidence = EvidenceService(session)
        self.settings = get_settings()

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def create_scan(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        connector_ids: list[str] | None = None,
        layer_scope: str = "surface",
    ) -> Any:
        await self._set_rls(user_id)

        # G1 hard gate
        ident = await self.identifiers.require_verified(user_id, identifier_id)

        # Sprint 11: Amber consent gating
        if layer_scope in ("deep", "constrained_dark") and self.settings.amber_scan_requires_consent:
            has_consent = await self.consent.ensure_consent(
                user_id=user_id,
                purpose="amber_discovery",
                scope=layer_scope,
            )
            if not has_consent:
                raise HTTPException(
                    status_code=403,
                    detail=f"Explicit consent required for {layer_scope} scans",
                )

        # Quotas
        active = await self.scans.count_active_for_user(user_id)
        if active >= self.settings.scan_max_concurrent_per_user:
            raise HTTPException(
                status_code=429,
                detail=f"Max concurrent scans ({self.settings.scan_max_concurrent_per_user}) reached",
            )
        today = await self.scans.count_today_for_user(user_id)
        if today >= self.settings.default_user_scan_quota_per_day:
            raise HTTPException(
                status_code=429,
                detail="Daily scan quota exceeded",
            )

        connectors = await build_connectors()
        db_flags = await self._load_db_flags()

        if connector_ids:
            selected = [c for c in connector_ids if c in connectors and c != "pwned_passwords"]
        else:
            selected = [
                cid
                for cid, c in connectors.items()
                if c.supports(ident.type)
                and cid != "pwned_passwords"
                and c.is_enabled_by_config()
                and (db_flags.get(cid) is not False)
            ]

        if not selected:
            raise HTTPException(status_code=400, detail="No connectors available for this identifier type")

        deadline = datetime.now(UTC) + timedelta(
            minutes=self.settings.scan_default_deadline_minutes
        )
        scan = await self.scans.create(
            user_id=user_id,
            identifier_id=ident.id,
            connector_ids=selected,
            deadline_at=deadline,
            layer_scope=layer_scope,
        )
        for cid in selected:
            await self.scans.add_connector_run(scan=scan, connector_id=cid)

        await self.audit.log(
            "scan.created",
            user_id=user_id,
            resource_type="scan",
            resource_id=str(scan.id),
            details={"identifier_id": str(ident.id), "connectors": selected},
        )
        await self.session.commit()

        # Enqueue worker (import late to avoid circular)
        from app.tasks.discovery_tasks import execute_scan_task

        execute_scan_task.delay(str(scan.id))

        # Reload with runs
        return await self.scans.get(scan.id, user_id)

    async def get_scan(self, user_id: uuid.UUID, scan_id: uuid.UUID):
        await self._set_rls(user_id)
        scan = await self.scans.get(scan_id, user_id)
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        return scan

    async def list_scans(self, user_id: uuid.UUID, limit: int = 50, offset: int = 0):
        await self._set_rls(user_id)
        return await self.scans.list_for_user(user_id, limit=limit, offset=offset)

    async def cancel_scan(self, user_id: uuid.UUID, scan_id: uuid.UUID):
        await self._set_rls(user_id)
        scan = await self.scans.get(scan_id, user_id)
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        if scan.status in {ScanStatus.COMPLETED.value, ScanStatus.PARTIAL.value, ScanStatus.FAILED.value, ScanStatus.CANCELLED.value, ScanStatus.TIMED_OUT.value}:
            raise HTTPException(status_code=400, detail="Scan already terminal")
        await self.scans.set_scan_status(scan, ScanStatus.CANCELLED, message="Cancelled by user")
        for run in scan.connector_runs or []:
            if run.status in {ConnectorRunStatus.PENDING.value, ConnectorRunStatus.RUNNING.value}:
                await self.scans.set_run_status(
                    run, ConnectorRunStatus.SKIPPED, skip_reason="cancelled"
                )
        await self.audit.log("scan.cancelled", user_id=user_id, resource_type="scan", resource_id=str(scan_id))
        await self.session.commit()
        return scan

    async def list_findings(
        self,
        user_id: uuid.UUID,
        *,
        identifier_id: uuid.UUID | None = None,
        source: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        await self._set_rls(user_id)
        return await self.findings.list_findings(
            user_id, identifier_id=identifier_id, source=source, limit=limit, offset=offset
        )

    async def get_finding(self, user_id: uuid.UUID, finding_id: uuid.UUID):
        await self._set_rls(user_id)
        row = await self.findings.get_finding(finding_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Finding not found")
        return row

    async def _load_db_flags(self) -> dict[str, bool]:
        result = await self.session.execute(select(ConnectorConfig))
        return {r.connector_id: r.enabled for r in result.scalars().all()}

    # ---------- Worker entry ----------
    async def execute_scan(self, scan_id: uuid.UUID) -> None:
        """
        Run all pending connector runs for a scan.
        Called from Celery worker. Self-healing: reconcile will recover stuck scans.
        """
        scan = await self.scans.get_by_id_internal(scan_id)
        if not scan:
            logger.warning("scan_not_found", scan_id=str(scan_id))
            return

        await self._set_rls(scan.user_id)

        if scan.status == ScanStatus.CANCELLED.value:
            return
        if scan.status in {
            ScanStatus.COMPLETED.value,
            ScanStatus.PARTIAL.value,
            ScanStatus.FAILED.value,
            ScanStatus.TIMED_OUT.value,
        }:
            return

        # Deadline check
        now = datetime.now(UTC)
        if scan.deadline_at < now:
            await self.scans.set_scan_status(scan, ScanStatus.TIMED_OUT, message="Deadline exceeded", error="deadline")
            for run in scan.connector_runs or []:
                if run.status in {ConnectorRunStatus.PENDING.value, ConnectorRunStatus.RUNNING.value}:
                    await self.scans.set_run_status(run, ConnectorRunStatus.TIMED_OUT, error="scan_deadline")
            await self.session.commit()
            return

        await self.scans.set_scan_status(scan, ScanStatus.RUNNING, message="Running connectors")
        await self.session.commit()

        # Reload
        scan = await self.scans.get_by_id_internal(scan_id)
        assert scan

        connectors = await build_connectors()
        db_flags = await self._load_db_flags()

        # Load identifier
        from app.repositories.identifier_repository import IdentifierRepository

        id_repo = IdentifierRepository(self.session)
        ident = await id_repo.get(scan.identifier_id, scan.user_id)
        if not ident or not ident.is_verified:
            await self.scans.set_scan_status(
                scan, ScanStatus.FAILED, message="Identifier not verified", error="G1_VIOLATION"
            )
            await self.session.commit()
            return

        if scan.layer_scope in ("deep", "constrained_dark") and self.settings.amber_scan_requires_consent:
            has_consent = await self.consent.has_active_grant(
                user_id=scan.user_id,
                identifier_id=ident.id,
                purpose="amber_discovery",
                scope=scan.layer_scope,
            )
            if not has_consent:
                await self.scans.set_scan_status(
                    scan, ScanStatus.FAILED, message=f"Missing explicit consent for {scan.layer_scope}", error="AMBER_CONSENT_VIOLATION"
                )
                await self.session.commit()
                return

        for run in list(scan.connector_runs or []):
            # Re-check cancel / deadline between connectors
            await self.session.refresh(scan)
            if scan.status == ScanStatus.CANCELLED.value:
                break
            if scan.deadline_at < datetime.now(UTC):
                await self.scans.set_scan_status(scan, ScanStatus.TIMED_OUT, message="Deadline exceeded")
                if run.status == ConnectorRunStatus.PENDING.value:
                    await self.scans.set_run_status(run, ConnectorRunStatus.TIMED_OUT)
                break

            if run.status != ConnectorRunStatus.PENDING.value:
                continue

            cid = run.connector_id
            connector = connectors.get(cid)
            if not connector:
                await self.scans.set_run_status(
                    run, ConnectorRunStatus.SKIPPED, skip_reason="unknown_connector"
                )
                await self.scans.recompute_progress(scan)
                await self.session.commit()
                continue

            env_on = connector.is_enabled_by_config()
            db_on = db_flags.get(cid)
            effective = env_on if db_on is None else (env_on and db_on)
            if not effective:
                await self.scans.set_run_status(run, ConnectorRunStatus.SKIPPED, skip_reason="disabled")
                await self.scans.recompute_progress(scan)
                await self.session.commit()
                continue

            purpose = f"discovery.{cid}"
            if connector.capability.sends_identifier:
                await self.consent.ensure_consent(
                    scan.user_id, purpose=purpose, auto_grant=True, scope=str(ident.id)
                )

            await self.scans.set_run_status(run, ConnectorRunStatus.RUNNING)
            await self.scans.recompute_progress(scan)
            await self.session.commit()

            ctx = ConnectorContext(
                user_id=scan.user_id,
                identifier_id=ident.id,
                identifier_type=ident.type,
                identifier_canonical=ident.value_canonical,
                consent_purpose=purpose,
            )

            try:
                result = await connector.run(ctx, enabled_override=True)
            except Exception as e:
                logger.exception("connector_run_exception", connector=cid, scan_id=str(scan_id))
                await self.scans.set_run_status(
                    run, ConnectorRunStatus.FAILED, error=str(e)[:2000]
                )
                await self.scans.recompute_progress(scan)
                await self.session.commit()
                continue

            # Ledger
            if connector.capability.sends_identifier and not result.skipped:
                host = {
                    "xposedornot": "api.xposedornot.com",
                    "crtsh": "crt.sh",
                    "rdap": "rdap.org",
                    "github": "api.github.com",
                    "username_presence": "multi",
                    "serp_ddg": "html.duckduckgo.com",
                    "gravatar": "www.gravatar.com",
                }.get(cid, cid)
                await self.consent.record_egress(
                    purpose=purpose,
                    destination_host=host,
                    method="GET",
                    status_code=200 if result.success else None,
                    success=result.success and not result.skipped,
                    user_id=scan.user_id,
                    identifier_id=ident.id,
                    summary={
                        "connector": cid,
                        "scan_id": str(scan.id),
                        "cache_hit": result.cache_hit,
                        "skipped": result.skipped,
                        "observation_count": len(result.observations),
                    },
                )

            if result.skipped:
                await self.scans.set_run_status(
                    run,
                    ConnectorRunStatus.SKIPPED,
                    skip_reason=result.skip_reason,
                    error=result.error,
                    cache_hit=result.cache_hit,
                    result_meta=result.to_dict().get("meta") or {"skip_reason": result.skip_reason},
                )
            elif not result.success:
                await self.scans.set_run_status(
                    run,
                    ConnectorRunStatus.FAILED,
                    error=result.error or "connector_failed",
                    cache_hit=result.cache_hit,
                    result_meta=result.meta,
                )
            else:
                obs_dicts = [o.to_dict() for o in result.observations]
                obs_n, find_n = await self.evidence.ingest_connector_observations(
                    user_id=scan.user_id,
                    identifier_id=ident.id,
                    scan_id=scan.id,
                    connector_run_id=run.id,
                    observations=obs_dicts,
                    connector_id=cid,
                )
                meta = dict(result.meta or {})
                if result.observations:
                    # carry attribution
                    for o in result.observations:
                        if o.attribution:
                            meta.setdefault("attribution", o.attribution)
                            break
                if not meta.get("attribution") and connector.capability.attribution:
                    meta["attribution"] = connector.capability.attribution

                await self.scans.set_run_status(
                    run,
                    ConnectorRunStatus.SUCCEEDED,
                    cache_hit=result.cache_hit,
                    observation_count=obs_n,
                    finding_count=find_n,
                    result_meta=meta,
                )

            await self.scans.recompute_progress(scan)
            await self.session.commit()

        # Finalize
        scan = await self.scans.get_by_id_internal(scan_id)
        if scan and scan.status not in {
                ScanStatus.CANCELLED.value,
                ScanStatus.TIMED_OUT.value,
            }:
            await self.scans.try_finalize(scan)
            await self.audit.log(
                "scan.finished",
                user_id=scan.user_id,
                resource_type="scan",
                resource_id=str(scan.id),
                details={
                    "status": scan.status,
                    "observation_count": scan.observation_count,
                    "finding_count": scan.finding_count,
                },
            )
            await self.session.commit()

            # Sprint 5: closed-loop score (best-effort)
            try:
                from app.services.scoring_service import ScoringService
                scoring = ScoringService(self.session)
                await scoring.compute(
                    scan.user_id,
                    identifier_id=scan.identifier_id,
                    persist=True,
                    trigger="post_scan",
                )
            except Exception:
                logger.exception("post_scan_score_failed", scan_id=str(scan.id))


    async def reconcile(self) -> dict[str, int]:
        """
        Self-healing sweep:
        - Timeout past-deadline scans
        - Re-enqueue pending scans with no progress
        - Purge expired evidence
        """
        now = datetime.now(UTC)
        timed_out = 0
        requeued = 0

        stale = await self.scans.list_stale_running(now)
        for scan in stale:
            await self._set_rls(scan.user_id)
            if scan.deadline_at < now:
                await self.scans.set_scan_status(
                    scan, ScanStatus.TIMED_OUT, message="Reconcile: deadline exceeded", error="reconcile_timeout"
                )
                for run in scan.connector_runs or []:
                    if run.status in {
                        ConnectorRunStatus.PENDING.value,
                        ConnectorRunStatus.RUNNING.value,
                    }:
                        await self.scans.set_run_status(
                            run, ConnectorRunStatus.TIMED_OUT, error="reconcile_timeout"
                        )
                timed_out += 1
            elif scan.status == ScanStatus.PENDING.value:
                from app.tasks.discovery_tasks import execute_scan_task

                execute_scan_task.delay(str(scan.id))
                requeued += 1

        purged = await self.evidence.purge_expired()
        await self.session.commit()
        logger.info("scan_reconcile", timed_out=timed_out, requeued=requeued, **purged)
        return {"timed_out": timed_out, "requeued": requeued, **purged}
