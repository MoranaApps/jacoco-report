"""
Unit tests for report-target: which channel gets the report (PR comment, job summary, or both), and how each cut reads.

The GitHub client is a mock. The job summary is a real file under tmp_path, set through GITHUB_STEP_SUMMARY.
"""

import logging
import re
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.generator import pr_comment_generator as generator_module
from jacoco_report.generator.pr_comment_generator import (
    SUMMARY_NO_COMMENT_INFO,
    PRCommentGenerator,
    all_filtered_summary_body,
)
from jacoco_report.model.counter import Counter
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.utils.gh_action import SUMMARY_NOT_SET_WARNING, SUMMARY_WRITE_FAILED_WARNING

GENERATOR_LOGGER = "jacoco_report.generator.pr_comment_generator"
RUN_URL = "https://github.com/owner/repo/actions/runs/42"
SUMMARY_LOG_NOTE = "Full report (job summary was cut)"
SAMPLE_REPORTS = 2
SAMPLE_FILES = 3
# Small enough to cut the sample body, and large enough for its head, note and footer.
SMALL_SUMMARY_LIMIT = 800


def _coverage(name, changed_files):
    coverage = EvaluatedReportCoverage(name, group_name="Unknown")
    coverage.overall_passed = True
    coverage.avg_changed_files_passed = True
    coverage.overall_coverage_reached = 85.0
    coverage.avg_changed_files_coverage_reached = 80.0
    coverage.overall_coverage_threshold = 75.0
    coverage.changed_files_threshold = 70.0
    coverage.per_changed_file_threshold = 70.0
    coverage.avg_changed_files_coverage = Counter(0, len(changed_files))
    coverage.changed_files_coverage_reached = changed_files
    coverage.changed_files_passed = {path: True for path in changed_files}
    return coverage


def _populate(evaluator, reports=SAMPLE_REPORTS, files_per_report=SAMPLE_FILES):
    evaluator.evaluated_groups_coverage = {}
    evaluator.evaluated_reports_coverage = {}
    for report in range(reports):
        files = {f"src/module{report}/File{i:03d}.java": 85.0 for i in range(files_per_report)}
        name = f"report-{report}"
        evaluator.evaluated_reports_coverage[name] = _coverage(name, files)


def _table_rows(text):
    return [line for line in text.split("\n") if line.startswith("| `") or line.startswith("| [")]


@pytest.fixture
def gh(mocker: MockerFixture):
    client = mocker.Mock()
    client.get_comments.return_value = []
    client.add_comment.return_value = True
    client.update_comment.return_value = True
    client.delete_comment.return_value = True
    return client


@pytest.fixture
def evaluator():
    ce = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=80.0, global_min_coverage_changed_files=80.0
    )
    ce.total_coverage_overall = 85.2
    ce.total_coverage_overall_passed = True
    ce.total_coverage_changed_files = 78.4
    ce.total_coverage_changed_files_passed = False
    _populate(ce)
    return ce


@pytest.fixture
def summary_file(tmp_path, monkeypatch):
    path = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(path))
    monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)
    return path


@pytest.fixture
def configure(mocker: MockerFixture):
    """Patch the ActionInputs getters the generator reads, with a run link of owner/repo run 42."""

    def _configure(*, report_target="comment", comment_level="full", update_comment=True):
        values = {
            "get_report_target": report_target,
            "get_comment_level": comment_level,
            "get_update_comment": update_comment,
            "get_title": "JaCoCo",
            "get_pass_symbol": "✅",
            "get_fail_symbol": "❌",
            "get_metric": "instruction",
            "get_global_overall_threshold": 80.0,
            "get_global_changed_files_average_threshold": 80.0,
            "get_repository": "owner/repo",
            "get_run_id": "42",
            "get_event_name": "pull_request",
            "get_action_ref": "",
        }
        for getter, value in values.items():
            mocker.patch(f"jacoco_report.action_inputs.ActionInputs.{getter}", return_value=value)

    return _configure


def _generator(gh, evaluator, ungrouped=None):
    return PRCommentGenerator(gh, evaluator, None, 1, ungrouped_reports=ungrouped)


def _lower_comment_limit(monkeypatch, limit):
    monkeypatch.setattr(generator_module, "MAX_COMMENT_LENGTH", limit)


