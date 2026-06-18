import logging

import pytest

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.generator.pr_comment_generator import PRCommentGenerator
from jacoco_report.model.counter import Counter
from jacoco_report.model.coverage import Coverage
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.utils.enums import CommentLevelEnum, MetricTypeEnum


@pytest.fixture
def mock_github(mocker):
    return mocker.Mock()

@pytest.fixture
def test_evaluator(mocker):
    ce = CoverageEvaluator(
        report_files_coverage=[],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=80.0,
    )
    ce.total_coverage_overall = 85.2
    ce.total_coverage_overall_passed = True
    ce.total_coverage_changed_files = 78.4
    ce.total_coverage_changed_files_passed = False
    return ce

@pytest.fixture
def pr_comment_generator(mock_github, test_evaluator):
    return PRCommentGenerator(mock_github, test_evaluator, None, 1)


def _make_evaluated_coverage(
    name,
    *,
    group_name="Unknown",
    overall_passed=True,
    changed_passed=True,
    overall_coverage=85.0,
    changed_coverage=80.0,
    overall_threshold=75.0,
    changed_threshold=70.0,
    changed_files=None,
):
    coverage = EvaluatedReportCoverage(name, group_name=group_name)
    coverage.overall_passed = overall_passed
    coverage.avg_changed_files_passed = changed_passed
    coverage.overall_coverage_reached = overall_coverage
    coverage.avg_changed_files_coverage_reached = changed_coverage
    coverage.overall_coverage_threshold = overall_threshold
    coverage.changed_files_threshold = changed_threshold
    coverage.per_changed_file_threshold = changed_threshold
    coverage.avg_changed_files_coverage = Counter(0, len(changed_files or {}))
    coverage.changed_files_coverage_reached = changed_files or {}
    coverage.changed_files_passed = {
        path: changed_passed if score >= changed_threshold else False
        for path, score in (changed_files or {}).items()
    }
    return coverage


def _configure_generator_for_comment_tests(generator, mocker, *, comment_level):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_level", return_value=comment_level)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="JaCoCo")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_pass_symbol", return_value="✅")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_fail_symbol", return_value="❌")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=80.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=80.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=False)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_repository", return_value="owner/repo")
    generator.gh.get_comments.return_value = []


def _set_mixed_comment_level_fixture(pr_comment_generator):
    pr_comment_generator.evaluator.evaluated_groups_coverage = {
        "changed-group": _make_evaluated_coverage("changed-group", changed_files={"src/Foo.java": 82.0}),
        "failing-group": _make_evaluated_coverage("failing-group", overall_passed=False, changed_files={}),
        "unchanged-group": _make_evaluated_coverage("unchanged-group", changed_files={}),
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "changed-report": _make_evaluated_coverage("changed-report", changed_files={"src/Foo.java": 82.0}),
        "failing-report": _make_evaluated_coverage(
            "failing-report",
            overall_passed=False,
            changed_passed=False,
            changed_files={"src/Bar.java": 60.0},
            changed_threshold=80.0,
        ),
        "unchanged-report": _make_evaluated_coverage("unchanged-report", changed_files={}),
    }

def test_get_basic_table(pr_comment_generator, mocker):
    table = pr_comment_generator.get_basic_table(
        "✅", "❌", MetricTypeEnum.INSTRUCTION,
        85.2, True, 80.0,
        78.4, False, 80.0
    )

    assert "| **Overall**       | 85.2% | 80.0% | ✅ |" in table
    assert "| **Changed Files** | 78.4% | 80.0% | ❌ |" in table

def test_get_changed_files_table_without_baseline(pr_comment_generator):
    table = pr_comment_generator.generate_changed_files_table_without_baseline("✅", "❌")
    assert "| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports." in table

def test_get_changed_files_table_with_baseline(pr_comment_generator):
    table = pr_comment_generator.generate_changed_files_table_with_baseline("✅", "❌")
    assert "| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports." in table

def test_calculate_group_diff(pr_comment_generator, mocker):
    # Current report: overall = 80/100 = 80.0%, changed = 85/100 = 85.0%, group="module-a"
    curr_erc = EvaluatedReportCoverage("module-a-report", group_name="module-a")
    curr_erc.overall_coverage = Counter(20, 80)
    curr_erc.avg_changed_files_coverage = Counter(15, 85)
    pr_comment_generator.evaluator.evaluated_reports_coverage = {"module-a-report": curr_erc}

    # Baseline report: overall = 70/100 = 70.0%, changed = 75/100 = 75.0%
    bs_erc = EvaluatedReportCoverage("module-a-report")
    bs_erc.overall_coverage = Counter(30, 70)
    bs_erc.avg_changed_files_coverage = Counter(25, 75)

    mock_baseline_evaluator = mocker.Mock()
    mock_baseline_evaluator.evaluated_groups_coverage = {"module-a": EvaluatedReportCoverage("module-a")}
    mock_baseline_evaluator.evaluated_reports_coverage = {"module-a-report": bs_erc}
    pr_comment_generator.bs_evaluator = mock_baseline_evaluator

    # Group ERC passed to calculate_baseline_group_diffs — name must match the group key
    evaluated_coverage_module = EvaluatedReportCoverage("module-a")

    # diff_o = 80.0 - 70.0 = 10.0, diff_ch = 85.0 - 75.0 = 10.0
    diff_o, diff_ch = pr_comment_generator.calculate_baseline_group_diffs(evaluated_coverage_module)

    assert diff_o == 10.0
    assert diff_ch == 10.0

def test_calculate_group_diff_no_group_in_baseline(pr_comment_generator, mocker):
    # Mock the baseline evaluator with no groups
    mock_baseline_evaluator = mocker.Mock()
    mock_baseline_evaluator.evaluated_groups_coverage = {}
    pr_comment_generator.bs_evaluator = mock_baseline_evaluator

    # Create an evaluated coverage module
    evaluated_coverage_module = EvaluatedReportCoverage("module-a")
    evaluated_coverage_module.overall_coverage_reached = 80.0
    evaluated_coverage_module.avg_changed_files_coverage_reached = 85.0

    # Calculate the differences
    diff_o, diff_ch = pr_comment_generator.calculate_baseline_group_diffs(evaluated_coverage_module)

    # Assert the differences are zero since the group is not in the baseline
    assert diff_o == 0.0
    assert diff_ch == 0.0

