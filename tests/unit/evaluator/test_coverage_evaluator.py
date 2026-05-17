import logging

import pytest
from pytest_mock import MockerFixture
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


def test_review_violations_global_overall_coverage_below_threshold_minimal(evaluator, mocker: MockerFixture):
    evaluator.total_coverage_overall = 60.0
    evaluator.total_coverage_changed_files = 90.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = True

    evaluator.review_violations()

    assert evaluator.violations == []


def test_review_violations_global_changed_files_coverage_below_threshold(evaluator, mocker: MockerFixture):
    evaluator.total_coverage_overall = 75.0
    evaluator.total_coverage_changed_files = 40.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = False

    evaluator.review_violations()

    assert "Global changed files coverage 40.0 is below the threshold 50.0." in evaluator.violations


def test_review_violations_global_changed_files_coverage_zero_no_changed_file(evaluator, mocker: MockerFixture):
    evaluator.total_coverage_overall = 75.0
    evaluator.total_coverage_changed_files = 0.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = True

    evaluator.review_violations()

    assert len(evaluator.violations) == 0


def test_review_violations_global_changed_files_coverage_zero_w_changed_file(evaluator, mocker: MockerFixture):
    evaluator.total_coverage_overall = 75.0
    evaluator.total_coverage_changed_files = 0.0
    evaluator.total_coverage_overall_passed = True
    evaluator.total_coverage_changed_files_passed = False

    evaluator.review_violations()

    assert "Global changed files coverage 0.0 is below the threshold 50.0." in evaluator.violations

def test_review_violations_report_overall_coverage_below_threshold(evaluator, mocker: MockerFixture):
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

def test_review_violations_report_changed_files_coverage_below_threshold(evaluator, mocker: MockerFixture):
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

def test_evaluate_group_with_zero_coverage(caplog):
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
    with caplog.at_level(logging.INFO, logger="jacoco_report.evaluator.coverage_evaluator"):
        evaluated_coverage = evaluator.evaluate_group(evaluated_coverage, group)

    assert evaluated_coverage.overall_coverage_reached == 0.0
    assert evaluated_coverage.overall_passed is True
    messages = [r.message for r in caplog.records]
    assert "Group 'module-a' has no overall coverage data for selected metric; treated as passed." in messages
    assert not any("Group 'module-a' reached overall coverage" in m for m in messages)


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


def test_threshold_uses_group_when_matched(mocker: MockerFixture):
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


def test_threshold_falls_back_to_report_thresholds_default_when_no_group_matches(mocker: MockerFixture):
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


def test_threshold_partial_group_thresholds_fall_back_to_report_thresholds_default(mocker: MockerFixture):
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


# --- Task 29: report-thresholds-default fallback chain tests ---

def test_report_thresholds_default_fallback_all_explicit(mocker: MockerFixture):
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


def test_report_thresholds_default_fallback_from_default(mocker: MockerFixture):
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


def test_report_thresholds_default_fallback_to_zero(mocker: MockerFixture):
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


def test_report_thresholds_default_field_level_mix(mocker: MockerFixture):
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


def test_global_thresholds_unaffected_by_report_thresholds_default(mocker: MockerFixture):
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


# --- Task 36: Enhanced logging (thresholds + reached values) ---

def _make_report_with_changed_file(name: str, group_name: str = "Unknown") -> ReportFileCoverage:
    overall = Coverage(
        instruction=Counter(missed=2, covered=8),
        branch=Counter(missed=0, covered=10),
        line=Counter(missed=0, covered=10),
        complexity=Counter(missed=0, covered=10),
        method=Counter(missed=0, covered=10),
        clazz=Counter(missed=0, covered=10),
    )
    changed_files = {
        "com/example/Foo.java": FileCoverage(
            file_name="Foo.java",
            file_path="com/example",
            instruction=Counter(missed=1, covered=9),
            branch=Counter(missed=0, covered=10),
            line=Counter(missed=0, covered=10),
            complexity=Counter(missed=0, covered=10),
            method=Counter(missed=0, covered=10),
            clazz=Counter(missed=0, covered=10),
        )
    }
    return ReportFileCoverage(
        path=f"{name}.xml", name=name, overall_coverage=overall,
        changed_files_coverage=changed_files, group_name=group_name,
    )


def test_report_overall_coverage_logged_for_unchanged_report(mocker: MockerFixture, caplog):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    report = _make_minimal_report("atum_agent", "Unknown")
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=0.0,
        report_thresholds_default=(80.0, 0.0, 0.0),
    )
    with caplog.at_level(logging.INFO, logger="jacoco_report.evaluator.coverage_evaluator"):
        evaluator.evaluate()

    messages = [r.message for r in caplog.records]
    assert "Report 'atum_agent' reached overall coverage of 100.0% with threshold set to 80.0%" in messages
    assert not any("average changed files" in m for m in messages)


