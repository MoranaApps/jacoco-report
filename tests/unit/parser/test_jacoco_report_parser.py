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


def _write_util_sources(root):
    """Writes com/x/Util.java into module-a and module-b, both under the workspace root."""
    for module in ("module-a", "module-b"):
        source = root / module / "src" / "main" / "java" / "com" / "x" / "Util.java"
        source.parent.mkdir(parents=True)
        source.write_text("class Util {}")


_MODULE_A_UTIL = "module-a/src/main/java/com/x/Util.java"
_MODULE_B_UTIL = "module-b/src/main/java/com/x/Util.java"


def test_module_report_without_its_changed_source_drops_the_other_modules_match(tmp_path, monkeypatch):
    _write_util_sources(tmp_path)
    monkeypatch.chdir(tmp_path)
    parser_for_b = JaCoCoReportParser(changed_files=[_MODULE_B_UTIL])
    report = tmp_path / "module-a" / "target" / "site" / "jacoco" / "jacoco.xml"
    report.parent.mkdir(parents=True)
    report_path = _write_report(report, [("com/x", "Util.java")])

    report_coverage = parser_for_b.parse(report_path)

    assert report_coverage.changed_files_coverage == {}


def test_module_report_keeps_only_its_own_changed_source(tmp_path, monkeypatch):
    _write_util_sources(tmp_path)
    monkeypatch.chdir(tmp_path)
    parser_for_b = JaCoCoReportParser(changed_files=[_MODULE_B_UTIL])
    report = tmp_path / "module-b" / "target" / "site" / "jacoco" / "jacoco.xml"
    report.parent.mkdir(parents=True)
    report_path = _write_report(report, [("com/x", "Util.java")])

    report_coverage = parser_for_b.parse(report_path)

    assert list(report_coverage.changed_files_coverage) == [_MODULE_B_UTIL]


def test_each_module_report_keeps_only_its_own_key_when_both_sources_changed(tmp_path, monkeypatch):
    _write_util_sources(tmp_path)
    monkeypatch.chdir(tmp_path)
    both_changed = JaCoCoReportParser(changed_files=[_MODULE_A_UTIL, _MODULE_B_UTIL])
    for module in ("module-a", "module-b"):
        (tmp_path / module / "target" / "site" / "jacoco").mkdir(parents=True)
    report_a = _write_report(
        tmp_path / "module-a" / "target" / "site" / "jacoco" / "jacoco.xml", [("com/x", "Util.java")]
    )
    report_b = _write_report(
        tmp_path / "module-b" / "target" / "site" / "jacoco" / "jacoco.xml", [("com/x", "Util.java")]
    )

    assert list(both_changed.parse(report_a).changed_files_coverage) == [_MODULE_A_UTIL]
    assert list(both_changed.parse(report_b).changed_files_coverage) == [_MODULE_B_UTIL]


def test_gradle_build_report_keeps_only_its_own_module_source(tmp_path, monkeypatch):
    _write_util_sources(tmp_path)
    monkeypatch.chdir(tmp_path)
    both_changed = JaCoCoReportParser(changed_files=[_MODULE_A_UTIL, _MODULE_B_UTIL])
    report = tmp_path / "module-b" / "build" / "reports" / "jacoco" / "test" / "x.xml"
    report.parent.mkdir(parents=True)
    report_path = _write_report(report, [("com/x", "Util.java")])

    report_coverage = both_changed.parse(report_path)

    assert list(report_coverage.changed_files_coverage) == [_MODULE_B_UTIL]


def test_nested_module_report_keeps_only_sources_under_its_module_directory(tmp_path, monkeypatch):
    for module in ("parent/module-a", "parent/module-b"):
        source = tmp_path / module / "src" / "main" / "java" / "com" / "x" / "Util.java"
        source.parent.mkdir(parents=True)
        source.write_text("class Util {}")
    monkeypatch.chdir(tmp_path)
    changed = ["parent/module-a/src/main/java/com/x/Util.java", "parent/module-b/src/main/java/com/x/Util.java"]
    parser_for_a = JaCoCoReportParser(changed_files=changed)
    report = tmp_path / "parent" / "module-a" / "target" / "site" / "jacoco" / "jacoco.xml"
    report.parent.mkdir(parents=True)
    report_path = _write_report(report, [("com/x", "Util.java")])

    report_coverage = parser_for_a.parse(report_path)

    assert list(report_coverage.changed_files_coverage) == ["parent/module-a/src/main/java/com/x/Util.java"]


def test_aggregate_report_without_a_match_under_its_directory_keeps_all_matches(tmp_path, monkeypatch):
    _write_util_sources(tmp_path)
    monkeypatch.chdir(tmp_path)
    both_changed = JaCoCoReportParser(changed_files=[_MODULE_A_UTIL, _MODULE_B_UTIL])
    report = tmp_path / "aggregate" / "target" / "site" / "jacoco-aggregate" / "jacoco.xml"
    report.parent.mkdir(parents=True)
    report_path = _write_report(report, [("com/x", "Util.java")])

    report_coverage = both_changed.parse(report_path)

    assert sorted(report_coverage.changed_files_coverage) == [_MODULE_A_UTIL, _MODULE_B_UTIL]


def test_report_without_target_or_build_segment_keeps_all_matches(tmp_path, monkeypatch):
    _write_util_sources(tmp_path)
    monkeypatch.chdir(tmp_path)
    both_changed = JaCoCoReportParser(changed_files=[_MODULE_A_UTIL, _MODULE_B_UTIL])
    report_path = _write_report(tmp_path / "jacoco.xml", [("com/x", "Util.java")])

    report_coverage = both_changed.parse(report_path)

    assert sorted(report_coverage.changed_files_coverage) == [_MODULE_A_UTIL, _MODULE_B_UTIL]


def test_report_outside_the_workspace_keeps_all_matches(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    _write_util_sources(workspace)
    monkeypatch.chdir(workspace)
    both_changed = JaCoCoReportParser(changed_files=[_MODULE_A_UTIL, _MODULE_B_UTIL])
    report = tmp_path / "elsewhere" / "module-a" / "target" / "jacoco.xml"
    report.parent.mkdir(parents=True)
    report_path = _write_report(report, [("com/x", "Util.java")])

    report_coverage = both_changed.parse(report_path)

    assert sorted(report_coverage.changed_files_coverage) == [_MODULE_A_UTIL, _MODULE_B_UTIL]


def test_report_under_target_at_the_workspace_root_keeps_all_matches(tmp_path, monkeypatch):
    _write_util_sources(tmp_path)
    monkeypatch.chdir(tmp_path)
    both_changed = JaCoCoReportParser(changed_files=[_MODULE_A_UTIL, _MODULE_B_UTIL])
    report = tmp_path / "target" / "site" / "jacoco" / "jacoco.xml"
    report.parent.mkdir(parents=True)
    report_path = _write_report(report, [("com/x", "Util.java")])

    report_coverage = both_changed.parse(report_path)

    assert sorted(report_coverage.changed_files_coverage) == [_MODULE_A_UTIL, _MODULE_B_UTIL]
