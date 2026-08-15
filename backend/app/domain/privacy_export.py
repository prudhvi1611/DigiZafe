"""Pure helpers to build machine-readable personal data export (portability)."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def build_export_package(
    *,
    user: dict[str, Any],
    identifiers: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    remediation_state: list[dict[str, Any]],
    consent_records: list[dict[str, Any]],
    audit_logs: list[dict[str, Any]] | None = None,
    egress_ledger: list[dict[str, Any]] | None = None,
    identity_edges: list[dict[str, Any]] | None = None,
    generated_requests: list[dict[str, Any]] | None = None,
    identity_anchor: dict[str, Any] | None = None,
    candidate_profiles: list[dict[str, Any]] | None = None,
    candidate_discovery_runs: list[dict[str, Any]] | None = None,
    candidate_provenance_observations: list[dict[str, Any]] | None = None,
    identity_match_assessments: list[dict[str, Any]] | None = None,
    identity_orchestration_runs: list[dict[str, Any]] | None = None,
    connector_execution_plan_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Structured, commonly used, machine-readable format (JSON).
    Secrets (hashed passwords, MFA secrets, refresh tokens) MUST already be excluded by caller.
    """
    return {
        "export_version": "1.0.0",
        "exported_at": datetime.now(UTC).isoformat(),
        "product": "DigiZafe",
        "notice": (
            "This package contains personal data associated with your DigiZafe account. "
            "Raw breach dumps and full HTML evidence are not retained. "
            "Third-party attributions (e.g. XposedOrNot, AIDR lineage) are preserved where present."
        ),
        "subject": {
            "user_id": user.get("id"),
            "email": user.get("email"),
            "is_active": user.get("is_active"),
            "mfa_enabled": user.get("mfa_enabled"),
            "created_at": user.get("created_at"),
            "last_login_at": user.get("last_login_at"),
        },
        "identifiers": identifiers,
        "findings": findings,
        "score_history": scores,
        "recommendations": recommendations,
        "broker_optout_state": remediation_state,
        "identity_anchor": identity_anchor,
        "identity_edges": identity_edges or [],
        "generated_requests": generated_requests or [],
        "candidate_profiles": candidate_profiles or [],
        "candidate_discovery_runs": candidate_discovery_runs or [],
        "candidate_provenance_observations": candidate_provenance_observations or [],
        "identity_match_assessments": identity_match_assessments or [],
        "identity_orchestration_runs": identity_orchestration_runs or [],
        "connector_execution_plan_items": connector_execution_plan_items or [],
        "consent_records": consent_records,
        "audit_logs": audit_logs or [],
        "egress_ledger": egress_ledger or [],
        "rights": {
            "export": "GDPR Art.20 / CCPA portability-style machine-readable export",
            "erasure": "Use POST /privacy/account/delete → crypto-shred + purge",
            "consent": "Manage via /privacy/consent",
            "access_audit": "GET /privacy/audit",
        },
    }


def redacted_user_public(user_row: Any) -> dict[str, Any]:
    return {
        "id": str(user_row.id),
        "email": user_row.email,
        "is_active": user_row.is_active,
        "mfa_enabled": user_row.mfa_enabled,
        "created_at": user_row.created_at.isoformat() if user_row.created_at else None,
        "last_login_at": user_row.last_login_at.isoformat() if user_row.last_login_at else None,
    }
