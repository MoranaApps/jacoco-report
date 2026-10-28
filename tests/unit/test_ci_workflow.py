import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "static_analysis_and_tests.yml"
REQUIREMENTS_PATHS = ["requirements.txt", "requirements-dev.txt"]
FULL_SHA = re.compile(r"[0-9a-f]{40}")
THIRD_PARTY_USES = re.compile(r"[\w.-]+/[\w.-]+(/[\w./-]+)?@(?P<ref>[^\s#]+)")
PINNED_USES_WITH_COMMENT = re.compile(r"uses:\s*(?P<uses>\S+)\s+#\s*v\d\S*\s*$", re.MULTILINE)


def _workflow() -> dict:
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))


def _all_steps() -> list[dict]:
    return [step for job in _workflow()["jobs"].values() for step in job.get("steps", [])]


def _third_party_uses() -> list[str]:
    return [step["uses"] for step in _all_steps() if "uses" in step and not step["uses"].startswith("./")]


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


def test_every_third_party_uses_is_pinned_to_a_full_commit_sha():
    uses_values = _third_party_uses()
    assert uses_values, "detector found no third-party actions"
    for uses in uses_values:
        match = THIRD_PARTY_USES.fullmatch(uses)
        assert match, f"unparsable uses: {uses}"
        assert FULL_SHA.fullmatch(match.group("ref")), f"{uses} is not pinned to a 40-hex commit SHA"


def test_every_pinned_third_party_uses_has_a_version_comment():
    # The version comment is what Renovate and readers use to tell which release a SHA is.
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    commented = {match.group("uses") for match in PINNED_USES_WITH_COMMENT.finditer(text)}
    assert commented == set(_third_party_uses())
