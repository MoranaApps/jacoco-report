import os
import re
import shutil
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
SETUP_STEP_ENV = {"INPUT_CA_BUNDLE": "${{ inputs.ca-bundle }}"}

INPUT_REFERENCE = re.compile(r"^\$\{\{\s*inputs\.([a-z-]+)\s*\}\}$")
TOKEN_REFERENCE = re.compile(r"inputs\.token", re.IGNORECASE)


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

    # No other step may reference the token or github.token. Each non-Run step's env is an exact allowlist,
    # and no expression may appear outside that env.
    for step in _steps():
        if step.get("id") == RUN_ID:
            continue
        expected_env = SETUP_STEP_ENV if step.get("id") == SETUP_ID else {}
        assert step.get("env", {}) == expected_env, f"{_label(step)} env: {step.get('env')}"
        step_outside_env = {key: value for key, value in step.items() if key != "env"}
        assert not any("${{" in text for text in _strings(step_outside_env)), f"{_label(step)} contains an expression"

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


def _setup_env(tmp_path, fake_bin):
    return {
        "PATH": str(fake_bin),
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_OUTPUT": str(tmp_path / "output"),
        "GITHUB_ACTION_PATH": str(ACTION_YML.parent),
    }


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


VENV_CAPABLE_FAKE = (
    '#!/bin/bash\ncase "$*" in\n'
    '  "-I --version") echo "Python 3.12.0" ;;\n'
    '  "-I -m venv "*) mkdir -p "${@: -1}/bin" && cp "$0" "${@: -1}/bin/python" ;;\n'
    "esac\nexit 0\n"
)
TOO_OLD_FAKE = (
    '#!/bin/bash\ncase "$*" in\n  "-I --version") echo "Python 3.10.12" ;;\n  *"-c"*) exit 1 ;;\n  *) exit 0 ;;\nesac\n'
)


def _fake_bin(tmp_path, fakes):
    # Only the fake interpreters and the tools the step needs: no /usr/bin, so no real python can be picked up.
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for tool in ("mktemp", "mkdir", "cp"):
        (fake_bin / tool).symlink_to(shutil.which(tool))
    for name, script in fakes.items():
        (fake_bin / name).write_text(script, encoding="utf-8")
        (fake_bin / name).chmod(0o755)
    return fake_bin


def _run_setup(tmp_path, fake_bin, env=None, cwd=None):
    if env is None:
        env = _setup_env(tmp_path, fake_bin)
    return subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", _step(SETUP_ID)["run"]],
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_setup_uses_python3_when_only_python3_is_on_path(tmp_path):
    fake_bin = _fake_bin(tmp_path, {"python3": VENV_CAPABLE_FAKE})
    result = _run_setup(tmp_path, fake_bin)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Current Python version: Python 3.12.0" in result.stdout
    venv_python = Path((tmp_path / "output").read_text(encoding="utf-8").removeprefix("python=").strip())
    assert venv_python.is_file()
    assert venv_python.parent.parent.parent == tmp_path


def test_setup_skips_a_too_old_python_and_uses_python3(tmp_path):
    # `python` is on PATH but reports 3.10, so the version check fails for it and `python3` is chosen.
    fake_bin = _fake_bin(tmp_path, {"python": TOO_OLD_FAKE, "python3": VENV_CAPABLE_FAKE})
    result = _run_setup(tmp_path, fake_bin)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "::error::" not in result.stdout
    assert "Current Python version: Python 3.12.0" in result.stdout
    venv_python = Path((tmp_path / "output").read_text(encoding="utf-8").removeprefix("python=").strip())
    assert venv_python.is_file()


def test_setup_emits_an_error_annotation_when_only_python3_is_too_old(tmp_path):
    fake_bin = _fake_bin(tmp_path, {"python3": TOO_OLD_FAKE})
    result = _run_setup(tmp_path, fake_bin)
    assert result.returncode != 0
    assert "::error::Python version is less than 3.11.0" in result.stdout
    assert list(tmp_path.glob("jacoco-report-venv*")) == []


def test_setup_error_names_both_python_and_python3_when_neither_is_on_path(tmp_path):
    fake_bin = _fake_bin(tmp_path, {})
    result = _run_setup(tmp_path, fake_bin)
    assert result.returncode != 0
    assert "::error::" in result.stdout
    assert "python3" in result.stdout and "python " in result.stdout
    assert "actions/setup-python" in result.stdout
    assert list(tmp_path.glob("jacoco-report-venv*")) == []


def test_setup_logs_the_version_of_each_python_it_rejects(tmp_path):
    fake_bin = _fake_bin(tmp_path, {"python": TOO_OLD_FAKE, "python3": TOO_OLD_FAKE})
    result = _run_setup(tmp_path, fake_bin)
    assert result.returncode != 0
    assert "Found python: Python 3.10.12" in result.stdout
    assert "Found python3: Python 3.10.12" in result.stdout


