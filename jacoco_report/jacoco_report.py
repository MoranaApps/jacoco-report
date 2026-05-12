"""
A module for generating the JaCoCo report.
"""

import json
import logging

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.generator.pr_comment_generator import PRCommentGenerator
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.model.report_group import ReportGroup
from jacoco_report.parser.jacoco_report_parser import JaCoCoReportParser
from jacoco_report.scanner.jacoco_report_input_scanner import JaCoCoReportInputScanner
from jacoco_report.utils.github import GitHub

logger = logging.getLogger(__name__)


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

        self.evaluated_coverage_reports: str = ""
        self.evaluated_coverage_groups: str = ""
        self.violations: list[str] = []

        self.reached_threshold_overall = True
        self.reached_threshold_changed_files_average = True
        self.reached_threshold_per_change_file = True

    def run(self) -> None:
        """
        The main function to run the JaCoCo GitHub Action adding the JaCoCo coverage report to the pull request.
        """
        if ActionInputs.get_event_name() != "pull_request":
            logger.error("Not a pull request event. Ending.")
            self.violations.append("Not a pull request event.")
            return
        logger.info("Event is a pull request.")

        gh = GitHub(ActionInputs.get_token())
        pr_number = ActionInputs.get_pr_number(gh=gh)
        if pr_number is None:
            logger.error("Not a pull request event. Ending run of Jacoco Report.")
            self.violations.append("No pull request number found.")
            return
        logger.info("Pull request number: %s", pr_number)

        # get report groups (if configured)
        report_groups: list[ReportGroup] = ActionInputs.get_report_groups()

        input_report_paths_to_analyse: list[str] = []
        if report_groups:
            logger.info("Report groups configured. Skipping top-level paths scan.")
        else:
            logger.info("Scanning for JaCoCo (xml) reports.")
            input_report_paths_to_analyse = self.scan_jacoco_xml_files(
                paths=ActionInputs.get_paths(), exclude_paths=ActionInputs.get_exclude_paths()
            )

            # skip when no top-level jacoco xml files found
            if len(input_report_paths_to_analyse) == 0:
                logger.error("No input JaCoCo xml file found. No comment will be generated.")
                self.violations.append("No input JaCoCo xml file found.")
                return

        # get changed files in PR
        logger.info("Getting changed files in PR.")
        changed_files_result: list[str] | None = gh.get_pr_changed_files()
        if changed_files_result is None:
            logger.error("Failed to retrieve changed files from GitHub API. Ending run.")
            self.violations.append("Failed to retrieve changed files from GitHub API.")
            self.reached_threshold_overall = False
            self.reached_threshold_changed_files_average = False
            self.reached_threshold_per_change_file = False
            return
        all_changed_files_in_pr: list[str] = changed_files_result

        # analyse received xml report files
        logger.info("Analyzing JaCoCo (xml) reports.")
        report_files_coverage: list[ReportFileCoverage] = []
        parser = JaCoCoReportParser(all_changed_files_in_pr)
        seen_report_paths: set[str] = set()
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
        else:
            for report_path in input_report_paths_to_analyse:
                report_files_coverage.append(parser.parse(report_path))

        # grouped flow may skip top-level scan; fail here if no grouped reports matched
        if len(report_files_coverage) == 0:
            logger.error("No input JaCoCo xml file found. No comment will be generated.")
            self.violations.append("No input JaCoCo xml file found.")
            return

        skip_unchanged = ActionInputs.get_skip_unchanged()
        evaluate_unchanged = ActionInputs.get_evaluate_unchanged()
        filtered_unchanged_reports: list[ReportFileCoverage] = []

        # scan-stage filter: remove reports with no changed files before evaluation
        if skip_unchanged:
            for report in report_files_coverage:
                if not report.changed_files_coverage:
                    if evaluate_unchanged:
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
                    filtered_unchanged_reports.append(report)

            report_files_coverage = [r for r in report_files_coverage if r.changed_files_coverage]
            if not report_files_coverage and not evaluate_unchanged:
                logger.info("All reports filtered out by skip-unchanged. No comment will be generated.")
                self.total_overall_coverage_passed = True
                self.total_changed_files_coverage_passed = True
                self.evaluated_coverage_reports = "{}"
                self.evaluated_coverage_groups = "{}"
                self._delete_stale_comment_if_update_enabled(gh=gh, pr_number=pr_number)
                return
            if not report_files_coverage and evaluate_unchanged:
                logger.info(
                    "All reports filtered out by skip-unchanged. Evaluating unchanged reports for threshold result only."
                )
                report_thresholds_default = ActionInputs.get_report_thresholds_default()
                filtered_evaluator = CoverageEvaluator(
                    report_files_coverage=filtered_unchanged_reports,
                    global_min_coverage_overall=ActionInputs.get_global_overall_threshold(),
                    global_min_coverage_changed_files=ActionInputs.get_global_changed_files_average_threshold(),
                    global_min_coverage_changed_per_file=ActionInputs.get_global_changed_file_threshold(),
                    report_groups=report_groups,
                    report_thresholds_default=report_thresholds_default,
                )
                filtered_evaluator.evaluate()

                self.total_overall_coverage = filtered_evaluator.total_coverage_overall
                self.total_overall_coverage_passed = filtered_evaluator.total_coverage_overall_passed
                self.total_changed_files_coverage = filtered_evaluator.total_coverage_changed_files
                self.total_changed_files_coverage_passed = filtered_evaluator.total_coverage_changed_files_passed

                evaluated_coverage_reports = {
                    k: v.to_dict() for k, v in filtered_evaluator.evaluated_reports_coverage.items()
                }
                evaluated_coverage_groups = {
                    k: v.to_dict() for k, v in filtered_evaluator.evaluated_groups_coverage.items()
                }
                self.evaluated_coverage_reports = json.dumps(evaluated_coverage_reports, indent=4)
                self.evaluated_coverage_groups = json.dumps(evaluated_coverage_groups, indent=4)
                self.violations = filtered_evaluator.violations
                self.reached_threshold_overall = filtered_evaluator.reached_threshold_overall
                self.reached_threshold_changed_files_average = (
                    filtered_evaluator.reached_threshold_changed_files_average
                )
                self.reached_threshold_per_change_file = filtered_evaluator.reached_threshold_per_change_file

                self._delete_stale_comment_if_update_enabled(gh=gh, pr_number=pr_number)
                return

        # get baseline files for comparison
        logger.info("Scanning for JaCoCo (xml) baseline reports.")
        bs_report_files_coverage: list[ReportFileCoverage] = []
        if report_groups:
            global_baseline_paths = ActionInputs.get_baseline_paths()
            baseline_scan_cache: dict[tuple[str, ...], list[str]] = {}
            seen_baseline_report_paths: set[str] = set()
            groups_inheriting_global = [
                group for group in report_groups if not getattr(group, "baseline_paths_configured", False)
            ]
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
                group_baseline_paths = (
                    group.baseline_paths
                    if getattr(group, "baseline_paths_configured", False)
                    else global_baseline_paths
                )
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
        else:
            baseline_paths = ActionInputs.get_baseline_paths()
            if baseline_paths:
                baseline_report_paths_to_analyse = self.scan_jacoco_xml_files(paths=baseline_paths, exclude_paths=[])
                if len(baseline_report_paths_to_analyse) == 0:
                    logger.warning("No baseline JaCoCo xml file found. No difference will be calculated.")
                else:
                    logger.info("Analyzing baseline JaCoCo (xml) reports.")
                    for report_path in baseline_report_paths_to_analyse:
                        bs_report_files_coverage.append(parser.parse(report_path))

        # evaluate the coverage
        logger.info("Evaluating the coverage of the reports.")
        report_thresholds_default = ActionInputs.get_report_thresholds_default()
        reports_for_evaluation = (
            report_files_coverage + filtered_unchanged_reports
            if skip_unchanged and evaluate_unchanged and filtered_unchanged_reports
            else report_files_coverage
        )
        evaluator_for_results: CoverageEvaluator = CoverageEvaluator(
            report_files_coverage=reports_for_evaluation,
            global_min_coverage_overall=ActionInputs.get_global_overall_threshold(),
            global_min_coverage_changed_files=ActionInputs.get_global_changed_files_average_threshold(),
            global_min_coverage_changed_per_file=ActionInputs.get_global_changed_file_threshold(),
            report_groups=report_groups,
            report_thresholds_default=report_thresholds_default,
        )
        evaluator_for_results.evaluate()

        bs_evaluator: CoverageEvaluator = CoverageEvaluator(
            report_files_coverage=bs_report_files_coverage,
            global_min_coverage_overall=ActionInputs.get_global_overall_threshold(),
            global_min_coverage_changed_files=ActionInputs.get_global_changed_files_average_threshold(),
            global_min_coverage_changed_per_file=ActionInputs.get_global_changed_file_threshold(),
            report_groups=report_groups,
            report_thresholds_default=report_thresholds_default,
        )

        if bs_report_files_coverage:
            bs_evaluator.evaluate()

        self.total_overall_coverage = evaluator_for_results.total_coverage_overall
        self.total_overall_coverage_passed = evaluator_for_results.total_coverage_overall_passed
        self.total_changed_files_coverage = evaluator_for_results.total_coverage_changed_files
        self.total_changed_files_coverage_passed = evaluator_for_results.total_coverage_changed_files_passed

        evaluated_coverage_reports = {
            k: v.to_dict() for k, v in evaluator_for_results.evaluated_reports_coverage.items()
        }
        evaluated_coverage_groups = {k: v.to_dict() for k, v in evaluator_for_results.evaluated_groups_coverage.items()}

        self.evaluated_coverage_reports = json.dumps(evaluated_coverage_reports, indent=4)
        self.evaluated_coverage_groups = json.dumps(evaluated_coverage_groups, indent=4)

        self.violations = evaluator_for_results.violations
        self.reached_threshold_overall = evaluator_for_results.reached_threshold_overall
        self.reached_threshold_changed_files_average = evaluator_for_results.reached_threshold_changed_files_average
        self.reached_threshold_per_change_file = evaluator_for_results.reached_threshold_per_change_file

        # generate the comment(s)
        logger.info("Generating PR comment(s).")
        skip_report_names: frozenset[str] = (
            frozenset(r.name for r in filtered_unchanged_reports)
            if skip_unchanged and evaluate_unchanged and filtered_unchanged_reports
            else frozenset()
        )
        generator = PRCommentGenerator(gh, evaluator_for_results, bs_evaluator, pr_number, skip_report_names)
        generator.generate()
        logger.info("PR comment(s) generated successfully.")

    def scan_jacoco_xml_files(self, paths: list[str], exclude_paths: list[str]) -> list[str]:
        # get files jacoco xml files for analysis
        paths_to_analyse: list[str] = JaCoCoReportInputScanner(paths=paths, exclude_paths=exclude_paths).scan()
        logger.info("Found %s JaCoCo reports.", len(paths_to_analyse))
        return paths_to_analyse

    def _delete_stale_comment_if_update_enabled(self, gh: GitHub, pr_number: int) -> None:
        """Delete the previous JaCoCo PR comment when update-comment is enabled."""
        if not ActionInputs.get_update_comment():
            return

        title = f"**{ActionInputs.get_title()}**"
        for comment in gh.get_comments(pr_number):
            if comment["body"].startswith(title):
                gh.delete_comment(comment["id"])
                logger.info("Deleted stale comment from previous run.")
                break
