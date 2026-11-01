import io
import logging
import os
import ssl

import pytest
import requests
from urllib3.exceptions import ConnectTimeoutError, ProtocolError, ReadTimeoutError
from urllib3.response import HTTPResponse

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


@pytest.mark.parametrize("body", [b"<html><body>Service unavailable</body></html>", b""], ids=["html", "empty"])
def test_get_comments_real_non_json_response_returns_none(mocker, body):
    """A real 200 response whose body is not JSON makes get_comments return None instead of raising."""
    mocker.patch("os.getenv", return_value="fake_repo")
    response = requests.Response()
    response.status_code = 200
    response._content = body
    mocker.patch.object(GitHub, "send_request", return_value=response)
    github = GitHub("fake_token")

    assert github.get_comments(1) is None


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


@pytest.mark.parametrize(
    ("json_return", "json_error"),
    [
        pytest.param(None, ValueError("Expecting value: line 1 column 1 (char 0)"), id="non-json-body"),
        pytest.param({"id": 1}, None, id="json-without-body"),
        pytest.param(["body"], None, id="json-list"),
        pytest.param(None, None, id="json-null"),
    ],
)
def test_update_comment_unusable_2xx_response_returns_false(mocker, caplog, json_return, json_error):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_response = mocker.Mock()
    mock_response.json.return_value = json_return
    mock_response.json.side_effect = json_error
    mocker.patch.object(GitHub, "send_request", return_value=mock_response)
    github = GitHub("fake_token")

    with caplog.at_level(logging.ERROR, logger="jacoco_report.utils.github"):
        result = github.update_comment(1, "Updated comment")

    assert result is False
    assert "Unexpected response format when updating comment" in caplog.text


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


# retry of transient failures: GET only (#256)

TRANSIENT_FAILURES = [
    pytest.param(429, id="429"),
    pytest.param(500, id="500"),
    pytest.param(502, id="502"),
    pytest.param(503, id="503"),
    pytest.param(504, id="504"),
    pytest.param(ProtocolError("Connection aborted.", ConnectionResetError(54, "reset")), id="connection-reset"),
    pytest.param(ReadTimeoutError(None, "/test", "Read timed out."), id="read-timeout"),
    pytest.param(ConnectTimeoutError("Connect timed out."), id="connect-timeout"),
]


def _fake_transport(mocker, outcomes):
    """
    Patch urllib3 below its retry loop: attempt n gets outcomes[n], a status code, a (status, headers) pair or an
    exception. Returns the methods of the attempts made and the mocked sleep.
    """
    methods = []

    def fake_make_request(conn, method, url, **kwargs):
        outcome = outcomes[len(methods)]
        methods.append(method)
        if isinstance(outcome, Exception):
            raise outcome
        status, headers = outcome if isinstance(outcome, tuple) else (outcome, {})
        return HTTPResponse(
            body=io.BytesIO(b"[]"), status=status, headers=headers, preload_content=False, request_method=method
        )

    mocker.patch("urllib3.connectionpool.HTTPConnectionPool._make_request", side_effect=fake_make_request)
    mocker.patch.dict(os.environ, {"NO_PROXY": "*"})
    return methods, mocker.patch("time.sleep")


@pytest.mark.parametrize("failure", TRANSIENT_FAILURES)
def test_get_retries_transient_failure(failure, mocker):
    methods, _ = _fake_transport(mocker, [failure, 200])

    response = GitHub("fake_token").send_request("GET", "https://api.github.com/test")

    assert response.status_code == 200
    assert methods == ["GET", "GET"]


def test_get_gives_up_after_three_retries_with_exponential_backoff(mocker):
    methods, sleep = _fake_transport(mocker, [502, 502, 502, 502, 200])

    response = GitHub("fake_token").send_request("GET", "https://api.github.com/test")

    assert response is None
    assert methods == ["GET"] * 4
    assert [call.args[0] for call in sleep.call_args_list] == [2, 4]


@pytest.mark.parametrize(
    "retry_after, expected_wait", [pytest.param("7", 7, id="honoured"), pytest.param("3600", 60, id="capped")]
)
def test_get_waits_for_retry_after(retry_after, expected_wait, mocker):
    methods, sleep = _fake_transport(mocker, [(429, {"Retry-After": retry_after}), 200])

    response = GitHub("fake_token").send_request("GET", "https://api.github.com/test")

    assert response.status_code == 200
    assert methods == ["GET", "GET"]
    sleep.assert_called_once_with(expected_wait)


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
@pytest.mark.parametrize(
    "failure", TRANSIENT_FAILURES + [pytest.param(ssl.SSLError("bad record mac"), id="ssl-error-after-send")]
)
def test_write_is_sent_once_on_failure(method, failure, mocker):
    methods, _ = _fake_transport(mocker, [failure, 200])

    response = GitHub("fake_token").send_request(method, "https://api.github.com/test", data={"body": "x"})

    assert response is None
    assert methods == [method]


def test_each_retry_logs_a_warning(mocker, caplog):
    _fake_transport(mocker, [502, ProtocolError("Connection aborted."), 200])
    caplog.set_level(logging.WARNING, logger="jacoco_report.utils.github")

    GitHub("fake_token").send_request("GET", "https://api.github.com/test")

    warnings = [
        r.getMessage()
        for r in caplog.records
        if r.name == "jacoco_report.utils.github" and r.levelno == logging.WARNING
    ]
    assert len(warnings) == 2
    assert "GET /test" in warnings[0] and "502" in warnings[0] and "2 retries left" in warnings[0]
    assert "Connection aborted." in warnings[1] and "1 retries left" in warnings[1]


@pytest.mark.parametrize("url", ["https://api.github.com/test", "http://ghes.example.com/api/v3/test"])
def test_session_pins_retry_config(url, mocker):
    adapters = []

    def fake_send(adapter, request, **kwargs):
        adapters.append(adapter)
        response = requests.Response()
        response.status_code = 200
        return response

    mocker.patch("requests.adapters.HTTPAdapter.send", autospec=True, side_effect=fake_send)

    GitHub("fake_token").send_request("GET", url)

    retry = adapters[0].max_retries
    assert retry.total == 3
    assert retry.backoff_factor == 1
    assert set(retry.status_forcelist) == {429, 500, 502, 503, 504}
    assert set(retry.allowed_methods) == {"GET"}
    assert retry.respect_retry_after_header is True
    assert retry.retry_after_max == 60
    assert retry.raise_on_status is False
