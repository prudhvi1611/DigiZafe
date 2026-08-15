import uuid
import logging
from typing import Sequence
from urllib.parse import urlparse
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.identity_anchor import IdentityAnchor, IdentityAlias, ConfirmedProfileReference
from app.models.candidate_profile import CandidateDiscoveryRun, CandidateProfile
from app.models.consent_egress import ConsentRecord

logger = logging.getLogger(__name__)

class CandidateDiscoveryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_anchor(self, user_id: uuid.UUID) -> IdentityAnchor | None:
        stmt = select(IdentityAnchor).where(
            IdentityAnchor.user_id == user_id, 
            IdentityAnchor.status == "active"
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def check_consent(self, user_id: uuid.UUID) -> bool:
        stmt = select(ConsentRecord).where(
            ConsentRecord.user_id == user_id,
            ConsentRecord.granted == True,
            ConsentRecord.purpose == "discovery.maigret"
        )
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None

    async def get_eligible_inputs(self, user_id: uuid.UUID, anchor_id: uuid.UUID, input_ids: list[uuid.UUID] | None = None) -> Sequence[IdentityAlias]:
        # For MVP, only active IdentityAlias records of type username/handle are eligible
        conditions = [
            IdentityAlias.user_id == user_id,
            IdentityAlias.anchor_id == anchor_id,
            IdentityAlias.status == "active",
            IdentityAlias.alias_type.in_(["username", "handle"])
        ]
        if input_ids:
            conditions.append(IdentityAlias.id.in_(input_ids))
            
        stmt = select(IdentityAlias).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_discovery_run(
        self, 
        user_id: uuid.UUID, 
        input_ids: list[uuid.UUID] | None = None,
        source_tool: str = "maigret",
        source_tool_version: str = "0.4.4",
        orchestration_run_id: uuid.UUID | None = None,
        plan_item_id: uuid.UUID | None = None
    ) -> CandidateDiscoveryRun | None:
        anchor = await self.get_active_anchor(user_id)
        if not anchor:
            return None
        
        has_consent = await self.check_consent(user_id)
        if not has_consent:
            raise PermissionError("Consent required for OSINT discovery")

        inputs = await self.get_eligible_inputs(user_id, anchor.id, input_ids)
        if not inputs:
            raise ValueError("No eligible inputs found")

        run = CandidateDiscoveryRun(
            user_id=user_id,
            anchor_id=anchor.id,
            anchor_version=anchor.version,
            orchestration_run_id=orchestration_run_id,
            plan_item_id=plan_item_id,
            source_tool=source_tool,
            source_tool_version=source_tool_version,
            status="queued",
            input_count=len(inputs)
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    def _canonicalize_url(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            # Remove trailing slashes and lowercase hostname
            canonical = f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path}"
            return canonical.rstrip("/")
        except Exception:
            return url.strip().rstrip("/")

    async def persist_candidates(
        self, 
        run: CandidateDiscoveryRun, 
        source_input: IdentityAlias, 
        raw_results: dict
    ) -> int:
        count = 0
        now = datetime.now(timezone.utc)
        for site_name, data in raw_results.items():
            if not isinstance(data, dict):
                continue
            
            # Maigret usually has 'url_user' or 'url_main' or 'status'
            status = data.get("status", {}).get("status")
            profile_url = data.get("url_user")
            
            if not profile_url:
                continue

            canonical_url = self._canonicalize_url(profile_url)
            
            from app.services.discovery.canonical_fact_service import CanonicalFactService
            from app.models.candidate_provenance import CandidateProvenanceObservation
            from app.services.discovery.connectors.registry import ConnectorCapability
            
            fact_key = CanonicalFactService.generate_profile_existence_key(site_name, canonical_url)
            
            # If not claimed, we record an absence
            if status != "Claimed": 
                now = datetime.now(timezone.utc)
                stmt_prov = select(CandidateProvenanceObservation).where(
                    CandidateProvenanceObservation.user_id == run.user_id,
                    CandidateProvenanceObservation.canonical_fact_key == fact_key,
                    CandidateProvenanceObservation.superseded_at.is_(None)
                ).order_by(CandidateProvenanceObservation.valid_from.desc())
                
                existing_prov = (await self.db.execute(stmt_prov)).scalars().first()
                if not existing_prov:
                    continue
                
                existing_prov.superseded_at = now
                self.db.add(existing_prov)
                    
                prov = CandidateProvenanceObservation(
                    user_id=run.user_id,
                    candidate_profile_id=existing_prov.candidate_profile_id,
                    discovery_run_id=run.id,
                    connector_type=run.source_tool,
                    connector_version=run.source_tool_version,
                    capability=ConnectorCapability.PROFILE_LOOKUP.value,
                    input_alias_id=source_input.id,
                    observation_type="maigret_profile_absent",
                    canonical_fact_key=fact_key,
                    normalized_payload=data,
                    observed_at=existing_prov.observed_at if existing_prov else now,
                    valid_from=now,
                    last_observed_at=now
                )
                self.db.add(prov)
                await self.db.flush()
                
                from app.tasks.temporal_tasks import process_temporal_observation
                process_temporal_observation.delay(str(prov.id))
                continue
            
            canonical_url = self._canonicalize_url(profile_url)

            # Check if this candidate already exists for this user/platform/canonical_url
            stmt = select(CandidateProfile).where(
                CandidateProfile.user_id == run.user_id,
                CandidateProfile.platform == site_name,
                CandidateProfile.canonical_profile_url == canonical_url
            )
            result = await self.db.execute(stmt)
            existing = result.scalars().first()

            if existing:
                existing.last_observed_at = now
                existing.discovery_run_id = run.id
                existing.source_tool_version = run.source_tool_version
                candidate = existing
            else:
                candidate = CandidateProfile(
                    user_id=run.user_id,
                    discovery_run_id=run.id,
                    anchor_id=run.anchor_id,
                    anchor_version=run.anchor_version,
                    source_input_id=source_input.id,
                    source_input_type="identity_alias",
                    source_input_value_reference=source_input.value_canonical,
                    platform=site_name,
                    profile_url=profile_url,
                    canonical_profile_url=canonical_url,
                    username_observed=source_input.value_display,
                    source_tool=run.source_tool,
                    source_tool_version=run.source_tool_version,
                    first_observed_at=now,
                    last_observed_at=now
                )
                self.db.add(candidate)
                await self.db.flush()
                
            from app.services.discovery.canonical_fact_service import CanonicalFactService
            from app.models.candidate_provenance import CandidateProvenanceObservation
            from app.services.discovery.connectors.registry import ConnectorCapability
            
            fact_key = CanonicalFactService.generate_profile_existence_key(site_name, canonical_url)
            
            stmt_prov = select(CandidateProvenanceObservation).where(
                CandidateProvenanceObservation.user_id == run.user_id,
                CandidateProvenanceObservation.canonical_fact_key == fact_key,
                CandidateProvenanceObservation.superseded_at.is_(None)
            ).order_by(CandidateProvenanceObservation.valid_from.desc())
            
            existing_prov = (await self.db.execute(stmt_prov)).scalars().first()
            
            if existing_prov:
                existing_prov.superseded_at = now
                self.db.add(existing_prov)
                
            prov = CandidateProvenanceObservation(
                user_id=run.user_id,
                candidate_profile_id=candidate.id,
                discovery_run_id=run.id,
                connector_type=run.source_tool,
                connector_version=run.source_tool_version,
                capability=ConnectorCapability.PROFILE_LOOKUP.value,
                input_alias_id=source_input.id,
                observation_type="maigret_profile_observed",
                canonical_fact_key=fact_key,
                normalized_payload=data,
                observed_at=existing_prov.observed_at if existing_prov else now,
                valid_from=now,
                last_observed_at=now
            )
            self.db.add(prov)
            await self.db.flush()
            
            from app.tasks.temporal_tasks import process_temporal_observation
            process_temporal_observation.delay(str(prov.id))
                
            count += 1
            
            # Dispatch enrichment if URL is known (Sprint 18)
            avatar_url = data.get("url_user_avatar") or data.get("avatar_url") or data.get("image")
            if avatar_url:
                from app.tasks.enrichment_tasks import enrich_avatar_task
                provenance = {"source": "maigret_discovery", "site": site_name}
                enrich_avatar_task.delay(
                    user_id_str=str(run.user_id),
                    source_url=avatar_url,
                    provenance=provenance,
                    candidate_id_str=str(candidate.id) if not existing else str(existing.id)
                )
        
        await self.db.commit()
        return count

    async def confirm_candidate(self, user_id: uuid.UUID, candidate_id: uuid.UUID) -> ConfirmedProfileReference | None:
        stmt = select(CandidateProfile).where(
            CandidateProfile.id == candidate_id,
            CandidateProfile.user_id == user_id,
            CandidateProfile.candidate_status == "unreviewed"
        )
        result = await self.db.execute(stmt)
        candidate = result.scalars().first()
        if not candidate:
            return None

        # Change status
        candidate.candidate_status = "confirmed_by_user"
        
        # Create ConfirmedProfileReference
        cpr = ConfirmedProfileReference(
            user_id=user_id,
            anchor_id=candidate.anchor_id,
            platform=candidate.platform,
            profile_url_display=candidate.profile_url,
            profile_url_canonical=candidate.canonical_profile_url,
            username_hint=candidate.username_observed,
            confirmation_method="user_asserted"
        )
        self.db.add(cpr)
        await self.db.commit()
        await self.db.refresh(cpr)
        
        # Trigger cluster sync asynchronously
        from app.tasks.enrichment_tasks import sync_cluster_task
        sync_cluster_task.delay(str(candidate.anchor_id), str(user_id))
        
        return cpr

    async def dismiss_candidate(self, user_id: uuid.UUID, candidate_id: uuid.UUID) -> bool:
        stmt = select(CandidateProfile).where(
            CandidateProfile.id == candidate_id,
            CandidateProfile.user_id == user_id,
            CandidateProfile.candidate_status == "unreviewed"
        )
        result = await self.db.execute(stmt)
        candidate = result.scalars().first()
        if not candidate:
            return False

        candidate.candidate_status = "dismissed"
        await self.db.commit()
        return True

    async def execute_osintgram_run(self, run_id: uuid.UUID) -> None:
        stmt = select(CandidateDiscoveryRun).where(CandidateDiscoveryRun.id == run_id)
        result = await self.db.execute(stmt)
        run = result.scalars().first()
        if not run or run.status != "queued":
            return
            
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        from app.services.discovery.connectors.osintgram_adapter import OSINTgramAdapter
        from app.services.discovery.connectors.capability_registry import ConnectorCapability
        from app.models.candidate_provenance import CandidateProvenanceObservation
        
        adapter = OSINTgramAdapter()
        status = await adapter.check_availability()
        if status != "available":
            run.status = "failed"
            run.error_code = status
            run.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return
            
        inputs = await self.get_eligible_inputs(run.user_id, run.anchor_id)
        if not inputs:
            run.status = "failed"
            run.error_code = "no_inputs"
            run.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return
            
        # For simplicity, we just use the first capability string from the run, or assume a default.
        # But run.source_tool tells us it's osintgram. 
        # We will loop over PROFILE_LOOKUP for each input
        
        candidate_count = 0
        has_partial = False
        
        from app.connectors.sdk.redis_clients import get_broker_redis
        from app.services.discovery.connector_budget_service import ConnectorBudgetService
        redis_client = await get_broker_redis()
        budget_svc = ConnectorBudgetService(redis_client)
        
        for alias in inputs:
            
            # Find the plan item for this execution
            from app.models.orchestration import ConnectorExecutionPlanItem
            from app.models.connector_certification import ConnectorCertificationRecord
            
            plan_stmt = select(ConnectorExecutionPlanItem).where(
                ConnectorExecutionPlanItem.discovery_run_id == run.id,
                ConnectorExecutionPlanItem.input_alias_id == alias.id,
                ConnectorExecutionPlanItem.connector_type == "osintgram"
            )
            plan_item = (await self.db.execute(plan_stmt)).scalars().first()
            
            # Fetch active certification for execution context
            cert_stmt = select(ConnectorCertificationRecord).where(
                ConnectorCertificationRecord.connector_type == "osintgram",
                ConnectorCertificationRecord.availability.in_(["available", "test_only", "installed_unverified"])
            ).order_by(ConnectorCertificationRecord.created_at.desc())
            cert_record = (await self.db.execute(cert_stmt)).scalars().first()

            if plan_item:
                plan_item.execution_status = "running"
                if cert_record:
                    plan_item.certification_id = cert_record.id
                    plan_item.runtime_fingerprint = cert_record.runtime_fingerprint
                    plan_item.execution_mode = "mock" if cert_record.availability == "test_only" else "live"
                await self.db.commit()

            lease_id = str(uuid.uuid4())
            acquired = await budget_svc.acquire_connector_lease("osintgram", lease_id)
            if not acquired:
                run.status = "failed"
                run.error_code = "concurrency_limit_exceeded"
                run.completed_at = datetime.now(timezone.utc)
                if plan_item:
                    plan_item.execution_status = "failed"
                    plan_item.outcome = "failure"
                    plan_item.error_category = "concurrency_limit_exceeded"
                await self.db.commit()
                return
                
            try:
                res = await adapter.execute(alias.value_canonical, ConnectorCapability.PROFILE_LOOKUP)
            finally:
                await budget_svc.release_connector_lease("osintgram", lease_id)

            if res.get("status") == "completed":
                observations = res.get("observations", [])
                
                if plan_item:
                    plan_item.execution_status = "completed"
                    plan_item.outcome = "success"
                    plan_item.normalized_result_count = len(observations)
                    await self.db.commit()

                for obs in observations:
                    # Deduplicate CandidateProfile
                    canonical_url = f"https://instagram.com/{alias.value_canonical}"
                    
                    stmt_cand = select(CandidateProfile).where(
                        CandidateProfile.user_id == run.user_id,
                        CandidateProfile.canonical_profile_url == canonical_url
                    )
                    cand_res = await self.db.execute(stmt_cand)
                    existing = cand_res.scalars().first()
                    
                    if existing:
                        candidate = existing
                        candidate.last_observed_at = datetime.now(timezone.utc)
                    else:
                        candidate = CandidateProfile(
                            user_id=run.user_id,
                            discovery_run_id=run.id,
                            anchor_id=run.anchor_id,
                            anchor_version=run.anchor_version,
                            source_input_id=alias.id,
                            source_input_type="identity_alias",
                            source_input_value_reference=alias.value_canonical,
                            platform="instagram",
                            profile_url=canonical_url,
                            canonical_profile_url=canonical_url,
                            username_observed=alias.value_display,
                            source_tool=adapter.CONNECTOR_NAME,
                            source_tool_version=adapter.CONNECTOR_VERSION,
                            first_observed_at=datetime.now(timezone.utc),
                            last_observed_at=datetime.now(timezone.utc)
                        )
                        self.db.add(candidate)
                        await self.db.flush()
                        candidate_count += 1
                        
                    from app.services.discovery.canonical_fact_service import CanonicalFactService
                    
                    fact_key = CanonicalFactService.generate_profile_existence_key("instagram", canonical_url)
                    
                    # Find existing provenance
                    stmt_prov = select(CandidateProvenanceObservation).where(
                        CandidateProvenanceObservation.user_id == run.user_id,
                        CandidateProvenanceObservation.canonical_fact_key == fact_key,
                        CandidateProvenanceObservation.superseded_at.is_(None)
                    ).order_by(CandidateProvenanceObservation.valid_from.desc())
                    
                    existing_prov_res = await self.db.execute(stmt_prov)
                    existing_prov = existing_prov_res.scalars().first()
                    
                    now = datetime.now(timezone.utc)
                    
                    # Check for material change
                    if existing_prov:
                        # Even if identical, we are superseding the old freshness tracking with a new valid_from baseline
                        existing_prov.superseded_at = now
                        self.db.add(existing_prov)
                        
                    # Always emit a new observation to establish a new freshness baseline
                    prov = CandidateProvenanceObservation(
                        user_id=run.user_id,
                        candidate_profile_id=candidate.id,
                        discovery_run_id=run.id,
                        connector_type=adapter.CONNECTOR_NAME,
                        connector_version=adapter.CONNECTOR_VERSION,
                        connector_certification_id=cert_record.id if cert_record else None,
                        runtime_fingerprint=cert_record.runtime_fingerprint if cert_record else None,
                        adapter_version=cert_record.adapter_version if cert_record else None,
                        runtime_version=cert_record.runtime_version if cert_record else None,
                        capability=ConnectorCapability.PROFILE_LOOKUP.value,
                        input_alias_id=alias.id,
                        observation_type="instagram_profile_observed",
                        canonical_fact_key=fact_key,
                        normalized_payload=obs,
                        observed_at=existing_prov.observed_at if existing_prov else now,
                        valid_from=now,
                        last_observed_at=now
                    )
                    self.db.add(prov)
                    await self.db.flush()
                    
                    from app.tasks.temporal_tasks import process_temporal_observation
                    process_temporal_observation.delay(str(prov.id))
                    
                    # Avatar Observation Dispatch
                    avatar_url = obs.get("profile_pic_url")
                    if avatar_url:
                        from app.tasks.enrichment_tasks import enrich_avatar_task
                        enrich_avatar_task.delay(
                            user_id_str=str(run.user_id),
                            source_url=avatar_url,
                            provenance={"source": "osintgram", "site": "instagram"},
                            candidate_id_str=str(candidate.id)
                        )
                        
                    # External Link dispatch
                    bio_link = obs.get("external_url")
                    if bio_link:
                        from app.tasks.enrichment_tasks import extract_cross_links_task
                        extract_cross_links_task.delay(
                            user_id_str=str(run.user_id),
                            candidate_id_str=str(candidate.id),
                            target_url=bio_link,
                            source="osintgram"
                        )
                
                if not observations:
                    # Emit absence
                    canonical_url = f"https://instagram.com/{alias.value_canonical}"
                    from app.services.discovery.canonical_fact_service import CanonicalFactService
                    fact_key = CanonicalFactService.generate_profile_existence_key("instagram", canonical_url)
                    
                    stmt_cand = select(CandidateProfile).where(
                        CandidateProfile.user_id == run.user_id,
                        CandidateProfile.canonical_profile_url == canonical_url
                    )
                    existing_cand = (await self.db.execute(stmt_cand)).scalars().first()
                    if not existing_cand:
                        continue
                    
                    stmt_prov = select(CandidateProvenanceObservation).where(
                        CandidateProvenanceObservation.user_id == run.user_id,
                        CandidateProvenanceObservation.canonical_fact_key == fact_key,
                        CandidateProvenanceObservation.superseded_at.is_(None)
                    ).order_by(CandidateProvenanceObservation.valid_from.desc())
                    existing_prov = (await self.db.execute(stmt_prov)).scalars().first()
                    
                    now = datetime.now(timezone.utc)
                    if existing_prov:
                        existing_prov.superseded_at = now
                        self.db.add(existing_prov)
                        
                    prov = CandidateProvenanceObservation(
                        user_id=run.user_id,
                        candidate_profile_id=existing_cand.id,
                        discovery_run_id=run.id,
                        connector_type=adapter.CONNECTOR_NAME,
                        connector_version=adapter.CONNECTOR_VERSION,
                        connector_certification_id=cert_record.id if cert_record else None,
                        runtime_fingerprint=cert_record.runtime_fingerprint if cert_record else None,
                        adapter_version=cert_record.adapter_version if cert_record else None,
                        runtime_version=cert_record.runtime_version if cert_record else None,
                        capability=ConnectorCapability.PROFILE_LOOKUP.value,
                        input_alias_id=alias.id,
                        observation_type="instagram_profile_absent",
                        canonical_fact_key=fact_key,
                        normalized_payload={"status": "absent"},
                        observed_at=existing_prov.observed_at if existing_prov else now,
                        valid_from=now,
                        last_observed_at=now
                    )
                    self.db.add(prov)
                    await self.db.flush()
                    
                    from app.tasks.temporal_tasks import process_temporal_observation
                    process_temporal_observation.delay(str(prov.id))
            else:
                has_partial = True
                run.error_code = res.get("error")
                
        if has_partial:
            run.status = "partially_completed"
        else:
            run.status = "completed"
            
        run.candidate_count = candidate_count
        run.completed_at = datetime.now(timezone.utc)
        await self.db.commit()

