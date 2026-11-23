from pytest_mock import MockerFixture, MockType

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.utils.enums import FailOnThresholdEnum
from main import run


def test_run_no_violations(mocker: MockerFixture):
    # Mock dependencies
    mocker.patch("main.setup_logging")
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
    mock_jr.evaluated_coverage_groups = "Group Coverage"
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
    mock_set_action_output_text.assert_any_call("groups-coverage", "Group Coverage")
    mock_set_action_failed.assert_not_called()
    mock_sys_exit.assert_called_once_with(0)


def test_run_fail_overall_level(mocker: MockerFixture):
    # Mock dependencies
    mocker.patch("main.setup_logging")
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
    mock_jr.evaluated_coverage_groups = "Group Coverage"
    mock_jr.violations = ["Violation 1"]
    mock_jr.reached_threshold_overall = False
    mock_jr.reached_threshold_changed_files_average = True
    mock_jr.reached_threshold_per_change_file = True
    mock_jr.reached_threshold_fail_unchanged = True
    mock_jr.has_operational_failure = False

    # Run the main function
    run()

    # Assertions
    mock_validate_inputs.assert_called_once()
    mock_jacoco_report.assert_called_once()
    mock_jr.run.assert_called_once()
    mock_set_action_output.assert_any_call("coverage-overall", "85.0")
    mock_set_action_output.assert_any_call("coverage-changed-files", "75.0")
    mock_set_action_output_text.assert_any_call("reports-coverage", "Report Coverage")
    mock_set_action_output_text.assert_any_call("groups-coverage", "Group Coverage")
    mock_set_action_failed.assert_called_once_with(messages=["Violation 1"], fail=True)


def test_run_fail_changed_files_average_level(mocker: MockerFixture):
    # Mock dependencies
    mocker.patch("main.setup_logging")
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
    mock_jr.evaluated_coverage_groups = "Group Coverage"
    mock_jr.violations = ["Violation 1"]
    mock_jr.reached_threshold_overall = True
    mock_jr.reached_threshold_changed_files_average = False
    mock_jr.reached_threshold_per_change_file = True
    mock_jr.reached_threshold_fail_unchanged = True
    mock_jr.has_operational_failure = False

    # Run the main function
    run()

    # Assertions
    mock_validate_inputs.assert_called_once()
    mock_jacoco_report.assert_called_once()
    mock_jr.run.assert_called_once()
    mock_set_action_output.assert_any_call("coverage-overall", "85.0")
    mock_set_action_output.assert_any_call("coverage-changed-files", "75.0")
    mock_set_action_output_text.assert_any_call("reports-coverage", "Report Coverage")
    mock_set_action_output_text.assert_any_call("groups-coverage", "Group Coverage")
    mock_set_action_failed.assert_called_once_with(messages=["Violation 1"], fail=True)


def test_run_fail_per_changed_file_level(mocker: MockerFixture):
    # Mock dependencies
    mocker.patch("main.setup_logging")
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
    mock_jr.evaluated_coverage_groups = "Group Coverage"
    mock_jr.violations = ["Violation 1"]
    mock_jr.reached_threshold_overall = True
    mock_jr.reached_threshold_changed_files_average = True
    mock_jr.reached_threshold_per_change_file = False
    mock_jr.reached_threshold_fail_unchanged = True
    mock_jr.has_operational_failure = False

    # Run the main function
    run()

    # Assertions
    mock_validate_inputs.assert_called_once()
    mock_jacoco_report.assert_called_once()
    mock_jr.run.assert_called_once()
    mock_set_action_output.assert_any_call("coverage-overall", "85.0")
    mock_set_action_output.assert_any_call("coverage-changed-files", "75.0")
    mock_set_action_output_text.assert_any_call("reports-coverage", "Report Coverage")
    mock_set_action_output_text.assert_any_call("groups-coverage", "Group Coverage")
    mock_set_action_failed.assert_called_once_with(messages=["Violation 1"], fail=True)


