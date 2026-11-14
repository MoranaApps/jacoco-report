import logging

import pytest

from jacoco_report.parser.jacoco_report_parser import JaCoCoReportParser
from jacoco_report.model.counter import Counter
from jacoco_report.model.report_file_coverage import ReportFileCoverage


@pytest.fixture
def sample_jacoco_report(tmp_path):
    report_content = """
    <report name="Example Report Name">
        <package name="com/example">
            <sourcefile name="Example.java">
                <counter type="INSTRUCTION" missed="1" covered="9"/>
                <counter type="BRANCH" missed="0" covered="7"/>
                <counter type="LINE" missed="2" covered="8"/>
                <counter type="COMPLEXITY" missed="1" covered="9"/>
                <counter type="METHOD" missed="4" covered="6"/>
                <counter type="CLASS" missed="0" covered="5"/>
            </sourcefile>
        </package>
        <counter type="INSTRUCTION" missed="5" covered="10"/>
        <counter type="BRANCH" missed="3" covered="7"/>
        <counter type="LINE" missed="2" covered="8"/>
        <counter type="COMPLEXITY" missed="1" covered="9"/>
        <counter type="METHOD" missed="4" covered="6"/>
        <counter type="CLASS" missed="0" covered="5"/>
    </report>
    """
    report_path = tmp_path / "jacoco_report.xml"
    report_path.write_text(report_content)
    return str(report_path)


@pytest.fixture
def parser():
    return JaCoCoReportParser(changed_files=["com/example/Example.java"])


def test_parse_overall_stats(parser, sample_jacoco_report):
    report_coverage = parser.parse(report_path := sample_jacoco_report)
    assert isinstance(report_coverage, ReportFileCoverage)
    assert report_coverage.path == report_path
    assert report_coverage.name == "Example Report Name"
    assert report_coverage.overall_coverage.instruction == Counter(missed=5, covered=10)
    assert report_coverage.overall_coverage.branch == Counter(missed=3, covered=7)
    assert report_coverage.overall_coverage.line == Counter(missed=2, covered=8)
    assert report_coverage.overall_coverage.complexity == Counter(missed=1, covered=9)
    assert report_coverage.overall_coverage.method == Counter(missed=4, covered=6)
    assert report_coverage.overall_coverage.clazz == Counter(missed=0, covered=5)


def test_parse_overall_stats_with_group_name(parser, sample_jacoco_report):
    report_coverage = parser.parse(report_path := sample_jacoco_report, group_name="my-group")
    assert isinstance(report_coverage, ReportFileCoverage)
    assert report_coverage.path == report_path
    assert report_coverage.name == "Example Report Name"
    assert report_coverage.group_name == "my-group"
    assert report_coverage.overall_coverage.instruction == Counter(missed=5, covered=10)
    assert report_coverage.overall_coverage.branch == Counter(missed=3, covered=7)
    assert report_coverage.overall_coverage.line == Counter(missed=2, covered=8)
    assert report_coverage.overall_coverage.complexity == Counter(missed=1, covered=9)
    assert report_coverage.overall_coverage.method == Counter(missed=4, covered=6)
    assert report_coverage.overall_coverage.clazz == Counter(missed=0, covered=5)


def test_parse_changed_files_stats(parser, sample_jacoco_report):
    report_coverage = parser.parse(sample_jacoco_report)
    assert "com/example/Example.java" in report_coverage.changed_files_coverage
    file_coverage = report_coverage.changed_files_coverage["com/example/Example.java"]
    assert file_coverage.instruction == Counter(missed=1, covered=9)
    assert file_coverage.branch == Counter(missed=0, covered=7)
    assert file_coverage.line == Counter(missed=2, covered=8)
    assert file_coverage.complexity == Counter(missed=1, covered=9)
    assert file_coverage.method == Counter(missed=4, covered=6)
    assert file_coverage.clazz == Counter(missed=0, covered=5)


_GROUPED_PACKAGE = """
<package name="com/example">
    <sourcefile name="Example.java">
        <counter type="INSTRUCTION" missed="3" covered="17"/>
        <counter type="BRANCH" missed="1" covered="5"/>
        <counter type="LINE" missed="4" covered="12"/>
        <counter type="COMPLEXITY" missed="2" covered="6"/>
        <counter type="METHOD" missed="1" covered="3"/>
        <counter type="CLASS" missed="0" covered="1"/>
    </sourcefile>
</package>
"""


