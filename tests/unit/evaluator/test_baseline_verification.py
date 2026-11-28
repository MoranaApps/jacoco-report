import json

import pytest
from pytest_mock import MockerFixture

from jacoco_report.evaluator.baseline_verification import unverified_baseline_reason

EXPECTED_SHA = "0123456789abcdef0123456789abcdef01234567"
SUFFIX = ". The Δ against it is informational, and 'no-decrease' skips it."


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _warning(reason: str) -> str:
    return f"Unverified baseline: {reason}{SUFFIX}"


def test_matching_sha_verifies_the_baseline(tmp_path):
    metadata = _write_json(tmp_path / "metadata.json", {"sha": EXPECTED_SHA})
    assert unverified_baseline_reason(EXPECTED_SHA, metadata) is None


@pytest.mark.parametrize(
    "file_sha",
    [
        pytest.param(EXPECTED_SHA.upper(), id="upper-case"),
        pytest.param(f"  {EXPECTED_SHA}\n", id="surrounding-whitespace"),
    ],
)
def test_sha_comparison_ignores_case_and_surrounding_whitespace(tmp_path, file_sha):
    metadata = _write_json(tmp_path / "metadata.json", {"sha": file_sha})
    assert unverified_baseline_reason(EXPECTED_SHA, metadata) is None


def test_metadata_file_with_a_utf8_bom_verifies_the_baseline(tmp_path):
    # Windows PowerShell 5.1 `Set-Content -Encoding utf8` writes a BOM.
    metadata = tmp_path / "metadata.json"
    metadata.write_bytes(b"\xef\xbb\xbf" + json.dumps({"sha": EXPECTED_SHA}).encode("utf-8"))
    assert unverified_baseline_reason(EXPECTED_SHA, str(metadata)) is None


def test_different_sha_is_unverified(tmp_path):
    other = "f" * 40
    metadata = _write_json(tmp_path / "metadata.json", {"sha": other})
    assert unverified_baseline_reason(EXPECTED_SHA, metadata) == _warning(
        f"metadata file '{metadata}' names commit {other}, but baseline-sha is {EXPECTED_SHA}"
    )


def test_missing_file_is_unverified(tmp_path):
    metadata = str(tmp_path / "missing.json")
    assert unverified_baseline_reason(EXPECTED_SHA, metadata) == _warning(f"metadata file '{metadata}' not found")


def test_directory_is_unverified(tmp_path):
    assert unverified_baseline_reason(EXPECTED_SHA, str(tmp_path)) == _warning(
        f"metadata file '{tmp_path}' could not be read"
    )


def test_malformed_json_is_unverified(tmp_path):
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"sha": ', encoding="utf-8")
    assert unverified_baseline_reason(EXPECTED_SHA, str(metadata)) == _warning(
        f"metadata file '{metadata}' is not a UTF-8 JSON file"
    )


def test_not_utf8_is_unverified(tmp_path):
    metadata = tmp_path / "metadata.json"
    metadata.write_bytes(b'{"sha": "\xff\xfe"}')
    assert unverified_baseline_reason(EXPECTED_SHA, str(metadata)) == _warning(
        f"metadata file '{metadata}' is not a UTF-8 JSON file"
    )


def test_json_that_is_not_an_object_is_unverified(tmp_path):
    metadata = _write_json(tmp_path / "metadata.json", [EXPECTED_SHA])
    assert unverified_baseline_reason(EXPECTED_SHA, metadata) == _warning(
        f"metadata file '{metadata}' does not hold a JSON object"
    )


@pytest.mark.parametrize(
    "data",
    [
        pytest.param({}, id="no-sha"),
        pytest.param({"sha": ""}, id="empty-sha"),
        pytest.param({"sha": "   "}, id="whitespace-sha"),
        pytest.param({"sha": 123}, id="non-string-sha"),
        pytest.param({"sha": None}, id="null-sha"),
    ],
)
def test_missing_or_invalid_sha_field_is_unverified(tmp_path, data):
    metadata = _write_json(tmp_path / "metadata.json", data)
    assert unverified_baseline_reason(EXPECTED_SHA, metadata) == _warning(
        f"metadata file '{metadata}' has no non-empty string 'sha' field"
    )


@pytest.mark.parametrize(
    "file_sha",
    [
        pytest.param(EXPECTED_SHA[:7], id="short-sha"),
        pytest.param(EXPECTED_SHA + "\n::add-mask::x", id="sha-with-command"),
        pytest.param("\ud800" + EXPECTED_SHA[1:], id="lone-surrogate"),
        pytest.param("e" * 1000, id="long-string"),
    ],
)
def test_sha_that_is_not_a_full_commit_sha_is_unverified_and_not_echoed(tmp_path, file_sha):
    metadata = _write_json(tmp_path / "metadata.json", {"sha": file_sha})
    reason = unverified_baseline_reason(EXPECTED_SHA, metadata)
    assert reason == _warning(f"metadata file '{metadata}' has a 'sha' that is not a full commit SHA")
    # A lone surrogate in the message would make print() raise when the warning is written.
    reason.encode("utf-8")


def test_json_nested_too_deeply_is_unverified(tmp_path, mocker: MockerFixture):
    # Python 3.11's json decoder recurses at a depth the size limit still allows; newer ones need a far deeper file.
    metadata = tmp_path / "metadata.json"
    metadata.write_text("[" * 5_000 + "]" * 5_000, encoding="utf-8")
    mocker.patch("jacoco_report.evaluator.baseline_verification.json.loads", side_effect=RecursionError)
    assert unverified_baseline_reason(EXPECTED_SHA, str(metadata)) == _warning(
        f"metadata file '{metadata}' is not a UTF-8 JSON file"
    )


def test_metadata_file_over_the_size_limit_is_unverified(tmp_path):
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps({"sha": EXPECTED_SHA, "padding": "x" * 70_000}), encoding="utf-8")
    assert unverified_baseline_reason(EXPECTED_SHA, str(metadata)) == _warning(
        f"metadata file '{metadata}' is larger than 65536 characters"
    )


def test_mismatch_warning_names_the_file_sha_without_surrounding_whitespace(tmp_path):
    other = "e" * 40
    metadata = _write_json(tmp_path / "metadata.json", {"sha": f" {other}\n"})
    assert unverified_baseline_reason(EXPECTED_SHA, metadata) == _warning(
        f"metadata file '{metadata}' names commit {other}, but baseline-sha is {EXPECTED_SHA}"
    )