def _lower_summary_limit(monkeypatch, limit):
    monkeypatch.setattr(generator_module, "MAX_SUMMARY_BYTES", limit)


def _uncut_body_length(gh, evaluator, configure, monkeypatch, **settings):
    """Length of the comment body with no limit, so tests can pick a limit that is actually exceeded."""
    configure(**settings)
    _lower_comment_limit(monkeypatch, 10**9)
    _generator(gh, evaluator).generate()
    return len(gh.add_comment.call_args[0][1])


# ---------------------------------------------------------------------------
# A: the comment channel (comment and both) keeps today's API calls
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("report_target", ["comment", "both"])
def test_a1_creates_comment_when_none_exists(gh, evaluator, configure, report_target, summary_file):
    configure(report_target=report_target, update_comment=True)
    gh.get_comments.return_value = []

    assert _generator(gh, evaluator).generate() is True

    gh.add_comment.assert_called_once()
    gh.update_comment.assert_not_called()


@pytest.mark.parametrize("report_target", ["comment", "both"])
def test_a2_updates_existing_comment_with_the_same_title(gh, evaluator, configure, report_target, summary_file):
    configure(report_target=report_target, update_comment=True)
    gh.get_comments.return_value = [{"id": 7, "body": "**JaCoCo**\n\nold"}]

    assert _generator(gh, evaluator).generate() is True

    gh.update_comment.assert_called_once()
    assert gh.update_comment.call_args[0][0] == 7
    gh.add_comment.assert_not_called()


@pytest.mark.parametrize("report_target", ["comment", "both"])
def test_a3_appends_without_reading_comments_when_update_comment_is_false(
    gh, evaluator, configure, report_target, summary_file
):
    configure(report_target=report_target, update_comment=False)

    assert _generator(gh, evaluator).generate() is True

    gh.get_comments.assert_not_called()
    gh.add_comment.assert_called_once()


@pytest.mark.parametrize("report_target", ["comment", "both"])
def test_a4_comment_level_none_deletes_the_existing_comment(gh, evaluator, configure, report_target, summary_file):
    configure(report_target=report_target, comment_level="none", update_comment=True)
    gh.get_comments.return_value = [{"id": 9, "body": "**JaCoCo**\n\nold"}]

    assert _generator(gh, evaluator).generate() is True

    gh.delete_comment.assert_called_once_with(9)
    gh.add_comment.assert_not_called()


@pytest.mark.parametrize("report_target", ["comment", "both"])
def test_a5_comment_level_none_without_existing_comment_only_reads(
    gh, evaluator, configure, report_target, summary_file
):
    configure(report_target=report_target, comment_level="none", update_comment=True)
    gh.get_comments.return_value = []

    assert _generator(gh, evaluator).generate() is True

    gh.get_comments.assert_called_once()
    gh.delete_comment.assert_not_called()
    gh.add_comment.assert_not_called()


@pytest.mark.parametrize("report_target", ["comment", "both"])
def test_a6_comment_level_none_without_update_comment_makes_no_comment_call(
    gh, evaluator, configure, report_target, summary_file
):
    configure(report_target=report_target, comment_level="none", update_comment=False)

    assert _generator(gh, evaluator).generate() is True

    for method in (gh.get_comments, gh.add_comment, gh.update_comment, gh.delete_comment):
        method.assert_not_called()


# ---------------------------------------------------------------------------
# A7: report-target summary never calls the comment API, for either update-comment value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("update_comment", [True, False])
def test_a7_summary_makes_no_comment_call_and_logs_info_once(
    gh, evaluator, configure, update_comment, summary_file, caplog
):
    configure(report_target="summary", update_comment=update_comment)

    with caplog.at_level(logging.INFO, logger=GENERATOR_LOGGER):
        assert _generator(gh, evaluator).generate() is True

    for method in (gh.get_comments, gh.add_comment, gh.update_comment, gh.delete_comment):
        method.assert_not_called()
    infos = [record.getMessage() for record in caplog.records if record.name == GENERATOR_LOGGER]
    assert infos.count(SUMMARY_NO_COMMENT_INFO) == 1


def test_a7_info_text_is_the_spec_text():
    assert SUMMARY_NO_COMMENT_INFO == (
        "report-target is 'summary': no PR comment is created, updated or removed (update-comment is ignored)."
    )


# ---------------------------------------------------------------------------
# B: the job summary channel
# ---------------------------------------------------------------------------


