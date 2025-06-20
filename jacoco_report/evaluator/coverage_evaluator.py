"""
A module evaluating the coverage of the reports.
"""

import logging

from typing_extensions import Optional

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.model.counter import Counter
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.model.module import Module

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods, too-many-instance-attributes
class CoverageEvaluator:
    """
    A class evaluating the coverage of the reports.
    The target is to evaluate coverage percentages of overall coverage and changed files coverage and
    to check if they pass the thresholds.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        report_files_coverage: list[ReportFileCoverage],
        global_min_coverage_overall: float,
        global_min_coverage_changed_files: float,
        global_min_coverage_changed_per_file: float,
        modules: Optional[dict[str, Module]] = None,
    ):
        # input data stats
        self._report_files_coverage: list[ReportFileCoverage] = report_files_coverage

        # thresholds
        self._global_min_coverage_overall: float = global_min_coverage_overall
        self._global_min_coverage_changed_files: float = global_min_coverage_changed_files
        self._global_min_coverage_changed_per_file = global_min_coverage_changed_per_file
        self._modules: dict[str, Module] = modules if modules is not None else {}

        # *** output data for the comment(s) ***
        # global data
        self.total_coverage_overall: float = 0.0
        self.total_coverage_overall_passed: bool = False
        self.total_coverage_changed_files: float = 0.0
        self.total_coverage_changed_files_passed: bool = False

        # evaluated module data
        self.evaluated_modules_coverage: dict[str, EvaluatedReportCoverage] = {}

        # evaluated report files data
        self.evaluated_reports_coverage: dict[str, EvaluatedReportCoverage] = {}

        # violations
        self.violations: list[str] = []
        self.reached_threshold_overall: bool = True
        self.reached_threshold_changed_files_average: bool = True
        self.reached_threshold_per_change_file: bool = True

    # pylint: disable=too-many-locals
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
        is_unknown_module_present = False
        for report in self._report_files_coverage:
            evaluated_coverage_report: EvaluatedReportCoverage = EvaluatedReportCoverage(
                report.name, report.module_name
            )

            # get report's overall values
            mi, co = report.overall_coverage.get_values_by_metric(m)
            evaluated_coverage_report.overall_coverage_reached = report.overall_coverage.get_coverage_by_metric(m)
            evaluated_coverage_report.overall_coverage.append(mi, co)
            global_overall.append(mi, co)

            # get report's changed files values
            for key, changed_file_coverage in report.changed_files_coverage.items():
                changed_file_counter += 1
                mi, co = changed_file_coverage.get_values_by_metric(m)
                global_changed_files.append(mi, co)  # sum all reports
                evaluated_coverage_report.changed_files_coverage_reached[key] = (
                    changed_file_coverage.get_coverage_by_metric(m)
                )
                evaluated_coverage_report.avg_changed_files_coverage.append(mi, co)

            # count reached values from raw weights - changed files
            evaluated_coverage_report.avg_changed_files_coverage_reached = (
                evaluated_coverage_report.avg_changed_files_coverage.coverage()
            )

            # save the evaluated report
            self.evaluated_reports_coverage[report.name] = self._evaluate_report(report, evaluated_coverage_report)

            if report.module_name in "Unknown":
                is_unknown_module_present = True

        # evaluation of all modules (module == group of reports under module root path)
        if ActionInputs.get_modules() != {}:
            modules: list[str] = list(ActionInputs.get_modules().keys())  # type: ignore[union-attr]

            if is_unknown_module_present:
                modules.append("Unknown")

            for module_name in modules:  # type: ignore[union-attr]
                evaluated_coverage_module: EvaluatedReportCoverage = EvaluatedReportCoverage(module_name)

                # get the numbers from all module's reports counters (raw weights)
                for evaluated_report_coverage in self.evaluated_reports_coverage.values():
                    if evaluated_report_coverage.module_name == module_name:
                        evaluated_coverage_module.overall_coverage.append(evaluated_report_coverage.overall_coverage)
                        evaluated_coverage_module.avg_changed_files_coverage.append(
                            evaluated_report_coverage.avg_changed_files_coverage
                        )

                        evaluated_coverage_module.changed_files_passed.update(
                            evaluated_report_coverage.changed_files_passed
                        )
                        evaluated_coverage_module.changed_files_coverage_reached.update(
                            evaluated_report_coverage.changed_files_coverage_reached
                        )

                # count reached values from raw weights
                evaluated_coverage_module.overall_coverage_reached = (
                    evaluated_coverage_module.overall_coverage.coverage()
                )
                evaluated_coverage_module.avg_changed_files_coverage_reached = (
                    evaluated_coverage_module.avg_changed_files_coverage.coverage()
                )

                # save the evaluated module
                self.evaluated_modules_coverage[module_name] = self._evaluate_module(evaluated_coverage_module)

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
        self._review_violations()

    # pylint: disable=too-many-branches, too-many-statements
    def _review_violations(self) -> None:
        """
        Reviews the coverage evaluation results and appends violations to the violations list.
        Global violations are only reported when comment mode is set to SINGLE.
        Module and report-level violations are added based on sensitivity and comment mode settings.
        """
        skip_unchanged_with_none_changed_files = ActionInputs.get_skip_unchanged() and self.changed_files_count() == 0

        # global - usable only for `single` comment-mode
        if not skip_unchanged_with_none_changed_files:
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

        # module violations
        module_violations: list[str] = []
        for module_name, evaluated_coverage_module in self.evaluated_modules_coverage.items():
            if ActionInputs.get_skip_unchanged() and len(evaluated_coverage_module.changed_files_coverage_reached) == 0:
                continue

            if not evaluated_coverage_module.overall_passed:
                module_violations.append(
                    f"Module '{module_name}' overall coverage {evaluated_coverage_module.overall_coverage_reached} "
                    f"is below the threshold {evaluated_coverage_module.overall_coverage_threshold}."
                )
                self.reached_threshold_overall = False
            if not evaluated_coverage_module.avg_changed_files_passed:
                module_violations.append(
                    f"Module '{module_name}' changed files coverage "
                    f"{evaluated_coverage_module.avg_changed_files_coverage_reached} is below the threshold "
                    f"{evaluated_coverage_module.changed_files_threshold}."
                )
                self.reached_threshold_changed_files_average = False

        report_violations: list[str] = []
        changed_files_violations: list[str] = []

        for report_path, evaluated_coverage_report in self.evaluated_reports_coverage.items():
            if ActionInputs.get_skip_unchanged() and len(evaluated_coverage_report.changed_files_coverage_reached) == 0:
                continue

            if not evaluated_coverage_report.overall_passed:
                report_violations.append(
                    f"Report '{report_path}' overall coverage {evaluated_coverage_report.overall_coverage_reached} "
                    f"is below the threshold {evaluated_coverage_report.overall_coverage_threshold}."
                )
                self.reached_threshold_overall = False
            if not evaluated_coverage_report.avg_changed_files_passed:
                report_violations.append(
                    f"Report '{report_path}' changed files coverage "
                    f"{evaluated_coverage_report.avg_changed_files_coverage_reached} is below the threshold "
                    f"{evaluated_coverage_report.changed_files_threshold}."
                )
                self.reached_threshold_changed_files_average = False
            for key, passed in evaluated_coverage_report.changed_files_passed.items():
                if not passed:
                    changed_files_violations.append(
                        f"Report '{report_path}' changed file '{key}' coverage "
                        f"{evaluated_coverage_report.changed_files_coverage_reached[key]} is below the threshold "
                        f"{evaluated_coverage_report.per_changed_file_threshold}."
                    )
                    self.reached_threshold_per_change_file = False

        # Add all violations to the list depending on the sensitivity and comment mode
        self.violations.extend(report_violations)
        self.violations.extend(changed_files_violations)

    def _evaluate_module(self, evaluated_coverage: EvaluatedReportCoverage) -> EvaluatedReportCoverage:
        """
        Evaluates the coverage of the one module.
        Evaluation uses modules thresholds if defined, otherwise global thresholds.

        Parameters:
            evaluated_coverage (EvaluatedReportCoverage): The evaluated coverage of the module

        Returns:
            EvaluatedReportCoverage: The evaluated coverage of the module
        """
        # get the thresholds for the module
        overall_threshold, changed_files_threshold, changed_per_file_threshold = self._set_thresholds(
            evaluated_coverage.name
        )
        evaluated_coverage.overall_coverage_threshold = overall_threshold
        evaluated_coverage.changed_files_threshold = changed_files_threshold
        evaluated_coverage.per_changed_file_threshold = changed_per_file_threshold

        if evaluated_coverage.overall_coverage.covered == 0 and evaluated_coverage.overall_coverage.missed == 0:
            evaluated_coverage.overall_coverage_reached = 0.0
            evaluated_coverage.overall_passed = True
        else:
            evaluated_coverage.overall_passed = evaluated_coverage.overall_coverage_reached >= overall_threshold

        if (
            evaluated_coverage.avg_changed_files_coverage.covered == 0
            and evaluated_coverage.avg_changed_files_coverage.missed == 0
        ):
            evaluated_coverage.avg_changed_files_coverage_reached = 0.0
            evaluated_coverage.avg_changed_files_passed = True
        else:
            evaluated_coverage.avg_changed_files_passed = (
                evaluated_coverage.avg_changed_files_coverage_reached >= changed_files_threshold
            )

        return evaluated_coverage

    def _evaluate_report(
        self, report_coverage: ReportFileCoverage, evaluated_coverage_report: EvaluatedReportCoverage
    ) -> EvaluatedReportCoverage:
        """
        Evaluates the coverage of the one report.
        Evaluation uses modules thresholds if defined, otherwise global thresholds.

        Parameters:
            report_coverage (ReportFileCoverage): The coverage of the report
            evaluated_coverage_report (EvaluatedReportCoverage): The evaluated coverage of the report

        Returns:
            EvaluatedReportCoverage: The evaluated coverage of the report
        """
        # get the thresholds for the report
        overall_threshold, changed_files_threshold, changed_per_file_threshold = self._set_thresholds(
            report_coverage.module_name
        )
        evaluated_coverage_report.overall_coverage_threshold = overall_threshold
        evaluated_coverage_report.changed_files_threshold = changed_files_threshold
        evaluated_coverage_report.per_changed_file_threshold = changed_per_file_threshold

        if (
            evaluated_coverage_report.overall_coverage.covered == 0
            and evaluated_coverage_report.overall_coverage.missed == 0
        ):
            evaluated_coverage_report.overall_coverage_reached = 0.0
            evaluated_coverage_report.overall_passed = True
        else:
            evaluated_coverage_report.overall_passed = (
                evaluated_coverage_report.overall_coverage_reached >= overall_threshold
            )

        if (
            evaluated_coverage_report.avg_changed_files_coverage.covered == 0
            and evaluated_coverage_report.avg_changed_files_coverage.missed == 0
        ):
            evaluated_coverage_report.avg_changed_files_coverage_reached = 0.0
            evaluated_coverage_report.avg_changed_files_passed = True
        else:
            evaluated_coverage_report.avg_changed_files_coverage_reached = round(
                sum(evaluated_coverage_report.changed_files_coverage_reached.values())
                / len(evaluated_coverage_report.changed_files_coverage_reached.values()),
                2,
            )

            evaluated_coverage_report.avg_changed_files_passed = (
                evaluated_coverage_report.avg_changed_files_coverage_reached >= changed_files_threshold
            )

            # evaluate the changed files
            for key, changed_file_coverage in report_coverage.changed_files_coverage.items():
                evaluated_coverage_report.changed_files_passed[key] = (
                    changed_file_coverage.get_coverage_by_metric(ActionInputs.get_metric())
                    >= changed_per_file_threshold
                )

        return evaluated_coverage_report

    def _set_thresholds(self, module_name: str) -> tuple[float, float, float]:
        """
        Sets the coverage thresholds for the report.
        """
        if len(self._modules.items()) > 0 and module_name in self._modules.keys():
            overall_threshold = (
                self._modules[module_name].min_coverage_overall
                if self._modules[module_name].min_coverage_overall is not None
                else self._global_min_coverage_overall
            )
            changed_files_threshold = (
                self._modules[module_name].min_coverage_changed_files
                if self._modules[module_name].min_coverage_changed_files is not None
                else self._global_min_coverage_changed_files
            )
            changed_per_file_threshold = (
                self._modules[module_name].min_coverage_per_changed_file
                if self._modules[module_name].min_coverage_per_changed_file is not None
                else self._global_min_coverage_changed_per_file
            )
        else:
            overall_threshold = self._global_min_coverage_overall
            changed_files_threshold = self._global_min_coverage_changed_files
            changed_per_file_threshold = self._global_min_coverage_changed_per_file

        return overall_threshold, changed_files_threshold, changed_per_file_threshold

    def changed_files_count(self) -> int:
        """
        Returns the total number of changed files across all reports.
        """
        return sum(len(report.changed_files_coverage) for report in self._report_files_coverage)