def test_report_overall_coverage_logged_as_na_when_no_metric_weight(mocker: MockerFixture, caplog):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    overall = Coverage(
        instruction=Counter(missed=0, covered=0),
        branch=Counter(missed=0, covered=0),
        line=Counter(missed=0, covered=0),
        complexity=Counter(missed=0, covered=0),
        method=Counter(missed=0, covered=0),
        clazz=Counter(missed=0, covered=0),
    )
    report = ReportFileCoverage(
        path="na_report.xml",
        name="na_report",
        overall_coverage=overall,
        changed_files_coverage={},
    )
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=0.0,
        report_thresholds_default=(80.0, 0.0, 0.0),
    )

    with caplog.at_level(logging.INFO, logger="jacoco_report.evaluator.coverage_evaluator"):
        evaluator.evaluate()

    messages = [r.message for r in caplog.records]
    assert "Report 'na_report' has no overall coverage data for selected metric; treated as passed." in messages
    assert not any("Report 'na_report' reached overall coverage" in m for m in messages)
    assert evaluator.evaluated_reports_coverage["na_report"].overall_passed is True


def test_report_changed_files_coverage_logged_as_na_when_no_metric_weight(mocker: MockerFixture, caplog):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="branch")
    overall = Coverage(
        instruction=Counter(missed=0, covered=10),
        branch=Counter(missed=0, covered=10),
        line=Counter(missed=0, covered=10),
        complexity=Counter(missed=0, covered=10),
        method=Counter(missed=0, covered=10),
        clazz=Counter(missed=0, covered=10),
    )
    changed_files = {
        "com/example/Foo.java": FileCoverage(
            file_name="Foo.java",
            file_path="com/example",
            instruction=Counter(missed=0, covered=10),
            branch=Counter(missed=0, covered=0),
            line=Counter(missed=0, covered=10),
            complexity=Counter(missed=0, covered=10),
            method=Counter(missed=0, covered=10),
            clazz=Counter(missed=0, covered=10),
        )
    }
    report = ReportFileCoverage(
        path="na_cf_report.xml",
        name="na_cf_report",
        overall_coverage=overall,
        changed_files_coverage=changed_files,
    )
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=0.0,
        report_thresholds_default=(0.0, 80.0, 0.0),
    )

    with caplog.at_level(logging.INFO, logger="jacoco_report.evaluator.coverage_evaluator"):
        evaluator.evaluate()

    messages = [r.message for r in caplog.records]
    assert "Report 'na_cf_report' has no changed-files coverage data for selected metric; treated as passed." in messages
    assert not any("Report 'na_cf_report' reached average changed files coverage" in m for m in messages)
    assert evaluator.evaluated_reports_coverage["na_cf_report"].avg_changed_files_passed is True


def test_report_changed_files_coverage_logged_for_changed_report(mocker: MockerFixture, caplog):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    report = _make_report_with_changed_file("atum_reader")
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=75.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=0.0,
        report_thresholds_default=(75.0, 82.0, 0.0),
    )
    with caplog.at_level(logging.INFO, logger="jacoco_report.evaluator.coverage_evaluator"):
        evaluator.evaluate()

    messages = [r.message for r in caplog.records]
    assert "Report 'atum_reader' reached overall coverage of 80.0% with threshold set to 75.0%" in messages
    assert "Report 'atum_reader' reached average changed files coverage of 90.0% with threshold set to 82.0%" in messages


def test_group_overall_coverage_logged(mocker: MockerFixture, caplog):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    report = _make_minimal_report("rep-a", "backend")
    group = ReportGroup(name="backend", paths=["**"], min_coverage_overall=70.0)
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=50.0,
        report_groups=[group],
    )
    with caplog.at_level(logging.INFO, logger="jacoco_report.evaluator.coverage_evaluator"):
        evaluator.evaluate()

    messages = [r.message for r in caplog.records]
    assert "Group 'backend' reached overall coverage of 100.0% with threshold set to 70.0%" in messages
    assert not any("Group 'backend' reached average changed files" in m for m in messages)


def test_group_changed_files_coverage_logged(mocker: MockerFixture, caplog):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    report = _make_report_with_changed_file("rep-b", "frontend")
    group = ReportGroup(
        name="frontend", paths=["**"],
        min_coverage_overall=60.0, min_coverage_changed_files=55.0,
    )
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=50.0,
        report_groups=[group],
    )
    with caplog.at_level(logging.INFO, logger="jacoco_report.evaluator.coverage_evaluator"):
        evaluator.evaluate()

    messages = [r.message for r in caplog.records]
    assert "Group 'frontend' reached overall coverage of 80.0% with threshold set to 60.0%" in messages
    assert "Group 'frontend' reached average changed files coverage of 90.0% with threshold set to 55.0%" in messages


