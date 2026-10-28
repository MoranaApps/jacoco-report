import os
import re
import subprocess
from pathlib import Path
from unittest import mock

import pytest
import yaml

from jacoco_report.utils.gh_action import get_action_input

ACTION_YML = Path(__file__).resolve().parents[2] / "action.yml"
SETUP_ID = "setup"
RUN_ID = "jacoco-report-to-pr-comment"
RUN_STEP_EXTRA_ENV = {"JACOCO_REPORT_PYTHON": "${{ steps.setup.outputs.python }}"}
RUN_STEP_SCRIPT = '"$JACOCO_REPORT_PYTHON" -E -s "$GITHUB_ACTION_PATH/main.py"'

INPUT_REFERENCE = re.compile(r"^\$\{\{\s*inputs\.([a-z-]+)\s*\}\}$")
TOKEN_REFERENCE = re.compile(r"inputs\.token", re.IGNORECASE)
# A python command word: bare `python`, or a variable such as "$venv_python" or $JACOCO_REPORT_PYTHON.
# `command -v python` only looks the name up, so it is not a command word.
PYTHON_COMMAND = re.compile(r"""(?:^|[\s;&|(])(?<!-v )"?(?:python3?|\$\{?\w*(?i:python)\w*\}?)"?(?=\s)""")
UNQUOTED_PATH = re.compile(r"""(?<!")\$\{?(?:RUNNER_TEMP|GITHUB_ACTION_PATH|GITHUB_OUTPUT)\b""")
PORTABILITY_BANS = {
    "grep -P": re.compile(r"grep\s+-[a-zA-Z]*P"),
    ".venv": re.compile(r"\.venv\b"),
}


def _load_action():
    with open(ACTION_YML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _steps():
    return _load_action()["runs"]["steps"]


def _step(step_id):
    return next(step for step in _steps() if step.get("id") == step_id)


def _label(step):
    return step.get("name") or step.get("id") or "<unnamed step>"


def _run_scripts():
    return [(_label(step), step["run"]) for step in _steps() if "run" in step]


def _python_invocations(script):
    # Yields (line, text after the command word) for every python command in a run script.
    for line in script.splitlines():
        if line.strip().startswith("#"):
            continue
        for match in PYTHON_COMMAND.finditer(line):
            yield line.strip(), line[match.end() :]


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _strings(value)


def test_no_run_script_contains_an_expression():
    # GitHub pastes `${{ … }}` into the script before bash parses it, so any expression in `run:`
    # is a shell injection point. Use env vars and runner-provided paths instead.
    for label, script in _run_scripts():
        assert "${{" not in script, f"{label}: `${{ … }}` expression in run script"


def test_token_is_passed_only_to_the_run_step_env():
    run_step = _step(RUN_ID)
    assert run_step["env"]["INPUT_TOKEN"] == "${{ inputs.token }}"

    # The token may appear in exactly one Run-step env value, so an extra `LEAK: ${{ inputs.token }}` fails.
    token_values = [key for key, value in run_step["env"].items() if TOKEN_REFERENCE.search(str(value))]
    assert token_values == ["INPUT_TOKEN"], f"inputs.token is passed under {token_values}"

    # No other step may contain an expression at all, so none can reference the token or github.token.
    for step in _steps():
        if step.get("id") != RUN_ID:
            assert not any("${{" in text for text in _strings(step)), f"{_label(step)} contains an expression"

    # The Run step's expressions live only in its env, and test_run_step_env_maps_every_input pins that map.
    run_step_outside_env = {key: value for key, value in run_step.items() if key != "env"}
    assert not any("${{" in text for text in _strings(run_step_outside_env)), f"{_label(run_step)}: expression"


def test_no_run_script_writes_github_env():
    # Anything written to $GITHUB_ENV (e.g. the token) leaks into every later step of the caller's job.
    for label, script in _run_scripts():
        assert "GITHUB_ENV" not in script, label


def test_run_step_env_maps_every_input_with_the_real_reader():
    # Feeds each input's `${{ inputs.<name> }}` env value a sentinel, then reads it back with get_action_input.
    run_env = _step(RUN_ID)["env"]
    sandbox = {}
    for key, value in run_env.items():
        match = INPUT_REFERENCE.match(value)
        if match:
            sandbox[key] = f"value-of-{match.group(1)}"

    with mock.patch.dict(os.environ, sandbox, clear=True):
        for name in _load_action()["inputs"]:
            assert get_action_input(name) == f"value-of-{name}", f"input '{name}' is not passed via the Run step env"

    extra_env = {key: value for key, value in run_env.items() if key not in sandbox}
    assert extra_env == RUN_STEP_EXTRA_ENV


def test_action_has_exactly_setup_and_run_steps():
    assert [step.get("id") for step in _steps()] == [SETUP_ID, RUN_ID]


def test_setup_makes_a_fresh_venv_under_runner_temp_and_passes_its_interpreter_via_github_output():
    setup_script = _step(SETUP_ID)["run"]
    # A new private dir per call, under RUNNER_TEMP so the caller's checkout stays clean.
    assert 'venv_dir="$(mktemp -d "$RUNNER_TEMP/jacoco-report-venv.XXXXXX")"' in setup_script
    assert '>> "$GITHUB_OUTPUT"' in setup_script


def test_setup_stops_with_a_setup_python_hint_when_python_is_not_on_path(tmp_path):
    empty_bin = tmp_path / "bin"
    empty_bin.mkdir()
    env = {
        "PATH": str(empty_bin),
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_OUTPUT": str(tmp_path / "output"),
        "GITHUB_ACTION_PATH": str(ACTION_YML.parent),
    }
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", _step(SETUP_ID)["run"]],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "actions/setup-python" in result.stdout + result.stderr
    assert list(tmp_path.glob("jacoco-report-venv*")) == []


def test_setup_python_calls_all_run_isolated():
    # Python puts the working directory on sys.path, and that is the caller's checkout. `-I` drops it, so a
    # planted argparse.py or pip/ there can't run in the setup step.
    invocations = list(_python_invocations(_step(SETUP_ID)["run"]))
    assert len(invocations) >= 4, "detector found too few python invocations"
    for line, rest in invocations:
        assert re.match(r"\s+-I(\s|$)", rest), f"python invocation without -I: {line}"


def test_run_step_runs_main_with_the_venv_interpreter():
    # Not -I: it implies -P, which would keep main.py's directory off sys.path and break `import jacoco_report`.
    assert _step(RUN_ID)["run"].strip() == RUN_STEP_SCRIPT


def test_run_scripts_are_portable_and_leave_no_venv_in_the_workspace():
    for label, script in _run_scripts():
        for name, pattern in PORTABILITY_BANS.items():
            assert pattern.search(script) is None, f"{label}: `{name}` is not portable or touches the workspace"


def test_run_scripts_quote_every_path_variable():
    for label, script in _run_scripts():
        assert UNQUOTED_PATH.search(script) is None, f"{label}: unquoted path variable"
