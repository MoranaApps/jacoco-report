import pytest


@pytest.fixture
def mock_logging_setup(mocker):
    """Fixture to mock the basic logging setup using pytest-mock."""
    mock_log_config = mocker.patch("logging.basicConfig")
    yield mock_log_config
