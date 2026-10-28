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
# -B: no __pycache__ in the caller's checkout (-E drops PYTHONDONTWRITEBYTECODE). -E -s: see the Run step comment.
RUN_STEP_SCRIPT = '"$JACOCO_REPORT_PYTHON" -B -E -s "$GITHUB_ACTION_PATH/main.py"'

INPUT_REFERENCE = re.compile(r"^\$\{\{\s*inputs\.([a-z-]+)\s*\}\}$")
TOKEN_REFERENCE = re.compile(r"inputs\.token", re.IGNORECASE)
# A python command word at command position: line start, or after `;` `&` `|` `(` `!` `$(` or if/then/else/do.
# Prose such as `echo "Using python 3.11"` or `command -v python` has no such prefix, so it is not a command word.
# Matches bare `python`/`python3`, or a variable such as "$venv_python" or $JACOCO_REPORT_PYTHON.
PYTHON_COMMAND = re.compile(
    r"""(?:^|[;&|(!]|\$\(|\b(?:if|then|else|do)\b)\s*"?(?:python3?|\$\{?\w*(?i:python)\w*\}?)"?(?=\s|$)"""
)
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


def _strip_comments(script):
    # Drops `# …` comments: a `#` at line start or after whitespace, outside quotes. `$#` and `"#"` stay.
    lines = []
    for line in script.splitlines():
        quote = None
        cut = len(line)
        for index, char in enumerate(line):
            if quote:
                if char == quote:
                    quote = None
            elif char in "\"'":
                quote = char
            elif char == "#" and (index == 0 or line[index - 1].isspace()):
                cut = index
                break
        lines.append(line[:cut])
    return "\n".join(lines)


def _python_invocations(script):
    # Yields (line, text after the command word) for every python command in a run script.
    for line in _strip_comments(script).splitlines():
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


def test_setup_makes_a_fresh_venv_under_runner_temp_and_passes_its_interpreter_via_github_output(tmp_path):
    # A fake `python` that accepts the version checks and, for `-m venv DIR`, creates DIR/bin/python.
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python"
    fake_python.write_text(
        '#!/bin/bash\ncase "$*" in\n'
        '  "-I --version") echo "Python 3.12.0" ;;\n'
        '  "-I -m venv "*) mkdir -p "${@: -1}/bin" && cp "$0" "${@: -1}/bin/python" ;;\n'
        "esac\nexit 0\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    output = tmp_path / "output"
    env = {
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_OUTPUT": str(output),
        "GITHUB_ACTION_PATH": str(ACTION_YML.parent),
    }
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", _step(SETUP_ID)["run"]],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    # The interpreter is handed on as a step output and lives in a new venv dir directly under RUNNER_TEMP.
    venv_python = Path(output.read_text(encoding="utf-8").removeprefix("python=").strip())
    venv_dir = venv_python.parent.parent
    assert venv_python.is_file()
    assert venv_dir.parent == tmp_path
    assert venv_dir.name.startswith("jacoco-report-venv.")


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


def test_setup_emits_an_error_annotation_when_python_is_too_old(tmp_path):
    # A fake `python` on PATH that reports 3.10: the version check (`-c`) fails, as it does for a real 3.10.
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python"
    fake_python.write_text(
        '#!/bin/bash\ncase "$*" in\n  "-I --version") echo "Python 3.10.12" ;;\n  *"-c"*) exit 1 ;;\n  *) exit 0 ;;\nesac\n',
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    env = {
        "PATH": str(fake_bin),
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
    assert "::error::Python version is less than 3.11.0" in result.stdout
    assert list(tmp_path.glob("jacoco-report-venv*")) == []


def test_python_detector_skips_prose_and_comments_but_finds_real_calls():
    script = "\n".join(
        [
            'echo "Using python 3.11"',
            'echo "Please install python first"',
            "# python -I is only a comment",
            "  python -I -m venv x  # python -m pip",
            'echo "Version: $(python3 -I --version)"',
            'if ! "$venv_python" -I -c "import sys"; then',
        ]
    )
    assert [line for line, _ in _python_invocations(script)] == [
        "python -I -m venv x",
        'echo "Version: $(python3 -I --version)"',
        'if ! "$venv_python" -I -c "import sys"; then',
    ]


def test_setup_python_calls_all_run_isolated():
    # Python puts the working directory on sys.path, and that is the caller's checkout. `-I` drops it, so a
    # planted argparse.py or pip/ there can't run in the setup step.
    invocations = list(_python_invocations(_step(SETUP_ID)["run"]))
    # Guard that the detector still sees the calls that matter, so the -I check below can't pass on an empty list.
    for module in ("venv", "pip"):
        assert any(re.search(rf"-m\s+{module}\b", rest) for _, rest in invocations), f"no `-m {module}` call detected"
    for line, rest in invocations:
        assert re.match(r"\s+-I(\s|$)", rest), f"python invocation without -I: {line}"


def test_run_step_runs_main_with_the_venv_interpreter():
    # Not -I: it implies -P, which would keep main.py's directory off sys.path and break `import jacoco_report`.
    assert _step(RUN_ID)["run"].strip() == RUN_STEP_SCRIPT


def test_run_scripts_are_portable_and_leave_no_venv_in_the_workspace():
    for label, script in _run_scripts():
        for name, pattern in PORTABILITY_BANS.items():
            assert (
                pattern.search(_strip_comments(script)) is None
            ), f"{label}: `{name}` is not portable or touches the workspace"


def test_run_scripts_quote_every_path_variable():
    for label, script in _run_scripts():
        assert UNQUOTED_PATH.search(_strip_comments(script)) is None, f"{label}: unquoted path variable"


def test_strip_comments_keeps_code_and_drops_only_comments():
    assert _strip_comments("# uses .venv\necho ok  # and .venv\n") == "\necho ok  "
    assert _strip_comments('echo "a # .venv"') == 'echo "a # .venv"'
    assert _strip_comments("echo $# .venv") == "echo $# .venv"
    assert ".venv" in _strip_comments("python3 -m venv .venv")