def test_setup_runs_every_python_call_with_dash_i(tmp_path):
    # -I keeps the caller's checkout (the working directory) off sys.path. The fake logs every call it gets,
    # including the venv's own python that runs pip, so a call without -I shows up in the log.
    calls_log = tmp_path / "calls.log"
    fake = (
        "#!/bin/bash\n"
        f'echo "$*" >> "{calls_log}"\n'
        'case "$*" in\n'
        '  "-I --version") echo "Python 3.12.0" ;;\n'
        '  "-I -m venv "*) mkdir -p "${@: -1}/bin" && cp "$0" "${@: -1}/bin/python" ;;\n'
        "esac\nexit 0\n"
    )
    fake_bin = _fake_bin(tmp_path, {"python": fake})
    result = _run_setup(tmp_path, fake_bin)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = calls_log.read_text(encoding="utf-8").splitlines()
    assert any(" -m venv " in call for call in calls), calls
    assert any(" -m pip " in call for call in calls), calls
    assert all(call.startswith("-I ") for call in calls), calls


def test_setup_falls_back_to_tmpdir_when_runner_temp_is_unset(tmp_path):
    # Under `act` RUNNER_TEMP is unset. The venv must land under TMPDIR, not fail at the filesystem root.
    fake_bin = _fake_bin(tmp_path, {"python": VENV_CAPABLE_FAKE})
    env = _setup_env(tmp_path, fake_bin)
    del env["RUNNER_TEMP"]
    env["TMPDIR"] = str(tmp_path)
    result = _run_setup(tmp_path, fake_bin, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    venv_python = Path((tmp_path / "output").read_text(encoding="utf-8").removeprefix("python=").strip())
    assert venv_python.is_file()
    assert venv_python.parent.parent.parent == tmp_path
    assert venv_python.parent.parent.name.startswith("jacoco-report-venv.")


def test_run_step_runs_main_with_dash_b_only_and_clears_only_pythonpath(tmp_path):
    # The fake interpreter records its argv and the Python env it sees. Only -B is passed, PYTHONPATH is
    # cleared, and other Python env vars such as PYTHONIOENCODING reach the interpreter.
    record = tmp_path / "record.txt"
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        "#!/bin/bash\n"
        'printf "%s\\n" "$@" > "$RECORD"\n'
        'printf "PYTHONPATH=%s\\n" "${PYTHONPATH-<unset>}" >> "$RECORD"\n'
        'printf "PYTHONIOENCODING=%s\\n" "${PYTHONIOENCODING-<unset>}" >> "$RECORD"\n',
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    env = {
        "PATH": "/usr/bin:/bin",
        "GITHUB_ACTION_PATH": str(ACTION_YML.parent),
        "JACOCO_REPORT_PYTHON": str(fake_python),
        "PYTHONPATH": "/caller/job/path",
        "PYTHONIOENCODING": "utf-8",
        "RECORD": str(record),
    }
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", _step(RUN_ID)["run"]],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert record.read_text(encoding="utf-8").splitlines() == [
        "-B",
        str(ACTION_YML.parent / "main.py"),
        "PYTHONPATH=<unset>",
        "PYTHONIOENCODING=utf-8",
    ]


def test_ca_bundle_input_is_optional_and_defaults_to_empty():
    ca_bundle = _load_action()["inputs"]["ca-bundle"]
    assert ca_bundle["required"] is False
    assert ca_bundle["default"] == ""


def _ca_bundle_fake_bin(tmp_path):
    # The venv python is a copy of this fake. The pip call records its argv and the CA env vars it sees.
    fake = (
        "#!/bin/bash\n"
        'case "$*" in\n'
        '  "-I --version") echo "Python 3.12.0" ;;\n'
        '  "-I -m venv "*) mkdir -p "${@: -1}/bin" && cp "$0" "${@: -1}/bin/python" ;;\n'
        '  *"-m pip "*)\n'
        '    printf "%s\\n" "$*" "PIP_CERT=${PIP_CERT-<unset>}" "REQUESTS_CA_BUNDLE=${REQUESTS_CA_BUNDLE-<unset>}" '
        '"CURL_CA_BUNDLE=${CURL_CA_BUNDLE-<unset>}" > "$RECORD" ;;\n'
        "esac\nexit 0\n"
    )
    return _fake_bin(tmp_path, {"python": fake})


