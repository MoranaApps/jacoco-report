"""
This module provides a class to interact with the GitHub API.
"""

import json
import logging
import os
import re

from types import TracebackType
from typing import Any, Optional, Self
import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.connectionpool import ConnectionPool
from urllib3.response import BaseHTTPResponse
from urllib3.util.retry import Retry

from jacoco_report.utils.constants import (
    DEFAULT_GITHUB_API_URL,
    DEFAULT_GITHUB_SERVER_URL,
    GITHUB_API_URL,
    GITHUB_SERVER_URL,
)

logger = logging.getLogger(__name__)

# (connect, read) seconds for every GitHub API call
REQUEST_TIMEOUT = (10, 60)

# Static hints logged after "HTTP error occurred" for the statuses that usually mean a token problem
HINT_TOKEN_INVALID = "Hint: the GitHub token is invalid or expired. Check the `token` input."
HINT_RATE_LIMITED = (
    "Hint: the GitHub API rate limit is exhausted (X-RateLimit-Remaining: 0). Re-run the job after the limit resets."
)
HINT_FORBIDDEN = (
    "Hint: the token lacks a permission. The job needs `contents: read`, `pull-requests: read` and `issues: write`. "
    "On fork PRs and Dependabot PRs the token is read-only, so the comment can't be posted."
)
HINT_NOT_FOUND = (
    "Hint: the token can't access this repository or pull request, e.g. a private repository it can't see, "
    "or GITHUB_API_URL points to the wrong server on GitHub Enterprise Server."
)


def _hint_for_http_error(http_err: requests.HTTPError) -> Optional[str]:
    """Returns the static hint for a 401, 403 or 404 response, or None (no response, or any other status)."""
    response = http_err.response
    if response is None:
        return None
    if response.status_code == 401:
        return HINT_TOKEN_INVALID
    if response.status_code == 403:
        return HINT_RATE_LIMITED if response.headers.get("X-RateLimit-Remaining") == "0" else HINT_FORBIDDEN
    if response.status_code == 404:
        return HINT_NOT_FOUND
    return None


def get_api_url() -> str:
    """REST API base URL from the runner's GITHUB_API_URL (not an action input); github.com's when unset."""
    return os.getenv(GITHUB_API_URL) or DEFAULT_GITHUB_API_URL


def get_server_url() -> str:
    """Server base URL from the runner's GITHUB_SERVER_URL (not an action input); github.com's when unset."""
    return os.getenv(GITHUB_SERVER_URL) or DEFAULT_GITHUB_SERVER_URL


class _GetOnlyRetry(Retry):
    """
    Retries GET requests only, and logs each retry.

    allowed_methods alone isn't enough: urllib3 checks it for read errors and statuses only, and repeats connect and
    other errors (e.g. an SSL error after the request was sent) for any method. A repeated POST can post the comment
    twice, so any other method fails as with requests' default Retry(0, read=False).
    """

    def increment(
        self,
        method: Optional[str] = None,
        url: Optional[str] = None,
        response: Optional[BaseHTTPResponse] = None,
        error: Optional[Exception] = None,
        _pool: Optional[ConnectionPool] = None,
        _stacktrace: Optional[TracebackType] = None,
    ) -> Self:
        if method is None or not self._is_method_retryable(method):
            # Always raises: total=0 is exhausted on the first failure
            return Retry.increment(self.new(total=0, read=False), method, url, response, error, _pool, _stacktrace)

        new_retry = super().increment(method, url, response, error, _pool, _stacktrace)
        logger.warning(
            "GitHub API %s %s failed: %s. Retrying, %d retries left.",
            method,
            url,
            response.status if response else error,
            new_retry.total,
        )
        return new_retry


