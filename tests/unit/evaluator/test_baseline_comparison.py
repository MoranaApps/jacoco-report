import logging
from typing import Collection, Optional

import pytest

from jacoco_report.evaluator.baseline_comparison import BaselineComparison, CoverageDelta
from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.model.counter import Counter
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage


def _erc(
    name: str,
    overall: tuple[int, int],
    changed: tuple[int, int] = (0, 0),
    path: str = "",
    group_name: str = "Unknown",
) -> EvaluatedReportCoverage:
    """Build an evaluated report from (missed, covered) counters; the reached values follow from them."""
    erc = EvaluatedReportCoverage(name, group_name=group_name, path=path)
    erc.overall_coverage = Counter(*overall)
    erc.overall_coverage_reached = erc.overall_coverage.coverage()
    erc.avg_changed_files_coverage = Counter(*changed)
    erc.avg_changed_files_coverage_reached = erc.avg_changed_files_coverage.coverage()
    return erc


def _evaluator(
    reports: list[EvaluatedReportCoverage], groups: Optional[list[EvaluatedReportCoverage]] = None
) -> CoverageEvaluator:
    evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    evaluator.evaluated_reports_coverage = {erc.path or erc.name: erc for erc in reports}
    evaluator.evaluated_groups_coverage = {erc.name: erc for erc in groups or []}
    return evaluator


# --- has_baseline_data ---


def test_has_no_baseline_data_without_baseline_evaluator():
    assert BaselineComparison(_evaluator([]), None).has_baseline_data() is False


def test_has_no_baseline_data_when_baseline_found_no_report():
    assert BaselineComparison(_evaluator([]), _evaluator([])).has_baseline_data() is False


def test_has_baseline_data_when_baseline_holds_a_report():
    bs = _evaluator([_erc("A", (20, 80))])
    assert BaselineComparison(_evaluator([]), bs).has_baseline_data() is True


# --- report_delta ---


@pytest.mark.parametrize(
    "current, baseline, expected",
    [
        pytest.param((10, 90), (20, 80), CoverageDelta(10.0, 0.0), id="positive"),
        pytest.param((20, 80), (10, 90), CoverageDelta(-10.0, 0.0), id="negative"),
        pytest.param((20, 80), (20, 80), CoverageDelta(0.0, 0.0), id="zero"),
    ],
)
def test_report_delta_is_the_change_in_percentage_points(current, baseline, expected):
    curr = _erc("A", current, path="a.xml")
    bs = _evaluator([_erc("A", baseline, path="a.xml")])

    assert BaselineComparison(_evaluator([curr]), bs).report_delta(curr) == expected


def test_report_delta_is_rounded_to_two_decimals():
    # 2/3 = 66.67 %, 1/3 = 33.33 %
    curr = _erc("A", (1, 2), (2, 1), path="a.xml")
    bs = _evaluator([_erc("A", (2, 1), (1, 2), path="a.xml")])

    assert BaselineComparison(_evaluator([curr]), bs).report_delta(curr) == CoverageDelta(33.34, -33.34)


def test_report_delta_matches_by_name_when_the_path_differs():
    curr = _erc("A", (10, 90), path="current/a.xml")
    bs = _evaluator([_erc("A", (20, 80), path="baseline/a.xml")])

    assert BaselineComparison(_evaluator([curr]), bs).report_delta(curr) == CoverageDelta(10.0, 0.0)


def test_report_delta_is_none_without_a_matching_baseline_report():
    curr = _erc("A", (10, 90), path="a.xml")
    bs = _evaluator([_erc("B", (20, 80), path="b.xml")])

    assert BaselineComparison(_evaluator([curr]), bs).report_delta(curr) is None


def test_report_delta_is_none_without_baseline_evaluator():
    curr = _erc("A", (10, 90), path="a.xml")

    assert BaselineComparison(_evaluator([curr]), None).report_delta(curr) is None


# --- global_delta ---


