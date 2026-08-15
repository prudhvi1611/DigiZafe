"""Remediation job + broker opt-out state transitions (pure). AIDR state.json lineage."""
from __future__ import annotations

from datetime import UTC
from enum import Enum


class RemediationJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_CAPTCHA = "waiting_captcha"
    WAITING_EMAIL_CONFIRM = "waiting_email_confirm"
    WAITING_MANUAL = "waiting_manual"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class BrokerOptOutStatus(str, Enum):
    """Per-broker status — maps AIDR run outcomes."""
    PENDING = "pending"
    RUNNING = "running"
    SUBMITTED = "submitted"              # form accepted (≠ deleted)
    AWAITING_EMAIL_CONFIRM = "awaiting_email_confirm"
    SKIPPED_FRESH = "skipped_fresh"      # within recheck window
    NOT_LISTED = "not_listed"
    MANUAL_NEEDED = "manual_needed"
    CAPTCHA_NEEDED = "captcha_needed"
    VERIFIED_REMOVED = "verified_removed"
    STILL_LISTED = "still_listed"        # after verify
    ERROR = "error"
    DEAD = "dead"                        # stale URL
    CANCELLED = "cancelled"


class CaptchaItemStatus(str, Enum):
    PENDING = "pending"
    SOLVED = "solved"
    EXPIRED = "expired"
    SKIPPED = "skipped"


TERMINAL_JOB = frozenset({
    RemediationJobStatus.COMPLETED,
    RemediationJobStatus.PARTIAL,
    RemediationJobStatus.FAILED,
    RemediationJobStatus.CANCELLED,
    RemediationJobStatus.TIMED_OUT,
})

TERMINAL_BROKER = frozenset({
    BrokerOptOutStatus.SUBMITTED,
    BrokerOptOutStatus.SKIPPED_FRESH,
    BrokerOptOutStatus.NOT_LISTED,
    BrokerOptOutStatus.VERIFIED_REMOVED,
    BrokerOptOutStatus.STILL_LISTED,
    BrokerOptOutStatus.ERROR,
    BrokerOptOutStatus.DEAD,
    BrokerOptOutStatus.CANCELLED,
    BrokerOptOutStatus.MANUAL_NEEDED,  # terminal for auto runner; user may resume
    BrokerOptOutStatus.AWAITING_EMAIL_CONFIRM,  # semi-terminal until confirm
    BrokerOptOutStatus.CAPTCHA_NEEDED,
})


class InvalidTransition(ValueError):
    pass


_JOB_TRANSITIONS: dict[RemediationJobStatus, set[RemediationJobStatus]] = {
    RemediationJobStatus.PENDING: {
        RemediationJobStatus.RUNNING,
        RemediationJobStatus.CANCELLED,
        RemediationJobStatus.TIMED_OUT,
        RemediationJobStatus.FAILED,
    },
    RemediationJobStatus.RUNNING: {
        RemediationJobStatus.WAITING_CAPTCHA,
        RemediationJobStatus.WAITING_EMAIL_CONFIRM,
        RemediationJobStatus.WAITING_MANUAL,
        RemediationJobStatus.VERIFYING,
        RemediationJobStatus.COMPLETED,
        RemediationJobStatus.PARTIAL,
        RemediationJobStatus.FAILED,
        RemediationJobStatus.CANCELLED,
        RemediationJobStatus.TIMED_OUT,
    },
    RemediationJobStatus.WAITING_CAPTCHA: {
        RemediationJobStatus.RUNNING,
        RemediationJobStatus.WAITING_MANUAL,
        RemediationJobStatus.CANCELLED,
        RemediationJobStatus.TIMED_OUT,
        RemediationJobStatus.FAILED,
    },
    RemediationJobStatus.WAITING_EMAIL_CONFIRM: {
        RemediationJobStatus.RUNNING,
        RemediationJobStatus.VERIFYING,
        RemediationJobStatus.COMPLETED,
        RemediationJobStatus.PARTIAL,
        RemediationJobStatus.CANCELLED,
        RemediationJobStatus.TIMED_OUT,
    },
    RemediationJobStatus.WAITING_MANUAL: {
        RemediationJobStatus.RUNNING,
        RemediationJobStatus.COMPLETED,
        RemediationJobStatus.PARTIAL,
        RemediationJobStatus.CANCELLED,
        RemediationJobStatus.TIMED_OUT,
    },
    RemediationJobStatus.VERIFYING: {
        RemediationJobStatus.COMPLETED,
        RemediationJobStatus.PARTIAL,
        RemediationJobStatus.FAILED,
        RemediationJobStatus.TIMED_OUT,
    },
    RemediationJobStatus.COMPLETED: set(),
    RemediationJobStatus.PARTIAL: set(),
    RemediationJobStatus.FAILED: set(),
    RemediationJobStatus.CANCELLED: set(),
    RemediationJobStatus.TIMED_OUT: set(),
}


def transition_job(current: RemediationJobStatus | str, new: RemediationJobStatus | str) -> RemediationJobStatus:
    cur = RemediationJobStatus(current)
    nxt = RemediationJobStatus(new)
    if cur == nxt:
        return cur
    if nxt not in _JOB_TRANSITIONS.get(cur, set()):
        raise InvalidTransition(f"Invalid remediation job transition {cur.value} → {nxt.value}")
    return nxt


def is_terminal_job(status: RemediationJobStatus | str) -> bool:
    return RemediationJobStatus(status) in TERMINAL_JOB


def is_fresh_optout(last_success_iso: str | None, recheck_days: int, now_iso: str | None = None) -> bool:
    """AIDR skip-if-fresh within recheck window."""
    if not last_success_iso:
        return False
    from datetime import datetime, timedelta
    try:
        last = datetime.fromisoformat(last_success_iso.replace("Z", "+00:00"))
        now = datetime.fromisoformat(now_iso.replace("Z", "+00:00")) if now_iso else datetime.now(UTC)
        return (now - last) < timedelta(days=recheck_days)
    except Exception:
        return False
