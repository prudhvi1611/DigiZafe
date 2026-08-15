import uuid
from typing import Sequence
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.identity_cluster import IdentityCluster, IdentityClusterMember
from app.models.candidate_profile import CandidateProfile
from app.models.identity_match_assessment import IdentityMatchAssessment

logger = logging.getLogger(__name__)

class IdentityClusterService:
    """
    Manages grouping of deterministic identity matches into IdentityClusters.
    Follows conservative merge strategy: NO transitive trapping.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def get_cluster_for_anchor(self, anchor_id: uuid.UUID) -> IdentityCluster | None:
        stmt = select(IdentityCluster).where(IdentityCluster.anchor_id == anchor_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()
        
    async def sync_clusters(self, anchor_id: uuid.UUID, user_id: uuid.UUID):
        """
        Re-evaluate the cluster for the given anchor.
        Only candidates with a 'likely_match' or 'confirmed_by_user' status are included.
        If any contradictory evidence exists across the cluster, mark cluster as ambiguous.
        """
        # Find all current assessments for this anchor
        stmt = select(IdentityMatchAssessment).where(
            IdentityMatchAssessment.anchor_id == anchor_id,
            IdentityMatchAssessment.is_current == True
        )
        assessments = (await self.db.execute(stmt)).scalars().all()
        
        # Determine eligible candidates
        eligible_candidates = []
        has_conflicts = False
        
        for assess in assessments:
            if assess.confidence_band == "likely_match":
                eligible_candidates.append(assess.candidate_profile_id)
            elif assess.confidence_band == "conflicting_evidence":
                has_conflicts = True
                
        # Also include any confirmed_by_user candidates natively
        cands_stmt = select(CandidateProfile).where(
            CandidateProfile.user_id == user_id,
            CandidateProfile.candidate_status == "confirmed_by_user"
        )
        confirmed_cands = (await self.db.execute(cands_stmt)).scalars().all()
        for c in confirmed_cands:
            if c.id not in eligible_candidates:
                eligible_candidates.append(c.id)
                
        # Calculate fingerprint
        fingerprint_data = {
            "assessments": sorted([(str(a.id), a.confidence_band) for a in assessments]),
            "confirmed": sorted([str(c.id) for c in confirmed_cands])
        }
        import json
        import hashlib
        fingerprint = hashlib.sha256(json.dumps(fingerprint_data).encode("utf-8")).hexdigest()
        
        cluster = await self.get_cluster_for_anchor(anchor_id)
        if cluster and cluster.input_fingerprint == fingerprint:
            return  # Cluster is up to date
            
        if not cluster:
            if not eligible_candidates:
                return # Nothing to do
            # Create new cluster
            cluster = IdentityCluster(
                user_id=user_id,
                anchor_id=anchor_id,
                status="conflicting" if has_conflicts else "supported",
                cluster_version=1,
                policy_version=1,
                input_fingerprint=fingerprint
            )
            self.db.add(cluster)
            await self.db.flush()
        else:
            cluster.status = "conflicting" if has_conflicts else "supported"
            cluster.cluster_version += 1
            cluster.input_fingerprint = fingerprint
            await self.db.flush()
            
        # Replace cluster members
        # First remove old
        del_stmt = select(IdentityClusterMember).where(IdentityClusterMember.cluster_id == cluster.id)
        old_members = (await self.db.execute(del_stmt)).scalars().all()
        for m in old_members:
            await self.db.delete(m)
            
        # Add new
        for cid in set(eligible_candidates):
            new_mem = IdentityClusterMember(
                cluster_id=cluster.id,
                candidate_id=cid
            )
            self.db.add(new_mem)
            
        await self.db.flush()
        logger.info("cluster_synced", anchor_id=str(anchor_id), status=cluster.status, members=len(eligible_candidates))
