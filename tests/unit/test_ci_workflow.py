import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "static_analysis_and_tests.yml"
WORKFLOW_FILES = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
REQUIREMENTS_PATHS = ["requirements.txt", "requirements-dev.txt"]
FULL_SHA = re.compile(r"[0-9a-f]{40}")
THIRD_PARTY_USES = re.compile(r"[\w.-]+/[\w.-]+(/[\w./-]+)?@(?P<ref>[^\s#]+)")
DOCKER_DIGEST_USES = re.compile(r"docker://[\w./-]+@sha256:[0-9a-f]{64}")
PINNED_USES_WITH_COMMENT = re.compile(r"uses:\s*(?P<uses>\S+)\s+#\s*v?\d\S*\s*$", re.MULTILINE)


def _workflow(path: Path = CI_WORKFLOW) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _all_steps(path: Path = CI_WORKFLOW) -> list[dict]:
    return [step for job in _workflow(path)["jobs"].values() for step in job.get("steps", [])]


def _third_party_uses(path: Path = CI_WORKFLOW) -> list[str]:
    return [step["uses"] for step in _all_steps(path) if "uses" in step and not step["uses"].startswith("./")]


def test_setup_python_steps_with_pip_cache_cover_both_requirement_files():
    """Every pip-cached setup-python step keys its cache on runtime and dev pins, so a pin bump invalidates it."""
    cached = [
        step
        for step in _all_steps()
        if str(step.get("uses", "")).startswith("actions/setup-python@") and step.get("with", {}).get("cache") == "pip"
    ]

    assert cached, "no setup-python step uses pip cache"
    for step in cached:
        paths = step["with"].get("cache-dependency-path", "").split()
        assert sorted(paths) == sorted(REQUIREMENTS_PATHS), f"{step['uses']} cache key: {paths}"


def test_no_run_script_in_the_workflow_contains_an_expression():
    # GitHub pastes `${{ … }}` into a run script before bash parses it. Pass values through `env:` instead.
    for step in _all_steps():
        if "run" in step:
            assert "${{" not in step["run"], f"'{step.get('name', step.get('id'))}' has `${{{{ … }}}}` in run"


def test_the_detector_finds_third_party_actions_in_the_workflows():
    assert any(_third_party_uses(path) for path in WORKFLOW_FILES), "detector found no third-party actions"


@pytest.mark.parametrize("workflow", WORKFLOW_FILES, ids=lambda path: path.name)
def test_every_third_party_uses_is_pinned_to_a_full_commit_sha(workflow):
    for uses in _third_party_uses(workflow):
        if uses.startswith("docker://"):
            assert DOCKER_DIGEST_USES.fullmatch(uses), f"{uses} is not pinned to a sha256 image digest"
            continue
        match = THIRD_PARTY_USES.fullmatch(uses)
        assert match, f"unparsable uses: {uses}"
        assert FULL_SHA.fullmatch(match.group("ref")), f"{uses} is not pinned to a 40-hex commit SHA"


def test_workflow_default_token_permissions_are_read_only():
    # Jobs without their own `permissions:` inherit this block; a missing one gives the repo default, often write.
    permissions = _workflow().get("permissions")
    assert isinstance(permissions, dict) and permissions, "workflow has no top-level permissions block"
    assert all(
        level == "read" for level in permissions.values()
    ), f"workflow permissions are not read-only: {permissions}"


def test_version_comment_accepts_a_bare_number_without_v():
    # Renovate and people write `# 4.2.0` as well as `# v4.2.0`; both must count as a version comment.
    assert PINNED_USES_WITH_COMMENT.search("uses: actions/foo@" + "a" * 40 + " # 4.2.0\n")
    assert PINNED_USES_WITH_COMMENT.search("uses: actions/foo@" + "a" * 40 + " # v4.2.0\n")


@pytest.mark.parametrize("workflow", WORKFLOW_FILES, ids=lambda path: path.name)
def test_every_pinned_third_party_uses_has_a_version_comment(workflow):
    # The version comment is what Renovate and readers use to tell which release a SHA is.
    text = workflow.read_text(encoding="utf-8")
    commented = {match.group("uses") for match in PINNED_USES_WITH_COMMENT.finditer(text)}
    assert commented == set(_third_party_uses(workflow))
