"""Scan / connector-run state machine (pure)."""
from __future__ import annotations

from enum import Enum


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"  # finished with some connector failures/skips
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ConnectorRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


# Terminal scan statuses
TERMINAL_SCAN: frozenset[ScanStatus] = frozenset(
    {
        ScanStatus.COMPLETED,
        ScanStatus.PARTIAL,
        ScanStatus.FAILED,
        ScanStatus.CANCELLED,
        ScanStatus.TIMED_OUT,
    }
)

TERMINAL_RUN: frozenset[ConnectorRunStatus] = frozenset(
    {
        ConnectorRunStatus.SUCCEEDED,
        ConnectorRunStatus.SKIPPED,
        ConnectorRunStatus.FAILED,
        ConnectorRunStatus.TIMED_OUT,
    }
)

# Allowed transitions: from -> set of to
_SCAN_TRANSITIONS: dict[ScanStatus, set[ScanStatus]] = {
    ScanStatus.PENDING: {ScanStatus.RUNNING, ScanStatus.CANCELLED, ScanStatus.TIMED_OUT, ScanStatus.FAILED},
    ScanStatus.RUNNING: {
        ScanStatus.COMPLETED,
        ScanStatus.PARTIAL,
        ScanStatus.FAILED,
        ScanStatus.CANCELLED,
        ScanStatus.TIMED_OUT,
    },
    # Terminal states have no outgoing transitions
    ScanStatus.COMPLETED: set(),
    ScanStatus.PARTIAL: set(),
    ScanStatus.FAILED: set(),
    ScanStatus.CANCELLED: set(),
    ScanStatus.TIMED_OUT: set(),
}

_RUN_TRANSITIONS: dict[ConnectorRunStatus, set[ConnectorRunStatus]] = {
    ConnectorRunStatus.PENDING: {
        ConnectorRunStatus.RUNNING,
        ConnectorRunStatus.SKIPPED,
        ConnectorRunStatus.FAILED,
        ConnectorRunStatus.TIMED_OUT,
    },
    ConnectorRunStatus.RUNNING: {
        ConnectorRunStatus.SUCCEEDED,
        ConnectorRunStatus.SKIPPED,
        ConnectorRunStatus.FAILED,
        ConnectorRunStatus.TIMED_OUT,
    },
    ConnectorRunStatus.SUCCEEDED: set(),
    ConnectorRunStatus.SKIPPED: set(),
    ConnectorRunStatus.FAILED: set(),
    ConnectorRunStatus.TIMED_OUT: set(),
}


class InvalidTransition(ValueError):
    pass


def can_transition_scan(current: ScanStatus | str, new: ScanStatus | str) -> bool:
    cur = ScanStatus(current)
    nxt = ScanStatus(new)
    if cur == nxt:
        return True
    return nxt in _SCAN_TRANSITIONS.get(cur, set())


def transition_scan(current: ScanStatus | str, new: ScanStatus | str) -> ScanStatus:
    cur = ScanStatus(current)
    nxt = ScanStatus(new)
    if cur == nxt:
        return cur
    if nxt not in _SCAN_TRANSITIONS.get(cur, set()):
        raise InvalidTransition(f"Invalid scan transition {cur.value} → {nxt.value}")
    return nxt


def can_transition_run(current: ConnectorRunStatus | str, new: ConnectorRunStatus | str) -> bool:
    cur = ConnectorRunStatus(current)
    nxt = ConnectorRunStatus(new)
    if cur == nxt:
        return True
    allowed = _RUN_TRANSITIONS.get(cur, set())
    # PENDING can also go to SUCCEEDED directly in edge cases
    if cur == ConnectorRunStatus.PENDING:
        allowed = allowed | {
            ConnectorRunStatus.SUCCEEDED,
            ConnectorRunStatus.SKIPPED,
            ConnectorRunStatus.FAILED,
            ConnectorRunStatus.TIMED_OUT,
            ConnectorRunStatus.RUNNING,
        }
    return nxt in allowed


def transition_run(current: ConnectorRunStatus | str, new: ConnectorRunStatus | str) -> ConnectorRunStatus:
    cur = ConnectorRunStatus(current)
    nxt = ConnectorRunStatus(new)
    if cur == nxt:
        return cur
    if not can_transition_run(cur, nxt):
        raise InvalidTransition(f"Invalid connector-run transition {cur.value} → {nxt.value}")
    return nxt


def is_terminal_scan(status: ScanStatus | str) -> bool:
    return ScanStatus(status) in TERMINAL_SCAN


def is_terminal_run(status: ConnectorRunStatus | str) -> bool:
    return ConnectorRunStatus(status) in TERMINAL_RUN


def derive_scan_status_from_runs(
    run_statuses: list[ConnectorRunStatus | str],
) -> ScanStatus:
    """
    After all runs terminal:
    - all succeeded (or empty) → COMPLETED
    - mix of success + skip/fail → PARTIAL
    - all failed/timed_out (no success) → FAILED
    - any still non-terminal → RUNNING (caller should not finalize yet)
    """
    if not run_statuses:
        return ScanStatus.COMPLETED

    statuses = [ConnectorRunStatus(s) for s in run_statuses]
    if any(not is_terminal_run(s) for s in statuses):
        return ScanStatus.RUNNING

    successes = sum(1 for s in statuses if s == ConnectorRunStatus.SUCCEEDED)
    fails = sum(
        1
        for s in statuses
        if s in (ConnectorRunStatus.FAILED, ConnectorRunStatus.TIMED_OUT)
    )
    skips = sum(1 for s in statuses if s == ConnectorRunStatus.SKIPPED)

    if successes > 0 and (fails > 0 or skips > 0):
        return ScanStatus.PARTIAL
    if successes > 0 and fails == 0:
        return ScanStatus.COMPLETED
    if successes == 0 and skips > 0 and fails == 0:
        return ScanStatus.COMPLETED  # all intentionally skipped
    return ScanStatus.FAILED