def test_group_changed_files_coverage_logged_when_metric_has_zero_weight(
    mocker: MockerFixture,
    caplog,
):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="branch")
    overall = Coverage(
        instruction=Counter(missed=0, covered=10),
        branch=Counter(missed=0, covered=10),
        line=Counter(missed=0, covered=10),
        complexity=Counter(missed=0, covered=10),
        method=Counter(missed=0, covered=10),
        clazz=Counter(missed=0, covered=10),
    )
    changed_files = {
        "com/example/Foo.java": FileCoverage(
            file_name="Foo.java",
            file_path="com/example",
            instruction=Counter(missed=0, covered=10),
            branch=Counter(missed=0, covered=0),
            line=Counter(missed=0, covered=10),
            complexity=Counter(missed=0, covered=10),
            method=Counter(missed=0, covered=10),
            clazz=Counter(missed=0, covered=10),
        )
    }
    report = ReportFileCoverage(
        path="rep-c.xml",
        name="rep-c",
        overall_coverage=overall,
        changed_files_coverage=changed_files,
        group_name="frontend",
    )
    group = ReportGroup(
        name="frontend",
        paths=["**"],
        min_coverage_overall=60.0,
        min_coverage_changed_files=55.0,
    )
    evaluator = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=50.0,
        global_min_coverage_changed_files=50.0,
        global_min_coverage_changed_per_file=50.0,
        report_groups=[group],
    )
    with caplog.at_level(logging.INFO, logger="jacoco_report.evaluator.coverage_evaluator"):
        evaluator.evaluate()

    messages = [r.message for r in caplog.records]
    assert "Group 'frontend' has no changed-files coverage data for selected metric; treated as passed." in messages
    assert not any("Group 'frontend' reached average changed files coverage" in m for m in messages)
    assert evaluator.evaluated_groups_coverage["frontend"].avg_changed_files_passed is True
    assert not any("Group 'frontend' changed files coverage 0.0 is below the threshold 55.0." in v for v in evaluator.violations)


def _make_report_with_changed_file_instruction(
    report_name: str,
    changed_file_name: str,
    covered: int,
    missed: int,
) -> ReportFileCoverage:
    overall = Coverage(
        instruction=Counter(missed=0, covered=10),
        branch=Counter(missed=0, covered=10),
        line=Counter(missed=0, covered=10),
        complexity=Counter(missed=0, covered=10),
        method=Counter(missed=0, covered=10),
        clazz=Counter(missed=0, covered=10),
    )
    changed_files = {
        changed_file_name: FileCoverage(
            file_name=changed_file_name.split("/")[-1],
            file_path="/".join(changed_file_name.split("/")[:-1]),
            instruction=Counter(missed=missed, covered=covered),
            branch=Counter(missed=0, covered=10),
            line=Counter(missed=0, covered=10),
            complexity=Counter(missed=0, covered=10),
            method=Counter(missed=0, covered=10),
            clazz=Counter(missed=0, covered=10),
        )
    }
    return ReportFileCoverage(
        path=f"{report_name}.xml",
        name=report_name,
        overall_coverage=overall,
        changed_files_coverage=changed_files,
    )


def test_global_per_changed_file_threshold_passes_when_all_changed_files_meet_global_third(
    mocker: MockerFixture,
):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    report_a = _make_report_with_changed_file_instruction("report-a", "src/A.java", covered=8, missed=2)
    report_b = _make_report_with_changed_file_instruction("report-b", "src/B.java", covered=9, missed=1)

    evaluator = CoverageEvaluator(
        report_files_coverage=[report_a, report_b],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=75.0,
        report_thresholds_default=(0.0, 0.0, 0.0),
    )

    evaluator.evaluate()

    assert evaluator.reached_threshold_per_change_file is True
    assert not any("Global changed file" in violation for violation in evaluator.violations)


def test_global_per_changed_file_threshold_fails_when_any_changed_file_below_global_third(
    mocker: MockerFixture,
):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    report_a = _make_report_with_changed_file_instruction("report-a", "src/A.java", covered=8, missed=2)
    report_b = _make_report_with_changed_file_instruction("report-b", "src/B.java", covered=7, missed=3)

    evaluator = CoverageEvaluator(
        report_files_coverage=[report_a, report_b],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=75.0,
        report_thresholds_default=(0.0, 0.0, 0.0),
    )

    evaluator.evaluate()

    assert evaluator.reached_threshold_per_change_file is False
    assert any("Global changed file" in violation for violation in evaluator.violations)


# ---------------------------------------------------------------------------
# G4a  Duplicate report name triggers evaluator warning
# ---------------------------------------------------------------------------

