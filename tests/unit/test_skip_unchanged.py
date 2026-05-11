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
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_file_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_level", return_value=CommentLevelEnum.FULL)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[])
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
    return make_report_file_coverage(name=name, changed_files_coverage={"src/Foo.java": fc})


def _report_without_changes(name: str, make_report_file_coverage) -> ReportFileCoverage:
    return make_report_file_coverage(name=name, changed_files_coverage={})


# --- scan-stage filter tests ---

def test_skip_unchanged_filters_report_with_no_changed_files(
    mocker: MockerFixture, make_report_file_coverage, caplog
):
    unchanged = _report_without_changes("Report A", make_report_file_coverage)
    changed = _report_with_changes("Report B", make_report_file_coverage)

    _make_run_mocks(mocker, skip_unchanged=True, evaluate_unchanged=False, reports=[unchanged, changed])

    with caplog.at_level(logging.INFO, logger="jacoco_report.jacoco_report"):
        JaCoCoReport().run()

    assert "Skipping report 'Report A': no changed files." in caplog.text
    assert "Skipping report 'Report B'" not in caplog.text


def test_skip_unchanged_logs_each_filtered_report(mocker: MockerFixture, make_report_file_coverage, caplog):
    unchanged_a = _report_without_changes("Alpha Report", make_report_file_coverage)
    unchanged_b = _report_without_changes("Beta Report", make_report_file_coverage)
    changed = _report_with_changes("Gamma Report", make_report_file_coverage)

    _make_run_mocks(mocker, skip_unchanged=True, evaluate_unchanged=False, reports=[unchanged_a, unchanged_b, changed])

    with caplog.at_level(logging.INFO, logger="jacoco_report.jacoco_report"):
        JaCoCoReport().run()

    messages = caplog.text
    assert "Skipping report 'Alpha Report': no changed files." in messages
    assert "Skipping report 'Beta Report': no changed files." in messages
    assert "Skipping report 'Gamma Report'" not in messages


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
        global_min_coverage_changed_per_file=0.0,
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
                                     global_min_coverage_changed_files=0.0, global_min_coverage_changed_per_file=0.0)
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
                                     global_min_coverage_changed_files=0.0, global_min_coverage_changed_per_file=0.0)
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
                                     global_min_coverage_changed_files=0.0, global_min_coverage_changed_per_file=0.0)
    generator = PRCommentGenerator(gh_mock, evaluator_with_changed, bs_evaluator, pr_number=1)
    generator.generate()

    body = gh_mock.add_comment.call_args[0][1]
    assert "**Overall**" in body
    if comment_level == CommentLevelEnum.MINIMAL:
        assert "| Report |" not in body
    else:
        assert "| Report |" in body


# --- fail-on-threshold boolean deprecation ---

def test_fail_on_threshold_true_emits_deprecation_warning(mocker: MockerFixture, caplog):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="true")
    with caplog.at_level(logging.WARNING, logger="jacoco_report.action_inputs"):
        result = ActionInputs.get_fail_on_threshold()
    assert result == ["overall", "changed-files-average", "per-changed-file"]
    assert "no longer supported from v3" in caplog.text
    assert "overall,changed-files-average,per-changed-file" in caplog.text


def test_fail_on_threshold_false_emits_deprecation_warning(mocker: MockerFixture, caplog):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="false")
    with caplog.at_level(logging.WARNING, logger="jacoco_report.action_inputs"):
        result = ActionInputs.get_fail_on_threshold()
    assert result == []
    assert "no longer supported from v3" in caplog.text
    assert "empty string" in caplog.text


def test_fail_on_threshold_list_form_no_warning(mocker: MockerFixture, caplog):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="overall")
    with caplog.at_level(logging.WARNING, logger="jacoco_report.action_inputs"):
        result = ActionInputs.get_fail_on_threshold()
    assert result == ["overall"]
    assert "deprecated" not in caplog.text.lower()
