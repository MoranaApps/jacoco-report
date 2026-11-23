"""
A module matching evaluated reports to their baseline and computing the coverage change (Δ) against it.
"""

import logging
from dataclasses import dataclass
from typing import Callable, Collection, Iterable, Optional

from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.model.counter import Counter
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage

logger = logging.getLogger(__name__)

# A (current, baseline) report pair, matched by path or by report name.
_Pair = tuple[EvaluatedReportCoverage, EvaluatedReportCoverage]

NO_BASELINE_VIOLATION = (
    "'no-decrease' needs a baseline, but no baseline report was found. "
    "Set 'baseline-paths' to the JaCoCo reports of the base branch."
)
NO_MATCH_VIOLATION = (
    "'no-decrease' found baseline reports, but none matches a current report by path or report name, "
    "so no coverage drop could be checked."
)


@dataclass(frozen=True)
class CoverageDelta:
    """The coverage change against the baseline in percentage points, rounded to two decimals."""

    overall: float
    changed_files: float

    def to_dict(self) -> dict[str, float]:
        """Return the delta as the `delta` object of the reports-coverage and groups-coverage outputs."""
        return {"overall": self.overall, "changed_files": self.changed_files}


@dataclass(frozen=True)
class OverallChange:
    """The overall coverage of one row (global, group or report) against its baseline, for the 'no-decrease' gate.

    `baseline` and `current` are coverage percentages, `delta` the change in percentage points as the comment shows
    it, and `missed_increased` whether the missed count of the selected metric grew.
    """

    baseline: float
    current: float
    delta: float
    missed_increased: bool

    def is_drop(self, max_decrease: float) -> bool:
        """Return whether coverage fell by more than `max_decrease` percentage points and more code is missed."""
        return self.delta < -max_decrease and self.missed_increased


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


def _overall_counter(report: EvaluatedReportCoverage) -> Counter:
    return report.overall_coverage


def _changed_files_counter(report: EvaluatedReportCoverage) -> Counter:
    return report.avg_changed_files_coverage


def _aggregate_counters(
    current_reports: Collection[EvaluatedReportCoverage],
    pairs: list[_Pair],
    select: Callable[[EvaluatedReportCoverage], Counter],
) -> tuple[Counter, Counter]:
    """Return the (current, baseline) counters of a set of reports, the counter chosen by `select`.

    The baseline is the same set with each matched report's counters swapped for its baseline counters; unmatched
    reports count as unchanged, so a baseline that covers only some reports still gives the change of those reports,
    weighted by the whole set.
    """
    curr = Counter(0, 0)
    for report in current_reports:
        curr.append(select(report))

    bs = Counter(curr.missed, curr.covered)
    for curr_report, bs_report in pairs:
        bs.append(
            select(bs_report).missed - select(curr_report).missed,
            select(bs_report).covered - select(curr_report).covered,
        )
    return curr, bs


def _aggregate_delta(current_reports: Collection[EvaluatedReportCoverage], pairs: list[_Pair]) -> CoverageDelta:
    """Return the delta of a set of reports, overall and changed files, as `_aggregate_counters` defines it."""
    curr_o, bs_o = _aggregate_counters(current_reports, pairs, _overall_counter)
    curr_ch, bs_ch = _aggregate_counters(current_reports, pairs, _changed_files_counter)
    return CoverageDelta(_change(curr_o, bs_o), _change(curr_ch, bs_ch))


def _aggregate_overall_change(
    current_reports: Collection[EvaluatedReportCoverage], pairs: list[_Pair]
) -> OverallChange:
    """Return the overall change of a set of reports, the coverage percentages from the same counters as the Δ."""
    curr, bs = _aggregate_counters(current_reports, pairs, _overall_counter)
    return OverallChange(
        baseline=bs.coverage(),
        current=curr.coverage(),
        delta=_change(curr, bs),
        missed_increased=curr.missed > bs.missed,
    )


def _report_overall_delta(report: EvaluatedReportCoverage, bs_report: EvaluatedReportCoverage) -> float:
    """Return the overall change of one report in percentage points, from the reached values."""
    return _round_pp(report.overall_coverage_reached - bs_report.overall_coverage_reached)


