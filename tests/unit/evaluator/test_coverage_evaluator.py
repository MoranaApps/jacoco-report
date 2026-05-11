import pytest
from jacoco_report.evaluator.coverage_evaluator import CoverageEvaluator
from jacoco_report.model.counter import Counter
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.model.file_coverage import FileCoverage
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.model.coverage import Coverage
from jacoco_report.model.report_group import ReportGroup

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
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=50.0
    )

def test_evaluate_overall_coverage(evaluator):
    evaluator.evaluate()
    assert evaluator.total_coverage_overall == pytest.approx(66.67, 0.01)
    assert evaluator.total_coverage_overall_passed is True

def test_evaluate_changed_files_coverage(evaluator):
    evaluator.evaluate()
    assert evaluator.total_coverage_changed_files == pytest.approx(90.0, 0.01)
    assert evaluator.total_coverage_changed_files_passed is True

def test_evaluate_with_low_thresholds(sample_report_file_coverage):
    evaluator = CoverageEvaluator(
        report_files_coverage=[sample_report_file_coverage],
        global_min_coverage_overall=70.0,
        global_min_coverage_changed_files=95.0,
        global_min_coverage_changed_per_file=50.0
    )
    evaluator.evaluate()
    assert evaluator.total_coverage_overall_passed is False
    assert evaluator.total_coverage_changed_files_passed is False


# _review_violations

def test_review_violations_global_overall_coverage_below_threshold(evaluator,):
    evaluator.total_coverage_overall = 40.0
    evaluator.total_coverage_changed_files = 90.0
    evaluator.total_coverage_overall_passed = False
    evaluator.total_coverage_changed_files_passed = True

    evaluator.review_violations()

    assert "Global overall coverage 40.0 is below the threshold 50.0." in evaluator.violations


def test_review_violations_global_overall_coverage_below_threshold_minimal(evaluator, mocker):
    evaluator.total_coverage_overall = 60.0
    evaluator.total_coverage_changed_files = 90.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = True

    evaluator.review_violations()

    assert evaluator.violations == []


def test_review_violations_global_changed_files_coverage_below_threshold(evaluator, mocker):
    evaluator.total_coverage_overall = 75.0
    evaluator.total_coverage_changed_files = 40.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = False

    evaluator.review_violations()

    assert "Global changed files coverage 40.0 is below the threshold 50.0." in evaluator.violations


def test_review_violations_global_changed_files_coverage_zero_no_changed_file(evaluator, mocker):
    evaluator.total_coverage_overall = 75.0
    evaluator.total_coverage_changed_files = 0.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = True

    evaluator.review_violations()

    assert len(evaluator.violations) == 0


def test_review_violations_global_changed_files_coverage_zero_w_changed_file(evaluator, mocker):
    evaluator.total_coverage_overall = 75.0
    evaluator.total_coverage_changed_files = 0.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = False

    evaluator.review_violations()

    assert "Global changed files coverage 0.0 is below the threshold 50.0." in evaluator.violations

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
    evaluator.review_violations()

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

    report_evaluated_coverage.avg_changed_files_passed = False
    report_evaluated_coverage.avg_changed_files_coverage_reached = 40.0
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
    evaluator.review_violations()

    assert "Report 'filepath' changed files coverage 40.0 is below the threshold 50.0." in evaluator.violations

def test_evaluate_group_with_zero_coverage(mocker):
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
        changed_files_coverage=changed_files_coverage,

    )

    # Create an instance of CoverageEvaluator
    evaluator = CoverageEvaluator(
        report_files_coverage=[report_file_coverage],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=50.0
    )

    evaluated_coverage = EvaluatedReportCoverage("module-a")
    evaluated_coverage.overall_coverage.covered = 0
    evaluated_coverage.overall_coverage.missed = 0

    group = ReportGroup(name="module-a", paths=[])
    evaluated_coverage = evaluator.evaluate_group(evaluated_coverage, group)

    assert evaluated_coverage.overall_coverage_reached == 0.0
    assert evaluated_coverage.overall_passed is True


