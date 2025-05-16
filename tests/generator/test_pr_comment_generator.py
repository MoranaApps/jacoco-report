import pytest

from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.generator.pr_comment_generator import PRCommentGenerator
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.model.module import Module
from jacoco_report.utils.enums import SensitivityEnum, MetricTypeEnum


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
        modules={},
    )
    ce.total_coverage_overall = 85.2
    ce.total_coverage_overall_passed = True
    ce.total_coverage_changed_files = 78.4
    ce.total_coverage_changed_files_passed = False
    return ce

@pytest.fixture
def pr_comment_generator(mock_github, test_evaluator):
    return PRCommentGenerator(mock_github, test_evaluator, None, 1)

def test_generate_throws_exception(pr_comment_generator, mocker):
    with pytest.raises(NotImplementedError) as excinfo:
        pr_comment_generator.generate()

    assert str(excinfo.value) == "Subclasses should implement this method"

def test_get_basic_table(pr_comment_generator, mocker):
    table = pr_comment_generator._get_basic_table(
        "✅", "❌", MetricTypeEnum.INSTRUCTION,
        85.2, True, 80.0,
        78.4, False, 80.0
    )

    assert "| **Overall**       | 85.2% | 80.0% | ✅ |" in table
    assert "| **Changed Files** | 78.4% | 80.0% | ❌ |" in table

def test_get_modules_table(pr_comment_generator):
    table = pr_comment_generator._get_modules_table("✅", "❌")
    assert "" == table

def test_get_modules_table_with_baseline_with_modules(pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["baseline.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_modules", return_value={"test", "test2"})
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_not_changed", return_value=False)
    mocker.patch("jacoco_report.generator.pr_comment_generator.PRCommentGenerator._calculate_baseline_module_diffs", return_value=(1.1, 2.0))

    pr_comment_generator.evaluator._modules["test"] = Module("test", "path",85.2, 80.0, 80.0)

    pr_comment_generator.evaluator.evaluated_modules_coverage["test"] = EvaluatedReportCoverage()
    pr_comment_generator.evaluator.evaluated_modules_coverage["test"].name = "test"

    expected_table = """| Module | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|--------|-----------------|------------------|---------------|---------------|
| `test` | 0.0% / 0.0% | 0.0% / 0.0% | +1.1% / +2.0% | ✅/✅ |"""

    table = pr_comment_generator._get_modules_table("✅", "❌")
    assert expected_table == table

def test_generate_modules_table_with_baseline(pr_comment_generator, mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["baseline.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_modules", return_value={"test", "test2"})
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_not_changed", return_value=True)
    mocker.patch("jacoco_report.generator.pr_comment_generator.PRCommentGenerator._calculate_baseline_module_diffs", return_value=(1.1, 2.0))

    pr_comment_generator.evaluator._modules["test"] = Module("test", "path",85.2, 80.0, 80.0)

    pr_comment_generator.evaluator.evaluated_modules_coverage["test"] = EvaluatedReportCoverage()
    pr_comment_generator.evaluator.evaluated_modules_coverage["test"].name = "test"

    expected_table = """| Module | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |\n|--------|-----------------|------------------|---------------|---------------|\n\nNo changed file in reports."""

    table = pr_comment_generator._get_modules_table("✅", "❌")
    assert expected_table == table

def test_get_changed_files_table_without_baseline(pr_comment_generator):
    table = pr_comment_generator._generate_changed_files_table_without_baseline("✅", "❌")
    assert "| File Path | Coverage | Threshold | Status |\n|-----------|----------|-----------|--------|\n\nNo changed file in reports." in table

def test_get_changed_files_table_with_baseline(pr_comment_generator):
    table = pr_comment_generator._generate_changed_files_table_with_baseline("✅", "❌")
    assert "| File Path | Coverage | Threshold | Δ Coverage | Status |\n|-----------|----------|-----------|------------|--------|\n\nNo changed file in reports." in table

def test_calculate_module_diff(pr_comment_generator, mocker):
    # Mock the baseline evaluator with some values
    mock_baseline_evaluator = mocker.Mock()
    mock_baseline_evaluator.evaluated_modules_coverage = {
        "module-a": EvaluatedReportCoverage("module-a")
    }
    mock_baseline_evaluator.evaluated_modules_coverage["module-a"].overall_coverage_reached = 70.0
    mock_baseline_evaluator.evaluated_modules_coverage["module-a"].sum_changed_files_coverage_reached = 75.0
    pr_comment_generator.bs_evaluator = mock_baseline_evaluator

    # Create an evaluated coverage module with different values
    evaluated_coverage_module = EvaluatedReportCoverage("module-a")
    evaluated_coverage_module.overall_coverage_reached = 80.0
    evaluated_coverage_module.sum_changed_files_coverage_reached = 85.0

    # Calculate the differences
    diff_o, diff_ch = pr_comment_generator._calculate_baseline_module_diffs(evaluated_coverage_module)

    # Assert the differences are calculated correctly
    assert diff_o == 10.0
    assert diff_ch == 10.0

def test_calculate_module_diff_no_module_in_baseline(pr_comment_generator, mocker):
    # Mock the baseline evaluator with no modules
    mock_baseline_evaluator = mocker.Mock()
    mock_baseline_evaluator.evaluated_modules_coverage = {}
    pr_comment_generator.bs_evaluator = mock_baseline_evaluator

    # Create an evaluated coverage module
    evaluated_coverage_module = EvaluatedReportCoverage("module-a")
    evaluated_coverage_module.overall_coverage_reached = 80.0
    evaluated_coverage_module.sum_changed_files_coverage_reached = 85.0

    # Calculate the differences
    diff_o, diff_ch = pr_comment_generator._calculate_baseline_module_diffs(evaluated_coverage_module)

    # Assert the differences are zero since the module is not in the baseline
    assert diff_o == 0.0
    assert diff_ch == 0.0

def test_generate_changed_files_table_with_baseline(pr_comment_generator, mocker):
    # Mock the necessary methods and attributes
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["baseline.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_modules", return_value={"test", "test2"})
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_not_changed", return_value=False)
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
    table = pr_comment_generator._generate_changed_files_table_with_baseline("✅", "❌")

    # Assert the table content
    expected_table = """| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [file1.java](https://github.com/fake_repo/pull/1/files#diff-fakehash) | 80.0% | 0.0% | +10.0% | ✅ |"""
    assert table == expected_table

def test_generate_changed_files_table_with_baseline_no_evaluated_report_coverage(pr_comment_generator, mocker):
    # Mock the necessary methods and attributes
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["baseline.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_modules", return_value={"test", "test2"})
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_not_changed", return_value=False)
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
    table = pr_comment_generator._generate_changed_files_table_with_baseline("✅", "❌")

    # Assert the table content
    expected_table = """| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [file1.java](https://github.com/fake_repo/pull/1/files#diff-fakehash) | 80.0% | 0.0% | 0.0% | ✅ |"""
    assert table == expected_table

def test_generate_changed_files_table_with_baseline_no_changed_file(pr_comment_generator, mocker):
    # Mock the necessary methods and attributes
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_baseline_paths", return_value=["baseline.xml"])
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_modules", return_value={"test", "test2"})
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_skip_not_changed", return_value=False)
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
    table = pr_comment_generator._generate_changed_files_table_with_baseline("✅", "❌")

    # Assert the table content
    expected_table = """| File Path | Coverage | Threshold | Δ Coverage | Status |
|-----------|----------|-----------|------------|--------|
| [file1.java](https://github.com/fake_repo/pull/1/files#diff-fakehash) | 80.0% | 0.0% | 0.0% | ✅ |"""
    assert table == expected_table