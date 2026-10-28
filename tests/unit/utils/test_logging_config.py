import io
import logging
import os
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

from jacoco_report.utils import logging_config
from tests import conftest as tests_conftest
from jacoco_report.utils.logging_config import setup_logging


def test_default_logging_level(mock_logging_setup, caplog):
    """Test default logging level when no environment variables are set."""
    with caplog.at_level(logging.INFO):
        setup_logging()

    mock_logging_setup.assert_called_once()

    # Get the actual call arguments from the mock
    call_args = mock_logging_setup.call_args[1]  # Extract the kwargs from the call

    # Validate the logging level and format
    assert call_args["level"] == logging.INFO
    formatter = call_args["handlers"][0].formatter
    assert isinstance(formatter, logging_config.WorkflowCommandSafeFormatter)
    assert formatter._fmt == logging_config.LOG_FORMAT
    assert formatter.datefmt == logging_config.LOG_DATE_FORMAT

    # Check that the handler is a StreamHandler and outputs to sys.stdout
    handlers = call_args["handlers"]
    assert len(handlers) == 1  # Only one handler is expected
    assert isinstance(handlers[0], logging.StreamHandler)  # Handler should be StreamHandler
    assert handlers[0].stream is sys.stdout  # Stream should be sys.stdout

    # Check that the log message is present
    assert "Logging configuration set up." in caplog.text


def test_verbose_logging_enabled(mock_logging_setup, caplog):
    """Test that verbose logging is enabled with INPUT_VERBOSE set to true."""
    os.environ["INPUT_DEBUG"] = "true"

    with caplog.at_level(logging.DEBUG):
        setup_logging()

    mock_logging_setup.assert_called_once()

    # Get the actual call arguments from the mock
    call_args = mock_logging_setup.call_args[1]  # Extract the kwargs from the call

    # Validate the logging level and format
    assert call_args["level"] == logging.DEBUG
    formatter = call_args["handlers"][0].formatter
    assert isinstance(formatter, logging_config.WorkflowCommandSafeFormatter)
    assert formatter._fmt == logging_config.LOG_FORMAT
    assert formatter.datefmt == logging_config.LOG_DATE_FORMAT

    # Check that the handler is a StreamHandler and outputs to sys.stdout
    handlers = call_args["handlers"]
    assert len(handlers) == 1  # Only one handler is expected
    assert isinstance(handlers[0], logging.StreamHandler)
    assert handlers[0].stream is sys.stdout

    assert "Debug logging enabled" in caplog.text


def test_debug_mode_enabled(mock_logging_setup, caplog):
    """Test that debug mode is enabled when RUNNER_DEBUG is set to 1."""
    os.environ["RUNNER_DEBUG"] = "1"

    with caplog.at_level(logging.DEBUG):
        setup_logging()

    mock_logging_setup.assert_called_once()

    # Get the actual call arguments from the mock
    call_args = mock_logging_setup.call_args[1]  # Extract the kwargs from the call

    # Validate the logging level and format
    assert call_args["level"] == logging.DEBUG
    formatter = call_args["handlers"][0].formatter
    assert isinstance(formatter, logging_config.WorkflowCommandSafeFormatter)
    assert formatter._fmt == logging_config.LOG_FORMAT
    assert formatter.datefmt == logging_config.LOG_DATE_FORMAT

    # Check that the handler is a StreamHandler and outputs to sys.stdout
    handlers = call_args["handlers"]
    assert len(handlers) == 1  # Only one handler is expected
    assert isinstance(handlers[0], logging.StreamHandler)
    assert handlers[0].stream is sys.stdout

    assert "Debug mode enabled by CI runner" in caplog.text


def _format_record(msg: str, args: tuple = (), exc_info=None) -> str:
    """Format one record with the workflow-command-safe formatter."""
    record = logging.LogRecord("test", logging.INFO, __file__, 1, msg, args, exc_info)
    return logging_config.WorkflowCommandSafeFormatter("%(message)s").format(record)


def _continuation_lines(text: str) -> list[str]:
    """Return every line after the first one of a formatted record."""
    return text.split("\n")[1:]


