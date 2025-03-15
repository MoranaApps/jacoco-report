import pytest

from jacoco_report.generator.pr_comment_generator_factory import PRCommentGeneratorFactory
from jacoco_report.generator.module_pr_comment_generator import ModulePRCommentGenerator
from jacoco_report.generator.multi_pr_comment_generator import MultiPRCommentGenerator
from jacoco_report.generator.single_pr_comment_generator import SinglePRCommentGenerator
from jacoco_report.utils.enums import CommentModeEnum

# get_generator

def test_get_generator_single():
    generator = PRCommentGeneratorFactory.get_generator(CommentModeEnum.SINGLE, None, None, None, None)
    assert isinstance(generator, SinglePRCommentGenerator)

def test_get_generator_multi():
    generator = PRCommentGeneratorFactory.get_generator(CommentModeEnum.MULTI, None, None, None, None)
    assert isinstance(generator, MultiPRCommentGenerator)

def test_get_generator_module():
    generator = PRCommentGeneratorFactory.get_generator(CommentModeEnum.MODULE, None, None, None, None)
    assert isinstance(generator, ModulePRCommentGenerator)

def test_get_generator_invalid():
    with pytest.raises(ValueError, match="Unknown generator type: invalid"):
        PRCommentGeneratorFactory.get_generator("invalid", None, None, None, None)
