import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.orchestration import IdentityOrchestrationRun, ConnectorExecutionPlanItem
from app.models.identity_anchor import IdentityAlias
from app.models.candidate_provenance import CandidateProvenanceObservation
from app.services.discovery.connectors.registry import ConnectorRegistry, ConnectorAvailability, ConnectorCapability
from app.services.discovery.connector_budget_service import ConnectorBudgetService
from app.services.discovery.connector_health_service import ConnectorHealthService, CircuitBreakerState
from app.services.discovery.evidence_freshness_service import EvidenceFreshnessService, FreshnessState
from app.services.consent_service import ConsentService
from app.services.discovery.connectors.conformance_service import ConnectorConformanceService

logger = get_logger(__name__)


class OrchestrationDecision(str, Enum):
    EXECUTE = "execute"
    SKIP_FRESH = "skip_fresh"
    SKIP_DISABLED = "skip_disabled"
    SKIP_NO_CONSENT = "skip_no_consent"
    SKIP_BUDGET = "skip_budget"
    SKIP_UNAVAILABLE = "skip_unavailable"
    SKIP_TEST_ONLY = "skip_test_only"
    SKIP_UNHEALTHY = "skip_unhealthy"
    SKIP_INELIGIBLE = "skip_ineligible"
    SKIP_DUPLICATE = "skip_duplicate"
    DEFER = "defer_runtime_control_unavailable"


