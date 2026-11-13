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
from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.utils.constants import ACTION_REPOSITORY, ACTION_REPOSITORY_URL
from jacoco_report.utils.enums import CommentLevelEnum
from jacoco_report.utils.github import GitHub, get_server_url

logger = logging.getLogger(__name__)

_MD_LINK_TEXT_UNSAFE = str.maketrans({"[": "\\[", "]": "\\]", "`": "\\`", "|": "\\|"})


# The limit GitHub enforces on a comment body. The note in a cut body always states it.
GITHUB_COMMENT_LIMIT = 65_536
# The cap this module enforces. It equals GitHub's limit; tests lower it to exercise the boundary.
MAX_COMMENT_LENGTH = GITHUB_COMMENT_LIMIT

UNGROUPED_LOG_HEADER = "Reports not assigned to any group:"


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


def _kept_rows_per_section(sections: list[_Section], keep: int) -> list[int]:
    """Count the leading rows of each section that are kept when the first `keep` rows of all sections are kept."""
    kept: list[int] = []
    remaining = keep
    for section in sections:
        count = min(len(section.rows), remaining)
        kept.append(count)
        remaining -= count
    return kept


def _render_body(head: str, sections: list[_Section], footer: str, keep: int) -> str:
    """Join the comment parts, keeping the first `keep` rows in document order."""
    parts = [head]
    for section, count in zip(sections, _kept_rows_per_section(sections, keep)):
        if count or not section.rows or section.frame_kept:
            parts.append("\n".join(section.header + section.rows[:count] + section.trailing))
    total = sum(len(section.rows) for section in sections)
    if keep < total:
        noun = "row" if total - keep == 1 else "rows"
        parts.append(
            f"… {total - keep} {noun} omitted (GitHub's {GITHUB_COMMENT_LIMIT:,}-character comment limit), "
            "see the job log."
        )
    parts.append(footer)
    return "\n\n".join(parts)


def _log_omitted_rows(sections: list[_Section], keep: int, body_length: int) -> None:
    """Log the cut to the job log: one warning, then each cut section with its header and omitted rows."""
    cut_sections = [
        (section.log_header, section.rows[count:])
        for section, count in zip(sections, _kept_rows_per_section(sections, keep))
        if section.rows and count < len(section.rows)
    ]
    omitted = sum(len(rows) for _, rows in cut_sections)
    logger.warning(
        "PR comment body is %d characters, over the %d character limit; %d row(s) omitted from the comment.",
        body_length,
        MAX_COMMENT_LENGTH,
        omitted,
    )
    for log_header, rows in cut_sections:
        logger.info("Omitted from the PR comment:\n%s", "\n".join([log_header, *rows]))


