from pathlib import Path

import yaml

ACTION_YML = Path(__file__).resolve().parents[2] / "action.yml"


def _load_action():
    with open(ACTION_YML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _steps():
    return _load_action()["runs"]["steps"]


def test_no_run_script_interpolates_inputs():
    # `${{ inputs.* }}` inside `run:` is pasted into the bash source before it runs,
    # so an input value can inject shell.
    for step in _steps():
        assert "${{ inputs." not in step.get("run", ""), step["name"]


def test_no_step_writes_to_github_env():
    # Anything written to $GITHUB_ENV (e.g. the token) leaks into every later step of the caller's job.
    for step in _steps():
        assert "GITHUB_ENV" not in step.get("run", ""), step["name"]


def test_run_step_passes_every_input_via_env():
    action = _load_action()
    run_step = next(step for step in action["runs"]["steps"] if step.get("id") == "jacoco-report-to-pr-comment")

    expected = {f'INPUT_{name.replace("-", "_").upper()}': f"${{{{ inputs.{name} }}}}" for name in action["inputs"]}

    assert run_step["env"] == expected
