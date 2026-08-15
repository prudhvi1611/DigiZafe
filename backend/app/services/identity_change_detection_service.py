import hashlib
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.domain.temporal_states import (
    FACT_VALUE_CHANGED,
    FACT_APPEARED,
    FACT_DISAPPEARED,
    FACT_ABSENCE_SUSPECTED,
    FACT_REAPPEARED,
    FACT_SUPERSEDED,
    STATE_CURRENT,
    STATE_SUPERSEDED,
    STATE_ABSENT_UNCONFIRMED,
    STATE_ABSENT_CONFIRMED,
    CONFIDENCE_OBSERVED_ONCE,
    CONFIDENCE_REVALIDATED,
    CONFIDENCE_OPERATIONALLY_UNCERTAIN
)
from app.models.temporal import IdentityChangeEvent
from app.services.identity_change_materiality_policy import IdentityChangeMaterialityPolicy
from app.services.identity_match_engine import IdentityMatchEngine
from app.services.identity_review_queue_service import IdentityReviewQueueService
from app.services.identity_cluster_service import IdentityClusterService
from app.models.candidate_provenance import CandidateProvenanceObservation
from app.models.candidate_profile import CandidateProfile


class IdentityChangeDetectionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.config = get_settings()
        self.materiality_policy = IdentityChangeMaterialityPolicy(self.config.identity_change_policy_version)

    def calculate_event_fingerprint(
        self,
        user_id: uuid.UUID,
        canonical_fact_key: str,
        change_type: str,
        previous_fingerprint: str | None,
        new_fingerprint: str | None,
        policy_version: int,
    ) -> str:
        payload = f"{user_id}:{canonical_fact_key}:{change_type}:{previous_fingerprint}:{new_fingerprint}:{policy_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def detect_and_record_change(
        self,
        user_id: uuid.UUID,
        anchor_id: uuid.UUID,
        candidate_profile_id: uuid.UUID | None,
        canonical_fact_key: str,
        change_type: str,
        new_state: str,
        confidence_state: str,
        detected_at: datetime,
        previous_state: str | None = None,
        previous_value_fingerprint: str | None = None,
        new_value_fingerprint: str | None = None,
        is_confirmed_profile: bool = False,
        is_likely_match: bool = False,
        source_lineage: dict | None = None,
        effective_at: datetime | None = None,
    ) -> IdentityChangeEvent | None:
        
        if not self.config.feature_identity_change_detection:
            return None

        materiality, priority = self.materiality_policy.evaluate(
            change_type=change_type,
            fact_key=canonical_fact_key,
            is_confirmed_profile=is_confirmed_profile,
            is_likely_match=is_likely_match
        )
        
        fingerprint = self.calculate_event_fingerprint(
            user_id=user_id,
            canonical_fact_key=canonical_fact_key,
            change_type=change_type,
            previous_fingerprint=previous_value_fingerprint,
            new_fingerprint=new_value_fingerprint,
            policy_version=self.config.identity_change_policy_version
        )
        
        # Check idempotency
        stmt = select(IdentityChangeEvent).where(IdentityChangeEvent.event_fingerprint == fingerprint)
        existing = (await self.db.execute(stmt)).scalars().first()
        if existing:
            return existing

        event = IdentityChangeEvent(
            user_id=user_id,
            anchor_id=anchor_id,
            candidate_profile_id=candidate_profile_id,
            canonical_fact_key=canonical_fact_key,
            change_type=change_type,
            previous_value_fingerprint=previous_value_fingerprint,
            new_value_fingerprint=new_value_fingerprint,
            previous_state=previous_state,
            new_state=new_state,
            materiality=materiality,
            review_priority=priority,
            confidence_state=confidence_state,
            event_fingerprint=fingerprint,
            detected_at=detected_at,
            effective_at=effective_at,
            change_policy_version=self.config.identity_change_policy_version,
            source_observation_lineage=source_lineage
        )
        self.db.add(event)
        
        # 28. Integrate material events with incremental reassessment
        # 21. Integrate with review queue
        if materiality in (MATERIALITY_CRITICAL_REVIEW, MATERIALITY_HIGH, MATERIALITY_MEDIUM):
            review_queue = IdentityReviewQueueService(self.db)
            await review_queue.enqueue_from_event(event)
            
            # Reassess candidate
            if candidate_profile_id:
                match_engine = IdentityMatchEngine(self.db)
                assessment = await match_engine.assess_candidate(user_id, candidate_profile_id)
                
                # 29. Integrate assessment changes with cluster fingerprints
                # Rebuild cluster footprint if needed (ClusterService does this intrinsically if we update member state,
                # but we can explicitly trigger a recalc)
                cluster_svc = IdentityClusterService(self.db)
                await cluster_svc.sync_clusters(anchor_id, user_id)
                
        return event

    async def evaluate_observation(self, observation_id: uuid.UUID) -> None:
        """
        Evaluates a newly added observation for temporal state changes.
        """
        stmt = select(CandidateProvenanceObservation).where(CandidateProvenanceObservation.id == observation_id)
        obs = (await self.db.execute(stmt)).scalars().first()
        if not obs:
            return

        # Fetch history for this fact key, sorted by valid_from (or observed_at)
        history_stmt = select(CandidateProvenanceObservation).where(
            CandidateProvenanceObservation.user_id == obs.user_id,
            CandidateProvenanceObservation.canonical_fact_key == obs.canonical_fact_key
        ).order_by(CandidateProvenanceObservation.valid_from.asc(), CandidateProvenanceObservation.id.asc())
        
        history = (await self.db.execute(history_stmt)).scalars().all()
        
        # We need to evaluate the state transition based on the sequence
        # We'll replay the sequence up to this observation to determine the current state
        # In a real event sourcing system, we would just look at the last materialized state
        
        # Let's see the previous observation
        index = next((i for i, h in enumerate(history) if h.id == obs.id), -1)
        if index == -1:
            return
            
        previous_obs = history[index - 1] if index > 0 else None
        
        is_absent = obs.observation_type.endswith("_absent") or (obs.normalized_payload and obs.normalized_payload.get("status") == "absent")
        was_absent = previous_obs and (previous_obs.observation_type.endswith("_absent") or (previous_obs.normalized_payload and previous_obs.normalized_payload.get("status") == "absent"))
        
        # Get candidate profile to check if it's confirmed
        is_confirmed = False
        if obs.candidate_profile_id:
            cand_stmt = select(CandidateProfile).where(CandidateProfile.id == obs.candidate_profile_id)
            cand = (await self.db.execute(cand_stmt)).scalars().first()
            if cand and cand.candidate_status == "confirmed_by_user":
                is_confirmed = True
                
        change_type = None
        new_state = STATE_CURRENT
        previous_state = None
        
        if not previous_obs:
            if not is_absent:
                change_type = FACT_APPEARED
        else:
            if not is_absent and not was_absent:
                # Value change? (for now we assume if it's the same fact key, and not absent, it's a value change if payload changed)
                # For profile existence, fact key is unique to URL, so it's not a value change. 
                # For bio or avatar, we would check if value fingerprint changed.
                if obs.normalized_payload != previous_obs.normalized_payload:
                    change_type = FACT_VALUE_CHANGED
                    previous_state = STATE_SUPERSEDED
            elif not is_absent and was_absent:
                change_type = FACT_REAPPEARED
            elif is_absent and not was_absent:
                change_type = FACT_ABSENCE_SUSPECTED
                new_state = STATE_ABSENT_UNCONFIRMED
            elif is_absent and was_absent:
                # Consecutive absences
                # Apply absence policy
                policy_threshold = self._get_absence_threshold(obs.canonical_fact_key)
                # count consecutive absences looking back
                consecutive = 1
                for i in range(index - 1, -1, -1):
                    p = history[i]
                    if p.observation_type.endswith("_absent") or (p.normalized_payload and p.normalized_payload.get("status") == "absent"):
                        consecutive += 1
                    else:
                        break
                        
                if consecutive == policy_threshold:
                    # Do we also check time separation? 
                    # "2 successful eligible revalidation attempts separated by at least 24 hours"
                    first_absent = history[index - consecutive + 1]
                    delta = obs.valid_from - first_absent.valid_from
                    min_hours = self._get_absence_time_separation(obs.canonical_fact_key)
                    if delta.total_seconds() >= min_hours * 3600:
                        change_type = FACT_DISAPPEARED
                        new_state = STATE_ABSENT_CONFIRMED
                    else:
                        change_type = FACT_ABSENCE_SUSPECTED
                        new_state = STATE_ABSENT_UNCONFIRMED
                elif consecutive > policy_threshold:
                    # Already disappeared, no new event
                    pass
                else:
                    change_type = FACT_ABSENCE_SUSPECTED
                    new_state = STATE_ABSENT_UNCONFIRMED
                    
        if change_type:
            await self.detect_and_record_change(
                user_id=obs.user_id,
                anchor_id=cand.anchor_id if obs.candidate_profile_id and cand else obs.user_id, # Fallback
                candidate_profile_id=obs.candidate_profile_id,
                canonical_fact_key=obs.canonical_fact_key,
                change_type=change_type,
                new_state=new_state,
                confidence_state=CONFIDENCE_REVALIDATED if is_absent else CONFIDENCE_OBSERVED_ONCE,
                detected_at=datetime.utcnow(),
                previous_state=previous_state,
                is_confirmed_profile=is_confirmed,
                is_likely_match=is_confirmed # Simplification
            )

    def _get_absence_threshold(self, fact_key: str) -> int:
        if fact_key.startswith("profile:"):
            return 2
        elif fact_key.startswith("bio:"):
            return 3
        elif fact_key.startswith("username:"):
            return 1
        return 2
        
    def _get_absence_time_separation(self, fact_key: str) -> int:
        # returns hours
        if fact_key.startswith("profile:"):
            return 24
        elif fact_key.startswith("link:"):
            return 12
        return 0