def test_generate_changed_files_table_with_baseline(pr_comment_generator, mocker):
    # Mock the necessary methods and attributes
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["baseline.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value=False)
    mocker.patch("hashlib.sha256", return_value=mocker.Mock(hexdigest=lambda: "fakehash"))

    pr_comment_generator.github_repository = "fake_repo"
    pr_comment_generator.pr_number = 1

    # Mock the evaluator with some values
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "report1": EvaluatedReportCoverage("report1")
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage["report1"].changed_files_coverage_reached = {
        "file1.java": 80.0
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage["report1"].changed_files_threshold = 75.0
    pr_comment_generator.evaluator.evaluated_reports_coverage["report1"].changed_files_passed = {
        "file1.java": True
    }

    # Mock the baseline evaluator with some values
    pr_comment_generator.bs_evaluator = mocker.Mock()
    pr_comment_generator.bs_evaluator.evaluated_reports_coverage = {
        "report1": EvaluatedReportCoverage("report1")
    }
    pr_comment_generator.bs_evaluator.evaluated_reports_coverage["report1"].changed_files_coverage_reached = {
        "file1.java": 70.0
    }

    # Generate the table
    table = pr_comment_generator.generate_changed_files_table_with_baseline("✅", "❌")

    # Assert the table content
    expected_table = """| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [file1.java](https://github.com/fake_repo/pull/1/files#diff-fakehash) | 80.0% | 0.0% | +10.0% | ✅ |"""
    assert table == expected_table

def test_generate_changed_files_table_with_baseline_no_evaluated_report_coverage(pr_comment_generator, mocker):
    # Mock the necessary methods and attributes
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["baseline.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value=False)
    mocker.patch("hashlib.sha256", return_value=mocker.Mock(hexdigest=lambda: "fakehash"))

    pr_comment_generator.github_repository = "fake_repo"
    pr_comment_generator.pr_number = 1

    # Mock the evaluator with some values
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "report1": EvaluatedReportCoverage("report1")
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage["report1"].changed_files_coverage_reached = {
        "file1.java": 80.0
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage["report1"].changed_files_threshold = 75.0
    pr_comment_generator.evaluator.evaluated_reports_coverage["report1"].changed_files_passed = {
        "file1.java": True
    }

    # Mock the baseline evaluator with some values
    pr_comment_generator.bs_evaluator = mocker.Mock()
    pr_comment_generator.bs_evaluator.evaluated_reports_coverage = {
        "report21": EvaluatedReportCoverage("report21")
    }
    pr_comment_generator.bs_evaluator.evaluated_reports_coverage["report21"].changed_files_coverage_reached = {
        "file1.java": 70.0
    }

    # Generate the table
    table = pr_comment_generator.generate_changed_files_table_with_baseline("✅", "❌")

    # Assert the table content
    expected_table = """| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [file1.java](https://github.com/fake_repo/pull/1/files#diff-fakehash) | 80.0% | 0.0% | 0.0% | ✅ |"""
    assert table == expected_table

def test_generate_changed_files_table_with_baseline_no_changed_file(pr_comment_generator, mocker):
    # Mock the necessary methods and attributes
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["baseline.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_unchanged", return_value=False)
    mocker.patch("hashlib.sha256", return_value=mocker.Mock(hexdigest=lambda: "fakehash"))

    pr_comment_generator.github_repository = "fake_repo"
    pr_comment_generator.pr_number = 1

    # Mock the evaluator with some values
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "report1": EvaluatedReportCoverage("report1")
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage["report1"].changed_files_coverage_reached = {
        "file1.java": 80.0
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage["report1"].changed_files_threshold = 75.0
    pr_comment_generator.evaluator.evaluated_reports_coverage["report1"].changed_files_passed = {
        "file1.java": True
    }

    # Mock the baseline evaluator with some values
    pr_comment_generator.bs_evaluator = mocker.Mock()
    pr_comment_generator.bs_evaluator.evaluated_reports_coverage = {
        "report1": EvaluatedReportCoverage("report1")
    }
    pr_comment_generator.bs_evaluator.evaluated_reports_coverage["report1"].changed_files_coverage_reached = {
        "file2.java": 70.0
    }

    # Generate the table
    table = pr_comment_generator.generate_changed_files_table_with_baseline("✅", "❌")

    # Assert the table content
    expected_table = """| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [file1.java](https://github.com/fake_repo/pull/1/files#diff-fakehash) | 80.0% | 0.0% | 0.0% | ✅ |"""
    assert table == expected_table


def test_get_groups_table_empty(pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=[])
    pr_comment_generator.evaluator.evaluated_groups_coverage = {}
    assert pr_comment_generator.get_groups_table("✅", "❌") == ""


def test_get_groups_table_without_baseline(pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=[])
    ev = EvaluatedReportCoverage("backend")
    ev.overall_coverage_reached = 85.0
    ev.avg_changed_files_coverage_reached = 80.0
    ev.overall_coverage_threshold = 75.0
    ev.changed_files_threshold = 70.0
    ev.overall_passed = True
    ev.avg_changed_files_passed = True
    pr_comment_generator.evaluator.evaluated_groups_coverage = {"backend": ev}

    table = pr_comment_generator.get_groups_table("✅", "❌")

    assert "| Group |" in table
    assert "| `backend` | 85.0% / 80.0% | 75.0% / 70.0% | ✅/✅ |" in table


def test_get_groups_table_with_baseline(pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["baseline.xml"])
    ev = EvaluatedReportCoverage("backend")
    ev.overall_coverage_reached = 85.0
    ev.avg_changed_files_coverage_reached = 80.0
    ev.overall_coverage_threshold = 75.0
    ev.changed_files_threshold = 70.0
    ev.overall_passed = True
    ev.avg_changed_files_passed = False
    pr_comment_generator.evaluator.evaluated_groups_coverage = {"backend": ev}

    # Individual report: overall = 85/100 = 85.0%, changed = 80/100 = 80.0%, group="backend"
    curr_erc = EvaluatedReportCoverage("backend-report", group_name="backend")
    curr_erc.overall_coverage = Counter(15, 85)
    curr_erc.avg_changed_files_coverage = Counter(20, 80)
    pr_comment_generator.evaluator.evaluated_reports_coverage = {"backend-report": curr_erc}

    # Baseline: overall = 80/100 = 80.0%, changed = 75/100 = 75.0%
    bs_erc = EvaluatedReportCoverage("backend-report")
    bs_erc.overall_coverage = Counter(20, 80)
    bs_erc.avg_changed_files_coverage = Counter(25, 75)

    bs_ev = EvaluatedReportCoverage("backend")
    bs_ev.overall_coverage_reached = 80.0
    bs_ev.avg_changed_files_coverage_reached = 75.0
    bs_evaluator = mocker.Mock()
    bs_evaluator.evaluated_groups_coverage = {"backend": bs_ev}
    bs_evaluator.evaluated_reports_coverage = {"backend-report": bs_erc}
    pr_comment_generator.bs_evaluator = bs_evaluator

    table = pr_comment_generator.get_groups_table("✅", "❌")

    # diff_o = 85.0 - 80.0 = 5.0, diff_ch = 80.0 - 75.0 = 5.0
    assert "| Group |" in table
    assert "Δ Coverage" in table
    assert "| `backend` | 85.0% / 80.0% | 75.0% / 70.0% | +5.0% / +5.0% | ✅/❌ |" in table


def test_reports_table_uses_group_thresholds_when_groups_configured(pr_comment_generator, mocker):
    from jacoco_report.model.report_group import ReportGroup
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups",
                 return_value=[ReportGroup("backend", ["**/jacoco.xml"])])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=50.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=50.0)

    ev = EvaluatedReportCoverage("backend-report")
    ev.overall_coverage_reached = 90.0
    ev.avg_changed_files_coverage_reached = 85.0
    ev.overall_coverage_threshold = 75.0
    ev.changed_files_threshold = 70.0
    ev.overall_passed = True
    ev.avg_changed_files_passed = True
    pr_comment_generator.evaluator.evaluated_reports_coverage = {"backend-report": ev}

    table = pr_comment_generator.get_reports_table("✅", "❌")

    assert "75.0% / 70.0%" in table
    assert "50.0%" not in table


def test_reports_table_uses_evaluated_thresholds_not_global(pr_comment_generator):
    """Reports table always uses the thresholds the evaluator actually applied, regardless of group config."""
    ev = EvaluatedReportCoverage("backend-report")
    ev.overall_coverage_reached = 90.0
    ev.avg_changed_files_coverage_reached = 85.0
    ev.overall_coverage_threshold = 75.0
    ev.changed_files_threshold = 70.0
    ev.overall_passed = True
    ev.avg_changed_files_passed = True
    pr_comment_generator.evaluator.evaluated_reports_coverage = {"backend-report": ev}
    pr_comment_generator.evaluator.evaluated_groups_coverage = {}

    table = pr_comment_generator.get_reports_table("✅", "❌")

    assert "75.0% / 70.0%" in table


def test_report_table_orders_by_group_config_order_then_report_name(pr_comment_generator):
    pr_comment_generator.evaluator.report_group_order = ["backend", "frontend"]

    backend_z = _make_evaluated_coverage("z-report", group_name="backend")
    backend_a = _make_evaluated_coverage("a-report", group_name="backend")
    frontend_b = _make_evaluated_coverage("b-report", group_name="frontend")

    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "b-report": frontend_b,
        "z-report": backend_z,
        "a-report": backend_a,
    }

    table = pr_comment_generator.get_reports_table("✅", "❌")

    assert table.index("`a-report`") < table.index("`z-report`")
    assert table.index("`z-report`") < table.index("`b-report`")


def test_report_table_keeps_ungrouped_reports_after_configured_groups(pr_comment_generator):
    pr_comment_generator.evaluator.report_group_order = ["backend", "frontend"]

    backend = _make_evaluated_coverage("backend-report", group_name="backend")
    unknown = _make_evaluated_coverage("unknown-report", group_name="unknown")

    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "unknown-report": unknown,
        "backend-report": backend,
    }

    table = pr_comment_generator.get_reports_table("✅", "❌")

    assert table.index("`backend-report`") < table.index("`unknown-report`")


def test_report_table_without_report_groups_keeps_name_sort(pr_comment_generator):
    pr_comment_generator.evaluator.report_group_order = []

    beta = _make_evaluated_coverage("beta-report", group_name="backend")
    alpha = _make_evaluated_coverage("alpha-report", group_name="frontend")

    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "beta-report": beta,
        "alpha-report": alpha,
    }

    table = pr_comment_generator.get_reports_table("✅", "❌")

    assert table.index("`alpha-report`") < table.index("`beta-report`")

