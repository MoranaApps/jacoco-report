"""
This module contains the logging configuration for the project.
"""

import logging
import os
import re
import sys
from types import TracebackType

from jacoco_report.utils.gh_action import break_legacy_command_prefix

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


_LINE_BREAK = re.compile(r"\r\n|\r|\n")


class WorkflowCommandSafeFormatter(logging.Formatter):
    """
    Formatter that stops a record from carrying workflow commands to the GitHub runner.

    A line break in a message, argument or traceback (for example text from a PR report XML) could
    start a line such as `::add-mask::`, which the runner reads as a workflow command. Each
    continuation line gets a leading `| ` marker instead. The runner also reads the legacy `##[command]`
    syntax anywhere in a line, so every `##[` becomes `## [`.
    """

    def format(self, record: logging.LogRecord) -> str:
        text = _LINE_BREAK.sub("\n| ", super().format(record))
        if text.lstrip().startswith("::"):
            text = "| " + text
        return break_legacy_command_prefix(text)


def _log_uncaught_exception(
    exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType | None
) -> None:
    """
    Log an uncaught exception through the logger, so its line breaks are neutralized like any other record.

    Interrupts are left to the default hook. The interpreter still exits with code 1 afterwards.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Uncaught exception, the action stops.", exc_info=(exc_type, exc_value, exc_traceback))


def setup_logging() -> None:
    """
    Set up the logging configuration in the project

    @return: None
    """
    # Load logging configuration from the environment variables
    is_verbose_logging: bool = os.getenv("INPUT_DEBUG", "false").lower() == "true"
    is_debug_mode = os.getenv("RUNNER_DEBUG", "0") == "1"
    level = logging.DEBUG if is_verbose_logging or is_debug_mode else logging.INFO

    # Set up the logging configuration
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(WorkflowCommandSafeFormatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logging.basicConfig(
        level=level,
        handlers=[handler],
        force=True,
    )
    sys.stdout.flush()

    # Route uncaught exceptions and Python warnings (stderr) through the same formatter
    sys.excepthook = _log_uncaught_exception
    logging.captureWarnings(True)

    logging.info("Logging configuration set up.")

    if is_verbose_logging:
        logging.debug("Debug logging enabled.")
    if is_debug_mode:
        logging.debug("Debug mode enabled by CI runner.")