def test_global_delta_is_none_without_baseline_data():
    curr = _erc("A", (10, 90), path="a.xml")

    assert BaselineComparison(_evaluator([curr]), _evaluator([])).global_delta() is None


def test_global_delta_is_none_when_no_report_matched():
    curr = _erc("A", (10, 90), path="a.xml")
    bs = _evaluator([_erc("B", (20, 80), path="b.xml")])

    assert BaselineComparison(_evaluator([curr]), bs).global_delta() is None


def test_global_delta_is_in_percentage_points_when_the_code_size_changes():
    # Baseline 800/1000 = 80 %; the PR adds 20 instructions, 10 of them covered: 810/1020 = 79.41 %.
    curr = _erc("A", (210, 810), (10, 10), path="a.xml")
    bs = _evaluator([_erc("A", (200, 800), (0, 0), path="a.xml")])

    delta = BaselineComparison(_evaluator([curr]), bs).global_delta()

    assert delta == CoverageDelta(-0.59, 50.0)


def test_global_delta_counts_unmatched_reports_as_unchanged():
    # A: 80 % -> 90 % (100 instructions each); B has no baseline and stays at 50/100.
    # Current 140/200 = 70 %; baseline with B unchanged 130/200 = 65 %.
    curr_a = _erc("A", (10, 90), path="a.xml")
    curr_b = _erc("B", (50, 50), path="b.xml")
    bs = _evaluator([_erc("A", (20, 80), path="a.xml")])

    assert BaselineComparison(_evaluator([curr_a, curr_b]), bs).global_delta() == CoverageDelta(5.0, 0.0)


def test_global_delta_matches_by_name_when_no_path_matches():
    curr = _erc("A", (10, 90), path="current/a.xml")
    bs = _evaluator([_erc("A", (20, 80), path="baseline/a.xml")])

    assert BaselineComparison(_evaluator([curr]), bs).global_delta() == CoverageDelta(10.0, 0.0)


def test_global_changed_files_delta_is_zero_without_current_changed_files():
    # The baseline still holds data for a changed file that the current report no longer has.
    curr = _erc("A", (10, 90), (0, 0), path="a.xml")
    bs = _evaluator([_erc("A", (20, 80), (5, 5), path="a.xml")])

    assert BaselineComparison(_evaluator([curr]), bs).global_delta() == CoverageDelta(10.0, 0.0)


def test_global_delta_has_no_negative_zero():
    # 33.332 % against 33.333 %: the change rounds to zero.
    curr = _erc("A", (66668, 33332), path="a.xml")
    bs = _evaluator([_erc("A", (2, 1), path="a.xml")])

    delta = BaselineComparison(_evaluator([curr]), bs).global_delta()

    assert delta is not None
    assert str(delta.overall) == "0.0"


# --- group_delta ---


def test_group_delta_is_none_when_the_group_has_no_baseline():
    curr = _erc("A", (10, 90), path="a.xml", group_name="g")
    group = _erc("g", (10, 90), group_name="g")
    bs = _evaluator([_erc("A", (20, 80), path="a.xml", group_name="g")])

    assert BaselineComparison(_evaluator([curr], [group]), bs).group_delta(group) is None


def test_group_delta_is_none_when_no_report_of_the_group_matched():
    curr = _erc("A", (10, 90), path="a.xml", group_name="g")
    group = _erc("g", (10, 90), group_name="g")
    bs_group = _erc("g", (20, 80), group_name="g")
    bs = _evaluator([_erc("B", (20, 80), path="b.xml", group_name="g")], [bs_group])

    assert BaselineComparison(_evaluator([curr], [group]), bs).group_delta(group) is None


