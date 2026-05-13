# Copyright (c) MoranaApps
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests: skip-unchanged × comment-level matrix (Task 34).

Covers all 2 × 6 = 12 combinations of skip-unchanged × comment-level.
For skip-unchanged=true cases, the evaluate-unchanged=false branch is exercised:
unchanged reports are removed at the scan stage before CoverageEvaluator runs
and are fully excluded from both comment rows and global threshold evaluation.
For skip-unchanged=false cases, evaluate-unchanged has no effect.
"""

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from jacoco_report.utils.enums import CommentLevelEnum
from tests.integration.helpers import (
    TEST_PROJECT_GLOB,
    capture_run,
    make_env_base,
    mock_github_offline,
)

# Only module_large files are changed; all other reports have no changed files.
_CHANGED_FILES = ["com/example/module_large/MidClass.java"]

# Report that always survives the scan-stage filter (has a changed file).
_CHANGED_REPORT = "Module Large Report"

# Report that is filtered when skip-unchanged=true (no changed files).
_UNCHANGED_REPORT = "Module Small Report"

_COMMENT_LEVELS = [level.value for level in CommentLevelEnum]


@pytest.mark.parametrize("comment_level", _COMMENT_LEVELS)
def test_skip_unchanged_false_all_comment_levels(
    mocker: MockerFixture, comment_level: str
) -> None:
    """skip-unchanged=false: all reports reach evaluation for every comment level.

    Verifies:
    - Action completes without error for all 6 levels
    - 'none' suppresses the comment; all other levels post exactly one comment
    - 'full' level includes unchanged report rows (no scan-stage filter active)
    - 'changed' and 'failed-or-changed' levels include the report with changed files
    - 'failed' level emits 'No rows match' (all reports pass at 0% thresholds)
    """
    captured = mock_github_offline(mocker, _CHANGED_FILES)

    result = capture_run(
        make_env_base(
            INPUT_PATHS=TEST_PROJECT_GLOB,
            INPUT_SKIP_UNCHANGED="false",
            INPUT_COMMENT_LEVEL=comment_level,
        )
    )

    assert result.exit_code == 0, (
        f"[skip=false, level={comment_level!r}] Unexpected exit code {result.exit_code}.\n"
        f"stdout:\n{result.stdout}"
    )

    if comment_level == "none":
        assert len(captured) == 0, (
            f"[skip=false, level=none] comment-level=none must suppress the comment"
        )
    else:
        assert len(captured) == 1, (
            f"[skip=false, level={comment_level!r}] Expected one comment, got {len(captured)}"
        )

    if comment_level == "full":
        assert _UNCHANGED_REPORT in captured[0], (
            f"[skip=false, level=full] {_UNCHANGED_REPORT!r} must appear "
            f"(no filter applied — all reports reach evaluation)"
        )
        assert _CHANGED_REPORT in captured[0]

    if comment_level in ("changed", "failed-or-changed"):
        assert _CHANGED_REPORT in captured[0], (
            f"[skip=false, level={comment_level!r}] {_CHANGED_REPORT!r} must appear "
            f"(it has changed files)"
        )
        assert _UNCHANGED_REPORT not in captured[0], (
            f"[skip=false, level={comment_level!r}] {_UNCHANGED_REPORT!r} must be absent — "
            f"this level filters to rows with changed files only"
        )

    if comment_level == "failed":
        # At 0% thresholds all reports pass — no failing rows in tables.
        assert "No rows match the selected comment level." in captured[0], (
            f"[skip=false, level=failed] Expected 'No rows match' message "
            f"(all reports pass at 0% threshold)"
        )


@pytest.mark.parametrize("comment_level", _COMMENT_LEVELS)
def test_skip_unchanged_true_all_comment_levels(
    mocker: MockerFixture, comment_level: str
) -> None:
    """skip-unchanged=true + evaluate-unchanged=false: unchanged reports filtered before evaluation.

    Verifies:
    - Action completes without error for all 6 levels
    - 'none' suppresses the comment; all other levels post exactly one comment
    - Log output confirms reports are filtered at the scan stage (before evaluation)
    - 'full' level does NOT include unchanged report rows (filter-before-evaluation)
    - 'changed' and 'failed-or-changed' include the report with changed files
    - 'failed' emits 'No rows match' (the surviving report passes at 0% threshold)
    """
    captured = mock_github_offline(mocker, _CHANGED_FILES)

    result = capture_run(
        make_env_base(
            INPUT_PATHS=TEST_PROJECT_GLOB,
            INPUT_SKIP_UNCHANGED="true",
            INPUT_EVALUATE_UNCHANGED="false",
            INPUT_COMMENT_LEVEL=comment_level,
        )
    )

    assert result.exit_code == 0, (
        f"[skip=true, level={comment_level!r}] Unexpected exit code {result.exit_code}.\n"
        f"stdout:\n{result.stdout}"
    )

    # Scan-stage filter log must appear — confirms filter runs before evaluation.
    assert "Filtering report" in result.stdout, (
        f"[skip=true, level={comment_level!r}] Expected scan-stage filter log in stdout; "
        f"Module Small Report (and others) have no changed files and must be filtered."
    )

    if comment_level == "none":
        assert len(captured) == 0, (
            f"[skip=true, level=none] comment-level=none must suppress the comment"
        )
    else:
        assert len(captured) == 1, (
            f"[skip=true, level={comment_level!r}] Expected one comment, got {len(captured)}"
        )

    if comment_level == "full":
        assert _UNCHANGED_REPORT not in captured[0], (
            f"[skip=true, level=full] {_UNCHANGED_REPORT!r} must be absent — "
            f"filter-before-evaluation: removed at scan stage, not inside comment generator"
        )
        assert _CHANGED_REPORT in captured[0], (
            f"[skip=true, level=full] {_CHANGED_REPORT!r} must appear "
            f"(survived scan-stage filter — has changed files)"
        )

    if comment_level in ("changed", "failed-or-changed"):
        assert _CHANGED_REPORT in captured[0], (
            f"[skip=true, level={comment_level!r}] {_CHANGED_REPORT!r} must appear "
            f"(has changed files, survived filter)"
        )

    if comment_level == "failed":
        # At 0% thresholds the surviving report (module_large) passes — no failing rows.
        assert "No rows match the selected comment level." in captured[0], (
            f"[skip=true, level=failed] Expected 'No rows match' message "
            f"(module_large passes at 0% threshold)"
        )


def test_filter_before_evaluation_changes_global_coverage(mocker: MockerFixture) -> None:
    """Global coverage summary differs between skip-unchanged=false and skip-unchanged=true.

    With skip-unchanged=false all reports contribute to the global totals.
    With skip-unchanged=true + evaluate-unchanged=false only the changed report contributes.

    The minimal-level comment bodies must differ, proving the filter runs before the
    CoverageEvaluator rather than inside the comment generator.
    """
    # Run 1: no filter — all reports in evaluator.
    captured_all = mock_github_offline(mocker, _CHANGED_FILES)
    r1 = capture_run(
        make_env_base(
            INPUT_PATHS=TEST_PROJECT_GLOB,
            INPUT_SKIP_UNCHANGED="false",
            INPUT_COMMENT_LEVEL="minimal",
        )
    )
    assert r1.exit_code == 0, f"Run 1 failed: {r1.stdout}"
    assert len(captured_all) == 1, f"Expected one comment in run 1, got {len(captured_all)}"

    # Run 2: scan-stage filter active — only module_large in evaluator.
    captured_filtered = mock_github_offline(mocker, _CHANGED_FILES)
    r2 = capture_run(
        make_env_base(
            INPUT_PATHS=TEST_PROJECT_GLOB,
            INPUT_SKIP_UNCHANGED="true",
            INPUT_EVALUATE_UNCHANGED="false",
            INPUT_COMMENT_LEVEL="minimal",
        )
    )
    assert r2.exit_code == 0, f"Run 2 failed: {r2.stdout}"
    assert len(captured_filtered) == 1, f"Expected one comment in run 2, got {len(captured_filtered)}"

    assert captured_all[0] != captured_filtered[0], (
        "Global coverage summary must differ between skip-unchanged=false (all reports evaluated) "
        "and skip-unchanged=true (only the changed report evaluated). "
        "Matching bodies would indicate the filter is not running before the evaluator."
    )
