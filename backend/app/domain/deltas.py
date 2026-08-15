"""Pure delta helpers for scores and findings (AIDR lib/diff.js lineage)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ScoreDelta:
    before: float
    after: float
    delta: float
    severity_before: str
    severity_after: str
    improved: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "before": self.before,
            "after": self.after,
            "delta": round(self.delta, 2),
            "severity_before": self.severity_before,
            "severity_after": self.severity_after,
            "improved": self.improved,
            "summary": (
                f"PDSS {self.before:.1f}→{self.after:.1f} (Δ {self.delta:+.1f}); "
                f"{self.severity_before}→{self.severity_after}"
            ),
        }


@dataclass
class FindingDelta:
    new_finding_ids: list[str]
    resolved_finding_ids: list[str]
    regressed_finding_ids: list[str]
    unchanged_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "new_finding_ids": self.new_finding_ids,
            "resolved_finding_ids": self.resolved_finding_ids,
            "regressed_finding_ids": self.regressed_finding_ids,
            "unchanged_count": self.unchanged_count,
            "summary": (
                f"+{len(self.new_finding_ids)} new, "
                f"{len(self.resolved_finding_ids)} resolved, "
                f"{len(self.regressed_finding_ids)} regressed"
            ),
        }


def score_delta(
    before_score: float,
    after_score: float,
    severity_before: str,
    severity_after: str,
) -> ScoreDelta:
    d = after_score - before_score
    return ScoreDelta(
        before=before_score,
        after=after_score,
        delta=d,
        severity_before=severity_before,
        severity_after=severity_after,
        improved=d < 0,
    )


def finding_delta(
    prev_open_ids: set[str],
    curr_open_ids: set[str],
    *,
    prev_resolved_ids: set[str] | None = None,
) -> FindingDelta:
    prev_resolved_ids = prev_resolved_ids or set()
    new = sorted(curr_open_ids - prev_open_ids)
    resolved = sorted(prev_open_ids - curr_open_ids)
    # regressed: was resolved, now open again
    regressed = sorted(curr_open_ids & prev_resolved_ids)
    unchanged = len(prev_open_ids & curr_open_ids)
    return FindingDelta(
        new_finding_ids=new,
        resolved_finding_ids=resolved,
        regressed_finding_ids=regressed,
        unchanged_count=unchanged,
    )