def test_group_delta_is_in_percentage_points_when_the_code_size_changes():
    curr = _erc("A", (210, 810), path="a.xml", group_name="g")
    other = _erc("B", (0, 100), path="b.xml", group_name="other")
    group = _erc("g", (210, 810), group_name="g")
    bs_group = _erc("g", (200, 800), group_name="g")
    bs = _evaluator([_erc("A", (200, 800), path="a.xml", group_name="g")], [bs_group])

    delta = BaselineComparison(_evaluator([curr, other], [group]), bs).group_delta(group)

    assert delta == CoverageDelta(-0.59, 0.0)


def test_group_delta_matches_reports_by_name_when_no_path_matches():
    curr = _erc("A", (210, 810), path="current/a.xml", group_name="g")
    group = _erc("g", (210, 810), group_name="g")
    bs_group = _erc("g", (200, 800), group_name="g")
    bs = _evaluator([_erc("A", (200, 800), path="baseline/a.xml", group_name="g")], [bs_group])

    delta = BaselineComparison(_evaluator([curr], [group]), bs).group_delta(group)

    assert delta == CoverageDelta(-0.59, 0.0)


# --- CoverageDelta ---


def test_coverage_delta_serializes_to_a_json_object():
    assert CoverageDelta(1.5, -0.25).to_dict() == {"overall": 1.5, "changed_files": -0.25}


# --- no_decrease_violations ---

NO_BASELINE = (
    "'no-decrease' needs a baseline, but no baseline report was found. "
    "Set 'baseline-paths' to the JaCoCo reports of the base branch."
)
NO_MATCH = (
    "'no-decrease' found baseline reports, but none matches a current report by path or report name, "
    "so no coverage drop could be checked."
)


def _no_decrease(
    reports: list[EvaluatedReportCoverage],
    bs: Optional[CoverageEvaluator],
    groups: Optional[list[EvaluatedReportCoverage]] = None,
    max_decrease: float = 0.0,
    unchanged: Collection[EvaluatedReportCoverage] = (),
    evidence: Collection[EvaluatedReportCoverage] = (),
) -> list[str]:
    return BaselineComparison(_evaluator(reports, groups), bs).no_decrease_violations(max_decrease, unchanged, evidence)


def test_no_decrease_passes_when_coverage_rises():
    curr = _erc("A", (10, 90), path="a.xml")
    bs = _evaluator([_erc("A", (20, 80), path="a.xml")])

    assert _no_decrease([curr], bs) == []


def test_no_decrease_reports_the_global_and_the_report_drop():
    curr = _erc("A", (30, 70), path="a.xml")
    bs = _evaluator([_erc("A", (20, 80), path="a.xml")])

    assert _no_decrease([curr], bs) == [
        "Global overall coverage dropped from 80.0 to 70.0 (-10.0 percentage points) against the baseline, "
        "more than 'max-decrease' 0.0.",
        "Report 'A' overall coverage dropped from 80.0 to 70.0 (-10.0 percentage points) against the baseline, "
        "more than 'max-decrease' 0.0.",
    ]


@pytest.mark.parametrize(
    "max_decrease, violated",
    [
        pytest.param(9.99, True, id="drop-above-tolerance"),
        pytest.param(10.0, False, id="drop-equal-to-tolerance"),
        pytest.param(10.5, False, id="drop-below-tolerance"),
    ],
)
def test_no_decrease_tolerates_a_drop_up_to_max_decrease(max_decrease, violated):
    curr = _erc("A", (30, 70), path="a.xml")
    bs = _evaluator([_erc("A", (20, 80), path="a.xml")])

    assert bool(_no_decrease([curr], bs, max_decrease=max_decrease)) is violated


def test_no_decrease_passes_when_only_covered_code_was_deleted():
    # Coverage falls from 80 % to 75 %, but the missed count stays at 20: nothing new is left uncovered.
    curr = _erc("A", (20, 60), path="a.xml")
    bs = _evaluator([_erc("A", (20, 80), path="a.xml")])

    assert _no_decrease([curr], bs) == []


def test_no_decrease_does_not_gate_the_changed_files_coverage():
    curr = _erc("A", (10, 90), (50, 50), path="a.xml")
    bs = _evaluator([_erc("A", (20, 80), (0, 100), path="a.xml")])

    assert _no_decrease([curr], bs) == []