def test_run_fail_disabled(mocker: MockerFixture):
    # Mock dependencies
    mocker.patch("main.setup_logging")
    mock_validate_inputs = mocker.patch.object(ActionInputs, "validate_inputs")
    mock_jacoco_report = mocker.patch("main.JaCoCoReport")
    mock_set_action_output = mocker.patch("main.set_action_output")
    mock_set_action_output_text = mocker.patch("main.set_action_output_text")
    mock_set_action_failed = mocker.patch("main.set_action_failed")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_fail_on_threshold", return_value=[])

    # Create a mock JaCoCoReport instance
    mock_jr = mock_jacoco_report.return_value
    mock_jr.total_overall_coverage = 85.0
    mock_jr.total_changed_files_coverage = 75.0
    mock_jr.evaluated_coverage_reports = "Report Coverage"
    mock_jr.evaluated_coverage_groups = "Group Coverage"
    mock_jr.violations = ["Violation 1"]
    mock_jr.reached_threshold_overall = True
    mock_jr.reached_threshold_changed_files_average = True
    mock_jr.reached_threshold_per_change_file = True
    mock_jr.reached_threshold_fail_unchanged = True
    mock_jr.has_operational_failure = False

    # Run the main function
    run()

    # Assertions
    mock_validate_inputs.assert_called_once()
    mock_jacoco_report.assert_called_once()
    mock_jr.run.assert_called_once()
    mock_set_action_output.assert_any_call("coverage-overall", "85.0")
    mock_set_action_output.assert_any_call("coverage-changed-files", "75.0")
    mock_set_action_output_text.assert_any_call("reports-coverage", "Report Coverage")
    mock_set_action_output_text.assert_any_call("groups-coverage", "Group Coverage")
    mock_set_action_failed.assert_called_once_with(messages=["Violation 1"], fail=False)


def test_run_fail_disabled_level(mocker: MockerFixture):
    # Mock dependencies
    mocker.patch("main.setup_logging")
    mock_validate_inputs = mocker.patch.object(ActionInputs, "validate_inputs")
    mock_jacoco_report = mocker.patch("main.JaCoCoReport")
    mock_set_action_output = mocker.patch("main.set_action_output")
    mock_set_action_output_text = mocker.patch("main.set_action_output_text")
    mock_set_action_failed = mocker.patch("main.set_action_failed")
    mocker.patch(
        "jacoco_report.action_inputs.ActionInputs.get_fail_on_threshold",
        return_value=[FailOnThresholdEnum.OVERALL, FailOnThresholdEnum.CHANGED_FILES_AVERAGE],
    )

    # Create a mock JaCoCoReport instance
    mock_jr = mock_jacoco_report.return_value
    mock_jr.total_overall_coverage = 85.0
    mock_jr.total_changed_files_coverage = 75.0
    mock_jr.evaluated_coverage_reports = "Report Coverage"
    mock_jr.evaluated_coverage_groups = "Group Coverage"
    mock_jr.violations = ["Violation 1"]
    mock_jr.reached_threshold_overall = True
    mock_jr.reached_threshold_changed_files_average = True
    mock_jr.reached_threshold_per_change_file = False
    mock_jr.reached_threshold_fail_unchanged = True
    mock_jr.has_operational_failure = False

    # Run the main function
    run()

    # Assertions
    mock_validate_inputs.assert_called_once()
    mock_jacoco_report.assert_called_once()
    mock_jr.run.assert_called_once()
    mock_set_action_output.assert_any_call("coverage-overall", "85.0")
    mock_set_action_output.assert_any_call("coverage-changed-files", "75.0")
    mock_set_action_output_text.assert_any_call("reports-coverage", "Report Coverage")
    mock_set_action_output_text.assert_any_call("groups-coverage", "Group Coverage")
    mock_set_action_failed.assert_called_once_with(messages=["Violation 1"], fail=False)


