import pytest
from app.domain.scan_states import (
    ScanStatus,
    ConnectorRunStatus,
    transition_scan,
    transition_run,
    InvalidTransition,
    is_terminal_scan,
    derive_scan_status_from_runs,
)


def test_scan_happy_path():
    assert transition_scan(ScanStatus.PENDING, ScanStatus.RUNNING) == ScanStatus.RUNNING
    assert transition_scan(ScanStatus.RUNNING, ScanStatus.COMPLETED) == ScanStatus.COMPLETED
    assert is_terminal_scan(ScanStatus.COMPLETED)


def test_invalid_scan_transition():
    with pytest.raises(InvalidTransition):
        transition_scan(ScanStatus.COMPLETED, ScanStatus.RUNNING)


def test_derive_partial():
    s = derive_scan_status_from_runs(
        [ConnectorRunStatus.SUCCEEDED, ConnectorRunStatus.SKIPPED, ConnectorRunStatus.FAILED]
    )
    assert s == ScanStatus.PARTIAL


def test_derive_all_success():
    s = derive_scan_status_from_runs([ConnectorRunStatus.SUCCEEDED, ConnectorRunStatus.SUCCEEDED])
    assert s == ScanStatus.COMPLETED


def test_derive_still_running():
    s = derive_scan_status_from_runs([ConnectorRunStatus.SUCCEEDED, ConnectorRunStatus.PENDING])
    assert s == ScanStatus.RUNNING