# --- Issue 1: get_groups_table baseline decision logic ---

def test_get_groups_table_baseline_decision_global_only(pr_comment_generator, mocker):
    """Test that get_groups_table shows baseline Δ when global baseline-paths is set"""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["baseline.xml"])
    ev = EvaluatedReportCoverage("backend")
    ev.overall_coverage_reached = 85.0
    ev.avg_changed_files_coverage_reached = 80.0
    ev.overall_coverage_threshold = 75.0
    ev.changed_files_threshold = 70.0
    ev.overall_passed = True
    ev.avg_changed_files_passed = True
    pr_comment_generator.evaluator.evaluated_groups_coverage = {"backend": ev}

    # Individual report: overall = 85/100 = 85.0%, changed = 80/100 = 80.0%, group="backend"
    curr_erc = EvaluatedReportCoverage("backend-report", group_name="backend")
    curr_erc.overall_coverage = Counter(15, 85)
    curr_erc.avg_changed_files_coverage = Counter(20, 80)
    pr_comment_generator.evaluator.evaluated_reports_coverage = {"backend-report": curr_erc}

    # Baseline: overall = 80/100 = 80.0%, changed = 75/100 = 75.0%
    bs_erc = EvaluatedReportCoverage("backend-report")
    bs_erc.overall_coverage = Counter(20, 80)
    bs_erc.avg_changed_files_coverage = Counter(25, 75)

    bs_ev = EvaluatedReportCoverage("backend")
    bs_ev.overall_coverage_reached = 80.0
    bs_ev.avg_changed_files_coverage_reached = 75.0
    bs_evaluator = mocker.Mock()
    bs_evaluator.evaluated_groups_coverage = {"backend": bs_ev}
    bs_evaluator.evaluated_reports_coverage = {"backend-report": bs_erc}
    pr_comment_generator.bs_evaluator = bs_evaluator

    table = pr_comment_generator.get_groups_table("✅", "❌")

    # diff_o = 85.0 - 80.0 = 5.0, diff_ch = 80.0 - 75.0 = 5.0
    assert "Δ Coverage" in table
    assert "+5.0% / +5.0%" in table


def test_get_groups_table_baseline_decision_group_only(pr_comment_generator, mocker):
    """Test that get_groups_table shows baseline Δ when group has per-group baseline-paths"""
    # Global baseline-paths is empty
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=[])
    
    ev = EvaluatedReportCoverage("backend", group_name="backend")
    ev.overall_coverage_reached = 85.0
    ev.avg_changed_files_coverage_reached = 80.0
    ev.overall_coverage_threshold = 75.0
    ev.changed_files_threshold = 70.0
    ev.overall_passed = True
    ev.avg_changed_files_passed = True
    pr_comment_generator.evaluator.evaluated_groups_coverage = {"backend": ev}

    # Simulate baseline evaluator with data
    bs_ev = EvaluatedReportCoverage("backend", group_name="backend")
    bs_ev.overall_coverage_reached = 80.0
    bs_ev.avg_changed_files_coverage_reached = 75.0
    bs_evaluator = mocker.Mock()
    bs_evaluator.evaluated_groups_coverage = {"backend": bs_ev}
    pr_comment_generator.bs_evaluator = bs_evaluator

    table = pr_comment_generator.get_groups_table("✅", "❌")

    # Should show baseline Δ when bs_evaluator has data, even if global baseline-paths is empty
    assert "Δ Coverage" in table


def test_get_reports_table_baseline_decision_group_only(pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=50.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=50.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[])

    ev = EvaluatedReportCoverage("backend-report")
    ev.overall_coverage_reached = 90.0
    ev.avg_changed_files_coverage_reached = 85.0
    ev.overall_coverage_threshold = 75.0
    ev.changed_files_threshold = 70.0
    ev.overall_passed = True
    ev.avg_changed_files_passed = True
    pr_comment_generator.evaluator.evaluated_reports_coverage = {"backend-report": ev}

    bs_ev = EvaluatedReportCoverage("backend-report")
    bs_ev.overall_coverage_reached = 80.0
    bs_ev.avg_changed_files_coverage_reached = 75.0
    bs_evaluator = mocker.Mock()
    bs_evaluator.evaluated_reports_coverage = {"backend-report": bs_ev}
    bs_evaluator.evaluated_groups_coverage = {}
    pr_comment_generator.bs_evaluator = bs_evaluator

    table = pr_comment_generator.get_reports_table("✅", "❌")

    assert "Δ Coverage (O/Ch)" in table


