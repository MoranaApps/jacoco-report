import logging
import uuid

import pytest
from pytest_mock import MockerFixture

from jacoco_report.utils.gh_action import (
    append_step_summary,
    break_legacy_command_prefix,
    get_action_input,
    get_step_summary_path,
    print_action_warning,
    set_action_failed,
    set_action_output,
    set_action_output_text,
)

FIXED_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
FIXED_DELIMITER = f"ghadelimiter_{FIXED_UUID}"


@pytest.fixture
def fixed_delimiter(mocker: MockerFixture):
    mocker.patch("uuid.uuid4", return_value=FIXED_UUID)


# get_input


def test_get_input_with_hyphen(mocker: MockerFixture):
    mock_getenv = mocker.patch("os.getenv", return_value="test_value")

    result = get_action_input("test-input", default="")

    mock_getenv.assert_called_with("INPUT_TEST_INPUT", default="")
    assert "test_value" == result


def test_get_input_without_hyphen(mocker: MockerFixture):
    mock_getenv = mocker.patch("os.getenv", return_value="another_test_value")

    result = get_action_input("anotherinput", default="")

    mock_getenv.assert_called_with("INPUT_ANOTHERINPUT", default="")
    assert "another_test_value" == result


# set_output


def test_set_output_default(mocker: MockerFixture, fixed_delimiter):
    mocker.patch("os.getenv", return_value="default_output.txt")
    mock_open = mocker.patch("builtins.open", new_callable=mocker.mock_open)

    set_action_output("test-output", "test_value")

    mock_open.assert_called_with("default_output.txt", "a", encoding="utf-8")
    handle = mock_open()
    handle.write.assert_any_call(f"test-output<<{FIXED_DELIMITER}\n")
    handle.write.assert_any_call("test_value\n")
    handle.write.assert_any_call(f"{FIXED_DELIMITER}\n")


def test_set_output_custom_path(mocker: MockerFixture, fixed_delimiter):
    mocker.patch("os.getenv", return_value="custom_output.txt")
    mock_open = mocker.patch("builtins.open", new_callable=mocker.mock_open)

    set_action_output("custom-output", "custom_value", "default_output.txt")

    mock_open.assert_called_with("custom_output.txt", "a", encoding="utf-8")
    handle = mock_open()
    handle.write.assert_any_call(f"custom-output<<{FIXED_DELIMITER}\n")
    handle.write.assert_any_call("custom_value\n")
    handle.write.assert_any_call(f"{FIXED_DELIMITER}\n")


# set_output_text


def test_set_output_text_default(mocker: MockerFixture, fixed_delimiter):
    mocker.patch("os.getenv", return_value="default_output.txt")
    mock_open = mocker.patch("builtins.open", new_callable=mocker.mock_open)

    set_action_output_text("test-output", "test_value")

    mock_open.assert_called_with("default_output.txt", "a", encoding="utf-8")
    handle = mock_open()
    handle.write.assert_any_call(f"test-output<<{FIXED_DELIMITER}\n")
    handle.write.assert_any_call("test_value\n")
    handle.write.assert_any_call(f"{FIXED_DELIMITER}\n")


def test_set_output_text_custom_path(mocker: MockerFixture, fixed_delimiter):
    mocker.patch("os.getenv", return_value="custom_output.txt")
    mock_open = mocker.patch("builtins.open", new_callable=mocker.mock_open)

    set_action_output_text("custom-output", "custom_value", "default_output.txt")

    mock_open.assert_called_with("custom_output.txt", "a", encoding="utf-8")
    handle = mock_open()
    handle.write.assert_any_call(f"custom-output<<{FIXED_DELIMITER}\n")
    handle.write.assert_any_call("custom_value\n")
    handle.write.assert_any_call(f"{FIXED_DELIMITER}\n")


def _read_output_file(path) -> dict[str, str]:
    """
    Parse a GITHUB_OUTPUT file the way the runner does: `name=value` on one line, or `name<<delimiter`
    up to a line equal to the delimiter.
    """
    outputs: dict[str, str] = {}
    lines = path.read_text(encoding="utf-8").split("\n")
    i = 0
    while i < len(lines):
        if not lines[i]:
            i += 1
            continue
        key, _, rest = lines[i].partition("=")
        if "<<" in key:
            name, delimiter = key.split("<<", 1)
            end = lines.index(delimiter, i + 1)
            outputs[name] = "\n".join(lines[i + 1 : end])
            i = end + 1
        else:
            outputs[key] = rest
            i += 1
    return outputs


def test_set_output_text_value_with_eof_line_round_trips_as_one_output(tmp_path, monkeypatch):
    output_file = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    value = "first\nEOF\nsecond=injected\nEOF"

    set_action_output_text("report", value)

    assert _read_output_file(output_file) == {"report": value}


