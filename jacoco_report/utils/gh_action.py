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


def set_action_output(name: str, value: str, default_output_path: str = "default_output.txt") -> None:
    """
    Write an action output to a file in the format expected by GitHub Actions.

    This function writes the output in a specific format that includes the name of the
    output and its value. The output is appended to the specified file.

    @param name: The name of the output parameter.
    @param value: The value of the output parameter.
    @param default_output_path: The default file path to which the output is written if the
    @return: None
    """
    output_file = os.getenv("GITHUB_OUTPUT", default_output_path)
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"{name}={value}\n")


def set_action_output_text(name: str, value: str, default_output_path: str = "default_output.txt") -> None:
    """
    Write an action output to a file in the format expected by GitHub Actions.

    @param name: The name of the output parameter.
    @param value: The value of the output parameter.
    @param default_output_path: The default file path to which the output is written if the
    'GITHUB_OUTPUT' environment variable is not set. Defaults to "default_output.txt".
    """
    # A fixed delimiter would end the heredoc early at a value line equal to it, so the delimiter is random,
    # as in actions/toolkit. Refuse a name or value that contains it, before anything is written.
    delimiter = f"ghadelimiter_{uuid.uuid4()}"
    if delimiter in name or delimiter in value:
        raise ValueError(f"Output '{name}' contains the generated delimiter; refusing to write it.")
    output_file = os.getenv("GITHUB_OUTPUT", default_output_path)
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"{name}<<{delimiter}\n")
        f.write(f"{value}\n")
        f.write(f"{delimiter}\n")


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