def test_set_thresholds_uses_group_when_matched():
    group = ReportGroup(name="team-a", paths=[], min_coverage_overall=70.0,
                        min_coverage_changed_files=60.0, min_coverage_per_changed_file=50.0)
    evaluator = CoverageEvaluator(
        report_files_coverage=[],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=75.0,
        global_min_coverage_changed_per_file=65.0,
        report_groups=[group],
    )
    o, ch, pf = evaluator._set_thresholds("team-a")
    assert o == 70.0
    assert ch == 60.0
    assert pf == 50.0


def test_set_thresholds_falls_back_to_global_when_no_match():
    group = ReportGroup(name="team-a", paths=[])
    evaluator = CoverageEvaluator(
        report_files_coverage=[],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=75.0,
        global_min_coverage_changed_per_file=65.0,
        report_groups=[group],
    )
    o, ch, pf = evaluator._set_thresholds("unknown-group")
    assert o == 80.0
    assert ch == 75.0
    assert pf == 65.0


def test_set_thresholds_partial_group_thresholds_fall_back_to_global():
    group = ReportGroup(name="team-a", paths=[], min_coverage_overall=70.0)
    evaluator = CoverageEvaluator(
        report_files_coverage=[],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=75.0,
        global_min_coverage_changed_per_file=65.0,
        report_groups=[group],
    )
    o, ch, pf = evaluator._set_thresholds("team-a")
    assert o == 70.0
    assert ch == 75.0
    assert pf == 65.0


def test_evaluate_populates_evaluated_groups_coverage():
    overall_coverage = Coverage(
        instruction=Counter(missed=0, covered=10),
        branch=Counter(missed=0, covered=10),
        line=Counter(missed=0, covered=10),
        complexity=Counter(missed=0, covered=10),
        method=Counter(missed=0, covered=10),
        clazz=Counter(missed=0, covered=10),
    )
    report = ReportFileCoverage(
        path="report.xml",
        name="My Report",
        overall_coverage=overall_coverage,
        changed_files_coverage={},
        group_name="team-a",
    )
    group = ReportGroup(name="team-a", paths=[], min_coverage_overall=80.0)
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=50.0,
        report_groups=[group],
    )
    evaluator.evaluate()

    assert "team-a" in evaluator.evaluated_groups_coverage
    group_cov = evaluator.evaluated_groups_coverage["team-a"]
    assert group_cov.overall_coverage_threshold == 80.0
    assert group_cov.overall_passed is True


# --- Issue 2: EvaluatedReportCoverage group_name initialization ---

def test_group_name_populated_in_evaluated_coverage():
    """Test that EvaluatedReportCoverage properly initializes group_name field"""
    overall_coverage = Coverage(
        instruction=Counter(missed=0, covered=10),
        branch=Counter(missed=0, covered=10),
        line=Counter(missed=0, covered=10),
        complexity=Counter(missed=0, covered=10),
        method=Counter(missed=0, covered=10),
        clazz=Counter(missed=0, covered=10),
    )
    report = ReportFileCoverage(
        path="report.xml",
        name="My Report",
        overall_coverage=overall_coverage,
        changed_files_coverage={},
        group_name="integration-tests",
    )
    group = ReportGroup(name="integration-tests", paths=[])
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=50.0,
        report_groups=[group],
    )
    evaluator.evaluate()

    group_cov = evaluator.evaluated_groups_coverage["integration-tests"]
    # group_name should be set to group.name, not "Unknown"
    assert group_cov.group_name == "integration-tests"
    assert group_cov.group_name != "Unknown"


def test_group_name_in_serialized_output():
    """Test that group_name is correctly serialized to JSON output"""
    overall_coverage = Coverage(
        instruction=Counter(missed=0, covered=10),
        branch=Counter(missed=0, covered=10),
        line=Counter(missed=0, covered=10),
        complexity=Counter(missed=0, covered=10),
        method=Counter(missed=0, covered=10),
        clazz=Counter(missed=0, covered=10),
    )
    report = ReportFileCoverage(
        path="report.xml",
        name="My Report",
        overall_coverage=overall_coverage,
        changed_files_coverage={},
        group_name="backend",
    )
    group = ReportGroup(name="backend", paths=[])
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=50.0,
        report_groups=[group],
    )
    evaluator.evaluate()

    group_cov = evaluator.evaluated_groups_coverage["backend"]
    group_dict = group_cov.to_dict()
    # to_dict() should include group_name field with correct value
    assert group_dict["group_name"] == "backend"
    assert group_dict["group_name"] != "Unknown"