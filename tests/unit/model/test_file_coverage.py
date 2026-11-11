import pytest

from jacoco_report.model.file_coverage import FileCoverage
from jacoco_report.model.coverage import Coverage
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
        clazz=clazz,
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
        clazz=clazz,
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


# positional construction and equality


def _counters():
    return [
        Counter(missed=5, covered=10),
        Counter(missed=3, covered=7),
        Counter(missed=2, covered=8),
        Counter(missed=1, covered=9),
        Counter(missed=4, covered=6),
        Counter(missed=0, covered=5),
    ]


def test_positional_construction_assigns_fields_in_order():
    instruction, branch, line, complexity, method, clazz = _counters()

    file_coverage = FileCoverage("n", "p", instruction, branch, line, complexity, method, clazz)

    assert file_coverage.file_name == "n"
    assert file_coverage.file_path == "p"
    assert file_coverage.instruction == instruction
    assert file_coverage.branch == branch
    assert file_coverage.line == line
    assert file_coverage.complexity == complexity
    assert file_coverage.method == method
    assert file_coverage.clazz == clazz


def test_equal_when_all_fields_equal():
    assert FileCoverage("n", "p", *_counters()) == FileCoverage("n", "p", *_counters())


def test_not_equal_when_only_file_path_differs():
    assert FileCoverage("n", "p1", *_counters()) != FileCoverage("n", "p2", *_counters())


def test_not_equal_to_coverage_with_same_counters():
    assert FileCoverage("n", "p", *_counters()) != Coverage(*_counters())
