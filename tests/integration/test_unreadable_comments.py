"""
Integration test: an unreadable PR comment read keeps the action outputs and the threshold exit code.

With update-comment enabled, a failed comment read (get_comments returns None) must change no comment,
and the run still writes its outputs and exits by the thresholds alone.
"""

from __future__ import annotations

import pytest
import requests
from pytest_mock import MockerFixture

import main as jacoco_main
from tests.integration.helpers import (
    TEST_PROJECT_GLOB,
    capture_run,
    make_env_base,
    mock_github_offline,
)

_CHANGED_FILES = ["com/example/module_large/MidClass.java"]

_EXPECTED_OUTPUTS = {
    "coverage-overall",
    "coverage-changed-files",
    "coverage-overall-passed",
    "coverage-changed-files-passed",
    "reports-coverage",
    "groups-coverage",
}


@pytest.mark.parametrize(
    ("global_thresholds", "expected_exit_code"),
    [
        pytest.param("0.0*0.0", 0, id="thresholds-pass"),
        pytest.param("99.9*0.0", 1, id="overall-threshold-fails"),
    ],
)
def test_unreadable_comments_keep_outputs_and_threshold_exit_code(
    mocker: MockerFixture, global_thresholds: str, expected_exit_code: int
) -> None:
    captured = mock_github_offline(mocker, _CHANGED_FILES)
    mocker.patch("jacoco_report.utils.github.GitHub.get_comments", return_value=None)
    update_comment = mocker.patch("jacoco_report.utils.github.GitHub.update_comment")
    delete_comment = mocker.patch("jacoco_report.utils.github.GitHub.delete_comment")
    set_output = mocker.spy(jacoco_main, "set_action_output")
    set_output_text = mocker.spy(jacoco_main, "set_action_output_text")

    result = capture_run(
        make_env_base(
            INPUT_PATHS=TEST_PROJECT_GLOB,
            INPUT_UPDATE_COMMENT="true",
            INPUT_COMMENT_LEVEL="full",
            INPUT_GLOBAL_THRESHOLDS=global_thresholds,
        )
    )

    assert result.exit_code == expected_exit_code, (
        f"Unexpected exit code {result.exit_code} for thresholds {global_thresholds!r}.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    written = {call.args[0] for call in set_output.call_args_list} | {
        call.args[0] for call in set_output_text.call_args_list
    }
    assert written == _EXPECTED_OUTPUTS

    assert captured == []
    update_comment.assert_not_called()
    delete_comment.assert_not_called()


def _warning_lines(stdout: str) -> list[str]:
    return [line for line in stdout.splitlines() if line.startswith("::warning::")]


@pytest.mark.parametrize(
    ("global_thresholds", "expected_exit_code"),
    [
        pytest.param("0.0*0.0", 0, id="thresholds-pass"),
        pytest.param("99.9*0.0", 1, id="overall-threshold-fails"),
    ],
)
def test_unreadable_comments_emit_one_warning_and_keep_threshold_exit_code(
    mocker: MockerFixture, global_thresholds: str, expected_exit_code: int
) -> None:
    mock_github_offline(mocker, _CHANGED_FILES)
    mocker.patch("jacoco_report.utils.github.GitHub.get_comments", return_value=None)

    result = capture_run(
        make_env_base(
            INPUT_PATHS=TEST_PROJECT_GLOB,
            INPUT_UPDATE_COMMENT="true",
            INPUT_COMMENT_LEVEL="full",
            INPUT_GLOBAL_THRESHOLDS=global_thresholds,
        )
    )

    assert result.exit_code == expected_exit_code, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    warnings = _warning_lines(result.stdout)
    assert len(warnings) == 1, f"stdout:\n{result.stdout}"
    assert warnings[0] == (
        "::warning::The PR comment may not have been changed and may be out of date. See the job log for the error."
    )
    assert "PR comment(s) generated successfully." not in result.stdout


