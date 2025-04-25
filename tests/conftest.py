import pytest

from jacoco_report.utils.github import GitHub


@pytest.fixture
def mock_logging_setup(mocker):
    """Fixture to mock the basic logging setup using pytest-mock."""
    mock_log_config = mocker.patch("logging.basicConfig")
    yield mock_log_config

@pytest.fixture
def github(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    return GitHub("fake_token")
