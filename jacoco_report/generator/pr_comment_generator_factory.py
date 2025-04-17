"""
A module that contains the PR Comment Generator Factory.
"""

from typing_extensions import Optional

from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.generator.module_pr_comment_generator import ModulePRCommentGenerator
from jacoco_report.generator.multi_pr_comment_generator import MultiPRCommentGenerator
from jacoco_report.generator.single_pr_comment_generator import SinglePRCommentGenerator
from jacoco_report.utils.enums import CommentModeEnum
from jacoco_report.utils.github import GitHub


# pylint: disable=too-few-public-methods
class PRCommentGeneratorFactory:
    """
    A class that represents the PR Comment Generator Factory.
    """

    # pylint: disable=too-many-arguments
    @staticmethod
    def get_generator(
        generator_type: str,
        gh: GitHub,
        evaluator: CoverageEvaluator,
        bs_evaluator: CoverageEvaluator,
        pr_number: int,
        changed_modules: Optional[list[str]] = None,
    ):
        """
        The method that returns the PR Comment Generator based on the generator type.

        Parameters:
            generator_type (str): The type of the generator.
            gh (GitHub): The GitHub object.
            evaluator (CoverageEvaluator): The coverage evaluator object.
            bs_evaluator (CoverageEvaluator): The baseline coverage evaluator object.
            pr_number (int): The pull request number.
            changed_modules (list[str]): The list of changed modules.
        """
        match generator_type:
            case CommentModeEnum.SINGLE:
                return SinglePRCommentGenerator(gh, evaluator, bs_evaluator, pr_number, changed_modules)
            case CommentModeEnum.MULTI:
                return MultiPRCommentGenerator(gh, evaluator, bs_evaluator, pr_number, changed_modules)
            case CommentModeEnum.MODULE:
                return ModulePRCommentGenerator(gh, evaluator, bs_evaluator, pr_number, changed_modules)
            case _:
                raise ValueError(f"Unknown generator type: {generator_type}")