@pytest.mark.parametrize(
    "report_body",
    [
        pytest.param(f'<group name="module-a">{_GROUPED_PACKAGE}</group>', id="one-group-level"),
        pytest.param(
            f'<group name="app"><group name="module-a">{_GROUPED_PACKAGE}</group></group>', id="two-nested-group-levels"
        ),
    ],
)
def test_parse_changed_files_stats_finds_packages_inside_groups(parser, tmp_path, report_body):
    report_path = tmp_path / "jacoco.xml"
    report_path.write_text(f'<report name="Aggregate Report">{report_body}</report>')

    report_coverage = parser.parse(str(report_path))

    assert list(report_coverage.changed_files_coverage) == ["com/example/Example.java"]
    file_coverage = report_coverage.changed_files_coverage["com/example/Example.java"]
    assert file_coverage.instruction == Counter(missed=3, covered=17)
    assert file_coverage.branch == Counter(missed=1, covered=5)
    assert file_coverage.line == Counter(missed=4, covered=12)
    assert file_coverage.complexity == Counter(missed=2, covered=6)
    assert file_coverage.method == Counter(missed=1, covered=3)
    assert file_coverage.clazz == Counter(missed=0, covered=1)


def test_file_not_in_changed_files(sample_jacoco_report, caplog):
    non_matching_parser = JaCoCoReportParser(changed_files=["com/example/NonExistent.java"])

    with caplog.at_level(logging.DEBUG):
        non_matching_parser.parse(sample_jacoco_report)

    assert "File 'com/example/Example.java' is not in the list of changed files." in caplog.text


def test_parse_counter_value_error_invalid(parser, sample_jacoco_report, caplog):
    # Modify the report to include an invalid counter value
    invalid_report_content = """
    <report name="Example Report Name">
        <package name="com/example">
            <sourcefile name="Example.java">
                <counter type="INSTRUCTION" missed="invalid" covered="9"/>
                <counter type="BRANCH" missed="0" covered="7"/>
                <counter type="LINE" missed="2" covered="8"/>
                <counter type="COMPLEXITY" missed="1" covered="9"/>
                <counter type="METHOD" missed="4" covered="6"/>
                <counter type="CLASS" missed="0" covered="5"/>
            </sourcefile>
        </package>
        <counter type="INSTRUCTION" missed="5" covered="10"/>
        <counter type="BRANCH" missed="3" covered="7"/>
        <counter type="LINE" missed="2" covered="8"/>
        <counter type="COMPLEXITY" missed="1" covered="9"/>
        <counter type="METHOD" missed="4" covered="6"/>
        <counter type="CLASS" missed="0" covered="5"/>
    </report>
    """
    report_path = sample_jacoco_report
    with open(report_path, "w") as f:
        f.write(invalid_report_content)

    with caplog.at_level(logging.ERROR):
        report_coverage = parser.parse(report_path)

    assert "Failed to parse INSTRUCTION counter from JaCoCo report." in caplog.text


def test_parse_counter_value_error_missing(parser, sample_jacoco_report, caplog):
    # Modify the report to include an invalid counter value
    invalid_report_content = """
    <report name="Example Report Name">
        <package name="com/example">
            <sourcefile name="Example.java">
                <counter type="INSTRUCTION" covered="9"/>
                <counter type="BRANCH" missed="0" covered="7"/>
                <counter type="LINE" missed="2" covered="8"/>
                <counter type="COMPLEXITY" missed="1" covered="9"/>
                <counter type="METHOD" missed="4" covered="6"/>
                <counter type="CLASS" missed="0" covered="5"/>
            </sourcefile>
        </package>
        <counter type="INSTRUCTION" missed="5" covered="10"/>
        <counter type="BRANCH" missed="3" covered="7"/>
        <counter type="LINE" missed="2" covered="8"/>
        <counter type="COMPLEXITY" missed="1" covered="9"/>
        <counter type="METHOD" missed="4" covered="6"/>
        <counter type="CLASS" missed="0" covered="5"/>
    </report>
    """

    report_path = sample_jacoco_report
    with open(report_path, "w") as f:
        f.write(invalid_report_content)

    with caplog.at_level(logging.ERROR):
        report_coverage = parser.parse(report_path)

    assert "Failed to find INSTRUCTION counter in JaCoCo report." in caplog.text
