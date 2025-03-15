import pytest

from jacoco_report.model.counter import Counter
from jacoco_report.model.coverage import Coverage
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.model.file_coverage import FileCoverage
from jacoco_report.model.report_file_coverage import ReportFileCoverage

@pytest.fixture
def report_coverage_file():
    # Provide the required constructor inputs for ReportFileCoverage
    return ReportFileCoverage(
        path="example_path",
        overall_coverage=Coverage(
            instruction=Counter(missed=5, covered=10),
            branch=Counter(missed=3, covered=7),
            line=Counter(missed=2, covered=8),
            complexity=Counter(missed=1, covered=9),
            method=Counter(missed=4, covered=6),
            clazz=Counter(missed=0, covered=5)
        ),
        changed_files_coverage={
            "example_file.py": FileCoverage(
                file_name="example_file.py",
                file_path="example_path/example_file.py",
                instruction=Counter(missed=1, covered=9),
                branch=Counter(missed=0, covered=7),
                line=Counter(missed=2, covered=8),
                complexity=Counter(missed=1, covered=9),
                method=Counter(missed=4, covered=6),
                clazz=Counter(missed=0, covered=5)
            )
        }
    )

# @pytest.fixture
# def evaluated_coverage_report(report_coverage_file):
#     return EvaluatedCoverage(report_coverage_file)

# def test_initialization(evaluated_coverage_report, report_coverage_file):
#     # TODO - napis testy znova - doslo k velkym zmenam
#     assert evaluated_coverage_report.overall_passed == False
#     assert evaluated_coverage_report.overall_coverage_reached == 0.0
#     assert evaluated_coverage_report.changed_files_passed == {}
#     assert evaluated_coverage_report.changed_files_coverage_reached == {}
#     assert evaluated_coverage_report.sum_changed_files_passed == False
#     assert evaluated_coverage_report.sum_changed_files_coverage_reached == 0.0
