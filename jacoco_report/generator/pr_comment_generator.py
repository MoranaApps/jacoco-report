"""
A module that contains the PRCommentGenerator class.
"""

import hashlib
import logging
import os
from textwrap import dedent
from typing import Optional

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.utils.github import GitHub

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class PRCommentGenerator:
    """
    A class that represents the PR Comment Generator.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        gh: GitHub,
        evaluator: CoverageEvaluator,
        bs_evaluator: CoverageEvaluator,
        pr_number: int,
        changed_modules: list[str] = None,
    ):
        self.gh: GitHub = gh
        self.evaluator: CoverageEvaluator = evaluator
        self.bs_evaluator: CoverageEvaluator = bs_evaluator
        self.pr_number: int = pr_number
        self.github_repository: str = ActionInputs.get_repository()
        self.changed_modules: list[str] = changed_modules or []

    def generate(self):
        """
        The method that generates the comment.
        """
        raise NotImplementedError("Subclasses should implement this method")

    # Full example of the table
    # | Metric (Instruction) | Coverage | Threshold | Δ Coverage | Status |
    # |----------------------|----------|-----------|------------|--------|
    # | **Overall**          | 85.2%    | 80%       | +1,3%      | ✅      |
    # | **Changed Files**    | 78.4%    | 80%       | 0.3%       | ❌      |

    def _get_basic_table(
        self,
        p: str,
        f: str,
        metric: str,
        total_overall_reached: float,
        total_overall_passed: bool,
        min_overall: float,
        total_changed_files_reached: float,
        total_changed_files_passed: bool,
        min_changed_files: float,
    ) -> str:
        return (
            dedent(
                """
            | Metric ({}) | Coverage | Threshold | Status |
            |----------------------|----------|-----------|--------|
            | **Overall**       | {}% | {}% | {} |
            | **Changed Files** | {}% | {}% | {} |
        """
            )
            .strip()
            .format(
                metric,
                total_overall_reached,
                min_overall,
                p if total_overall_passed else f,
                total_changed_files_reached,
                min_changed_files,
                p if total_changed_files_passed else f,
            )
        )

    def _get_basic_table_with_baseline(
        self,
        p: str,
        f: str,
        metric: str,
        total_overall_reached: float,
        total_overall_passed: bool,
        min_overall: float,
        total_changed_files_reached: float,
        total_changed_files_passed: bool,
        min_changed_files: float,
        bs_total_overall_reached: float,
        bs_total_changed_files_reached: float,
    ) -> str:
        diff_o = total_overall_reached - bs_total_overall_reached
        diff_ch = total_changed_files_reached - bs_total_changed_files_reached

        return (
            dedent(
                """
            | Metric ({}) | Coverage | Threshold | Δ Coverage | Status |
            |-------------------|-----|-----|-----|----|
            | **Overall**       | {}% | {}% | {}{}% | {} |
            | **Changed Files** | {}% | {}% | {}{}% | {} |
        """
            )
            .strip()
            .format(
                metric,
                total_overall_reached,
                min_overall,
                "+" if diff_o > 0 else "",
                round(diff_o, 1),
                p if total_overall_passed else f,
                total_changed_files_reached,
                min_changed_files,
                "+" if diff_ch > 0 else "",
                round(diff_ch, 1),
                p if total_changed_files_passed else f,
            )
        )

    # Full example of the table
    # | Module      | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
    # |-------------|-----------------|------------------|-------------------|---------------|
    # | `module-1`  | 87.5% / 35.2%   | 60% / 80%        | -0.6% / +1.0%     | ✅/✅           |
    # | `module-2`  | 80.0% / 45.6%   | 40% / 82%        | +0.3% / -2.1%     | ✅/✅           |
    # | `module-3`  | 76.3% / 76.4%   | 50% / 76%        | -2.5% / -1.2%     | ❌/✅           |

    def _get_modules_table(self, p: str, f: str) -> str:
        if ActionInputs.get_modules() == {}:
            logger.info("No modules defined. No modules table will be generated.")
            return ""

        if not ActionInputs.get_baseline_paths():
            return self._generate_modules_table_without_baseline(p, f)

        return self._generate_modules_table_with_baseline(p, f)

    def _generate_modules_table_without_baseline(self, p: str, f: str) -> str:
        s = dedent(
            """
            | Module | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
            |--------|-----------------|------------------|---------------|
        """
        ).strip()

        for evaluated_coverage_module in self.evaluator.evaluated_modules_coverage.values():
            if ActionInputs.get_skip_not_changed() and evaluated_coverage_module.name not in self.changed_modules:
                continue

            # pylint: disable=C0209
            s += "\n| `{}` | {}% / {}% | {}% / {}% | {}/{} |".format(
                evaluated_coverage_module.name,
                evaluated_coverage_module.overall_coverage_reached,
                evaluated_coverage_module.sum_changed_files_coverage_reached,
                evaluated_coverage_module.overall_coverage_threshold,
                evaluated_coverage_module.changed_files_threshold,
                p if evaluated_coverage_module.overall_passed else f,
                p if evaluated_coverage_module.sum_changed_files_passed else f,
            )

        return s

    def _generate_modules_table_with_baseline(self, p: str, f: str) -> str:
        s = dedent(
            """
            | Module | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
            |--------|-----------------|------------------|---------------|---------------|
        """
        ).strip()

        for evaluated_coverage_module in self.evaluator.evaluated_modules_coverage.values():
            if ActionInputs.get_skip_not_changed() and evaluated_coverage_module.name not in self.changed_modules:
                continue

            diff_o, diff_ch = self._calculate_module_diff(evaluated_coverage_module)

            # pylint: disable=C0209
            s += "\n| `{}` | {}% / {}% | {}% / {}% | {}{}% / {}{}% | {}/{} |".format(
                evaluated_coverage_module.name,
                evaluated_coverage_module.overall_coverage_reached,
                evaluated_coverage_module.sum_changed_files_coverage_reached,
                evaluated_coverage_module.overall_coverage_threshold,
                evaluated_coverage_module.changed_files_threshold,
                "+" if diff_o > 0 else "",
                round(diff_o, 1),
                "+" if diff_ch > 0 else "",
                round(diff_ch, 1),
                p if evaluated_coverage_module.overall_passed else f,
                p if evaluated_coverage_module.sum_changed_files_passed else f,
            )

        return s

    def _calculate_module_diff(self, evaluated_coverage_module) -> (float, float):
        if evaluated_coverage_module.name not in self.bs_evaluator.evaluated_modules_coverage.keys():
            return 0.0, 0.0

        diff_o = (
            evaluated_coverage_module.overall_coverage_reached
            - self.bs_evaluator.evaluated_modules_coverage[evaluated_coverage_module.name].overall_coverage_reached
        )
        diff_ch = (
            evaluated_coverage_module.sum_changed_files_coverage_reached
            - self.bs_evaluator.evaluated_modules_coverage[
                evaluated_coverage_module.name
            ].sum_changed_files_coverage_reached
        )

        return diff_o, diff_ch

    # Full example of the table
    # | File Path                                      | Coverage | Threshold | Δ Coverage | Status |
    # |------------------------------------------------|----------|-----------|------------|--------|
    # | `src/main/java/com/example/File1.java`         | 90.1%    | 80%       | +0.3%      | ✅      |
    # | `src/main/java/com/example/File2.java`         | 70.5%    | 80%       | -1.0%      | ❌      |
    # | `src/main/java/com/example/File3.java`         | 82.1%    | 80%       | +2.7%      | ✅      |

    def _generate_changed_files_table_without_baseline(
        self, p: str, f: str, evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None
    ) -> str:
        """
        Generate a table with changed files without baseline. The table contains the files from all reports.
        """
        s = dedent(
            """
            | File Path | Coverage | Threshold | Status |
            |-----------|----------|-----------|--------|
        """
        ).strip()

        if evaluated_reports_coverage is None:
            evaluated_reports_coverage = self.evaluator.evaluated_reports_coverage

        lines = []
        for ecr_key in evaluated_reports_coverage.keys():
            for file_key in evaluated_reports_coverage[ecr_key].changed_files_coverage_reached.keys():
                filename = os.path.basename(file_key)
                file_hash = hashlib.sha256(file_key.encode("utf-8")).hexdigest()
                file_as_link_to_diff = (
                    f"https://github.com/{self.github_repository}/pull/{self.pr_number}/files#diff-{file_hash}"
                )

                # pylint: disable=C0209
                line = "\n| {} | {}% | {}% | {} |".format(
                    f"[{filename}]({file_as_link_to_diff})",
                    evaluated_reports_coverage[ecr_key].changed_files_coverage_reached[file_key],
                    evaluated_reports_coverage[ecr_key].changed_files_threshold,
                    (p if evaluated_reports_coverage[ecr_key].changed_files_passed[file_key] else f),
                )
                lines.append(line)

        if len(lines) > 0:
            lines.sort()
            s += "".join(lines)
            return s

        return "No changed file in report."

    def _generate_changed_files_table_with_baseline(
        self, p: str, f: str, evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None
    ) -> str:
        s = dedent(
            """
            | File Path | Coverage | Threshold | Δ Coverage | Status |
            |-----------|----------|-----------|------------|--------|
        """
        ).strip()

        if evaluated_reports_coverage is None:
            evaluated_reports_coverage = self.evaluator.evaluated_reports_coverage

        lines = []
        for ecr_key in evaluated_reports_coverage.keys():
            for file_key in evaluated_reports_coverage[ecr_key].changed_files_coverage_reached.keys():
                filename = os.path.basename(file_key)
                file_hash = hashlib.sha256(file_key.encode("utf-8")).hexdigest()
                file_as_link_to_diff = (
                    f"https://github.com/{self.github_repository}/pull/{self.pr_number}/files#diff-{file_hash}"
                )

                if ecr_key not in self.bs_evaluator.evaluated_reports_coverage.keys():
                    diff = 0.0
                elif (
                    file_key
                    not in self.bs_evaluator.evaluated_reports_coverage[ecr_key].changed_files_coverage_reached.keys()
                ):
                    diff = 0.0
                else:
                    diff = (
                        evaluated_reports_coverage[ecr_key].changed_files_coverage_reached[file_key]
                        - self.bs_evaluator.evaluated_reports_coverage[ecr_key].changed_files_coverage_reached[file_key]
                    )

                # pylint: disable=C0209
                line = "\n| {} | {}% | {}% | {}{}% | {} |".format(
                    f"[{filename}]({file_as_link_to_diff})",
                    evaluated_reports_coverage[ecr_key].changed_files_coverage_reached[file_key],
                    evaluated_reports_coverage[ecr_key].changed_files_threshold,
                    "+" if diff > 0 else "",
                    round(diff, 1),
                    (p if evaluated_reports_coverage[ecr_key].changed_files_passed[file_key] else f),
                )
                lines.append(line)

        if len(lines) > 0:
            lines.sort()
            s += "".join(lines)
            return s

        return "No changed file in report."
