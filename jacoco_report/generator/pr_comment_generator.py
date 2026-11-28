"""
A module that contains the PRCommentGenerator class.
"""

import hashlib
import logging
import os
from dataclasses import dataclass
from textwrap import dedent
from typing import NamedTuple, Optional

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.evaluator.baseline_comparison import BaselineComparison, CoverageDelta
from jacoco_report.evaluator.baseline_verification import UNVERIFIED_BASELINE_NOTE
from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.utils.constants import ACTION_REPOSITORY, ACTION_REPOSITORY_URL
from jacoco_report.utils.enums import CommentLevelEnum, FailOnThresholdEnum, ReportTargetEnum
from jacoco_report.utils.gh_action import write_job_summary
from jacoco_report.utils.github import GitHub, get_server_url

logger = logging.getLogger(__name__)

_MD_LINK_TEXT_UNSAFE = str.maketrans({"[": "\\[", "]": "\\]", "`": "\\`", "|": "\\|"})


# The limit GitHub enforces on a comment body. The note in a cut body always states it.
GITHUB_COMMENT_LIMIT = 65_536
# The cap this module enforces. It equals GitHub's limit; tests lower it to exercise the boundary.
MAX_COMMENT_LENGTH = GITHUB_COMMENT_LIMIT

# GitHub's job summary limit for one step. Measured in UTF-8 bytes. Tests lower it to exercise the boundary.
GITHUB_SUMMARY_LIMIT = 1_048_576
MAX_SUMMARY_BYTES = GITHUB_SUMMARY_LIMIT

UNGROUPED_LOG_HEADER = "Reports not assigned to any group:"
SUMMARY_NO_COMMENT_INFO = (
    "report-target is 'summary': no PR comment is created, updated or removed (update-comment is ignored)."
)
ALL_FILTERED_MESSAGE = (
    "All reports are unchanged: skip-unchanged removed every report, so there are no coverage rows to show."
)


class _Section(NamedTuple):
    """A cuttable part of the comment: lines before its rows, its rows, and lines after them."""

    log_header: str
    header: list[str]
    rows: list[str]
    trailing: list[str]
    # A section whose rows are all cut still renders its header and trailing lines (the ungrouped-reports frame).
    frame_kept: bool


@dataclass(frozen=True)
class SummaryRow:
    """One row of the global summary table: the coverage reached, whether it passed, and its threshold."""

    reached: float
    passed: bool
    threshold: float


def _single_line(text: str) -> str:
    """Keep a name on one line, so that a line break in it cannot split its table row or list item."""
    return text.replace("\r", " ").replace("\n", " ")


def _escape_md_link_text(text: str) -> str:
    """Escape characters that break Markdown inline-link text."""
    return _single_line(text).translate(_MD_LINK_TEXT_UNSAFE)


def _diffs_or_zero(delta: Optional[CoverageDelta]) -> tuple[float, float]:
    """Return a Δ as (overall, changed files) for a table row; a row without a matched baseline shows 0.0%."""
    if delta is None:
        return 0.0, 0.0
    return delta.overall, delta.changed_files


def _split_table(section: str) -> _Section:
    """Split a rendered table into its two header lines and its rows. A table with any other line is not cut."""
    lines = section.split("\n")
    rest = lines[2:]
    if rest and all(line.startswith("|") for line in rest):
        return _Section("\n".join(lines[:2]), lines[:2], rest, [], False)
    return _Section("", lines, [], [], False)


def _split_ungrouped(warning: str) -> _Section:
    """Split the ungrouped-reports warning into its frame before the items, its `- ` items and the frame after."""
    lines = warning.split("\n")
    first = next((i for i, line in enumerate(lines) if line.startswith("- ")), len(lines))
    end = first
    while end < len(lines) and lines[end].startswith("- "):
        end += 1
    return _Section(UNGROUPED_LOG_HEADER, lines[:first], lines[first:end], lines[end:], True)


@dataclass(frozen=True)
class _CutRules:
    """How one body is cut: what the limit counts, the note's words, and what the job log gets."""

    where: str
    unit: str
    limit: int
    limit_name: str
    tail: str
    log_full_body: bool
    # Logged when the body is cut; filled with the body size, the limit and the number of rows omitted.
    cut_warning: str

    def size(self, text: str) -> int:
        """Return the size of text in the rule's unit: UTF-8 bytes for the job summary, code points for the comment."""
        return len(text.encode("utf-8")) if self.unit == "bytes" else len(text)

    def truncate(self, text: str) -> str:
        """Cut text to the limit. In bytes, a multi-byte character that does not fit is dropped whole."""
        if self.unit == "bytes":
            return text.encode("utf-8")[: self.limit].decode("utf-8", errors="ignore")
        return text[: self.limit]


