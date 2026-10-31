import io
import os

import pytest
import requests

from jacoco_report.utils.github import GitHub, get_api_url, get_server_url

# get_pr_changed_files


def test_get_pr_changed_files(mocker):
    mocker.patch(
        "os.getenv", side_effect=lambda key: "fake_repo" if key == "GITHUB_REPOSITORY" else "refs/pull/1/merge"
    )
    mock_response = mocker.Mock()
    mock_response.json.return_value = [{"filename": "file1.py"}, {"filename": "file2.py"}]
    mocker.patch.object(GitHub, "send_request", return_value=mock_response)
    github = GitHub("fake_token")

    files = github.get_pr_changed_files()

    assert files == ["file1.py", "file2.py"]


def test_get_pr_changed_files_none_response(mocker):
    mocker.patch(
        "os.getenv", side_effect=lambda key: "fake_repo" if key == "GITHUB_REPOSITORY" else "refs/pull/1/merge"
    )
    mocker.patch.object(GitHub, "send_request", return_value=None)
    github = GitHub("fake_token")

    files = github.get_pr_changed_files()

    assert files is None


# get_api_url / get_server_url (GitHub Enterprise Server: runner default variables, not action inputs)


def test_get_api_url_returns_runner_value(monkeypatch):
    monkeypatch.setenv("GITHUB_API_URL", "https://ghes.example.com/api/v3")
    assert get_api_url() == "https://ghes.example.com/api/v3"


def test_get_server_url_returns_runner_value(monkeypatch):
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://ghes.example.com")
    assert get_server_url() == "https://ghes.example.com"


@pytest.mark.parametrize("env_value", [None, ""])
def test_get_api_url_falls_back_to_github_com(env_value, monkeypatch):
    if env_value is None:
        monkeypatch.delenv("GITHUB_API_URL", raising=False)
    else:
        monkeypatch.setenv("GITHUB_API_URL", env_value)
    assert get_api_url() == "https://api.github.com"


@pytest.mark.parametrize("env_value", [None, ""])
def test_get_server_url_falls_back_to_github_com(env_value, monkeypatch):
    if env_value is None:
        monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)
    else:
        monkeypatch.setenv("GITHUB_SERVER_URL", env_value)
    assert get_server_url() == "https://github.com"


# custom API base (GitHub Enterprise Server)


def test_get_pr_changed_files_uses_custom_api_url(mocker):
    mocker.patch(
        "os.getenv", side_effect=lambda key: "fake_repo" if key == "GITHUB_REPOSITORY" else "refs/pull/1/merge"
    )
    mock_send = mocker.patch.object(GitHub, "send_request", return_value=None)
    github = GitHub("fake_token", api_url="https://ghes.example.com/api/v3")

    github.get_pr_changed_files()

    assert mock_send.call_args.args[1] == "https://ghes.example.com/api/v3/repos/fake_repo/pulls/1/files"


def test_add_comment_uses_custom_api_url(mocker, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "fake_repo")
    mock_send = mocker.patch.object(GitHub, "send_request", return_value=None)
    github = GitHub("fake_token", api_url="https://ghes.example.com/api/v3")

    github.add_comment(1, "Test comment")

    assert mock_send.call_args.args[1] == "https://ghes.example.com/api/v3/repos/fake_repo/issues/1/comments"


def _capture_request_headers(mocker):
    """Patch the transport so the real requests session runs and the headers of the prepared request are recorded."""
    seen = []

    def fake_send(request, **kwargs):
        seen.append(dict(request.headers))
        response = requests.Response()
        response.status_code = 200
        response.raw = io.BytesIO(b"[]")
        return response

    mocker.patch("requests.adapters.HTTPAdapter.send", side_effect=fake_send)
    return seen


def test_session_sends_no_host_header_and_keeps_authorization(mocker):
    seen = _capture_request_headers(mocker)

    GitHub("fake_token", api_url="https://ghes.example.com/api/v3").send_request("GET", "https://ghes.example.com/x")

    assert "Host" not in seen[0]
    assert seen[0]["Authorization"] == "Bearer fake_token"


# send_request


