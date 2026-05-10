import logging
import os
import sys

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
    assert call_args["format"] == "%(asctime)s - %(levelname)s - %(message)s"
    assert call_args["datefmt"] == "%Y-%m-%d %H:%M:%S"

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
    assert call_args["format"] == "%(asctime)s - %(levelname)s - %(message)s"
    assert call_args["datefmt"] == "%Y-%m-%d %H:%M:%S"

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
    assert call_args["format"] == "%(asctime)s - %(levelname)s - %(message)s"
    assert call_args["datefmt"] == "%Y-%m-%d %H:%M:%S"

    # Check that the handler is a StreamHandler and outputs to sys.stdout
    handlers = call_args["handlers"]
    assert len(handlers) == 1  # Only one handler is expected
    assert isinstance(handlers[0], logging.StreamHandler)
    assert handlers[0].stream is sys.stdout

    assert "Debug mode enabled by CI runner" in caplog.text