class _ReportParts(NamedTuple):
    """The parts of a report body. The PR comment and the job summary are both joined from them."""

    head: str
    sections: list[_Section]
    footer: str


def _comment_rules(summary_written: bool, run_url: str) -> _CutRules:
    """Rules for the PR comment. Its note points to the job summary only when the summary holds the report."""
    tail = f"see the {_link('job summary', run_url)}." if summary_written else "see the job log."
    return _CutRules(
        where="PR comment",
        unit="characters",
        limit=MAX_COMMENT_LENGTH,
        limit_name=f"{GITHUB_COMMENT_LIMIT:,}-character comment limit",
        tail=tail,
        log_full_body=False,
        cut_warning=(
            "PR comment body is %d characters, over the %d character limit; %d row(s) omitted from the comment."
        ),
    )


def _summary_rules(run_url: str) -> _CutRules:
    """Rules for the job summary: cut only at its own limit, and the full body goes to the job log."""
    return _CutRules(
        where="Job summary",
        unit="bytes",
        limit=MAX_SUMMARY_BYTES,
        limit_name="1 MiB job summary limit",
        tail=f"the full report is in the {_link('job log', run_url)}.",
        log_full_body=True,
        cut_warning="Job summary body is %d bytes, over the %d byte limit; %d row(s) omitted from the job summary.",
    )


def _link(text: str, url: str) -> str:
    """Return a Markdown link to url, or the plain text when there is no url."""
    return f"[{text}]({url})" if url else text


def _run_url(server_url: str, repository: str) -> str:
    """Return the URL of this workflow run, or '' when the run id or the repository is unknown."""
    run_id = ActionInputs.get_run_id()
    if not run_id or not repository:
        return ""
    return f"{server_url}/{repository}/actions/runs/{run_id}"


def _metadata_footer(server_url: str, repository: str) -> str:
    """Build the metadata footer appended to every report body.

    The "Generated by" line is always rendered, so the footer is never empty.
    """
    run_id = ActionInputs.get_run_id()
    event = ActionInputs.get_event_name()
    action_ref = ActionInputs.get_action_ref()

    lines = ["---"]
    run_parts: list[str] = []
    if run_id:
        url = _run_url(server_url, repository)
        run_parts.append(f"Run [{run_id}]({url})" if url else f"Run `{run_id}`")
    if event:
        run_parts.append(f"Event: `{event}`")
    if run_parts:
        lines.append("*" + " · ".join(run_parts) + "*")

    generated_by = f"Generated by [{ACTION_REPOSITORY}]({ACTION_REPOSITORY_URL})"
    if action_ref:
        generated_by += f" `@{action_ref}`"
    lines.append(f"*{generated_by}*")
    return "\n".join(lines)


def all_filtered_summary_body() -> str:
    """Build the job summary for a run in which skip-unchanged removed every report: title, message, footer."""
    footer = _metadata_footer(get_server_url(), ActionInputs.get_repository())
    return f"**{ActionInputs.get_title()}**\n\n{ALL_FILTERED_MESSAGE}\n\n{footer}"


def _total_rows(parts: _ReportParts) -> int:
    """Return the number of cuttable rows in a report body."""
    return sum(len(section.rows) for section in parts.sections)


def _kept_rows_per_section(sections: list[_Section], keep: int) -> list[int]:
    """Count the leading rows of each section that are kept when the first `keep` rows of all sections are kept."""
    kept: list[int] = []
    remaining = keep
    for section in sections:
        count = min(len(section.rows), remaining)
        kept.append(count)
        remaining -= count
    return kept


def _render_body(parts: _ReportParts, keep: int, rules: _CutRules) -> str:
    """Join the report parts, keeping the first `keep` rows in document order."""
    body = [parts.head]
    for section, count in zip(parts.sections, _kept_rows_per_section(parts.sections, keep)):
        if count or not section.rows or section.frame_kept:
            body.append("\n".join(section.header + section.rows[:count] + section.trailing))
    omitted = _total_rows(parts) - keep
    if omitted > 0:
        noun = "row" if omitted == 1 else "rows"
        body.append(f"… {omitted} {noun} omitted (GitHub's {rules.limit_name}), {rules.tail}")
    body.append(parts.footer)
    return "\n\n".join(body)


def _log_cut(parts: _ReportParts, keep: int, body: str, rules: _CutRules) -> None:
    """Log a cut body: the job summary logs the whole uncut body, the PR comment its omitted rows by section."""
    logger.warning(rules.cut_warning, rules.size(body), rules.limit, _total_rows(parts) - keep)
    if rules.log_full_body:
        logger.info("Full report (job summary was cut):\n%s", body)
        return
    for section, count in zip(parts.sections, _kept_rows_per_section(parts.sections, keep)):
        if section.rows and count < len(section.rows):
            logger.info("Omitted from the PR comment:\n%s", "\n".join([section.log_header, *section.rows[count:]]))


