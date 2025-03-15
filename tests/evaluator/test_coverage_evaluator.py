import pytest
from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.generator.pr_comment_generator import PRCommentGenerator
from jacoco_report.model.counter import Counter
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.model.file_coverage import FileCoverage
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.model.coverage import Coverage
from jacoco_report.utils.enums import SensitivityEnum
from jacoco_report.utils.github import GitHub


@pytest.fixture
def sample_report_file_coverage():
    overall_coverage = Coverage(
        instruction=Counter(missed=5, covered=10),
        branch=Counter(missed=3, covered=7),
        line=Counter(missed=2, covered=8),
        complexity=Counter(missed=1, covered=9),
        method=Counter(missed=4, covered=6),
        clazz=Counter(missed=0, covered=5)
    )
    changed_files_coverage = {
        "com/example/Example.java": FileCoverage(
            file_name="Example.java",
            file_path="com/example",
            instruction=Counter(missed=1, covered=9),
            branch=Counter(missed=0, covered=7),
            line=Counter(missed=2, covered=8),
            complexity=Counter(missed=1, covered=9),
            method=Counter(missed=4, covered=6),
            clazz=Counter(missed=0, covered=5)
        )
    }
    return ReportFileCoverage(
        path="sample_report.xml",
        name="Sample Report Name",
        overall_coverage=overall_coverage,
        changed_files_coverage=changed_files_coverage
    )

@pytest.fixture
def evaluator(sample_report_file_coverage):
    return CoverageEvaluator(
        report_files_coverage=[sample_report_file_coverage],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0
    )

def test_evaluate_overall_coverage(evaluator):
    evaluator.evaluate()
    assert evaluator.total_coverage_overall == pytest.approx(66.67, 0.01)
    assert evaluator.total_coverage_overall_passed is True

def test_evaluate_changed_files_coverage(evaluator):
    evaluator.evaluate()
    assert evaluator.total_coverage_changed_files == pytest.approx(90.0, 0.01)
    assert evaluator.total_coverage_changed_files_passed is True

def test_evaluate_with_low_thresholds(evaluator):
    evaluator._global_min_coverage_overall = 70.0
    evaluator._global_min_coverage_changed_files = 95.0
    evaluator.evaluate()
    assert evaluator.total_coverage_overall_passed is False
    assert evaluator.total_coverage_changed_files_passed is False


# _review_violations

def test_review_violations_global_overall_coverage_below_threshold(evaluator, mocker):
    evaluator.total_coverage_overall = 40.0
    evaluator.total_coverage_changed_files = 90.0
    evaluator.total_coverage_overall_passed = False
    evaluator.total_coverage_changed_files_passed = True

    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_sensitivity", return_value=SensitivityEnum.DETAIL)
    evaluator._review_violations()

    assert "Global overall coverage 40.0 is below the threshold 50.0." in evaluator.violations


def test_review_violations_global_overall_coverage_below_threshold_minimal(evaluator, mocker):
    evaluator.total_coverage_overall = 60.0
    evaluator.total_coverage_changed_files = 90.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = True

    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_sensitivity", return_value=SensitivityEnum.MINIMAL)
    evaluator._review_violations()

    assert evaluator.violations == []


def test_review_violations_global_changed_files_coverage_below_threshold(evaluator, mocker):
    evaluator.total_coverage_overall = 75.0
    evaluator.total_coverage_changed_files = 40.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = False

    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_sensitivity", return_value=SensitivityEnum.DETAIL)
    evaluator._review_violations()

    assert "Global changed files coverage 40.0 is below the threshold 50.0." in evaluator.violations

def test_review_violations_module_overall_coverage_below_threshold(evaluator, mocker):
    evaluator.total_coverage_overall = 75.0
    evaluator.total_coverage_changed_files = 80.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = True

    module_evaluated_coverage: EvaluatedReportCoverage = EvaluatedReportCoverage("module-a")
    module_evaluated_coverage.overall_coverage_reached = 40.0
    module_evaluated_coverage.overall_passed = False
    module_evaluated_coverage.overall_coverage_threshold = 50.0

    evaluator.evaluated_modules_coverage = {
        "module-a": module_evaluated_coverage
    }
    evaluator._review_violations()

    assert "Module 'module-a' overall coverage 40.0 is below the threshold 50.0." in evaluator.violations

