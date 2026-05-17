import logging

from jacoco_report.scanner.jacoco_report_input_scanner import JaCoCoReportInputScanner

# __init__

def test_initialization():
    paths = ["path/to/reports"]
    exclude_paths = ["path/to/exclude"]
    scanner = JaCoCoReportInputScanner(paths, exclude_paths)

    assert scanner.paths == paths
    assert scanner.exclude_paths == exclude_paths


# scan

def test_scan_exact_paths_one_input(mocker):
    file_path_1 = "tests/data/test_project/module small/target/jacoco.xml"

    scanner = JaCoCoReportInputScanner(
        [file_path_1],
        [])

    result = scanner.scan()

    assert len(result) == 1
    assert file_path_1 in result[0]


def test_scan_exact_paths_more_inputs(mocker):
    file_path_1 = "tests/data/test_project/module small/target/jacoco.xml"
    file_path_2 = "tests/data/test_project/module_large/jacoco.xml"

    scanner = JaCoCoReportInputScanner(
        [file_path_1, file_path_2],
        [])

    result = scanner.scan()

    assert len(result) == 2
    assert any(file_path_1 in path for path in result), f"{file_path_1} not found in {result}"
    assert any(file_path_2 in path for path in result), f"{file_path_2} not found in {result}"


def test_scan_exact_paths_more_inputs_with_exclude(mocker):
    file_path_1 = "tests/data/test_project/module small/target/jacoco.xml"
    file_path_2 = "tests/data/test_project/module_large/target/jacoco.xml"

    scanner = JaCoCoReportInputScanner(
        [file_path_1, file_path_2],
        [file_path_2])

    result = scanner.scan()

    assert len(result) == 1
    file_path_1_detected = False
    file_path_2_detected = False
    for path in result:
        if file_path_1 in path:
            file_path_1_detected = True
        if file_path_2 in path:
            file_path_2_detected = True

    assert file_path_1_detected, f"{file_path_1} not found in {result}"
    assert not file_path_2_detected, f"{file_path_2} found in {result}"


def test_scan_blob_paths_no_exclude(mocker):
    blob_path = "tests/data/test_project/**/jacoco.xml"

    scanner = JaCoCoReportInputScanner(
        [blob_path],
        [])

    result = scanner.scan()

    assert len(result) == 9


def test_scan_blob_paths_with_exact_exclude(mocker):
    blob_path = "tests/data/test_project/**/jacoco.xml"
    ex_path = "tests/data/test_project/module_large/jacoco.xml"

    scanner = JaCoCoReportInputScanner(
        [blob_path],
        [ex_path])

    result = scanner.scan()

    assert len(result) == 8
    ex_path_detected = False
    for path in result:
        if ex_path in path:
            ex_path_detected = True

    assert not ex_path_detected, f"{ex_path} found in {result}"


def test_scan_blob_paths_with_blob_exclude(mocker):
    blob_path = "tests/data/test_project/**/jacoco.xml"
    ex_blob_path = "tests/data/test_project/module*/**/jacoco.xml"

    scanner = JaCoCoReportInputScanner(
        [blob_path],
        [ex_blob_path])

    result = scanner.scan()

    assert len(result) == 7
    file_path_1 = "test/data/test_project/module small/target/jacoco.xml"
    file_path_2 = "test/data/test_project/module_large/jacoco.xml"
    file_path_1_detected = False
    file_path_2_detected = False
    for path in result:
        if file_path_1 in path:
            file_path_1_detected = True
        if file_path_2 in path:
            file_path_2_detected = True

    assert not file_path_1_detected, f"{file_path_1} found in {result}"
    assert not file_path_2_detected, f"{file_path_2} found in {result}"


# ---------------------------------------------------------------------------
# G1 / G14  Scanner logs matched file paths at DEBUG level
# ---------------------------------------------------------------------------

def test_scanner_logs_matched_xml_file_at_debug_level(tmp_path, caplog):
    """Scanner emits a DEBUG log message containing the absolute path of each matched XML file."""
    xml_file = tmp_path / "jacoco.xml"
    xml_file.write_text("<report/>")

    with caplog.at_level(logging.DEBUG, logger="jacoco_report.scanner.jacoco_report_input_scanner"):
        JaCoCoReportInputScanner(paths=[str(xml_file)], exclude_paths=[]).scan()

    debug_msgs = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
    assert any("Found 'xml' file" in m for m in debug_msgs)
    assert any(str(xml_file) in m for m in debug_msgs)


def test_scanner_does_not_log_non_xml_files(tmp_path, caplog):
    """Scanner does not emit DEBUG messages for non-XML files."""
    txt_file = tmp_path / "report.txt"
    txt_file.write_text("not xml")

    with caplog.at_level(logging.DEBUG, logger="jacoco_report.scanner.jacoco_report_input_scanner"):
        JaCoCoReportInputScanner(paths=[str(txt_file)], exclude_paths=[]).scan()

    assert "Found 'xml' file" not in caplog.text


def test_scanner_logs_each_matched_file_separately(tmp_path, caplog):
    """One DEBUG message is emitted per matched XML file."""
    for i in range(3):
        (tmp_path / f"report_{i}.xml").write_text("<report/>")

    with caplog.at_level(logging.DEBUG, logger="jacoco_report.scanner.jacoco_report_input_scanner"):
        result = JaCoCoReportInputScanner(paths=[str(tmp_path / "*.xml")], exclude_paths=[]).scan()

    found_msgs = [r for r in caplog.records if r.levelno == logging.DEBUG and "Found 'xml' file" in r.message]
    assert len(found_msgs) == len(result)
