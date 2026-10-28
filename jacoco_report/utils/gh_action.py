"""
Utility functions for interacting with GitHub Actions.
"""

import os
import re
import sys
import uuid

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
