"""
Integration test helpers for jacoco-report action tests.

Provides capture_run() for running the full action pipeline in-process
and fixture-assembly helpers for constructing canonical env var inputs.

Fixture roots used by this module:
- TEST_PROJECT_GLOB reads main fixtures from tests/data/test_project/**/jacoco.xml
- BASELINE_PROJECT_GLOB reads baseline fixtures from tests/data_baseline/test_project/**/jacoco.xml
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path

from pytest_mock import MockerFixture

TESTS_DIR: Path = Path(__file__).parent.parent
DATA_DIR: Path = TESTS_DIR / "data"
TEST_PROJECT_GLOB: str = str(DATA_DIR / "test_project" / "**" / "jacoco.xml")
BASELINE_PROJECT_GLOB: str = str(TESTS_DIR / "data_baseline" / "test_project" / "**" / "jacoco.xml")


@dataclass
class ActionResult:
    """Captured outcome of a single capture_run invocation."""

    exit_code: int
    stdout: str
    stderr: str


def capture_run(env_overrides: dict[str, str]) -> ActionResult:
    """
    Run the full action pipeline with env_overrides applied to os.environ.

    Environment isolation performed before each run:
    - All pre-existing INPUT_* and GITHUB_* keys are deleted from os.environ
      so that ambient CI variables cannot bleed into the run.
    - GITHUB_OUTPUT is always set to an internally managed temp file,
      regardless of any value supplied in env_overrides, so that action-output
      side effects are fully contained and cleaned up after the call.

    Redirects stdout/stderr and resets root-logger handlers so that
    setup_logging() emits to the captured stream. Catches SystemExit and
    records its code.

    GitHub API calls must be mocked by the caller (via pytest-mock) before
    invoking this function for offline tests.
    """
    import main as jacoco_main  # local import avoids module-level side-effects

    original_env = dict(os.environ)
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    root_logger = logging.getLogger()
    saved_handlers: list[logging.Handler] = root_logger.handlers[:]
    saved_level: int = root_logger.level
    for h in saved_handlers:
        root_logger.removeHandler(h)

    exit_code = 0
    tmp_output_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp_output_path = tmp.name

        for key in [
            env_key
            for env_key in os.environ
            if env_key.startswith("INPUT_") or env_key.startswith("GITHUB_")
        ]:
            del os.environ[key]

        os.environ.update(env_overrides)
        os.environ["GITHUB_OUTPUT"] = tmp_output_path

        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            try:
                jacoco_main.run()
            except SystemExit as exc:
                exit_code = int(exc.code) if exc.code is not None else 0
    finally:
        captured_handlers: list[logging.Handler] = root_logger.handlers[:]
        for h in captured_handlers:
            root_logger.removeHandler(h)
        for h in captured_handlers:
            if h not in saved_handlers:
                h.close()
        for h in saved_handlers:
            root_logger.addHandler(h)
        root_logger.setLevel(saved_level)
        os.environ.clear()
        os.environ.update(original_env)
        if tmp_output_path and os.path.exists(tmp_output_path):
            os.unlink(tmp_output_path)

    return ActionResult(
        exit_code=exit_code,
        stdout=stdout_buf.getvalue(),
        stderr=stderr_buf.getvalue(),
    )


def make_env_base(**overrides: str) -> dict[str, str]:
    """
    Return a minimal env var dict for offline integration tests.

    Provides sensible defaults for all action inputs. The fake token
    satisfies the format check in validate_inputs(). GitHub API calls
    must still be mocked by the caller via pytest-mock.

    Any keyword argument overrides the corresponding default key.
    """
    env: dict[str, str] = {
        # GitHub-injected vars (no INPUT_ prefix)
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_RUN_ID": "1111111111",
        "GITHUB_RUN_STARTED_AT": "2025-01-01T00:00:00Z",
        "GITHUB_ACTION_REF": "v3.0.0",
        # Action inputs
        "INPUT_TOKEN": "ghs_" + "x" * 36,
        "INPUT_PATHS": TEST_PROJECT_GLOB,
        "INPUT_EXCLUDE_PATHS": "",
        "INPUT_GLOBAL_THRESHOLDS": "0.0*0.0",
        "INPUT_REPORT_THRESHOLDS_DEFAULT": "0.0*0.0",
        "INPUT_METRIC": "instruction",
        "INPUT_PR_NUMBER": "1",
        "INPUT_TITLE": "JaCoCo Coverage Report",
        "INPUT_COMMENT_LEVEL": "full",
        "INPUT_SKIP_UNCHANGED": "false",
        "INPUT_EVALUATE_UNCHANGED": "true",
        "INPUT_UPDATE_COMMENT": "false",
        "INPUT_FAIL_ON_THRESHOLD": "overall,changed-files-average,per-changed-file",
        "INPUT_PASS_SYMBOL": "✅",
        "INPUT_FAIL_SYMBOL": "❌",
        "INPUT_DEBUG": "false",
        "INPUT_BASELINE_PATHS": "",
        "INPUT_REPORT_GROUPS": "",
    }
    env.update(overrides)
    return env


def mock_github_offline(mocker: MockerFixture, changed_files: list[str]) -> list[str]:
    """Patch GitHub API calls for offline integration tests.

    Parameters
    ----------
    mocker
        pytest-mock fixture used to patch GitHub client methods.
    changed_files
        Changed file paths returned by the mocked pull-request changed-files API.

    Returns
    -------
    list[str]
        Mutable list that accumulates posted PR comment bodies.
    """
    mocker.patch(
        "jacoco_report.utils.github.GitHub.get_pr_changed_files",
        return_value=changed_files,
    )
    mocker.patch(
        "jacoco_report.utils.github.GitHub.get_comments",
        return_value=[],
    )
    captured: list[str] = []
    mocker.patch(
        "jacoco_report.utils.github.GitHub.add_comment",
        side_effect=lambda pr_number, body: captured.append(body) or True,
    )
    return captured
