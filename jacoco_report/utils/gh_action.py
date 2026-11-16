"""
Utility functions for interacting with GitHub Actions.
"""

import logging
import os
import re
import sys
import uuid

logger = logging.getLogger(__name__)

# The runner's legacy `##[command]` syntax is found anywhere in a line, so `##[` is broken up as well.
LEGACY_COMMAND_PREFIX = re.compile(r"##\[")


def break_legacy_command_prefix(text: str) -> str:
    """
    Rewrite every legacy `##[` command prefix to `## [`, so the runner's v1 parser does not find it.

    @param text: The text to rewrite.
    @return: The text without the `##[` prefix.
    """
    return LEGACY_COMMAND_PREFIX.sub("## [", text)


def get_action_input(name: str, default: str = "", prefix: str = "INPUT_") -> str:
    """
    Retrieve the value of a specified input parameter from environment variables.

    @param name: The name of the input parameter.
    @param default: The default value to return if the environment variable is not set.

    @return: The value of the specified input parameter, or an empty string if the environment
    """
    return os.getenv(f'{prefix}{name.replace("-", "_").upper()}', default=default)


def _write_action_output(name: str, value: str, default_output_path: str) -> None:
    """
    Append one output to the GITHUB_OUTPUT file, in the heredoc form for every value.

    A newline in a value would otherwise start a new line of the file, which the runner reads as another
    output. The delimiter is random, so no value line can equal it and end the heredoc early, as in
    actions/toolkit. A name with a line break is refused before anything is written.

    @param name: The name of the output parameter. Must not contain a line break.
    @param value: The value of the output parameter.
    @param default_output_path: The file path used when 'GITHUB_OUTPUT' is not set.
    @raise ValueError: If the name contains a line break.
    """
    if "\n" in name or "\r" in name:
        raise ValueError(f"Output name {name!r} contains a line break; refusing to write it.")
    delimiter = f"ghadelimiter_{uuid.uuid4()}"
    output_file = os.getenv("GITHUB_OUTPUT", default_output_path)
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"{name}<<{delimiter}\n")
        f.write(f"{value}\n")
        f.write(f"{delimiter}\n")


def set_action_output(name: str, value: str, default_output_path: str = "default_output.txt") -> None:
    """
    Write an action output to a file in the format expected by GitHub Actions.

    The output is appended to the file named by 'GITHUB_OUTPUT'.

    @param name: The name of the output parameter. Must not contain a line break.
    @param value: The value of the output parameter.
    @param default_output_path: The default file path to which the output is written if the
    'GITHUB_OUTPUT' environment variable is not set. Defaults to "default_output.txt".
    @return: None
    """
    _write_action_output(name, value, default_output_path)


def set_action_output_text(name: str, value: str, default_output_path: str = "default_output.txt") -> None:
    """
    Write an action output to a file in the format expected by GitHub Actions.

    @param name: The name of the output parameter. Must not contain a line break.
    @param value: The value of the output parameter.
    @param default_output_path: The default file path to which the output is written if the
    'GITHUB_OUTPUT' environment variable is not set. Defaults to "default_output.txt".
    """
    _write_action_output(name, value, default_output_path)


def get_step_summary_path() -> str:
    """
    Get the job summary file the runner set for this step ('GITHUB_STEP_SUMMARY').

    @return: The file path, or an empty string when the variable is not set (outside a GitHub Actions runner,
    or on GHES older than 3.6).
    """
    return os.getenv("GITHUB_STEP_SUMMARY", "")


def append_step_summary(path: str, text: str) -> bool:
    """
    Append markdown to the job summary file, as UTF-8. Nothing is added, so a body within the limit keeps the file
    within it.

    @param path: The job summary file path, as returned by get_step_summary_path().
    @param text: The markdown to append.
    @return: True when the text was written. False when the write failed: the error is logged with its traceback.
    """
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        logger.error("Could not write the job summary to GITHUB_STEP_SUMMARY.", exc_info=True)
        return False
    return True


SUMMARY_NOT_SET_WARNING = (
    "report-target '{target}' writes to the job summary, but GITHUB_STEP_SUMMARY is not set (not a GitHub Actions "
    "runner, or GHES older than 3.6). The report was not written to the job summary."
)
SUMMARY_WRITE_FAILED_WARNING = (
    "report-target '{target}' writes to the job summary, but writing to GITHUB_STEP_SUMMARY failed. "
    "The report was not written to the job summary. See the job log for the error."
)


def write_job_summary(target: str, body: str) -> str | None:
    """
    Append a report body to the job summary of this step.

    @param target: The report-target value, named in the warning.
    @param body: The markdown to append.
    @return: None when it was written, else the warning for the caller to print: GITHUB_STEP_SUMMARY is not set,
    or the write failed.
    """
    path = get_step_summary_path()
    if not path:
        return SUMMARY_NOT_SET_WARNING.format(target=target)
    if not append_step_summary(path, body):
        return SUMMARY_WRITE_FAILED_WARNING.format(target=target)
    return None


def escape_workflow_command_data(value: str) -> str:
    """
    Escape a value so it can be printed as the message of a workflow command.

    Same escaping as actions/toolkit `escapeData`. `%` is escaped first so the escapes added for
    `\\r` and `\\n` are not escaped again. Without it, a newline in a message could start a new
    workflow command line such as `::add-mask::`. The legacy `##[` prefix is broken to `## [`, because
    the runner finds it anywhere in a line.

    @param value: The text to escape.
    @return: The escaped text, safe to print on a single line.
    """
    escaped = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return break_legacy_command_prefix(escaped)


def set_action_failed(messages: list[str], fail: bool = True) -> None:
    """
    Mark the GitHub Action as failed and exit with an error message.

    @param messages: A list of error messages to display.
    @param fail: A boolean flag indicating whether the action should be marked as failed.
    @return: None
    """
    annotation = "error" if fail else "notice"
    for message in messages:
        print(f"::{annotation}::{escape_workflow_command_data(message)}")

    sys.exit(1 if fail else 0)


def print_action_warning(message: str) -> None:
    """
    Print a workflow warning annotation without changing the job result.

    @param message: The warning message to display.
    @return: None
    """
    print(f"::warning::{escape_workflow_command_data(message)}")