def test_run_operational_violation_fails_even_with_fail_unchanged_only(mocker: MockerFixture):
    mocker.patch("main.setup_logging")
    mocker.patch.object(ActionInputs, "validate_inputs")
    mock_jacoco_report = mocker.patch("main.JaCoCoReport")
    mock_set_action_output = mocker.patch("main.set_action_output")
    mock_set_action_output_text = mocker.patch("main.set_action_output_text")
    mock_set_action_failed = mocker.patch("main.set_action_failed")
    mocker.patch(
        "jacoco_report.action_inputs.ActionInputs.get_fail_on_threshold",
        return_value=[FailOnThresholdEnum.FAIL_UNCHANGED],
    )

    mock_jr = mock_jacoco_report.return_value
    mock_jr.total_overall_coverage = 0.0
    mock_jr.total_changed_files_coverage = 0.0
    mock_jr.evaluated_coverage_reports = "{}"
    mock_jr.evaluated_coverage_groups = "{}"
    mock_jr.violations = ["Failed to retrieve changed files from GitHub API."]
    mock_jr.reached_threshold_overall = True
    mock_jr.reached_threshold_changed_files_average = True
    mock_jr.reached_threshold_per_change_file = True
    mock_jr.reached_threshold_fail_unchanged = True
    mock_jr.has_operational_failure = True

    run()

    mock_set_action_output.assert_any_call("coverage-overall", "0.0")
    mock_set_action_output_text.assert_any_call("reports-coverage", "{}")
    mock_set_action_failed.assert_called_once_with(
        messages=["Failed to retrieve changed files from GitHub API."],
        fail=True,
    )


# ---------------------------------------------------------------------------
# G15  coverage-overall-passed and coverage-changed-files-passed set as outputs
# ---------------------------------------------------------------------------


def test_main_sets_coverage_overall_passed_output(mocker: MockerFixture):
    """main.run() writes coverage-overall-passed as a GitHub Actions output."""
    mocker.patch("main.setup_logging")
    mocker.patch.object(ActionInputs, "validate_inputs")
    mock_jr_cls = mocker.patch("main.JaCoCoReport")
    mock_set_output = mocker.patch("main.set_action_output")
    mocker.patch("main.set_action_output_text")
    mocker.patch("main.set_action_failed")
    mocker.patch("sys.exit")

    mock_jr = mock_jr_cls.return_value
    mock_jr.total_overall_coverage = 88.0
    mock_jr.total_changed_files_coverage = 75.0
    mock_jr.total_overall_coverage_passed = True
    mock_jr.total_changed_files_coverage_passed = False
    mock_jr.evaluated_coverage_reports = "{}"
    mock_jr.evaluated_coverage_groups = "{}"
    mock_jr.violations = []

    run()

    mock_set_output.assert_any_call("coverage-overall-passed", "True")
    mock_set_output.assert_any_call("coverage-changed-files-passed", "False")


def test_main_sets_coverage_changed_files_passed_false_when_failing(mocker: MockerFixture):
    """main.run() correctly writes False when changed-files coverage does not pass."""
    mocker.patch("main.setup_logging")
    mocker.patch.object(ActionInputs, "validate_inputs")
    mock_jr_cls = mocker.patch("main.JaCoCoReport")
    mock_set_output = mocker.patch("main.set_action_output")
    mocker.patch("main.set_action_output_text")
    mock_set_failed = mocker.patch("main.set_action_failed")
    mocker.patch(
        "jacoco_report.action_inputs.ActionInputs.get_fail_on_threshold",
        return_value=["overall", "changed-files-average"],
    )

    mock_jr = mock_jr_cls.return_value
    mock_jr.total_overall_coverage = 85.0
    mock_jr.total_changed_files_coverage = 60.0
    mock_jr.total_overall_coverage_passed = True
    mock_jr.total_changed_files_coverage_passed = False
    mock_jr.evaluated_coverage_reports = "{}"
    mock_jr.evaluated_coverage_groups = "{}"
    mock_jr.violations = ["Changed files coverage below threshold."]
    mock_jr.reached_threshold_overall = True
    mock_jr.reached_threshold_changed_files_average = False
    mock_jr.reached_threshold_per_change_file = True
    mock_jr.reached_threshold_fail_unchanged = True
    mock_jr.has_operational_failure = False

    run()

    mock_set_output.assert_any_call("coverage-overall-passed", "True")
    mock_set_output.assert_any_call("coverage-changed-files-passed", "False")
    mock_set_failed.assert_called_once_with(messages=["Changed files coverage below threshold."], fail=True)


