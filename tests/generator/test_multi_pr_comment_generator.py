import pytest

from jacoco_report.generator.multi_pr_comment_generator import MultiPRCommentGenerator
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.utils.github import GitHub

def test_existing_comment_detection(mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=True)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="Report Title")

    # Create a mock GitHub instance
    mock_gh = mocker.Mock(spec=GitHub)
    mock_gh.get_comments.return_value = [
        {"id": 1, "body": "Report Title for module-a"},
        {"id": 2, "body": "Another comment"}
    ]

    # Create an instance of MultiPRCommentGenerator
    generator = MultiPRCommentGenerator(
        gh=mock_gh,
        pr_number=123,
        evaluator=mocker.MagicMock(),
        bs_evaluator=mocker.MagicMock()
    )

    # Mock the _get_comments_content method to return a specific title and body
    mocker.patch.object(generator, '_get_comments_content', return_value={"Report Title for module-a": "Comment body"})

    # Run the generate method
    generator.generate()

    # Verify that the existing comment was detected and update_comment was called
    mock_gh.update_comment.assert_called_once_with(1, "Comment body")
    mock_gh.add_comment.assert_not_called()

def test_no_changed_files_in_reports(mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=True)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="Report Title")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=None)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value=False)

    # Create a mock GitHub instance
    mock_gh = mocker.Mock(spec=GitHub)

    # Create an instance of MultiPRCommentGenerator
    generator = MultiPRCommentGenerator(
        gh=mock_gh,
        pr_number=123,
        evaluator=mocker.MagicMock(),
        bs_evaluator=mocker.MagicMock()
    )

    # Mock the evaluated_reports_coverage to be empty
    generator.evaluator.evaluated_reports_coverage = {}

    # Call the _get_changed_files_table_for_report method
    result = generator._get_changed_files_table_for_report("✓", "✗", "key", EvaluatedReportCoverage())

    # Verify the result
    assert result == "| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports."

def test__comment_for_delete_detection(mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=True)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="Report Title")

    # Create a mock GitHub instance
    mock_gh = mocker.Mock(spec=GitHub)
    mock_gh.get_comments.return_value = [
        {"id": 1, "body": "Report Title for module-a"},
        {"id": 2, "body": "Another comment"}
    ]

    # Create an instance of MultiPRCommentGenerator
    generator = MultiPRCommentGenerator(
        gh=mock_gh,
        pr_number=123,
        evaluator=mocker.MagicMock(),
        bs_evaluator=mocker.MagicMock()
    )

    # Mock the _get_comments_content method to return a specific title and body
    mocker.patch.object(generator, '_get_comments_content', return_value={"Report Title for module-a": None})

    # Run the generate method
    generator.generate()

    # Verify that the existing comment was detected and update_comment was called
    mock_gh.update_comment.assert_not_called()
    mock_gh.add_comment.assert_not_called()
    mock_gh.delete_comment.assert_called_once_with(1)
