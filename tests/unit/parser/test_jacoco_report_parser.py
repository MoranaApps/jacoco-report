import logging
import os
import time

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


@pytest.mark.parametrize(
    "changed_file, is_match",
    [
        pytest.param("com/example/Example.java", True, id="same-path"),
        pytest.param("src/main/java/com/example/Example.java", True, id="suffix-on-directory-boundary"),
        pytest.param("src/xcom/example/Example.java", False, id="suffix-inside-directory-name"),
        pytest.param("src/main/java/com/example/Example.javax", False, id="prefix-of-file-name"),
    ],
)
def test_changed_file_matches_on_directory_boundary(
    sample_jacoco_report, tmp_path, monkeypatch, changed_file, is_match
):
    monkeypatch.chdir(tmp_path)  # no source on disk, so the key is the report path "com/example/Example.java"
    boundary_parser = JaCoCoReportParser(changed_files=[changed_file])

    report_coverage = boundary_parser.parse(sample_jacoco_report)

    assert ("com/example/Example.java" in report_coverage.changed_files_coverage) is is_match


def test_changed_file_in_default_package_matches(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no source on disk, so the key comes from the report alone
    report_path = tmp_path / "jacoco.xml"
    report_path.write_text(
        '<report name="Default Package Report"><package name="">'
        '<sourcefile name="Example.java"><counter type="LINE" missed="1" covered="3"/></sourcefile>'
        "</package></report>"
    )
    default_package_parser = JaCoCoReportParser(changed_files=["src/main/java/Example.java"])

    report_coverage = default_package_parser.parse(str(report_path))

    assert list(report_coverage.changed_files_coverage) == ["Example.java"]
    assert report_coverage.changed_files_coverage["Example.java"].line == Counter(missed=1, covered=3)


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


def _write_report(path, packages):
    """Writes a JaCoCo report with one <package> per (package name, source file name) pair."""
    body = "".join(
        f'<package name="{package}"><sourcefile name="{file_name}">'
        '<counter type="LINE" missed="1" covered="3"/></sourcefile></package>'
        for package, file_name in packages
    )
    path.write_text(f'<report name="Index Report">{body}</report>')
    return str(path)


def test_source_file_in_module_subdirectory_is_keyed_by_workspace_path(tmp_path, monkeypatch):
    source = tmp_path / "module-a" / "src" / "main" / "java" / "com" / "example" / "Example.java"
    source.parent.mkdir(parents=True)
    source.write_text("class Example {}")
    monkeypatch.chdir(tmp_path)
    module_parser = JaCoCoReportParser(changed_files=["module-a/src/main/java/com/example/Example.java"])
    report = _write_report(tmp_path / "jacoco.xml", [("com/example", "Example.java")])

    report_coverage = module_parser.parse(report)

    assert list(report_coverage.changed_files_coverage) == ["module-a/src/main/java/com/example/Example.java"]


def test_default_package_source_file_on_disk_is_keyed_by_workspace_path(tmp_path, monkeypatch):
    source = tmp_path / "src" / "main" / "java" / "Example.java"
    source.parent.mkdir(parents=True)
    source.write_text("class Example {}")
    monkeypatch.chdir(tmp_path)
    default_package_parser = JaCoCoReportParser(changed_files=["src/main/java/Example.java"])
    report = _write_report(tmp_path / "jacoco.xml", [("", "Example.java")])

    report_coverage = default_package_parser.parse(report)

    assert list(report_coverage.changed_files_coverage) == ["src/main/java/Example.java"]


def test_source_file_matching_only_inside_a_directory_name_is_not_found(tmp_path, monkeypatch):
    source = tmp_path / "src" / "xcom" / "example" / "Example.java"
    source.parent.mkdir(parents=True)
    source.write_text("class Example {}")
    monkeypatch.chdir(tmp_path)
    boundary_parser = JaCoCoReportParser(changed_files=["src/xcom/example/Example.java"])
    report = _write_report(tmp_path / "jacoco.xml", [("com/example", "Example.java")])

    report_coverage = boundary_parser.parse(report)

    assert report_coverage.changed_files_coverage == {}


def test_source_file_under_git_directory_is_not_found(tmp_path, monkeypatch):
    source = tmp_path / ".git" / "com" / "example" / "Example.java"
    source.parent.mkdir(parents=True)
    source.write_text("class Example {}")
    monkeypatch.chdir(tmp_path)
    git_parser = JaCoCoReportParser(changed_files=[".git/com/example/Example.java"])
    report = _write_report(tmp_path / "jacoco.xml", [("com/example", "Example.java")])

    report_coverage = git_parser.parse(report)

    assert list(report_coverage.changed_files_coverage) == ["com/example/Example.java"]


def test_workspace_is_walked_once_for_all_reports_of_a_parser(tmp_path, monkeypatch, mocker):
    (tmp_path / "com" / "example").mkdir(parents=True)
    (tmp_path / "com" / "example" / "Example.java").write_text("class Example {}")
    monkeypatch.chdir(tmp_path)
    shared_parser = JaCoCoReportParser(changed_files=["com/example/Example.java"])
    report = _write_report(tmp_path / "jacoco.xml", [("com/example", "Example.java")])
    walk_spy = mocker.spy(os, "walk")

    shared_parser.parse(report)
    shared_parser.parse(report, group_name="baseline")
    shared_parser.parse(report)

    assert walk_spy.call_count == 1


def test_parse_with_2000_directories_and_200_source_files_is_fast(tmp_path, monkeypatch):
    module_names = [f"m{i:03d}" for i in range(200)]
    for module in module_names:
        (tmp_path / module / "com" / "example").mkdir(parents=True)
    for index, module in enumerate(module_names):
        (tmp_path / module / "com" / "example" / f"File{index:03d}.java").write_text("class File {}")
    for extra in range(1400):
        (tmp_path / f"extra{extra:04d}").mkdir()
    monkeypatch.chdir(tmp_path)
    changed = [f"{module}/com/example/File{index:03d}.java" for index, module in enumerate(module_names)]
    perf_parser = JaCoCoReportParser(changed_files=changed)
    report = _write_report(
        tmp_path / "jacoco.xml",
        [(f"{module}/com/example", f"File{index:03d}.java") for index, module in enumerate(module_names)],
    )

    started = time.perf_counter()
    report_coverage = perf_parser.parse(report)
    elapsed = time.perf_counter() - started

    assert len(report_coverage.changed_files_coverage) == 200
    assert elapsed < 1.0, f"parse took {elapsed:.2f}s"
