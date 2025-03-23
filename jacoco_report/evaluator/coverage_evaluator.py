"""
A module evaluating the coverage of the reports.
"""

import logging

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.model.counter import Counter
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.model.module import Module
from jacoco_report.utils.enums import SensitivityEnum, CommentModeEnum

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods, too-many-instance-attributes
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
        modules: dict[str, Module] = None,
    ):
        # input data stats
        self._report_files_coverage: list[ReportFileCoverage] = report_files_coverage

        # thresholds
        self._global_min_coverage_overall: float = global_min_coverage_overall
        self._global_min_coverage_changed_files: float = global_min_coverage_changed_files
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

        # evaluation of all report files (report == input xml file)
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
                mi, co = changed_file_coverage.get_values_by_metric(m)
                global_changed_files.append(mi, co)  # sum all reports
                evaluated_coverage_report.changed_files_coverage_reached[key] = (
                    changed_file_coverage.get_coverage_by_metric(m)
                )
                evaluated_coverage_report.sum_changed_files_coverage.append(mi, co)

            # count reached values from raw weights - changed files
            evaluated_coverage_report.sum_changed_files_coverage_reached = (
                evaluated_coverage_report.sum_changed_files_coverage.coverage()
            )

            # save the evaluated report
            self.evaluated_reports_coverage[report.name] = self._evaluate_report(report, evaluated_coverage_report)

        # evaluation of all modules (module == group of reports under module root path)
        if (
            ActionInputs.get_comment_mode() in (CommentModeEnum.SINGLE, CommentModeEnum.MODULE)
            and ActionInputs.get_modules() != {}
        ):
            for module_name in ActionInputs.get_modules().keys():
                evaluated_coverage_module: EvaluatedReportCoverage = EvaluatedReportCoverage(module_name)

                # get the numbers from all module's reports counters (raw weights)
                for evaluated_report_coverage in self.evaluated_reports_coverage.values():
                    if evaluated_report_coverage.module_name == module_name:
                        evaluated_coverage_module.overall_coverage.append(evaluated_report_coverage.overall_coverage)
                        evaluated_coverage_module.sum_changed_files_coverage.append(
                            evaluated_report_coverage.sum_changed_files_coverage
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
                evaluated_coverage_module.sum_changed_files_coverage_reached = (
                    evaluated_coverage_module.sum_changed_files_coverage.coverage()
                )

                # save the evaluated module
                self.evaluated_modules_coverage[module_name] = self._evaluate_module(evaluated_coverage_module)

        # evaluate the global coverage values
        self.total_coverage_overall = global_overall.coverage()
        self.total_coverage_changed_files = global_changed_files.coverage()
        self.total_coverage_overall_passed = self.total_coverage_overall >= self._global_min_coverage_overall
        self.total_coverage_changed_files_passed = (
            self.total_coverage_changed_files >= self._global_min_coverage_changed_files
        )

        # review for violations
        self._review_violations()

    def _review_violations(self) -> None:
        # global
        if not self.total_coverage_overall_passed:
            self.violations.append(
                f"Global overall coverage {self.total_coverage_overall} is below the threshold "
                f"{self._global_min_coverage_overall}."
            )
        if not self.total_coverage_changed_files_passed:
            self.violations.append(
                f"Global changed files coverage {self.total_coverage_changed_files} is below the threshold "
                f"{self._global_min_coverage_changed_files}."
            )

        # modules
        if ActionInputs.get_sensitivity() == SensitivityEnum.MINIMAL:
            return

        for module_name, evaluated_coverage_module in self.evaluated_modules_coverage.items():
            if not evaluated_coverage_module.overall_passed:
                self.violations.append(
                    f"Module '{module_name}' overall coverage {evaluated_coverage_module.overall_coverage_reached} "
                    f"is below the threshold {evaluated_coverage_module.overall_coverage_threshold}."
                )
            if not evaluated_coverage_module.sum_changed_files_passed:
                self.violations.append(
                    f"Module '{module_name}' changed files coverage "
                    f"{evaluated_coverage_module.sum_changed_files_coverage_reached} is below the threshold "
                    f"{evaluated_coverage_module.changed_files_threshold}."
                )

        # reports
        if ActionInputs.get_sensitivity() != SensitivityEnum.DETAIL:
            return

        for report_path, evaluated_coverage_report in self.evaluated_reports_coverage.items():
            if not evaluated_coverage_report.overall_passed:
                self.violations.append(
                    f"Report '{report_path}' overall coverage {evaluated_coverage_report.overall_coverage_reached} "
                    f"is below the threshold {evaluated_coverage_report.overall_coverage_threshold}."
                )
            if not evaluated_coverage_report.sum_changed_files_passed:
                self.violations.append(
                    f"Report '{report_path}' changed files coverage "
                    f"{evaluated_coverage_report.sum_changed_files_coverage_reached} is below the threshold "
                    f"{evaluated_coverage_report.changed_files_threshold}."
                )
            for key, passed in evaluated_coverage_report.changed_files_passed.items():
                if not passed:
                    self.violations.append(
                        f"Report '{report_path}' changed file '{key}' coverage "
                        f"{evaluated_coverage_report.changed_files_coverage_reached[key]} is below the threshold "
                        f"{evaluated_coverage_report.changed_files_threshold}."
                    )

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
        overall_threshold, changed_files_threshold = self._set_thresholds(evaluated_coverage.name)
        evaluated_coverage.overall_coverage_threshold = overall_threshold
        evaluated_coverage.changed_files_threshold = changed_files_threshold

        if evaluated_coverage.overall_coverage.covered == 0 and evaluated_coverage.overall_coverage.missed == 0:
            evaluated_coverage.overall_coverage_reached = 0.0
            evaluated_coverage.overall_passed = True
        else:
            evaluated_coverage.overall_passed = evaluated_coverage.overall_coverage_reached >= overall_threshold

        if (
            evaluated_coverage.sum_changed_files_coverage.covered == 0
            and evaluated_coverage.sum_changed_files_coverage.missed == 0
        ):
            evaluated_coverage.sum_changed_files_coverage_reached = 0.0
            evaluated_coverage.sum_changed_files_passed = True
        else:
            evaluated_coverage.sum_changed_files_passed = (
                evaluated_coverage.sum_changed_files_coverage_reached >= changed_files_threshold
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
        overall_threshold, changed_files_threshold = self._set_thresholds(report_coverage.module_name)
        evaluated_coverage_report.overall_coverage_threshold = overall_threshold
        evaluated_coverage_report.changed_files_threshold = changed_files_threshold

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
            evaluated_coverage_report.sum_changed_files_coverage.covered == 0
            and evaluated_coverage_report.sum_changed_files_coverage.missed == 0
        ):
            evaluated_coverage_report.sum_changed_files_coverage_reached = 0.0
            evaluated_coverage_report.sum_changed_files_passed = True
        else:
            evaluated_coverage_report.sum_changed_files_coverage_reached = sum(
                evaluated_coverage_report.changed_files_coverage_reached.values()
            )
            evaluated_coverage_report.sum_changed_files_passed = (
                evaluated_coverage_report.sum_changed_files_coverage_reached >= changed_files_threshold
            )

            # evaluate the changed files
            for key, changed_file_coverage in report_coverage.changed_files_coverage.items():
                evaluated_coverage_report.changed_files_passed[key] = (
                    changed_file_coverage.get_coverage_by_metric(ActionInputs.get_metric()) >= changed_files_threshold
                )

        return evaluated_coverage_report

    def _set_thresholds(self, module_name: str) -> (float, float):
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
        else:
            overall_threshold = self._global_min_coverage_overall
            changed_files_threshold = self._global_min_coverage_changed_files

        return overall_threshold, changed_files_threshold