@pytest.mark.parametrize("writer", [set_action_output, set_action_output_text], ids=["plain", "text"])
def test_output_value_with_newline_does_not_create_extra_output(writer, tmp_path, monkeypatch):
    output_file = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    value = "first\nsecond=injected"

    writer("report", value)

    assert _read_output_file(output_file) == {"report": value}


@pytest.mark.parametrize("writer", [set_action_output, set_action_output_text], ids=["plain", "text"])
@pytest.mark.parametrize("name", ["a\nb=c", "a\rb=c"], ids=["lf", "cr"])
def test_output_name_with_line_break_is_refused_and_nothing_written(writer, name, tmp_path, monkeypatch):
    output_file = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    with pytest.raises(ValueError):
        writer(name, "value")

    assert not output_file.exists()


def test_break_legacy_command_prefix_rewrites_every_prefix():
    assert break_legacy_command_prefix("bad ##[add-mask]x ##[end]") == "bad ## [add-mask]x ## [end]"


def test_break_legacy_command_prefix_leaves_other_text_unchanged():
    assert break_legacy_command_prefix("## Heading [1]") == "## Heading [1]"


def test_set_failed(mocker: MockerFixture):
    mock_print = mocker.patch("builtins.print", return_value=None)
    mock_exit = mocker.patch("sys.exit", return_value=None)

    set_action_failed(["failure message"])

    mock_print.assert_called_with("::error::failure message")
    mock_exit.assert_called_with(1)


def test_set_failed_escapes_newline_so_message_cannot_inject_command(mocker: MockerFixture):
    mock_print = mocker.patch("builtins.print", return_value=None)
    mocker.patch("sys.exit", return_value=None)

    set_action_failed(["ok\n::add-mask::x"])

    mock_print.assert_called_once_with("::error::ok%0A::add-mask::x")


def test_set_failed_breaks_legacy_command_prefix(mocker: MockerFixture):
    mock_print = mocker.patch("builtins.print", return_value=None)
    mocker.patch("sys.exit", return_value=None)

    set_action_failed(["bad ##[add-mask]x"])

    mock_print.assert_called_once_with("::error::bad ## [add-mask]x")


def test_set_failed_escapes_percent_before_other_characters(mocker: MockerFixture):
    mock_print = mocker.patch("builtins.print", return_value=None)
    mocker.patch("sys.exit", return_value=None)

    set_action_failed(["100% done\r\nnext"])

    mock_print.assert_called_once_with("::error::100%25 done%0D%0Anext")


# print_action_warning


def test_print_action_warning_prints_warning_command(mocker: MockerFixture, capsys):
    mocker.patch("sys.exit", return_value=None)

    print_action_warning("comment not changed")

    assert capsys.readouterr().out == "::warning::comment not changed\n"


def test_print_action_warning_does_not_exit(mocker: MockerFixture):
    mock_exit = mocker.patch("sys.exit", return_value=None)

    print_action_warning("comment not changed")

    mock_exit.assert_not_called()


def test_print_action_warning_escapes_newline_so_message_cannot_inject_command(capsys):
    print_action_warning("ok\n::add-mask::x")

    assert capsys.readouterr().out == "::warning::ok%0A::add-mask::x\n"


def test_print_action_warning_breaks_legacy_command_prefix(capsys):
    print_action_warning("bad ##[add-mask]x")

    assert capsys.readouterr().out == "::warning::bad ## [add-mask]x\n"


def test_print_action_warning_escapes_percent_before_other_characters(capsys):
    print_action_warning("100% done\r\nnext")

    assert capsys.readouterr().out == "::warning::100%25 done%0D%0Anext\n"


# job summary (GITHUB_STEP_SUMMARY)


def test_step_summary_path_is_the_runner_variable(monkeypatch, tmp_path):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert get_step_summary_path() == str(summary)


def test_step_summary_path_is_empty_when_unset(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert get_step_summary_path() == ""


def test_append_step_summary_writes_exactly_the_text_as_utf8(tmp_path):
    # Nothing is added: a body cut to the 1 MiB limit must leave the file at or under the limit.
    summary = tmp_path / "summary.md"
    assert append_step_summary(str(summary), "**Title** ✅ ok") is True
    assert summary.read_bytes() == "**Title** ✅ ok".encode("utf-8")


def test_append_step_summary_appends_to_existing_content(tmp_path):
    summary = tmp_path / "summary.md"
    summary.write_text("first\n", encoding="utf-8")
    assert append_step_summary(str(summary), "second") is True
    assert summary.read_text(encoding="utf-8") == "first\nsecond"


def test_append_step_summary_returns_false_and_logs_the_error_when_the_write_fails(tmp_path, caplog):
    # A directory cannot be opened for appending, so the write raises OSError.
    with caplog.at_level(logging.ERROR, logger="jacoco_report.utils.gh_action"):
        assert append_step_summary(str(tmp_path), "body") is False
    assert "Could not write the job summary" in caplog.text
    assert caplog.records[0].exc_info is not None
