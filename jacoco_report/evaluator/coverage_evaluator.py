"""
A module evaluating the coverage of the reports.
"""

import logging

from typing import Optional

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.model.counter import Counter
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.model.report_group import ReportGroup

logger = logging.getLogger(__name__)


class CoverageEvaluator:
    """
    A class evaluating the coverage of the reports.
    The target is to evaluate coverage percentages of overall coverage and changed files coverage and
    to check if they pass the thresholds.
    """

    def __init__(
        self,
        report_files_coverage: list[ReportFileCoverage],
        global_min_coverage_overall: float,
        global_min_coverage_changed_files: float,
        report_groups: Optional[list[ReportGroup]] = None,
        report_thresholds_default: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ):
        # input data stats
        self._report_files_coverage: list[ReportFileCoverage] = report_files_coverage

        # thresholds
        self._global_min_coverage_overall: float = global_min_coverage_overall
        self._global_min_coverage_changed_files: float = global_min_coverage_changed_files
        # Per-report/group fallback: group field → report-thresholds-default field → 0.0
        # global-thresholds is a separate evaluation pass and is never in this chain.
        self._report_thresholds_default: tuple[float, float, float] = report_thresholds_default
        self._report_groups: list[ReportGroup] = report_groups if report_groups is not None else []
        self.report_group_order: list[str] = [group.name for group in self._report_groups]
        self._group_thresholds_lookup: dict[str, tuple[float, float, float]] = {
            group.name: (
                (
                    group.min_coverage_overall
                    if group.min_coverage_overall is not None
                    else self._report_thresholds_default[0]
                ),
                (
                    group.min_coverage_changed_files
                    if group.min_coverage_changed_files is not None
                    else self._report_thresholds_default[1]
                ),
                (
                    group.min_coverage_per_changed_file
                    if group.min_coverage_per_changed_file is not None
                    else self._report_thresholds_default[2]
                ),
            )
            for group in self._report_groups
        }

        # *** output data for the comment(s) ***
        # global data
        self.total_coverage_overall: float = 0.0
        self.total_coverage_overall_passed: bool = False
        self.total_coverage_changed_files: float = 0.0
        self.total_coverage_changed_files_passed: bool = False

        # evaluated group data
        self.evaluated_groups_coverage: dict[str, EvaluatedReportCoverage] = {}

        # evaluated report files data
        self.evaluated_reports_coverage: dict[str, EvaluatedReportCoverage] = {}

        # violations
        self.violations: list[str] = []
        self.reached_threshold_overall: bool = True
        self.reached_threshold_changed_files_average: bool = True
        self.reached_threshold_per_change_file: bool = True

    def evaluate(self) -> None:
        """
        Evaluates the coverage of the all reports.

        Returns:
            None
        """
        m = ActionInputs.get_metric()

        # sum variables needed for the evaluation
        global_overall = Counter(0, 0)
        global_changed_files = Counter(0, 0)
        changed_file_counter = 0

        # evaluation of all report files (report == input xml file)
        seen_report_names: set[str] = set()
        for report in self._report_files_coverage:
            evaluated_coverage_report: EvaluatedReportCoverage = EvaluatedReportCoverage(report.name, report.group_name)
            evaluated_coverage_report.path = report.path

            # get report's overall values
            mi, co = report.overall_coverage.get_values_by_metric(m)
            evaluated_coverage_report.overall_coverage_reached = report.overall_coverage.get_coverage_by_metric(m)
            evaluated_coverage_report.overall_coverage.append(mi, co)
            global_overall.append(mi, co)

            # get report's changed files values
            for key, changed_file_coverage in report.changed_files_coverage.items():
                mi, co = changed_file_coverage.get_values_by_metric(m)
                # Skip files with zero metric weight (no coverage data for selected metric)
                has_file_metric_weight = not (mi == 0 and co == 0)
                if not has_file_metric_weight:
                    continue
                changed_file_counter += 1
                global_changed_files.append(mi, co)  # sum all reports
                evaluated_coverage_report.changed_files_coverage_reached[key] = (
                    changed_file_coverage.get_coverage_by_metric(m)
                )
                evaluated_coverage_report.avg_changed_files_coverage.append(mi, co)

            # count reached values from raw weights - changed files
            evaluated_coverage_report.avg_changed_files_coverage_reached = (
                evaluated_coverage_report.avg_changed_files_coverage.coverage()
            )

            # Warn about duplicate XML report name; keying by path prevents data loss.
            if report.name in seen_report_names:
                logger.warning(
                    "Duplicate report name '%s' detected; using file path as unique key to prevent"
                    " data collision. Consider setting a unique <title> per module in the Maven"
                    " JaCoCo plugin to avoid confusion in the PR comment.",
                    report.name,
                )
            seen_report_names.add(report.name)
            self.evaluated_reports_coverage[report.path] = self._evaluate_report(report, evaluated_coverage_report)

        # evaluation of all groups (group == named set of reports with common paths/thresholds)
        for group in self._report_groups:
            evaluated_coverage_group: EvaluatedReportCoverage = EvaluatedReportCoverage(
                group.name, group_name=group.name
            )

            # aggregate all reports belonging to this group
            for evaluated_report_coverage in self.evaluated_reports_coverage.values():
                if evaluated_report_coverage.group_name == group.name:
                    evaluated_coverage_group.overall_coverage.append(evaluated_report_coverage.overall_coverage)
                    evaluated_coverage_group.avg_changed_files_coverage.append(
                        evaluated_report_coverage.avg_changed_files_coverage
                    )
                    evaluated_coverage_group.changed_files_passed.update(evaluated_report_coverage.changed_files_passed)
                    evaluated_coverage_group.changed_files_coverage_reached.update(
                        evaluated_report_coverage.changed_files_coverage_reached
                    )

            # count reached values from raw weights
            evaluated_coverage_group.overall_coverage_reached = evaluated_coverage_group.overall_coverage.coverage()
            evaluated_coverage_group.avg_changed_files_coverage_reached = (
                evaluated_coverage_group.avg_changed_files_coverage.coverage()
            )

            if (
                evaluated_coverage_group.overall_coverage.covered == 0
                and evaluated_coverage_group.overall_coverage.missed == 0
                and not any(ev.group_name == group.name for ev in self.evaluated_reports_coverage.values())
            ):
                logger.info("Group '%s' has no reports contributing after filtering.", group.name)

            # save the evaluated group
            self.evaluated_groups_coverage[group.name] = self.evaluate_group(evaluated_coverage_group, group)

        # evaluate the global coverage values
        self.total_coverage_overall = global_overall.coverage()
        self.total_coverage_changed_files = global_changed_files.coverage()
        self.total_coverage_overall_passed = self.total_coverage_overall >= self._global_min_coverage_overall

        if changed_file_counter == 0:
            self.total_coverage_changed_files_passed = True
        else:
            self.total_coverage_changed_files_passed = (
                self.total_coverage_changed_files >= self._global_min_coverage_changed_files
            )

        # review for violations
        self.review_violations()

    def review_violations(self) -> None:
        """
        Reviews the coverage evaluation results and appends violations to the violations list.
        """
        if not self.total_coverage_overall_passed:
            self.violations.append(
                f"Global overall coverage {self.total_coverage_overall} is below the threshold "
                f"{self._global_min_coverage_overall}."
            )
            self.reached_threshold_overall = False
        if not self.total_coverage_changed_files_passed:
            self.violations.append(
                f"Global changed files coverage {self.total_coverage_changed_files} is below the threshold "
                f"{self._global_min_coverage_changed_files}."
            )
            self.reached_threshold_changed_files_average = False

        # group violations
        group_violations: list[str] = []
        for group_name, evaluated_coverage_group in self.evaluated_groups_coverage.items():
            if not evaluated_coverage_group.overall_passed:
                group_violations.append(
                    f"Group '{group_name}' overall coverage {evaluated_coverage_group.overall_coverage_reached} "
                    f"is below the threshold {evaluated_coverage_group.overall_coverage_threshold}."
                )
                self.reached_threshold_overall = False
            if not evaluated_coverage_group.avg_changed_files_passed:
                group_violations.append(
                    f"Group '{group_name}' changed files coverage "
                    f"{evaluated_coverage_group.avg_changed_files_coverage_reached} is below the threshold "
                    f"{evaluated_coverage_group.changed_files_threshold}."
                )
                self.reached_threshold_changed_files_average = False

        report_violations: list[str] = []
        changed_files_violations: list[str] = []

        for evaluated_coverage_report in self.evaluated_reports_coverage.values():
            report_display = evaluated_coverage_report.name
            if not evaluated_coverage_report.overall_passed:
                report_violations.append(
                    f"Report '{report_display}' overall coverage {evaluated_coverage_report.overall_coverage_reached} "
                    f"is below the threshold {evaluated_coverage_report.overall_coverage_threshold}."
                )
                self.reached_threshold_overall = False
            if not evaluated_coverage_report.avg_changed_files_passed:
                report_violations.append(
                    f"Report '{report_display}' changed files coverage "
                    f"{evaluated_coverage_report.avg_changed_files_coverage_reached} is below the threshold "
                    f"{evaluated_coverage_report.changed_files_threshold}."
                )
                self.reached_threshold_changed_files_average = False
            for key, passed in evaluated_coverage_report.changed_files_passed.items():
                if not passed:
                    changed_files_violations.append(
                        f"Report '{report_display}' changed file '{key}' coverage "
                        f"{evaluated_coverage_report.changed_files_coverage_reached[key]} is below the threshold "
                        f"{evaluated_coverage_report.per_changed_file_threshold}."
                    )
                    self.reached_threshold_per_change_file = False

        # Add all violations to the list
        self.violations.extend(group_violations)
        self.violations.extend(report_violations)
        self.violations.extend(changed_files_violations)

    def evaluate_group(
        self, evaluated_coverage: EvaluatedReportCoverage, group: ReportGroup
    ) -> EvaluatedReportCoverage:
        """
        Evaluates the coverage of one report group.
        Uses group-level thresholds when set, otherwise falls back to report-thresholds-default (then 0.0).
        global-thresholds is a separate evaluation pass and is never in this fallback chain.
        """
        overall_threshold = (
            group.min_coverage_overall if group.min_coverage_overall is not None else self._report_thresholds_default[0]
        )
        changed_files_threshold = (
            group.min_coverage_changed_files
            if group.min_coverage_changed_files is not None
            else self._report_thresholds_default[1]
        )
        changed_per_file_threshold = (
            group.min_coverage_per_changed_file
            if group.min_coverage_per_changed_file is not None
            else self._report_thresholds_default[2]
        )
        evaluated_coverage.overall_coverage_threshold = overall_threshold
        evaluated_coverage.changed_files_threshold = changed_files_threshold
        evaluated_coverage.per_changed_file_threshold = changed_per_file_threshold

        has_overall_metric_weight = not (
            evaluated_coverage.overall_coverage.covered == 0 and evaluated_coverage.overall_coverage.missed == 0
        )
        if not has_overall_metric_weight:
            evaluated_coverage.overall_coverage_reached = 0.0
            evaluated_coverage.overall_passed = True
        else:
            evaluated_coverage.overall_passed = evaluated_coverage.overall_coverage_reached >= overall_threshold

        has_changed_files_for_log = bool(evaluated_coverage.changed_files_coverage_reached)
        has_changed_files_metric_weight = not (
            evaluated_coverage.avg_changed_files_coverage.covered == 0
            and evaluated_coverage.avg_changed_files_coverage.missed == 0
        )
        if not has_changed_files_metric_weight:
            evaluated_coverage.avg_changed_files_coverage_reached = 0.0
            evaluated_coverage.avg_changed_files_passed = True
        else:
            evaluated_coverage.avg_changed_files_passed = (
                evaluated_coverage.avg_changed_files_coverage_reached >= changed_files_threshold
            )

        if has_overall_metric_weight:
            logger.info(
                "Group '%s' reached overall coverage of %.1f%% with threshold set to %.1f%%",
                evaluated_coverage.name,
                evaluated_coverage.overall_coverage_reached,
                overall_threshold,
            )
        else:
            logger.info(
                "Group '%s' has no overall coverage data for selected metric; treated as passed.",
                evaluated_coverage.name,
            )
        # Log changed files info if there are files with metric weight OR if all files were filtered out (zero metric weight)
        if has_changed_files_for_log or not has_changed_files_metric_weight:
            if has_changed_files_metric_weight:
                logger.info(
                    "Group '%s' reached average changed files coverage of %.1f%% with threshold set to %.1f%%",
                    evaluated_coverage.name,
                    evaluated_coverage.avg_changed_files_coverage_reached,
                    changed_files_threshold,
                )
            else:
                logger.info(
                    "Group '%s' has no changed-files coverage data for selected metric; treated as passed.",
                    evaluated_coverage.name,
                )

        return evaluated_coverage

    def _evaluate_report(
        self, report_coverage: ReportFileCoverage, evaluated_coverage_report: EvaluatedReportCoverage
    ) -> EvaluatedReportCoverage:
        """
        Evaluates the coverage of the one report.
        Evaluation uses group thresholds when set, otherwise falls back to
        report-thresholds-default (then 0.0). global-thresholds is a separate
        evaluation pass and is never in this fallback chain.

        Parameters:
            report_coverage (ReportFileCoverage): The coverage of the report
            evaluated_coverage_report (EvaluatedReportCoverage): The evaluated coverage of the report

        Returns:
            EvaluatedReportCoverage: The evaluated coverage of the report
        """
        # get the thresholds for the report
        overall_threshold, changed_files_threshold, changed_per_file_threshold = self._set_thresholds(
            report_coverage.group_name
        )
        evaluated_coverage_report.overall_coverage_threshold = overall_threshold
        evaluated_coverage_report.changed_files_threshold = changed_files_threshold
        evaluated_coverage_report.per_changed_file_threshold = changed_per_file_threshold

        has_overall_metric_weight = not (
            evaluated_coverage_report.overall_coverage.covered == 0
            and evaluated_coverage_report.overall_coverage.missed == 0
        )
        if not has_overall_metric_weight:
            evaluated_coverage_report.overall_coverage_reached = 0.0
            evaluated_coverage_report.overall_passed = True
        else:
            evaluated_coverage_report.overall_passed = (
                evaluated_coverage_report.overall_coverage_reached >= overall_threshold
            )

        has_avg_changed_files_metric_weight = not (
            evaluated_coverage_report.avg_changed_files_coverage.covered == 0
            and evaluated_coverage_report.avg_changed_files_coverage.missed == 0
        )
        if not has_avg_changed_files_metric_weight:
            evaluated_coverage_report.avg_changed_files_coverage_reached = 0.0
            evaluated_coverage_report.avg_changed_files_passed = True
        else:
            evaluated_coverage_report.avg_changed_files_passed = (
                evaluated_coverage_report.avg_changed_files_coverage_reached >= changed_files_threshold
            )

        # Evaluate per-file thresholds only for changed files that have metric weight.
        # Files with zero coverage data (covered=0, missed=0) for selected metric are
        # filtered out and NOT included in changed_files_passed — they won't appear in PR comment tables.
        for key, changed_file_coverage in report_coverage.changed_files_coverage.items():
            metric = ActionInputs.get_metric()
            missed, covered = changed_file_coverage.get_values_by_metric(metric)
            has_file_metric_weight = not (missed == 0 and covered == 0)

            if has_file_metric_weight:
                evaluated_coverage_report.changed_files_passed[key] = (
                    changed_file_coverage.get_coverage_by_metric(metric) >= changed_per_file_threshold
                )

        if has_overall_metric_weight:
            logger.info(
                "Report '%s' reached overall coverage of %.1f%% with threshold set to %.1f%%",
                report_coverage.name,
                evaluated_coverage_report.overall_coverage_reached,
                overall_threshold,
            )
        else:
            logger.info(
                "Report '%s' has no overall coverage data for selected metric; treated as passed.",
                report_coverage.name,
            )
        if report_coverage.changed_files_coverage:
            if has_avg_changed_files_metric_weight:
                logger.info(
                    "Report '%s' reached average changed files coverage of %.1f%% with threshold set to %.1f%%",
                    report_coverage.name,
                    evaluated_coverage_report.avg_changed_files_coverage_reached,
                    changed_files_threshold,
                )
            else:
                logger.info(
                    "Report '%s' has no changed-files coverage data for selected metric; treated as passed.",
                    report_coverage.name,
                )

        return evaluated_coverage_report

    def _set_thresholds(self, group_name: str) -> tuple[float, float, float]:
        """
        Returns coverage thresholds for a report using the field-level fallback chain:
        group field → report-thresholds-default → 0.0.
        global-thresholds is a separate evaluation pass and is never in this chain.
        """
        return self._group_thresholds_lookup.get(group_name, self._report_thresholds_default)

    def changed_files_count(self) -> int:
        """
        Returns the total number of changed files across all reports.
        """
        return sum(len(report.changed_files_coverage) for report in self._report_files_coverage)