def test_get_basic_table_baseline_decision_group_only(pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=[])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value=MetricTypeEnum.INSTRUCTION)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=50.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=50.0)

    pr_comment_generator.evaluator.total_coverage_overall = 85.0
    pr_comment_generator.evaluator.total_coverage_overall_passed = True
    pr_comment_generator.evaluator.total_coverage_changed_files = 80.0
    pr_comment_generator.evaluator.total_coverage_changed_files_passed = True

    bs_evaluator = mocker.Mock()
    bs_evaluator.total_coverage_overall = 80.0
    bs_evaluator.total_coverage_changed_files = 75.0
    bs_evaluator.evaluated_reports_coverage = {"backend-report": EvaluatedReportCoverage("backend-report")}
    bs_evaluator.evaluated_groups_coverage = {}
    pr_comment_generator.bs_evaluator = bs_evaluator

    table = pr_comment_generator.get_basic_table_for_all("✅", "❌")

    assert "Δ Coverage" in table


def test_get_groups_table_baseline_decision_no_baseline(pr_comment_generator, mocker):
    """Test that get_groups_table omits baseline Δ when no baseline data available"""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=[])
    
    ev = EvaluatedReportCoverage("backend")
    ev.overall_coverage_reached = 85.0
    ev.avg_changed_files_coverage_reached = 80.0
    ev.overall_coverage_threshold = 75.0
    ev.changed_files_threshold = 70.0
    ev.overall_passed = True
    ev.avg_changed_files_passed = True
    pr_comment_generator.evaluator.evaluated_groups_coverage = {"backend": ev}

    # No baseline data
    bs_evaluator = mocker.Mock()
    bs_evaluator.evaluated_groups_coverage = {}
    pr_comment_generator.bs_evaluator = bs_evaluator

    table = pr_comment_generator.get_groups_table("✅", "❌")

    # Should NOT show baseline Δ
    assert "Δ Coverage" not in table
    assert "| Group |" in table


def test_get_groups_table_hides_baseline_when_paths_set_but_no_evaluated_data(pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["baseline.xml"])

    ev = EvaluatedReportCoverage("backend")
    ev.overall_coverage_reached = 85.0
    ev.avg_changed_files_coverage_reached = 80.0
    ev.overall_coverage_threshold = 75.0
    ev.changed_files_threshold = 70.0
    ev.overall_passed = True
    ev.avg_changed_files_passed = True
    pr_comment_generator.evaluator.evaluated_groups_coverage = {"backend": ev}

    bs_evaluator = mocker.Mock()
    bs_evaluator.evaluated_reports_coverage = {}
    bs_evaluator.evaluated_groups_coverage = {}
    pr_comment_generator.bs_evaluator = bs_evaluator

    table = pr_comment_generator.get_groups_table("✅", "❌")

    assert "Δ Coverage" not in table


def test_calculate_baseline_group_diffs_no_data_returns_zero(pr_comment_generator, mocker):
    ev = EvaluatedReportCoverage("backend")
    ev.overall_coverage_reached = 85.0
    ev.avg_changed_files_coverage_reached = 80.0

    bs_ev = EvaluatedReportCoverage("backend")
    # Keep baseline counters at zero to represent "group entry exists but no baseline reports"
    bs_ev.overall_coverage_reached = 0.0
    bs_ev.avg_changed_files_coverage_reached = 0.0

    bs_evaluator = mocker.Mock()
    bs_evaluator.evaluated_groups_coverage = {"backend": bs_ev}
    pr_comment_generator.bs_evaluator = bs_evaluator

    diff_o, diff_ch = pr_comment_generator.calculate_baseline_group_diffs(ev)

    assert diff_o == 0.0
    assert diff_ch == 0.0


# --- comment-level expansion ---

def test_generate_skips_github_comment_for_none(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="none")

    pr_comment_generator.generate()

    pr_comment_generator.gh.get_comments.assert_not_called()
    pr_comment_generator.gh.add_comment.assert_not_called()
    pr_comment_generator.gh.update_comment.assert_not_called()


def test_none_deletes_existing_comment_when_update_comment_enabled(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="none")
    pr_comment_generator.gh.get_comments.return_value = [{"id": 123, "body": "**JaCoCo**\n\nold body"}]
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=True)

    pr_comment_generator.generate()

    pr_comment_generator.gh.get_comments.assert_called_once_with(1)
    pr_comment_generator.gh.add_comment.assert_not_called()
    pr_comment_generator.gh.update_comment.assert_not_called()
    pr_comment_generator.gh.delete_comment.assert_called_once_with(123)


def test_none_leaves_existing_comment_when_update_comment_disabled(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="none")
    pr_comment_generator.gh.get_comments.return_value = [{"id": 123, "body": "**JaCoCo**\n\nold body"}]
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=False)

    pr_comment_generator.generate()

    pr_comment_generator.gh.get_comments.assert_not_called()
    pr_comment_generator.gh.add_comment.assert_not_called()
    pr_comment_generator.gh.update_comment.assert_not_called()
    pr_comment_generator.gh.delete_comment.assert_not_called()


@pytest.mark.parametrize(
    ("comment_level", "expected_fragments", "absent_fragments"),
    [
        (
            "minimal",
            ["| Metric (instruction) |"],
            ["| Group |", "| Report |", "| File Path |", "`changed-group`", "[Foo.java]"],
        ),
        (
            "full",
            [
                "| Metric (instruction) |",
                "| Group |",
                "| Report |",
                "| File Path |",
                "`changed-group`",
                "`failing-group`",
                "`unchanged-group`",
                "`changed-report`",
                "`failing-report`",
                "`unchanged-report`",
                "[Foo.java]",
                "[Bar.java]",
            ],
            [],
        ),
        (
            "changed",
            ["| Metric (instruction) |", "| Group |", "| Report |", "| File Path |", "`changed-group`", "`changed-report`", "`failing-report`", "[Foo.java]", "[Bar.java]"],
            ["`unchanged-group`", "`unchanged-report`", "`failing-group`"],
        ),
        (
            "failed",
            ["| Metric (instruction) |", "| Group |", "| Report |", "| File Path |", "`failing-group`", "`failing-report`", "[Bar.java]"],
            ["`changed-group`", "`changed-report`", "`unchanged-group`", "`unchanged-report`", "[Foo.java]"],
        ),
        (
            "failed-or-changed",
            ["| Metric (instruction) |", "| Group |", "| Report |", "| File Path |", "`changed-group`", "`failing-group`", "`changed-report`", "`failing-report`", "[Foo.java]", "[Bar.java]"],
            ["`unchanged-group`", "`unchanged-report`"],
        ),
    ],
)
def test_comment_level_final_pr_body_matrix(
    pr_comment_generator,
    mocker,
    comment_level,
    expected_fragments,
    absent_fragments,
):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level=comment_level)
    _set_mixed_comment_level_fixture(pr_comment_generator)

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]
    for fragment in expected_fragments:
        assert fragment in body
    for fragment in absent_fragments:
        assert fragment not in body


