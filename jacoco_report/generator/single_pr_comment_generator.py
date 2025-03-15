"""
A module that contains the SinglePRCommentGenerator class.
"""

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.generator.pr_comment_generator import PRCommentGenerator
from jacoco_report.utils.enums import SensitivityEnum


# pylint: disable=too-few-public-methods
class SinglePRCommentGenerator(PRCommentGenerator):
    """
    A class that represents the Single PR Comment Generator.
    """

    def generate(self) -> None:
        """
        The method that generates the comment for a single generator.
        """
        title, pr_body = self._get_comment_content()

        # Get all comments on the pull request
        comments = self.gh.get_comments(self.pr_number)

        # Check for existing comment with the same title
        existing_comment = None
        for comment in comments:
            if comment["body"].startswith(title):  # Detects if it starts with the title
                existing_comment = comment
                break

        if existing_comment and ActionInputs.get_update_comment():
            # Update the existing comment
            self.gh.update_comment(existing_comment["id"], pr_body)
        else:
            # create a comment on pull request
            self.gh.add_comment(self.pr_number, pr_body)

    def _get_comment_content(self) -> (str, str):
        title = body = f"**{ActionInputs.get_title()}**"

        p = ActionInputs.get_pass_symbol()
        f = ActionInputs.get_fail_symbol()

        body += f"\n\n{self._get_basic_table_for_all(p, f)}"

        if ActionInputs.get_sensitivity() in (SensitivityEnum.SUMMARY, SensitivityEnum.DETAIL):
            modules_table = self._get_modules_table(p, f)
            if modules_table != "":
                body += f"\n\n{modules_table}"

        if ActionInputs.get_sensitivity() == SensitivityEnum.DETAIL:
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
                ActionInputs.get_min_coverage_overall(),
                self.evaluator.total_coverage_changed_files,
                self.evaluator.total_coverage_changed_files_passed,
                ActionInputs.get_min_coverage_changed_files(),
            )

        return self._get_basic_table_with_baseline(
            p,
            f,
            ActionInputs.get_metric(),
            self.evaluator.total_coverage_overall,
            self.evaluator.total_coverage_overall_passed,
            ActionInputs.get_min_coverage_overall(),
            self.evaluator.total_coverage_changed_files,
            self.evaluator.total_coverage_changed_files_passed,
            ActionInputs.get_min_coverage_changed_files(),
            self.bs_evaluator.total_coverage_overall,
            self.bs_evaluator.total_coverage_changed_files,
        )

    def _get_changed_files_table(self, p, f) -> str:
        if len(self.evaluator.evaluated_reports_coverage.keys()) == 0:
            return "No changed file in reports."

        if not ActionInputs.get_baseline_paths():
            return self._generate_changed_files_table_without_baseline(p, f)

        return self._generate_changed_files_table_with_baseline(p, f)
