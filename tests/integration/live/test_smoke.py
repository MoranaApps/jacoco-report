"""
Live integration smoke tests for the jacoco-report GitHub Action.

These tests make real GitHub API calls and are skipped unless all of the
following environment variables are present at module import time:

    GITHUB_TOKEN         — a valid GitHub token with PR write access
    GITHUB_REPOSITORY    — e.g. ``owner/repo``
    GITHUB_REF           — e.g. ``refs/pull/42/merge``

In CI the ``live-integration-test`` job injects ``GITHUB_TOKEN`` via
``secrets.GITHUB_TOKEN`` and runs only for same-repository pull requests
(the ``if:`` guard prevents fork PRs from accessing the secret).
"""

from __future__ import annotations

import os
import re
import uuid
import warnings
from collections.abc import Generator

import pytest
import requests

from tests.integration.helpers import TEST_PROJECT_GLOB, capture_run, make_env_base

# ---------------------------------------------------------------------------
# Module-level constants — captured before any capture_run call can clear them.
# ---------------------------------------------------------------------------
_TOKEN: str = os.environ.get("GITHUB_TOKEN", "")
_REPO: str = os.environ.get("GITHUB_REPOSITORY", "")
_REF: str = os.environ.get("GITHUB_REF", "")

pytestmark = pytest.mark.skipif(
    not _TOKEN
    or not _REPO
    or not re.fullmatch(r"refs/pull/\d+/merge", _REF),
    reason=(
        "Live tests require GITHUB_TOKEN, GITHUB_REPOSITORY, and "
        "GITHUB_REF in refs/pull/<n>/merge format"
    ),
)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _pr_number() -> int:
    """Extract the PR number from GITHUB_REF."""
    match = re.fullmatch(r"refs/pull/(\d+)/merge", _REF)
    assert match, f"Cannot extract PR number from GITHUB_REF={_REF!r}"
    return int(match.group(1))


def _api_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def _live_env(**overrides: str) -> dict[str, str]:
    """Return a full env dict for a live ``capture_run`` invocation."""
    env = make_env_base(
        INPUT_TOKEN=_TOKEN,
        INPUT_PR_NUMBER=str(_pr_number()),
        GITHUB_REPOSITORY=_REPO,
        GITHUB_REF=_REF,
        GITHUB_EVENT_NAME="pull_request",
    )
    env.update(overrides)
    return env