def test_full_comment_contains_all_tables(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="full")
    pr_comment_generator.evaluator.evaluated_groups_coverage = {
        "backend": _make_evaluated_coverage("backend", changed_files={"src/Foo.java": 82.0})
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "backend-report": _make_evaluated_coverage(
            "backend-report",
            group_name="backend",
            changed_files={"src/Foo.java": 82.0},
        )
    }

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]
    assert "| Metric (instruction) |" in body
    assert "| Group |" in body
    assert "| Report |" in body
    assert "| File Path |" in body


def test_changed_filters_group_report_and_file_rows_without_changes(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="changed")
    pr_comment_generator.evaluator.evaluated_groups_coverage = {
        "changed-group": _make_evaluated_coverage("changed-group", changed_files={"src/Foo.java": 82.0}),
        "unchanged-group": _make_evaluated_coverage("unchanged-group", changed_files={}),
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "changed-report": _make_evaluated_coverage("changed-report", changed_files={"src/Foo.java": 82.0}),
        "unchanged-report": _make_evaluated_coverage("unchanged-report", changed_files={}),
    }

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]
    assert "`changed-group`" in body
    assert "`unchanged-group`" not in body
    assert "`changed-report`" in body
    assert "`unchanged-report`" not in body
    assert "[Foo.java]" in body


def test_failed_filters_only_failing_rows(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="failed")
    pr_comment_generator.evaluator.evaluated_groups_coverage = {
        "passing-group": _make_evaluated_coverage("passing-group", changed_files={"src/Foo.java": 82.0}),
        "failing-group": _make_evaluated_coverage(
            "failing-group",
            overall_passed=False,
            changed_passed=False,
            changed_files={},
        ),
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "passing-report": _make_evaluated_coverage("passing-report", changed_files={"src/Foo.java": 82.0}),
        "failing-report": _make_evaluated_coverage(
            "failing-report",
            overall_passed=False,
            changed_passed=False,
            changed_files={"src/Bar.java": 60.0},
            changed_threshold=80.0,
        ),
    }

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]
    assert "`failing-group`" in body
    assert "`passing-group`" not in body
    assert "`failing-report`" in body
    assert "`passing-report`" not in body
    assert "[Bar.java]" in body
    assert "[Foo.java]" not in body


def test_failed_or_changed_filters_union_of_rows(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="failed-or-changed")
    pr_comment_generator.evaluator.evaluated_groups_coverage = {
        "changed-group": _make_evaluated_coverage("changed-group", changed_files={"src/Foo.java": 82.0}),
        "failing-group": _make_evaluated_coverage("failing-group", overall_passed=False, changed_files={}),
        "hidden-group": _make_evaluated_coverage("hidden-group", changed_files={}),
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "changed-report": _make_evaluated_coverage("changed-report", changed_files={"src/Foo.java": 82.0}),
        "failing-report": _make_evaluated_coverage(
            "failing-report",
            overall_passed=False,
            changed_passed=False,
            changed_files={"src/Bar.java": 60.0},
            changed_threshold=80.0,
        ),
        "hidden-report": _make_evaluated_coverage("hidden-report", changed_files={}),
    }

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]
    assert "`changed-group`" in body
    assert "`failing-group`" in body
    assert "`hidden-group`" not in body
    assert "`changed-report`" in body
    assert "`failing-report`" in body
    assert "`hidden-report`" not in body
    assert "[Foo.java]" in body
    assert "[Bar.java]" in body


@pytest.mark.parametrize("comment_level", ["changed", "failed", "failed-or-changed"])
def test_filtered_comment_levels_handle_empty_result_gracefully(pr_comment_generator, mocker, comment_level):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level=comment_level)
    pr_comment_generator.evaluator.evaluated_groups_coverage = {
        "hidden-group": _make_evaluated_coverage("hidden-group", changed_files={})
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "hidden-report": _make_evaluated_coverage("hidden-report", changed_files={})
    }

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]
    assert "| Metric (instruction) |" in body
    assert "No rows match the selected comment level." in body
    assert "`hidden-group`" not in body
    assert "`hidden-report`" not in body


@pytest.mark.parametrize("comment_level", ["changed", "failed", "failed-or-changed"])
def test_filtered_comment_levels_empty_result_do_not_render_detail_table_headers(
    pr_comment_generator,
    mocker,
    comment_level,
):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level=comment_level)
    pr_comment_generator.evaluator.evaluated_groups_coverage = {
        "hidden-group": _make_evaluated_coverage("hidden-group", changed_files={})
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "hidden-report": _make_evaluated_coverage("hidden-report", changed_files={})
    }

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]
    assert "| Metric (instruction) |" in body
    assert "No rows match the selected comment level." in body
    assert "| Group |" not in body
    assert "| Report |" not in body
    assert "| File Path |" not in body


# --- skip_report_names row-filtering ---

def test_skip_report_names_hides_specified_reports_from_rendered_rows(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="full")
    pr_comment_generator.evaluator.evaluated_groups_coverage = {}
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "changed-report": _make_evaluated_coverage("changed-report", changed_files={"src/Foo.java": 82.0}),
        "unchanged-report": _make_evaluated_coverage("unchanged-report", changed_files={}),
    }
    pr_comment_generator.skip_report_names = frozenset({"unchanged-report"})

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]
    assert "`changed-report`" in body
    assert "`unchanged-report`" not in body


def test_skip_report_names_global_summary_still_shows_evaluator_totals(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="full")
    pr_comment_generator.evaluator.total_coverage_overall = 50.0
    pr_comment_generator.evaluator.total_coverage_overall_passed = False
    pr_comment_generator.evaluator.total_coverage_changed_files = 60.0
    pr_comment_generator.evaluator.total_coverage_changed_files_passed = True
    pr_comment_generator.evaluator.evaluated_groups_coverage = {}
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "changed-report": _make_evaluated_coverage("changed-report", changed_files={"src/Foo.java": 82.0}),
        "unchanged-report": _make_evaluated_coverage("unchanged-report", changed_files={}),
    }
    pr_comment_generator.skip_report_names = frozenset({"unchanged-report"})

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]
    assert "50.0%" in body
    assert "`unchanged-report`" not in body


def test_skip_report_names_empty_set_does_not_hide_any_reports(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="full")
    pr_comment_generator.evaluator.evaluated_groups_coverage = {}
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "report-a": _make_evaluated_coverage("report-a", changed_files={"src/Foo.java": 82.0}),
        "report-b": _make_evaluated_coverage("report-b", changed_files={}),
    }
    # skip_report_names defaults to frozenset() — no explicit assignment

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]
    assert "`report-a`" in body
    assert "`report-b`" in body


def test_skip_report_names_hides_group_when_all_group_reports_are_skipped(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="full")
    # group "backend" has one report that is skipped; group "frontend" has one visible report
    pr_comment_generator.evaluator.evaluated_groups_coverage = {
        "backend": _make_evaluated_coverage("backend"),
        "frontend": _make_evaluated_coverage("frontend"),
    }
    pr_comment_generator.evaluator.evaluated_reports_coverage = {
        "backend-report": _make_evaluated_coverage(
            "backend-report", group_name="backend", changed_files={}
        ),
        "frontend-report": _make_evaluated_coverage(
            "frontend-report", group_name="frontend", changed_files={"src/Foo.java": 80.0}
        ),
    }
    pr_comment_generator.skip_report_names = frozenset({"backend-report"})

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]
    assert "`frontend`" in body
    assert "`backend`" not in body
    assert "`frontend-report`" in body
    assert "`backend-report`" not in body


