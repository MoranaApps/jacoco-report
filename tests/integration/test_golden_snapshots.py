"""
Golden snapshot tests for the full PR comment pipeline.

Each test runs the complete action end-to-end with mocked GitHub API calls and
compares the generated PR comment body to a stored snapshot file.

To regenerate all snapshot files (e.g. after intentional output changes):
    WRITE_SNAPSHOTS=1 pytest tests/integration/test_golden_snapshots.py -v
"""

from __future__ import annotations

import os
from pathlib import Path

from pytest_mock import MockerFixture

from tests.integration.helpers import (
    DATA_DIR,
    TEST_PROJECT_GLOB,
    capture_run,
    make_env_base,
    mock_github_offline,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_NOTIFICATION_GLOB = str(DATA_DIR / "test_project" / "context" / "notification" / "**" / "jacoco.xml")
_USER_INFO_GLOB = str(DATA_DIR / "test_project" / "context" / "user-info" / "**" / "jacoco.xml")

# Changed files for scenario 1: only module_large reports have changed files
_CHANGED_FILES_NO_GROUPS = [
    "com/example/module_large/MidClass.java",
    "com/example/module_large/BigClass.java",
]

# Changed files for scenario 2: one file per group
_CHANGED_FILES_WITH_GROUPS = [
    "com/example/notification/api/ApiClass.java",
    "com/example/user-info/controller/ControllerClass.java",
]

# Changed files for scenario 3: only module_large; all other reports are filtered by skip-unchanged
_CHANGED_FILES_SKIP_UNCHANGED = [
    "com/example/module_large/MidClass.java",
]

_REPORT_GROUPS_YAML = f"""\
- name: notification
  paths:
    - {_NOTIFICATION_GLOB}
- name: user-info
  paths:
    - {_USER_INFO_GLOB}
"""


def _assert_or_write_snapshot(scenario: str, actual: str) -> None:
    """Assert actual matches the stored snapshot, or write it when WRITE_SNAPSHOTS=1."""
    fixture_path = FIXTURES_DIR / f"snapshot_{scenario}.md"
    if os.environ.get("WRITE_SNAPSHOTS") == "1":
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(actual, encoding="utf-8")
        return
    assert fixture_path.exists(), (
        f"Snapshot '{fixture_path.name}' not found. "
        "Run with WRITE_SNAPSHOTS=1 to generate: "
        "WRITE_SNAPSHOTS=1 pytest tests/integration/test_golden_snapshots.py"
    )
    expected = fixture_path.read_text(encoding="utf-8")
    assert actual == expected, (
        f"PR comment output changed for scenario '{scenario}'. "
        "If this change is intentional, regenerate with: "
        "WRITE_SNAPSHOTS=1 pytest tests/integration/test_golden_snapshots.py"
    )


def test_snapshot_no_groups(mocker: MockerFixture) -> None:
    """Full comment: all reports loaded from TEST_PROJECT_GLOB, no groups configured.

    Two files from module_large appear as changed; all other reports have no changed files.
    """
    captured = mock_github_offline(mocker, _CHANGED_FILES_NO_GROUPS)

    env = make_env_base(
        INPUT_PATHS=TEST_PROJECT_GLOB,
        INPUT_COMMENT_LEVEL="full",
        INPUT_SKIP_UNCHANGED="false",
    )
    result = capture_run(env)

    assert result.exit_code == 0, (
        f"Action exited with code {result.exit_code}.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert len(captured) == 1, (
        f"Expected exactly one comment posted, got {len(captured)}.\n"
        f"stdout:\n{result.stdout}"
    )

    _assert_or_write_snapshot("no_groups", captured[0])


def test_snapshot_with_groups(mocker: MockerFixture) -> None:
    """Full comment: two report groups (notification, user-info), one changed file per group.

    The groups table appears between the global summary and the reports table.
    """
    captured = mock_github_offline(mocker, _CHANGED_FILES_WITH_GROUPS)

    env = make_env_base(
        INPUT_PATHS="",
        INPUT_REPORT_GROUPS=_REPORT_GROUPS_YAML,
        INPUT_COMMENT_LEVEL="full",
        INPUT_SKIP_UNCHANGED="false",
    )
    result = capture_run(env)

    assert result.exit_code == 0, (
        f"Action exited with code {result.exit_code}.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert len(captured) == 1, (
        f"Expected exactly one comment posted, got {len(captured)}.\n"
        f"stdout:\n{result.stdout}"
    )

    _assert_or_write_snapshot("with_groups", captured[0])


def test_snapshot_skip_unchanged(mocker: MockerFixture) -> None:
    """Full comment with skip-unchanged active.

    Only module_large has a changed file (MidClass.java).  All other eight reports
    are scan-stage filtered; evaluate-unchanged keeps their overall coverage in the
    global summary but hides them from the reports table rows.
    """
    captured = mock_github_offline(mocker, _CHANGED_FILES_SKIP_UNCHANGED)

    env = make_env_base(
        INPUT_PATHS=TEST_PROJECT_GLOB,
        INPUT_COMMENT_LEVEL="full",
        INPUT_SKIP_UNCHANGED="true",
        INPUT_EVALUATE_UNCHANGED="true",
    )
    result = capture_run(env)

    assert result.exit_code == 0, (
        f"Action exited with code {result.exit_code}.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert len(captured) == 1, (
        f"Expected exactly one comment posted, got {len(captured)}.\n"
        f"stdout:\n{result.stdout}"
    )

    _assert_or_write_snapshot("skip_unchanged", captured[0])