def testsend_request_get(mocker):
    mock_session = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_session.get.return_value = mock_response
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token")

    response = github.send_request("GET", "https://api.github.com/test")

    mock_session.get.assert_called_once_with("https://api.github.com/test", params=None, timeout=(10, 60))
    mock_response.raise_for_status.assert_called_once()
    assert response == mock_response


def testsend_request_post(mocker):
    mock_session = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_session.post.return_value = mock_response
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token")

    response = github.send_request("POST", "https://api.github.com/test", data={"key": "value"})

    mock_session.post.assert_called_once_with(
        "https://api.github.com/test", json={"key": "value"}, params=None, timeout=(10, 60)
    )
    mock_response.raise_for_status.assert_called_once()
    assert response == mock_response


def testsend_request_patch(mocker):
    mock_session = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_session.patch.return_value = mock_response
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token")

    response = github.send_request("PATCH", "https://api.github.com/test", data={"key": "value"})

    mock_session.patch.assert_called_once_with(
        "https://api.github.com/test", json={"key": "value"}, params=None, timeout=(10, 60)
    )
    mock_response.raise_for_status.assert_called_once()
    assert response == mock_response


def testsend_request_delete(mocker):
    mock_session = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_session.delete.return_value = mock_response
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token")

    response = github.send_request("DELETE", "https://api.github.com/test", data={"key": "value"})

    mock_session.delete.assert_called_once_with(
        "https://api.github.com/test", json={"key": "value"}, params=None, timeout=(10, 60)
    )
    mock_response.raise_for_status.assert_called_once()
    assert response == mock_response


def testsend_request_unsupported_method(mocker):
    mock_logger = mocker.patch("jacoco_report.utils.github.logger")
    github = GitHub("fake_token")

    response = github.send_request("PUT", "https://api.github.com/test")

    mock_logger.error.assert_called_once_with("Unsupported HTTP method: %s.", "PUT")
    assert response is None


def testsend_request_get_http_error(mocker):
    mock_session = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("HTTP Error")
    mock_session.get.return_value = mock_response
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token")

    response = github.send_request("GET", "https://api.github.com/test")

    mock_session.get.assert_called_once_with("https://api.github.com/test", params=None, timeout=(10, 60))
    mock_response.raise_for_status.assert_called_once()
    assert response is None


def testsend_request_get_timeout(mocker):
    mock_session = mocker.Mock()
    mock_session.get.side_effect = requests.Timeout("Read timed out")
    mocker.patch("requests.Session", return_value=mock_session)
    mock_logger = mocker.patch("jacoco_report.utils.github.logger")
    github = GitHub("fake_token")

    response = github.send_request("GET", "https://api.github.com/test")

    mock_session.get.assert_called_once_with("https://api.github.com/test", params=None, timeout=(10, 60))
    mock_logger.error.assert_called_once()
    assert response is None


def testsend_request_post_request_exception(mocker):
    mock_session = mocker.Mock()
    mock_session.post.side_effect = requests.RequestException("Request Exception")
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token")

    response = github.send_request("POST", "https://api.github.com/test", data={"key": "value"})

    mock_session.post.assert_called_once_with(
        "https://api.github.com/test", json={"key": "value"}, params=None, timeout=(10, 60)
    )
    assert response is None


# get_pr_number


def test_get_pr_number(mocker):
    mocker.patch("os.getenv", return_value="fake_event_path")
    mock_open = mocker.patch("builtins.open", mocker.mock_open(read_data='{"pull_request": {"number": 123}}'))
    github = GitHub("fake_token")

    pr_number = github.get_pr_number()

    mock_open.assert_called_once_with("fake_event_path", "r", encoding="utf-8")
    assert pr_number == 123


def test_get_pr_number_no_pr(mocker):
    mocker.patch("os.getenv", return_value="fake_event_path")
    mock_open = mocker.patch("builtins.open", mocker.mock_open(read_data='{"not_a_pull_request": {}}'))
    github = GitHub("fake_token")

    pr_number = github.get_pr_number()

    mock_open.assert_called_once_with("fake_event_path", "r", encoding="utf-8")
    assert pr_number is None


# add_comment


