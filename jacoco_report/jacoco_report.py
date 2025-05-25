"""
A module for generating the JaCoCo report.
"""

import json
import logging

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.generator.pr_comment_generator_factory import PRCommentGeneratorFactory
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.model.module import Module
from jacoco_report.parser.jacoco_report_parser import JaCoCoReportParser
from jacoco_report.parser.module_parser import ModuleParser
from jacoco_report.scanner.jacoco_report_input_scanner import JaCoCoReportInputScanner
from jacoco_report.utils.github import GitHub

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
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
        self.evaluated_coverage_modules: str = ""
        self.violations: list[str] = []

        self.reached_threshold_overall = True
        self.reached_threshold_changed_files_average = True
        self.reached_threshold_per_change_file = True

    # pylint: disable=too-many-locals, too-many-branches, too-many-statements
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

        logger.info("Scanning for JaCoCo (xml) reports.")
        input_report_paths_to_analyse = self._scan_jacoco_xml_files(
            paths=ActionInputs.get_paths(), exclude_paths=ActionInputs.get_exclude_paths()  # type: ignore[arg-type]
        )

        # skip when not jacoco xml files found
        if len(input_report_paths_to_analyse) == 0:
            logger.warning("No JaCoCo xml file found. No comment will be generated.")
            return

        # get changed files in PR
        logger.info("Getting changed files in PR.")
        all_changed_files_in_pr = gh.get_pr_changed_files()

        # map modules if comment mode is set to MODULE
        logger.info("Mapping modules (if defined).")
        modules: dict[str, Module] = self._get_modules()

        # analyse received xml report files
        logger.info("Analyzing JaCoCo (xml) reports.")
        report_files_coverage: list[ReportFileCoverage] = []
        changed_modules: set[str] = set()
        parser = JaCoCoReportParser(all_changed_files_in_pr, modules)  # type: ignore[arg-type]
        for report_path in input_report_paths_to_analyse:
            report_files_coverage.append(rfc := parser.parse(report_path))

            if ActionInputs.get_skip_unchanged() and rfc.module_name is not None and rfc.changed_files_coverage != {}:
                changed_modules.add(rfc.module_name)  # note module with changed files

        # get baseline files for comparison
        logger.info("Scanning for JaCoCo (xml) baseline reports.")
        baseline_report_paths_to_analyse = self._scan_jacoco_xml_files(
            paths=ActionInputs.get_baseline_paths(), exclude_paths=[]  # type: ignore[arg-type]
        )
        bs_report_files_coverage: list[ReportFileCoverage] = []
        if len(baseline_report_paths_to_analyse) == 0:
            logger.warning("No baseline JaCoCo xml file found. No difference will be calculated.")
        else:
            # analyse received baseline xml report files - limit to the same modules and changed files
            logger.info("Analyzing baseline JaCoCo (xml) reports.")
            for report_path in baseline_report_paths_to_analyse:
                bs_report_files_coverage.append(parser.parse(report_path))

        # evaluate the coverage and module to xml file mapping
        logger.info("Evaluating the coverage of the reports.")
        evaluator: CoverageEvaluator = CoverageEvaluator(
            report_files_coverage=report_files_coverage,
            global_min_coverage_overall=ActionInputs.get_min_coverage_overall(),
            global_min_coverage_changed_files=ActionInputs.get_min_coverage_changed_files(),
            global_min_coverage_changed_per_file=ActionInputs.get_min_coverage_per_changed_file(),
            modules=modules,
        )
        evaluator.evaluate()

        bs_evaluator: CoverageEvaluator = CoverageEvaluator(
            report_files_coverage=bs_report_files_coverage,
            global_min_coverage_overall=ActionInputs.get_min_coverage_overall(),
            global_min_coverage_changed_files=ActionInputs.get_min_coverage_changed_files(),
            global_min_coverage_changed_per_file=ActionInputs.get_min_coverage_per_changed_file(),
            modules=modules,
        )

        if len(ActionInputs.get_baseline_paths()) > 0:
            bs_evaluator.evaluate()

        self.total_overall_coverage = evaluator.total_coverage_overall
        self.total_overall_coverage_passed = evaluator.total_coverage_overall_passed
        self.total_changed_files_coverage = evaluator.total_coverage_changed_files
        self.total_changed_files_coverage_passed = evaluator.total_coverage_changed_files_passed

        evaluated_coverage_reports = {k: v.to_dict() for k, v in evaluator.evaluated_reports_coverage.items()}
        evaluated_coverage_modules = {k: v.to_dict() for k, v in evaluator.evaluated_modules_coverage.items()}

        self.evaluated_coverage_reports = json.dumps(evaluated_coverage_reports, indent=4)
        self.evaluated_coverage_modules = json.dumps(evaluated_coverage_modules, indent=4)

        self.violations = evaluator.violations
        self.reached_threshold_overall = evaluator.reached_threshold_overall
        self.reached_threshold_changed_files_average = evaluator.reached_threshold_changed_files_average
        self.reached_threshold_per_change_file = evaluator.reached_threshold_per_change_file

        # generate the comment(s)
        logger.info("Generating PR comment(s).")
        generator = PRCommentGeneratorFactory.get_generator(
            ActionInputs.get_comment_mode(),
            gh,
            evaluator,
            bs_evaluator,
            pr_number,
            changed_modules,
        )
        generator.generate()

        logger.info("PR comment(s) generated successfully.")

    def _scan_jacoco_xml_files(self, paths: list[str], exclude_paths: list[str]) -> list[str]:
        # get files jacoco xml files for analysis
        paths_to_analyse: list[str] = JaCoCoReportInputScanner(paths=paths, exclude_paths=exclude_paths).scan()
        logger.info("Found %s JaCoCo reports.", len(paths_to_analyse))
        return paths_to_analyse

    def _get_modules(self) -> dict[str, Module]:
        return ModuleParser().parse(
            modules=ActionInputs.get_modules(),  # type: ignore[arg-type]
            modules_thresholds=ActionInputs.get_modules_thresholds(),  # type: ignore[arg-type]
        )
