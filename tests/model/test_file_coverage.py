import pytest

from jacoco_report.model.file_coverage import FileCoverage
from jacoco_report.model.counter import Counter


@pytest.fixture
def file_coverage():
    instruction = Counter(missed=5, covered=10)
    branch = Counter(missed=3, covered=7)
    line = Counter(missed=2, covered=8)
    complexity = Counter(missed=1, covered=9)
    method = Counter(missed=4, covered=6)
    clazz = Counter(missed=0, covered=5)
    return FileCoverage(
        file_name="test_file.py",
        file_path="src/test_file.py",
        instruction=instruction,
        branch=branch,
        line=line,
        complexity=complexity,
        method=method,
        clazz=clazz
    )


# __init__

def test_initialization():
    instruction = Counter(missed=5, covered=10)
    branch = Counter(missed=3, covered=7)
    line = Counter(missed=2, covered=8)
    complexity = Counter(missed=1, covered=9)
    method = Counter(missed=4, covered=6)
    clazz = Counter(missed=0, covered=5)

    file_coverage = FileCoverage(
        file_name="file_name",
        file_path="file_path",
        instruction=instruction,
        branch=branch,
        line=line,
        complexity=complexity,
        method=method,
        clazz=clazz
    )

    assert file_coverage.file_name == "file_name"
    assert file_coverage.file_path == "file_path"
    assert file_coverage.instruction == instruction
    assert file_coverage.branch == branch
    assert file_coverage.line == line
    assert file_coverage.complexity == complexity
    assert file_coverage.method == method
    assert file_coverage.clazz == clazz


def test_str(file_coverage):
    expected_str = (
        "File: test_file.py, Path: src/test_file.py, "
        "Instruction: Missed: 5, Covered: 10, Branch: Missed: 3, Covered: 7, "
        "Line: Missed: 2, Covered: 8, Complexity: Missed: 1, Covered: 9, "
        "Method: Missed: 4, Covered: 6, Class: Missed: 0, Covered: 5"
    )
    assert str(file_coverage) == expected_str