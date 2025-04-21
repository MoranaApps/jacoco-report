"""
This module is responsible for generating PR comments for a single module.
"""

import hashlib
import os
from textwrap import dedent

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.generator.multi_pr_comment_generator import MultiPRCommentGenerator
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.utils.enums import SensitivityEnum


# pylint: disable=too-few-public-methods
class ModulePRCommentGenerator(MultiPRCommentGenerator):
    """
    A class that represents the Module PR Comment Generator.
    """

    def _get_comments_content(self) -> dict[str, str]:
        comments: dict[str, str] = {}
        p = ActionInputs.get_pass_symbol()
        f = ActionInputs.get_fail_symbol()

        for key, evaluated_module_coverage in self.evaluator.evaluated_modules_coverage.items():
            title = body = f"**{ActionInputs.get_title(evaluated_module_coverage.name)}**"
            baseline_evaluated_coverage_report = (
                self.bs_evaluator.evaluated_modules_coverage[key]
                if key in self.bs_evaluator.evaluated_modules_coverage.keys()
                else None
            )
            basic_table = self._get_basic_table_for_report(
                p, f, evaluated_module_coverage, baseline_evaluated_coverage_report
            )
            body += f"\n\n{basic_table}"

            # Hint: no module table makes sense for set of reports in one module

            if ActionInputs.get_sensitivity() in (SensitivityEnum.SUMMARY, SensitivityEnum.DETAIL):
                reports_table = self.__get_reports_table(p, f, evaluated_module_coverage.name)
                if reports_table != "":
                    body += f"\n\n{reports_table}"

            changed_lines: list[str] = []
            if ActionInputs.get_sensitivity() == SensitivityEnum.DETAIL:
                # get changed lines from all reports in module=
                for evaluated_report_coverage in self.evaluator.evaluated_reports_coverage.values():
                    if key == evaluated_report_coverage.module_name:
                        changed_lines.extend(self._get_changed_lines(p, f, evaluated_report_coverage))

                body += f"\n\n{self._get_changed_files_table_for_report_from_changed_lines(changed_lines)}"

            if (
                ActionInputs.get_skip_not_changed()
                and len(changed_lines) == 0
                and evaluated_module_coverage.overall_passed
                and evaluated_module_coverage.sum_changed_files_passed
            ):
                continue

            comments[title] = body

        return comments

    def _get_changed_lines(self, p: str, f: str, evaluated_report_coverage: EvaluatedReportCoverage) -> list[str]:
        changed_lines: list[str] = []
        ecr_key = evaluated_report_coverage.name

        for changed_file_key in evaluated_report_coverage.changed_files_passed.keys():
            filename = os.path.basename(changed_file_key)
            file_hash = hashlib.sha256(changed_file_key.encode("utf-8")).hexdigest()
            file_as_link_to_diff = (
                f"https://github.com/{self.github_repository}/pull/{self.pr_number}/files#diff-{file_hash}"
            )

            if not ActionInputs.get_baseline_paths():
                # pylint: disable=C0209
                line = "\n| {} | {}% | {}% | {} |".format(
                    f"[{filename}]({file_as_link_to_diff})",
                    evaluated_report_coverage.changed_files_coverage_reached[changed_file_key],
                    evaluated_report_coverage.changed_files_threshold,
                    (p if evaluated_report_coverage.changed_files_passed[changed_file_key] else f),
                )
            else:
                if (
                    changed_file_key
                    not in self.bs_evaluator.evaluated_reports_coverage[ecr_key].changed_files_coverage_reached.keys()
                ):
                    diff = 0.0
                else:
                    diff = (
                        evaluated_report_coverage.changed_files_coverage_reached[changed_file_key]
                        - self.bs_evaluator.evaluated_reports_coverage[ecr_key].changed_files_coverage_reached[
                            changed_file_key
                        ]
                    )

                # pylint: disable=C0209
                line = "\n| {} | {}% | {}% | {}{}% | {} |".format(
                    f"[{filename}]({file_as_link_to_diff})",
                    evaluated_report_coverage.changed_files_coverage_reached[changed_file_key],
                    evaluated_report_coverage.changed_files_threshold,
                    "+" if diff > 0.001 else "",
                    round(diff, 2),
                    (p if evaluated_report_coverage.changed_files_passed[changed_file_key] else f),
                )

            changed_lines.append(line)

        return changed_lines

    def _get_changed_files_table_for_report_from_changed_lines(self, changed_lines: list[str]) -> str:
        if not ActionInputs.get_baseline_paths():
            s = dedent(
                """
                | File Path | Coverage | Threshold | Status |
                |-----------|----------|-----------|--------|
            """
            ).strip()

        else:
            s = dedent(
                """
                | File Path | Coverage | Threshold | Δ Coverage | Status |
                |-----------|----------|-----------|------------|--------|
            """
            ).strip()

        if len(changed_lines) > 0:
            changed_lines.sort()
            s += "".join(changed_lines)
        else:
            s += "\nNo changed file in reports."

        return s

    def __get_reports_table(self, p: str, f: str, module_name: str) -> str:
        if not ActionInputs.get_baseline_paths():
            return self.__generate_reports_table_without_baseline(p, f, module_name)

        return self.__generate_reports_table_with_baseline(p, f, module_name)

    def __generate_reports_table_without_baseline(self, p: str, f: str, module_name: str) -> str:
        s = dedent(
            """
            | Report | Coverage | Threshold | Status |
            |--------|----------|-----------|--------|
        """
        ).strip()

        provided_reports = 0
        keys: list[str] = sorted(list(self.evaluator.evaluated_reports_coverage.keys()))
        for key in keys:
            evaluated_report = self.evaluator.evaluated_reports_coverage[key]
            if (
                    ActionInputs.get_skip_not_changed()
                    and evaluated_report.name not in self.changed_modules
                    and evaluated_report.overall_passed
                    and evaluated_report.sum_changed_files_passed
                    and len(evaluated_report.changed_files_coverage_reached) == 0
            ):
                continue

            if evaluated_report.module_name != module_name:
                continue

            provided_reports += 1
            o_thres = ActionInputs.get_min_coverage_overall()
            ch_thres = ActionInputs.get_min_coverage_changed_files()

            if len(ActionInputs.get_modules()) > 0 and len(ActionInputs.get_modules_thresholds()) > 0:
                o_thres = evaluated_report.overall_coverage_threshold
                ch_thres = evaluated_report.changed_files_threshold

            # pylint: disable=C0209
            s += "\n| `{}` | {}% / {}% | {}% / {}% | {}/{} |".format(
                evaluated_report.name,
                evaluated_report.overall_coverage_reached,
                evaluated_report.sum_changed_files_coverage_reached,
                o_thres,
                ch_thres,
                p if evaluated_report.overall_passed else f,
                p if evaluated_report.sum_changed_files_passed else f,
            )

        if provided_reports == 0:
            s += "\nNo changed file in reports."

        return s

    def __generate_reports_table_with_baseline(self, p: str, f: str, module_name: str) -> str:
        s = dedent(
            """
            | Report | Coverage | Threshold | Δ Coverage | Status |
            |--------|----------|-----------|------------|--------|
        """
        ).strip()

        provided_reports = 0
        keys: list[str] = sorted(list(self.evaluator.evaluated_reports_coverage.keys()))
        for key in keys:
            evaluated_report = self.evaluator.evaluated_reports_coverage[key]

            if (
                    ActionInputs.get_skip_not_changed()
                    and evaluated_report.name not in self.changed_modules
                    and evaluated_report.overall_passed
                    and evaluated_report.sum_changed_files_passed
                    and len(evaluated_report.changed_files_coverage_reached) == 0
            ):
                continue

            if evaluated_report.module_name != module_name:
                continue

            provided_reports += 1
            diff_o, diff_ch = self._calculate_module_diff(evaluated_report)

            o_thres = ActionInputs.get_min_coverage_overall()
            ch_thres = ActionInputs.get_min_coverage_changed_files()

            if len(ActionInputs.get_modules()) > 0 and len(ActionInputs.get_modules_thresholds()) > 0:
                o_thres = evaluated_report.overall_coverage_threshold
                ch_thres = evaluated_report.changed_files_threshold

            # pylint: disable=C0209
            s += "\n| `{}` | {}% / {}% | {}% / {}% | {}{}% / {}{}% | {}/{} |".format(
                evaluated_report.name,
                evaluated_report.overall_coverage_reached,
                evaluated_report.sum_changed_files_coverage_reached,
                o_thres,
                ch_thres,
                "+" if diff_o > 0.001 else "",
                round(diff_o, 2),
                "+" if diff_ch > 0.001 else "",
                round(diff_ch, 2),
                p if evaluated_report.overall_passed else f,
                p if evaluated_report.sum_changed_files_passed else f,
            )

        if provided_reports == 0:
            s += "\nNo changed file in reports."

        return s