def _drop_message(subject: str, change: OverallChange, max_decrease: float) -> str:
    """Return the 'no-decrease' violation for one row that dropped."""
    return (
        f"{subject} dropped from {change.baseline} to {change.current} ({change.delta} percentage points) "
        f"against the baseline, more than 'max-decrease' {max_decrease}."
    )


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
            _report_overall_delta(evaluated_report, bs_report),
            _round_pp(
                evaluated_report.avg_changed_files_coverage_reached - bs_report.avg_changed_files_coverage_reached
            ),
        )

    def group_delta(self, evaluated_group: EvaluatedReportCoverage) -> Optional[CoverageDelta]:
        """Return the delta of one group, or None when the group has no baseline or none of its reports matched."""
        scope = self._group_scope(evaluated_group)
        if scope is None:
            return None

        group_reports, pairs = scope
        return _aggregate_delta(group_reports.values(), pairs)

    def global_delta(self) -> Optional[CoverageDelta]:
        """Return the delta across all evaluated reports, or None when there is no baseline or no report matched."""
        pairs = self._global_pairs()
        if pairs is None:
            return None

        return _aggregate_delta(self.evaluator.evaluated_reports_coverage.values(), pairs)

    def no_decrease_violations(
        self,
        max_decrease: float,
        unchanged_reports: Collection[EvaluatedReportCoverage] = (),
        match_evidence: Collection[EvaluatedReportCoverage] = (),
    ) -> list[str]:
        """Return the 'no-decrease' violations: rows whose overall coverage dropped against the baseline.

        Checks the global row, every group and every report of the evaluator, then each of `unchanged_reports` as a
        report row, in that order. The global and group rows cover the evaluator only. A row dropped when its coverage
        fell by more than `max_decrease` percentage points and its missed count grew. A row with no matching baseline is
        skipped with an INFO log. `match_evidence` reports are never checked for drops; they only count as matches, so
        a PR that adds a module is not a misconfiguration. With no baseline data, or no match among the evaluator,
        `unchanged_reports` and `match_evidence`, the only violation says so. When only those matched, the global row is
        skipped with an INFO log.
        """
        if not self.has_baseline_data():
            return [NO_BASELINE_VIOLATION]
        global_pairs = self._global_pairs()
        matched_outside_evaluator = any(
            self.find_baseline_report(report) is not None for report in (*unchanged_reports, *match_evidence)
        )
        if global_pairs is None and not matched_outside_evaluator:
            return [NO_MATCH_VIOLATION]

        violations: list[str] = []
        if global_pairs is None:
            logger.info("Global overall coverage has no matching baseline report, skipped by 'no-decrease'.")
        else:
            global_change = _aggregate_overall_change(self.evaluator.evaluated_reports_coverage.values(), global_pairs)
            if global_change.is_drop(max_decrease):
                violations.append(_drop_message("Global overall coverage", global_change, max_decrease))

        for group in self.evaluator.evaluated_groups_coverage.values():
            group_change = self._group_change(group)
            if group_change is None:
                logger.info(
                    "Group '%s' has no matching baseline group or report, skipped by 'no-decrease'.", group.name
                )
            elif group_change.is_drop(max_decrease):
                violations.append(_drop_message(f"Group '{group.name}' overall coverage", group_change, max_decrease))

        violations.extend(self._report_violations(self.evaluator.evaluated_reports_coverage.values(), max_decrease))
        violations.extend(self._report_violations(unchanged_reports, max_decrease))
        return violations

    def _report_violations(self, reports: Iterable[EvaluatedReportCoverage], max_decrease: float) -> list[str]:
        """Return the 'no-decrease' violations of report rows; a report without a matching baseline is skipped."""
        violations: list[str] = []
        for report in reports:
            report_change = self._report_change(report)
            if report_change is None:
                logger.info("Report '%s' has no matching baseline report, skipped by 'no-decrease'.", report.name)
            elif report_change.is_drop(max_decrease):
                violations.append(
                    _drop_message(f"Report '{report.name}' overall coverage", report_change, max_decrease)
                )
        return violations

    def _report_change(self, evaluated_report: EvaluatedReportCoverage) -> Optional[OverallChange]:
        """Return the overall change of one report, or None when no baseline report matches it."""
        bs_report = self.find_baseline_report(evaluated_report)
        if bs_report is None:
            return None

        return OverallChange(
            baseline=bs_report.overall_coverage_reached,
            current=evaluated_report.overall_coverage_reached,
            delta=_report_overall_delta(evaluated_report, bs_report),
            missed_increased=evaluated_report.overall_coverage.missed > bs_report.overall_coverage.missed,
        )

    def _group_change(self, evaluated_group: EvaluatedReportCoverage) -> Optional[OverallChange]:
        """Return the overall change of one group, or None when it has no baseline or none of its reports matched."""
        scope = self._group_scope(evaluated_group)
        if scope is None:
            return None

        group_reports, pairs = scope
        return _aggregate_overall_change(group_reports.values(), pairs)

    def _global_pairs(self) -> Optional[list[_Pair]]:
        """Return the matched pairs of all evaluated reports, or None when there is no baseline or no report matched."""
        if not self.has_baseline_data():
            return None

        pairs = self._matched_pairs(self.evaluator.evaluated_reports_coverage)
        return pairs if pairs else None

    def _group_scope(
        self, evaluated_group: EvaluatedReportCoverage
    ) -> Optional[tuple[dict[str, EvaluatedReportCoverage], list[_Pair]]]:
        """Return the reports of a group with their matched pairs, or None when it has no baseline or no match."""
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

        return group_reports, pairs

    def _matched_pairs(self, current_reports: dict[str, EvaluatedReportCoverage]) -> list[_Pair]:
        """Pair current reports with baseline reports: by path when any path matches, otherwise by report name."""
        if self.bs_evaluator is None:
            return []
        bs_by_path = self.bs_evaluator.evaluated_reports_coverage

        matched_paths = set(current_reports.keys()) & set(bs_by_path.keys())
        if matched_paths:
            return [(current_reports[p], bs_by_path[p]) for p in matched_paths]

        bs_by_name = {v.name: v for v in bs_by_path.values()}
        return [(curr, bs_by_name[curr.name]) for curr in current_reports.values() if curr.name in bs_by_name]
