"""
Tests for the skip-unchanged scan-stage filter (Task 27 / issue #112).

Covers:
- Filter removes reports with no changed files before evaluation
- INFO log emitted per filtered report
- All-reports-filtered → clean exit, no comment, no violations
- comment-level × skip-unchanged combinations across all supported levels
- fail-on-threshold boolean deprecation warning
"""
import logging

import pytest
from pytest_mock import MockerFixture

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.generator.pr_comment_generator import PRCommentGenerator
from jacoco_report.jacoco_report import JaCoCoReport
from jacoco_report.model.counter import Counter
from jacoco_report.model.file_coverage import FileCoverage
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.utils.enums import CommentLevelEnum


# --- helpers ---

def _make_run_mocks(
    mocker: MockerFixture,
    *,
    skip_unchanged: bool,
    evaluate_unchanged: bool,
    fail_on_threshold: list[str] | None = None,
    reports: list[ReportFileCoverage],
) -> dict:
    """Patch the minimum surface needed to exercise JaCoCoReport.run()."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value="pull_request")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_token", return_value="token")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_pr_number", return_value=1)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_paths", return_value=["**/jacoco.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_exclude_paths", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value=skip_unchanged)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_evaluate_unchanged", return_value=evaluate_unchanged)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_level", return_value=CommentLevelEnum.FULL)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[])
    mocker.patch(
        "jacoco_report.action_inputs.ActionInputs.get_fail_on_threshold",
        return_value=fail_on_threshold if fail_on_threshold is not None else ["overall", "changed-files-average", "per-changed-file"],
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="JaCoCo")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=False)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_pass_symbol", return_value="✅")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_fail_symbol", return_value="❌")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_repository", return_value="owner/repo")

    gh_mock = mocker.Mock()
    gh_mock.get_pr_changed_files.return_value = ["src/Foo.java"]
    gh_mock.get_comments.return_value = []
    mocker.patch("jacoco_report.jacoco_report.GitHub", return_value=gh_mock)

    n = len(reports)
    mocker.patch.object(JaCoCoReport, "scan_jacoco_xml_files", side_effect=lambda paths, exclude_paths: (
        [f"dummy_{i}.xml" for i in range(n)] if paths else []
    ))

    parser_mock = mocker.patch("jacoco_report.jacoco_report.JaCoCoReportParser")
    instance = parser_mock.return_value
    instance.parse.side_effect = reports

    return {"gh": gh_mock}


def _report_with_changes(name: str, make_report_file_coverage) -> ReportFileCoverage:
    fc = FileCoverage("Foo.java", "src", Counter(0, 10), Counter(0, 10), Counter(0, 10),
                      Counter(0, 10), Counter(0, 10), Counter(0, 10))
    return make_report_file_coverage(path=f"{name}.xml", name=name, changed_files_coverage={"src/Foo.java": fc})


def _report_without_changes(name: str, make_report_file_coverage) -> ReportFileCoverage:
    return make_report_file_coverage(path=f"{name}.xml", name=name, changed_files_coverage={})


# --- scan-stage filter tests ---

def test_skip_unchanged_filters_report_with_no_changed_files(
    mocker: MockerFixture, make_report_file_coverage, caplog
):
    unchanged = _report_without_changes("Report A", make_report_file_coverage)
    changed = _report_with_changes("Report B", make_report_file_coverage)

    _make_run_mocks(mocker, skip_unchanged=True, evaluate_unchanged=False, reports=[unchanged, changed])

    with caplog.at_level(logging.INFO, logger="jacoco_report.jacoco_report"):
        JaCoCoReport().run()

    assert "Filtering report 'Report A' from evaluation and comment rows: no changed files." in caplog.text
    assert "Filtering report 'Report B'" not in caplog.text


def test_skip_unchanged_logs_each_filtered_report(mocker: MockerFixture, make_report_file_coverage, caplog):
    unchanged_a = _report_without_changes("Alpha Report", make_report_file_coverage)
    unchanged_b = _report_without_changes("Beta Report", make_report_file_coverage)
    changed = _report_with_changes("Gamma Report", make_report_file_coverage)

    _make_run_mocks(mocker, skip_unchanged=True, evaluate_unchanged=False, reports=[unchanged_a, unchanged_b, changed])

    with caplog.at_level(logging.INFO, logger="jacoco_report.jacoco_report"):
        JaCoCoReport().run()

    messages = caplog.text
    assert "Filtering report 'Alpha Report' from evaluation and comment rows: no changed files." in messages
    assert "Filtering report 'Beta Report' from evaluation and comment rows: no changed files." in messages
    assert "Filtering report 'Gamma Report'" not in messages


def test_skip_unchanged_evaluate_unchanged_true_logs_threshold_result_clarification(
    mocker: MockerFixture, make_report_file_coverage, caplog
):
    unchanged = _report_without_changes("Report A", make_report_file_coverage)
    _make_run_mocks(mocker, skip_unchanged=True, evaluate_unchanged=True, reports=[unchanged])

    with caplog.at_level(logging.INFO, logger="jacoco_report.jacoco_report"):
        JaCoCoReport().run()

    assert (
        "Filtering report 'Report A' from comment rows and changed-files evaluation: no changed files "
        "(overall threshold checks may still apply)." in caplog.text
    )


def test_skip_unchanged_all_filtered_exits_cleanly(mocker: MockerFixture, make_report_file_coverage, caplog):
    unchanged_a = _report_without_changes("Report A", make_report_file_coverage)
    unchanged_b = _report_without_changes("Report B", make_report_file_coverage)

    mocks = _make_run_mocks(mocker, skip_unchanged=True, evaluate_unchanged=False, reports=[unchanged_a, unchanged_b])

    with caplog.at_level(logging.INFO, logger="jacoco_report.jacoco_report"):
        jr = JaCoCoReport()
        jr.run()

    assert "All reports filtered out by skip-unchanged" in caplog.text
    mocks["gh"].add_comment.assert_not_called()
    assert jr.violations == []
    assert jr.total_overall_coverage_passed is True
    assert jr.total_changed_files_coverage_passed is True
    assert jr.evaluated_coverage_reports == "{}"
    assert jr.evaluated_coverage_groups == "{}"


def test_skip_unchanged_all_filtered_deletes_stale_comment(mocker: MockerFixture, make_report_file_coverage, caplog):
    unchanged = _report_without_changes("Report A", make_report_file_coverage)
    mocks = _make_run_mocks(mocker, skip_unchanged=True, evaluate_unchanged=False, reports=[unchanged])

    mocks["gh"].get_comments.return_value = [{"id": 99, "body": "**JaCoCo**\n\nsome old content"}]
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=True)

    with caplog.at_level(logging.INFO, logger="jacoco_report.jacoco_report"):
        JaCoCoReport().run()

    mocks["gh"].delete_comment.assert_called_once_with(99)
    assert "Deleted stale comment" in caplog.text


def test_skip_unchanged_all_filtered_no_delete_when_update_comment_false(
    mocker: MockerFixture, make_report_file_coverage
):
    unchanged = _report_without_changes("Report A", make_report_file_coverage)
    mocks = _make_run_mocks(mocker, skip_unchanged=True, evaluate_unchanged=False, reports=[unchanged])

    mocks["gh"].get_comments.return_value = [{"id": 99, "body": "**JaCoCo**\n\nsome old content"}]

    JaCoCoReport().run()

    mocks["gh"].delete_comment.assert_not_called()


def test_skip_unchanged_false_does_not_filter(mocker: MockerFixture, make_report_file_coverage):
    unchanged = _report_without_changes("Report A", make_report_file_coverage)
    _make_run_mocks(mocker, skip_unchanged=False, evaluate_unchanged=False, reports=[unchanged])

    jr = JaCoCoReport()
    jr.run()

    # run completed without early exit; unchanged report was evaluated (no violations at 0% thresholds)
    assert jr.violations == []


def test_skip_unchanged_all_filtered_evaluate_unchanged_true_checks_overall_threshold(
    mocker: MockerFixture,
    make_report_file_coverage,
    make_coverage,
):
    low_overall = make_coverage(instruction=Counter(missed=10, covered=0))
    unchanged = make_report_file_coverage(
        name="Low Report",
        overall_coverage=low_overall,
        changed_files_coverage={},
    )
    mocks = _make_run_mocks(
        mocker,
        skip_unchanged=True,
        evaluate_unchanged=True,
        reports=[unchanged],
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_thresholds_default", return_value=(50.0, 0.0, 0.0))

    jr = JaCoCoReport()
    jr.run()

    assert any("Report 'Low Report' overall coverage 0.0 is below the threshold 50.0." in v for v in jr.violations)
    mocks["gh"].add_comment.assert_not_called()


def test_skip_unchanged_all_filtered_evaluate_unchanged_true_uses_unchanged_reports_for_global_threshold(
    mocker: MockerFixture,
    make_report_file_coverage,
    make_coverage,
):
    high_overall = make_coverage(instruction=Counter(missed=0, covered=10))
    unchanged = make_report_file_coverage(
        name="High Report",
        overall_coverage=high_overall,
        changed_files_coverage={},
    )
    _make_run_mocks(
        mocker,
        skip_unchanged=True,
        evaluate_unchanged=True,
        reports=[unchanged],
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=50.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_thresholds_default", return_value=(0.0, 0.0, 0.0))

    jr = JaCoCoReport()
    jr.run()

    assert jr.total_overall_coverage == 100.0
    assert jr.total_overall_coverage_passed is True
    assert not any("Global overall coverage" in violation for violation in jr.violations)


def test_skip_unchanged_all_filtered_evaluate_unchanged_true_still_fails_global_when_unchanged_totals_below_threshold(
    mocker: MockerFixture,
    make_report_file_coverage,
    make_coverage,
):
    low_overall = make_coverage(instruction=Counter(missed=10, covered=0))
    unchanged = make_report_file_coverage(
        name="Low Report",
        overall_coverage=low_overall,
        changed_files_coverage={},
    )
    _make_run_mocks(
        mocker,
        skip_unchanged=True,
        evaluate_unchanged=True,
        reports=[unchanged],
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=50.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_thresholds_default", return_value=(0.0, 0.0, 0.0))

    jr = JaCoCoReport()
    jr.run()

    assert jr.total_overall_coverage == 0.0
    assert jr.total_overall_coverage_passed is False
    assert any("Global overall coverage 0.0 is below the threshold 50.0." in v for v in jr.violations)


def test_skip_unchanged_all_filtered_evaluate_unchanged_true_deletes_stale_comment(
    mocker: MockerFixture,
    make_report_file_coverage,
):
    unchanged = _report_without_changes("Report A", make_report_file_coverage)
    mocks = _make_run_mocks(mocker, skip_unchanged=True, evaluate_unchanged=True, reports=[unchanged])

    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_thresholds_default", return_value=(0.0, 0.0, 0.0))
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=True)
    mocks["gh"].get_comments.return_value = [{"id": 100, "body": "**JaCoCo**\n\nsome old content"}]

    JaCoCoReport().run()

    mocks["gh"].delete_comment.assert_called_once_with(100)


def test_skip_unchanged_evaluate_unchanged_true_checks_filtered_report_in_mixed_input(
    mocker: MockerFixture,
    make_report_file_coverage,
    make_coverage,
):
    low_overall = make_coverage(instruction=Counter(missed=10, covered=0))
    unchanged = make_report_file_coverage(
        name="Low Report",
        overall_coverage=low_overall,
        changed_files_coverage={},
    )
    changed = _report_with_changes("Changed Report", make_report_file_coverage)
    mocks = _make_run_mocks(
        mocker,
        skip_unchanged=True,
        evaluate_unchanged=True,
        reports=[unchanged, changed],
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_thresholds_default", return_value=(50.0, 0.0, 0.0))

    jr = JaCoCoReport()
    jr.run()

    assert any("Report 'Low Report' overall coverage 0.0 is below the threshold 50.0." in v for v in jr.violations)
    mocks["gh"].add_comment.assert_called_once()


def test_skip_unchanged_evaluate_unchanged_true_mixed_input_uses_all_reports_for_global_result(
    mocker: MockerFixture,
    make_report_file_coverage,
    make_coverage,
):
    unchanged_low = make_report_file_coverage(
        path="unchanged-low.xml",
        name="Unchanged Low",
        overall_coverage=make_coverage(instruction=Counter(missed=10, covered=0)),
        changed_files_coverage={},
    )
    changed_high = make_report_file_coverage(
        path="changed-high.xml",
        name="Changed High",
        overall_coverage=make_coverage(instruction=Counter(missed=0, covered=10)),
        changed_files_coverage={
            "src/Foo.java": FileCoverage(
                "Foo.java",
                "src",
                Counter(0, 10),
                Counter(0, 10),
                Counter(0, 10),
                Counter(0, 10),
                Counter(0, 10),
                Counter(0, 10),
            )
        },
    )

    _make_run_mocks(
        mocker,
        skip_unchanged=True,
        evaluate_unchanged=True,
        reports=[unchanged_low, changed_high],
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=80.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_thresholds_default", return_value=(0.0, 0.0, 0.0))

    jr = JaCoCoReport()
    jr.run()

    assert jr.total_overall_coverage == 50.0
    assert jr.total_overall_coverage_passed is False
    assert any("Global overall coverage 50.0 is below the threshold 80.0." in v for v in jr.violations)
    assert "Unchanged Low" in jr.evaluated_coverage_reports
    assert "Changed High" in jr.evaluated_coverage_reports


@pytest.mark.parametrize("evaluate_unchanged", [False, True])
def test_skip_unchanged_false_no_regression_when_toggling_evaluate_unchanged(
    mocker: MockerFixture,
    make_report_file_coverage,
    evaluate_unchanged: bool,
):
    unchanged = _report_without_changes("Report A", make_report_file_coverage)
    _make_run_mocks(
        mocker,
        skip_unchanged=False,
        evaluate_unchanged=evaluate_unchanged,
        reports=[unchanged],
    )

    jr = JaCoCoReport()
    jr.run()

    assert jr.violations == []


def test_skip_unchanged_all_filtered_evaluate_unchanged_true_serializes_reports_to_output(
    mocker: MockerFixture,
    make_report_file_coverage,
    make_coverage,
):
    """When all reports are filtered and evaluate-unchanged=true, evaluated_coverage_reports is populated."""
    unchanged = make_report_file_coverage(
        name="Unchanged Report",
        overall_coverage=make_coverage(instruction=Counter(missed=0, covered=10)),
        changed_files_coverage={},
    )
    _make_run_mocks(
        mocker,
        skip_unchanged=True,
        evaluate_unchanged=True,
        reports=[unchanged],
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_thresholds_default", return_value=(0.0, 0.0, 0.0))

    jr = JaCoCoReport()
    jr.run()

    assert "Unchanged Report" in jr.evaluated_coverage_reports
    assert jr.evaluated_coverage_reports != "{}"


def test_skip_unchanged_true_fail_unchanged_enabled_evaluates_filtered_reports(
    mocker: MockerFixture,
    make_report_file_coverage,
    make_coverage,
):
    low_overall = make_coverage(instruction=Counter(missed=10, covered=0))
    unchanged = make_report_file_coverage(
        name="Low Report",
        overall_coverage=low_overall,
        changed_files_coverage={},
    )
    _make_run_mocks(
        mocker,
        skip_unchanged=True,
        evaluate_unchanged=False,
        fail_on_threshold=["fail-unchanged"],
        reports=[unchanged],
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_thresholds_default", return_value=(50.0, 0.0, 0.0))

    jr = JaCoCoReport()
    jr.run()

    assert any("Report 'Low Report' overall coverage 0.0 is below the threshold 50.0." in v for v in jr.violations)
    assert jr.reached_threshold_fail_unchanged is False


def test_skip_unchanged_true_fail_unchanged_disabled_excludes_filtered_reports(
    mocker: MockerFixture,
    make_report_file_coverage,
    make_coverage,
):
    low_overall = make_coverage(instruction=Counter(missed=10, covered=0))
    unchanged = make_report_file_coverage(
        name="Low Report",
        overall_coverage=low_overall,
        changed_files_coverage={},
    )
    _make_run_mocks(
        mocker,
        skip_unchanged=True,
        evaluate_unchanged=False,
        fail_on_threshold=["overall"],
        reports=[unchanged],
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_thresholds_default", return_value=(50.0, 0.0, 0.0))

    jr = JaCoCoReport()
    jr.run()

    assert not any("Report 'Low Report' overall coverage 0.0 is below the threshold 50.0." in v for v in jr.violations)
    assert jr.reached_threshold_fail_unchanged is True


def test_operational_failure_marks_fail_unchanged_flag_false(mocker: MockerFixture):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value="pull_request")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_token", return_value="token")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_pr_number", return_value=1)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_paths", return_value=["**/jacoco.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_exclude_paths", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_fail_on_threshold", return_value=["fail-unchanged"])

    gh_mock = mocker.Mock()
    gh_mock.get_pr_changed_files.return_value = None
    mocker.patch("jacoco_report.jacoco_report.GitHub", return_value=gh_mock)
    mocker.patch.object(JaCoCoReport, "scan_jacoco_xml_files", return_value=["dummy.xml"])

    jr = JaCoCoReport()
    jr.run()

    assert jr.has_operational_failure is True
    assert jr.reached_threshold_fail_unchanged is False
    assert "Failed to retrieve changed files from GitHub API." in jr.violations


def test_skip_unchanged_fail_unchanged_mixed_flow_uses_single_evaluator_pass(
    mocker: MockerFixture,
    make_report_file_coverage,
):
    unchanged = _report_without_changes("Unchanged Report", make_report_file_coverage)
    changed = _report_with_changes("Changed Report", make_report_file_coverage)

    _make_run_mocks(
        mocker,
        skip_unchanged=True,
        evaluate_unchanged=False,
        fail_on_threshold=["fail-unchanged"],
        reports=[unchanged, changed],
    )

    evaluate_spy = mocker.spy(CoverageEvaluator, "evaluate")

    jr = JaCoCoReport()
    jr.run()

    assert evaluate_spy.call_count == 1
    assert jr.reached_threshold_fail_unchanged is True


# --- comment-level × skip-unchanged combinations ---
#
# 2 (skip-unchanged: true / false) × 6 comment levels = 12 cases.

@pytest.fixture
def evaluator_with_changed(make_report_file_coverage, make_file_coverage):
    fc = make_file_coverage(instruction=Counter(missed=0, covered=10))
    rfc = make_report_file_coverage(changed_files_coverage={"src/Foo.java": fc})
    ce = CoverageEvaluator(
        report_files_coverage=[rfc],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
    )
    ce.evaluate()
    return ce


@pytest.fixture
def gh_mock(mocker: MockerFixture):
    m = mocker.Mock()
    m.get_comments.return_value = []
    return m


@pytest.mark.parametrize("skip_unchanged,comment_level", [
    (False, "none"),
    (False, "minimal"),
    (False, "full"),
    (False, "changed"),
    (False, "failed"),
    (False, "failed-or-changed"),
    (True, "none"),
    (True, "minimal"),
    (True, "full"),
    (True, "changed"),
    (True, "failed"),
    (True, "failed-or-changed"),
])
def test_comment_level_x_skip_unchanged_comment_posted(
    mocker: MockerFixture,
    gh_mock,
    evaluator_with_changed,
    skip_unchanged: bool,
    comment_level: str,
):
    """When changed reports exist, only the NONE level suppresses comment posting."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value=skip_unchanged)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_level", return_value=comment_level)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="JaCoCo")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_pass_symbol", return_value="✅")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_fail_symbol", return_value="❌")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=False)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_repository", return_value="owner/repo")

    bs_evaluator = CoverageEvaluator(report_files_coverage=[], global_min_coverage_overall=0.0,
                                      global_min_coverage_changed_files=0.0)
    generator = PRCommentGenerator(gh_mock, evaluator_with_changed, bs_evaluator, pr_number=1)
    generator.generate()

    if comment_level == "none":
        gh_mock.add_comment.assert_not_called()
    else:
        gh_mock.add_comment.assert_called_once()