def _fit_to_comment_limit(head: str, sections: list[_Section], footer: str) -> str:
    """Return the comment body, cutting rows from the end when it is over MAX_COMMENT_LENGTH.

    A body at or under the limit is returned unchanged. Otherwise the largest number of leading rows that fits is kept.
    If the head, frames, note and footer alone do not fit, the body is cut to the limit.
    """
    total = sum(len(section.rows) for section in sections)
    body = _render_body(head, sections, footer, total)
    if len(body) <= MAX_COMMENT_LENGTH:
        return body

    # A body grows with every kept row, so the largest kept count that fits is found by binary search.
    low, high = 0, total
    while low < high:
        middle = (low + high + 1) // 2
        if len(_render_body(head, sections, footer, middle)) <= MAX_COMMENT_LENGTH:
            low = middle
        else:
            high = middle - 1

    cut = _render_body(head, sections, footer, low)
    _log_omitted_rows(sections, low, len(body))
    if len(cut) > MAX_COMMENT_LENGTH:
        logger.warning(
            "PR comment is still over the limit without its table rows; cut to %d characters.", MAX_COMMENT_LENGTH
        )
        cut = cut[:MAX_COMMENT_LENGTH]
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
    ):
        self.gh: GitHub = gh
        self.evaluator: CoverageEvaluator = evaluator
        self.bs_evaluator: Optional[CoverageEvaluator] = bs_evaluator
        self.pr_number: int = pr_number
        self.skip_report_names: frozenset[str] = skip_report_names
        self.ungrouped_reports: list[str] = ungrouped_reports or []
        self.github_repository: str = ActionInputs.get_repository()
        self.github_server_url: str = get_server_url()

    def generate(self) -> bool:
        """
        The method that generates the comment for a single generator.

        @return: True when no comment operation failed (including when there is nothing to do), False when
            the comments could not be read or the add, update or delete request failed. Prints no warning.
        """
        comment_level = ActionInputs.get_comment_level()
        update_comment = ActionInputs.get_update_comment()

        # No comment operation is needed in this mode, so skip the API read call entirely.
        if comment_level == CommentLevelEnum.NONE and not update_comment:
            return True

        title, pr_body = self._get_comment_content(comment_level)

        # Without update-comment each run appends a new comment, so the existing comments are not read.
        if not update_comment:
            return self.gh.add_comment(self.pr_number, pr_body)

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

    def _get_comment_content(self, comment_level: str) -> tuple[str, str]:
        """Build the PR comment title and body for the selected comment level."""
        title = f"**{ActionInputs.get_title()}**"

        if comment_level == CommentLevelEnum.NONE:
            return title, title

        p = ActionInputs.get_pass_symbol()
        f = ActionInputs.get_fail_symbol()

        head = f"{title}\n\n{self.get_basic_table_for_all(p, f)}"
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

            # Filter out reports with no changed files where metric weight is zero
            # This indicates all changed files were filtered due to zero metric weight.
            # Only hide when: had_changed_files_before_filtering is True
            filtered_reports = {k: v for k, v in filtered_reports.items() if not v.had_changed_files_before_filtering}

            # Similar logic for groups
            filtered_groups = {k: v for k, v in filtered_groups.items() if not v.had_changed_files_before_filtering}

            if comment_level != CommentLevelEnum.FULL:
                filtered_groups = self._filter_evaluated_coverage_rows(filtered_groups, comment_level)
                filtered_reports = self._filter_evaluated_coverage_rows(filtered_reports, comment_level)

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

        return title, _fit_to_comment_limit(head, sections, self._get_metadata_footer())

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

    def _get_metadata_footer(self) -> str:
        """Build the metadata footer appended to every non-NONE PR comment.

        The "Generated by" line is always rendered, so the footer is never empty.
        """
        run_id = ActionInputs.get_run_id()
        event = ActionInputs.get_event_name()
        action_ref = ActionInputs.get_action_ref()

        lines = ["---"]
        run_parts: list[str] = []
        if run_id:
            if self.github_repository:
                url = f"{self.github_server_url}/{self.github_repository}/actions/runs/{run_id}"
                run_parts.append(f"Run [{run_id}]({url})")
            else:
                run_parts.append(f"Run `{run_id}`")
        if event:
            run_parts.append(f"Event: `{event}`")
        if run_parts:
            lines.append("*" + " · ".join(run_parts) + "*")

        generated_by = f"Generated by [{ACTION_REPOSITORY}]({ACTION_REPOSITORY_URL})"
        if action_ref:
            generated_by += f" `@{action_ref}`"
        lines.append(f"*{generated_by}*")
        return "\n".join(lines)

    def _filter_evaluated_coverage_rows(
        self,
        evaluated_coverages: dict[str, EvaluatedReportCoverage],
        comment_level: str,
    ) -> dict[str, EvaluatedReportCoverage]:
        """Filter group or report rows according to the selected comment level."""
        return {
            key: coverage
            for key, coverage in evaluated_coverages.items()
            if self._should_include_coverage_row(coverage, comment_level)
        }

    def _should_include_coverage_row(self, coverage: EvaluatedReportCoverage, comment_level: str) -> bool:
        """Return whether one evaluated group or report row should be rendered."""
        if comment_level == CommentLevelEnum.FULL:
            return True

        has_changed_files = self._has_changed_files(coverage)
        is_failing = self._is_failing_coverage(coverage)

        if comment_level == CommentLevelEnum.CHANGED:
            return has_changed_files

        if comment_level == CommentLevelEnum.FAILED:
            return is_failing

        if comment_level == CommentLevelEnum.FAILED_OR_CHANGED:
            return has_changed_files or is_failing

        return False

    def _has_changed_files(self, coverage: EvaluatedReportCoverage) -> bool:
        """Return whether a coverage row represents at least one changed file."""
        if coverage.changed_files_coverage_reached:
            return True

        return (coverage.avg_changed_files_coverage.covered + coverage.avg_changed_files_coverage.missed) > 0

    def _is_failing_coverage(self, coverage: EvaluatedReportCoverage) -> bool:
        """Return whether any threshold represented by the coverage row is failing."""
        return (
            not coverage.overall_passed
            or not coverage.avg_changed_files_passed
            or any(not passed for passed in coverage.changed_files_passed.values())
        )

    def _has_baseline_data(self) -> bool:
        """Return whether baseline evaluator data is available for diff columns."""
        if self.bs_evaluator is None:
            return False

        return bool(self.bs_evaluator.evaluated_reports_coverage) or bool(self.bs_evaluator.evaluated_groups_coverage)

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

        # bs_evaluator is guaranteed non-None here due to _has_baseline_data() check
        bs_evaluator = self.bs_evaluator
        assert bs_evaluator is not None
        # Compute diffs from matched report names only to avoid comparing N current
        # reports against a partial baseline that covers fewer reports.
        diff_o, diff_ch = self._compute_matched_global_diffs(bs_evaluator)
        return self._render_basic_table_with_delta(
            p, f, ActionInputs.get_metric(), overall, changed_files, diff_o, diff_ch
        )

    def _compute_matched_global_diffs(self, bs_evaluator: "CoverageEvaluator") -> tuple[float, float]:
        """Return (diff_overall, diff_changed) using reports matched between both evaluators.

        Matching is path-first (same directory structure) with a name-based fallback for setups
        where current and baseline reports live in different directory trees.
        """
        curr_by_path = self.evaluator.evaluated_reports_coverage
        bs_by_path = bs_evaluator.evaluated_reports_coverage

        matched_paths = set(curr_by_path.keys()) & set(bs_by_path.keys())
        if matched_paths:
            pairs = [(curr_by_path[p], bs_by_path[p]) for p in matched_paths]
        else:
            bs_by_name = {v.name: v for v in bs_by_path.values()}
            pairs = [(curr, bs_by_name[curr.name]) for curr in curr_by_path.values() if curr.name in bs_by_name]

        if not pairs:
            return 0.0, 0.0

        curr_covered_o = bs_covered_o = 0
        curr_covered_ch = bs_covered_ch = 0
        for curr, bs in pairs:
            curr_covered_o += curr.overall_coverage.covered
            bs_covered_o += bs.overall_coverage.covered
            curr_covered_ch += curr.avg_changed_files_coverage.covered
            bs_covered_ch += bs.avg_changed_files_coverage.covered

        global_total_o = sum(
            erc.overall_coverage.covered + erc.overall_coverage.missed for erc in curr_by_path.values()
        )
        global_total_ch = sum(
            erc.avg_changed_files_coverage.covered + erc.avg_changed_files_coverage.missed
            for erc in curr_by_path.values()
        )

        diff_o = round((curr_covered_o - bs_covered_o) / global_total_o * 100, 2) if global_total_o > 0 else 0.0
        diff_ch = round((curr_covered_ch - bs_covered_ch) / global_total_ch * 100, 2) if global_total_ch > 0 else 0.0

        return diff_o, diff_ch

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
        """Calculate baseline deltas for one rendered group row using path-first, name-fallback matching."""
        if self.bs_evaluator is None or evaluated_coverage.name not in self.bs_evaluator.evaluated_groups_coverage:
            return 0.0, 0.0

        group_name = evaluated_coverage.name
        curr_in_group = {
            path: erc for path, erc in self.evaluator.evaluated_reports_coverage.items() if erc.group_name == group_name
        }

        bs_reports = self.bs_evaluator.evaluated_reports_coverage

        matched_paths = set(curr_in_group.keys()) & set(bs_reports.keys())
        if matched_paths:
            pairs = [(curr_in_group[p], bs_reports[p]) for p in matched_paths]
        else:
            bs_by_name = {v.name: v for v in bs_reports.values()}
            pairs = [(curr, bs_by_name[curr.name]) for curr in curr_in_group.values() if curr.name in bs_by_name]

        if not pairs:
            return 0.0, 0.0

        curr_covered_o = bs_covered_o = 0
        curr_covered_ch = bs_covered_ch = 0
        for curr, bs in pairs:
            curr_covered_o += curr.overall_coverage.covered
            bs_covered_o += bs.overall_coverage.covered
            curr_covered_ch += curr.avg_changed_files_coverage.covered
            bs_covered_ch += bs.avg_changed_files_coverage.covered

        group_total_o = sum(
            erc.overall_coverage.covered + erc.overall_coverage.missed for erc in curr_in_group.values()
        )
        group_total_ch = sum(
            erc.avg_changed_files_coverage.covered + erc.avg_changed_files_coverage.missed
            for erc in curr_in_group.values()
        )

        diff_o = round((curr_covered_o - bs_covered_o) / group_total_o * 100, 2) if group_total_o > 0 else 0.0
        diff_ch = round((curr_covered_ch - bs_covered_ch) / group_total_ch * 100, 2) if group_total_ch > 0 else 0.0

        return diff_o, diff_ch

    def _find_baseline_report(self, evaluated_coverage: EvaluatedReportCoverage) -> Optional["EvaluatedReportCoverage"]:
        """Return the matching baseline EvaluatedReportCoverage, or None.

        Tries path-based lookup first (same directory structure), then falls back to name-based
        matching for setups where current and baseline reports live in different directory trees.
        """
        if self.bs_evaluator is None:
            return None
        bs = self.bs_evaluator.evaluated_reports_coverage
        if evaluated_coverage.path and evaluated_coverage.path in bs:
            return bs[evaluated_coverage.path]
        return next((v for v in bs.values() if v.name == evaluated_coverage.name), None)

    def _calculate_baseline_report_diffs(self, evaluated_coverage: EvaluatedReportCoverage) -> tuple[float, float]:
        """Calculate baseline deltas for one rendered report row."""
        bs_coverage = self._find_baseline_report(evaluated_coverage)
        if bs_coverage is None:
            return 0.0, 0.0

        diff_o = evaluated_coverage.overall_coverage_reached - bs_coverage.overall_coverage_reached
        diff_ch = evaluated_coverage.avg_changed_files_coverage_reached - bs_coverage.avg_changed_files_coverage_reached
        return diff_o, diff_ch

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

        lines = []
        for ecr_key in evaluated_reports_coverage.keys():
            curr_erc = evaluated_reports_coverage[ecr_key]
            bs_erc = self._find_baseline_report(curr_erc)
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
