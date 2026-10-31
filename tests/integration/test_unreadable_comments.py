"""
Integration test: an unreadable PR comment read keeps the action outputs and the threshold exit code.

With update-comment enabled, a failed comment read (get_comments returns None) must change no comment,
and the run still writes its outputs and exits by the thresholds alone.
"""

from __future__ import annotations

import pytest
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