# --- metadata footer ---

def test_metadata_footer_all_fields(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="minimal")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_id", return_value="9876543210")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value="pull_request")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_started_at", return_value="2025-01-01T00:00:00Z")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_action_ref", return_value="v3.0.0")
    pr_comment_generator.github_repository = "owner/repo"

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]

    assert "---" in body
    assert "Run [9876543210](https://github.com/owner/repo/actions/runs/9876543210)" in body
    assert "Event: `pull_request`" in body
    assert "Action: `v3.0.0`" in body
    assert "Started: `2025-01-01T00:00:00Z`" in body


def test_metadata_footer_no_run_id(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="minimal")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_id", return_value="")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value="pull_request")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_started_at", return_value="2025-01-01T00:00:00Z")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_action_ref", return_value="v3.0.0")

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]

    assert "Run" not in body
    assert "Event: `pull_request`" in body
    assert "Action: `v3.0.0`" in body
    assert "Started: `2025-01-01T00:00:00Z`" in body


def test_metadata_footer_all_empty_returns_empty_string(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="minimal")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_id", return_value="")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value="")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_started_at", return_value="")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_action_ref", return_value="")

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]

    assert "\n\n---\n*" not in body


def test_metadata_footer_run_id_without_repository(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="minimal")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_id", return_value="42")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value="")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_started_at", return_value="")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_action_ref", return_value="")
    pr_comment_generator.github_repository = ""

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]

    assert "Run `42`" in body
    assert "github.com" not in body


def test_metadata_footer_appended_to_comment_body(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="minimal")
    pr_comment_generator.github_repository = "owner/repo"
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_id", return_value="9876543210")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value="pull_request")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_started_at", return_value="2025-01-01T00:00:00Z")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_action_ref", return_value="v3.0.0")

    pr_comment_generator.generate()

    body = pr_comment_generator.gh.add_comment.call_args[0][1]
    assert "---" in body
    assert "Run [9876543210]" in body
    assert "Event: `pull_request`" in body
    assert "Action: `v3.0.0`" in body
    assert "Started: `2025-01-01T00:00:00Z`" in body


def test_metadata_footer_not_appended_for_none_level(pr_comment_generator, mocker):
    _configure_generator_for_comment_tests(pr_comment_generator, mocker, comment_level="none")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_id", return_value="9876543210")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_event_name", return_value="pull_request")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_run_started_at", return_value="2025-01-01T00:00:00Z")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_action_ref", return_value="v3.0.0")

    pr_comment_generator.generate()

    pr_comment_generator.gh.add_comment.assert_not_called()


def _make_empty_evaluator():
    return CoverageEvaluator(
        report_files_coverage=[],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
    )


# ---------------------------------------------------------------------------
# G2  Column header reflects selected metric type
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("metric", ["instruction", "line", "branch", "complexity", "method", "class"])
def test_basic_table_header_reflects_selected_metric(pr_comment_generator, metric):
    """get_basic_table header label changes with the metric parameter."""
    table = pr_comment_generator.get_basic_table("✅", "❌", metric, 85.0, True, 80.0, 80.0, True, 80.0)
    assert f"Metric ({metric})" in table


def test_basic_table_with_baseline_header_reflects_metric(pr_comment_generator):
    """get_basic_table_with_baseline also reflects the metric in its header."""
    table = pr_comment_generator.get_basic_table_with_baseline(
        "✅", "❌", "line", 85.0, True, 80.0, 80.0, True, 80.0, 80.0, 75.0
    )
    assert "Metric (line)" in table


# ---------------------------------------------------------------------------
# G3  Custom pass/fail symbols appear in every table type
# ---------------------------------------------------------------------------

def test_custom_pass_symbol_appears_in_basic_table(pr_comment_generator):
    """Custom pass symbol is rendered in Status column of the global summary table."""
    table = pr_comment_generator.get_basic_table("PASS", "FAIL", "instruction", 85.0, True, 80.0, 85.0, True, 80.0)
    assert "PASS" in table
    assert "FAIL" not in table


def test_custom_fail_symbol_appears_in_basic_table(pr_comment_generator):
    """Custom fail symbol is rendered when a threshold is not met in the global summary table."""
    table = pr_comment_generator.get_basic_table("PASS", "FAIL", "instruction", 50.0, False, 80.0, 50.0, False, 80.0)
    assert "FAIL" in table


def test_custom_pass_symbol_in_groups_table(pr_comment_generator):
    """Custom pass symbol appears in the Status column of the groups table."""
    ec = EvaluatedReportCoverage("grp", "grp")
    ec.overall_passed = True
    ec.avg_changed_files_passed = True
    ec.overall_coverage_reached = 85.0
    ec.avg_changed_files_coverage_reached = 85.0
    ec.overall_coverage_threshold = 70.0
    ec.changed_files_threshold = 70.0
    ec.avg_changed_files_coverage = Counter(0, 0)
    ec.changed_files_coverage_reached = {}

    table = pr_comment_generator.get_groups_table("OK", "NOTOK", {"grp": ec})
    assert "OK" in table
    assert "NOTOK" not in table


def test_custom_fail_symbol_in_groups_table(pr_comment_generator):
    """Custom fail symbol appears in the Status column of the groups table."""
    ec = EvaluatedReportCoverage("grp", "grp")
    ec.overall_passed = False
    ec.avg_changed_files_passed = False
    ec.overall_coverage_reached = 50.0
    ec.avg_changed_files_coverage_reached = 50.0
    ec.overall_coverage_threshold = 80.0
    ec.changed_files_threshold = 80.0
    ec.avg_changed_files_coverage = Counter(0, 0)
    ec.changed_files_coverage_reached = {}

    table = pr_comment_generator.get_groups_table("OK", "NOTOK", {"grp": ec})
    assert "NOTOK" in table


def test_custom_symbols_in_reports_table(pr_comment_generator):
    """Custom pass/fail symbols appear in the Status column of the reports table."""
    erc_pass = EvaluatedReportCoverage("rep-a", "Unknown")
    erc_pass.overall_passed = True
    erc_pass.avg_changed_files_passed = True
    erc_pass.overall_coverage_reached = 85.0
    erc_pass.avg_changed_files_coverage_reached = 85.0
    erc_pass.overall_coverage_threshold = 0.0
    erc_pass.changed_files_threshold = 0.0
    erc_pass.per_changed_file_threshold = 0.0
    erc_pass.avg_changed_files_coverage = Counter(0, 0)
    erc_pass.changed_files_coverage_reached = {}
    erc_pass.changed_files_passed = {}

    erc_fail = EvaluatedReportCoverage("rep-b", "Unknown")
    erc_fail.overall_passed = False
    erc_fail.avg_changed_files_passed = True
    erc_fail.overall_coverage_reached = 40.0
    erc_fail.avg_changed_files_coverage_reached = 0.0
    erc_fail.overall_coverage_threshold = 80.0
    erc_fail.changed_files_threshold = 0.0
    erc_fail.per_changed_file_threshold = 0.0
    erc_fail.avg_changed_files_coverage = Counter(0, 0)
    erc_fail.changed_files_coverage_reached = {}
    erc_fail.changed_files_passed = {}

    table = pr_comment_generator.get_reports_table("OK", "NOTOK", {"rep-a": erc_pass, "rep-b": erc_fail})
    assert "OK" in table
    assert "NOTOK" in table