def test_duplicate_report_name_emits_warning(make_report_file_coverage, mocker, caplog):
    """Evaluator logs a WARNING when two reports share the same name (title)."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    report_a = make_report_file_coverage(name="same-name")
    report_b = make_report_file_coverage(name="same-name")

    evaluator = CoverageEvaluator(
        report_files_coverage=[report_a, report_b],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=0.0,
    )

    with caplog.at_level(logging.WARNING, logger="jacoco_report.evaluator.coverage_evaluator"):
        evaluator.evaluate()

    assert "Duplicate report name 'same-name' detected" in caplog.text


# ---------------------------------------------------------------------------
# G5  Baseline has no effect on threshold evaluation
# ---------------------------------------------------------------------------

def test_baseline_does_not_affect_threshold_evaluation(make_report_file_coverage, make_coverage, mocker):
    """High-coverage baseline does not cause a low-coverage current report to pass thresholds."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")

    low_cov = make_coverage(instruction=Counter(missed=10, covered=0))
    high_cov = make_coverage(instruction=Counter(missed=0, covered=10))

    current_report = make_report_file_coverage(name="mod", overall_coverage=low_cov)
    baseline_report = make_report_file_coverage(name="mod", overall_coverage=high_cov)

    evaluator = CoverageEvaluator(
        report_files_coverage=[current_report],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=0.0,
    )
    evaluator.evaluate()

    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[baseline_report],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=0.0,
    )
    bs_evaluator.evaluate()

    assert evaluator.total_coverage_overall == 0.0
    assert evaluator.total_coverage_overall_passed is False
    assert any("Global overall coverage 0.0 is below the threshold 80.0" in v for v in evaluator.violations)
    assert bs_evaluator.total_coverage_overall == 100.0
    assert bs_evaluator.total_coverage_overall_passed is True


def test_low_baseline_does_not_cause_high_coverage_to_fail(make_report_file_coverage, make_coverage, mocker):
    """Low-coverage baseline does not drag down a passing current report."""
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")

    high_cov = make_coverage(instruction=Counter(missed=0, covered=10))
    low_cov = make_coverage(instruction=Counter(missed=9, covered=1))

    current_report = make_report_file_coverage(name="mod", overall_coverage=high_cov)
    baseline_report = make_report_file_coverage(name="mod", overall_coverage=low_cov)

    evaluator = CoverageEvaluator(
        report_files_coverage=[current_report],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=0.0,
    )
    evaluator.evaluate()

    bs_evaluator = CoverageEvaluator(
        report_files_coverage=[baseline_report],
        global_min_coverage_overall=0.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=0.0,
    )
    bs_evaluator.evaluate()

    assert evaluator.total_coverage_overall == 100.0
    assert evaluator.total_coverage_overall_passed is True
    assert evaluator.violations == []


# ---------------------------------------------------------------------------
# G11  Selected metric affects threshold comparison, not just display
# ---------------------------------------------------------------------------

def test_metric_instruction_passes_when_line_would_fail(mocker):
    """Instruction coverage passes an 80% threshold; line coverage (0%) would fail the same threshold."""
    report = ReportFileCoverage(
        path="test.xml",
        name="test-mod",
        overall_coverage=Coverage(
            instruction=Counter(missed=0, covered=10),
            branch=Counter(missed=0, covered=10),
            line=Counter(missed=10, covered=0),
            complexity=Counter(missed=0, covered=10),
            method=Counter(missed=0, covered=10),
            clazz=Counter(missed=0, covered=10),
        ),
        changed_files_coverage={},
    )

    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="instruction")
    ev_instr = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=0.0,
    )
    ev_instr.evaluate()
    assert ev_instr.total_coverage_overall_passed is True
    assert ev_instr.total_coverage_overall == 100.0


def test_metric_line_fails_when_instruction_would_pass(mocker):
    """Line coverage (0%) fails an 80% threshold even though instruction coverage is 100%."""
    report = ReportFileCoverage(
        path="test.xml",
        name="test-mod",
        overall_coverage=Coverage(
            instruction=Counter(missed=0, covered=10),
            branch=Counter(missed=0, covered=10),
            line=Counter(missed=10, covered=0),
            complexity=Counter(missed=0, covered=10),
            method=Counter(missed=0, covered=10),
            clazz=Counter(missed=0, covered=10),
        ),
        changed_files_coverage={},
    )

    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_metric", return_value="line")
    ev_line = CoverageEvaluator(
        report_files_coverage=[report],
        global_min_coverage_overall=80.0,
        global_min_coverage_changed_files=0.0,
        global_min_coverage_changed_per_file=0.0,
    )
    ev_line.evaluate()
    assert ev_line.total_coverage_overall_passed is False
    assert ev_line.total_coverage_overall == 0.0