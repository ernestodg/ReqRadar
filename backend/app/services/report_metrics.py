from collections import Counter
from dataclasses import dataclass

from app.models import ChangeType, Comparison, ImpactFinding, RequirementChange, ReviewStatus, Severity


@dataclass(frozen=True)
class ReportStats:
    modified: int
    added: int
    removed: int
    unchanged: int
    total_findings: int
    severity_counts: Counter
    review_counts: Counter

    @property
    def changed_total(self) -> int:
        return self.modified + self.added + self.removed

    @property
    def reviewed_total(self) -> int:
        return self.review_counts[ReviewStatus.CONFIRMED] + self.review_counts[ReviewStatus.DISMISSED]


def calculate_report_stats(comparison: Comparison, changes: list[RequirementChange], findings: list[ImpactFinding]) -> ReportStats:
    change_counts = Counter(change.change_type for change in changes)
    summary = comparison.summary_json or {}
    return ReportStats(
        modified=change_counts[ChangeType.MODIFIED] or int(summary.get(ChangeType.MODIFIED.value, 0) or 0),
        added=change_counts[ChangeType.ADDED] or int(summary.get(ChangeType.ADDED.value, 0) or 0),
        removed=change_counts[ChangeType.REMOVED] or int(summary.get(ChangeType.REMOVED.value, 0) or 0),
        unchanged=change_counts[ChangeType.UNCHANGED] or int(summary.get(ChangeType.UNCHANGED.value, 0) or 0),
        total_findings=len(findings),
        severity_counts=Counter(finding.severity for finding in findings),
        review_counts=Counter(finding.review_status for finding in findings),
    )


def report_summary_json(stats: ReportStats) -> dict[str, int]:
    return {
        ChangeType.MODIFIED.value: stats.modified,
        ChangeType.ADDED.value: stats.added,
        ChangeType.REMOVED.value: stats.removed,
        ChangeType.UNCHANGED.value: stats.unchanged,
        "impact_findings": stats.total_findings,
        "high_impact": stats.severity_counts[Severity.HIGH],
        "medium_impact": stats.severity_counts[Severity.MEDIUM],
        "low_impact": stats.severity_counts[Severity.LOW],
        "reviewed": stats.reviewed_total,
        "confirmed": stats.review_counts[ReviewStatus.CONFIRMED],
        "dismissed": stats.review_counts[ReviewStatus.DISMISSED],
        "unreviewed": stats.review_counts[ReviewStatus.UNREVIEWED],
    }