class ConnectorOrchestrationService:
    def __init__(self, session: AsyncSession, redis: Redis):
        self.session = session
        self.redis = redis
        self.settings = get_settings()
        self.budget_service = ConnectorBudgetService(redis)
        self.health_service = ConnectorHealthService(redis)
        self.consent_service = ConsentService(session)
        self.conformance_service = ConnectorConformanceService(session)

    def _generate_input_fingerprint(
        self, user_id: uuid.UUID, anchor_id: uuid.UUID | None, aliases: list[IdentityAlias], requested_capabilities: list[str]
    ) -> str:
        # Deterministic input fingerprint
        alias_data = sorted([{"id": str(a.id), "type": a.type, "value": a.value_canonical} for a in aliases], key=lambda x: x["id"])
        data = {
            "user_id": str(user_id),
            "anchor_id": str(anchor_id) if anchor_id else None,
            "anchor_version": 1, # Mock version for MVP, you might want to fetch actual anchor version
            "aliases": alias_data,
            "requested_capabilities": sorted(requested_capabilities),
            "orchestration_policy_version": self.settings.connector_orchestration_policy_version,
            "enabled_connectors": sorted([c.connector_type for c in ConnectorRegistry.get_all_connectors() if c.enabled])
        }
        raw = json.dumps(data, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _generate_execution_plan_fingerprint(self, run: IdentityOrchestrationRun, plan_items: list[ConnectorExecutionPlanItem]) -> str:
        data = {
            "run_id": str(run.id),
            "input_fingerprint": run.input_fingerprint,
            "plan_items": [
                {
                    "connector": p.connector_type,
                    "capability": p.capability,
                    "alias": str(p.input_alias_id) if p.input_alias_id else None,
                    "decision": p.decision
                }
                for p in sorted(plan_items, key=lambda x: f"{x.connector_type}_{x.capability}_{x.input_alias_id}")
            ]
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    async def create_orchestration_run(
        self, user_id: uuid.UUID, anchor_id: uuid.UUID | None, aliases: list[IdentityAlias], requested_capabilities: list[ConnectorCapability], force_refresh: bool = False, purpose: str = "general"
    ) -> tuple[IdentityOrchestrationRun, bool]:
        """
        Creates an idempotent orchestration run. Returns tuple of (run, created).
        """
        fingerprint = self._generate_input_fingerprint(user_id, anchor_id, aliases, [c.value for c in requested_capabilities])
        
        # Idempotency check: see if a running or recently completed identical run exists
        result = await self.session.execute(
            select(IdentityOrchestrationRun).where(
                IdentityOrchestrationRun.user_id == user_id,
                IdentityOrchestrationRun.input_fingerprint == fingerprint,
                IdentityOrchestrationRun.status.in_(["planned", "queued", "running"])
            )
        )
        existing_run = result.scalar_one_or_none()
        
        if existing_run:
            return existing_run, False
            
        # Check global budget
        if not await self.budget_service.check_and_consume_orchestration_run(user_id, purpose=purpose):
            raise ValueError("orchestration_budget_exhausted")
            
        run = IdentityOrchestrationRun(
            user_id=user_id,
            anchor_id=anchor_id,
            policy_version=self.settings.connector_orchestration_policy_version,
            input_fingerprint=fingerprint,
            requested_capabilities=[c.value for c in requested_capabilities]
        )
        self.session.add(run)
        await self.session.flush()
        
        return run, True

    async def evaluate_eligibility(
        self, 
        user_id: uuid.UUID, 
        connector: str, 
        capability: ConnectorCapability, 
        alias: IdentityAlias | None,
        force_refresh: bool = False
    ) -> tuple[OrchestrationDecision, str]:
        
        descriptor = ConnectorRegistry.get_descriptor(connector)
        if not descriptor:
            return OrchestrationDecision.SKIP_UNAVAILABLE, "connector_not_found"
            
        if not descriptor.enabled:
            return OrchestrationDecision.SKIP_DISABLED, "connector_disabled_in_config"
            
        if capability not in descriptor.capabilities:
            return OrchestrationDecision.SKIP_INELIGIBLE, "capability_not_supported"
            
        real_availability = await self.conformance_service.get_connector_status(connector)
            
        if real_availability == "test_only" and not self.settings.is_development:
            # We block test_only connectors in production unless explicitly allowed (mocked)
            # Given instructions: "test_only runtime + production execution request -> skip_test_only / unavailable"
            if self.settings.app_env != "test":
                return OrchestrationDecision.SKIP_TEST_ONLY, "connector_test_only_in_prod"

        if real_availability in ["disabled", "unavailable", "installed_unverified", "certification_failed", "temporarily_unhealthy"]:
            return OrchestrationDecision.SKIP_UNAVAILABLE, "connector_unavailable"

        # Check circuit breaker
        health = await self.health_service.get_state(connector)
        if health == CircuitBreakerState.OPEN:
            return OrchestrationDecision.SKIP_UNHEALTHY, "circuit_breaker_open"
            
        # Check consent if applicable
        has_consent = await self.consent_service.check_consent(user_id, f"discovery.{connector}")
        if not has_consent:
            return OrchestrationDecision.SKIP_NO_CONSENT, "missing_consent"

        # Freshness Check
        if alias and not force_refresh:
            result = await self.session.execute(
                select(CandidateProvenanceObservation).where(
                    CandidateProvenanceObservation.user_id == user_id,
                    CandidateProvenanceObservation.input_alias_id == alias.id,
                    CandidateProvenanceObservation.connector_type == connector,
                    CandidateProvenanceObservation.capability == capability.value
                ).order_by(CandidateProvenanceObservation.last_observed_at.desc())
            )
            last_obs = result.scalar_one_or_none()
            if last_obs:
                freshness = EvidenceFreshnessService.evaluate(last_obs.valid_from, last_obs.observation_type)
                if freshness == FreshnessState.FRESH:
                    return OrchestrationDecision.SKIP_FRESH, "existing_observation_fresh"
                    
        return OrchestrationDecision.EXECUTE, "eligible"

    async def plan_run(
        self, run: IdentityOrchestrationRun, aliases: list[IdentityAlias], force_refresh: bool = False
    ) -> list[ConnectorExecutionPlanItem]:
        
        plan_items = []
        connectors = ConnectorRegistry.get_all_connectors()
        
        for alias in aliases:
            for connector in connectors:
                for capability_str in (run.requested_capabilities or []):
                    capability = ConnectorCapability(capability_str)
                    
                    decision, reason = await self.evaluate_eligibility(run.user_id, connector.connector_type, capability, alias, force_refresh)
                    
                    item = ConnectorExecutionPlanItem(
                        orchestration_run_id=run.id,
                        connector_type=connector.connector_type,
                        capability=capability.value,
                        input_alias_id=alias.id,
                        decision=decision.value,
                        decision_reason=reason
                    )
                    
                    if decision == OrchestrationDecision.EXECUTE:
                        run.planned_connector_count += 1
                    else:
                        run.skipped_connector_count += 1
                        
                    plan_items.append(item)
                    self.session.add(item)
        
        await self.session.flush()
        return plan_items
