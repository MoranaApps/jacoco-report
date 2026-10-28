from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "static_analysis_and_tests.yml"


def _setup_python_steps_with_cache_path() -> list[dict]:
    """Return every `actions/setup-python` step of the CI workflow that sets `cache-dependency-path`."""
    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    return [
        step
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if str(step.get("uses", "")).startswith("actions/setup-python") and "cache-dependency-path" in step["with"]
    ]


def test_setup_python_cache_key_covers_both_requirement_files():
    """The pip cache key includes the runtime pins too, so a runtime pin bump invalidates the cache."""
    steps = _setup_python_steps_with_cache_path()

    assert len(steps) == 6
    for step in steps:
        assert step["with"]["cache-dependency-path"].split() == ["requirements.txt", "requirements-dev.txt"]