def test_setup_rejects_a_ca_bundle_that_is_not_a_file(tmp_path):
    fake_bin = _ca_bundle_fake_bin(tmp_path)
    env = _setup_env(tmp_path, fake_bin)
    env["INPUT_CA_BUNDLE"] = str(tmp_path / "missing-7f3a.pem")
    result = _run_setup(tmp_path, fake_bin, env=env)
    assert result.returncode != 0
    assert "::error::" in result.stdout
    # The raw path is not echoed: a crafted value could inject workflow commands.
    assert "missing-7f3a.pem" not in result.stdout + result.stderr
    assert list(tmp_path.glob("jacoco-report-venv*")) == []


def test_setup_passes_the_ca_bundle_to_pip_and_overrides_requests_env_vars(tmp_path):
    fake_bin = _ca_bundle_fake_bin(tmp_path)
    bundle = tmp_path / "proxy-ca.pem"
    bundle.write_text("-----BEGIN CERTIFICATE-----\n", encoding="utf-8")
    record = tmp_path / "record.txt"
    env = _setup_env(tmp_path, fake_bin)
    env.update(
        {
            "INPUT_CA_BUNDLE": str(bundle),
            "REQUESTS_CA_BUNDLE": "/caller/requests.pem",
            "CURL_CA_BUNDLE": "/caller/curl.pem",
            "RECORD": str(record),
        }
    )
    result = _run_setup(tmp_path, fake_bin, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    pip_call, *ca_env = record.read_text(encoding="utf-8").splitlines()
    assert "-m pip install -r" in pip_call
    assert ca_env == [f"PIP_CERT={bundle}", "REQUESTS_CA_BUNDLE=<unset>", "CURL_CA_BUNDLE=<unset>"]


def test_setup_leaves_pip_ca_env_alone_when_ca_bundle_is_unset(tmp_path):
    # An empty input is the default, so it counts as unset.
    fake_bin = _ca_bundle_fake_bin(tmp_path)
    record = tmp_path / "record.txt"
    env = _setup_env(tmp_path, fake_bin)
    env.update({"INPUT_CA_BUNDLE": "", "REQUESTS_CA_BUNDLE": "/caller/requests.pem", "RECORD": str(record)})
    result = _run_setup(tmp_path, fake_bin, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    _, *ca_env = record.read_text(encoding="utf-8").splitlines()
    assert ca_env == ["PIP_CERT=<unset>", "REQUESTS_CA_BUNDLE=/caller/requests.pem", "CURL_CA_BUNDLE=<unset>"]


def test_setup_trims_a_ca_bundle_with_surrounding_whitespace_before_checking_and_passing_it(tmp_path):
    # `>` in a caller's workflow adds a trailing newline; Python strips it, so bash must too.
    fake_bin = _ca_bundle_fake_bin(tmp_path)
    bundle = tmp_path / "proxy-ca.pem"
    bundle.write_text("-----BEGIN CERTIFICATE-----\n", encoding="utf-8")
    record = tmp_path / "record.txt"
    env = _setup_env(tmp_path, fake_bin)
    env.update({"INPUT_CA_BUNDLE": f"  {bundle}\n", "RECORD": str(record)})
    result = _run_setup(tmp_path, fake_bin, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    _, *ca_env = record.read_text(encoding="utf-8").splitlines()
    assert ca_env[0] == f"PIP_CERT={bundle}"


def test_setup_treats_a_whitespace_only_ca_bundle_as_unset(tmp_path):
    # Python's ActionInputs.get_ca_bundle() returns "" for this, so the caller's REQUESTS_CA_BUNDLE must pass through.
    fake_bin = _ca_bundle_fake_bin(tmp_path)
    record = tmp_path / "record.txt"
    env = _setup_env(tmp_path, fake_bin)
    env.update({"INPUT_CA_BUNDLE": " \n\t", "REQUESTS_CA_BUNDLE": "/caller/requests.pem", "RECORD": str(record)})
    result = _run_setup(tmp_path, fake_bin, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    _, *ca_env = record.read_text(encoding="utf-8").splitlines()
    assert ca_env == ["PIP_CERT=<unset>", "REQUESTS_CA_BUNDLE=/caller/requests.pem", "CURL_CA_BUNDLE=<unset>"]


def test_setup_resolves_a_relative_ca_bundle_from_the_working_directory(tmp_path):
    # Setup and the Run step share the workspace cwd, so a relative path must resolve the same way in both.
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "ca.pem").write_text("-----BEGIN CERTIFICATE-----\n", encoding="utf-8")
    fake_bin = _ca_bundle_fake_bin(tmp_path)
    record = tmp_path / "record.txt"
    env = _setup_env(tmp_path, fake_bin)
    env.update({"INPUT_CA_BUNDLE": "ca.pem", "RECORD": str(record)})
    result = _run_setup(tmp_path, fake_bin, env=env, cwd=workspace)
    assert result.returncode == 0, result.stdout + result.stderr
    _, *ca_env = record.read_text(encoding="utf-8").splitlines()
    assert ca_env[0] == "PIP_CERT=ca.pem"
