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
            title = body = f"**{ActionInputs.get_title()}{evaluated_module_coverage.name}**"
            baseline_evaluated_coverage_report = (
                self.bs_evaluator.evaluated_modules_coverage[key]
                if key in self.bs_evaluator.evaluated_modules_coverage.keys()
                else None
            )
            body += f"\n\n{self._get_basic_table_for_report(p, f, evaluated_module_coverage,
                                                            baseline_evaluated_coverage_report)}"

            # Hint: no module table makes sense for set of reports in one module

            changed_lines: list[str] = []
            if ActionInputs.get_sensitivity() == SensitivityEnum.DETAIL:
                # get changed lines from all reports in module=
                for evaluated_report_coverage in self.evaluator.evaluated_reports_coverage.values():
                    if key == evaluated_report_coverage.module_name:
                        changed_lines.extend(self._get_changed_lines(p, f, evaluated_report_coverage))

                if len(changed_lines) > 0:
                    body += f"\n\n{self._get_changed_files_table_for_report_from_changed_lines(changed_lines)}"
                else:
                    body += "\n\nNo changed file in reports."

            if ActionInputs.get_skip_not_changed() and len(changed_lines) == 0:
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
                    "+" if diff > 0 else "",
                    round(diff, 1),
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
            return s

        return ""