def test_custom_symbols_in_changed_files_table(pr_comment_generator):
    """Custom symbols appear in the Status column of the changed-files table."""
    erc = EvaluatedReportCoverage("rep", "Unknown")
    erc.overall_passed = True
    erc.avg_changed_files_passed = True
    erc.overall_coverage_reached = 90.0
    erc.avg_changed_files_coverage_reached = 90.0
    erc.overall_coverage_threshold = 0.0
    erc.changed_files_threshold = 0.0
    erc.per_changed_file_threshold = 0.0
    erc.avg_changed_files_coverage = Counter(0, 10)
    erc.changed_files_coverage_reached = {"src/Foo.java": 90.0}
    erc.changed_files_passed = {"src/Foo.java": True}

    table = pr_comment_generator.generate_changed_files_table_without_baseline("PASS", "FAIL", {"rep": erc})
    assert "PASS" in table
    assert "FAIL" not in table


def test_custom_fail_symbol_in_changed_files_table(pr_comment_generator):
    """Custom fail symbol appears in the changed-files table when a file fails."""
    erc = EvaluatedReportCoverage("rep", "Unknown")
    erc.overall_passed = False
    erc.avg_changed_files_passed = False
    erc.overall_coverage_reached = 30.0
    erc.avg_changed_files_coverage_reached = 30.0
    erc.overall_coverage_threshold = 80.0
    erc.changed_files_threshold = 80.0
    erc.per_changed_file_threshold = 80.0
    erc.avg_changed_files_coverage = Counter(7, 3)
    erc.changed_files_coverage_reached = {"src/Bar.java": 30.0}
    erc.changed_files_passed = {"src/Bar.java": False}

    table = pr_comment_generator.generate_changed_files_table_without_baseline("PASS", "FAIL", {"rep": erc})
    assert "FAIL" in table


# ---------------------------------------------------------------------------
# G4b  Baseline delta matched by report title
# ---------------------------------------------------------------------------

def test_baseline_report_matched_by_name(make_report_file_coverage, make_coverage, mocker, pr_comment_generator):
    """Baseline delta for a report uses its name (title) as the match key."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")

    current = make_report_file_coverage(
        name="module-a",
        overall_coverage=make_coverage(instruction=Counter(missed=2, covered=8)),
    )
    baseline = make_report_file_coverage(
        name="module-a",
        overall_coverage=make_coverage(instruction=Counter(missed=4, covered=6)),
    )

    evaluator = CoverageEvaluator(
        report_files_coverage=[current],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
    )
    evaluator.evaluate()

    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[baseline],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
    )
    bs_evaluator.evaluate()

    pr_comment_generator.evaluator = evaluator
    pr_comment_generator.bs_evaluator = bs_evaluator

    ev = evaluator.evaluated_reports_coverage["report.xml"]
    diff_o, _ = pr_comment_generator._calculate_baseline_report_diffs(ev)
    assert abs(diff_o - 20.0) < 0.1


def test_baseline_mismatched_name_yields_zero_delta(make_report_file_coverage, make_coverage, mocker, pr_comment_generator):
    """When the report name has no matching baseline entry, delta is 0.0."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")

    baseline = make_report_file_coverage(
        name="module-a",
        overall_coverage=make_coverage(instruction=Counter(missed=0, covered=10)),
    )
    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[baseline],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
    )
    bs_evaluator.evaluate()
    pr_comment_generator.bs_evaluator = bs_evaluator

    unmatched = EvaluatedReportCoverage("module-b", "Unknown")
    unmatched.overall_coverage_reached = 80.0
    unmatched.avg_changed_files_coverage_reached = 0.0

    diff_o, diff_ch = pr_comment_generator._calculate_baseline_report_diffs(unmatched)
    assert diff_o == 0.0
    assert diff_ch == 0.0


# ---------------------------------------------------------------------------
# G6  Title change orphans old comment; new comment is created
# ---------------------------------------------------------------------------

def test_title_change_creates_new_comment_orphans_old(mocker, mock_github, test_evaluator):
    """Changing title creates a new comment; the old comment with the previous title is not touched."""
    empty_bs = _make_empty_evaluator()
    gen = PRCommentGenerator(mock_github, test_evaluator, empty_bs, pr_number=1)
    _configure_generator_for_comment_tests(gen, mocker, comment_level=CommentLevelEnum.MINIMAL)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="New Title")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=True)
    mock_github.get_comments.return_value = [{"id": 99, "body": "**Old Title**\n\nold coverage content"}]

    gen.generate()

    mock_github.add_comment.assert_called_once()
    mock_github.update_comment.assert_not_called()
    mock_github.delete_comment.assert_not_called()


# ---------------------------------------------------------------------------
# G7  Two distinct titles produce two independent comments
# ---------------------------------------------------------------------------

def test_two_generators_with_different_titles_post_independently(mocker, mock_github):
    """Two PRCommentGenerators with distinct titles each post their own comment independently."""
    ev_a = CoverageEvaluator(report_files_coverage=[], global_min_coverage_overall=0.0,
                              global_min_coverage_changed_files=0.0)
    ev_a.total_coverage_overall = 85.0
    ev_a.total_coverage_overall_passed = True
    ev_a.total_coverage_changed_files = 80.0
    ev_a.total_coverage_changed_files_passed = True

    bs_ev = _make_empty_evaluator()
    gen_a = PRCommentGenerator(mock_github, ev_a, bs_ev, pr_number=1)
    _configure_generator_for_comment_tests(gen_a, mocker, comment_level=CommentLevelEnum.MINIMAL)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="Team A Coverage")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=True)
    gen_a.generate()

    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="Team B Coverage")
    mock_github.get_comments.return_value = [{"id": 1, "body": "**Team A Coverage**\n\nteam a content"}]

    ev_b = CoverageEvaluator(report_files_coverage=[], global_min_coverage_overall=0.0,
                              global_min_coverage_changed_files=0.0)
    ev_b.total_coverage_overall = 90.0
    ev_b.total_coverage_overall_passed = True
    ev_b.total_coverage_changed_files = 85.0
    ev_b.total_coverage_changed_files_passed = True
    gen_b = PRCommentGenerator(mock_github, ev_b, bs_ev, pr_number=1)
    gen_b.generate()

    assert mock_github.add_comment.call_count == 2
    mock_github.update_comment.assert_not_called()


# ---------------------------------------------------------------------------
# G8  debug flag has no effect on comment content
# ---------------------------------------------------------------------------

