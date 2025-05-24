import pytest

from jacoco_report.generator.single_pr_comment_generator import SinglePRCommentGenerator
from jacoco_report.utils.enums import SensitivityEnum
from jacoco_report.utils.github import GitHub

@pytest.fixture
def mock_github(mocker):
    return mocker.Mock(spec=GitHub)

@pytest.fixture
def mock_evaluator(mocker):
    evaluator = mocker.Mock()
    evaluator.total_coverage_overall = 85.2
    evaluator.total_coverage_changed_files = 78.4
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = False
    evaluator.evaluated_reports_coverage = {}
    return evaluator

@pytest.fixture
def mock_baseline_evaluator(mocker):
    evaluator = mocker.Mock()
    evaluator.total_coverage_overall = 0.0
    evaluator.total_coverage_changed_files = 0.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = True
    return evaluator

@pytest.fixture
def single_pr_comment_generator(mock_github, mock_evaluator, mock_baseline_evaluator):
    return SinglePRCommentGenerator(mock_github, mock_evaluator, mock_baseline_evaluator, 1)

def test_generate_creates_comment(single_pr_comment_generator, mocker):
    mocker.patch.object(single_pr_comment_generator, "_get_comment_content", return_value=("Title", "Test Body"))
    mocker.patch.object(single_pr_comment_generator.gh, "get_comments", return_value=[])
    mock_add_comment = mocker.patch.object(single_pr_comment_generator.gh, "add_comment")

    single_pr_comment_generator.generate()

    mock_add_comment.assert_called_once_with(1, "Test Body")

def test_generate_updates_comment(single_pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value="false")
    mocker.patch.object(single_pr_comment_generator, "_get_comment_content", return_value=("Title", "Test Body"))
    mocker.patch.object(single_pr_comment_generator.gh, "get_comments", return_value=[{"id": 1, "body": "Title"}])
    mocker.patch.object(single_pr_comment_generator.evaluator, "changed_files_count", return_value=1)
    mock_update_comment = mocker.patch.object(single_pr_comment_generator.gh, "update_comment")

    single_pr_comment_generator.generate()

    mock_update_comment.assert_called_once_with(1, "Test Body")

def test_generate_deletes_comment(single_pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value="false")
    mocker.patch.object(single_pr_comment_generator, "_get_comment_content", return_value=("Title", "Test Body"))
    mocker.patch.object(single_pr_comment_generator.gh, "get_comments", return_value=[{"id": 1, "body": "Title"}])
    mocker.patch.object(single_pr_comment_generator.evaluator, "changed_files_count", return_value=0)
    mock_delete_comment = mocker.patch.object(single_pr_comment_generator.gh, "delete_comment")

    single_pr_comment_generator.generate()

    mock_delete_comment.assert_called_once_with(1)

def test_get_comment_content_minimalist(single_pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="Test Title")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_pass_symbol", return_value="✅")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_fail_symbol", return_value="❌")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_sensitivity", return_value=SensitivityEnum.MINIMAL)

    title, body = single_pr_comment_generator._get_comment_content()

    assert "**Test Title**" in title
    assert "**Test Title**" in body
    assert "| **Overall**       | 85.2% | 0.0% | ✅ |" in body
    assert "| **Changed Files** | 78.4% | 0.0% | ❌ |" in body


def test_get_comment_content_summary(single_pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="Test Title")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_pass_symbol", return_value="✅")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_fail_symbol", return_value="❌")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_sensitivity", return_value=SensitivityEnum.SUMMARY)

    title, body = single_pr_comment_generator._get_comment_content()

    assert "**Test Title**" in title
    assert "**Test Title**" in body
    assert "| **Overall**       | 85.2% | 0.0% | ✅ |" in body
    assert "| **Changed Files** | 78.4% | 0.0% | ❌ |" in body


def test_get_comment_content_detailed(single_pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="Test Title")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_pass_symbol", return_value="✅")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_fail_symbol", return_value="❌")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_sensitivity", return_value=SensitivityEnum.DETAIL)

    title, body = single_pr_comment_generator._get_comment_content()

    assert "**Test Title**" in title
    assert "**Test Title**" in body
    assert "| **Overall**       | 85.2% | 0.0% | ✅ |" in body
    assert "| **Changed Files** | 78.4% | 0.0% | ❌ |" in body
