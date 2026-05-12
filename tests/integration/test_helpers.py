import logging
import os

from pytest_mock import MockerFixture

from tests.integration.helpers import capture_run


class TrackingHandler(logging.Handler):
    """Track whether close() was called during teardown."""

    def __init__(self) -> None:
        super().__init__()
        self.was_closed = False

    def emit(self, record: logging.LogRecord) -> None:
        del record

    def close(self) -> None:
        self.was_closed = True
        super().close()


def test_capture_run_clears_preexisting_ci_env_keys(mocker: MockerFixture, monkeypatch) -> None:
    """Ensure stale INPUT_/GITHUB_ env keys do not leak into capture_run execution."""
    monkeypatch.setenv("INPUT_STALE", "stale-input")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "stale-event")

    observed_env: dict[str, str | None] = {}

    def fake_run() -> None:
        observed_env["INPUT_STALE"] = os.getenv("INPUT_STALE")
        observed_env["GITHUB_EVENT_NAME"] = os.getenv("GITHUB_EVENT_NAME")

    mocker.patch("main.run", side_effect=fake_run)

    capture_run({"INPUT_PATHS": "tests/data/test_project/**/jacoco.xml"})

    assert observed_env["INPUT_STALE"] is None
    assert observed_env["GITHUB_EVENT_NAME"] is None


def test_capture_run_closes_handlers_added_during_run(mocker: MockerFixture) -> None:
    """Ensure handlers added during run are removed and closed in teardown."""
    root_logger = logging.getLogger()

    saved_handler = logging.NullHandler()
    root_logger.addHandler(saved_handler)

    runtime_handler = TrackingHandler()

    def fake_run() -> None:
        root_logger.addHandler(runtime_handler)

    mocker.patch("main.run", side_effect=fake_run)

    try:
        capture_run({"INPUT_PATHS": "tests/data/test_project/**/jacoco.xml"})
    finally:
        if saved_handler in root_logger.handlers:
            root_logger.removeHandler(saved_handler)

    assert runtime_handler.was_closed is True
