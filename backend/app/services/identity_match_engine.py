import uuid
import hashlib
import json
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.candidate_profile import CandidateProfile
from app.models.identity_anchor import IdentityAnchor, IdentityAlias, ConfirmedProfileReference
from app.models.identity_match_assessment import IdentityMatchAssessment
from app.schemas.identity_assessment import IdentityEvidence, ExplanationItem
from app.services.identity_evidence_service import IdentityEvidenceService
from app.services.identity_collision_policy import IdentityCollisionPolicy


class IdentityMatchEngine:
    ENGINE_VERSION = 5
    POLICY_VERSION = 5

    def __init__(self, db: AsyncSession):
        self.db = db
        self.evidence_service = IdentityEvidenceService(db)

    def _generate_fingerprint(self, evidence: list[IdentityEvidence]) -> str:
        # Sort evidence by ID for stable fingerprint
        sorted_ev = sorted(evidence, key=lambda x: x.evidence_id)
        ev_dicts = [ev.model_dump(mode="json") for ev in sorted_ev]
        payload = json.dumps(ev_dicts, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _map_explanation(self, evidence: list[IdentityEvidence], status: str, collision_class: str) -> dict:
        why_matched = []
        why_not_matched = []
        
        # Explain contradictions or user actions
        user_dismissals = [e for e in evidence if e.evidence_type == "explicit_user_dismissal"]
        if user_dismissals:
            why_not_matched.append(ExplanationItem(
                rule_id="user_override_dismissal",
                message_key="user_dismissed",
                evidence_keys=[e.evidence_id for e in user_dismissals],
                message_text="You previously dismissed this candidate."
            ))
            
        user_confirmations = [e for e in evidence if e.evidence_type == "explicit_user_confirmation"]
        if user_confirmations:
            why_matched.append(ExplanationItem(
                rule_id="user_override_confirmation",
                message_key="user_confirmed",
                evidence_keys=[e.evidence_id for e in user_confirmations],
                message_text="You have confirmed this profile."
            ))

        contradictions = [e for e in evidence if e.evidence_type == "contradictory_profile_reference"]
        if contradictions:
            why_not_matched.append(ExplanationItem(
                rule_id="contradiction_detected",
                message_key="conflict_confirmed_profile",
                evidence_keys=[e.evidence_id for e in contradictions],
                message_text="This candidate conflicts with a profile you already confirmed on this platform."
            ))
            
        # Group independent evidence
        groups = set([e.independence_group for e in evidence if e.direction == "positive" and e.evidence_type not in ["explicit_user_confirmation"]])
        if groups:
            why_matched.append(ExplanationItem(
                rule_id="independent_evidence_groups",
                message_key="independent_groups",
                evidence_keys=[],
                message_text=f"Found {len(groups)} independent piece(s) of supporting evidence."
            ))
            
        # Collision
        collision_evs = [e for e in evidence if e.evidence_type in ["maigret_profile_observation", "exact_username_match"]]
        if collision_evs:
            if collision_class == "high_collision":
                why_not_matched.append(ExplanationItem(
                    rule_id="collision_risk_high",
                    message_key="high_collision",
                    evidence_keys=[e.evidence_id for e in collision_evs],
                    message_text="The username is very common, which limits confidence without other proof."
                ))
            elif collision_class == "low_collision":
                why_matched.append(ExplanationItem(
                    rule_id="collision_risk_low",
                    message_key="low_collision",
                    evidence_keys=[e.evidence_id for e in collision_evs],
                    message_text="The username is distinctive, reducing the risk of a random collision."
                ))

        return {
            "why_matched": [i.model_dump(mode="json") for i in why_matched],
            "why_not_matched": [i.model_dump(mode="json") for i in why_not_matched]
        }

    async def _calculate_provenance_fingerprint(self, user_id: uuid.UUID, candidate_id: uuid.UUID) -> str:
        from app.models.candidate_provenance import CandidateProvenanceObservation
        stmt = select(CandidateProvenanceObservation).where(
            CandidateProvenanceObservation.user_id == user_id,
            CandidateProvenanceObservation.candidate_profile_id == candidate_id,
            CandidateProvenanceObservation.superseded_at.is_(None)
        ).order_by(CandidateProvenanceObservation.id)
        
        obs_list = (await self.db.execute(stmt)).scalars().all()
        
        fingerprint_data = []
        for obs in obs_list:
            fingerprint_data.append({
                "id": str(obs.id),
                "valid_from": obs.valid_from.isoformat() if obs.valid_from else None,
                "fact_key": obs.canonical_fact_key
            })
            
        payload = json.dumps(fingerprint_data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    async def assess_candidate(
        self,
        user_id: uuid.UUID,
        candidate_id: uuid.UUID
    ) -> IdentityMatchAssessment:
        
        # 1. Calculate provenance fingerprint
        fingerprint = await self._calculate_provenance_fingerprint(user_id, candidate_id)
        
        # 2. Check for existing identical assessment
        existing_stmt = select(IdentityMatchAssessment).where(
            IdentityMatchAssessment.candidate_profile_id == candidate_id,
            IdentityMatchAssessment.is_current == True
        )
        existing = (await self.db.execute(existing_stmt)).scalars().first()
        
        # If fingerprint matches exactly, return existing
        if existing and existing.assessment_input_fingerprint == fingerprint and existing.engine_version == self.ENGINE_VERSION and existing.policy_version == self.POLICY_VERSION:
            return existing
            
        # 3. Load data
        candidate = (await self.db.execute(select(CandidateProfile).where(CandidateProfile.id == candidate_id, CandidateProfile.user_id == user_id))).scalars().first()
        if not candidate:
            raise ValueError("Candidate not found")
            
        anchor = (await self.db.execute(select(IdentityAnchor).where(IdentityAnchor.user_id == user_id, IdentityAnchor.status == "active"))).scalars().first()
        if not anchor:
            raise ValueError("Anchor not found")
            
        aliases = (await self.db.execute(select(IdentityAlias).where(IdentityAlias.user_id == user_id, IdentityAlias.status == "active"))).scalars().all()
        confirmed_profiles = (await self.db.execute(select(ConfirmedProfileReference).where(ConfirmedProfileReference.user_id == user_id, ConfirmedProfileReference.status == "active"))).scalars().all()
        
        # 4. Generate Evidence
        evidence = await self.evidence_service.collect_evidence(candidate, anchor, aliases, confirmed_profiles)
        
        # 5. Score and Cap Evidence
        score = 0
        collision_class = IdentityCollisionPolicy.assess_collision_risk(candidate.username_observed)
        username_cap = IdentityCollisionPolicy.get_username_evidence_cap(collision_class)
        
        independent_groups_score = {}
        authoritative_count = 0
        
        for ev in evidence:
            if ev.direction == "positive":
                group = ev.independence_group
                pts = 0
                if ev.strength_class == "strong": pts = 70
                elif ev.strength_class == "moderate": pts = 40
                elif ev.strength_class == "weak": pts = 20
                
                if ev.source_reliability_class == "authoritative":
                    authoritative_count += 1
                
                # cap logic
                if "username_observation" in group:
                    # applying cap
                    independent_groups_score[group] = min(username_cap, independent_groups_score.get(group, 0) + pts)
                else:
                    independent_groups_score[group] = independent_groups_score.get(group, 0) + pts

        score = sum(independent_groups_score.values())
        
        # 5. Apply contradictions and user state
        has_contradiction = any(e.evidence_type == "contradictory_profile_reference" for e in evidence)
        has_dismissal = any(e.evidence_type == "explicit_user_dismissal" for e in evidence)
        has_confirmation = any(e.evidence_type == "explicit_user_confirmation" for e in evidence)
        
        # 6. Assess status and band
        status = "insufficient_evidence"
        band = "Limited evidence"
        
        if has_dismissal:
            # User explicit state - we persist their override but note it algorithmically
            status = "unlikely_match"
            band = "Evidence against match"
            score = 0
        elif has_confirmation:
            status = "likely_match"
            band = "Strong supporting evidence"
            score = 100
        elif has_contradiction:
            status = "conflicting_evidence"
            band = "Conflicting evidence"
        else:
            # Algorithmic scoring
            # Require >= 2 independent groups OR 1 authoritative group
            independent_count = len(independent_groups_score.keys())
            
            if score >= 70 and (independent_count >= 2 or authoritative_count >= 1):
                status = "likely_match"
                band = "Strong supporting evidence"
            elif score >= 30:
                status = "possible_match"
                band = "Moderate supporting evidence"
            else:
                status = "insufficient_evidence"
                band = "Limited evidence"
                
        # 7. Generate explanation
        explanation_mapping = self._map_explanation(evidence, status, collision_class)
        
        # 8. Persist new assessment
        if existing:
            existing.is_current = False
            
        new_assessment = IdentityMatchAssessment(
            user_id=user_id,
            anchor_id=anchor.id,
            candidate_profile_id=candidate.id,
            is_current=True,
            anchor_version=anchor.version,
            candidate_revision=str(candidate.updated_at.timestamp()),
            engine_version=self.ENGINE_VERSION,
            policy_version=self.POLICY_VERSION,
            assessment_input_fingerprint=fingerprint,
            score=score,
            assessment_status=status,
            confidence_band=band,
            evidence_snapshot=[e.model_dump(mode="json") for e in evidence],
            explanation_mapping=explanation_mapping,
            stale_state="active"
        )
        self.db.add(new_assessment)
        await self.db.commit()
        await self.db.refresh(new_assessment)
        return new_assessment

