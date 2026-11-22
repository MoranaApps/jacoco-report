"""
A module matching evaluated reports to their baseline and computing the coverage change (Δ) against it.
"""

from dataclasses import dataclass
from typing import Iterable, Optional

from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.model.counter import Counter
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage


@dataclass(frozen=True)
class CoverageDelta:
    """The coverage change against the baseline in percentage points, rounded to two decimals."""

    overall: float
    changed_files: float

    def to_dict(self) -> dict[str, float]:
        """Return the delta as the `delta` object of the reports-coverage and groups-coverage outputs."""
        return {"overall": self.overall, "changed_files": self.changed_files}


def _round_pp(value: float) -> float:
    """Round a change in percentage points to two decimals; adding 0.0 turns -0.0 into 0.0."""
    return round(value, 2) + 0.0


def _percent(counter: Counter) -> float:
    """Return the unrounded coverage of a counter in percent, 0.0 for an empty counter."""
    total = counter.missed + counter.covered
    return counter.covered / total * 100 if total > 0 else 0.0


def _change(current: Counter, baseline: Counter) -> float:
    """Return the change from baseline to current coverage; 0.0 when the current counter is empty."""
    if current.missed + current.covered == 0:
        return 0.0
    return _round_pp(_percent(current) - _percent(baseline))


def _aggregate_delta(
    current_reports: Iterable[EvaluatedReportCoverage],
    pairs: list[tuple[EvaluatedReportCoverage, EvaluatedReportCoverage]],
) -> CoverageDelta:
    """Return the delta of a set of reports: their coverage now minus the same set with matched reports swapped.

    Each matched report's counters are replaced by its baseline counters; unmatched reports count as unchanged, so a
    baseline that covers only some reports still gives the change of those reports, weighted by the whole set.
    """
    curr_o, curr_ch = Counter(0, 0), Counter(0, 0)
    for report in current_reports:
        curr_o.append(report.overall_coverage)
        curr_ch.append(report.avg_changed_files_coverage)

    bs_o = Counter(curr_o.missed, curr_o.covered)
    bs_ch = Counter(curr_ch.missed, curr_ch.covered)
    for curr, bs in pairs:
        bs_o.append(
            bs.overall_coverage.missed - curr.overall_coverage.missed,
            bs.overall_coverage.covered - curr.overall_coverage.covered,
        )
        bs_ch.append(
            bs.avg_changed_files_coverage.missed - curr.avg_changed_files_coverage.missed,
            bs.avg_changed_files_coverage.covered - curr.avg_changed_files_coverage.covered,
        )

    return CoverageDelta(_change(curr_o, bs_o), _change(curr_ch, bs_ch))


class BaselineComparison:
    """
    Compares the evaluated reports and groups with the baseline evaluator.

    The PR comment, the job summary and the action outputs all take their Δ from here, so they show the same numbers.
    A report is matched to a baseline report by path (same directory structure), else by report name, for setups
    where current and baseline reports live in different directory trees.
    """

    def __init__(self, evaluator: CoverageEvaluator, bs_evaluator: Optional[CoverageEvaluator]):
        self.evaluator: CoverageEvaluator = evaluator
        self.bs_evaluator: Optional[CoverageEvaluator] = bs_evaluator

    def has_baseline_data(self) -> bool:
        """Return whether the baseline holds any evaluated report or group."""
        if self.bs_evaluator is None:
            return False

        return bool(self.bs_evaluator.evaluated_reports_coverage) or bool(self.bs_evaluator.evaluated_groups_coverage)

    def find_baseline_report(self, evaluated_report: EvaluatedReportCoverage) -> Optional[EvaluatedReportCoverage]:
        """Return the baseline report matching one evaluated report, or None."""
        if self.bs_evaluator is None:
            return None
        bs = self.bs_evaluator.evaluated_reports_coverage
        if evaluated_report.path and evaluated_report.path in bs:
            return bs[evaluated_report.path]
        return next((v for v in bs.values() if v.name == evaluated_report.name), None)

    def report_delta(self, evaluated_report: EvaluatedReportCoverage) -> Optional[CoverageDelta]:
        """Return the delta of one report, or None when no baseline report matches it."""
        bs_report = self.find_baseline_report(evaluated_report)
        if bs_report is None:
            return None

        return CoverageDelta(
            _round_pp(evaluated_report.overall_coverage_reached - bs_report.overall_coverage_reached),
            _round_pp(
                evaluated_report.avg_changed_files_coverage_reached - bs_report.avg_changed_files_coverage_reached
            ),
        )

    def group_delta(self, evaluated_group: EvaluatedReportCoverage) -> Optional[CoverageDelta]:
        """Return the delta of one group, or None when the group has no baseline or none of its reports matched."""
        if self.bs_evaluator is None or evaluated_group.name not in self.bs_evaluator.evaluated_groups_coverage:
            return None

        group_reports = {
            path: erc
            for path, erc in self.evaluator.evaluated_reports_coverage.items()
            if erc.group_name == evaluated_group.name
        }
        pairs = self._matched_pairs(group_reports)
        if not pairs:
            return None

        return _aggregate_delta(group_reports.values(), pairs)

    def global_delta(self) -> Optional[CoverageDelta]:
        """Return the delta across all evaluated reports, or None when there is no baseline or no report matched."""
        if not self.has_baseline_data():
            return None

        pairs = self._matched_pairs(self.evaluator.evaluated_reports_coverage)
        if not pairs:
            return None

        return _aggregate_delta(self.evaluator.evaluated_reports_coverage.values(), pairs)

    def _matched_pairs(
        self, current_reports: dict[str, EvaluatedReportCoverage]
    ) -> list[tuple[EvaluatedReportCoverage, EvaluatedReportCoverage]]:
        """Pair current reports with baseline reports: by path when any path matches, otherwise by report name."""
        if self.bs_evaluator is None:
            return []
        bs_by_path = self.bs_evaluator.evaluated_reports_coverage

        matched_paths = set(current_reports.keys()) & set(bs_by_path.keys())
        if matched_paths:
            return [(current_reports[p], bs_by_path[p]) for p in matched_paths]

        bs_by_name = {v.name: v for v in bs_by_path.values()}
        return [(curr, bs_by_name[curr.name]) for curr in current_reports.values() if curr.name in bs_by_name]
