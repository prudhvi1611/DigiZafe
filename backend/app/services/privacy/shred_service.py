"""
Crypto-shred + purge (G6).

Strategy:
1) Destroy user-specific secrets (MFA encrypted blob, refresh tokens, password hash randomized)
2) Hard-delete PII tables for the user (identifiers, findings, scores, remediation, etc.)
3) Keep anonymized audit rows with user_id NULL + action privacy.account_shredded
4) Mark user inactive / email scrambled so login fails permanently

Note: App-wide MASTER_KEY is NOT destroyed (would shred all users).
User-bound ciphertext (MFA) becomes undecryptable after secret wipe + row delete.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.alert import Alert, RescanPolicy
from app.models.audit import AuditLog
from app.models.consent_egress import ConsentRecord, EgressLedger
from app.models.identifier import Identifier, VerificationChallenge
from app.models.identity import IdentityCollision, IdentityEdge
from app.models.identity_anchor import IdentityAnchor, IdentityAlias, ConfirmedProfileReference
from app.models.observation_finding import EvidenceBlob, Finding, Observation
from app.models.privacy import AccountDeletionRequest, DataExportJob, NarrativeBriefing
from app.models.recommendation import Recommendation, RecommendationPlan
from app.models.scan import Scan, ScanConnectorRun
from app.models.score import ExplanationRecord, ScoreSnapshot
from app.models.user import RefreshToken, User
from app.security.password import hash_password
from app.services.audit_service import AuditService

logger = get_logger(__name__)


class ShredService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.audit = AuditService(session)

    async def _set_rls(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )

    async def execute_shred(self, user_id: uuid.UUID, *, deletion_request_id: uuid.UUID | None = None) -> dict[str, Any]:
        if not self.settings.feature_crypto_shred:
            raise HTTPException(status_code=503, detail="Crypto-shred disabled")

        # Workers may need elevated path — set RLS to user then delete own rows
        await self._set_rls(user_id)

        counts: dict[str, int] = {}

        async def _del(model, extra=None) -> int:
            q = delete(model).where(model.user_id == user_id)  # type: ignore[attr-defined]
            r = await self.session.execute(q)
            return r.rowcount or 0

        # Order: children-ish first where FK allows cascade; explicit deletes for safety
        tables_models = [
            ("narrative_briefings", NarrativeBriefing),
            ("data_export_jobs", DataExportJob),
            ("explanation_records", ExplanationRecord),
            ("score_snapshots", ScoreSnapshot),
            ("identity_collisions", IdentityCollision),
            ("identity_edges", IdentityEdge),
            ("identity_aliases", IdentityAlias),
            ("identity_cluster_members", __import__("app.models.identity_cluster", fromlist=["IdentityClusterMember"]).IdentityClusterMember),
            ("identity_clusters", __import__("app.models.identity_cluster", fromlist=["IdentityCluster"]).IdentityCluster),
            ("profile_visual_fingerprints", __import__("app.models.profile_visual_fingerprint", fromlist=["ProfileVisualFingerprint"]).ProfileVisualFingerprint),
            ("identity_cross_link_observations", __import__("app.models.identity_cross_link", fromlist=["IdentityCrossLinkObservation"]).IdentityCrossLinkObservation),
            ("identity_match_assessments", __import__("app.models.identity_match_assessment", fromlist=["IdentityMatchAssessment"]).IdentityMatchAssessment),
            ("candidate_provenance_observations", __import__("app.models.candidate_provenance", fromlist=["CandidateProvenanceObservation"]).CandidateProvenanceObservation),
            ("identity_change_events", __import__("app.models.temporal", fromlist=["IdentityChangeEvent"]).IdentityChangeEvent),
            ("identity_review_item_events", __import__("app.models.temporal", fromlist=["IdentityReviewItemEvent"]).IdentityReviewItemEvent),
            ("identity_review_items", __import__("app.models.temporal", fromlist=["IdentityReviewItem"]).IdentityReviewItem),
            ("connector_execution_plan_items", __import__("app.models.orchestration", fromlist=["ConnectorExecutionPlanItem"]).ConnectorExecutionPlanItem),
            ("identity_orchestration_runs", __import__("app.models.orchestration", fromlist=["IdentityOrchestrationRun"]).IdentityOrchestrationRun),
            ("candidate_profiles", __import__("app.models.candidate_profile", fromlist=["CandidateProfile"]).CandidateProfile),
            ("candidate_discovery_runs", __import__("app.models.candidate_profile", fromlist=["CandidateDiscoveryRun"]).CandidateDiscoveryRun),
            ("confirmed_profile_references", ConfirmedProfileReference),
            ("identity_anchors", IdentityAnchor),
            ("evidence_blobs", EvidenceBlob),
            ("observations", Observation),
            ("findings", Finding),
            ("scan_connector_runs", ScanConnectorRun),
            ("scans", Scan),
            ("recommendations", Recommendation),
            ("recommendation_plans", RecommendationPlan),
            ("alerts", Alert),
            ("rescan_policies", RescanPolicy),
            ("verification_challenges", VerificationChallenge),
            ("identifiers", Identifier),
            ("consent_records", ConsentRecord),
            ("egress_ledger", EgressLedger),
            ("refresh_tokens", RefreshToken),
        ]

        # Remediation models if present
        try:
            from app.models.remediation import (
                BrokerOptOutState,
                CaptchaQueueItem,
                FreezeChecklistItem,
                GeneratedRequest,
                RemediationJob,
                RemediationJobItem,
            )
            tables_models = [
                ("captcha_queue", CaptchaQueueItem),
                ("remediation_job_items", RemediationJobItem),
                ("remediation_jobs", RemediationJob),
                ("broker_optout_state", BrokerOptOutState),
                ("freeze_checklist_items", FreezeChecklistItem),
                ("generated_requests", GeneratedRequest),
            ] + tables_models
        except Exception:
            pass

        for name, model in tables_models:
            try:
                counts[name] = await _del(model)
            except Exception as e:
                logger.warning("shred_table_failed", table=name, error=str(e))
                counts[name] = -1

        # Crypto-shred user credentials
        r = await self.session.execute(select_user := __import__("sqlalchemy", fromlist=["select"]).select(User).where(User.id == user_id))
        from sqlalchemy import select as sa_select
        r = await self.session.execute(sa_select(User).where(User.id == user_id))
        user = r.scalar_one_or_none()
        if user:
            # Destroy MFA secret (ciphertext discarded)
            user.mfa_secret_encrypted = None
            user.mfa_enabled = False
            # Unusable password
            user.hashed_password = hash_password(secrets.token_urlsafe(48))
            # Scramble email (preserve uniqueness)
            user.email = f"shredded+{user_id.hex[:16]}@invalid.local"
            user.email_blind = None
            user.is_active = False
            user.is_verified = False
            counts["user_credential_shred"] = 1

        # Anonymize remaining audit logs for this user (keep actions for integrity research, drop link)
        try:
            await self.session.execute(
                update(AuditLog)
                .where(AuditLog.user_id == user_id)
                .values(user_id=None, details={"redacted": True, "reason": "crypto_shred"})
            )
            counts["audit_anonymized"] = 1
        except Exception as e:
            logger.warning("audit_anonymize_failed", error=str(e))

        # Mark deletion request completed
        if deletion_request_id:
            r = await self.session.execute(
                sa_select(AccountDeletionRequest).where(AccountDeletionRequest.id == deletion_request_id)
            )
            req = r.scalar_one_or_none()
            if req:
                req.status = "completed"
                req.completed_at = datetime.now(UTC)
                req.meta = {**(req.meta or {}), "counts": counts}

        # Final audit (user_id null after anonymize — log with resource)
        try:
            self.session.add(
                AuditLog(
                    user_id=None,
                    action="privacy.account_shredded",
                    resource_type="user",
                    resource_id=str(user_id),
                    details={"counts": counts},
                )
            )
        except Exception:
            pass

        await self.session.commit()
        logger.info("crypto_shred_completed", user_id=str(user_id), counts=counts)
        return {"user_id": str(user_id), "status": "completed", "counts": counts}