def test_failed_comment_add_emits_warning_and_no_success_line(mocker: MockerFixture) -> None:
    mock_github_offline(mocker, _CHANGED_FILES)
    mocker.patch("jacoco_report.utils.github.GitHub.add_comment", return_value=False)

    result = capture_run(
        make_env_base(
            INPUT_PATHS=TEST_PROJECT_GLOB,
            INPUT_UPDATE_COMMENT="false",
            INPUT_COMMENT_LEVEL="full",
            INPUT_GLOBAL_THRESHOLDS="0.0*0.0",
        )
    )

    assert result.exit_code == 0
    assert len(_warning_lines(result.stdout)) == 1
    assert "PR comment(s) generated successfully." not in result.stdout


def test_successful_comment_change_logs_success_and_no_warning(mocker: MockerFixture) -> None:
    captured = mock_github_offline(mocker, _CHANGED_FILES)

    result = capture_run(
        make_env_base(
            INPUT_PATHS=TEST_PROJECT_GLOB,
            INPUT_UPDATE_COMMENT="false",
            INPUT_COMMENT_LEVEL="full",
            INPUT_GLOBAL_THRESHOLDS="0.0*0.0",
        )
    )

    assert result.exit_code == 0
    assert len(captured) == 1
    assert _warning_lines(result.stdout) == []
    assert "PR comment(s) generated successfully." in result.stdout


def test_comment_level_none_without_update_comment_makes_no_call_and_no_warning(mocker: MockerFixture) -> None:
    mock_github_offline(mocker, _CHANGED_FILES)
    get_comments = mocker.patch("jacoco_report.utils.github.GitHub.get_comments")
    add_comment = mocker.patch("jacoco_report.utils.github.GitHub.add_comment")

    result = capture_run(
        make_env_base(
            INPUT_PATHS=TEST_PROJECT_GLOB,
            INPUT_UPDATE_COMMENT="false",
            INPUT_COMMENT_LEVEL="none",
            INPUT_GLOBAL_THRESHOLDS="0.0*0.0",
        )
    )

    assert result.exit_code == 0
    get_comments.assert_not_called()
    add_comment.assert_not_called()
    assert _warning_lines(result.stdout) == []
    assert "PR comment(s) generated successfully." in result.stdout


@pytest.mark.parametrize(
    ("global_thresholds", "expected_exit_code"),
    [
        pytest.param("0.0*0.0", 0, id="thresholds-pass"),
        pytest.param("99.9*0.0", 1, id="overall-threshold-fails"),
    ],
)
def test_unusable_update_response_warns_once_and_keeps_threshold_exit_code(
    mocker: MockerFixture, global_thresholds: str, expected_exit_code: int
) -> None:
    """The real update_comment runs: a 2xx PATCH with a non-JSON body changes nothing the run can read back."""
    mock_github_offline(mocker, _CHANGED_FILES)
    mocker.patch(
        "jacoco_report.utils.github.GitHub.get_comments",
        return_value=[{"id": 42, "body": "**JaCoCo Coverage Report**\n\nold coverage content"}],
    )
    response = requests.Response()
    response.status_code = 200
    response._content = b"<html>not json</html>"
    session_patch = mocker.patch("requests.Session.patch", return_value=response)
    set_output = mocker.spy(jacoco_main, "set_action_output")
    set_output_text = mocker.spy(jacoco_main, "set_action_output_text")

    result = capture_run(
        make_env_base(
            INPUT_PATHS=TEST_PROJECT_GLOB,
            INPUT_UPDATE_COMMENT="true",
            INPUT_COMMENT_LEVEL="full",
            INPUT_GLOBAL_THRESHOLDS=global_thresholds,
        )
    )

    session_patch.assert_called_once()
    assert result.exit_code == expected_exit_code, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    warnings = _warning_lines(result.stdout)
    assert len(warnings) == 1, f"stdout:\n{result.stdout}"
    assert "PR comment(s) generated successfully." not in result.stdout

    written = {call.args[0] for call in set_output.call_args_list} | {
        call.args[0] for call in set_output_text.call_args_list
    }
    assert written == _EXPECTED_OUTPUTS
