import logging
import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.candidate_provenance import CandidateProvenanceObservation
from app.models.candidate_profile import CandidateProfile
from app.services.identity_match_engine import IdentityMatchEngine
from app.services.identity_cluster_service import IdentityClusterService

logger = logging.getLogger(__name__)

class IdentityReassessmentCoordinator:
    """
    Coordinates identity reassessment when systemic trust changes occur (e.g., certification invalidation).
    Prevents global recomputation by finding exactly which profiles are affected.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.match_engine = IdentityMatchEngine(db)
        self.cluster_service = IdentityClusterService(db)
        
    async def process_certification_change(self, connector_type: str, runtime_fingerprint: str):
        """
        Triggered when a certification state changes for a specific runtime fingerprint.
        """
        logger.info(f"Processing certification change fan-out for {connector_type} {runtime_fingerprint}")
        
        # 1. Find provenance linked to affected runtime fingerprint
        stmt = select(CandidateProvenanceObservation.user_id, CandidateProvenanceObservation.candidate_profile_id).where(
            CandidateProvenanceObservation.connector_type == connector_type,
            CandidateProvenanceObservation.runtime_fingerprint == runtime_fingerprint,
            CandidateProvenanceObservation.superseded_at.is_(None)
        ).distinct()
        
        results = (await self.db.execute(stmt)).all()
        
        if not results:
            logger.info("No active provenance observations found for this runtime fingerprint. No reassessment needed.")
            return
            
        logger.info(f"Found {len(results)} affected candidates. Triggering reassessment.")
        
        # 2. Identify affected candidates and group by user_id
        user_to_candidates = {}
        for user_id, cand_id in results:
            if user_id not in user_to_candidates:
                user_to_candidates[user_id] = []
            user_to_candidates[user_id].append(cand_id)
            
        # 3. Recalculate assessments for affected candidates
        for user_id, candidate_ids in user_to_candidates.items():
            for cand_id in candidate_ids:
                # Recalculate match score (the Match Engine reads the updated trust policy)
                await self.match_engine.assess_candidate(cand_id)
                
            # 4. Rebuild changed clusters only
            await self.cluster_service.rebuild_clusters_for_user(user_id)
            
        logger.info(f"Completed reassessment fan-out for {connector_type} {runtime_fingerprint}")
