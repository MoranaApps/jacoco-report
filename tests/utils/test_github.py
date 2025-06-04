import requests

from jacoco_report.utils.github import GitHub


# get_pr_changed_files

def test_get_pr_changed_files(mocker):
    mocker.patch("os.getenv", side_effect=lambda key: "fake_repo" if key == "GITHUB_REPOSITORY" else "refs/pull/1/merge")
    mock_response = mocker.Mock()
    mock_response.json.return_value = [{"filename": "file1.py"}, {"filename": "file2.py"}]
    mocker.patch.object(GitHub, "_send_request", return_value=mock_response)
    github = GitHub("fake_token")

    files = github.get_pr_changed_files()

    assert files == ["file1.py", "file2.py"]


def test_get_pr_changed_files_none_response(mocker):
    mocker.patch("os.getenv", side_effect=lambda key: "fake_repo" if key == "GITHUB_REPOSITORY" else "refs/pull/1/merge")
    mocker.patch.object(GitHub, "_send_request", return_value=None)
    github = GitHub("fake_token")

    files = github.get_pr_changed_files()

    assert files is None


# _send_request

def test_send_request_get(mocker):
    mock_session = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_session.get.return_value = mock_response
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token")

    response = github._send_request("GET", "https://api.github.com/test")

    mock_session.get.assert_called_once_with("https://api.github.com/test", params=None)
    mock_response.raise_for_status.assert_called_once()
    assert response == mock_response


def test_send_request_post(mocker):
    mock_session = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_session.post.return_value = mock_response
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token")

    response = github._send_request("POST", "https://api.github.com/test", data={"key": "value"})

    mock_session.post.assert_called_once_with("https://api.github.com/test", json={"key": "value"}, params=None)
    mock_response.raise_for_status.assert_called_once()
    assert response == mock_response


def test_send_request_patch(mocker):
    mock_session = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_session.patch.return_value = mock_response
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token")

    response = github._send_request("PATCH", "https://api.github.com/test", data={"key": "value"})

    mock_session.patch.assert_called_once_with("https://api.github.com/test", json={"key": "value"}, params=None)
    mock_response.raise_for_status.assert_called_once()
    assert response == mock_response


def test_send_request_delete(mocker):
    mock_session = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_session.delete.return_value = mock_response
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token")

    response = github._send_request("DELETE", "https://api.github.com/test", data={"key": "value"})

    mock_session.delete.assert_called_once_with("https://api.github.com/test", json={"key": "value"}, params=None)
    mock_response.raise_for_status.assert_called_once()
    assert response == mock_response


def test_send_request_unsupported_method(mocker):
    mock_logger = mocker.patch("jacoco_report.utils.github.logger")
    github = GitHub("fake_token")

    response = github._send_request("PUT", "https://api.github.com/test")

    mock_logger.error.assert_called_once_with("Unsupported HTTP method: %s.", "PUT")
    assert response is None


def test_send_request_get_http_error(mocker):
    mock_session = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("HTTP Error")
    mock_session.get.return_value = mock_response
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token")

    response = github._send_request("GET", "https://api.github.com/test")

    mock_session.get.assert_called_once_with("https://api.github.com/test", params=None)
    mock_response.raise_for_status.assert_called_once()
    assert response is None


def test_send_request_post_request_exception(mocker):
    mock_session = mocker.Mock()
    mock_session.post.side_effect = requests.RequestException("Request Exception")
    mocker.patch("requests.Session", return_value=mock_session)
    github = GitHub("fake_token")

    response = github._send_request("POST", "https://api.github.com/test", data={"key": "value"})

    mock_session.post.assert_called_once_with("https://api.github.com/test", json={"key": "value"}, params=None)
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
    mock_send_req = mocker.patch.object(GitHub, "_send_request", return_value=mock_response)
    github = GitHub("fake_token")

    github.add_comment(1, "Test comment")

    mock_send_req.assert_called_once_with("POST", "https://api.github.com/repos/fake_repo/issues/1/comments", data={"body": "Test comment"})