@pytest.mark.parametrize("skip_unchanged", [False, True])
def test_comment_level_none_still_suppresses_comment(
    mocker: MockerFixture,
    gh_mock,
    evaluator_with_changed,
    skip_unchanged: bool,
):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value=skip_unchanged)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_level", return_value="none")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="JaCoCo")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_pass_symbol", return_value="✅")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_fail_symbol", return_value="❌")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=True)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_repository", return_value="owner/repo")

    gh_mock.get_comments.return_value = [{"id": 99, "body": "**JaCoCo**\n\nold content"}]

    bs_evaluator = CoverageEvaluator(report_files_coverage=[], global_min_coverage_overall=0.0,
                                      global_min_coverage_changed_files=0.0)
    generator = PRCommentGenerator(gh_mock, evaluator_with_changed, bs_evaluator, pr_number=1)
    generator.generate()

    gh_mock.add_comment.assert_not_called()
    gh_mock.update_comment.assert_not_called()


@pytest.mark.parametrize("comment_level", [CommentLevelEnum.MINIMAL, CommentLevelEnum.FULL])
def test_minimal_comment_contains_only_global_table(
    mocker: MockerFixture,
    gh_mock,
    evaluator_with_changed,
    comment_level: CommentLevelEnum,
):
    """MINIMAL level produces only the global summary table; FULL includes the reports table."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_level", return_value=comment_level)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="JaCoCo")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_pass_symbol", return_value="✅")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_fail_symbol", return_value="❌")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=False)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_repository", return_value="owner/repo")

    bs_evaluator = CoverageEvaluator(report_files_coverage=[], global_min_coverage_overall=0.0,
                                      global_min_coverage_changed_files=0.0)
    generator = PRCommentGenerator(gh_mock, evaluator_with_changed, bs_evaluator, pr_number=1)
    generator.generate()

    body = gh_mock.add_comment.call_args[0][1]
    assert "**Overall**" in body
    if comment_level == CommentLevelEnum.MINIMAL:
        assert "| Report |" not in body
    else:
        assert "| Report |" in body


# --- fail-on-threshold boolean removal ---

def test_fail_on_threshold_true_is_rejected(mocker: MockerFixture):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="true")
    with pytest.raises(ValueError) as exc_info:
        ActionInputs.get_fail_on_threshold()
    assert "Boolean values for 'fail-on-threshold' are no longer supported." in str(exc_info.value)


def test_fail_on_threshold_false_is_rejected(mocker: MockerFixture):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="false")
    with pytest.raises(ValueError) as exc_info:
        ActionInputs.get_fail_on_threshold()
    assert "Boolean values for 'fail-on-threshold' are no longer supported." in str(exc_info.value)


# --- skip-unchanged with report groups ---

def test_skip_unchanged_with_report_groups_filters_groupless_unchanged_report(
    mocker: MockerFixture, make_report_file_coverage, make_file_coverage, caplog
):
    """Reports with no changed files inside a group are filtered; reports with changes proceed."""
    from jacoco_report.model.report_group import ReportGroup

    fc = make_file_coverage(instruction=Counter(missed=0, covered=10))
    changed = make_report_file_coverage(
        name="Changed Report", changed_files_coverage={"src/Foo.java": fc}, group_name="team-a"
    )
    unchanged = make_report_file_coverage(
        name="Unchanged Report", changed_files_coverage={}, group_name="team-a"
    )

    group = ReportGroup(name="team-a", paths=["**/jacoco.xml"])

    mocks = _make_run_mocks(mocker, skip_unchanged=True, evaluate_unchanged=False, reports=[changed, unchanged])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[group])

    with caplog.at_level(logging.INFO, logger="jacoco_report.jacoco_report"):
        jr = JaCoCoReport()
        jr.run()

    assert "Filtering report 'Unchanged Report' from evaluation and comment rows: no changed files." in caplog.text
    assert "Filtering report 'Changed Report'" not in caplog.text
    assert jr.violations == []


def test_fail_on_threshold_list_form_no_warning(mocker: MockerFixture, caplog):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="overall")
    with caplog.at_level(logging.WARNING, logger="jacoco_report.action_inputs"):
        result = ActionInputs.get_fail_on_threshold()
    assert result == ["overall"]
    assert "deprecated" not in caplog.text.lower()