def test_review_violations_module_changed_files_coverage_below_threshold(evaluator, mocker):
    evaluator.total_coverage_overall = 75.0
    evaluator.total_coverage_changed_files = 80.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = True

    module_evaluated_coverage: EvaluatedReportCoverage = EvaluatedReportCoverage("module-a")
    module_evaluated_coverage.overall_coverage_reached = 60.0
    module_evaluated_coverage.overall_passed = True
    module_evaluated_coverage.overall_coverage_threshold = 50.0

    module_evaluated_coverage.sum_changed_files_passed = False
    module_evaluated_coverage.sum_changed_files_coverage_reached = 40.0
    module_evaluated_coverage.changed_files_threshold = 50.0

    evaluator.evaluated_modules_coverage = {
        "module-a": module_evaluated_coverage
    }
    evaluator._review_violations()

    assert "Module 'module-a' changed files coverage 40.0 is below the threshold 50.0." in evaluator.violations

def test_review_violations_sensitivity_summary(evaluator, mocker):
    # evaluator.total_coverage_overall = 75.0
    # evaluator.total_coverage_changed_files = 80.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = True

    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_sensitivity", return_value=SensitivityEnum.SUMMARY)
    evaluator._review_violations()

    assert len(evaluator.violations) == 0

def test_review_violations_report_overall_coverage_below_threshold(evaluator, mocker):
    evaluator.total_coverage_overall = 75.0
    evaluator.total_coverage_changed_files = 80.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = True

    report_evaluated_coverage: EvaluatedReportCoverage = EvaluatedReportCoverage("module-a")
    report_evaluated_coverage.overall_passed = False
    report_evaluated_coverage.overall_coverage_reached = 40.0
    report_evaluated_coverage.overall_coverage_threshold = 50.0

    evaluator.evaluated_reports_coverage = {
        "filepath": report_evaluated_coverage
    }
    evaluator._review_violations()

    assert "Report 'filepath' overall coverage 40.0 is below the threshold 50.0." in evaluator.violations

def test_review_violations_report_changed_files_coverage_below_threshold(evaluator, mocker):
    evaluator.total_coverage_overall = 75.0
    evaluator.total_coverage_changed_files = 80.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = True

    report_evaluated_coverage: EvaluatedReportCoverage = EvaluatedReportCoverage("module-a")
    report_evaluated_coverage.overall_passed = True
    report_evaluated_coverage.overall_coverage_reached = 60.0
    report_evaluated_coverage.overall_coverage_threshold = 50.0

    report_evaluated_coverage.sum_changed_files_passed = False
    report_evaluated_coverage.sum_changed_files_coverage_reached = 40.0
    report_evaluated_coverage.changed_files_threshold = 50.0

    report_evaluated_coverage.changed_files_coverage_reached = {
        "filepath/report": 40.0
    }
    report_evaluated_coverage.changed_files_passed = {
        "filepath/report": False
    }

    evaluator.evaluated_reports_coverage = {
        "filepath": report_evaluated_coverage
    }
    evaluator._review_violations()

    assert "Report 'filepath' changed files coverage 40.0 is below the threshold 50.0." in evaluator.violations

def test_evaluate_module_with_patched_thresholds(mocker):
    # Create a sample report file coverage
    overall_coverage = Coverage(
        instruction=Counter(missed=0, covered=0),
        branch=Counter(missed=0, covered=0),
        line=Counter(missed=0, covered=0),
        complexity=Counter(missed=0, covered=0),
        method=Counter(missed=0, covered=0),
        clazz=Counter(missed=0, covered=0)
    )
    changed_files_coverage = {
        "file1.java": FileCoverage(
            file_name="file1.java",
            file_path="path/to/file1.java",
            instruction=Counter(missed=0, covered=0),
            branch=Counter(missed=0, covered=0),
            line=Counter(missed=0, covered=0),
            complexity=Counter(missed=0, covered=0),
            method=Counter(missed=0, covered=0),
            clazz=Counter(missed=0, covered=0)
        )
    }
    report_file_coverage = ReportFileCoverage(
        path="sample_report.xml",
        name="Sample Report Name",
        overall_coverage=overall_coverage,
        changed_files_coverage=changed_files_coverage
    )

    # Create an instance of CoverageEvaluator
    evaluator = CoverageEvaluator(
        report_files_coverage=[report_file_coverage],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0
    )

    # Patch the _set_thresholds method
    mocker.patch.object(evaluator, '_set_thresholds', return_value=(50.0, 50.0))

    # Create an evaluated coverage module with no coverage
    evaluated_coverage_module = EvaluatedReportCoverage("module-a")
    evaluated_coverage_module.overall_coverage.covered = 0
    evaluated_coverage_module.overall_coverage.missed = 0

    # Evaluate the module
    evaluated_coverage_module = evaluator._evaluate_module(evaluated_coverage_module)

    # Assert that the overall coverage reached is 0.0 and it passed
    assert evaluated_coverage_module.overall_coverage_reached == 0.0
    assert evaluated_coverage_module.overall_passed is True