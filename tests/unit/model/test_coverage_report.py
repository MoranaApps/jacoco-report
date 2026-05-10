from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.model.coverage import Coverage
from jacoco_report.model.file_coverage import FileCoverage
from jacoco_report.model.counter import Counter

# __init__

def test_initialization():
    instruction = Counter(missed=5, covered=10)
    branch = Counter(missed=3, covered=7)
    line = Counter(missed=2, covered=8)
    complexity = Counter(missed=1, covered=9)
    method = Counter(missed=4, covered=6)
    clazz = Counter(missed=0, covered=5)

    overall_coverage = Coverage(instruction, branch, line, complexity, method, clazz)
    changed_files_coverage = {
        "file1": FileCoverage(
            "file_name1", "file_path1",
            instruction, branch, line, complexity, method, clazz),
        "file2": FileCoverage(
            "file_name2", "file_path2",
            instruction, branch, line, complexity, method, clazz)
    }

    coverage_report = ReportFileCoverage(
        path="path/to/report",
        name="Report title",
        overall_coverage=overall_coverage,
        changed_files_coverage=changed_files_coverage)

    assert coverage_report.path == "path/to/report"
    assert coverage_report.module_name == "Unknown"
    assert coverage_report.overall_coverage == overall_coverage
    assert coverage_report.changed_files_coverage == changed_files_coverage