def _fit_to_limit(parts: _ReportParts, rules: _CutRules) -> str:
    """Return the body if within the limit, else keep the most leading rows that fit, or cut to the limit."""
    total = _total_rows(parts)
    body = _render_body(parts, total, rules)
    if rules.size(body) <= rules.limit:
        return body

    # A body grows with every kept row, so the largest kept count that fits is found by binary search.
    low, high = 0, total
    while low < high:
        middle = (low + high + 1) // 2
        if rules.size(_render_body(parts, middle, rules)) <= rules.limit:
            low = middle
        else:
            high = middle - 1

    cut = _render_body(parts, low, rules)
    _log_cut(parts, low, body, rules)
    if rules.size(cut) > rules.limit:
        logger.warning(
            "%s is still over the limit without its table rows; cut to %d %s.", rules.where, rules.limit, rules.unit
        )
        cut = rules.truncate(cut)
    return cut


class PRCommentGenerator:
    """
    A class that represents the PR Comment Generator.
    """

    def __init__(
        self,
        gh: GitHub,
        evaluator: CoverageEvaluator,
        bs_evaluator: Optional[CoverageEvaluator],
        pr_number: int,
        skip_report_names: frozenset[str] = frozenset(),
        ungrouped_reports: list[str] | None = None,
        baseline_unverified: bool = False,
    ):
        self.gh: GitHub = gh
        self.evaluator: CoverageEvaluator = evaluator
        self.bs_evaluator: Optional[CoverageEvaluator] = bs_evaluator
        self.pr_number: int = pr_number
        self.skip_report_names: frozenset[str] = skip_report_names
        self.ungrouped_reports: list[str] = ungrouped_reports or []
        self.baseline_unverified: bool = baseline_unverified
        self.github_repository: str = ActionInputs.get_repository()
        self.github_server_url: str = get_server_url()
        # Set by generate(): whether the report reached the job summary, and the warning for the caller to print
        # when it did not (None when nothing needs printing).
        self.summary_written: bool = False
        self.summary_warning: str | None = None

    def generate(self) -> bool:
        """
        Write the report to the job summary and/or the PR comment, as report-target selects. Summary comes first.

        @return: True when no comment operation failed (also when there is nothing to do, and for 'summary'), False
            when the comments could not be read or a comment request failed. Nothing is printed: see summary_warning.
        """
        comment_level = ActionInputs.get_comment_level()
        update_comment = ActionInputs.get_update_comment()
        report_target = ActionInputs.get_report_target()

        title, parts = self._get_comment_content(comment_level)
        if report_target != ReportTargetEnum.COMMENT:
            self.summary_written = self._write_summary(comment_level, parts)
        # The summary target never reads or changes a comment, so it stops here.
        if report_target == ReportTargetEnum.SUMMARY:
            logger.info("%s", SUMMARY_NO_COMMENT_INFO)
            return True

        # No comment operation is needed in this mode, so skip the API read call entirely.
        if comment_level == CommentLevelEnum.NONE and not update_comment:
            return True

        pr_body = title if comment_level == CommentLevelEnum.NONE else self._comment_body(parts)

        # Without update-comment each run appends a new comment, so the existing comments are not read.
        if not update_comment:
            return self.gh.add_comment(self.pr_number, pr_body)

        return self._change_comment(title, pr_body, comment_level)

    def _change_comment(self, title: str, pr_body: str, comment_level: str) -> bool:
        """Add, update or (at comment-level none) delete the PR comment that starts with the title."""
        # Get all comments on the pull request
        comments = self.gh.get_comments(self.pr_number)
        if comments is None:
            logger.error("Could not read PR comments; skipping PR comment changes.")
            return False

        # Check for existing comment with the same title
        existing_comment = None
        for comment in comments:
            if len(title) > 0 and comment["body"].startswith(title):  # Detects if it starts with the title
                existing_comment = comment
                break

        if comment_level == CommentLevelEnum.NONE:
            if existing_comment:
                return self.gh.delete_comment(existing_comment["id"])
            return True

        if existing_comment:
            return self.gh.update_comment(existing_comment["id"], pr_body)
        return self.gh.add_comment(self.pr_number, pr_body)

    def _write_summary(self, comment_level: str, parts: _ReportParts) -> bool:
        """Append the report to the job summary, cut only at its own limit. Returns True when it was written."""
        if comment_level == CommentLevelEnum.NONE:
            return False
        body = _fit_to_limit(parts, _summary_rules(_run_url(self.github_server_url, self.github_repository)))
        self.summary_warning = write_job_summary(ActionInputs.get_report_target(), body)
        return self.summary_warning is None

    def _comment_body(self, parts: _ReportParts) -> str:
        """Return the PR comment body, whose note names the job summary only when the summary holds the report."""
        return _fit_to_limit(
            parts, _comment_rules(self.summary_written, _run_url(self.github_server_url, self.github_repository))
        )

    def _get_comment_content(self, comment_level: str) -> tuple[str, _ReportParts]:
        """Build the title and the parts of the report for the selected comment level."""
        title = f"**{ActionInputs.get_title()}**"

        if comment_level == CommentLevelEnum.NONE:
            return title, _ReportParts(title, [], "")

        p = ActionInputs.get_pass_symbol()
        f = ActionInputs.get_fail_symbol()

        head = f"{title}\n\n{self.get_basic_table_for_all(p, f)}"
        if self.baseline_unverified and self._has_baseline_data():
            head += f"\n\n{UNVERIFIED_BASELINE_NOTE}"
        detail_sections: list[str] = []

        if comment_level != CommentLevelEnum.MINIMAL:
            filtered_groups = self.evaluator.evaluated_groups_coverage
            filtered_reports = {
                k: v for k, v in self.evaluator.evaluated_reports_coverage.items() if k not in self.skip_report_names
            }
            if self.skip_report_names:
                visible_group_names: frozenset[str] = frozenset(
                    v.group_name
                    for k, v in self.evaluator.evaluated_reports_coverage.items()
                    if k not in self.skip_report_names
                )
                filtered_groups = {k: v for k, v in filtered_groups.items() if k in visible_group_names}

            # 'no-decrease' drops are found on the rows that survive skip-unchanged, before the zero-weight filter.
            dropped_groups = self._dropped_row_keys(filtered_groups, is_group=True)
            dropped_reports = self._dropped_row_keys(filtered_reports, is_group=False)

            # Hide reports and groups whose changed files all have zero metric weight, unless they fail a threshold
            # or dropped against the baseline: a failing row must not vanish from the comment.
            filtered_reports = self._keep_zero_weight_rows_that_fail(filtered_reports, dropped_reports)
            filtered_groups = self._keep_zero_weight_rows_that_fail(filtered_groups, dropped_groups)

            if comment_level != CommentLevelEnum.FULL:
                filtered_groups = self._filter_evaluated_coverage_rows(filtered_groups, comment_level, dropped_groups)
                filtered_reports = self._filter_evaluated_coverage_rows(
                    filtered_reports, comment_level, dropped_reports
                )

            groups_table = self.get_groups_table(p, f, filtered_groups)
            if groups_table:
                detail_sections.append(groups_table)

            reports_table = self.get_reports_table(p, f, filtered_reports)
            if reports_table:
                detail_sections.append(reports_table)

            changed_files_table = self._get_changed_files_table(p, f, filtered_reports, comment_level)
            if changed_files_table:
                detail_sections.append(changed_files_table)

            if not detail_sections and comment_level != CommentLevelEnum.FULL:
                head += "\n\nNo rows match the selected comment level."

        sections = [_split_table(section) for section in detail_sections]
        ungrouped_warning = self._get_ungrouped_reports_warning()
        if ungrouped_warning:
            sections.append(_split_ungrouped(ungrouped_warning))

        return title, _ReportParts(head, sections, _metadata_footer(self.github_server_url, self.github_repository))

    def _get_ungrouped_reports_warning(self) -> str:
        """Build a warning section for reports not assigned to any group.

        Returns empty string if no ungrouped reports.
        """
        if not self.ungrouped_reports:
            return ""

        count = len(self.ungrouped_reports)
        report_list = "\n".join(f"- `{_single_line(report)}`" for report in self.ungrouped_reports)

        warning_content = (
            f"<details><summary>⚠️ Warning: {count} report{'s' if count > 1 else ''} "
            f"not assigned to any group</summary>\n\n"
            f"The following reports were found but not matched by configured groups and are only "
            f"included in **global overall** coverage:\n"
            f"{report_list}\n\n"
            f"**Hint:** Review your group path patterns or set `global-overall-scope: groups-only` "
            f"to exclude ungrouped reports.\n\n"
            f"</details>"
        )
        return warning_content

    def _keep_zero_weight_rows_that_fail(
        self, evaluated_coverages: dict[str, EvaluatedReportCoverage], dropped_keys: frozenset[str]
    ) -> dict[str, EvaluatedReportCoverage]:
        """Hide rows whose changed files all have zero metric weight, except rows that fail a threshold or dropped."""
        return {
            key: coverage
            for key, coverage in evaluated_coverages.items()
            if not coverage.had_changed_files_before_filtering
            or key in dropped_keys
            or self._is_failing_coverage(coverage)
        }

    def _dropped_row_keys(
        self, evaluated_coverages: dict[str, EvaluatedReportCoverage], is_group: bool
    ) -> frozenset[str]:
        """Return the keys of the rows that dropped against the baseline under 'no-decrease'.

        Empty unless 'no-decrease' is selected, so the max-decrease input is only read then. A row without a matching
        baseline is not dropped.
        """
        if self.baseline_unverified or FailOnThresholdEnum.NO_DECREASE not in ActionInputs.get_fail_on_threshold():
            return frozenset()

        max_decrease = ActionInputs.get_max_decrease()
        baseline = self._baseline()
        dropped = baseline.group_dropped if is_group else baseline.report_dropped
        return frozenset(key for key, coverage in evaluated_coverages.items() if dropped(coverage, max_decrease))

    def _filter_evaluated_coverage_rows(
        self,
        evaluated_coverages: dict[str, EvaluatedReportCoverage],
        comment_level: str,
        dropped_keys: frozenset[str],
    ) -> dict[str, EvaluatedReportCoverage]:
        """Filter group or report rows according to the selected comment level; `dropped_keys` are failing rows."""
        return {
            key: coverage
            for key, coverage in evaluated_coverages.items()
            if self._should_include_coverage_row(coverage, comment_level, key in dropped_keys)
        }

    def _should_include_coverage_row(
        self, coverage: EvaluatedReportCoverage, comment_level: str, dropped: bool
    ) -> bool:
        """Return whether one evaluated group or report row should be rendered.

        A row is failing when a fixed threshold fails or, under 'no-decrease', when it dropped against the baseline.
        """
        if comment_level == CommentLevelEnum.FULL:
            return True

        has_changed_files = self._has_changed_files(coverage)
        is_failing = dropped or self._is_failing_coverage(coverage)

        if comment_level == CommentLevelEnum.CHANGED:
            return has_changed_files

        if comment_level == CommentLevelEnum.FAILED:
            return is_failing

        if comment_level == CommentLevelEnum.FAILED_OR_CHANGED:
            return has_changed_files or is_failing

        return False

    def _has_changed_files(self, coverage: EvaluatedReportCoverage) -> bool:
        """Return whether a coverage row represents at least one changed file.

        A row whose changed files all have zero weight for the selected metric still had changed files.
        """
        if coverage.changed_files_coverage_reached or coverage.had_changed_files_before_filtering:
            return True

        return (coverage.avg_changed_files_coverage.covered + coverage.avg_changed_files_coverage.missed) > 0

    def _is_failing_coverage(self, coverage: EvaluatedReportCoverage) -> bool:
        """Return whether any threshold represented by the coverage row is failing."""
        return (
            not coverage.overall_passed
            or not coverage.avg_changed_files_passed
            or any(not passed for passed in coverage.changed_files_passed.values())
        )

    def _baseline(self) -> BaselineComparison:
        """Return the baseline comparison of the current evaluators, built per call as tests replace them."""
        return BaselineComparison(self.evaluator, self.bs_evaluator)

    def _has_baseline_data(self) -> bool:
        """Return whether baseline evaluator data is available for diff columns."""
        return self._baseline().has_baseline_data()

    def get_basic_table_for_all(self, p: str, f: str) -> str:
        """Render the global summary table, with baseline deltas when available."""
        overall = SummaryRow(
            self.evaluator.total_coverage_overall,
            self.evaluator.total_coverage_overall_passed,
            ActionInputs.get_global_overall_threshold(),
        )
        changed_files = SummaryRow(
            self.evaluator.total_coverage_changed_files,
            self.evaluator.total_coverage_changed_files_passed,
            ActionInputs.get_global_changed_files_average_threshold(),
        )
        if not self._has_baseline_data():
            return self.get_basic_table(p, f, ActionInputs.get_metric(), overall, changed_files)

        # With baseline data but no matched report the Δ column still shows, as 0.0%.
        diff_o, diff_ch = _diffs_or_zero(self._baseline().global_delta())
        return self._render_basic_table_with_delta(
            p, f, ActionInputs.get_metric(), overall, changed_files, diff_o, diff_ch
        )

    # Full example of the table
    # | Metric (Instruction) | Coverage | Threshold | Δ Coverage | Status |
    # |----------------------|----------|-----------|------------|--------|
    # | **Overall**          | 85.2%    | 80%       | +1,3%      | ✅      |
    # | **Changed Files**    | 78.4%    | 80%       | 0.3%       | ❌      |

    def get_basic_table(self, p: str, f: str, metric: str, overall: SummaryRow, changed_files: SummaryRow) -> str:
        """Render the global summary table without baseline deltas."""
        return (
            dedent("""
            | Metric ({}) | Coverage | Threshold | Status |
            |----------------------|----------|-----------|--------|
            | **Overall**       | {}% | {}% | {} |
            | **Changed Files** | {}% | {}% | {} |
        """)
            .strip()
            .format(
                metric,
                overall.reached,
                overall.threshold,
                p if overall.passed else f,
                changed_files.reached,
                changed_files.threshold,
                p if changed_files.passed else f,
            )
        )

    def get_basic_table_with_baseline(
        self,
        p: str,
        f: str,
        metric: str,
        overall: SummaryRow,
        changed_files: SummaryRow,
        bs_overall_reached: float,
        bs_changed_files_reached: float,
    ) -> str:
        """Render the global summary table with baseline delta columns."""
        return self._render_basic_table_with_delta(
            p,
            f,
            metric,
            overall,
            changed_files,
            overall.reached - bs_overall_reached,
            changed_files.reached - bs_changed_files_reached,
        )

    def _render_basic_table_with_delta(
        self,
        p: str,
        f: str,
        metric: str,
        overall: SummaryRow,
        changed_files: SummaryRow,
        diff_o: float,
        diff_ch: float,
    ) -> str:
        """Render the global summary table given pre-computed deltas."""
        return (
            dedent("""
            | Metric ({}) | Coverage | Threshold | Δ Coverage | Status |
            |-------------------|-----|-----|-----|----|
            | **Overall**       | {}% | {}% | {}{}% | {} |
            | **Changed Files** | {}% | {}% | {}{}% | {} |
        """)
            .strip()
            .format(
                metric,
                overall.reached,
                overall.threshold,
                "+" if diff_o > 0.001 else "",
                round(diff_o, 2),
                p if overall.passed else f,
                changed_files.reached,
                changed_files.threshold,
                "+" if diff_ch > 0.001 else "",
                round(diff_ch, 2),
                p if changed_files.passed else f,
            )
        )

    def get_groups_table(
        self,
        p: str,
        f: str,
        evaluated_groups_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None,
    ) -> str:
        """Render the groups table for the provided evaluated group rows."""
        if evaluated_groups_coverage is None:
            evaluated_groups_coverage = self.evaluator.evaluated_groups_coverage

        if not evaluated_groups_coverage:
            return ""

        has_baseline = self._has_baseline_data()

        if not has_baseline:
            s = dedent("""
                | Group | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
                |-------|----------|-----------|--------|
            """).strip()
            for group_name, ev in sorted(evaluated_groups_coverage.items()):
                cov = f"{ev.overall_coverage_reached}% / {ev.avg_changed_files_coverage_reached}%"
                thres = f"{ev.overall_coverage_threshold}% / {ev.changed_files_threshold}%"
                status = f"{p if ev.overall_passed else f}/{p if ev.avg_changed_files_passed else f}"
                s += f"\n| `{_single_line(group_name)}` | {cov} | {thres} | {status} |"
        else:
            s = dedent("""
                | Group | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
                |-------|----------|-----------|------------|--------|
            """).strip()
            for group_name, ev in sorted(evaluated_groups_coverage.items()):
                diff_o, diff_ch = self.calculate_baseline_group_diffs(ev)
                diff_o = round(diff_o, 2)
                diff_ch = round(diff_ch, 2)
                cov = f"{ev.overall_coverage_reached}% / {ev.avg_changed_files_coverage_reached}%"
                thres = f"{ev.overall_coverage_threshold}% / {ev.changed_files_threshold}%"
                delta = f"{'+' if diff_o > 0.001 else ''}{diff_o}% / {'+' if diff_ch > 0.001 else ''}{diff_ch}%"
                status = f"{p if ev.overall_passed else f}/{p if ev.avg_changed_files_passed else f}"
                s += f"\n| `{_single_line(group_name)}` | {cov} | {thres} | {delta} | {status} |"
        return s

    def get_reports_table(
        self,
        p: str,
        f: str,
        evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None,
    ) -> str:
        """Render the reports table for the provided evaluated report rows."""
        if not self._has_baseline_data():
            return self._generate_reports_table_without_baseline(p, f, evaluated_reports_coverage)

        return self._generate_reports_table_with_baseline(p, f, evaluated_reports_coverage)

    def _generate_reports_table_without_baseline(
        self,
        p: str,
        f: str,
        evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None,
    ) -> str:
        if evaluated_reports_coverage is None:
            evaluated_reports_coverage = self.evaluator.evaluated_reports_coverage

        if not evaluated_reports_coverage:
            return ""

        s = dedent("""
            | Report | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
            |--------|----------|-----------|--------|
        """).strip()

        keys: list[str] = self._sorted_report_keys(evaluated_reports_coverage)
        for key in keys:
            evaluated_report = evaluated_reports_coverage[key]
            o_thres = evaluated_report.overall_coverage_threshold
            ch_thres = evaluated_report.changed_files_threshold

            name = evaluated_report.name
            overall_cov = evaluated_report.overall_coverage_reached
            cov = f"{overall_cov}% / {evaluated_report.avg_changed_files_coverage_reached}%"
            thres = f"{o_thres}% / {ch_thres}%"
            status_o = p if evaluated_report.overall_passed else f
            status_ch = p if evaluated_report.avg_changed_files_passed else f
            s += f"\n| `{_single_line(name)}` | {cov} | {thres} | {status_o}/{status_ch} |"

        return s

    def _generate_reports_table_with_baseline(
        self,
        p: str,
        f: str,
        evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None,
    ) -> str:
        if evaluated_reports_coverage is None:
            evaluated_reports_coverage = self.evaluator.evaluated_reports_coverage

        if not evaluated_reports_coverage:
            return ""

        s = dedent("""
            | Report | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
            |--------|----------|-----------|------------|--------|
        """).strip()

        keys: list[str] = self._sorted_report_keys(evaluated_reports_coverage)
        for key in keys:
            evaluated_report = evaluated_reports_coverage[key]
            diff_o, diff_ch = self._calculate_baseline_report_diffs(evaluated_report)

            o_thres = evaluated_report.overall_coverage_threshold
            ch_thres = evaluated_report.changed_files_threshold

            name = evaluated_report.name
            overall_cov = evaluated_report.overall_coverage_reached
            cov = f"{overall_cov}% / {evaluated_report.avg_changed_files_coverage_reached}%"
            thres = f"{o_thres}% / {ch_thres}%"
            delta = (
                f"{'+' if diff_o > 0.001 else ''}{round(diff_o, 2)}%"
                f" / {'+' if diff_ch > 0.001 else ''}{round(diff_ch, 2)}%"
            )
            status_o = p if evaluated_report.overall_passed else f
            status_ch = p if evaluated_report.avg_changed_files_passed else f
            s += f"\n| `{_single_line(name)}` | {cov} | {thres} | {delta} | {status_o}/{status_ch} |"

        return s

    def _sorted_report_keys(self, evaluated_reports_coverage: dict[str, EvaluatedReportCoverage]) -> list[str]:
        """Return report keys sorted by configured group order, then by display name."""
        group_order = self.evaluator.report_group_order
        if not group_order:
            return sorted(
                list(evaluated_reports_coverage.keys()),
                key=lambda k: evaluated_reports_coverage[k].name,
            )

        group_index: dict[str, int] = {name: idx for idx, name in enumerate(group_order)}
        fallback_index = len(group_index)

        return sorted(
            list(evaluated_reports_coverage.keys()),
            key=lambda k: (
                group_index.get(evaluated_reports_coverage[k].group_name, fallback_index),
                evaluated_reports_coverage[k].name,
            ),
        )

    def calculate_baseline_group_diffs(self, evaluated_coverage: EvaluatedReportCoverage) -> tuple[float, float]:
        """Return the (overall, changed files) Δ of one rendered group row, (0.0, 0.0) without a matched baseline."""
        return _diffs_or_zero(self._baseline().group_delta(evaluated_coverage))

    def _calculate_baseline_report_diffs(self, evaluated_coverage: EvaluatedReportCoverage) -> tuple[float, float]:
        """Return the (overall, changed files) Δ of one rendered report row, (0.0, 0.0) without a matched baseline."""
        return _diffs_or_zero(self._baseline().report_delta(evaluated_coverage))

    # Full example of the table
    # | File Path                                      | Coverage | Threshold | Δ Coverage | Status |
    # |------------------------------------------------|----------|-----------|------------|--------|
    # | `src/main/java/com/example/File1.java`         | 90.1%    | 80%       | +0.3%      | ✅      |
    # | `src/main/java/com/example/File2.java`         | 70.5%    | 80%       | -1.0%      | ❌      |
    # | `src/main/java/com/example/File3.java`         | 82.1%    | 80%       | +2.7%      | ✅      |

    def generate_changed_files_table_without_baseline(
        self, p: str, f: str, evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None
    ) -> str:
        """
        Generate a table with changed files without baseline. The table contains the files from all reports.
        """
        s = dedent("""
            | File Path | Coverage | Threshold | Status |
            |-----------|----------|-----------|--------|
        """).strip()

        if evaluated_reports_coverage is None:
            evaluated_reports_coverage = self.evaluator.evaluated_reports_coverage

        lines = []
        for ecr_key in evaluated_reports_coverage.keys():
            for file_key in evaluated_reports_coverage[ecr_key].changed_files_coverage_reached.keys():
                filename = _escape_md_link_text(os.path.basename(file_key))
                file_hash = hashlib.sha256(file_key.encode("utf-8")).hexdigest()
                file_as_link_to_diff = (
                    f"{self.github_server_url}/{self.github_repository}/pull/{self.pr_number}/files#diff-{file_hash}"
                )

                line = (
                    f"\n| [{filename}]({file_as_link_to_diff})"
                    f" | {evaluated_reports_coverage[ecr_key].changed_files_coverage_reached[file_key]}%"
                    f" | {evaluated_reports_coverage[ecr_key].per_changed_file_threshold}%"
                    f" | {p if evaluated_reports_coverage[ecr_key].changed_files_passed[file_key] else f} |"
                )
                lines.append(line)

        if len(lines) > 0:
            lines.sort()
            s += "".join(lines)
        else:
            s += "\n\nNo changed file in reports."

        return s

    def _get_changed_files_table(
        self,
        p: str,
        f: str,
        evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None,
        comment_level: str = CommentLevelEnum.FULL,
    ) -> str:
        """Render the changed-files table after applying any file-level filters."""
        if evaluated_reports_coverage is None:
            evaluated_reports_coverage = self.evaluator.evaluated_reports_coverage

        if not evaluated_reports_coverage:
            return ""

        if comment_level == CommentLevelEnum.FAILED:
            evaluated_reports_coverage = self._filter_reports_for_failed_files(evaluated_reports_coverage)

        if not self._has_baseline_data():
            return self.generate_changed_files_table_without_baseline(p, f, evaluated_reports_coverage)

        return self.generate_changed_files_table_with_baseline(p, f, evaluated_reports_coverage)

    def _filter_reports_for_failed_files(
        self,
        evaluated_reports_coverage: dict[str, EvaluatedReportCoverage],
    ) -> dict[str, EvaluatedReportCoverage]:
        """Keep only failing changed-file rows while preserving report metadata."""
        filtered_reports: dict[str, EvaluatedReportCoverage] = {}
        for key, coverage in evaluated_reports_coverage.items():
            failed_files = {
                file_path: score
                for file_path, score in coverage.changed_files_coverage_reached.items()
                if not coverage.changed_files_passed.get(file_path, True)
            }
            if not failed_files:
                continue

            filtered_coverage = coverage.clone()
            filtered_coverage.changed_files_coverage_reached = failed_files
            filtered_coverage.changed_files_passed = {
                file_path: coverage.changed_files_passed[file_path] for file_path in failed_files
            }
            filtered_reports[key] = filtered_coverage

        return filtered_reports

    def generate_changed_files_table_with_baseline(
        self, p: str, f: str, evaluated_reports_coverage: Optional[dict[str, EvaluatedReportCoverage]] = None
    ) -> str:
        """Generate a changed-files table that includes baseline deltas."""
        s = dedent("""
            | File Path | Coverage | Threshold | Δ Coverage | Status |
            |-----------|----------|-----------|------------|--------|
        """).strip()

        if evaluated_reports_coverage is None:
            evaluated_reports_coverage = self.evaluator.evaluated_reports_coverage

        baseline = self._baseline()
        lines = []
        for ecr_key in evaluated_reports_coverage.keys():
            curr_erc = evaluated_reports_coverage[ecr_key]
            bs_erc = baseline.find_baseline_report(curr_erc)
            for file_key in curr_erc.changed_files_coverage_reached.keys():
                filename = _escape_md_link_text(os.path.basename(file_key))
                file_hash = hashlib.sha256(file_key.encode("utf-8")).hexdigest()
                file_as_link_to_diff = (
                    f"{self.github_server_url}/{self.github_repository}/pull/{self.pr_number}/files#diff-{file_hash}"
                )

                if bs_erc is None or file_key not in bs_erc.changed_files_coverage_reached:
                    diff = 0.0
                else:
                    diff = (
                        curr_erc.changed_files_coverage_reached[file_key]
                        - bs_erc.changed_files_coverage_reached[file_key]
                    )

                line = (
                    f"\n| [{filename}]({file_as_link_to_diff})"
                    f" | {curr_erc.changed_files_coverage_reached[file_key]}%"
                    f" | {curr_erc.per_changed_file_threshold}%"
                    f" | {'+' if diff > 0.001 else ''}{round(diff, 2)}%"
                    f" | {p if curr_erc.changed_files_passed[file_key] else f} |"
                )
                lines.append(line)

        if len(lines) > 0:
            lines.sort()
            s += "".join(lines)
        else:
            s += "\n\nNo changed file in reports."

        return s
