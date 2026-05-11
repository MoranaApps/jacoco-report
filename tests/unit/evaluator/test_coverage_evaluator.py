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

    group = ReportGroup(name="module-a", paths=["**"])
    evaluated_coverage = evaluator.evaluate_group(evaluated_coverage, group)

    assert evaluated_coverage.overall_coverage_reached == 0.0
    assert evaluated_coverage.overall_passed is True


def _make_minimal_report(name: str, group_name: str) -> ReportFileCoverage:
    overall = Coverage(
        instruction=Counter(missed=0, covered=10),
        branch=Counter(missed=0, covered=10),
        line=Counter(missed=0, covered=10),
        complexity=Counter(missed=0, covered=10),
        method=Counter(missed=0, covered=10),
        clazz=Counter(missed=0, covered=10),
    )
    return ReportFileCoverage(path=f"{name}.xml", name=name, overall_coverage=overall,
                              changed_files_coverage={}, group_name=group_name)


def test_threshold_uses_group_when_matched(mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    group = ReportGroup(name="team-a", paths=["**"], min_coverage_overall=70.0,
                        min_coverage_changed_files=60.0, min_coverage_per_changed_file=50.0)
    report = _make_minimal_report("report-a", "team-a")
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=75.0,
        global_min_coverage_changed_per_file=65.0,
        report_groups=[group],
    )
    evaluator.evaluate()
    ev = evaluator.evaluated_reports_coverage["report-a"]
    assert ev.overall_coverage_threshold == 70.0
    assert ev.changed_files_threshold == 60.0
    assert ev.per_changed_file_threshold == 50.0


def test_threshold_falls_back_to_report_thresholds_default_when_no_group_matches(mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    group = ReportGroup(name="team-a", paths=["**"])
    # report belongs to no group (group_name not set / doesn't match any ReportGroup)
    report = _make_minimal_report("report-b", "unknown-group")
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=75.0,
        global_min_coverage_changed_per_file=65.0,
        report_groups=[group],
        report_thresholds_default=(55.0, 45.0, 35.0),
    )
    evaluator.evaluate()
    ev = evaluator.evaluated_reports_coverage["report-b"]
    # fallback chain: group field → report-thresholds-default → 0.0 (global NOT in chain)
    assert ev.overall_coverage_threshold == 55.0
    assert ev.changed_files_threshold == 45.0
    assert ev.per_changed_file_threshold == 35.0


def test_threshold_partial_group_thresholds_fall_back_to_report_thresholds_default(mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    group = ReportGroup(name="team-a", paths=["**"], min_coverage_overall=70.0)
    report = _make_minimal_report("report-c", "team-a")
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=75.0,
        global_min_coverage_changed_per_file=65.0,
        report_groups=[group],
        report_thresholds_default=(55.0, 45.0, 35.0),
    )
    evaluator.evaluate()
    ev = evaluator.evaluated_reports_coverage["report-c"]
    # overall is set on the group; changed_files and per_file fall back to report_thresholds_default
    assert ev.overall_coverage_threshold == 70.0
    assert ev.changed_files_threshold == 45.0
    assert ev.per_changed_file_threshold == 35.0


def test_evaluate_report_docstring_mentions_report_thresholds_default_fallback():
    doc = CoverageEvaluator._evaluate_report.__doc__
    assert doc is not None
    assert "report-thresholds-default" in doc
    assert "global-thresholds is a separate" in doc
    assert "evaluation pass" in doc


# --- Task 29: report-thresholds-default fallback chain tests ---

def test_report_thresholds_default_fallback_all_explicit(mocker):
    """All three threshold fields set on the group — report_thresholds_default is never used."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    group = ReportGroup(
        name="team-a",
        paths=["**"],
        min_coverage_overall=80.0,
        min_coverage_changed_files=70.0,
        min_coverage_per_changed_file=60.0,
    )
    report = _make_minimal_report("report-a", "team-a")
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=50.0,
        report_groups=[group],
        report_thresholds_default=(55.0, 45.0, 35.0),
    )
    evaluator.evaluate()
    ev = evaluator.evaluated_reports_coverage["report-a"]
    assert ev.overall_coverage_threshold == 80.0
    assert ev.changed_files_threshold == 70.0
    assert ev.per_changed_file_threshold == 60.0


def test_report_thresholds_default_fallback_from_default(mocker):
    """Group has no thresholds — all three fields fall back to report_thresholds_default."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    group = ReportGroup(name="team-b", paths=["**"])
    report = _make_minimal_report("report-b", "team-b")
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=50.0,
        report_groups=[group],
        report_thresholds_default=(75.0, 60.0, 40.0),
    )
    evaluator.evaluate()
    ev = evaluator.evaluated_reports_coverage["report-b"]
    assert ev.overall_coverage_threshold == 75.0
    assert ev.changed_files_threshold == 60.0
    assert ev.per_changed_file_threshold == 40.0


def test_report_thresholds_default_fallback_to_zero(mocker):
    """Group has no thresholds and report_thresholds_default is (0,0,0) — effective threshold is 0.0."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    group = ReportGroup(name="team-c", paths=["**"])
    report = _make_minimal_report("report-c", "team-c")
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=50.0,
        report_groups=[group],
        report_thresholds_default=(0.0, 0.0, 0.0),
    )
    evaluator.evaluate()
    ev = evaluator.evaluated_reports_coverage["report-c"]
    assert ev.overall_coverage_threshold == 0.0
    assert ev.changed_files_threshold == 0.0
    assert ev.per_changed_file_threshold == 0.0


def test_report_thresholds_default_field_level_mix(mocker):
    """Group sets overall only; avg and per-file fall back to report_thresholds_default fields."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    group = ReportGroup(name="team-d", paths=["**"], min_coverage_overall=80.0)
    report = _make_minimal_report("report-d", "team-d")
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=50.0,
        report_groups=[group],
        report_thresholds_default=(75.0, 60.0, 0.0),
    )
    evaluator.evaluate()
    ev = evaluator.evaluated_reports_coverage["report-d"]
    assert ev.overall_coverage_threshold == 80.0   # from group
    assert ev.changed_files_threshold == 60.0       # from report_thresholds_default
    assert ev.per_changed_file_threshold == 0.0     # from report_thresholds_default


def test_global_thresholds_unaffected_by_report_thresholds_default(mocker):
    """global-thresholds evaluation uses only global values; report_thresholds_default has no effect on it."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    overall_coverage = Coverage(
        instruction=Counter(missed=5, covered=5),
        branch=Counter(missed=0, covered=10),
        line=Counter(missed=0, covered=10),
        complexity=Counter(missed=0, covered=10),
        method=Counter(missed=0, covered=10),
        clazz=Counter(missed=0, covered=10),
    )
    report = ReportFileCoverage(
        path="report.xml",
        name="report",
        overall_coverage=overall_coverage,
        changed_files_coverage={},
    )
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=60.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=0.0,
        report_thresholds_default=(90.0, 90.0, 90.0),
    )
    evaluator.evaluate()
    # Global check uses 60.0; 50% coverage < 60.0 → should fail
    assert evaluator.total_coverage_overall_passed is False
    assert evaluator.total_coverage_overall == pytest.approx(50.0, 0.01)


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
    group = ReportGroup(name="team-a", paths=["**"], min_coverage_overall=80.0)
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
    group = ReportGroup(name="integration-tests", paths=["**"])
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
    group = ReportGroup(name="backend", paths=["**"])
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