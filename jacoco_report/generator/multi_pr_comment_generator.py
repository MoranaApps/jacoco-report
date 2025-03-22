"""
A module that contains the MultiPRCommentGenerator class.
"""

import logging
from typing import Optional

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.generator.pr_comment_generator import PRCommentGenerator
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.utils.enums import SensitivityEnum

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class MultiPRCommentGenerator(PRCommentGenerator):
    """
    A class that represents the Multi PR Comment Generator.
    """

    def generate(self) -> None:
        """
        The method that generates the comment for each report file.
        """
        jacoco_comments: dict[str, str] = self._get_comments_content()
        logger.info("Generating %s pr comments...", format(len(jacoco_comments)))

        # Get all gh_comments on the pull request
        gh_comments = self.gh.get_comments(self.pr_number)

        # Check for existing comment with the same title
        for title, body in jacoco_comments.items():
            existing_comment = None
            for gh_comment in gh_comments:
                if gh_comment["body"].startswith(title):  # Detects if it starts with the title
                    logger.info("Found existing comment with title: '%s'", title)
                    existing_comment = gh_comment
                    break

            if existing_comment and ActionInputs.get_update_comment():
                # Update the existing comment
                self.gh.update_comment(existing_comment["id"], body)
                logger.info("Updated comment with title: '%s'", title)
            else:
                # create a comment on pull request
                self.gh.add_comment(self.pr_number, body)
                logger.info("Added comment with title: '%s'", title)

    def _get_comments_content(self) -> dict[str, str]:
        comments: dict[str, str] = {}
        p = ActionInputs.get_pass_symbol()
        f = ActionInputs.get_fail_symbol()

        for key, evaluated_coverage_report in self.evaluator.evaluated_reports_coverage.items():
            if ActionInputs.get_skip_not_changed() and len(evaluated_coverage_report.changed_files_passed) == 0:
                continue

            title = body = f"**{ActionInputs.get_title()}{evaluated_coverage_report.name}**"
            baseline_evaluated_coverage_report = (
                self.bs_evaluator.evaluated_reports_coverage[key]
                if key in self.bs_evaluator.evaluated_reports_coverage.keys()
                else None
            )
            body += f"\n\n{self._get_basic_table_for_report(p, f, evaluated_coverage_report,
                                                            baseline_evaluated_coverage_report)}"

            # Hint: no module table makes sense for isolated jacoco report

            if ActionInputs.get_sensitivity() == SensitivityEnum.DETAIL:
                body += f"\n\n{self._get_changed_files_table_for_report(p, f, key, evaluated_coverage_report)}"

            comments[title] = body

        return comments

    def _get_basic_table_for_report(
        self,
        p: str,
        f: str,
        evaluated_report: EvaluatedReportCoverage,
        bs_evaluated_report: Optional[EvaluatedReportCoverage] = None,
    ) -> str:
        # pylint: disable=duplicate-code
        if not ActionInputs.get_baseline_paths():
            # pylint: disable=duplicate-code
            return self._get_basic_table(
                p,
                f,
                ActionInputs.get_metric(),
                evaluated_report.overall_coverage_reached,
                evaluated_report.overall_passed,
                evaluated_report.overall_coverage_threshold,
                evaluated_report.sum_changed_files_coverage_reached,
                evaluated_report.sum_changed_files_passed,
                evaluated_report.changed_files_threshold,
            )

        return self._get_basic_table_with_baseline(
            p,
            f,
            ActionInputs.get_metric(),
            evaluated_report.overall_coverage_reached,
            evaluated_report.overall_passed,
            evaluated_report.overall_coverage_threshold,
            evaluated_report.sum_changed_files_coverage_reached,
            evaluated_report.sum_changed_files_passed,
            evaluated_report.changed_files_threshold,
            bs_evaluated_report.overall_coverage_reached if bs_evaluated_report else 0.0,
            bs_evaluated_report.sum_changed_files_coverage_reached if bs_evaluated_report else 0.0,
        )

    def _get_changed_files_table_for_report(
        self, p: str, f: str, key: str, evaluated_report_coverage: EvaluatedReportCoverage
    ) -> str:
        if len(self.evaluator.evaluated_reports_coverage.keys()) == 0:
            return "No changed file in reports."

        if not ActionInputs.get_baseline_paths():
            return self._generate_changed_files_table_without_baseline(p, f, {key: evaluated_report_coverage})

        return self._generate_changed_files_table_with_baseline(p, f, {key: evaluated_report_coverage})