def test_add_comment(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_response = mocker.Mock()
    mock_send_req = mocker.patch.object(GitHub, "send_request", return_value=mock_response)
    github = GitHub("fake_token")

    github.add_comment(1, "Test comment")

    mock_send_req.assert_called_once_with(
        "POST", "https://api.github.com/repos/fake_repo/issues/1/comments", data={"body": "Test comment"}
    )


def test_add_comment_failed_request(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_send_req = mocker.patch.object(GitHub, "send_request", return_value=None)
    github = GitHub("fake_token")

    github.add_comment(1, "Test comment")

    mock_send_req.assert_called_once_with(
        "POST", "https://api.github.com/repos/fake_repo/issues/1/comments", data={"body": "Test comment"}
    )


# get_comments


def test_get_comments(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_response = mocker.Mock()
    mock_response.json.return_value = [{"body": "comment1"}, {"body": "comment2"}]
    mock_send_req = mocker.patch.object(GitHub, "send_request", return_value=mock_response)
    github = GitHub("fake_token")

    comments = github.get_comments(1)

    mock_send_req.assert_called_once_with(
        "GET", "https://api.github.com/repos/fake_repo/issues/1/comments?per_page=100&page=1"
    )
    assert comments == [{"body": "comment1"}, {"body": "comment2"}]


def test_get_comments_pagination(mocker):
    # Arrange
    comments_page_1 = [{"id": i, "body": f"comment {i}"} for i in range(100)]
    comments_page_2 = [{"id": 100, "body": "comment 100"}]

    mock_response_1 = mocker.Mock()
    mock_response_1.json.return_value = comments_page_1
    mock_response_2 = mocker.Mock()
    mock_response_2.json.return_value = comments_page_2

    mocker.patch("jacoco_report.utils.github.GitHub.send_request", side_effect=[mock_response_1, mock_response_2])

    mocker.patch("os.getenv", return_value="owner/repo")

    from jacoco_report.utils.github import GitHub

    gh = GitHub("token")

    # Act
    all_comments = gh.get_comments(pr_number=1, per_page=100)

    # Assert
    assert len(all_comments) == 101
    assert all_comments[0]["id"] == 0
    assert all_comments[-1]["id"] == 100


def test_get_comments_unexpected_format(mocker):
    mock_logger = mocker.patch("jacoco_report.utils.github.logger")
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"body": "comment1"}
    mock_send_req = mocker.patch.object(GitHub, "send_request", return_value=mock_response)
    github = GitHub("fake_token")

    comments = github.get_comments(1)

    assert comments is None
    mock_send_req.assert_called_once_with(
        "GET", "https://api.github.com/repos/fake_repo/issues/1/comments?per_page=100&page=1"
    )

    mock_logger.error.assert_called_once()
    call_args = mock_logger.error.call_args
    assert call_args[0][0] == "Unexpected response format (page %d): %s"


def test_get_comments_page_1_request_fails_returns_none(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mocker.patch.object(GitHub, "send_request", return_value=None)
    github = GitHub("fake_token")

    assert github.get_comments(1) is None


def test_get_comments_page_2_request_fails_returns_none(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    full_page = mocker.Mock()
    full_page.json.return_value = [{"id": i, "body": f"comment {i}"} for i in range(100)]
    mock_send_req = mocker.patch.object(GitHub, "send_request", side_effect=[full_page, None])
    github = GitHub("fake_token")

    assert github.get_comments(1) is None
    assert mock_send_req.call_count == 2


def test_get_comments_non_json_body_returns_none(mocker):
    mock_logger = mocker.patch("jacoco_report.utils.github.logger")
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_response = mocker.Mock()
    mock_response.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
    mocker.patch.object(GitHub, "send_request", return_value=mock_response)
    github = GitHub("fake_token")

    assert github.get_comments(1) is None
    mock_logger.error.assert_called_once()


def test_get_comments_empty_list_returns_empty_list(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_response = mocker.Mock()
    mock_response.json.return_value = []
    mocker.patch.object(GitHub, "send_request", return_value=mock_response)
    github = GitHub("fake_token")

    assert github.get_comments(1) == []


# update_comment


def test_update_comment_success(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"body": "Updated comment"}
    mock_send_req = mocker.patch.object(GitHub, "send_request", return_value=mock_response)
    github = GitHub("fake_token")

    result = github.update_comment(1, "Updated comment")

    mock_send_req.assert_called_once_with(
        "PATCH", "https://api.github.com/repos/fake_repo/issues/comments/1", data={"body": "Updated comment"}
    )
    assert result is True


def test_update_comment_failed_request(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_send_req = mocker.patch.object(GitHub, "send_request", return_value=None)
    github = GitHub("fake_token")

    result = github.update_comment(1, "Updated comment")

    mock_send_req.assert_called_once_with(
        "PATCH", "https://api.github.com/repos/fake_repo/issues/comments/1", data={"body": "Updated comment"}
    )
    assert result is False


def test_update_comment_unexpected_response_format(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"body": "unexpected_value"}
    mock_send_req = mocker.patch.object(GitHub, "send_request", return_value=mock_response)
    github = GitHub("fake_token")

    result = github.update_comment(1, "Updated comment")

    mock_send_req.assert_called_once_with(
        "PATCH", "https://api.github.com/repos/fake_repo/issues/comments/1", data={"body": "Updated comment"}
    )
    assert result is False


# delete pr comment


def test_delete_pr_comment_success(mocker, github):
    mock_response = mocker.Mock()
    mock_response.status_code = 204  # HTTP 204 No Content
    mocker.patch.object(github, "send_request", return_value=mock_response)

    result = github.delete_comment(123)

    github.send_request.assert_called_once_with("DELETE", "https://api.github.com/repos/fake_repo/issues/comments/123")
    assert result is True


def test_delete_pr_comment_failed_request(mocker, github):
    mocker.patch.object(github, "send_request", return_value=None)

    result = github.delete_comment(123)

    github.send_request.assert_called_once_with("DELETE", "https://api.github.com/repos/fake_repo/issues/comments/123")
    assert result is False


def test_delete_pr_comment_unexpected_response(mocker, github):
    mock_response = mocker.Mock()
    mock_response.status_code = 400  # HTTP 400 Bad Request
    mocker.patch.object(github, "send_request", return_value=mock_response)

    result = github.delete_comment(123)

    github.send_request.assert_called_once_with("DELETE", "https://api.github.com/repos/fake_repo/issues/comments/123")
    assert result is False


# ca_bundle

CA_PATH = "/etc/ssl/corp-ca.pem"


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
def test_send_request_passes_ca_bundle_as_verify(method, mocker):
    mock_session = mocker.Mock()
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token", CA_PATH)

    github.send_request(method, "https://api.github.com/test")

    call = getattr(mock_session, method.lower()).call_args
    assert call.args == ("https://api.github.com/test",)
    assert call.kwargs["verify"] == CA_PATH


def _capture_verify_sent_to_adapter(mocker):
    """Patch the transport so the real requests merge logic runs and the verify value that reaches it is recorded."""
    seen = []

    def fake_send(request, **kwargs):
        seen.append(kwargs["verify"])
        response = requests.Response()
        response.status_code = 200
        response.raw = io.BytesIO(b"[]")
        return response

    mocker.patch("requests.adapters.HTTPAdapter.send", side_effect=fake_send)
    return seen


@pytest.mark.parametrize("env_name", ["REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"])
def test_ca_bundle_input_wins_over_env_bundle(env_name, mocker):
    seen = _capture_verify_sent_to_adapter(mocker)
    mocker.patch.dict(os.environ, {env_name: "/env/other.pem"})

    GitHub("fake_token", CA_PATH).send_request("GET", "https://api.github.com/test")

    assert seen == [CA_PATH]


def test_unset_ca_bundle_keeps_requests_ca_bundle_env(mocker):
    seen = _capture_verify_sent_to_adapter(mocker)
    mocker.patch.dict(os.environ, {"REQUESTS_CA_BUNDLE": "/env/corp.pem"})

    GitHub("fake_token").send_request("GET", "https://api.github.com/test")

    assert seen == ["/env/corp.pem"]
