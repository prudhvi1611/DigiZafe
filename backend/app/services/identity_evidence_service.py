import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.candidate_profile import CandidateProfile
from app.models.identity_anchor import IdentityAnchor, IdentityAlias, ConfirmedProfileReference
from app.schemas.identity_assessment import IdentityEvidence
from app.models.candidate_provenance import CandidateProvenanceObservation
from app.models.connector_certification import ConnectorCertificationRecord
from app.services.discovery.evidence_trust_policy import EvidenceTrustPolicy, EvidenceTrustClass


class IdentityEvidenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def collect_evidence(
        self,
        candidate: CandidateProfile,
        anchor: IdentityAnchor,
        aliases: Sequence[IdentityAlias],
        confirmed_profiles: Sequence[ConfirmedProfileReference]
    ) -> list[IdentityEvidence]:
        evidence = []

        # 1. User review state
        if candidate.candidate_status == "dismissed":
            evidence.append(IdentityEvidence(
                evidence_id=f"user_dismissal_{candidate.id}",
                evidence_type="explicit_user_dismissal",
                direction="negative",
                strength_class="strong",
                source_type="user_action",
                source_reference=str(candidate.id),
                source_reliability_class="authoritative",
                canonical_fact_key=f"candidate:{candidate.id}|fact:user_review",
                independence_group=f"explicit_user_review:{candidate.id}",
                derived_from=f"candidate:{candidate.id}"
            ))
        elif candidate.candidate_status == "confirmed_by_user":
            evidence.append(IdentityEvidence(
                evidence_id=f"user_confirmation_{candidate.id}",
                evidence_type="explicit_user_confirmation",
                direction="positive",
                strength_class="strong",
                source_type="user_action",
                source_reference=str(candidate.id),
                source_reliability_class="authoritative",
                canonical_fact_key=f"candidate:{candidate.id}|fact:user_review",
                independence_group=f"explicit_user_review:{candidate.id}",
                derived_from=f"candidate:{candidate.id}"
            ))

        # 2. Maigret username observation (the core discovery)
        username = candidate.username_observed.lower()
        
        prov_stmt = select(CandidateProvenanceObservation, ConnectorCertificationRecord).outerjoin(
            ConnectorCertificationRecord,
            CandidateProvenanceObservation.connector_certification_id == ConnectorCertificationRecord.id
        ).where(
            CandidateProvenanceObservation.candidate_profile_id == candidate.id,
            CandidateProvenanceObservation.connector_type == "maigret",
            CandidateProvenanceObservation.superseded_at.is_(None)
        ).order_by(CandidateProvenanceObservation.valid_from.desc())
        
        prov_res = (await self.db.execute(prov_stmt)).first()
        
        trust_class = EvidenceTrustClass.TEST_ONLY
        if prov_res:
            prov, cert = prov_res
            trust_class = EvidenceTrustPolicy.evaluate(cert.availability if cert else None)
            
        strength = "weak"
        if trust_class in [EvidenceTrustClass.TEST_ONLY, EvidenceTrustClass.LIVE_UNCERTIFIED]:
            strength = "zero"
            
        evidence.append(IdentityEvidence(
            evidence_id=f"maigret_obs_{candidate.id}",
            evidence_type="maigret_profile_observation",
            direction="positive", # initially positive, but collision capped
            strength_class=strength,
            source_type="maigret",
            source_reference=str(candidate.id),
            source_reliability_class="medium",
            canonical_fact_key=f"candidate:{candidate.id}|fact:username|value:{username}",
            independence_group=f"username_observation:{username}",
            derived_from=f"candidate:{candidate.id}"
        ))

        # 3. Match against active aliases
        matched_aliases = [a for a in aliases if a.value_canonical.lower() == username and a.status == "active"]
        for alias in matched_aliases:
            evidence.append(IdentityEvidence(
                evidence_id=f"alias_match_{alias.id}_{candidate.id}",
                evidence_type="exact_username_match",
                direction="positive",
                strength_class="moderate",
                source_type="identity_alias",
                source_reference=str(alias.id),
                source_reliability_class="high",
                canonical_fact_key=f"candidate:{candidate.id}|fact:username|value:{username}",
                independence_group=f"username_observation:{username}", # same group as maigret obs
                derived_from=f"alias:{alias.id}"
            ))
            
        # 4. Check for conflicting confirmed profile on the same platform
        same_platform_profiles = [p for p in confirmed_profiles if p.platform.lower() == candidate.platform.lower() and p.status == "active"]
        for p in same_platform_profiles:
            # if the confirmed profile url is different from candidate canonical url, it might be a contradiction
            if p.profile_url_canonical != candidate.canonical_profile_url:
                evidence.append(IdentityEvidence(
                    evidence_id=f"conflict_{p.id}_{candidate.id}",
                    evidence_type="contradictory_profile_reference",
                    direction="negative",
                    strength_class="strong",
                    source_type="confirmed_profile",
                    source_reference=str(p.id),
                    source_reliability_class="high",
                    canonical_fact_key=f"platform:{p.platform}|fact:identity_conflict",
                    independence_group=f"platform_conflict:{p.platform}",
                    derived_from=f"confirmed_profile:{p.id}"
                ))
            else:
                # Same platform, same url -> this should already be "confirmed_by_user" but let's record the evidence anyway
                evidence.append(IdentityEvidence(
                    evidence_id=f"confirmed_match_{p.id}_{candidate.id}",
                    evidence_type="confirmed_profile_cross_reference",
                    direction="positive",
                    strength_class="strong",
                    source_type="confirmed_profile",
                    source_reference=str(p.id),
                    source_reliability_class="authoritative",
                    canonical_fact_key=f"platform:{p.platform}|fact:profile_url|value:{candidate.canonical_profile_url}",
                    independence_group=f"confirmed_profile:{p.id}",
                    derived_from=f"confirmed_profile:{p.id}"
                ))

        # 5. Cross-links (Sprint 18)
        from app.models.identity_cross_link import IdentityCrossLinkObservation
        cross_links = (await self.db.execute(
            select(IdentityCrossLinkObservation).where(IdentityCrossLinkObservation.source_entity_id == candidate.id)
        )).scalars().all()
        
        for link in cross_links:
            # Check if it links to a confirmed profile's URL or anchor URL
            is_confirmed = any(p.profile_url_canonical == link.target_url_canonical for p in confirmed_profiles if p.status == "active")
            
            # Or if it matches another known identity resource. For Sprint 18, cross links provide moderate positive evidence 
            # if they link out to something we consider "safe" or "confirmed". 
            # Actually, the spec just says "cross link observation". We can just add it as weak positive evidence 
            # if it's mutual or points to a known asset.
            # Let's add it unconditionally as weak, or moderate if confirmed.
            strength = "moderate" if is_confirmed else "weak"
            evidence.append(IdentityEvidence(
                evidence_id=f"cross_link_{link.id}",
                evidence_type="cross_link_observation",
                direction="positive",
                strength_class=strength,
                source_type="cross_link",
                source_reference=str(link.id),
                source_reliability_class="medium",
                canonical_fact_key=f"crosslink:{link.source_entity_id}->{link.target_url_canonical}",
                independence_group=f"cross_link_target:{link.target_url_canonical}",
                derived_from=f"cross_link:{link.id}"
            ))
            
        # 6. Avatar Similarity (Sprint 18)
        from app.models.profile_visual_fingerprint import ProfileVisualFingerprint
        from app.services.avatar_similarity_service import AvatarSimilarityService
        from app.core.config import get_settings
        
        settings = get_settings()
        if settings.feature_avatar_similarity:
            cand_fp = (await self.db.execute(
                select(ProfileVisualFingerprint).where(
                    ProfileVisualFingerprint.candidate_id == candidate.id,
                    ProfileVisualFingerprint.status == "active"
                )
            )).scalars().first()
            
            if cand_fp and cand_fp.phash:
                # Compare against all confirmed profiles' fingerprints
                conf_fps = (await self.db.execute(
                    select(ProfileVisualFingerprint).where(
                        ProfileVisualFingerprint.user_id == candidate.user_id,
                        ProfileVisualFingerprint.confirmed_profile_id.is_not(None),
                        ProfileVisualFingerprint.status == "active"
                    )
                )).scalars().all()
                
                similarity_svc = AvatarSimilarityService(self.db)
                for conf_fp in conf_fps:
                    if not conf_fp.phash:
                        continue
                    
                    if cand_fp.exact_hash_sha256 == conf_fp.exact_hash_sha256:
                        evidence.append(IdentityEvidence(
                            evidence_id=f"avatar_exact_{cand_fp.id}_{conf_fp.id}",
                            evidence_type="avatar_exact_match",
                            direction="positive",
                            strength_class="moderate", # Not strong, "Visual similarity != identity proof"
                            source_type="avatar_fingerprint",
                            source_reference=str(cand_fp.id),
                            source_reliability_class="high",
                            canonical_fact_key=f"avatar_exact:{cand_fp.exact_hash_sha256}",
                            independence_group="avatar_visual_similarity",
                            derived_from=f"fingerprint:{cand_fp.id}"
                        ))
                    else:
                        dist = similarity_svc.compute_distance(cand_fp.phash, conf_fp.phash)
                        if dist <= settings.avatar_similarity_phash_threshold:
                            evidence.append(IdentityEvidence(
                                evidence_id=f"avatar_perceptual_{cand_fp.id}_{conf_fp.id}",
                                evidence_type="avatar_perceptual_match",
                                direction="positive",
                                strength_class="weak",
                                source_type="avatar_fingerprint",
                                source_reference=str(cand_fp.id),
                                source_reliability_class="medium",
                                canonical_fact_key=f"avatar_phash_match:{cand_fp.id}_{conf_fp.id}",
                                independence_group="avatar_visual_similarity",
                                derived_from=f"fingerprint:{cand_fp.id}"
                            ))

        return evidence
