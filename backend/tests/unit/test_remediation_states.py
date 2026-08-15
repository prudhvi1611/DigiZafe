import pytest
from app.domain.remediation_states import (
    transition_job,
    RemediationJobStatus,
    InvalidTransition,
    is_fresh_optout,
)


def test_job_running_to_completed():
    assert transition_job(RemediationJobStatus.RUNNING, RemediationJobStatus.COMPLETED) == RemediationJobStatus.COMPLETED


def test_invalid_terminal():
    with pytest.raises(InvalidTransition):
        transition_job(RemediationJobStatus.COMPLETED, RemediationJobStatus.RUNNING)


def test_fresh_optout():
    from datetime import datetime, timezone, timedelta
    last = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    assert is_fresh_optout(last, 90) is True
    old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    assert is_fresh_optout(old, 90) is False