def test_no_decrease_without_baseline_gives_one_violation():
    curr = _erc("A", (30, 70), path="a.xml")

    assert _no_decrease([curr], None) == [NO_BASELINE]
    assert _no_decrease([curr], _evaluator([])) == [NO_BASELINE]


def test_no_decrease_with_baseline_but_no_matched_report_gives_one_violation():
    curr = _erc("A", (30, 70), path="a.xml")
    bs = _evaluator([_erc("B", (20, 80), path="b.xml")])

    assert _no_decrease([curr], bs) == [NO_MATCH]


def test_no_decrease_skips_a_report_without_baseline_and_logs_it(caplog):
    curr_a = _erc("A", (30, 70), path="a.xml")
    curr_b = _erc("B", (50, 50), path="b.xml")
    bs = _evaluator([_erc("A", (20, 80), path="a.xml")])
    caplog.set_level(logging.INFO, logger="jacoco_report.evaluator.baseline_comparison")

    # Global: 80/120 = 60 % now; the baseline swaps A back and keeps B unchanged: 70/130 = 65 %.
    assert _no_decrease([curr_a, curr_b], bs) == [
        "Global overall coverage dropped from 65.0 to 60.0 (-5.0 percentage points) against the baseline, "
        "more than 'max-decrease' 0.0.",
        "Report 'A' overall coverage dropped from 80.0 to 70.0 (-10.0 percentage points) against the baseline, "
        "more than 'max-decrease' 0.0.",
    ]
    assert "Report 'B' has no matching baseline report, skipped by 'no-decrease'." in caplog.text


def test_no_decrease_skips_a_group_without_baseline_and_checks_the_others(caplog):
    curr_a = _erc("A", (30, 70), path="a.xml", group_name="g")
    curr_b = _erc("B", (50, 50), path="b.xml", group_name="h")
    group_g = _erc("g", (30, 70), group_name="g")
    group_h = _erc("h", (50, 50), group_name="h")
    bs = _evaluator(
        [_erc("A", (20, 80), path="a.xml", group_name="g"), _erc("B", (50, 50), path="b.xml", group_name="h")],
        [_erc("g", (20, 80), group_name="g")],
    )
    caplog.set_level(logging.INFO, logger="jacoco_report.evaluator.baseline_comparison")

    assert _no_decrease([curr_a, curr_b], bs, groups=[group_g, group_h]) == [
        "Global overall coverage dropped from 65.0 to 60.0 (-5.0 percentage points) against the baseline, "
        "more than 'max-decrease' 0.0.",
        "Group 'g' overall coverage dropped from 80.0 to 70.0 (-10.0 percentage points) against the baseline, "
        "more than 'max-decrease' 0.0.",
        "Report 'A' overall coverage dropped from 80.0 to 70.0 (-10.0 percentage points) against the baseline, "
        "more than 'max-decrease' 0.0.",
    ]
    assert "Group 'h' has no matching baseline group or report, skipped by 'no-decrease'." in caplog.text


def test_no_decrease_checks_an_unchanged_report_after_the_regular_rows():
    curr_a = _erc("A", (30, 70), path="a.xml")
    unchanged_u = _erc("U", (30, 70), path="u.xml")
    bs = _evaluator([_erc("A", (20, 80), path="a.xml"), _erc("U", (20, 80), path="u.xml")])

    assert _no_decrease([curr_a], bs, unchanged=[unchanged_u]) == [
        "Global overall coverage dropped from 80.0 to 70.0 (-10.0 percentage points) against the baseline, "
        "more than 'max-decrease' 0.0.",
        "Report 'A' overall coverage dropped from 80.0 to 70.0 (-10.0 percentage points) against the baseline, "
        "more than 'max-decrease' 0.0.",
        "Report 'U' overall coverage dropped from 80.0 to 70.0 (-10.0 percentage points) against the baseline, "
        "more than 'max-decrease' 0.0.",
    ]