def test_debug_flag_does_not_change_comment_body(mocker, mock_github, test_evaluator):
    """Comment body is byte-for-byte identical whether get_debug() returns True or False."""
    empty_bs = _make_empty_evaluator()

    def _generate_body(debug_val):
        mock_github.reset_mock()
        mock_github.get_comments.return_value = []
        mocker.patch("jacoco_report.action_inputs.ActionInputs.get_debug", return_value=debug_val)
        mocker.patch("jacoco_report.action_inputs.ActionInputs.get_repository", return_value="owner/repo")
        gen = PRCommentGenerator(mock_github, test_evaluator, empty_bs, pr_number=1)
        _configure_generator_for_comment_tests(gen, mocker, comment_level=CommentLevelEnum.MINIMAL)
        gen.generate()
        return mock_github.add_comment.call_args[0][1]

    body_false = _generate_body(False)
    body_true = _generate_body(True)
    assert body_false == body_true


def test_debug_flag_not_consulted_during_generate(mocker, mock_github, test_evaluator):
    """PRCommentGenerator.generate() never reads the debug flag."""
    empty_bs = _make_empty_evaluator()
    gen = PRCommentGenerator(mock_github, test_evaluator, empty_bs, pr_number=1)
    _configure_generator_for_comment_tests(gen, mocker, comment_level=CommentLevelEnum.MINIMAL)
    debug_spy = mocker.spy(ActionInputs, "get_debug")
    gen.generate()
    debug_spy.assert_not_called()


# ---------------------------------------------------------------------------
# G12  update-comment: false appends even when a matching title already exists
# ---------------------------------------------------------------------------

def test_update_comment_false_appends_despite_matching_title(mocker, mock_github, test_evaluator):
    """update-comment=false causes add_comment to be called even when an existing comment matches the title."""
    empty_bs = _make_empty_evaluator()
    gen = PRCommentGenerator(mock_github, test_evaluator, empty_bs, pr_number=1)
    _configure_generator_for_comment_tests(gen, mocker, comment_level=CommentLevelEnum.MINIMAL)
    mock_github.get_comments.return_value = [{"id": 99, "body": "**JaCoCo**\n\nold content"}]

    gen.generate()

    mock_github.add_comment.assert_called_once()
    mock_github.update_comment.assert_not_called()


@pytest.mark.parametrize("level", [CommentLevelEnum.MINIMAL, CommentLevelEnum.FULL, CommentLevelEnum.CHANGED])
def test_update_comment_false_appends_across_comment_levels(mocker, mock_github, test_evaluator, level):
    """update-comment=false appends a new comment for every comment level that posts content."""
    empty_bs = _make_empty_evaluator()
    gen = PRCommentGenerator(mock_github, test_evaluator, empty_bs, pr_number=1)
    _configure_generator_for_comment_tests(gen, mocker, comment_level=level)
    mock_github.get_comments.return_value = [{"id": 99, "body": "**JaCoCo**\n\nprevious content"}]

    gen.generate()

    mock_github.add_comment.assert_called_once()
    mock_github.update_comment.assert_not_called()


# ---------------------------------------------------------------------------
# G13  Title identity key does not match comments with a different title
# ---------------------------------------------------------------------------

def test_title_identity_key_does_not_match_different_title(mocker, mock_github, test_evaluator):
    """Generator with 'New JaCoCo' title does not update a comment that starts with 'Old JaCoCo'."""
    empty_bs = _make_empty_evaluator()
    gen = PRCommentGenerator(mock_github, test_evaluator, empty_bs, pr_number=1)
    _configure_generator_for_comment_tests(gen, mocker, comment_level=CommentLevelEnum.MINIMAL)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_title", return_value="New JaCoCo")
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=True)
    mock_github.get_comments.return_value = [{"id": 99, "body": "**Old JaCoCo**\n\nold coverage content"}]

    gen.generate()

    mock_github.update_comment.assert_not_called()
    mock_github.add_comment.assert_called_once()


def test_title_identity_key_matches_correct_comment(mocker, mock_github, test_evaluator):
    """Generator with 'JaCoCo' title DOES update the comment that starts with '**JaCoCo**'."""
    empty_bs = _make_empty_evaluator()
    gen = PRCommentGenerator(mock_github, test_evaluator, empty_bs, pr_number=1)
    _configure_generator_for_comment_tests(gen, mocker, comment_level=CommentLevelEnum.MINIMAL)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_update_comment", return_value=True)
    mock_github.get_comments.return_value = [{"id": 42, "body": "**JaCoCo**\n\nexisting coverage content"}]

    gen.generate()

    mock_github.update_comment.assert_called_once_with(42, mocker.ANY)


# ---------------------------------------------------------------------------
# Ungrouped Reports Warning (G14)
# ---------------------------------------------------------------------------

def test_no_warning_all_reports_grouped(mocker, mock_github, test_evaluator):
    """No warning when all reports are matched to groups."""
    gen = PRCommentGenerator(mock_github, test_evaluator, None, pr_number=1, ungrouped_reports=[])
    _configure_generator_for_comment_tests(gen, mocker, comment_level=CommentLevelEnum.FULL)
    _set_mixed_comment_level_fixture(gen)

    title, body = gen._get_comment_content(CommentLevelEnum.FULL)

    assert "Warning:" not in body
    assert "not assigned to any group" not in body


def test_warning_one_ungrouped_report(mocker, mock_github, test_evaluator):
    """Warning section appears when 1 report is unmatched."""
    gen = PRCommentGenerator(mock_github, test_evaluator, None, pr_number=1, ungrouped_reports=["infra/target/jacoco.xml"])
    _configure_generator_for_comment_tests(gen, mocker, comment_level=CommentLevelEnum.FULL)
    _set_mixed_comment_level_fixture(gen)

    title, body = gen._get_comment_content(CommentLevelEnum.FULL)

    assert "Warning:" in body or "warning" in body.lower()
    assert "not assigned to any group" in body
    assert "infra/target/jacoco.xml" in body


def test_warning_multiple_ungrouped(mocker, mock_github, test_evaluator):
    """Warning section lists all ungrouped reports."""
    ungrouped = ["infra/target/jacoco.xml", "tests/target/jacoco.xml"]
    gen = PRCommentGenerator(mock_github, test_evaluator, None, pr_number=1, ungrouped_reports=ungrouped)
    _configure_generator_for_comment_tests(gen, mocker, comment_level=CommentLevelEnum.FULL)
    _set_mixed_comment_level_fixture(gen)

    title, body = gen._get_comment_content(CommentLevelEnum.FULL)

    assert "infra/target/jacoco.xml" in body
    assert "tests/target/jacoco.xml" in body


def test_no_warning_empty_ungrouped_list(mocker, mock_github, test_evaluator):
    """No warning when ungrouped_reports list is empty."""
    gen = PRCommentGenerator(mock_github, test_evaluator, None, pr_number=1, ungrouped_reports=[])
    _configure_generator_for_comment_tests(gen, mocker, comment_level=CommentLevelEnum.FULL)
    _set_mixed_comment_level_fixture(gen)

    title, body = gen._get_comment_content(CommentLevelEnum.FULL)

    assert "not assigned to any group" not in body
    mock_github.add_comment.assert_not_called()