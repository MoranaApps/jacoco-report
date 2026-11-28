"""
The report body: its parts, and the cut that keeps it within GitHub's size limits.
"""

import logging
from dataclasses import dataclass
from typing import NamedTuple

logger = logging.getLogger(__name__)

# The limit GitHub enforces on a comment body. The note in a cut body always states it.
GITHUB_COMMENT_LIMIT = 65_536
# The cap this module enforces. It equals GitHub's limit; tests lower it to exercise the boundary.
MAX_COMMENT_LENGTH = GITHUB_COMMENT_LIMIT

# GitHub's job summary limit for one step. Measured in UTF-8 bytes. Tests lower it to exercise the boundary.
GITHUB_SUMMARY_LIMIT = 1_048_576
MAX_SUMMARY_BYTES = GITHUB_SUMMARY_LIMIT

UNGROUPED_LOG_HEADER = "Reports not assigned to any group:"


class Section(NamedTuple):
    """A cuttable part of the comment: lines before its rows, its rows, and lines after them."""

    log_header: str
    header: list[str]
    rows: list[str]
    trailing: list[str]
    # A section whose rows are all cut still renders its header and trailing lines (the ungrouped-reports frame).
    frame_kept: bool


def split_table(section: str) -> Section:
    """Split a rendered table into its two header lines and its rows. A table with any other line is not cut."""
    lines = section.split("\n")
    rest = lines[2:]
    if rest and all(line.startswith("|") for line in rest):
        return Section("\n".join(lines[:2]), lines[:2], rest, [], False)
    return Section("", lines, [], [], False)


def split_ungrouped(warning: str) -> Section:
    """Split the ungrouped-reports warning into its frame before the items, its `- ` items and the frame after."""
    lines = warning.split("\n")
    first = next((i for i, line in enumerate(lines) if line.startswith("- ")), len(lines))
    end = first
    while end < len(lines) and lines[end].startswith("- "):
        end += 1
    return Section(UNGROUPED_LOG_HEADER, lines[:first], lines[first:end], lines[end:], True)


@dataclass(frozen=True)
class CutRules:
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


class ReportParts(NamedTuple):
    """The parts of a report body. The PR comment and the job summary are both joined from them."""

    head: str
    sections: list[Section]
    footer: str


def comment_rules(summary_written: bool, run_url: str) -> CutRules:
    """Rules for the PR comment. Its note points to the job summary only when the summary holds the report."""
    tail = f"see the {_link('job summary', run_url)}." if summary_written else "see the job log."
    return CutRules(
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


def summary_rules(run_url: str) -> CutRules:
    """Rules for the job summary: cut only at its own limit, and the full body goes to the job log."""
    return CutRules(
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


def _total_rows(parts: ReportParts) -> int:
    """Return the number of cuttable rows in a report body."""
    return sum(len(section.rows) for section in parts.sections)


def _kept_rows_per_section(sections: list[Section], keep: int) -> list[int]:
    """Count the leading rows of each section that are kept when the first `keep` rows of all sections are kept."""
    kept: list[int] = []
    remaining = keep
    for section in sections:
        count = min(len(section.rows), remaining)
        kept.append(count)
        remaining -= count
    return kept


def _render_body(parts: ReportParts, keep: int, rules: CutRules) -> str:
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


def _log_cut(parts: ReportParts, keep: int, body: str, rules: CutRules) -> None:
    """Log a cut body: the job summary logs the whole uncut body, the PR comment its omitted rows by section."""
    logger.warning(rules.cut_warning, rules.size(body), rules.limit, _total_rows(parts) - keep)
    if rules.log_full_body:
        logger.info("Full report (job summary was cut):\n%s", body)
        return
    for section, count in zip(parts.sections, _kept_rows_per_section(parts.sections, keep)):
        if section.rows and count < len(section.rows):
            logger.info("Omitted from the PR comment:\n%s", "\n".join([section.log_header, *section.rows[count:]]))


def fit_to_limit(parts: ReportParts, rules: CutRules) -> str:
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