@pytest.mark.parametrize(
    "msg, args",
    [
        ("a\n::add-mask::x", ()),
        ("a\r::add-mask::x", ()),
        ("a\r\n::add-mask::x", ()),
        ("value %s", ("a\n::add-mask::x",)),
        ("value %s", ("a\r\n::stop-commands::t",)),
    ],
    ids=["newline-in-message", "cr-in-message", "crlf-in-message", "newline-in-argument", "crlf-in-argument"],
)
def test_line_break_never_starts_a_workflow_command(msg, args):
    """A line break in any part of a record must not start a line that the runner could parse as a command."""
    text = _format_record(msg, args)

    assert "\r" not in text
    assert all(line.startswith("| ") for line in _continuation_lines(text))
    assert not any(line.lstrip().startswith("::") for line in text.split("\n"))


def test_line_break_is_marked_and_kept_visible():
    """The break stays visible as a continuation line, so the text reads the same."""
    assert _format_record("a\n::add-mask::x") == "a\n| ::add-mask::x"


def test_traceback_line_break_never_starts_a_workflow_command():
    """Exception text with a line break must not start a traceback line with a command."""
    try:
        raise ValueError("x\n::stop-commands::t")
    except ValueError:
        text = _format_record("boom", exc_info=sys.exc_info())

    assert "Traceback" in text
    assert all(line.startswith("| ") for line in _continuation_lines(text))
    assert "| ::stop-commands::t" in text


def test_first_line_that_starts_with_command_is_neutralized_without_timestamp_prefix():
    """A format without a leading timestamp must not let the first line start a workflow command."""
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "::add-mask::x", (), None)
    text = logging_config.WorkflowCommandSafeFormatter("%(message)s").format(record)

    assert text == "| ::add-mask::x"


@pytest.mark.parametrize("msg", ["  ::add-mask::x", "\t::add-mask::x"], ids=["spaces", "tab"])
def test_first_line_with_leading_whitespace_before_command_is_neutralized(msg):
    """The runner may trim leading whitespace, so a first line indented before `::` is neutralized too."""
    text = _format_record(msg)

    assert not text.lstrip().startswith("::")
    assert text.lstrip().startswith("| ")


def test_plain_text_is_unchanged():
    """Ordinary messages without line breaks are not altered."""
    assert _format_record("coverage 97.44%") == "coverage 97.44%"
    assert _format_record("value %s", ("ok",)) == "value ok"


def test_setup_logging_installs_safe_formatter(mock_logging_setup):
    """The handler given to basicConfig uses the workflow-command-safe formatter."""
    setup_logging()

    handlers = mock_logging_setup.call_args[1]["handlers"]
    assert isinstance(handlers[0].formatter, logging_config.WorkflowCommandSafeFormatter)


def test_emitted_record_with_line_break_argument_is_safe(mock_logging_setup, monkeypatch):
    """A record logged through the configured handler has no line that starts with a command."""
    setup_logging()
    handler = mock_logging_setup.call_args[1]["handlers"][0]
    stream = io.StringIO()
    handler.stream = stream

    logger = logging.getLogger("test_emitted_record_with_line_break_argument_is_safe")
    monkeypatch.setattr(logger, "handlers", [handler])
    monkeypatch.setattr(logger, "propagate", False)
    monkeypatch.setattr(logger, "level", logging.INFO)
    logger.info("Report name %s", "evil\n::add-mask::secret")

    output = stream.getvalue()
    assert "::add-mask::secret" in output
    assert not any(line.lstrip().startswith("::") for line in output.split("\n"))


def _output_of_root_handler(mock_logging_setup, monkeypatch) -> io.StringIO:
    """Run setup_logging and route the root logger's handler into a buffer."""
    setup_logging()
    handler = mock_logging_setup.call_args[1]["handlers"][0]
    stream = io.StringIO()
    handler.stream = stream
    monkeypatch.setattr(logging.getLogger(), "handlers", [handler])
    return stream


def test_uncaught_exception_is_logged_through_safe_formatter(mock_logging_setup, monkeypatch):
    """An uncaught exception is logged at ERROR with its traceback, and its line breaks stay neutralized."""
    stream = _output_of_root_handler(mock_logging_setup, monkeypatch)

    try:
        raise ValueError("bad path\n::add-mask::secret")
    except ValueError as err:
        sys.excepthook(type(err), err, err.__traceback__)

    output = stream.getvalue()
    assert " - ERROR - " in output
    assert "Traceback" in output
    assert "| ::add-mask::secret" in output
    assert not any(line.lstrip().startswith("::") for line in output.split("\n"))


