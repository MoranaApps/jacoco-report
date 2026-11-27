"""
Offline integration tests: a baseline whose metadata does not name baseline-sha skips the 'no-decrease' gate.

GitHub is mocked. The baseline is the test project's own fixture, so 'Module Large Report' drops against it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

from pytest_mock import MockerFixture

import main as jacoco_main
from jacoco_report.evaluator.baseline_verification import UNVERIFIED_BASELINE_NOTE
from tests.integration.helpers import (
    BASELINE_PROJECT_GLOB,
    TEST_PROJECT_GLOB,
    capture_run,
    make_env_base,
    mock_github_offline,
)

_CHANGED_FILES = ["com/example/module_large/MidClass.java", "com/example/module_large/BigClass.java"]
_EXPECTED_SHA = "a" * 40
_OTHER_SHA = "b" * 40


def _write_metadata(tmp_path: Path, sha: str) -> str:
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps({"sha": sha}), encoding="utf-8")
    return str(metadata)


def _warning_lines(stdout: str) -> list[str]:
    return [line for line in stdout.splitlines() if line.startswith("::warning::")]


def test_unverified_baseline_passes_no_decrease_warns_and_shows_the_note(mocker: MockerFixture, tmp_path: Path) -> None:
    mock_github_offline(mocker, _CHANGED_FILES)
    add_comment = cast(MagicMock, mocker.patch("jacoco_report.utils.github.GitHub.add_comment", return_value=True))
    mocker.patch("jacoco_report.utils.github.GitHub.get_comments", return_value=[])
    set_output = mocker.spy(jacoco_main, "set_action_output")
    metadata = _write_metadata(tmp_path, _OTHER_SHA)

    result = capture_run(
        make_env_base(
            INPUT_PATHS=TEST_PROJECT_GLOB,
            INPUT_BASELINE_PATHS=BASELINE_PROJECT_GLOB,
            INPUT_FAIL_ON_THRESHOLD="no-decrease",
            INPUT_UPDATE_COMMENT="false",
            INPUT_BASELINE_SHA=_EXPECTED_SHA,
            INPUT_BASELINE_METADATA_PATH=metadata,
        )
    )

    assert result.exit_code == 0, result.stdout
    assert _warning_lines(result.stdout) == [
        "::warning::Unverified baseline: metadata file "
        f"'{metadata}' names commit {_OTHER_SHA}, but baseline-sha is {_EXPECTED_SHA}. "
        "The Δ against it is informational, and 'no-decrease' skips it."
    ]
    assert UNVERIFIED_BASELINE_NOTE in add_comment.call_args[0][1]
    set_output.assert_any_call("baseline-verified", "false")


def test_no_baseline_report_still_fails_no_decrease_when_verification_is_configured(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    mock_github_offline(mocker, _CHANGED_FILES)
    mocker.patch("jacoco_report.utils.github.GitHub.get_comments", return_value=[])
    mocker.patch("jacoco_report.utils.github.GitHub.add_comment", return_value=True)
    metadata = _write_metadata(tmp_path, _OTHER_SHA)

    result = capture_run(
        make_env_base(
            INPUT_PATHS=TEST_PROJECT_GLOB,
            INPUT_BASELINE_PATHS="",
            INPUT_FAIL_ON_THRESHOLD="no-decrease",
            INPUT_UPDATE_COMMENT="false",
            INPUT_BASELINE_SHA=_EXPECTED_SHA,
            INPUT_BASELINE_METADATA_PATH=metadata,
        )
    )

    assert result.exit_code == 1, result.stdout
    assert "'no-decrease' needs a baseline, but no baseline report was found." in result.stdout