def test_no_decrease_unchanged_report_without_match_is_skipped_and_logged(caplog):
    curr_a = _erc("A", (20, 80), path="a.xml")
    unchanged_u = _erc("U", (30, 70), path="u.xml")
    bs = _evaluator([_erc("A", (20, 80), path="a.xml")])
    caplog.set_level(logging.INFO, logger="jacoco_report.evaluator.baseline_comparison")

    assert _no_decrease([curr_a], bs, unchanged=[unchanged_u]) == []
    assert "Report 'U' has no matching baseline report, skipped by 'no-decrease'." in caplog.text


def test_no_decrease_only_unchanged_reports_match_skips_the_global_row_with_a_log(caplog):
    curr_a = _erc("A", (30, 70), path="a.xml")
    unchanged_u = _erc("U", (30, 70), path="u.xml")
    bs = _evaluator([_erc("U", (20, 80), path="u.xml")])
    caplog.set_level(logging.INFO, logger="jacoco_report.evaluator.baseline_comparison")

    assert _no_decrease([curr_a], bs, unchanged=[unchanged_u]) == [
        "Report 'U' overall coverage dropped from 80.0 to 70.0 (-10.0 percentage points) against the baseline, "
        "more than 'max-decrease' 0.0.",
    ]
    assert "Global overall coverage has no matching baseline report, skipped by 'no-decrease'." in caplog.text
    assert "Report 'A' has no matching baseline report, skipped by 'no-decrease'." in caplog.text


def test_no_decrease_no_match_stays_one_violation_when_unchanged_reports_do_not_match():
    curr_a = _erc("A", (30, 70), path="a.xml")
    unchanged_u = _erc("U", (30, 70), path="u.xml")
    bs = _evaluator([_erc("B", (20, 80), path="b.xml")])

    assert _no_decrease([curr_a], bs, unchanged=[unchanged_u]) == [NO_MATCH]


def test_no_decrease_match_evidence_prevents_no_match_and_skips_the_global_row(caplog):
    # A new module: its report has no baseline, the matching report is filtered out of the evaluator.
    new_module = _erc("New", (30, 70), path="new.xml")
    filtered_core = _erc("Core", (20, 80), path="core.xml")
    bs = _evaluator([_erc("Core", (20, 80), path="core.xml")])
    caplog.set_level(logging.INFO, logger="jacoco_report.evaluator.baseline_comparison")

    assert _no_decrease([new_module], bs, evidence=[filtered_core]) == []
    assert "Global overall coverage has no matching baseline report, skipped by 'no-decrease'." in caplog.text
    assert "Report 'New' has no matching baseline report, skipped by 'no-decrease'." in caplog.text


def test_no_decrease_match_evidence_is_never_reported_even_when_it_dropped():
    new_module = _erc("New", (30, 70), path="new.xml")
    filtered_core = _erc("Core", (30, 70), path="core.xml")
    bs = _evaluator([_erc("Core", (20, 80), path="core.xml")])

    assert _no_decrease([new_module], bs, evidence=[filtered_core]) == []


def test_no_decrease_no_match_anywhere_is_still_no_match_with_evidence_that_does_not_match():
    new_module = _erc("New", (30, 70), path="new.xml")
    filtered_core = _erc("Core", (30, 70), path="core.xml")
    bs = _evaluator([_erc("B", (20, 80), path="b.xml")])

    assert _no_decrease([new_module], bs, evidence=[filtered_core]) == [NO_MATCH]


