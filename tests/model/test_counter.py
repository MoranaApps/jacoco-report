import pytest
from jacoco_report.model.counter import Counter

# __init__

def test_initialization():
    counter = Counter(missed=5, covered=10)
    assert counter.missed == 5
    assert counter.covered == 10

# coverage

def test_coverage():
    counter = Counter(missed=5, covered=10)
    assert counter.coverage() == pytest.approx(66.67)

def test_coverage_zero_covered():
    counter = Counter(missed=5, covered=0)
    assert counter.coverage() == 0.0

def test_coverage_zero_missed():
    counter = Counter(missed=0, covered=10)
    assert counter.coverage() == 100.0

def test_coverage_zero_total():
    counter = Counter(missed=0, covered=0)
    assert counter.coverage() == 0.0


# append

def test_append():
    counter = Counter(missed=5, covered=10)
    counter.append(missed=3, covered=7)
    assert counter.missed == 8
    assert counter.covered == 17

# __str__

def test_str():
    counter = Counter(missed=5, covered=10)
    assert str(counter) == "Missed: 5, Covered: 10"