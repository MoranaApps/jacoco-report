from typing import Optional

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