def test_no_decrease_without_aggregate_rows_checks_only_the_report_rows(caplog):
    # Reports A and B are unchanged in coverage, but the global coverage fell because B grew: only report rows count.
    curr_a = _erc("A", (10, 90), path="a.xml")
    curr_b = _erc("B", (180, 20), path="b.xml")
    bs = _evaluator([_erc("A", (10, 90), path="a.xml"), _erc("B", (90, 10), path="b.xml")])
    caplog.set_level(logging.INFO, logger="jacoco_report.evaluator.baseline_comparison")

    assert (
        BaselineComparison(_evaluator([curr_a, curr_b]), bs).no_decrease_violations(0.0, include_aggregate_rows=False)
        == []
    )
    assert "Global overall coverage" not in caplog.text


def test_no_decrease_without_aggregate_rows_still_checks_a_report_drop():
    curr_a = _erc("A", (30, 70), path="a.xml")
    bs = _evaluator([_erc("A", (20, 80), path="a.xml")])

    assert BaselineComparison(_evaluator([curr_a]), bs).no_decrease_violations(0.0, include_aggregate_rows=False) == [
        "Report 'A' overall coverage dropped from 80.0 to 70.0 (-10.0 percentage points) against the baseline, "
        "more than 'max-decrease' 0.0."
    ]


def test_no_decrease_without_aggregate_rows_still_gives_no_match_when_nothing_matches():
    curr_a = _erc("A", (30, 70), path="a.xml")
    bs = _evaluator([_erc("B", (20, 80), path="b.xml")])

    assert BaselineComparison(_evaluator([curr_a]), bs).no_decrease_violations(0.0, include_aggregate_rows=False) == [
        NO_MATCH
    ]


# --- report_dropped and group_dropped ---


@pytest.mark.parametrize(
    "current, baseline, max_decrease, dropped",
    [
        pytest.param((30, 70), (20, 80), 0.0, True, id="drop-above-tolerance"),
        pytest.param((30, 70), (20, 80), 10.0, False, id="drop-within-tolerance"),
        pytest.param((20, 60), (20, 80), 0.0, False, id="covered-code-deleted-missed-not-grown"),
        pytest.param((10, 90), (20, 80), 0.0, False, id="rise"),
    ],
)
def test_report_dropped_follows_the_no_decrease_rule(current, baseline, max_decrease, dropped):
    curr = _erc("A", current, path="a.xml")
    bs = _evaluator([_erc("A", baseline, path="a.xml")])

    assert BaselineComparison(_evaluator([curr]), bs).report_dropped(curr, max_decrease) is dropped


def test_report_dropped_is_false_without_a_matching_baseline_report():
    curr = _erc("A", (30, 70), path="a.xml")
    bs = _evaluator([_erc("B", (20, 80), path="b.xml")])

    assert BaselineComparison(_evaluator([curr]), bs).report_dropped(curr, 0.0) is False


def test_report_dropped_is_false_without_baseline_data():
    curr = _erc("A", (30, 70), path="a.xml")

    assert BaselineComparison(_evaluator([curr]), None).report_dropped(curr, 0.0) is False


@pytest.mark.parametrize(
    "max_decrease, dropped",
    [
        pytest.param(0.0, True, id="drop-above-tolerance"),
        pytest.param(10.0, False, id="drop-within-tolerance"),
    ],
)
def test_group_dropped_follows_the_no_decrease_rule(max_decrease, dropped):
    curr = _erc("A", (30, 70), path="a.xml", group_name="g")
    group = _erc("g", (30, 70), group_name="g")
    bs = _evaluator([_erc("A", (20, 80), path="a.xml", group_name="g")], [_erc("g", (20, 80), group_name="g")])

    comparison = BaselineComparison(_evaluator([curr], [group]), bs)

    assert comparison.group_dropped(group, max_decrease) is dropped


def test_group_dropped_is_false_without_a_matching_baseline_group():
    curr = _erc("A", (30, 70), path="a.xml", group_name="g")
    group = _erc("g", (30, 70), group_name="g")
    bs = _evaluator([_erc("B", (20, 80), path="b.xml", group_name="h")])

    assert BaselineComparison(_evaluator([curr], [group]), bs).group_dropped(group, 0.0) is False