class GitHub:
    """
    A class representing the GitHub API.
    """

    def __init__(self, token: str, ca_bundle: str = "", api_url: str = DEFAULT_GITHUB_API_URL):
        """
        Initializes the GitHub API object.

        Parameters:
            token (str): The GitHub token.
            ca_bundle (str): Path to a PEM CA bundle for TLS verification. Empty means the requests default.
            api_url (str): Base URL of the REST API, e.g. "https://ghes.example.com/api/v3".

        Returns:
            None
        """
        self.__token = token
        self.__session: Optional[Session] = None
        self.__gh_url = api_url
        # Passed per request, not as session.verify: requests lets REQUESTS_CA_BUNDLE/CURL_CA_BUNDLE override
        # session.verify, and the action input must win.
        self.__request_kwargs: dict[str, Any] = {"verify": ca_bundle} if ca_bundle else {}

    def __initialize_request_session(self) -> requests.Session:
        """
        Initializes the request Session and updates the headers.

        Returns:
            requests.Session: The initialized request Session.
        """

        self.__session = requests.Session()
        headers = {
            "Authorization": f"Bearer {self.__token}",
        }
        self.__session.headers.update(headers)

        # Transient failures on reads; worst-case duration is in CONTEXT.md
        retry = _GetOnlyRetry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods={"GET"},
            raise_on_status=False,
            retry_after_max=60,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.__session.mount("https://", adapter)
        self.__session.mount("http://", adapter)

        return self.__session

    def get_pr_changed_files(self) -> Optional[list[str]]:
        """
        Gets the list of changed files in the pull request.

        Returns:
            list[str]: The list of changed files in the pull request.
        """
        repo = os.getenv("GITHUB_REPOSITORY")
        github_ref = os.getenv("GITHUB_REF")
        logger.debug("GitHub - Repository: %s", repo)
        logger.debug("GitHub - ref: %s", github_ref)

        # Extract the PR number from the GITHUB_REF if it matches the PR ref pattern
        pr_number = None
        if github_ref and github_ref.startswith("refs/pull/"):
            match = re.match(r"refs/pull/(\d+)/merge", github_ref)
            if match:
                pr_number = match.group(1)
        logger.debug("GitHub - PR number: %s", pr_number)

        if not pr_number:
            logger.error("Failed to extract PR number from GitHub ref.")
            return None

        per_page = 100  # Maximum GitHub allows
        page = 1
        file_list = []

        while True:
            api_url = f"{self.__gh_url}/repos/{repo}/pulls/{pr_number}/files"
            params = {"per_page": per_page, "page": page}
            logger.debug("GitHub - URL: %s, Page: %d", api_url, page)

            response = self.send_request("GET", api_url, params=params)
            if response is None:
                logger.error("Failed to get the list of changed files.")
                return None

            page_files = response.json()
            if not page_files:
                break

            for file_info in page_files:
                filename = file_info.get("filename")
                if filename:
                    file_list.append(filename)

            if len(page_files) < per_page:
                break  # No more pages
            page += 1

        logger.info("List of changed files in PR: %s", file_list)
        return file_list

    def send_request(
        self, method: str, url: str, data: Optional[dict] = None, params: Optional[dict] = None
    ) -> Optional[requests.Response]:
        """
        Sends a request to the GitHub API.

        Parameters:
            method (str): The HTTP method to use.
            url (str): The URL of the API endpoint.
            data (dict): The data to send in the request (as json).
            params (dict): The parameters to send in the request.

        Returns:
            Optional[requests.Response]: The response from the API.
        """
        try:
            if self.__session is None:
                self.__session = self.__initialize_request_session()

            session = self.__session
            response = None
            # Fetch the response from the API
            if method == "GET":
                response = session.get(url, params=params, timeout=REQUEST_TIMEOUT, **self.__request_kwargs)
                response.raise_for_status()
            elif method == "POST":
                response = session.post(url, params=params, json=data, timeout=REQUEST_TIMEOUT, **self.__request_kwargs)
                response.raise_for_status()
            elif method == "PATCH":
                response = session.patch(
                    url, params=params, json=data, timeout=REQUEST_TIMEOUT, **self.__request_kwargs
                )
                response.raise_for_status()
            elif method == "DELETE":
                response = session.delete(
                    url, params=params, json=data, timeout=REQUEST_TIMEOUT, **self.__request_kwargs
                )
                response.raise_for_status()
            else:
                logger.error("Unsupported HTTP method: %s.", method)

            return response

        # Specific error handling for HTTP errors
        except requests.HTTPError as http_err:
            logger.error("HTTP error occurred: %s.", http_err, exc_info=True)
            hint = _hint_for_http_error(http_err)
            if hint:
                logger.error(hint)

        except requests.RequestException as req_err:
            logger.error("An error occurred: %s.", req_err, exc_info=True)

        return None

    def get_pr_number(self) -> Optional[int]:
        """
        Gets the PR number from the environment variables.

        Returns:
            Optional[int]: The PR number.
        """
        # try to detect pr number from local variable
        res = self._get_pr_number_from_gh_event_path_variable()
        if res:
            return res

        logger.error("Failed to get the PR number.")
        return None

    def _get_pr_number_from_gh_event_path_variable(self) -> Optional[int]:
        """
        Gets the PR number from the GitHub event payload file.

        Returns:
            Optional[int]: The PR number
        """
        # Path to the event payload file
        event_path = os.getenv("GITHUB_EVENT_PATH")
        if event_path is None:
            logger.error("GITHUB_EVENT_PATH environment variable is not set.")
            return None

        # Read and parse the event payload
        with open(event_path, "r", encoding="utf-8") as f:
            event_data = json.load(f)

        # Check if the event is a pull request and get the PR number
        if "pull_request" in event_data:
            pr_number = event_data["pull_request"]["number"]
            return int(pr_number)

        logger.error("This event is not a pull request.")
        return None

    def add_comment(self, pr_number: int, body: str) -> bool:
        """
        Adds a comment to the pull request.

        Parameters:
            pr_number (int): The PR number.
            body (str): The comment body.

        Returns:
            None
        """
        repo = os.getenv("GITHUB_REPOSITORY")

        # GitHub API endpoint for PR comments
        api_url = f"{self.__gh_url}/repos/{repo}/issues/{pr_number}/comments"
        logger.debug("GitHub - URL: %s", api_url)

        # Prepare the comment data
        comment_data = {"body": body}

        response = self.send_request("POST", api_url, data=comment_data)
        if response is None:
            logger.error("Failed to add a comment to the PR.")
            return False

        logger.info("Comment added to the PR.")
        return True

    def get_comments(self, pr_number: int, per_page: int = 100) -> Optional[list[dict]]:
        """
        Retrieves all comments from the pull request.

        Parameters:
            pr_number (int): The PR number.
            per_page (int): The number of comments to retrieve per page.

        Returns:
            Optional[list]: All comments from the PR, or None if any page could not be read
            (request failed or unexpected format). None means the read is incomplete, not empty.
        """
        repo = os.getenv("GITHUB_REPOSITORY")
        all_comments = []
        page = 1

        while True:

            # GitHub API endpoint for PR comments
            api_url = f"{self.__gh_url}/repos/{repo}/issues/{pr_number}/comments" f"?per_page={per_page}&page={page}"
            logger.debug("GitHub - URL (page %d): %s", page, api_url)

            response = self.send_request("GET", api_url)
            if response is None:
                logger.error("Failed to get PR comments.")
                return None

            try:
                comments = response.json()
            except ValueError:
                logger.error("Unexpected response format (page %d): body is not JSON.", page)
                return None
            if not isinstance(comments, list):
                logger.error("Unexpected response format (page %d): %s", page, response)
                return None

            logger.info("Retrieved %d comments from page %d.", len(comments), page)
            all_comments.extend(comments)

            if len(comments) < per_page:
                # No more pages
                break
            page += 1

        logger.info("Retrieved %d comments from the PR.", len(all_comments))
        return all_comments

    def update_comment(self, comment_id: int, pr_body: str) -> bool:
        """
        Updates an existing comment on the pull request.

        Parameters:
            comment_id (int): The ID of the comment.
            pr_body (str): The updated comment body.

        Returns:
            bool: True if the comment was updated successfully, False otherwise.
        """
        repo = os.getenv("GITHUB_REPOSITORY")

        # GitHub API endpoint for updating a comment
        api_url = f"{self.__gh_url}/repos/{repo}/issues/comments/{comment_id}"
        logger.debug("GitHub - Update Comment URL: %s", api_url)

        payload = {"body": pr_body}

        response = self.send_request("PATCH", api_url, data=payload)

        if response is None:
            logger.error("Failed to update the comment with ID %d.", comment_id)
            return False

        try:
            updated_body = response.json()["body"]
        except (ValueError, KeyError, TypeError):
            logger.error(
                "Unexpected response format when updating comment %d: body is not a JSON object with body.",
                comment_id,
            )
            return False

        if updated_body == pr_body:
            logger.info("Successfully updated the comment with ID %d.", comment_id)
            return True

        logger.error("Unexpected response format when updating comment: %s", response)
        return False

    def delete_comment(self, comment_id: int) -> bool:
        """
        Deletes a comment from the pull request.

        Parameters:
            comment_id (int): The ID of the comment.

        Returns:
            bool: True if the comment was deleted successfully, False otherwise.
        """
        repo = os.getenv("GITHUB_REPOSITORY")

        # GitHub API endpoint for deleting a comment
        api_url = f"{self.__gh_url}/repos/{repo}/issues/comments/{comment_id}"
        logger.debug("GitHub - Delete Comment URL: %s", api_url)

        response = self.send_request("DELETE", api_url)

        if response is None or response.status_code != 204:
            logger.error("Failed to delete the comment with ID %d.", comment_id)
            return False

        logger.info("Successfully deleted the comment with ID %d.", comment_id)
        return True
