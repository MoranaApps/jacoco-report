"""
Checking that the baseline reports were built from the commit the caller expects.

The check reads a metadata JSON file shipped with the baseline. It never fails the run: a result that does not
verify is reported, and the gate that depends on it decides what to do.
"""

import json
import re
from typing import Any, Optional

from jacoco_report.utils.constants import COMMIT_SHA_REGEX

UNVERIFIED_BASELINE_NOTE = (
    "⚠️ **Unverified baseline:** the baseline could not be verified against `baseline-sha`, so the Δ values are "
    "informational only and `no-decrease` does not fail on them. See the workflow warning for the reason."
)

_WARNING_SUFFIX = ". The Δ against it is informational, and 'no-decrease' skips it."

# The file comes from a downloaded artifact: a bound keeps a huge file from flooding memory and the log.
_MAX_METADATA_CHARACTERS = 65536

_COMMIT_SHA_PATTERN = re.compile(COMMIT_SHA_REGEX)


def unverified_baseline_reason(expected_sha: str, metadata_path: str) -> Optional[str]:
    """
    Check the baseline metadata file against the expected commit SHA.

    @param expected_sha: The baseline-sha input, stripped and validated by ActionInputs.
    @param metadata_path: The baseline-metadata-path input, stripped.

    @return: None when the file names expected_sha (case-insensitive), else the full warning text giving the reason.
    """
    data, reason = _read_metadata(metadata_path)
    if reason is None:
        reason = _sha_reason(data, expected_sha)
    if reason is None:
        return None
    return f"Unverified baseline: metadata file '{metadata_path}' {reason}{_WARNING_SUFFIX}"


def _read_metadata(metadata_path: str) -> tuple[Any, Optional[str]]:
    """Return (the parsed JSON, None), or (None, why the file cannot be used)."""
    not_json = "is not a UTF-8 JSON file"
    try:
        # utf-8-sig also reads a file that starts with a BOM, as Windows PowerShell 5.1 writes it.
        with open(metadata_path, encoding="utf-8-sig") as metadata_file:
            text = metadata_file.read(_MAX_METADATA_CHARACTERS + 1)
    except FileNotFoundError:
        return None, "not found"
    except OSError:
        return None, "could not be read"
    except ValueError:
        return None, not_json

    if len(text) > _MAX_METADATA_CHARACTERS:
        return None, f"is larger than {_MAX_METADATA_CHARACTERS} characters"
    try:
        return json.loads(text), None
    except (ValueError, RecursionError):
        return None, not_json


def _sha_reason(data: Any, expected_sha: str) -> Optional[str]:
    """Return why the parsed metadata does not name expected_sha, or None when it does."""
    if not isinstance(data, dict):
        return "does not hold a JSON object"

    file_sha = data.get("sha")
    if not isinstance(file_sha, str) or not file_sha.strip():
        return "has no non-empty string 'sha' field"

    # Only a value that is a full commit SHA is echoed: other text from the file stays out of the warning.
    file_sha = file_sha.strip()
    if not _COMMIT_SHA_PATTERN.fullmatch(file_sha):
        return "has a 'sha' that is not a full commit SHA"

    # Both SHAs go into the warning (escaped by print_action_warning), never into the PR comment.
    if file_sha.lower() != expected_sha.lower():
        return f"names commit {file_sha}, but baseline-sha is {expected_sha}"
    return None