def test_keyboard_interrupt_goes_to_default_hook(mock_logging_setup, monkeypatch):
    """KeyboardInterrupt is left to the default hook."""
    setup_logging()
    default_hook_calls = []
    monkeypatch.setattr(sys, "__excepthook__", lambda *args: default_hook_calls.append(args))

    err = KeyboardInterrupt()
    sys.excepthook(KeyboardInterrupt, err, None)

    assert default_hook_calls == [(KeyboardInterrupt, err, None)]


def test_uncaught_exception_still_exits_with_code_one():
    """The process exits with 1 after an uncaught exception, and the message is logged to stdout."""
    script = (
        "from jacoco_report.utils.logging_config import setup_logging\n"
        "setup_logging()\n"
        "raise ValueError('boom\\n::add-mask::secret')\n"
    )
    repo_root = Path(__file__).resolve().parents[3]

    result = subprocess.run([sys.executable, "-c", script], cwd=repo_root, capture_output=True, text=True, check=False)

    assert result.returncode == 1
    assert "ValueError" in result.stdout
    assert not any(line.lstrip().startswith("::") for line in result.stdout.split("\n"))


def test_python_warning_goes_through_safe_formatter(mock_logging_setup, monkeypatch):
    """A Python warning is logged through the handler, so its line breaks stay neutralized."""
    stream = _output_of_root_handler(mock_logging_setup, monkeypatch)

    warnings.warn("deprecated\n::add-mask::secret", UserWarning)

    output = stream.getvalue()
    assert "UserWarning" in output
    assert "| ::add-mask::secret" in output
    assert not any(line.lstrip().startswith("::") for line in output.split("\n"))


@pytest.mark.parametrize(
    "msg, args",
    [
        ("##[add-mask]x", ()),
        ("value %s", ("##[add-mask]x",)),
        ("a\n##[add-mask]x", ()),
        ("###[add-mask]x", ()),
    ],
    ids=["message", "argument", "after-line-break", "three-hashes"],
)
def test_legacy_command_prefix_is_never_emitted(msg, args):
    """The runner's v1 `##[` command syntax is found anywhere in a line, so no record may contain it."""
    assert "##[" not in _format_record(msg, args)


def test_traceback_legacy_command_prefix_is_never_emitted():
    """Exception text with the v1 command prefix must not reach the runner as a command."""
    try:
        raise ValueError("bad ##[add-mask]x")
    except ValueError:
        text = _format_record("boom", exc_info=sys.exc_info())

    assert "Traceback" in text
    assert "##[" not in text
    assert "## [add-mask]x" in text


def test_text_with_hashes_and_brackets_is_unchanged():
    """Text that only looks like the command prefix, without `##[` together, is not altered."""
    assert _format_record("## Heading [1]") == "## Heading [1]"
    assert _format_record("items [a] ## b") == "items [a] ## b"


def test_setup_logging_replaces_a_handler_configured_before():
    """With the real basicConfig, a root handler added earlier is replaced by the safe handler."""
    root = logging.getLogger()
    earlier = logging.StreamHandler(io.StringIO())
    root.handlers[:] = [earlier]

    setup_logging()

    assert earlier not in root.handlers
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, logging_config.WorkflowCommandSafeFormatter)


def test_restore_fixture_undoes_real_basicConfig(monkeypatch):
    """The autouse root-logger fixture in conftest puts back what the real basicConfig replaced.

    The fixture generator is driven by hand. The test sets its own root level first, so the result does not
    depend on --log-level, and it does not depend on test order.
    """
    root = logging.getLogger()
    monkeypatch.setattr(root, "level", logging.CRITICAL)
    handlers_before, level_before = root.handlers[:], root.level
    restore = tests_conftest.restore_root_logger_after_test.__wrapped__()
    next(restore)

    setup_logging()
    assert root.level != level_before
    assert root.handlers != handlers_before

    next(restore, None)

    assert root.level == level_before
    assert root.handlers == handlers_before