def test_b1_comment_target_does_not_read_the_summary_variable(gh, evaluator, configure, monkeypatch):
    configure(report_target="comment")
    read_path = MagicMock(return_value="/should/not/be/read")
    monkeypatch.setattr("jacoco_report.utils.gh_action.get_step_summary_path", read_path)

    _generator(gh, evaluator).generate()

    read_path.assert_not_called()


def test_b2_summary_gets_the_same_body_as_the_comment(gh, evaluator, configure, summary_file):
    configure(report_target="both")
    generator = _generator(gh, evaluator)

    generator.generate()

    written = summary_file.read_text(encoding="utf-8")
    assert written == gh.add_comment.call_args[0][1]
    assert generator.summary_written is True
    assert generator.summary_warning is None


def test_b3_comment_level_none_writes_nothing_to_the_summary(gh, evaluator, configure, summary_file):
    configure(report_target="summary", comment_level="none")
    generator = _generator(gh, evaluator)

    assert generator.generate() is True

    assert not summary_file.exists()
    assert generator.summary_warning is None


@pytest.mark.parametrize("report_target", ["summary", "both"])
def test_b4_summary_over_the_limit_is_cut_with_the_full_body_in_the_log(
    gh, evaluator, configure, summary_file, monkeypatch, caplog, report_target
):
    configure(report_target=report_target)
    _lower_comment_limit(monkeypatch, 10**9)
    _lower_summary_limit(monkeypatch, SMALL_SUMMARY_LIMIT)

    with caplog.at_level(logging.INFO, logger=GENERATOR_LOGGER):
        _generator(gh, evaluator).generate()

    written = summary_file.read_text(encoding="utf-8")
    assert re.search(r"… \d+ rows? omitted \(GitHub's 1 MiB job summary limit\), the full report is in the ", written)
    assert f"[job log]({RUN_URL})." in written
    assert len(written.encode("utf-8")) <= SMALL_SUMMARY_LIMIT  # the runner measures the whole file
    assert re.search(
        rf"Job summary body is \d+ bytes, over the {SMALL_SUMMARY_LIMIT} byte limit; \d+ row\(s\) omitted from the "
        "job summary\\.",
        caplog.text,
    )
    assert SUMMARY_LOG_NOTE in caplog.text


def test_b4_log_carries_the_whole_uncut_body_once(gh, evaluator, configure, summary_file, monkeypatch, caplog):
    uncut = _uncut_body_for_summary(evaluator, configure, monkeypatch)  # patches the target to comment first
    configure(report_target="summary")
    _lower_summary_limit(monkeypatch, SMALL_SUMMARY_LIMIT)

    with caplog.at_level(logging.INFO, logger=GENERATOR_LOGGER):
        _generator(gh, evaluator).generate()

    assert caplog.text.count(SUMMARY_LOG_NOTE) == 1
    assert uncut in caplog.text


def _uncut_body_for_summary(evaluator, configure, monkeypatch):
    """The full comment body, with no limit: the job summary log must carry exactly this text."""
    gh = MagicMock()
    gh.get_comments.return_value = []
    configure(report_target="comment")
    _lower_comment_limit(monkeypatch, 10**9)
    _generator(gh, evaluator).generate()
    return gh.add_comment.call_args[0][1]


def test_b4_without_run_id_the_note_has_no_link(gh, evaluator, configure, summary_file, monkeypatch):
    configure(report_target="summary")
    monkeypatch.setattr("jacoco_report.action_inputs.ActionInputs.get_run_id", lambda: "")
    _lower_summary_limit(monkeypatch, SMALL_SUMMARY_LIMIT)

    _generator(gh, evaluator).generate()

    written = summary_file.read_text(encoding="utf-8")
    assert "the full report is in the job log." in written
    assert "actions/runs" not in written


def test_b4_counts_bytes_not_characters(gh, evaluator, configure, summary_file, monkeypatch):
    configure(report_target="summary")
    # The symbols are multi-byte, so the body has as many characters as the limit but more bytes: only a byte
    # count cuts it.
    limit = len(_uncut_body_for_summary(evaluator, configure, monkeypatch))
    configure(report_target="summary")
    _lower_summary_limit(monkeypatch, limit)

    _generator(gh, evaluator).generate()

    written = summary_file.read_text(encoding="utf-8")
    assert "rows omitted (GitHub's 1 MiB job summary limit)" in written
    assert len(written.encode("utf-8")) <= limit


