"""
Integration test: a Maven jacoco:report-aggregate report, which wraps each module's packages in a <group>.
"""

from __future__ import annotations

import re

from pytest_mock import MockerFixture

from tests.integration.helpers import DATA_DIR, capture_run, make_env_base, mock_github_offline

_AGGREGATE_REPORT = str(DATA_DIR / "report_aggregate" / "jacoco.xml")

_CHANGED_FILES = ["module-a/src/main/java/com/example/aggregate/alpha/AlphaService.java"]


def test_report_aggregate_changed_file_is_evaluated(mocker: MockerFixture) -> None:
    """The changed file inside a <group> is listed and checked against the per-changed-file threshold."""
    captured = mock_github_offline(mocker, _CHANGED_FILES)

    env = make_env_base(
        INPUT_PATHS=_AGGREGATE_REPORT,
        INPUT_REPORT_THRESHOLDS_DEFAULT="0.0*0.0*80.0",
    )
    result = capture_run(env)

    assert len(captured) == 1, f"Expected exactly one comment posted, got {len(captured)}.\nstdout:\n{result.stdout}"
    comment_body = captured[0]
    assert re.search(r"\| \*\*Changed Files\*\* \| 75\.0% \|", comment_body), comment_body
    assert re.search(r"\| \[AlphaService\.java\]\([^)]*\) \| 75\.0% \| 80\.0% \| ❌ \|", comment_body), comment_body
    assert "BetaRepository.java" not in comment_body
    assert result.exit_code != 0, "per-changed-file threshold (80%) must fail for AlphaService.java (75%)"
