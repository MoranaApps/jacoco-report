"""
Tests for baseline delta calculation when baseline exists only for a subset of the report XML files.

Scenario (used in the integration test below)
----------------------------------------------
  Current:   Module A = 80%, B = 90%, C = 70%, D = 85%
             Combined: Counter(75, 325) → 325/400 = 81.25%
  Baseline:  only Module A at 50%
             bs_evaluator.evaluated_reports_coverage = {"Module A": ...}

  Global diff (intersection of matched names):
    Matched: only Module A → 80.0% − 50.0% = +30.0%

  Per-report A: 80.0% − 50.0% = +30.0%
  Per-report B, C, D: 0.0%  (name not in baseline → name lookup returns default)
"""

import pytest

from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.generator.pr_comment_generator import PRCommentGenerator
from jacoco_report.jacoco_report import JaCoCoReport
from jacoco_report.model.counter import Counter
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.model.report_group import ReportGroup
from jacoco_report.utils.enums import CommentLevelEnum


# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------

_CHANGED_FILES = [
    "com/partial_baseline/module_a/FileA.java",
    "com/partial_baseline/module_b/FileB.java",
    "com/partial_baseline/module_c/FileC.java",
    "com/partial_baseline/module_d/FileD.java",
]


def _make_erc(
    name: str,
    overall: float,
    changed: float,
    overall_counter: tuple[int, int],
    changed_counter: tuple[int, int],
    group_name: str = "Unknown",
    changed_files: dict[str, float] | None = None,
) -> EvaluatedReportCoverage:
    erc = EvaluatedReportCoverage(name, group_name=group_name)
    erc.overall_coverage_reached = overall
    erc.avg_changed_files_coverage_reached = changed
    erc.overall_coverage = Counter(overall_counter[0], overall_counter[1])
    erc.avg_changed_files_coverage = Counter(changed_counter[0], changed_counter[1])
    erc.overall_passed = True
    erc.avg_changed_files_passed = True
    erc.overall_coverage_threshold = 0.0
    erc.changed_files_threshold = 0.0
    erc.per_changed_file_threshold = 0.0
    erc.changed_files_coverage_reached = changed_files or {}
    erc.changed_files_passed = {k: True for k in (changed_files or {})}
    return erc


def _make_group_erc(
    name: str,
    overall: float,
    overall_counter: tuple[int, int],
) -> EvaluatedReportCoverage:
    erc = EvaluatedReportCoverage(name, group_name=name)
    erc.overall_coverage_reached = overall
    erc.avg_changed_files_coverage_reached = 0.0
    erc.overall_coverage = Counter(overall_counter[0], overall_counter[1])
    erc.avg_changed_files_coverage = Counter(0, 0)
    erc.overall_passed = True
    erc.avg_changed_files_passed = True
    erc.overall_coverage_threshold = 0.0
    erc.changed_files_threshold = 0.0
    erc.per_changed_file_threshold = 0.0
    return erc


