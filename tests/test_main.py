import logging

from jacoco_report.action_inputs import ActionInputs
from main import run

def test_run_no_violations(mocker):
    # Mock dependencies
    mocker.patch("main.setup_logging")
    mock_logger = mocker.patch("main.logging.getLogger")
    mock_logger.return_value = mocker.Mock(spec=logging.Logger)
    mock_validate_inputs = mocker.patch.object(ActionInputs, "validate_inputs")
    mock_jacoco_report = mocker.patch("main.JaCoCoReport")
    mock_set_action_output = mocker.patch("main.set_action_output")
    mock_set_action_output_text = mocker.patch("main.set_action_output_text")
    mock_set_action_failed = mocker.patch("main.set_action_failed")
    mock_sys_exit = mocker.patch("sys.exit")

    # Create a mock JaCoCoReport instance
    mock_jr = mock_jacoco_report.return_value
    mock_jr.total_overall_coverage = 85.0
    mock_jr.total_changed_files_coverage = 75.0
    mock_jr.evaluated_coverage_reports = "Report Coverage"
    mock_jr.evaluated_coverage_modules = "Module Coverage"
    mock_jr.violations = []

    # Run the main function
    run()

    # Assertions
    mock_validate_inputs.assert_called_once()
    mock_jacoco_report.assert_called_once()
    mock_jr.run.assert_called_once()
    mock_set_action_output.assert_any_call("coverage-overall", "85.0")
    mock_set_action_output.assert_any_call("coverage-changed-files", "75.0")
    mock_set_action_output_text.assert_any_call("reports-coverage", "Report Coverage")
    mock_set_action_output_text.assert_any_call("modules-coverage", "Module Coverage")
    mock_set_action_failed.assert_not_called()
    mock_sys_exit.assert_called_once_with(0)


def test_run_with_violations(mocker):
    # Mock dependencies
    mocker.patch("main.setup_logging")
    mock_logger = mocker.patch("main.logging.getLogger")
    mock_logger.return_value = mocker.Mock(spec=logging.Logger)
    mock_validate_inputs = mocker.patch.object(ActionInputs, "validate_inputs")
    mock_jacoco_report = mocker.patch("main.JaCoCoReport")
    mock_set_action_output = mocker.patch("main.set_action_output")
    mock_set_action_output_text = mocker.patch("main.set_action_output_text")
    mock_set_action_failed = mocker.patch("main.set_action_failed")

    # Create a mock JaCoCoReport instance
    mock_jr = mock_jacoco_report.return_value
    mock_jr.total_overall_coverage = 85.0
    mock_jr.total_changed_files_coverage = 75.0
    mock_jr.evaluated_coverage_reports = "Report Coverage"
    mock_jr.evaluated_coverage_modules = "Module Coverage"
    mock_jr.violations = ["Violation 1"]

    # Run the main function
    run()

    # Assertions
    mock_validate_inputs.assert_called_once()
    mock_jacoco_report.assert_called_once()
    mock_jr.run.assert_called_once()
    mock_set_action_output.assert_any_call("coverage-overall", "85.0")
    mock_set_action_output.assert_any_call("coverage-changed-files", "75.0")
    mock_set_action_output_text.assert_any_call("reports-coverage", "Report Coverage")
    mock_set_action_output_text.assert_any_call("modules-coverage", "Module Coverage")
    mock_set_action_failed.assert_called_once_with(messages=["Violation 1"], fail=ActionInputs.get_fail_on_threshold())
