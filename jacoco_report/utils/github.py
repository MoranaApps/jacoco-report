"""
This module provides a class to interact with the GitHub API.
"""

import json
import logging
import os
import re

from typing import Optional
import requests
from requests import Session

logger = logging.getLogger(__name__)


class GitHub:
    """
    A class representing the GitHub API.
    """

    def __init__(self, token: str):
        """
        Initializes the GitHub API object.

        Parameters:
            token (str): The GitHub token.

        Returns:
            None
        """
        self.__token = token
        self.__session: Optional[Session] = None
        self.__gh_url = "https://api.github.com"

    def __initialize_request_session(self) -> requests.Session:
        """
        Initializes the request Session and updates the headers.

        Returns:
            requests.Session: The initialized request Session.
        """

        self.__session: Optional[Session] = requests.Session()  # type: ignore[no-redef]
        headers = {
            "Authorization": f"Bearer {self.__token}",
            "Host": "api.github.com",
        }
        self.__session.headers.update(headers)

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

            response = self._send_request("GET", api_url, params=params)
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

    def _send_request(
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
                self.__initialize_request_session()

            response = None
            # Fetch the response from the API
            if method == "GET":
                response = self.__session.get(url, params=params)  # type: ignore[union-attr]
                response.raise_for_status()
            elif method == "POST":
                response = self.__session.post(url, params=params, json=data)  # type: ignore[union-attr]
                response.raise_for_status()
            elif method == "PATCH":
                response = self.__session.patch(url, params=params, json=data)  # type: ignore[union-attr]
                response.raise_for_status()
            elif method == "DELETE":
                response = self.__session.delete(url, params=params, json=data)  # type: ignore[union-attr]
                response.raise_for_status()
            else:
                logger.error("Unsupported HTTP method: %s.", method)

            return response

        # Specific error handling for HTTP errors
        except requests.HTTPError as http_err:
            logger.error("HTTP error occurred: %s.", http_err, exc_info=True)

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

        # Read and parse the event payload
        with open(event_path, "r", encoding="utf-8") as f:  # type: ignore[arg-type]
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

        response = self._send_request("POST", api_url, data=comment_data)
        if response is None:
            logger.error("Failed to add a comment to the PR.")
            return False

        logger.info("Comment added to the PR.")
        return True

    def get_comments(self, pr_number: int) -> list:
        """
        Retrieves all comments from the pull request.

        Parameters:
            pr_number (int): The PR number.

        Returns:
            list: A list of comments from the PR.
        """
        repo = os.getenv("GITHUB_REPOSITORY")

        # GitHub API endpoint for PR comments
        api_url = f"{self.__gh_url}/repos/{repo}/issues/{pr_number}/comments"
        logger.debug("GitHub - URL: %s", api_url)

        response = self._send_request("GET", api_url)
        if response is None:
            logger.error("Failed to get PR comments.")
            return []

        res: list = response.json()
        if not isinstance(res, list):
            logger.error("Unexpected response format when retrieving PR comments: %s", response)
            return []

        logger.info("Retrieved %d comments from the PR.", len(res))
        return res

    def update_comment(self, comment_id, pr_body) -> bool:
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

        response = self._send_request("PATCH", api_url, data=payload)

        if response is None:
            logger.error("Failed to update the comment with ID %d.", comment_id)
            return False

        if response.json()["body"] == pr_body:
            logger.info("Successfully updated the comment with ID %d.", comment_id)
            return True

        logger.error("Unexpected response format when updating comment: %s", response)
        return False

    def delete_comment(self, comment_id) -> bool:
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

        response = self._send_request("DELETE", api_url)

        if response is None or response.status_code != 204:
            logger.error("Failed to delete the comment with ID %d.", comment_id)
            return False

        logger.info("Successfully deleted the comment with ID %d.", comment_id)
        return True