def _mock_common_action_inputs(mocker) -> None:
    """Patch ActionInputs methods needed by PRCommentGenerator unit tests."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=0.0)
    mocker.patch(
        "jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=0.0
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_pass_symbol", return_value="✅")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_fail_symbol", return_value="❌")
    mocker.patch(
        "jacoco_report.action_inputs.ActionInputs.get_repository", return_value="MoranaApps/jacoco-report"
    )


# ---------------------------------------------------------------------------
# 1. Integration test — global table with partial baseline
# ---------------------------------------------------------------------------

def test_global_table_diff_wrong_with_partial_baseline(jacoco_report: JaCoCoReport, mocker):
    """
    Calculation
    -----------
    Current (4 XML files, all changed):
      Module A: missed=20, covered=80 → round(80/100*100, 2) = 80.0%
      Module B: missed=10, covered=90 → round(90/100*100, 2) = 90.0%
      Module C: missed=30, covered=70 → round(70/100*100, 2) = 70.0%
      Module D: missed=15, covered=85 → round(85/100*100, 2) = 85.0%
      Combined counter: Counter(20+10+30+15, 80+90+70+85) = Counter(75, 325)
      Global: round(325/400*100, 2) = 81.25%

    Baseline (1 XML file — only Module A):
      Module A: missed=50, covered=50 → round(50/100*100, 2) = 50.0%

    Global diff (intersection: only "Partial Baseline Module A" matched, weighted to global total):
      (80 − 50) / 400 × 100 = 30 / 400 × 100 = +7.5%

    Per-report diffs (name lookup):
      "Partial Baseline Module A" found in bs → 80.0 − 50.0 = +30.0%
      "Partial Baseline Module B" not in bs → 0.0%
      "Partial Baseline Module C" not in bs → 0.0%
      "Partial Baseline Module D" not in bs → 0.0%

    Per-file diffs (report matched first, then file path):
      FileA: report "Partial Baseline Module A" in bs AND "...FileA.java" in bs
             → 80.0 − 50.0 = +30.0%
      FileB: report "Partial Baseline Module B" not in bs → 0.0%
      FileC: report "Partial Baseline Module C" not in bs → 0.0%
      FileD: report "Partial Baseline Module D" not in bs → 0.0%
    """
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value="pull_request")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_id", return_value="")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_action_ref", return_value="")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_started_at", return_value="")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_token", return_value="fake_token")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_level", return_value=CommentLevelEnum.FULL)
    mocker.patch(
        "jacoco_report.action_inputs.ActionInputs.get_paths",
        return_value=["tests/data/partial_baseline/**/*.xml"],
    )
    mocker.patch(
        "jacoco_report.action_inputs.ActionInputs.get_baseline_paths",
        return_value=["tests/data_baseline_partial/module_a/*.xml"],
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=0.0)
    mocker.patch(
        "jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=0.0
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_thresholds_default", return_value=(0.0, 0.0, 0.0))
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_repository", return_value="MoranaApps/jacoco-report")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value=False)
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_number", return_value=35)
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_changed_files", return_value=_CHANGED_FILES)
    mock_add_comment = mocker.patch("jacoco_report.utils.github.GitHub.add_comment", return_value=None)

    jacoco_report.run()

    # Combined counter: Counter(75, 325) → 325/400 = 81.25%
    assert jacoco_report.total_overall_coverage == 81.25
    assert jacoco_report.total_changed_files_coverage == 81.25

    generated_comment = mock_add_comment.call_args[0][1]

    # Global diff: (80−50)/400×100 = 7.5% (weighted to all 4 reports' 400 instructions)
    assert "| **Overall**       | 81.25% | 0.0% | +7.5% | ✅ |" in generated_comment
    assert "| **Changed Files** | 81.25% | 0.0% | +7.5% | ✅ |" in generated_comment

    # Module A: name matched in baseline → 80.0 − 50.0 = +30.0%
    assert (
        "| `Partial Baseline Module A` | 80.0% / 80.0% | 0.0% / 0.0% | +30.0% / +30.0% | ✅/✅ |"
        in generated_comment
    )
    # Modules B/C/D: name not in baseline → 0.0%
    assert (
        "| `Partial Baseline Module B` | 90.0% / 90.0% | 0.0% / 0.0% | 0.0% / 0.0% | ✅/✅ |"
        in generated_comment
    )
    assert (
        "| `Partial Baseline Module C` | 70.0% / 70.0% | 0.0% / 0.0% | 0.0% / 0.0% | ✅/✅ |"
        in generated_comment
    )
    assert (
        "| `Partial Baseline Module D` | 85.0% / 85.0% | 0.0% / 0.0% | 0.0% / 0.0% | ✅/✅ |"
        in generated_comment
    )

    # FileA: report in bs AND file in bs → 80.0 − 50.0 = +30.0%
    assert "| 80.0% | 0.0% | +30.0% | ✅ |" in generated_comment
    # FileB/C/D: report not in bs → 0.0%
    assert "| 90.0% | 0.0% | 0.0% | ✅ |" in generated_comment
    assert "| 70.0% | 0.0% | 0.0% | ✅ |" in generated_comment
    assert "| 85.0% | 0.0% | 0.0% | ✅ |" in generated_comment


# ---------------------------------------------------------------------------
# 2. Unit test — group table with partial group baseline
# ---------------------------------------------------------------------------

def test_group_table_diff_wrong_with_partial_group_baseline(mocker):
    """
    Calculation
    -----------
    group-alpha current (Module A + Module B):
      Counter(20+10, 80+90) = Counter(30, 170) → 170/200 = 85.0%

    group-alpha baseline (only Module A at 50%):
      Counter(50, 50) → 50/100 = 50.0%

    group-alpha diff (intersection: only Module A matched, weighted to group total):
      group-alpha total: Counter(20+10, 80+90) = 200 instructions
      matched Module A: curr_covered=80, bs_covered=50
      diff_o = (80 − 50) / 200 × 100 = 30 / 200 × 100 = +15.0%

    group-beta current (Module C + Module D):
      Counter(30+15, 70+85) = Counter(45, 155) → 155/200 = 77.5%
      "group-beta" not in bs_evaluator.evaluated_groups_coverage
      calculate_baseline_group_diffs("group-beta"): returns (0.0, 0.0)

    Global diff (intersection: only Module A matched, weighted to global total):
      global total: 400 instructions (all 4 reports)
      matched Module A: curr_covered=80, bs_covered=50
      diff = (80 − 50) / 400 × 100 = 30 / 400 × 100 = +7.5%
    """
    _mock_common_action_inputs(mocker)

    evaluator = CoverageEvaluator(
        report_files_coverage=[],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
        report_groups=[ReportGroup("group-alpha", []), ReportGroup("group-beta", [])],
    )
    evaluator.total_coverage_overall = 81.25
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files = 0.0
    evaluator.total_coverage_changed_files_passed = True

    evaluator.evaluated_reports_coverage = {
        "Partial Baseline Module A": _make_erc(
            "Partial Baseline Module A", 80.0, 80.0, (20, 80), (20, 80), group_name="group-alpha"
        ),
        "Partial Baseline Module B": _make_erc(
            "Partial Baseline Module B", 90.0, 90.0, (10, 90), (10, 90), group_name="group-alpha"
        ),
        "Partial Baseline Module C": _make_erc(
            "Partial Baseline Module C", 70.0, 70.0, (30, 70), (30, 70), group_name="group-beta"
        ),
        "Partial Baseline Module D": _make_erc(
            "Partial Baseline Module D", 85.0, 85.0, (15, 85), (15, 85), group_name="group-beta"
        ),
    }
    # group-alpha: Counter(30, 170) → 85.0%; group-beta: Counter(45, 155) → 77.5%
    erc_alpha = _make_group_erc("group-alpha", 85.0, (30, 170))
    erc_beta = _make_group_erc("group-beta", 77.5, (45, 155))
    evaluator.evaluated_groups_coverage = {"group-alpha": erc_alpha, "group-beta": erc_beta}

    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
    )
    bs_evaluator.total_coverage_overall = 50.0
    bs_evaluator.total_coverage_overall_passed = True
    bs_evaluator.total_coverage_changed_files = 0.0
    bs_evaluator.total_coverage_changed_files_passed = True
    bs_evaluator.evaluated_reports_coverage = {
        "Partial Baseline Module A": _make_erc(
            "Partial Baseline Module A", 50.0, 50.0, (50, 50), (50, 50), group_name="group-alpha"
        ),
    }
    # group-alpha baseline: Counter(50, 50) → 50.0%
    bs_erc_alpha = _make_group_erc("group-alpha", 50.0, (50, 50))
    bs_evaluator.evaluated_groups_coverage = {"group-alpha": bs_erc_alpha}

    mock_gh = mocker.Mock()
    generator = PRCommentGenerator(mock_gh, evaluator, bs_evaluator, 35)

    # Global diff: (80−50)/400×100 = 7.5% (weighted to all 4 reports' 400 instructions)
    global_table = generator.get_basic_table_for_all("✅", "❌")
    assert "+7.5%" in global_table

    # group-alpha diff: (80−50)/200×100 = 15.0% (weighted to group-alpha's 200 instructions)
    groups_table = generator.get_groups_table("✅", "❌")
    assert "+15.0%" in groups_table

    # group-beta: name not in baseline groups → diff = 0.0%
    diff_o, diff_ch = generator.calculate_baseline_group_diffs(erc_beta)
    assert diff_o == 0.0
    assert diff_ch == 0.0


# ---------------------------------------------------------------------------
# 3. Sanity check — per-report diffs via name lookup
# ---------------------------------------------------------------------------

def test_per_report_diffs_correct_despite_wrong_global_diff(mocker):
    """
    _calculate_baseline_report_diffs does a name lookup in bs_evaluator.evaluated_reports_coverage.

    Calculation
    -----------
    bs_evaluator.evaluated_reports_coverage keys = {"Module A"}

    Module A lookup:
      "Module A" found in bs_evaluator.evaluated_reports_coverage
      diff_o  = 80.0 (current) − 50.0 (baseline) = 30.0
      diff_ch = 80.0 (current) − 50.0 (baseline) = 30.0

    Module B lookup:
      "Module B" not in bs_evaluator.evaluated_reports_coverage → (0.0, 0.0)

    Module C lookup:
      "Module C" not in bs_evaluator.evaluated_reports_coverage → (0.0, 0.0)

    Module D lookup:
      "Module D" not in bs_evaluator.evaluated_reports_coverage → (0.0, 0.0)
    """
    _mock_common_action_inputs(mocker)

    evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    evaluator.total_coverage_overall = 81.25
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files = 81.25
    evaluator.total_coverage_changed_files_passed = True

    erc_a = _make_erc("Module A", 80.0, 80.0, (20, 80), (20, 80))
    erc_b = _make_erc("Module B", 90.0, 90.0, (10, 90), (10, 90))
    erc_c = _make_erc("Module C", 70.0, 70.0, (30, 70), (30, 70))
    erc_d = _make_erc("Module D", 85.0, 85.0, (15, 85), (15, 85))
    evaluator.evaluated_reports_coverage = {
        "Module A": erc_a,
        "Module B": erc_b,
        "Module C": erc_c,
        "Module D": erc_d,
    }
    evaluator.evaluated_groups_coverage = {}

    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    bs_evaluator.total_coverage_overall = 50.0
    bs_evaluator.total_coverage_overall_passed = True
    bs_evaluator.total_coverage_changed_files = 50.0
    bs_evaluator.total_coverage_changed_files_passed = True
    bs_evaluator.evaluated_reports_coverage = {
        "Module A": _make_erc("Module A", 50.0, 50.0, (50, 50), (50, 50)),
    }
    bs_evaluator.evaluated_groups_coverage = {}

    mock_gh = mocker.Mock()
    generator = PRCommentGenerator(mock_gh, evaluator, bs_evaluator, 35)

    # Module A: name found → diff_o = 80.0 − 50.0 = 30.0
    diff_o, diff_ch = generator._calculate_baseline_report_diffs(erc_a)
    assert diff_o == 30.0
    assert diff_ch == 30.0

    # Modules B, C, D: name not found → (0.0, 0.0)
    assert generator._calculate_baseline_report_diffs(erc_b) == (0.0, 0.0)
    assert generator._calculate_baseline_report_diffs(erc_c) == (0.0, 0.0)
    assert generator._calculate_baseline_report_diffs(erc_d) == (0.0, 0.0)


# ---------------------------------------------------------------------------
# 4. Unit test — global diff when all reports have matching baselines
# ---------------------------------------------------------------------------

def test_global_diff_correct_when_all_reports_have_baseline(mocker):
    """
    Calculation
    -----------
    Current (4 reports):
      Module A: Counter(20, 80)  → 80/100  = 80.0%
      Module B: Counter(10, 90)  → 90/100  = 90.0%
      Module C: Counter(30, 70)  → 70/100  = 70.0%
      Module D: Counter(15, 85)  → 85/100  = 85.0%
      Combined: Counter(75, 325) → 325/400 = 81.25%

    Baseline (4 reports, all names matched):
      Module A: Counter(25, 75)  → 75/100  = 75.0%
      Module B: Counter(15, 85)  → 85/100  = 85.0%
      Module C: Counter(35, 65)  → 65/100  = 65.0%
      Module D: Counter(20, 80)  → 80/100  = 80.0%
      Combined: Counter(95, 305) → 305/400 = 76.25%

    Global diff (all 4 names present in both evaluators):
      round(325/400*100, 2) − round(305/400*100, 2) = 81.25 − 76.25 = +5.0%

    Per-report diffs:
      Module A: 80.0 − 75.0 = +5.0%
      Module B: 90.0 − 85.0 = +5.0%
      Module C: 70.0 − 65.0 = +5.0%
      Module D: 85.0 − 80.0 = +5.0%
    """
    _mock_common_action_inputs(mocker)

    evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    evaluator.total_coverage_overall = 81.25
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files = 81.25
    evaluator.total_coverage_changed_files_passed = True

    erc_a = _make_erc("Module A", 80.0, 80.0, (20, 80), (20, 80))
    erc_b = _make_erc("Module B", 90.0, 90.0, (10, 90), (10, 90))
    erc_c = _make_erc("Module C", 70.0, 70.0, (30, 70), (30, 70))
    erc_d = _make_erc("Module D", 85.0, 85.0, (15, 85), (15, 85))
    evaluator.evaluated_reports_coverage = {
        "Module A": erc_a,
        "Module B": erc_b,
        "Module C": erc_c,
        "Module D": erc_d,
    }
    evaluator.evaluated_groups_coverage = {}

    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    # Combined baseline: Counter(95, 305) → 305/400 = 76.25%
    bs_evaluator.total_coverage_overall = 76.25
    bs_evaluator.total_coverage_overall_passed = True
    bs_evaluator.total_coverage_changed_files = 76.25
    bs_evaluator.total_coverage_changed_files_passed = True
    bs_evaluator.evaluated_reports_coverage = {
        "Module A": _make_erc("Module A", 75.0, 75.0, (25, 75), (25, 75)),
        "Module B": _make_erc("Module B", 85.0, 85.0, (15, 85), (15, 85)),
        "Module C": _make_erc("Module C", 65.0, 65.0, (35, 65), (35, 65)),
        "Module D": _make_erc("Module D", 80.0, 80.0, (20, 80), (20, 80)),
    }
    bs_evaluator.evaluated_groups_coverage = {}

    mock_gh = mocker.Mock()
    generator = PRCommentGenerator(mock_gh, evaluator, bs_evaluator, 35)

    # Global diff: round(325/400*100,2) − round(305/400*100,2) = 81.25 − 76.25 = +5.0%
    global_table = generator.get_basic_table_for_all("✅", "❌")
    assert "+5.0%" in global_table
    assert "Δ Coverage" in global_table

    # Per-report diffs: 80.0−75.0, 90.0−85.0, 70.0−65.0, 85.0−80.0 = +5.0%
    assert generator._calculate_baseline_report_diffs(erc_a) == (5.0, 5.0)
    assert generator._calculate_baseline_report_diffs(erc_b) == (5.0, 5.0)
    assert generator._calculate_baseline_report_diffs(erc_c) == (5.0, 5.0)
    assert generator._calculate_baseline_report_diffs(erc_d) == (5.0, 5.0)


# ---------------------------------------------------------------------------
# 5. Unit test — no Δ column when baseline evaluator has no data
# ---------------------------------------------------------------------------

def test_no_delta_column_when_baseline_evaluator_has_no_data(mocker):
    """
    When bs_evaluator's dictionaries are empty, _has_baseline_data() returns False
    and get_basic_table_for_all() renders the table without a Δ Coverage column.

    Calculation
    -----------
    bs_evaluator.evaluated_reports_coverage = {}   → len({}) = 0
    bs_evaluator.evaluated_groups_coverage   = {}   → len({}) = 0

    _has_baseline_data():
      has_report_baseline = isinstance({}, dict) and len({}) > 0 = False
      has_group_baseline  = isinstance({}, dict) and len({}) > 0 = False
      return False or False = False

    get_basic_table_for_all():
      _has_baseline_data() is False
      → calls get_basic_table() (no baseline params, no Δ column)

    Result table header: "| Metric (instruction) | Coverage | Threshold | Status |"
    The string "Δ Coverage" does NOT appear anywhere.
    """
    _mock_common_action_inputs(mocker)

    evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    evaluator.total_coverage_overall = 80.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files = 80.0
    evaluator.total_coverage_changed_files_passed = True

    # Baseline evaluator with no data — both dicts remain {} by CoverageEvaluator.__init__
    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )

    mock_gh = mocker.Mock()
    generator = PRCommentGenerator(mock_gh, evaluator, bs_evaluator, 35)

    global_table = generator.get_basic_table_for_all("✅", "❌")

    # No Δ column when baseline has no data
    assert "Δ Coverage" not in global_table
    assert "| **Overall**" in global_table
    assert "80.0%" in global_table


# ---------------------------------------------------------------------------
# 6. Unit test — group diffs when all group reports have baselines
# ---------------------------------------------------------------------------

def test_group_table_diff_correct_when_all_group_reports_have_baseline(mocker):
    """
    Calculation
    -----------
    group-alpha current (Module A 80% + Module B 90%):
      Counter(20+10, 80+90) = Counter(30, 170) → 170/200 = 85.0%

    group-alpha baseline (A_bs 75% + B_bs 85%, all names matched):
      A_bs: Counter(25, 75) → 75.0%
      B_bs: Counter(15, 85) → 85.0%
      Combined: Counter(40, 160) → 160/200 = 80.0%

    group-alpha diff (all reports matched):
      round(170/200*100,2) − round(160/200*100,2) = 85.0 − 80.0 = +5.0%

    group-beta current (Module C 70% + Module D 85%):
      Counter(30+15, 70+85) = Counter(45, 155) → 155/200 = 77.5%

    group-beta baseline (C_bs 65% + D_bs 80%, all names matched):
      C_bs: Counter(35, 65) → 65.0%
      D_bs: Counter(20, 80) → 80.0%
      Combined: Counter(55, 145) → 145/200 = 72.5%

    group-beta diff (all reports matched):
      round(155/200*100,2) − round(145/200*100,2) = 77.5 − 72.5 = +5.0%

    Global diff (all 4 names matched):
      Counter(75, 325) → 81.25%;  Counter(95, 305) → 76.25%
      81.25 − 76.25 = +5.0%
    """
    _mock_common_action_inputs(mocker)

    evaluator = CoverageEvaluator(
        report_files_coverage=[],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
        report_groups=[ReportGroup("group-alpha", []), ReportGroup("group-beta", [])],
    )
    evaluator.total_coverage_overall = 81.25
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files = 0.0
    evaluator.total_coverage_changed_files_passed = True
    # Individual reports needed so calculate_baseline_group_diffs can find matched names per group
    evaluator.evaluated_reports_coverage = {
        "Module A": _make_erc("Module A", 80.0, 80.0, (20, 80), (20, 80), group_name="group-alpha"),
        "Module B": _make_erc("Module B", 90.0, 90.0, (10, 90), (10, 90), group_name="group-alpha"),
        "Module C": _make_erc("Module C", 70.0, 70.0, (30, 70), (30, 70), group_name="group-beta"),
        "Module D": _make_erc("Module D", 85.0, 85.0, (15, 85), (15, 85), group_name="group-beta"),
    }
    # group-alpha: Counter(30, 170) → 85.0%; group-beta: Counter(45, 155) → 77.5%
    erc_alpha = _make_group_erc("group-alpha", 85.0, (30, 170))
    erc_beta = _make_group_erc("group-beta", 77.5, (45, 155))
    evaluator.evaluated_groups_coverage = {"group-alpha": erc_alpha, "group-beta": erc_beta}

    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    # Combined baseline: Counter(95, 305) → 76.25%
    bs_evaluator.total_coverage_overall = 76.25
    bs_evaluator.total_coverage_overall_passed = True
    bs_evaluator.total_coverage_changed_files = 0.0
    bs_evaluator.total_coverage_changed_files_passed = True
    bs_evaluator.evaluated_reports_coverage = {
        "Module A": _make_erc("Module A", 75.0, 75.0, (25, 75), (25, 75), group_name="group-alpha"),
        "Module B": _make_erc("Module B", 85.0, 85.0, (15, 85), (15, 85), group_name="group-alpha"),
        "Module C": _make_erc("Module C", 65.0, 65.0, (35, 65), (35, 65), group_name="group-beta"),
        "Module D": _make_erc("Module D", 80.0, 80.0, (20, 80), (20, 80), group_name="group-beta"),
    }
    # group-alpha baseline: Counter(40, 160) → 80.0%
    bs_erc_alpha = _make_group_erc("group-alpha", 80.0, (40, 160))
    # group-beta baseline: Counter(55, 145) → 72.5%
    bs_erc_beta = _make_group_erc("group-beta", 72.5, (55, 145))
    bs_evaluator.evaluated_groups_coverage = {"group-alpha": bs_erc_alpha, "group-beta": bs_erc_beta}

    mock_gh = mocker.Mock()
    generator = PRCommentGenerator(mock_gh, evaluator, bs_evaluator, 35)

    # group-alpha (A+B): round(170/200*100,2) − round(160/200*100,2) = 85.0 − 80.0 = +5.0%
    diff_o, diff_ch = generator.calculate_baseline_group_diffs(erc_alpha)
    assert diff_o == 5.0

    # group-beta (C+D): round(155/200*100,2) − round(145/200*100,2) = 77.5 − 72.5 = +5.0%
    diff_o, diff_ch = generator.calculate_baseline_group_diffs(erc_beta)
    assert diff_o == 5.0

    # Groups table: "+5.0%" appears in both group rows (overall + changed files = 4 total)
    groups_table = generator.get_groups_table("✅", "❌")
    assert groups_table.count("+5.0%") == 4

    # Global diff: round(325/400*100,2) − round(305/400*100,2) = 81.25 − 76.25 = +5.0%
    global_table = generator.get_basic_table_for_all("✅", "❌")
    assert "+5.0%" in global_table


# ---------------------------------------------------------------------------
# 7. Unit test — per-file diffs: matched report gets a diff, unmatched gets 0.0%
# ---------------------------------------------------------------------------

def test_per_file_diff_correct_and_zero_for_unmatched_reports(mocker):
    """
    generate_changed_files_table_with_baseline looks up the baseline in two steps:
      1. Check if the report name (ecr_key) is in bs_evaluator.evaluated_reports_coverage
      2. Check if the file path is in that report's changed_files_coverage_reached

    Calculation
    -----------
    Report "Module A" (in baseline):
      ecr_key "Module A" found in bs_evaluator.evaluated_reports_coverage ✓
      "...FileA.java" found in bs["Module A"].changed_files_coverage_reached ✓
      diff = 80.0 (current) − 50.0 (baseline) = +30.0%

    Report "Module B" (not in baseline):
      ecr_key "Module B" not found in bs_evaluator.evaluated_reports_coverage
      diff = 0.0%

    Table row for FileA.java: "| 80.0% | 0.0% | +30.0% | ✅ |"
    Table row for FileB.java: "| 90.0% | 0.0% | 0.0% | ✅ |"
    """
    _mock_common_action_inputs(mocker)

    file_a = "com/partial_baseline/module_a/FileA.java"
    file_b = "com/partial_baseline/module_b/FileB.java"

    erc_a = _make_erc(
        "Module A", 80.0, 80.0, (20, 80), (20, 80),
        changed_files={file_a: 80.0},
    )
    erc_b = _make_erc(
        "Module B", 90.0, 90.0, (10, 90), (10, 90),
        changed_files={file_b: 90.0},
    )

    evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    evaluator.total_coverage_overall = 85.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files = 85.0
    evaluator.total_coverage_changed_files_passed = True
    evaluator.evaluated_reports_coverage = {"Module A": erc_a, "Module B": erc_b}
    evaluator.evaluated_groups_coverage = {}

    bs_a = _make_erc(
        "Module A", 50.0, 50.0, (50, 50), (50, 50),
        changed_files={file_a: 50.0},
    )
    # Module B intentionally absent from the baseline evaluator

    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    bs_evaluator.total_coverage_overall = 50.0
    bs_evaluator.total_coverage_overall_passed = True
    bs_evaluator.total_coverage_changed_files = 50.0
    bs_evaluator.total_coverage_changed_files_passed = True
    bs_evaluator.evaluated_reports_coverage = {"Module A": bs_a}
    bs_evaluator.evaluated_groups_coverage = {}

    mock_gh = mocker.Mock()
    generator = PRCommentGenerator(mock_gh, evaluator, bs_evaluator, 35)

    table = generator.generate_changed_files_table_with_baseline("✅", "❌", {"Module A": erc_a, "Module B": erc_b})

    # FileA: Module A in bs AND FileA in bs → diff = 80.0 − 50.0 = +30.0%
    assert "+30.0%" in table
    # FileB: Module B NOT in bs → diff = 0.0%
    assert "| 90.0% | 0.0% | 0.0% | ✅ |" in table


# ---------------------------------------------------------------------------
# 8. Unit test — Δ column appears even when NO report names match baseline
# ---------------------------------------------------------------------------

def test_global_diff_misleading_when_no_report_names_match_baseline(mocker):
    """
    _has_baseline_data() returns True when bs_evaluator.evaluated_reports_coverage
    is non-empty — regardless of whether any names correspond to current reports.

    Calculation
    -----------
    Current:
      Module A: Counter(20, 80) → 80.0%
      Module B: Counter(10, 90) → 90.0%
      Combined: Counter(30, 170) → 170/200 = 85.0%

    Baseline ("Completely Different Module" — no name match):
      Counter(20, 80) → 80.0%
      bs_evaluator.evaluated_reports_coverage = {"Completely Different Module": ...}

    _has_baseline_data():
      len({"Completely Different Module": ...}) = 1 > 0 → True
      → get_basic_table_with_baseline() is called (Δ column appears)

    Global diff (intersection is empty — matched_names = {}):
      _compute_matched_global_diffs returns (0.0, 0.0)
      → Δ column shows 0.0%

    Per-report diffs (name lookup):
      "Module A" not in {"Completely Different Module"} → (0.0, 0.0)
      "Module B" not in {"Completely Different Module"} → (0.0, 0.0)
    """
    _mock_common_action_inputs(mocker)

    erc_a = _make_erc("Module A", 80.0, 80.0, (20, 80), (20, 80))
    erc_b = _make_erc("Module B", 90.0, 90.0, (10, 90), (10, 90))

    evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    evaluator.total_coverage_overall = 85.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files = 85.0
    evaluator.total_coverage_changed_files_passed = True
    evaluator.evaluated_reports_coverage = {"Module A": erc_a, "Module B": erc_b}
    evaluator.evaluated_groups_coverage = {}

    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    bs_evaluator.total_coverage_overall = 80.0
    bs_evaluator.total_coverage_overall_passed = True
    bs_evaluator.total_coverage_changed_files = 80.0
    bs_evaluator.total_coverage_changed_files_passed = True
    bs_evaluator.evaluated_reports_coverage = {
        "Completely Different Module": _make_erc(
            "Completely Different Module", 80.0, 80.0, (20, 80), (20, 80)
        ),
    }
    bs_evaluator.evaluated_groups_coverage = {}

    mock_gh = mocker.Mock()
    generator = PRCommentGenerator(mock_gh, evaluator, bs_evaluator, 35)

    # bs_evaluator has 1 entry → _has_baseline_data() is True even with zero name matches
    assert generator._has_baseline_data() is True

    # matched_names = {} → _compute_matched_global_diffs returns (0.0, 0.0) → Δ shows 0.0%
    global_table = generator.get_basic_table_for_all("✅", "❌")
    assert "Δ Coverage" in global_table
    assert "| **Overall**       | 85.0% | 0.0% | 0.0% | ✅ |" in global_table

    # Per-report diffs: name not in baseline → (0.0, 0.0)
    assert generator._calculate_baseline_report_diffs(erc_a) == (0.0, 0.0)
    assert generator._calculate_baseline_report_diffs(erc_b) == (0.0, 0.0)


# ---------------------------------------------------------------------------
# 9. Unit test — 1 report + 1 matching baseline → global == per-report diff
# ---------------------------------------------------------------------------

def test_global_diff_correct_single_report_single_baseline_match(mocker):
    """
    Calculation
    -----------
    Current:
      Module A only: Counter(20, 80) → 80/100 = 80.0%

    Baseline:
      Module A: Counter(50, 50) → 50/100 = 50.0%

    Global diff (1-to-1 match):
      round(80/100*100, 2) − round(50/100*100, 2) = 80.0 − 50.0 = +30.0%

    Per-report diff for Module A:
      _calculate_baseline_report_diffs: 80.0 − 50.0 = +30.0%
    """
    _mock_common_action_inputs(mocker)

    erc_a = _make_erc("Module A", 80.0, 80.0, (20, 80), (20, 80))

    evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    evaluator.total_coverage_overall = 80.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files = 80.0
    evaluator.total_coverage_changed_files_passed = True
    evaluator.evaluated_reports_coverage = {"Module A": erc_a}
    evaluator.evaluated_groups_coverage = {}

    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    bs_evaluator.total_coverage_overall = 50.0
    bs_evaluator.total_coverage_overall_passed = True
    bs_evaluator.total_coverage_changed_files = 50.0
    bs_evaluator.total_coverage_changed_files_passed = True
    bs_evaluator.evaluated_reports_coverage = {
        "Module A": _make_erc("Module A", 50.0, 50.0, (50, 50), (50, 50)),
    }
    bs_evaluator.evaluated_groups_coverage = {}

    mock_gh = mocker.Mock()
    generator = PRCommentGenerator(mock_gh, evaluator, bs_evaluator, 35)

    # Global diff: round(80/100*100,2) − round(50/100*100,2) = 80.0 − 50.0 = +30.0%
    global_table = generator.get_basic_table_for_all("✅", "❌")
    assert "+30.0%" in global_table

    # Per-report diff: 80.0 − 50.0 = +30.0%
    diff_o, diff_ch = generator._calculate_baseline_report_diffs(erc_a)
    assert diff_o == 30.0
    assert diff_ch == 30.0


# ---------------------------------------------------------------------------
# 10. Integration test — groups with explicit per-group baseline paths
# ---------------------------------------------------------------------------

def test_group_flow_partial_baseline_with_explicit_per_group_baseline_paths(
    jacoco_report: JaCoCoReport, mocker
):
    """
    Integration test exercising the grouped code path in jacoco_report.run().
    Each group has baseline_paths explicitly set (baseline_paths_configured=True).

    Calculation
    -----------
    group-alpha (Module A + Module B):
      XML paths:      tests/data/partial_baseline/module_{a,b}/**/*.xml
      baseline_paths: tests/data_baseline_partial/module_a/*.xml (only Module A at 50%)

      current coverage:
        Module A: Counter(20, 80) → 80.0%
        Module B: Counter(10, 90) → 90.0%
        group combined: Counter(30, 170) → 170/200 = 85.0%

      baseline coverage (only Module A):
        Counter(50, 50) → 50/100 = 50.0%

      group-alpha diff (intersection: only Module A matched, weighted to group total):
        group-alpha total: 200 instructions (Module A + Module B)
        matched Module A: curr_covered=80, bs_covered=50
        diff = (80 − 50) / 200 × 100 = +15.0%

      per-report Module A (name lookup, report-scoped denominator):
        diff = 80.0 − 50.0 = +30.0%

    group-beta (Module C + Module D):
      XML paths:      tests/data/partial_baseline/module_{c,d}/**/*.xml
      baseline_paths: []  (explicitly disabled, baseline_paths_configured=True)

      current coverage:
        Module C: Counter(30, 70) → 70.0%
        Module D: Counter(15, 85) → 85.0%
        group combined: Counter(45, 155) → 155/200 = 77.5%

      no baseline → diff = 0.0%
    """
    group_alpha = ReportGroup(
        "group-alpha",
        paths=[
            "tests/data/partial_baseline/module_a/**/*.xml",
            "tests/data/partial_baseline/module_b/**/*.xml",
        ],
        baseline_paths=["tests/data_baseline_partial/module_a/*.xml"],
    )
    group_beta = ReportGroup(
        "group-beta",
        paths=[
            "tests/data/partial_baseline/module_c/**/*.xml",
            "tests/data/partial_baseline/module_d/**/*.xml",
        ],
        baseline_paths=[],  # explicitly disabled; baseline_paths_configured=True, baseline_paths=[]
    )

    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value="pull_request")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_id", return_value="")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_action_ref", return_value="")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_started_at", return_value="")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_token", return_value="fake_token")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_level", return_value=CommentLevelEnum.FULL)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=0.0)
    mocker.patch(
        "jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=0.0
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_thresholds_default", return_value=(0.0, 0.0, 0.0))
    mocker.patch(
        "jacoco_report.action_inputs.ActionInputs.get_report_groups",
        return_value=[group_alpha, group_beta],
    )
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_repository", return_value="MoranaApps/jacoco-report")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value=False)
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_number", return_value=35)
    mocker.patch("jacoco_report.utils.github.GitHub.get_pr_changed_files", return_value=_CHANGED_FILES)
    mock_add_comment = mocker.patch("jacoco_report.utils.github.GitHub.add_comment", return_value=None)

    jacoco_report.run()

    generated_comment = mock_add_comment.call_args[0][1]

    # Report-level Module A: 80.0 − 50.0 = +30.0% (per-report, report-scoped denominator)
    assert "+30.0%" in generated_comment
    # Group-alpha: (80−50)/200×100 = +15.0% (weighted to group's 200 instructions)
    assert "+15.0%" in generated_comment

    # group-beta: no baseline configured → no Δ column for this group
    assert "group-beta" in generated_comment


# ---------------------------------------------------------------------------
# 11. Unit test — per-file diff is 0.0% when file is absent from baseline
# ---------------------------------------------------------------------------

def test_per_file_diff_zero_when_changed_file_absent_from_baseline(mocker):
    """
    Even when the report name matches the baseline, a specific file that does not
    appear in the baseline's changed_files_coverage_reached gets diff = 0.0%.

    This exercises the third branch in generate_changed_files_table_with_baseline:
      elif file_key not in bs_evaluator.evaluated_reports_coverage[ecr_key]
                            .changed_files_coverage_reached.keys():
          diff = 0.0

    Calculation
    -----------
    Report "Module A" IS in baseline.

    FileA.java (present in baseline):
      ecr_key "Module A" found in bs ✓
      "...FileA.java" found in bs["Module A"].changed_files_coverage_reached ✓
      diff = 80.0 (current) − 50.0 (baseline) = +30.0%

    FileNew.java (new file — in current, not in baseline):
      ecr_key "Module A" found in bs ✓
      "...FileNew.java" not found in bs["Module A"].changed_files_coverage_reached
      diff = 0.0%

    Table row for FileA.java:   contains "+30.0%"
    Table row for FileNew.java: "| 75.0% | 0.0% | 0.0% | ✅ |"
    """
    _mock_common_action_inputs(mocker)

    file_a = "com/partial_baseline/module_a/FileA.java"
    file_new = "com/partial_baseline/module_a/FileNew.java"

    erc_a = _make_erc(
        "Module A", 80.0, 77.5, (20, 80), (22, 78),
        changed_files={
            file_a: 80.0,
            file_new: 75.0,  # new file — in current but not in baseline
        },
    )

    evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    evaluator.total_coverage_overall = 80.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files = 77.5
    evaluator.total_coverage_changed_files_passed = True
    evaluator.evaluated_reports_coverage = {"Module A": erc_a}
    evaluator.evaluated_groups_coverage = {}

    bs_a = _make_erc(
        "Module A", 50.0, 50.0, (50, 50), (50, 50),
        changed_files={
            file_a: 50.0,   # FileA.java present in baseline at 50%
            # FileNew.java intentionally absent
        },
    )
    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[], global_min_coverage_overall=0.0, global_min_coverage_changed_files=0.0
    )
    bs_evaluator.total_coverage_overall = 50.0
    bs_evaluator.total_coverage_overall_passed = True
    bs_evaluator.total_coverage_changed_files = 50.0
    bs_evaluator.total_coverage_changed_files_passed = True
    bs_evaluator.evaluated_reports_coverage = {"Module A": bs_a}
    bs_evaluator.evaluated_groups_coverage = {}

    mock_gh = mocker.Mock()
    generator = PRCommentGenerator(mock_gh, evaluator, bs_evaluator, 35)

    table = generator.generate_changed_files_table_with_baseline("✅", "❌", {"Module A": erc_a})

    # FileA.java: report in bs AND file in bs → 80.0 − 50.0 = +30.0%
    assert "+30.0%" in table
    # FileNew.java: report in bs but file not in bs → 0.0%
    assert "| 75.0% | 0.0% | 0.0% | ✅ |" in table