def test_b4_backstop_never_splits_a_utf8_character(gh, evaluator, configure, summary_file, monkeypatch, caplog):
    configure(report_target="summary")
    # A title made of multi-byte characters is kept whole, so only the hard cut can make the body fit.
    monkeypatch.setattr("jacoco_report.action_inputs.ActionInputs.get_title", lambda: "✅" * 40)
    _lower_summary_limit(monkeypatch, 101)

    with caplog.at_level(logging.WARNING, logger=GENERATOR_LOGGER):
        _generator(gh, evaluator).generate()

    raw = summary_file.read_bytes()
    text = raw.decode("utf-8")  # raises when a character was cut in half
    assert len(text.encode("utf-8")) <= 101
    assert "still over the limit without its table rows" in caplog.text


def test_b5_unset_summary_variable_gives_the_not_set_warning(gh, evaluator, configure, monkeypatch):
    configure(report_target="both")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    generator = _generator(gh, evaluator)

    assert generator.generate() is True

    expected = SUMMARY_NOT_SET_WARNING.format(target="both")
    assert generator.summary_warning == expected
    assert expected == (
        "report-target 'both' writes to the job summary, but GITHUB_STEP_SUMMARY is not set (not a GitHub Actions "
        "runner, or GHES older than 3.6). The report was not written to the job summary."
    )
    gh.add_comment.assert_called_once()


def test_b5_empty_summary_variable_counts_as_not_set(gh, evaluator, configure, monkeypatch):
    configure(report_target="summary")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", "")
    generator = _generator(gh, evaluator)

    generator.generate()

    assert generator.summary_warning == SUMMARY_NOT_SET_WARNING.format(target="summary")


def test_b6_unwritable_summary_gives_the_write_failed_warning_and_logs_the_error(
    gh, evaluator, configure, tmp_path, monkeypatch, caplog
):
    configure(report_target="summary")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path))  # a directory cannot be appended to
    generator = _generator(gh, evaluator)

    with caplog.at_level(logging.ERROR, logger="jacoco_report.utils.gh_action"):
        assert generator.generate() is True

    assert generator.summary_warning == SUMMARY_WRITE_FAILED_WARNING.format(target="summary")
    assert generator.summary_warning == (
        "report-target 'summary' writes to the job summary, but writing to GITHUB_STEP_SUMMARY failed. "
        "The report was not written to the job summary. See the job log for the error."
    )
    errors = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert errors and errors[0].exc_info is not None


def test_b6_failed_summary_write_does_not_stop_the_comment(gh, evaluator, configure, tmp_path, monkeypatch):
    configure(report_target="both")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path))
    gh.get_comments.return_value = []
    generator = _generator(gh, evaluator)

    assert generator.generate() is True

    gh.add_comment.assert_called_once()
    assert generator.summary_written is False


# ---------------------------------------------------------------------------
# C: the comment note when the comment is cut (65,536 characters, lowered in tests)
# ---------------------------------------------------------------------------


def _cut_limit(gh, evaluator, configure, monkeypatch, **settings):
    """A comment limit that cuts the body by a few rows only."""
    return _uncut_body_length(gh, evaluator, configure, monkeypatch, **settings) - 200


def test_c1_comment_note_points_to_the_job_log(gh, evaluator, configure, summary_file, monkeypatch):
    limit = _cut_limit(gh, evaluator, configure, monkeypatch, report_target="comment")
    _lower_comment_limit(monkeypatch, limit)
    gh.reset_mock()

    _generator(gh, evaluator).generate()

    body = gh.add_comment.call_args[0][1]
    assert re.search(r"… \d+ rows? omitted \(GitHub's 65,536-character comment limit\), see the job log\.", body)
    assert "job summary" not in body


def test_c1_comment_cut_warning_keeps_its_wording(gh, evaluator, configure, monkeypatch, caplog):
    limit = _cut_limit(gh, evaluator, configure, monkeypatch, report_target="comment")
    _lower_comment_limit(monkeypatch, limit)

    with caplog.at_level(logging.WARNING, logger=GENERATOR_LOGGER):
        _generator(gh, evaluator).generate()

    assert re.search(
        rf"PR comment body is \d+ characters, over the {limit} character limit; \d+ row\(s\) omitted from the comment\.",
        caplog.text,
    )