def _run_with_deltas(mocker: MockerFixture, overall_delta, changed_files_delta):
    mocker.patch("main.setup_logging")
    mocker.patch.object(ActionInputs, "validate_inputs")
    mock_jr = mocker.patch("main.JaCoCoReport").return_value
    mock_set_output = mocker.patch("main.set_action_output")
    mocker.patch("main.set_action_output_text")
    mocker.patch("sys.exit")
    mock_jr.total_overall_coverage_delta = overall_delta
    mock_jr.total_changed_files_coverage_delta = changed_files_delta
    mock_jr.violations = []

    run()

    return mock_set_output


def test_run_sets_delta_outputs_from_baseline(mocker: MockerFixture):
    mock_set_output = _run_with_deltas(mocker, -0.59, 1.5)

    mock_set_output.assert_any_call("coverage-overall-delta", "-0.59")
    mock_set_output.assert_any_call("coverage-changed-files-delta", "1.5")


def test_run_sets_empty_delta_outputs_without_baseline(mocker: MockerFixture):
    mock_set_output = _run_with_deltas(mocker, None, None)

    mock_set_output.assert_any_call("coverage-overall-delta", "")
    mock_set_output.assert_any_call("coverage-changed-files-delta", "")


def _patch_no_decrease_run(mocker: MockerFixture, fail_on_threshold: list[str]) -> tuple[MockType, MockType]:
    mocker.patch("main.setup_logging")
    mocker.patch.object(ActionInputs, "validate_inputs")
    mock_jr_cls = mocker.patch("main.JaCoCoReport")
    mocker.patch("main.set_action_output")
    mocker.patch("main.set_action_output_text")
    mock_set_action_failed = mocker.patch("main.set_action_failed")
    mocker.patch(
        "jacoco_report.action_inputs.ActionInputs.get_fail_on_threshold",
        return_value=fail_on_threshold,
    )
    mock_jr = mock_jr_cls.return_value
    mock_jr.total_overall_coverage = 70.0
    mock_jr.total_changed_files_coverage = 75.0
    mock_jr.evaluated_coverage_reports = "{}"
    mock_jr.evaluated_coverage_groups = "{}"
    mock_jr.reached_threshold_overall = True
    mock_jr.reached_threshold_changed_files_average = True
    mock_jr.reached_threshold_per_change_file = True
    mock_jr.reached_threshold_fail_unchanged = True
    mock_jr.has_operational_failure = False
    return mock_jr, mock_set_action_failed


def test_run_no_decrease_selected_fails_when_the_gate_is_not_reached(mocker: MockerFixture):
    mock_jr, mock_set_action_failed = _patch_no_decrease_run(mocker, [FailOnThresholdEnum.NO_DECREASE])
    mock_jr.violations = ["Global overall coverage dropped from 80.0 to 70.0."]
    mock_jr.reached_threshold_no_decrease = False

    run()

    mock_set_action_failed.assert_called_once_with(
        messages=["Global overall coverage dropped from 80.0 to 70.0."], fail=True
    )


def test_run_no_decrease_not_selected_does_not_fail_on_its_flag(mocker: MockerFixture):
    mock_jr, mock_set_action_failed = _patch_no_decrease_run(mocker, [FailOnThresholdEnum.OVERALL])
    mock_jr.violations = ["Global overall coverage dropped from 80.0 to 70.0."]
    mock_jr.reached_threshold_no_decrease = False

    run()

    mock_set_action_failed.assert_called_once_with(
        messages=["Global overall coverage dropped from 80.0 to 70.0."], fail=False
    )