def test_add_comment_failed_request(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_send_req = mocker.patch.object(GitHub, "_send_request", return_value=None)
    github = GitHub("fake_token")

    github.add_comment(1, "Test comment")

    mock_send_req.assert_called_once_with("POST", "https://api.github.com/repos/fake_repo/issues/1/comments", data={"body": "Test comment"})


# get_comments

def test_get_comments(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_response = mocker.Mock()
    mock_response.json.return_value = [{"body": "comment1"}, {"body": "comment2"}]
    mock_send_req = mocker.patch.object(GitHub, "_send_request", return_value=mock_response)
    github = GitHub("fake_token")

    comments = github.get_comments(1)

    mock_send_req.assert_called_once_with("GET", "https://api.github.com/repos/fake_repo/issues/1/comments?per_page=100&page=1")
    assert comments == [{"body": "comment1"}, {"body": "comment2"}]


def test_get_comments_pagination(mocker):
    # Arrange
    comments_page_1 = [{"id": i, "body": f"comment {i}"} for i in range(100)]
    comments_page_2 = [{"id": 100, "body": "comment 100"}]

    mock_response_1 = mocker.Mock()
    mock_response_1.json.return_value = comments_page_1
    mock_response_2 = mocker.Mock()
    mock_response_2.json.return_value = comments_page_2

    mocker.patch(
        "jacoco_report.utils.github.GitHub._send_request",
        side_effect=[mock_response_1, mock_response_2]
    )

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
    mock_send_req = mocker.patch.object(GitHub, "_send_request", return_value=mock_response)
    github = GitHub("fake_token")

    comments = github.get_comments(1)

    assert comments == []
    mock_send_req.assert_called_once_with("GET", "https://api.github.com/repos/fake_repo/issues/1/comments?per_page=100&page=1")

    mock_logger.error.assert_called_once()
    call_args = mock_logger.error.call_args
    assert call_args[0][0] == "Unexpected response format (page %d): %s"


# update_comment

def test_update_comment_success(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"body": "Updated comment"}
    mock_send_req = mocker.patch.object(GitHub, "_send_request", return_value=mock_response)
    github = GitHub("fake_token")

    result = github.update_comment(1, "Updated comment")

    mock_send_req.assert_called_once_with("PATCH", "https://api.github.com/repos/fake_repo/issues/comments/1", data={"body": "Updated comment"})
    assert result is True

def test_update_comment_failed_request(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_send_req = mocker.patch.object(GitHub, "_send_request", return_value=None)
    github = GitHub("fake_token")

    result = github.update_comment(1, "Updated comment")

    mock_send_req.assert_called_once_with("PATCH", "https://api.github.com/repos/fake_repo/issues/comments/1", data={"body": "Updated comment"})
    assert result is False

def test_update_comment_unexpected_response_format(mocker):
    mocker.patch("os.getenv", return_value="fake_repo")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"body": "unexpected_value"}
    mock_send_req = mocker.patch.object(GitHub, "_send_request", return_value=mock_response)
    github = GitHub("fake_token")

    result = github.update_comment(1, "Updated comment")

    mock_send_req.assert_called_once_with("PATCH", "https://api.github.com/repos/fake_repo/issues/comments/1", data={"body": "Updated comment"})
    assert result is False


# delete pr comment

def test_delete_pr_comment_success(mocker, github):
    mock_response = mocker.Mock()
    mock_response.status_code = 204  # HTTP 204 No Content
    mocker.patch.object(github, "_send_request", return_value=mock_response)

    result = github.delete_comment(123)

    github._send_request.assert_called_once_with("DELETE", "https://api.github.com/repos/fake_repo/issues/comments/123")
    assert result is True

def test_delete_pr_comment_failed_request(mocker, github):
    mocker.patch.object(github, "_send_request", return_value=None)

    result = github.delete_comment(123)

    github._send_request.assert_called_once_with("DELETE", "https://api.github.com/repos/fake_repo/issues/comments/123")
    assert result is False

def test_delete_pr_comment_unexpected_response(mocker, github):
    mock_response = mocker.Mock()
    mock_response.status_code = 400  # HTTP 400 Bad Request
    mocker.patch.object(github, "_send_request", return_value=mock_response)

    result = github.delete_comment(123)

    github._send_request.assert_called_once_with("DELETE", "https://api.github.com/repos/fake_repo/issues/comments/123")
    assert result is False
