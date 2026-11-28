"""
A module for generating the JaCoCo report.
"""

import json
import logging
from typing import Collection, Optional

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.evaluator.baseline_comparison import BaselineComparison, CoverageDelta
from jacoco_report.evaluator.baseline_verification import unverified_baseline_reason
from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.generator.pr_comment_generator import (
    SUMMARY_NO_COMMENT_INFO,
    PRCommentGenerator,
    all_filtered_summary_body,
)
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.model.report_group import ReportGroup
from jacoco_report.parser.jacoco_report_parser import JaCoCoReportParser
from jacoco_report.scanner.jacoco_report_input_scanner import JaCoCoReportInputScanner
from jacoco_report.utils.constants import DEFAULT_PATHS, GLOBAL_OVERALL_SCOPE_ALL
from jacoco_report.utils.enums import CommentLevelEnum, FailOnThresholdEnum, ReportTargetEnum
from jacoco_report.utils.gh_action import print_action_warning, write_job_summary
from jacoco_report.utils.github import GitHub, get_api_url

logger = logging.getLogger(__name__)

PR_COMMENT_MAY_BE_STALE_WARNING = (
    "The PR comment may not have been changed and may be out of date. See the job log for the error."
)


class JaCoCoReport:
    """
    A class representing the JaCoCo Report.
    A class analyzing the JaCoCo report and generating the comment.
    """

    def __init__(self):
        self.total_overall_coverage: float = 0.0
        self.total_changed_files_coverage: float = 0.0
        self.total_overall_coverage_passed: bool = False
        self.total_changed_files_coverage_passed: bool = False
        # Δ against the baseline in percentage points; None without a baseline or a matched baseline report.
        self.total_coverage_delta: Optional[CoverageDelta] = None
        # Whether the baseline matches baseline-sha; None when baseline-sha is not set.
        self.baseline_verified: Optional[bool] = None

        self.evaluated_coverage_reports: str = ""
        self.evaluated_coverage_groups: str = ""
        self.violations: list[str] = []

        self.reached_threshold_overall = True
        self.reached_threshold_changed_files_average = True
        self.reached_threshold_per_change_file = True
        self.reached_threshold_fail_unchanged = True
        self.reached_threshold_no_decrease = True
        self.has_operational_failure = False

    @property
    def total_overall_coverage_delta(self) -> Optional[float]:
        """The overall coverage Δ in percentage points, None without a matched baseline."""
        return None if self.total_coverage_delta is None else self.total_coverage_delta.overall

    @property
    def total_changed_files_coverage_delta(self) -> Optional[float]:
        """The changed-files coverage Δ in percentage points, None without a matched baseline."""
        return None if self.total_coverage_delta is None else self.total_coverage_delta.changed_files

    def run(self) -> None:
        """
        The main function to run the JaCoCo GitHub Action adding the JaCoCo coverage report to the pull request.
        """
        if ActionInputs.get_event_name() != "pull_request":
            logger.error("Not a pull request event. Ending.")
            self.violations.append("Not a pull request event.")
            self._mark_operational_failure()
            return
        logger.info("Event is a pull request.")

        gh = GitHub(ActionInputs.get_token(), ActionInputs.get_ca_bundle(), get_api_url())
        pr_number = ActionInputs.get_pr_number(gh=gh)
        if pr_number is None:
            logger.error("Not a pull request event. Ending run of Jacoco Report.")
            self.violations.append("No pull request number found.")
            self._mark_operational_failure()
            return
        logger.info("Pull request number: %s", pr_number)
        self._verify_baseline()

        # get report groups (if configured)
        report_groups: list[ReportGroup] = ActionInputs.get_report_groups()
        global_overall_scope = ActionInputs.get_global_overall_scope()

        top_level_report_paths = self._scan_reports(report_groups, global_overall_scope)

        # skip when no top-level jacoco xml files found (ungrouped flow only)
        if not report_groups and not top_level_report_paths:
            logger.error("No input JaCoCo xml file found. No comment will be generated.")
            self.violations.append("No input JaCoCo xml file found.")
            self._mark_operational_failure()
            return

        # get changed files in PR
        logger.info("Getting changed files in PR.")
        changed_files_result: list[str] | None = gh.get_pr_changed_files(pr_number)
        if changed_files_result is None:
            logger.error("Failed to retrieve changed files from GitHub API. Ending run.")
            self.violations.append("Failed to retrieve changed files from GitHub API.")
            self._mark_operational_failure()
            return
        all_changed_files_in_pr: list[str] = changed_files_result

        # analyse received xml report files
        parser = JaCoCoReportParser(all_changed_files_in_pr)
        report_files_coverage, ungrouped_reports = self._parse_reports(
            parser, report_groups, global_overall_scope, top_level_report_paths
        )

        # grouped flow may skip top-level scan; fail here if no grouped reports matched
        if len(report_files_coverage) == 0:
            logger.error("No input JaCoCo xml file found. No comment will be generated.")
            self.violations.append("No input JaCoCo xml file found.")
            self._mark_operational_failure()
            return

        skip_unchanged = ActionInputs.get_skip_unchanged()
        evaluate_unchanged = ActionInputs.get_evaluate_unchanged()
        fail_unchanged_enabled = FailOnThresholdEnum.FAIL_UNCHANGED in set(ActionInputs.get_fail_on_threshold())
        evaluate_filtered_unchanged = evaluate_unchanged or fail_unchanged_enabled

        report_files_coverage, filtered_unchanged_reports = self._split_unchanged_reports(
            report_files_coverage, skip_unchanged, evaluate_filtered_unchanged
        )
        if skip_unchanged and not report_files_coverage:
            self._handle_all_reports_filtered(
                gh,
                pr_number,
                parser,
                report_groups,
                filtered_unchanged_reports,
                evaluate_unchanged,
                fail_unchanged_enabled,
            )
            return

        evaluator_for_results, bs_evaluator = self._evaluate_coverage(
            parser,
            report_groups,
            report_files_coverage,
            filtered_unchanged_reports,
            evaluate_unchanged,
            fail_unchanged_enabled,
        )

        # generate the comment(s)
        logger.info("Generating PR comment(s).")
        # Always skip display of filtered unchanged reports when skip_unchanged is enabled,
        # regardless of evaluate_filtered_unchanged setting. These reports are included in
        # overall coverage but should not appear as rows in the comment.
        skip_report_names: frozenset[str] = (
            frozenset(r.path for r in filtered_unchanged_reports)
            if skip_unchanged and filtered_unchanged_reports
            else frozenset()
        )
        generator = PRCommentGenerator(
            gh,
            evaluator_for_results,
            bs_evaluator,
            pr_number,
            skip_report_names,
            ungrouped_reports,
            baseline_unverified=self.baseline_verified is False,
        )
        self._report_generator_result(generator)

    @staticmethod
    def _report_generator_result(generator: PRCommentGenerator) -> None:
        """Generate the report, then print its warnings: a job summary not written, or a comment that may be stale."""
        comment_ok = generator.generate()
        if generator.summary_warning:
            print_action_warning(generator.summary_warning)
        if not comment_ok:
            print_action_warning(PR_COMMENT_MAY_BE_STALE_WARNING)
        elif ActionInputs.get_report_target() != ReportTargetEnum.SUMMARY:
            logger.info("PR comment(s) generated successfully.")

    @staticmethod
    def _split_unchanged_reports(
        report_files_coverage: list[ReportFileCoverage], skip_unchanged: bool, evaluate_filtered_unchanged: bool
    ) -> tuple[list[ReportFileCoverage], list[ReportFileCoverage]]:
        """Split the reports into (kept, filtered unchanged) for skip-unchanged; with it off every report is kept.

        A report with no changed files is filtered and logged once. It never gets a comment row; it still counts for the
        informational overall total, and for fail-unchanged when that is enabled.
        """
        if not skip_unchanged:
            return report_files_coverage, []

        kept: list[ReportFileCoverage] = []
        filtered: list[ReportFileCoverage] = []
        for report in report_files_coverage:
            if report.changed_files_coverage:
                kept.append(report)
                continue
            if evaluate_filtered_unchanged:
                logger.info(
                    "Filtering report '%s' from comment rows and changed-files evaluation: "
                    "no changed files (overall threshold checks may still apply).",
                    report.name,
                )
            else:
                logger.info(
                    "Filtering report '%s' from evaluation and comment rows: no changed files.",
                    report.name,
                )
            filtered.append(report)
        return kept, filtered

    def _handle_all_reports_filtered(
        self,
        gh: GitHub,
        pr_number: int,
        parser: JaCoCoReportParser,
        report_groups: list[ReportGroup],
        filtered_unchanged_reports: list[ReportFileCoverage],
        evaluate_unchanged: bool,
        fail_unchanged_enabled: bool,
    ) -> None:
        """Finish a run in which skip-unchanged filtered out every report, so no comment is generated.

        Without evaluate-unchanged or fail-unchanged the totals pass by default. With either, the filtered reports are
        evaluated for the threshold result only, against the baseline for the delta outputs, and fail-unchanged checks
        all of them. Either way the stale comment is deleted. Without `evaluate_unchanged` the 'no-decrease' gate
        checks only their report rows, as it does for the filtered reports of a mixed run.
        """
        evaluate_filtered_unchanged = evaluate_unchanged or fail_unchanged_enabled
        if not evaluate_filtered_unchanged:
            logger.info("All reports filtered out by skip-unchanged. No comment will be generated.")
            self.total_overall_coverage_passed = True
            self.total_changed_files_coverage_passed = True
            self.evaluated_coverage_reports = "{}"
            self.evaluated_coverage_groups = "{}"
            self._finish_all_filtered_output(gh=gh, pr_number=pr_number)
            return

        logger.info(
            "All reports filtered out by skip-unchanged. Evaluating unchanged reports for threshold result only."
        )
        bs_report_files_coverage = self._collect_baseline_reports(parser, report_groups)
        report_thresholds_default = ActionInputs.get_report_thresholds_default()
        filtered_evaluator = self._new_evaluator(filtered_unchanged_reports, report_groups, report_thresholds_default)
        filtered_evaluator.evaluate()
        bs_evaluator = self._new_baseline_evaluator(bs_report_files_coverage, report_groups, report_thresholds_default)
        # Every evaluated report is an unchanged one here, so all of them count for fail-unchanged.
        fail_unchanged_passed = not fail_unchanged_enabled or all(
            evaluated_report.overall_passed
            for evaluated_report in filtered_evaluator.evaluated_reports_coverage.values()
        )
        self._apply_results(
            filtered_evaluator, bs_evaluator, fail_unchanged_passed, include_aggregate_rows=evaluate_unchanged
        )
        self._finish_all_filtered_output(gh=gh, pr_number=pr_number)

    def _finish_all_filtered_output(self, gh: GitHub, pr_number: int) -> None:
        """Write the all-unchanged message to the job summary, then remove the stale comment as the comment target does.

        The summary target never touches a comment, so it only logs that it does not.
        """
        report_target = ActionInputs.get_report_target()
        if report_target != ReportTargetEnum.COMMENT and ActionInputs.get_comment_level() != CommentLevelEnum.NONE:
            warning = write_job_summary(report_target, all_filtered_summary_body())
            if warning:
                print_action_warning(warning)
        if report_target == ReportTargetEnum.SUMMARY:
            logger.info("%s", SUMMARY_NO_COMMENT_INFO)
            return
        self._delete_stale_comment_if_update_enabled(gh=gh, pr_number=pr_number)

    def _evaluate_coverage(
        self,
        parser: JaCoCoReportParser,
        report_groups: list[ReportGroup],
        report_files_coverage: list[ReportFileCoverage],
        filtered_unchanged_reports: list[ReportFileCoverage],
        evaluate_unchanged: bool,
        fail_unchanged_enabled: bool,
    ) -> tuple[CoverageEvaluator, CoverageEvaluator]:
        """Run the main evaluation, apply its results to `self` and return (results evaluator, baseline evaluator).

        The overall evaluator sees kept and filtered reports. The results evaluator (violations, status, comment rows)
        drops the filtered reports unless `evaluate_unchanged` is set. Fail-unchanged reads only the filtered reports.
        """
        # get baseline files for comparison
        bs_report_files_coverage = self._collect_baseline_reports(parser, report_groups)

        # evaluate the coverage
        logger.info("Evaluating the coverage of the reports.")
        report_thresholds_default = ActionInputs.get_report_thresholds_default()
        # Always include all reports for the informational overall coverage percentage.
        # This must aggregate all reports regardless of changes so the displayed total
        # reflects the whole codebase (see #202).
        overall_evaluator = self._new_evaluator(
            report_files_coverage + filtered_unchanged_reports, report_groups, report_thresholds_default
        )
        overall_evaluator.evaluate()

        # Pass/fail evaluation (violations, reached_threshold_*, per-group/report status)
        # must exclude filtered unchanged reports entirely when evaluate_unchanged is False,
        # per docs/inputs/skip-unchanged.md: they must be "completely excluded from evaluation".
        if evaluate_unchanged or not filtered_unchanged_reports:
            evaluator_for_results: CoverageEvaluator = overall_evaluator
        else:
            evaluator_for_results = self._new_evaluator(report_files_coverage, report_groups, report_thresholds_default)
            evaluator_for_results.evaluate()
            # The comment's summary table still shows the informational total across all
            # reports; only violations/status below are scoped to changed reports.
            evaluator_for_results.total_coverage_overall = overall_evaluator.total_coverage_overall
            evaluator_for_results.total_coverage_overall_passed = overall_evaluator.total_coverage_overall_passed
            evaluator_for_results.total_coverage_changed_files = overall_evaluator.total_coverage_changed_files
            evaluator_for_results.total_coverage_changed_files_passed = (
                overall_evaluator.total_coverage_changed_files_passed
            )

        bs_evaluator = self._new_baseline_evaluator(bs_report_files_coverage, report_groups, report_thresholds_default)

        # Only the filtered unchanged reports count for fail-unchanged, read from the evaluator that saw them.
        fail_unchanged_passed = True
        # The results evaluator leaves the filtered reports out: the 'no-decrease' gate gets them as gated rows with
        # fail-unchanged, else as match evidence only, so a PR that adds a module does not look misconfigured.
        unchanged_gate_reports: list[EvaluatedReportCoverage] = []
        match_evidence_reports: list[EvaluatedReportCoverage] = []
        if filtered_unchanged_reports:
            filtered_unchanged_report_names = {report.path for report in filtered_unchanged_reports}
            filtered_evaluated_reports = [
                evaluated_report
                for report_name, evaluated_report in overall_evaluator.evaluated_reports_coverage.items()
                if report_name in filtered_unchanged_report_names
            ]
            if fail_unchanged_enabled:
                fail_unchanged_passed = all(report.overall_passed for report in filtered_evaluated_reports)
            if evaluator_for_results is not overall_evaluator:
                if fail_unchanged_enabled:
                    unchanged_gate_reports = filtered_evaluated_reports
                else:
                    match_evidence_reports = filtered_evaluated_reports
        self._apply_results(
            evaluator_for_results, bs_evaluator, fail_unchanged_passed, unchanged_gate_reports, match_evidence_reports
        )
        return evaluator_for_results, bs_evaluator

    def _scan_reports(self, report_groups: list[ReportGroup], global_overall_scope: str) -> list[str]:
        """Scan the top-level paths for JaCoCo (xml) reports.

        Grouped runs scan the top-level paths only for global-overall-scope=all, otherwise they return [].
        Ungrouped runs scan `paths` (or DEFAULT_PATHS). The caller exits when the ungrouped scan finds nothing.
        """
        if report_groups:
            logger.info("Report groups configured.")
            if global_overall_scope == GLOBAL_OVERALL_SCOPE_ALL:
                top_level_paths = ActionInputs.get_paths()
                if top_level_paths:
                    logger.info(
                        "global-overall-scope=all: scanning top-level paths to include all reports in global overall."
                    )
                    return self.scan_jacoco_xml_files(
                        paths=top_level_paths, exclude_paths=ActionInputs.get_exclude_paths()
                    )
                logger.info(
                    "global-overall-scope=all but top-level 'paths' is empty; "
                    "global overall will only include grouped reports."
                )
            return []

        logger.info("Scanning for JaCoCo (xml) reports.")
        paths = ActionInputs.get_paths() or [DEFAULT_PATHS]
        return self.scan_jacoco_xml_files(paths=paths, exclude_paths=ActionInputs.get_exclude_paths())

    def _parse_reports(
        self,
        parser: JaCoCoReportParser,
        report_groups: list[ReportGroup],
        global_overall_scope: str,
        top_level_report_paths: list[str],
    ) -> tuple[list[ReportFileCoverage], list[str]]:
        """Scan each report group and parse the reports into coverage objects.

        Returns (report_files_coverage, ungrouped_reports). Grouped reports are tagged with their group name and
        deduplicated by path, the first group wins. With global-overall-scope=all, top-level reports that no group
        matched are parsed without a group name and listed in ungrouped_reports.
        """
        logger.info("Analyzing JaCoCo (xml) reports.")
        report_files_coverage: list[ReportFileCoverage] = []
        seen_report_paths: set[str] = set()
        ungrouped_reports: list[str] = []
        if report_groups:
            # scan each group's paths independently and tag reports with group name
            # deduplicate by report path to avoid double-counting when groups have overlapping globs
            for group in report_groups:
                group_paths = self.scan_jacoco_xml_files(
                    paths=group.paths, exclude_paths=ActionInputs.get_exclude_paths()
                )
                for report_path in group_paths:
                    if report_path not in seen_report_paths:
                        report_files_coverage.append(parser.parse(report_path, group_name=group.name))
                        seen_report_paths.add(report_path)
                    else:
                        logger.info(
                            "Skipping duplicate report '%s' (already assigned to a group).",
                            report_path,
                        )

            # When global-overall-scope=all, include reports found by the top-level scan
            # that were not matched by any group. They contribute to global overall but
            # carry no group_name so they are excluded from per-group threshold evaluation.
            if global_overall_scope == GLOBAL_OVERALL_SCOPE_ALL:
                for report_path in top_level_report_paths:
                    if report_path not in seen_report_paths:
                        logger.warning(
                            "Report '%s' is not assigned to any report group. "
                            "Including in global overall coverage (global-overall-scope=all). "
                            "Set global-overall-scope: groups-only to exclude ungrouped reports.",
                            report_path,
                        )
                        report_files_coverage.append(parser.parse(report_path))
                        seen_report_paths.add(report_path)
                        ungrouped_reports.append(report_path)
        else:
            for report_path in top_level_report_paths:
                report_files_coverage.append(parser.parse(report_path))

        return report_files_coverage, ungrouped_reports

    def _collect_baseline_reports(
        self, parser: JaCoCoReportParser, report_groups: list[ReportGroup]
    ) -> list[ReportFileCoverage]:
        """Scan and parse the baseline reports, per group when report groups are configured.

        A group omitting baseline-paths inherits the global ones. Ambiguous inheritance (several such groups) skips
        them. An explicit empty baseline-paths disables the baseline for that group.
        """
        logger.info("Scanning for JaCoCo (xml) baseline reports.")
        if report_groups:
            return self._collect_group_baseline_reports(parser, report_groups)

        bs_report_files_coverage: list[ReportFileCoverage] = []
        baseline_paths = ActionInputs.get_baseline_paths()
        if baseline_paths:
            baseline_report_paths_to_analyse = self.scan_jacoco_xml_files(paths=baseline_paths, exclude_paths=[])
            if len(baseline_report_paths_to_analyse) == 0:
                logger.warning("No baseline JaCoCo xml file found. No difference will be calculated.")
            else:
                logger.info("Analyzing baseline JaCoCo (xml) reports.")
                for report_path in baseline_report_paths_to_analyse:
                    bs_report_files_coverage.append(parser.parse(report_path))

        return bs_report_files_coverage

    def _collect_group_baseline_reports(
        self, parser: JaCoCoReportParser, report_groups: list[ReportGroup]
    ) -> list[ReportFileCoverage]:
        """Scan and parse the baseline reports of each report group, tagging each with its group name."""
        bs_report_files_coverage: list[ReportFileCoverage] = []
        global_baseline_paths = ActionInputs.get_baseline_paths()
        baseline_scan_cache: dict[tuple[str, ...], list[str]] = {}
        seen_baseline_report_paths: set[str] = set()
        groups_inheriting_global = [group for group in report_groups if not group.baseline_paths_configured]
        ambiguous_global_inheritance = bool(global_baseline_paths) and len(groups_inheriting_global) > 1
        ambiguous_group_names = {group.name for group in groups_inheriting_global}

        if ambiguous_global_inheritance:
            logger.warning(
                "Ambiguous baseline configuration: multiple report groups omit 'baseline-paths' while global "
                "'baseline-paths' is set. Define explicit 'baseline-paths' per group to enable grouped baseline "
                "diffs for those groups."
            )

        for group in report_groups:
            if ambiguous_global_inheritance and group.name in ambiguous_group_names:
                logger.info(
                    "Skipping baseline scan for group '%s' due to ambiguous global baseline inheritance.",
                    group.name,
                )
                continue

            # Inherit global baseline paths only when group-level baseline-paths is omitted (None).
            # Explicit [] means baseline is intentionally disabled for this group.
            group_baseline_paths = group.baseline_paths if group.baseline_paths_configured else global_baseline_paths
            if not group_baseline_paths:
                continue

            baseline_paths_key = tuple(group_baseline_paths)
            if baseline_paths_key not in baseline_scan_cache:
                baseline_scan_cache[baseline_paths_key] = self.scan_jacoco_xml_files(
                    paths=group_baseline_paths,
                    exclude_paths=[],
                )

            group_baseline_report_paths = baseline_scan_cache[baseline_paths_key]
            if len(group_baseline_report_paths) == 0:
                logger.warning(
                    "No baseline JaCoCo xml file found for group '%s'. No difference will be calculated.",
                    group.name,
                )
            else:
                logger.info("Analyzing baseline JaCoCo (xml) reports for group '%s'.", group.name)
                for report_path in group_baseline_report_paths:
                    if report_path in seen_baseline_report_paths:
                        logger.info(
                            "Skipping duplicate baseline report '%s' (already assigned to a group).",
                            report_path,
                        )
                        continue
                    bs_report_files_coverage.append(parser.parse(report_path, group_name=group.name))
                    seen_baseline_report_paths.add(report_path)

        return bs_report_files_coverage

    def scan_jacoco_xml_files(self, paths: list[str], exclude_paths: list[str]) -> list[str]:
        # get files jacoco xml files for analysis
        paths_to_analyse: list[str] = JaCoCoReportInputScanner(paths=paths, exclude_paths=exclude_paths).scan()
        logger.info("Found %s JaCoCo reports.", len(paths_to_analyse))
        return paths_to_analyse

    @staticmethod
    def _new_evaluator(
        reports: list[ReportFileCoverage],
        report_groups: list[ReportGroup],
        report_thresholds_default: tuple[float, float, float],
    ) -> CoverageEvaluator:
        """Build a CoverageEvaluator over `reports` with the global thresholds and the given groups and defaults.

        The caller reads `report_thresholds_default` once per run: a two-part value logs a warning on every read.
        """
        return CoverageEvaluator(
            report_files_coverage=reports,
            global_min_coverage_overall=ActionInputs.get_global_overall_threshold(),
            global_min_coverage_changed_files=ActionInputs.get_global_changed_files_average_threshold(),
            report_groups=report_groups,
            report_thresholds_default=report_thresholds_default,
        )

    @staticmethod
    def _new_baseline_evaluator(
        bs_reports: list[ReportFileCoverage],
        report_groups: list[ReportGroup],
        report_thresholds_default: tuple[float, float, float],
    ) -> CoverageEvaluator:
        """Build the baseline evaluator, evaluated only when baseline reports were found (else it holds no data)."""
        bs_evaluator = JaCoCoReport._new_evaluator(bs_reports, report_groups, report_thresholds_default)
        if bs_reports:
            bs_evaluator.evaluate()
        return bs_evaluator

    def _apply_results(
        self,
        evaluator: CoverageEvaluator,
        bs_evaluator: Optional[CoverageEvaluator],
        fail_unchanged_passed: bool,
        unchanged_reports: Collection[EvaluatedReportCoverage] = (),
        match_evidence: Collection[EvaluatedReportCoverage] = (),
        include_aggregate_rows: bool = True,
    ) -> None:
        """Copy an evaluated evaluator's totals, Δ, report/group JSON, violations and threshold flags into `self`.

        The Δ comes from the same `BaselineComparison` the generator renders, so outputs and comment agree. The caller
        computes `fail_unchanged_passed`: the all-unchanged path and the main path derive it differently. The
        'no-decrease' gate also checks `unchanged_reports`, rows the evaluator leaves out, and takes `match_evidence`
        as matches only; neither adds outputs. `include_aggregate_rows` false gates report rows only.
        """
        self.total_overall_coverage = evaluator.total_coverage_overall
        self.total_overall_coverage_passed = evaluator.total_coverage_overall_passed
        self.total_changed_files_coverage = evaluator.total_coverage_changed_files
        self.total_changed_files_coverage_passed = evaluator.total_coverage_changed_files_passed

        baseline = BaselineComparison(evaluator, bs_evaluator)
        self.total_coverage_delta = baseline.global_delta()

        reports: dict[str, dict] = {}
        for key, report in evaluator.evaluated_reports_coverage.items():
            reports[key] = report.to_dict()
            report_delta = baseline.report_delta(report)
            if report_delta is not None:
                reports[key]["delta"] = report_delta.to_dict()
        groups: dict[str, dict] = {}
        for key, group in evaluator.evaluated_groups_coverage.items():
            groups[key] = group.to_dict()
            group_delta = baseline.group_delta(group)
            if group_delta is not None:
                groups[key]["delta"] = group_delta.to_dict()
        self.evaluated_coverage_reports = json.dumps(reports, indent=4)
        self.evaluated_coverage_groups = json.dumps(groups, indent=4)

        self.violations = evaluator.violations
        self.reached_threshold_overall = evaluator.reached_threshold_overall
        self.reached_threshold_changed_files_average = evaluator.reached_threshold_changed_files_average
        self.reached_threshold_per_change_file = evaluator.reached_threshold_per_change_file
        self.reached_threshold_fail_unchanged = fail_unchanged_passed

        # The gate is opt-in: nothing is computed and no violation is added unless no-decrease is selected.
        self.reached_threshold_no_decrease = True
        if FailOnThresholdEnum.NO_DECREASE in ActionInputs.get_fail_on_threshold():
            if self.baseline_verified is False and baseline.has_baseline_data():
                logger.info("'no-decrease' skipped: the baseline could not be verified against 'baseline-sha'.")
            else:
                gate_violations = baseline.no_decrease_violations(
                    ActionInputs.get_max_decrease(), unchanged_reports, match_evidence, include_aggregate_rows
                )
                self.violations = evaluator.violations + gate_violations
                self.reached_threshold_no_decrease = not gate_violations

    def _verify_baseline(self) -> None:
        """Check the baseline metadata against baseline-sha, once per run. A mismatch is a warning, not a failure."""
        expected_sha = ActionInputs.get_baseline_sha()
        metadata_path = ActionInputs.get_baseline_metadata_path()
        if not expected_sha and not metadata_path:
            return
        reason = unverified_baseline_reason(expected_sha, metadata_path)
        if reason is None:
            self.baseline_verified = True
            logger.info("Baseline verified: its metadata names the commit in 'baseline-sha'.")
            return
        self.baseline_verified = False
        print_action_warning(reason)

    def _delete_stale_comment_if_update_enabled(self, gh: GitHub, pr_number: int) -> None:
        """Delete the previous JaCoCo PR comment when update-comment is enabled."""
        if not ActionInputs.get_update_comment():
            return

        title = f"**{ActionInputs.get_title()}**"
        comments = gh.get_comments(pr_number)
        if comments is None:
            logger.error("Could not read PR comments; skipping stale comment deletion.")
            print_action_warning(PR_COMMENT_MAY_BE_STALE_WARNING)
            return
        for comment in comments:
            if comment["body"].startswith(title):
                if gh.delete_comment(comment["id"]):
                    logger.info("Deleted stale comment from previous run.")
                else:
                    print_action_warning(PR_COMMENT_MAY_BE_STALE_WARNING)
                break

    def _mark_operational_failure(self) -> None:
        """Mark operational failure so action fails regardless of selected threshold list."""
        self.has_operational_failure = True
        self.reached_threshold_overall = False
        self.reached_threshold_changed_files_average = False
        self.reached_threshold_per_change_file = False
        self.reached_threshold_fail_unchanged = False
        self.reached_threshold_no_decrease = False
