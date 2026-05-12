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


class PRCommentGenerator:
    """
    A class that represents the PR Comment Generator.
    """

    def __init__(
        self,
        gh: GitHub,
        evaluator: CoverageEvaluator,
        bs_evaluator: CoverageEvaluator,
        pr_number: int,
        skip_report_names: frozenset[str] = frozenset(),
    ):
        self.gh: GitHub = gh
        self.evaluator: CoverageEvaluator = evaluator
        self.bs_evaluator: CoverageEvaluator = bs_evaluator
        self.pr_number: int = pr_number
        self.skip_report_names: frozenset[str] = skip_report_names
        self.github_repository: str = ActionInputs.get_repository()

    def generate(self) -> None:
        """
        The method that generates the comment for a single generator.
        """
        comment_level = ActionInputs.get_comment_level()
        update_comment = ActionInputs.get_update_comment()

        # No comment operation is needed in this mode, so skip the API read call entirely.
        if comment_level == CommentLevelEnum.NONE and not update_comment:
            return

        title, pr_body = self._get_comment_content(comment_level)
        # Get all comments on the pull request
        comments = self.gh.get_comments(self.pr_number)

        # Check for existing comment with the same title
        existing_comment = None
        for comment in comments:
            if len(title) > 0 and comment["body"].startswith(title):  # Detects if it starts with the title
                existing_comment = comment
                break

        if comment_level == CommentLevelEnum.NONE:
            if existing_comment and update_comment:
                self.gh.delete_comment(existing_comment["id"])
            return

        if existing_comment and update_comment:
            self.gh.update_comment(existing_comment["id"], pr_body)
        else:
            self.gh.add_comment(self.pr_number, pr_body)

    def _get_comment_content(self, comment_level: str) -> tuple[str, str]:
        """Build the PR comment title and body for the selected comment level."""
        title = body = f"**{ActionInputs.get_title()}**"

        if comment_level == CommentLevelEnum.NONE:
            return title, body

        p = ActionInputs.get_pass_symbol()
        f = ActionInputs.get_fail_symbol()

        body += f"\n\n{self.get_basic_table_for_all(p, f)}"

        if comment_level == CommentLevelEnum.MINIMAL:
            return title, body

        filtered_groups = self.evaluator.evaluated_groups_coverage
        filtered_reports = {
            k: v
            for k, v in self.evaluator.evaluated_reports_coverage.items()
            if k not in self.skip_report_names
        }
        if self.skip_report_names:
            visible_group_names: frozenset[str] = frozenset(
                v.group_name
                for k, v in self.evaluator.evaluated_reports_coverage.items()
                if k not in self.skip_report_names
            )
            filtered_groups = {k: v for k, v in filtered_groups.items() if k in visible_group_names}

        if comment_level != CommentLevelEnum.FULL:
            filtered_groups = self._filter_evaluated_coverage_rows(filtered_groups, comment_level)
            filtered_reports = self._filter_evaluated_coverage_rows(filtered_reports, comment_level)

        detail_sections: list[str] = []

        groups_table = self.get_groups_table(p, f, filtered_groups)
        if groups_table:
            detail_sections.append(groups_table)

        reports_table = self.get_reports_table(p, f, filtered_reports)
        if reports_table:
            detail_sections.append(reports_table)

        changed_files_table = self._get_changed_files_table(p, f, filtered_reports, comment_level)
        if changed_files_table:
            detail_sections.append(changed_files_table)

        if detail_sections:
            body += "\n\n" + "\n\n".join(detail_sections)
        elif comment_level != CommentLevelEnum.FULL:
            body += "\n\nNo rows match the selected comment level."

        return title, body

    def _filter_evaluated_coverage_rows(
        self,
        evaluated_coverages: dict[str, EvaluatedReportCoverage],
        comment_level: str,
    ) -> dict[str, EvaluatedReportCoverage]:
        """Filter group or report rows according to the selected comment level."""
        return {
            key: coverage
            for key, coverage in evaluated_coverages.items()
            if self._should_include_coverage_row(coverage, comment_level)
        }

    def _should_include_coverage_row(self, coverage: EvaluatedReportCoverage, comment_level: str) -> bool:
        """Return whether one evaluated group or report row should be rendered."""
        if comment_level == CommentLevelEnum.FULL:
            return True

        has_changed_files = self._has_changed_files(coverage)
        is_failing = self._is_failing_coverage(coverage)

        if comment_level == CommentLevelEnum.CHANGED:
            return has_changed_files

        if comment_level == CommentLevelEnum.FAILED:
            return is_failing

        if comment_level == CommentLevelEnum.FAILED_OR_CHANGED:
            return has_changed_files or is_failing

        return False

    def _has_changed_files(self, coverage: EvaluatedReportCoverage) -> bool:
        """Return whether a coverage row represents at least one changed file."""
        if coverage.changed_files_coverage_reached:
            return True

        return (coverage.avg_changed_files_coverage.covered + coverage.avg_changed_files_coverage.missed) > 0

    def _is_failing_coverage(self, coverage: EvaluatedReportCoverage) -> bool:
        """Return whether any threshold represented by the coverage row is failing."""
        return (
            not coverage.overall_passed
            or not coverage.avg_changed_files_passed
            or any(not passed for passed in coverage.changed_files_passed.values())
        )

    def _has_baseline_data(self) -> bool:
        """Return whether baseline evaluator data is available for diff columns."""
        if not self.bs_evaluator:
            return False

        reports_coverage = getattr(self.bs_evaluator, "evaluated_reports_coverage", {})
        groups_coverage = getattr(self.bs_evaluator, "evaluated_groups_coverage", {})

        has_report_baseline = isinstance(reports_coverage, dict) and len(reports_coverage) > 0
        has_group_baseline = isinstance(groups_coverage, dict) and len(groups_coverage) > 0

        return has_report_baseline or has_group_baseline

    def get_basic_table_for_all(self, p: str, f: str) -> str:
        """Render the global summary table, with baseline deltas when available."""
        if not self._has_baseline_data():
            return self.get_basic_table(
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

        return self.get_basic_table_with_baseline(
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

    def get_basic_table(
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
        """Render the global summary table without baseline deltas."""
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

    def get_basic_table_with_baseline(
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
        """Render the global summary table with baseline delta columns."""
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

    def get_groups_table(
        self,
        p: str,
        f: str,
        evaluated_groups_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None,
    ) -> str:
        """Render the groups table for the provided evaluated group rows."""
        if evaluated_groups_coverage is None:
            evaluated_groups_coverage = self.evaluator.evaluated_groups_coverage

        if not evaluated_groups_coverage:
            return ""

        has_baseline = self._has_baseline_data()

        if not has_baseline:
            s = dedent(
                """
                | Group | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
                |-------|----------|-----------|--------|
            """
            ).strip()
            for group_name, ev in sorted(evaluated_groups_coverage.items()):
                cov = f"{ev.overall_coverage_reached}% / {ev.avg_changed_files_coverage_reached}%"
                thres = f"{ev.overall_coverage_threshold}% / {ev.changed_files_threshold}%"
                status = f"{p if ev.overall_passed else f}/{p if ev.avg_changed_files_passed else f}"
                s += f"\n| `{group_name}` | {cov} | {thres} | {status} |"
        else:
            s = dedent(
                """
                | Group | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
                |-------|----------|-----------|------------|--------|
            """
            ).strip()
            for group_name, ev in sorted(evaluated_groups_coverage.items()):
                diff_o, diff_ch = self.calculate_baseline_group_diffs(ev)
                diff_o = round(diff_o, 2)
                diff_ch = round(diff_ch, 2)
                cov = f"{ev.overall_coverage_reached}% / {ev.avg_changed_files_coverage_reached}%"
                thres = f"{ev.overall_coverage_threshold}% / {ev.changed_files_threshold}%"
                delta = f"{'+' if diff_o > 0.001 else ''}{diff_o}% / {'+' if diff_ch > 0.001 else ''}{diff_ch}%"
                status = f"{p if ev.overall_passed else f}/{p if ev.avg_changed_files_passed else f}"
                s += f"\n| `{group_name}` | {cov} | {thres} | {delta} | {status} |"
        return s

    def get_reports_table(
        self,
        p: str,
        f: str,
        evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None,
    ) -> str:
        """Render the reports table for the provided evaluated report rows."""
        if not self._has_baseline_data():
            return self._generate_reports_table_without_baseline(p, f, evaluated_reports_coverage)

        return self._generate_reports_table_with_baseline(p, f, evaluated_reports_coverage)

    def _generate_reports_table_without_baseline(
        self,
        p: str,
        f: str,
        evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None,
    ) -> str:
        if evaluated_reports_coverage is None:
            evaluated_reports_coverage = self.evaluator.evaluated_reports_coverage

        if not evaluated_reports_coverage:
            return ""

        s = dedent(
            """
            | Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
            |--------|----------|-----------|--------|
        """
        ).strip()

        keys: list[str] = sorted(list(evaluated_reports_coverage.keys()))
        for key in keys:
            evaluated_report = evaluated_reports_coverage[key]
            o_thres = evaluated_report.overall_coverage_threshold
            ch_thres = evaluated_report.changed_files_threshold

            name = evaluated_report.name
            overall_cov = evaluated_report.overall_coverage_reached
            cov = f"{overall_cov}% / {evaluated_report.avg_changed_files_coverage_reached}%"
            thres = f"{o_thres}% / {ch_thres}%"
            status_o = p if evaluated_report.overall_passed else f
            status_ch = p if evaluated_report.avg_changed_files_passed else f
            s += f"\n| `{name}` | {cov} | {thres} | {status_o}/{status_ch} |"

        return s

    def _generate_reports_table_with_baseline(
        self,
        p: str,
        f: str,
        evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None,
    ) -> str:
        if evaluated_reports_coverage is None:
            evaluated_reports_coverage = self.evaluator.evaluated_reports_coverage

        if not evaluated_reports_coverage:
            return ""

        s = dedent(
            """
            | Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
            |--------|----------|-----------|------------|--------|
        """
        ).strip()

        keys: list[str] = sorted(list(evaluated_reports_coverage.keys()))
        for key in keys:
            evaluated_report = evaluated_reports_coverage[key]
            diff_o, diff_ch = self._calculate_baseline_report_diffs(evaluated_report)

            o_thres = evaluated_report.overall_coverage_threshold
            ch_thres = evaluated_report.changed_files_threshold

            name = evaluated_report.name
            overall_cov = evaluated_report.overall_coverage_reached
            cov = f"{overall_cov}% / {evaluated_report.avg_changed_files_coverage_reached}%"
            thres = f"{o_thres}% / {ch_thres}%"
            delta = (
                f"{'+' if diff_o > 0.001 else ''}{round(diff_o, 2)}%"
                f" / {'+' if diff_ch > 0.001 else ''}{round(diff_ch, 2)}%"
            )
            status_o = p if evaluated_report.overall_passed else f
            status_ch = p if evaluated_report.avg_changed_files_passed else f
            s += f"\n| `{name}` | {cov} | {thres} | {delta} | {status_o}/{status_ch} |"

        return s

    def calculate_baseline_group_diffs(self, evaluated_coverage: EvaluatedReportCoverage) -> tuple[float, float]:
        """Calculate baseline deltas for one rendered group row."""
        if evaluated_coverage.name not in self.bs_evaluator.evaluated_groups_coverage.keys():
            return 0.0, 0.0

        baseline_group = self.bs_evaluator.evaluated_groups_coverage[evaluated_coverage.name]
        has_overall_data = (
            baseline_group.overall_coverage.covered + baseline_group.overall_coverage.missed
        ) > 0 or baseline_group.overall_coverage_reached > 0.0
        has_changed_data = (
            baseline_group.avg_changed_files_coverage.covered + baseline_group.avg_changed_files_coverage.missed
        ) > 0 or baseline_group.avg_changed_files_coverage_reached > 0.0
        if not has_overall_data and not has_changed_data:
            return 0.0, 0.0

        diff_o = evaluated_coverage.overall_coverage_reached - baseline_group.overall_coverage_reached
        diff_ch = (
            evaluated_coverage.avg_changed_files_coverage_reached - baseline_group.avg_changed_files_coverage_reached
        )

        return diff_o, diff_ch

    def _calculate_baseline_report_diffs(self, evaluated_coverage: EvaluatedReportCoverage) -> tuple[float, float]:
        """Calculate baseline deltas for one rendered report row."""
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

    def generate_changed_files_table_without_baseline(
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

                line = (
                    f"\n| [{filename}]({file_as_link_to_diff})"
                    f" | {evaluated_reports_coverage[ecr_key].changed_files_coverage_reached[file_key]}%"
                    f" | {evaluated_reports_coverage[ecr_key].per_changed_file_threshold}%"
                    f" | {p if evaluated_reports_coverage[ecr_key].changed_files_passed[file_key] else f} |"
                )
                lines.append(line)

        if len(lines) > 0:
            lines.sort()
            s += "".join(lines)
        else:
            s += "\n\nNo changed file in reports."

        return s

    def _get_changed_files_table(
        self,
        p: str,
        f: str,
        evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None,
        comment_level: str = CommentLevelEnum.FULL,
    ) -> str:
        """Render the changed-files table after applying any file-level filters."""
        if evaluated_reports_coverage is None:
            evaluated_reports_coverage = self.evaluator.evaluated_reports_coverage

        if not evaluated_reports_coverage:
            return ""

        if comment_level == CommentLevelEnum.FAILED:
            evaluated_reports_coverage = self._filter_reports_for_failed_files(evaluated_reports_coverage)

        if not evaluated_reports_coverage:
            return ""

        if not self._has_baseline_data():
            return self.generate_changed_files_table_without_baseline(p, f, evaluated_reports_coverage)

        return self.generate_changed_files_table_with_baseline(p, f, evaluated_reports_coverage)

    def _filter_reports_for_failed_files(
        self,
        evaluated_reports_coverage: dict[str, EvaluatedReportCoverage],
    ) -> dict[str, EvaluatedReportCoverage]:
        """Keep only failing changed-file rows while preserving report metadata."""
        filtered_reports: dict[str, EvaluatedReportCoverage] = {}
        for key, coverage in evaluated_reports_coverage.items():
            failed_files = {
                file_path: score
                for file_path, score in coverage.changed_files_coverage_reached.items()
                if not coverage.changed_files_passed.get(file_path, True)
            }
            if not failed_files:
                continue

            filtered_coverage = coverage.clone()
            filtered_coverage.changed_files_coverage_reached = failed_files
            filtered_coverage.changed_files_passed = {
                file_path: coverage.changed_files_passed[file_path] for file_path in failed_files
            }
            filtered_reports[key] = filtered_coverage

        return filtered_reports

    def generate_changed_files_table_with_baseline(
        self, p: str, f: str, evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None
    ) -> str:
        """Generate a changed-files table that includes baseline deltas."""
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

                line = (
                    f"\n| [{filename}]({file_as_link_to_diff})"
                    f" | {evaluated_reports_coverage[ecr_key].changed_files_coverage_reached[file_key]}%"
                    f" | {evaluated_reports_coverage[ecr_key].per_changed_file_threshold}%"
                    f" | {'+' if diff > 0.001 else ''}{round(diff, 2)}%"
                    f" | {p if evaluated_reports_coverage[ecr_key].changed_files_passed[file_key] else f} |"
                )
                lines.append(line)

        if len(lines) > 0:
            lines.sort()
            s += "".join(lines)
        else:
            s += "\n\nNo changed file in reports."

        return s
