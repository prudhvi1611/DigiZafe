from app.domain.deltas import score_delta, finding_delta


def test_score_improved():
    d = score_delta(7.0, 5.5, "high", "medium")
    assert d.improved
    assert d.delta == -1.5


def test_finding_delta_new_and_resolved():
    fd = finding_delta({"a", "b"}, {"b", "c"}, prev_resolved_ids={"c"})
    assert "c" in fd.new_finding_ids
    assert "a" in fd.resolved_finding_ids
    assert "c" in fd.regressed_finding_ids