def test_both_writes_the_summary_before_any_comment_call(gh, evaluator, configure, summary_file):
    # The comment's note may point to the job summary only once the summary is on disk.
    configure(report_target="both")
    summary_sizes_at_call: list[int] = []

    def read_comments(*_):
        summary_sizes_at_call.append(summary_file.stat().st_size)
        return []

    gh.get_comments.side_effect = read_comments

    _generator(gh, evaluator).generate()

    assert summary_sizes_at_call and summary_sizes_at_call[0] > 0
    gh.add_comment.assert_called_once()


def test_c2_both_with_summary_written_points_to_the_job_summary(gh, evaluator, configure, summary_file, monkeypatch):
    limit = _cut_limit(gh, evaluator, configure, monkeypatch, report_target="both")
    _lower_comment_limit(monkeypatch, limit)
    gh.reset_mock()
    gh.get_comments.return_value = []

    generator = _generator(gh, evaluator)
    generator.generate()

    body = gh.add_comment.call_args[0][1]
    assert generator.summary_written is True
    assert re.search(
        r"… \d+ rows? omitted \(GitHub's 65,536-character comment limit\), see the \[job summary\]\("
        + re.escape(RUN_URL),
        body,
    )


def test_c2_without_run_id_the_job_summary_note_has_no_link(gh, evaluator, configure, summary_file, monkeypatch):
    limit = _cut_limit(gh, evaluator, configure, monkeypatch, report_target="both")
    _lower_comment_limit(monkeypatch, limit)
    monkeypatch.setattr("jacoco_report.action_inputs.ActionInputs.get_run_id", lambda: "")
    gh.reset_mock()
    gh.get_comments.return_value = []

    _generator(gh, evaluator).generate()

    assert "see the job summary." in gh.add_comment.call_args[0][1]


def test_c3_both_with_summary_not_written_uses_the_job_log_note(gh, evaluator, configure, monkeypatch):
    limit = _cut_limit(gh, evaluator, configure, monkeypatch, report_target="both")
    _lower_comment_limit(monkeypatch, limit)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    gh.reset_mock()
    gh.get_comments.return_value = []

    generator = _generator(gh, evaluator)
    generator.generate()

    body = gh.add_comment.call_args[0][1]
    assert generator.summary_written is False
    assert "see the job log." in body
    assert "job summary" not in body


def test_c4_summary_keeps_every_row_when_the_comment_is_cut(gh, evaluator, configure, summary_file, monkeypatch):
    configure(report_target="both")
    _lower_comment_limit(monkeypatch, 800)
    gh.get_comments.return_value = []

    _generator(gh, evaluator).generate()

    written = summary_file.read_text(encoding="utf-8")
    comment = gh.add_comment.call_args[0][1]
    assert "omitted" in comment
    assert "omitted" not in written
    assert len(_table_rows(written)) == SAMPLE_REPORTS * (SAMPLE_FILES + 1)


def test_summary_gets_the_full_body_when_the_comment_is_cut(gh, evaluator, configure, summary_file, monkeypatch):
    configure(report_target="summary")
    _lower_comment_limit(monkeypatch, 500)

    _generator(gh, evaluator).generate()

    written = summary_file.read_text(encoding="utf-8")
    assert "omitted" not in written
    assert "**JaCoCo**" in written
    assert len(_table_rows(written)) == SAMPLE_REPORTS * (SAMPLE_FILES + 1)


# ---------------------------------------------------------------------------
# D1: the all-reports-unchanged message
# ---------------------------------------------------------------------------


def test_all_filtered_summary_body_has_title_message_and_footer(configure, monkeypatch):
    configure(report_target="summary")
    monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)

    body = all_filtered_summary_body()

    assert body.startswith("**JaCoCo**\n\nAll reports are unchanged: skip-unchanged removed every report, so there are")
    assert "no coverage rows to show.\n\n---\n" in body
    assert f"Run [42]({RUN_URL})" in body
    assert "Generated by [MoranaApps/jacoco-report]" in body


def test_generate_warning_is_none_for_comment_target(gh, evaluator, configure):
    configure(report_target="comment")
    generator = _generator(gh, evaluator)
    generator.generate()
    assert generator.summary_warning is None
    assert generator.summary_written is False
