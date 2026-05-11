import pytest

from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.generator.pr_comment_generator import PRCommentGenerator
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.utils.enums import MetricTypeEnum


@pytest.fixture
def mock_github(mocker):
    return mocker.Mock()

@pytest.fixture
def test_evaluator(mocker):
    ce = CoverageEvaluator(
        report_files_coverage=[],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=80.0,
        global_min_coverage_changed_per_file=80.0,
    )
    ce.total_coverage_overall = 85.2
    ce.total_coverage_overall_passed = True
    ce.total_coverage_changed_files = 78.4
    ce.total_coverage_changed_files_passed = False
    return ce

@pytest.fixture
def pr_comment_generator(mock_github, test_evaluator):
    return PRCommentGenerator(mock_github, test_evaluator, None, 1)

def testget_basic_table(pr_comment_generator, mocker):
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
    # Mock the baseline evaluator with some values
    mock_baseline_evaluator = mocker.Mock()
    mock_baseline_evaluator.evaluated_groups_coverage = {
        "module-a": EvaluatedReportCoverage("module-a")
    }
    mock_baseline_evaluator.evaluated_groups_coverage["module-a"].overall_coverage_reached = 70.0
    mock_baseline_evaluator.evaluated_groups_coverage["module-a"].avg_changed_files_coverage_reached = 75.0
    pr_comment_generator.bs_evaluator = mock_baseline_evaluator

    # Create an evaluated coverage module with different values
    evaluated_coverage_module = EvaluatedReportCoverage("module-a")
    evaluated_coverage_module.overall_coverage_reached = 80.0
    evaluated_coverage_module.avg_changed_files_coverage_reached = 85.0

    # Calculate the differences
    diff_o, diff_ch = pr_comment_generator.calculate_baseline_group_diffs(evaluated_coverage_module)

    # Assert the differences are calculated correctly
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

def testgenerate_changed_files_table_with_baseline(pr_comment_generator, mocker):
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

def testgenerate_changed_files_table_with_baseline_no_evaluated_report_coverage(pr_comment_generator, mocker):
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

def testgenerate_changed_files_table_with_baseline_no_changed_file(pr_comment_generator, mocker):
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

    bs_ev = EvaluatedReportCoverage("backend")
    bs_ev.overall_coverage_reached = 80.0
    bs_ev.avg_changed_files_coverage_reached = 75.0
    bs_evaluator = mocker.Mock()
    bs_evaluator.evaluated_groups_coverage = {"backend": bs_ev}
    pr_comment_generator.bs_evaluator = bs_evaluator

    table = pr_comment_generator.get_groups_table("✅", "❌")

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


def test_reports_table_does_not_call_get_report_groups_per_row(pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=50.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=50.0)
    get_groups_mock = mocker.patch("jacoco_report.action_inputs.ActionInputs.get_report_groups", return_value=[])

    ev = EvaluatedReportCoverage("backend-report")
    ev.overall_coverage_reached = 90.0
    ev.avg_changed_files_coverage_reached = 85.0
    ev.overall_coverage_threshold = 75.0
    ev.changed_files_threshold = 70.0
    ev.overall_passed = True
    ev.avg_changed_files_passed = True
    pr_comment_generator.evaluator.evaluated_reports_coverage = {"backend-report": ev}
    pr_comment_generator.evaluator.evaluated_groups_coverage = {"backend": EvaluatedReportCoverage("backend")}

    table = pr_comment_generator.get_reports_table("✅", "❌")

    assert "50.0% / 50.0%" in table
    get_groups_mock.assert_called_once()

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

    bs_ev = EvaluatedReportCoverage("backend")
    bs_ev.overall_coverage_reached = 80.0
    bs_ev.avg_changed_files_coverage_reached = 75.0
    bs_evaluator = mocker.Mock()
    bs_evaluator.evaluated_groups_coverage = {"backend": bs_ev}
    pr_comment_generator.bs_evaluator = bs_evaluator

    table = pr_comment_generator.get_groups_table("✅", "❌")

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