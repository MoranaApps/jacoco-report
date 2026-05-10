import pytest

from jacoco_report.model.coverage import Coverage
from jacoco_report.model.counter import Counter
from jacoco_report.utils.enums import MetricTypeEnum


@pytest.fixture
def coverage():
    instruction = Counter(missed=5, covered=10)
    branch = Counter(missed=3, covered=7)
    line = Counter(missed=2, covered=8)
    complexity = Counter(missed=1, covered=9)
    method = Counter(missed=4, covered=6)
    clazz = Counter(missed=0, covered=5)
    return Coverage(instruction, branch, line, complexity, method, clazz)


# __init__

def test_initialization():
    instruction = Counter(missed=5, covered=10)
    branch = Counter(missed=3, covered=7)
    line = Counter(missed=2, covered=8)
    complexity = Counter(missed=1, covered=9)
    method = Counter(missed=4, covered=6)
    clazz = Counter(missed=0, covered=5)

    coverage = Coverage(instruction, branch, line, complexity, method, clazz)

    assert coverage.instruction == instruction
    assert coverage.branch == branch
    assert coverage.line == line
    assert coverage.complexity == complexity
    assert coverage.method == method
    assert coverage.clazz == clazz


def test_get_coverage_by_metric(coverage, mocker):
    mock_logger = mocker.patch('jacoco_report.model.coverage.logger')
    assert coverage.get_coverage_by_metric(MetricTypeEnum.INSTRUCTION) == round(10 / 15 * 100, 2)
    assert coverage.get_coverage_by_metric(MetricTypeEnum.BRANCH) == round(7 / 10 * 100, 2)
    assert coverage.get_coverage_by_metric(MetricTypeEnum.LINE) == round(8 / 10 * 100, 2)
    assert coverage.get_coverage_by_metric(MetricTypeEnum.COMPLEXITY) == round(9 / 10 * 100, 2)
    assert coverage.get_coverage_by_metric(MetricTypeEnum.METHOD) == round(6 / 10 * 100, 2)
    assert coverage.get_coverage_by_metric(MetricTypeEnum.CLASS) == round(5 / 5 * 100, 2)
    assert coverage.get_coverage_by_metric("unknown") == 0.0
    mock_logger.error.assert_called_once_with("Unknown metric type: %s", "unknown")

def test_get_values_by_metric(coverage, mocker):
    mock_logger = mocker.patch('jacoco_report.model.coverage.logger')
    assert coverage.get_values_by_metric(MetricTypeEnum.INSTRUCTION) == (5, 10)
    assert coverage.get_values_by_metric(MetricTypeEnum.BRANCH) == (3, 7)
    assert coverage.get_values_by_metric(MetricTypeEnum.LINE) == (2, 8)
    assert coverage.get_values_by_metric(MetricTypeEnum.COMPLEXITY) == (1, 9)
    assert coverage.get_values_by_metric(MetricTypeEnum.METHOD) == (4, 6)
    assert coverage.get_values_by_metric(MetricTypeEnum.CLASS) == (0, 5)
    assert coverage.get_values_by_metric("unknown") == (0, 0)
    mock_logger.error.assert_called_once_with("Unknown metric type: %s", "unknown")

def test_str(coverage):
    expected_str = (
        "Instruction: Missed: 5, Covered: 10, Branch: Missed: 3, Covered: 7, "
        "Line: Missed: 2, Covered: 8, Complexity: Missed: 1, Covered: 9, "
        "Method: Missed: 4, Covered: 6, Class: Missed: 0, Covered: 5"
    )
    assert str(coverage) == expected_str