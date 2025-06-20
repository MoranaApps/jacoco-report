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
from jacoco_report.utils.enums import CommentLevelEnum
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
        changed_modules: Optional[set[str]] = None,
    ):
        self.gh: GitHub = gh
        self.evaluator: CoverageEvaluator = evaluator
        self.bs_evaluator: CoverageEvaluator = bs_evaluator
        self.pr_number: int = pr_number
        self.github_repository: str = ActionInputs.get_repository()
        self.changed_modules: set[str] = changed_modules or set()

    def generate(self):
        """
        The method that generates the comment for a single generator.
        """
        title, pr_body = self._get_comment_content()

        # Get all comments on the pull request
        comments = self.gh.get_comments(self.pr_number)

        # Check for existing comment with the same title
        existing_comment = None
        for comment in comments:
            if len(title) > 0 and comment["body"].startswith(title):  # Detects if it starts with the title
                existing_comment = comment
                break

        if existing_comment and ActionInputs.get_update_comment() and self.evaluator.changed_files_count() > 0:
            # Update the existing comment
            self.gh.update_comment(existing_comment["id"], pr_body)
        elif existing_comment and ActionInputs.get_update_comment() and self.evaluator.changed_files_count() == 0:
            # Delete the existing comment
            self.gh.delete_comment(existing_comment["id"])
        else:
            if ActionInputs.get_skip_unchanged() and self.evaluator.changed_files_count() == 0:
                logger.info("No changed files in PR. Skipping comment generation.")
                return

            # create a comment on pull request
            self.gh.add_comment(self.pr_number, pr_body)

    def _get_comment_content(self) -> tuple[str, str]:
        title = body = f"**{ActionInputs.get_title()}**"

        p = ActionInputs.get_pass_symbol()
        f = ActionInputs.get_fail_symbol()

        body += f"\n\n{self._get_basic_table_for_all(p, f)}"

        if ActionInputs.get_comment_level() == CommentLevelEnum.FULL:
            reports_table = self._get_reports_table(p, f)
            if reports_table != "":
                body += f"\n\n{reports_table}"

            body += f"\n\n{self._get_changed_files_table(p, f)}"

        return title, body

    def _get_basic_table_for_all(self, p: str, f: str) -> str:
        # pylint: disable=duplicate-code
        if not ActionInputs.get_baseline_paths():
            return self._get_basic_table(
                p,
                f,
                ActionInputs.get_metric(),
                self.evaluator.total_coverage_overall,
                self.evaluator.total_coverage_overall_passed,
                ActionInputs.get_global_overall_threshold(),
                self.evaluator.total_coverage_changed_files,
                self.evaluator.total_coverage_changed_files_passed,
                ActionInputs.get_global_changed_files_average_threshold(),
            )

        return self._get_basic_table_with_baseline(
            p,
            f,
            ActionInputs.get_metric(),
            self.evaluator.total_coverage_overall,
            self.evaluator.total_coverage_overall_passed,
            ActionInputs.get_global_overall_threshold(),
            self.evaluator.total_coverage_changed_files,
            self.evaluator.total_coverage_changed_files_passed,
            ActionInputs.get_global_changed_files_average_threshold(),
            self.bs_evaluator.total_coverage_overall,
            self.bs_evaluator.total_coverage_changed_files,
        )

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
                "+" if diff_o > 0.001 else "",
                round(diff_o, 2),
                p if total_overall_passed else f,
                total_changed_files_reached,
                min_changed_files,
                "+" if diff_ch > 0.001 else "",
                round(diff_ch, 2),
                p if total_changed_files_passed else f,
            )
        )

    def _get_reports_table(self, p: str, f: str) -> str:
        if not ActionInputs.get_baseline_paths():
            return self._generate_reports_table_without_baseline(p, f)

        return self._generate_reports_table_with_baseline(p, f)

    # pylint: disable=unused-argument
    def _generate_reports_table__skip(self, evaluated_report: EvaluatedReportCoverage, **kwargs) -> bool:
        if (
            ActionInputs.get_skip_unchanged()
            and evaluated_report.name not in self.changed_modules
            and len(evaluated_report.changed_files_coverage_reached) == 0
        ):
            return True
        return False

    def _generate_reports_table_without_baseline(self, p: str, f: str, **kwargs) -> str:
        s = dedent(
            """
            | Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
            |--------|----------|-----------|--------|
        """
        ).strip()

        provided_reports = 0
        keys: list[str] = sorted(list(self.evaluator.evaluated_reports_coverage.keys()))
        for key in keys:
            evaluated_report = self.evaluator.evaluated_reports_coverage[key]
            if self._generate_reports_table__skip(evaluated_report, **kwargs):
                continue

            provided_reports += 1
            o_thres = ActionInputs.get_global_overall_threshold()
            ch_thres = ActionInputs.get_global_changed_files_average_threshold()

            if len(ActionInputs.get_modules()) > 0 and len(ActionInputs.get_modules_thresholds()) > 0:
                o_thres = evaluated_report.overall_coverage_threshold
                ch_thres = evaluated_report.changed_files_threshold

            # pylint: disable=C0209
            s += "\n| `{}` | {}% / {}% | {}% / {}% | {}/{} |".format(
                evaluated_report.name,
                evaluated_report.overall_coverage_reached,
                evaluated_report.avg_changed_files_coverage_reached,
                o_thres,
                ch_thres,
                p if evaluated_report.overall_passed else f,
                p if evaluated_report.avg_changed_files_passed else f,
            )

        if provided_reports == 0:
            s += "\n\nNo changed file in reports."

        return s

    def _generate_reports_table_with_baseline(self, p: str, f: str, **kwargs) -> str:
        s = dedent(
            """
            | Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
            |--------|----------|-----------|------------|--------|
        """
        ).strip()

        provided_reports = 0
        keys: list[str] = sorted(list(self.evaluator.evaluated_reports_coverage.keys()))
        for key in keys:
            evaluated_report = self.evaluator.evaluated_reports_coverage[key]

            if self._generate_reports_table__skip(evaluated_report, **kwargs):
                continue

            provided_reports += 1
            diff_o, diff_ch = self._calculate_baseline_report_diffs(evaluated_report)

            o_thres = ActionInputs.get_global_overall_threshold()
            ch_thres = ActionInputs.get_global_changed_files_average_threshold()

            if len(ActionInputs.get_modules()) > 0 and len(ActionInputs.get_modules_thresholds()) > 0:
                o_thres = evaluated_report.overall_coverage_threshold
                ch_thres = evaluated_report.changed_files_threshold

            # pylint: disable=C0209
            s += "\n| `{}` | {}% / {}% | {}% / {}% | {}{}% / {}{}% | {}/{} |".format(
                evaluated_report.name,
                evaluated_report.overall_coverage_reached,
                evaluated_report.avg_changed_files_coverage_reached,
                o_thres,
                ch_thres,
                "+" if diff_o > 0.001 else "",
                round(diff_o, 2),
                "+" if diff_ch > 0.001 else "",
                round(diff_ch, 2),
                p if evaluated_report.overall_passed else f,
                p if evaluated_report.avg_changed_files_passed else f,
            )

        if provided_reports == 0:
            s += "\n\nNo changed file in reports."

        return s

    # pylint: disable=unused-argument
    def _generate_modules_table__skip(self, evaluated_report: EvaluatedReportCoverage, **kwargs) -> bool:
        if (
            ActionInputs.get_skip_unchanged()
            and evaluated_report.name not in self.changed_modules
            and len(evaluated_report.changed_files_coverage_reached) == 0
        ):
            return True
        return False

    def _calculate_baseline_module_diffs(self, evaluated_coverage: EvaluatedReportCoverage) -> tuple[float, float]:
        if evaluated_coverage.name not in self.bs_evaluator.evaluated_modules_coverage.keys():
            return 0.0, 0.0

        diff_o = (
            evaluated_coverage.overall_coverage_reached
            - self.bs_evaluator.evaluated_modules_coverage[evaluated_coverage.name].overall_coverage_reached
        )
        diff_ch = (
            evaluated_coverage.avg_changed_files_coverage_reached
            - self.bs_evaluator.evaluated_modules_coverage[evaluated_coverage.name].avg_changed_files_coverage_reached
        )

        return diff_o, diff_ch

    def _calculate_baseline_report_diffs(self, evaluated_coverage: EvaluatedReportCoverage) -> tuple[float, float]:
        if evaluated_coverage.name not in self.bs_evaluator.evaluated_reports_coverage.keys():
            return 0.0, 0.0

        diff_o = (
            evaluated_coverage.overall_coverage_reached
            - self.bs_evaluator.evaluated_reports_coverage[evaluated_coverage.name].overall_coverage_reached
        )
        diff_ch = (
            evaluated_coverage.avg_changed_files_coverage_reached
            - self.bs_evaluator.evaluated_reports_coverage[evaluated_coverage.name].avg_changed_files_coverage_reached
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
                    evaluated_reports_coverage[ecr_key].per_changed_file_threshold,
                    (p if evaluated_reports_coverage[ecr_key].changed_files_passed[file_key] else f),
                )
                lines.append(line)

        if len(lines) > 0:
            lines.sort()
            s += "".join(lines)
        else:
            s += "\n\nNo changed file in reports."

        return s

    def _get_changed_files_table(self, p, f) -> str:
        if len(self.evaluator.evaluated_reports_coverage.keys()) == 0:
            return "\nNo changed file in reports."

        if not ActionInputs.get_baseline_paths():
            return self._generate_changed_files_table_without_baseline(p, f)

        return self._generate_changed_files_table_with_baseline(p, f)

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
                    evaluated_reports_coverage[ecr_key].per_changed_file_threshold,
                    "+" if diff > 0.001 else "",
                    round(diff, 2),
                    (p if evaluated_reports_coverage[ecr_key].changed_files_passed[file_key] else f),
                )
                lines.append(line)

        if len(lines) > 0:
            lines.sort()
            s += "".join(lines)
        else:
            s += "\n\nNo changed file in reports."

        return s