def _fetch_all_comments(pr_number: int) -> list[dict]:
    """Retrieve every comment on the PR, following GitHub pagination."""
    all_comments: list[dict] = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{_REPO}/issues/{pr_number}/comments"
        resp = requests.get(
            url,
            headers=_api_headers(),
            params={"per_page": 100, "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        batch: list[dict] = resp.json()
        all_comments.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return all_comments


def _delete_comment(comment_id: int) -> None:
    """Delete a single PR comment by ID."""
    url = f"https://api.github.com/repos/{_REPO}/issues/comments/{comment_id}"
    resp = requests.delete(url, headers=_api_headers(), timeout=30)
    assert resp.status_code == 204, (
        f"Delete comment {comment_id} returned HTTP {resp.status_code}"
    )


def _is_comment_write_forbidden(output: str) -> bool:
    """Return whether output indicates 403 forbidden on PR issue-comments API writes."""
    normalized = output.lower()
    return (
        "403" in normalized
        and "forbidden" in normalized
        and "/issues/" in normalized
        and "/comments" in normalized
    )


@pytest.fixture
def cleanup_comments() -> Generator[list[int], None, None]:
    """Yield a list; append comment IDs to it and they will be deleted on teardown."""
    ids: list[int] = []
    yield ids
    cleanup_failures: list[str] = []
    for comment_id in ids:
        try:
            _delete_comment(comment_id)
        except (requests.RequestException, AssertionError) as exc:
            cleanup_failures.append(f"comment_id={comment_id}: {exc}")

    if cleanup_failures:
        warnings.warn(
            "Live test comment cleanup had failures:\n" + "\n".join(cleanup_failures),
            RuntimeWarning,
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_comment_creation(cleanup_comments: list[int]) -> None:
    """Action posts exactly one comment on the live PR and exits cleanly.

    Uses ``comment-level=minimal`` and zero thresholds so the run succeeds
    regardless of the actual coverage data in the test fixtures.
    """
    pr_number = _pr_number()
    before_ids = {c["id"] for c in _fetch_all_comments(pr_number)}
    marker = f"jacoco-live-smoke-create-{uuid.uuid4().hex}"

    env = _live_env(
        INPUT_PATHS=TEST_PROJECT_GLOB,
        INPUT_TITLE=marker,
        INPUT_COMMENT_LEVEL="minimal",
        INPUT_SKIP_UNCHANGED="false",
        INPUT_GLOBAL_THRESHOLDS="0.0*0.0*0.0",
    )
    result = capture_run(env)

    combined = result.stdout + result.stderr
    if _is_comment_write_forbidden(combined):
        pytest.skip(
            "Skipping live comment-creation check: token cannot write PR issue comments "
            "in this workflow context (HTTP 403)."
        )

    assert result.exit_code == 0, (
        f"Action exited with code {result.exit_code}.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    after_comments = _fetch_all_comments(pr_number)
    marker_comments = [c for c in after_comments if marker in c.get("body", "")]
    new_marker_comments = [c for c in marker_comments if c["id"] not in before_ids]
    assert len(new_marker_comments) == 1, (
        "Expected exactly one newly-created marker comment, "
        f"found {len(new_marker_comments)}.\n"
        f"stdout:\n{result.stdout}"
    )
    cleanup_comments.append(new_marker_comments[0]["id"])


def test_pagination_handling(cleanup_comments: list[int]) -> None:
    """``get_comments`` retrieves all pages when ``per_page`` forces multiple round trips.

    Three marker comments are posted directly via the API, then retrieved
    through the GitHub client with ``per_page=2`` to guarantee at least two
    API round trips.  All three must appear in the retrieved set.
    """
    pr_number = _pr_number()

    marker = f"jacoco-smoke-pagination-{uuid.uuid4().hex}"
    posted_ids: list[int] = []
    for i in range(3):
        url = f"https://api.github.com/repos/{_REPO}/issues/{pr_number}/comments"
        resp = requests.post(
            url,
            headers=_api_headers(),
            json={"body": f"{marker} #{i}"},
            timeout=30,
        )
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            if resp.status_code == 403:
                pytest.skip(
                    "Skipping live pagination check: token cannot write PR issue comments "
                    "in this workflow context (HTTP 403)."
                )
            raise
        comment_id = resp.json()["id"]
        posted_ids.append(comment_id)
        cleanup_comments.append(comment_id)

    from jacoco_report.utils.github import GitHub  # local import avoids module-level side effects

    saved_repo = os.environ.get("GITHUB_REPOSITORY")
    os.environ["GITHUB_REPOSITORY"] = _REPO
    try:
        gh = GitHub(_TOKEN)
        retrieved = gh.get_comments(pr_number, per_page=2)
    finally:
        if saved_repo is not None:
            os.environ["GITHUB_REPOSITORY"] = saved_repo
        else:
            os.environ.pop("GITHUB_REPOSITORY", None)

    posted_bodies = {f"{marker} #{i}" for i in range(3)}
    retrieved_bodies = {c["body"] for c in retrieved}
    assert posted_bodies.issubset(retrieved_bodies), (
        f"Pagination missed posted comments.\n"
        f"Expected to find: {posted_bodies}\n"
        f"Retrieved sample: {list(retrieved_bodies)[:10]}"
    )


def test_invalid_token_produces_clear_error() -> None:
    """Action exits non-zero and logs a clear error when the token is invalid.

    The token is syntactically valid (passes ``is_valid_github_token``) so
    the action proceeds past input validation and actually contacts the API,
    where the 401 response triggers the error path.
    """
    env = _live_env(
        INPUT_TOKEN="ghs_" + "z" * 36,
        INPUT_PATHS=TEST_PROJECT_GLOB,
        INPUT_COMMENT_LEVEL="minimal",
        INPUT_GLOBAL_THRESHOLDS="0.0*0.0*0.0",
    )
    result = capture_run(env)

    assert result.exit_code != 0, (
        "Expected a non-zero exit code for an invalid token, got 0.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    normalized = combined.lower()
    assert (
        "http error occurred" in normalized
        and (
            "401" in normalized
            or "unauthorized" in normalized
            or "bad credentials" in normalized
        )
    ), (
        "Expected an explicit authentication failure indicator for an invalid token "
        "(HTTP 401 / unauthorized / bad credentials).\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
