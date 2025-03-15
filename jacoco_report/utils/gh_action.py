"""
Utility functions for interacting with GitHub Actions.
"""

import os
import sys
from typing import Optional


def get_action_input(name: str, default: Optional[str] = None, prefix: str = "INPUT_") -> str:
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


def set_action_output_text(name: str, value: str, default_output_path: str = "default_output.txt"):
    """
    Write an action output to a file in the format expected by GitHub Actions.

    @param name: The name of the output parameter.
    @param value: The value of the output parameter.
    @param default_output_path: The default file path to which the output is written if the
    'GITHUB_OUTPUT' environment variable is not set. Defaults to "default_output.txt".
    """
    output_file = os.getenv("GITHUB_OUTPUT", default_output_path)
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"{name}<<EOF\n")
        f.write(f"{value}\n")
        f.write("EOF\n")


def set_action_failed(messages: list[str], fail: bool = True) -> None:
    """
    Mark the GitHub Action as failed and exit with an error message.

    @param messages: A list of error messages to display.
    @param fail: A boolean flag indicating whether the action should be marked as failed.
    @return: None
    """
    for message in messages:
        print(f"::error::{message}")

    sys.exit(1 if fail else 0)
