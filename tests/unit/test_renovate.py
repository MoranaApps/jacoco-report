import fnmatch
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RENOVATE_JSON = REPO_ROOT / "renovate.json"
RENOVATE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "renovate.yml"
CODEOWNERS = REPO_ROOT / ".github" / "CODEOWNERS"
RUNTIME_FILES = ["requirements.in", "requirements.txt"]
GATE_ID = "runtime-gate"
GATE_CLEAR = f"steps.{GATE_ID}.outputs.runtime-changed == 'false'"
APPROVE_STEP = "Approve Renovate PR (optional PAT)"
MERGE_STEP = "Enable auto-merge for Renovate PR"


def _renovate():
    return json.loads(RENOVATE_JSON.read_text(encoding="utf-8"))


def _rule_for(manager, file_names):
    return next(
        rule
        for rule in _renovate()["packageRules"]
        if manager in rule.get("matchManagers", []) and set(rule.get("matchFileNames", [])) == set(file_names)
    )


def _can_match_runtime_file(rule):
    patterns = rule.get("matchFileNames")
    if patterns is None:
        return True
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns for name in RUNTIME_FILES)


def test_no_automerge_rule_can_match_a_runtime_file():
    # A rule without matchFileNames, or with one that names a runtime file, would automerge the runtime lock or input.
    for rule in _renovate()["packageRules"]:
        if rule.get("automerge") is True:
            assert not _can_match_runtime_file(rule), f"automerge rule can match a runtime file: {rule}"


def test_runtime_updates_go_through_pip_compile_and_never_automerge():
    assert _rule_for("pip-compile", RUNTIME_FILES)["automerge"] is False


def test_runtime_updates_wait_seven_days_and_dev_updates_do_not():
    assert _rule_for("pip-compile", RUNTIME_FILES)["minimumReleaseAge"] == "7 days"
    assert "minimumReleaseAge" not in _rule_for("pip_requirements", ["requirements-dev.txt"])


def test_pip_requirements_manager_is_disabled_for_the_lock():
    # Renovate's pip_requirements manager also reads requirements.txt, so disable it there: the lock has one update path.
    assert _rule_for("pip_requirements", ["requirements.txt"])["enabled"] is False


def test_pip_compile_manager_reads_the_lock_and_not_the_input_or_dev_file():
    patterns = _renovate()["pip-compile"]["managerFilePatterns"]

    def matches(name):
        return any(re.search(pattern.strip("/"), name) for pattern in patterns)

    assert matches("requirements.txt")
    assert not matches("requirements.in")
    assert not matches("requirements-dev.txt")


def test_lock_file_maintenance_is_on_and_never_automerges():
    maintenance = _renovate()["lockFileMaintenance"]
    assert maintenance["enabled"] is True
    assert maintenance.get("automerge", False) is False
    assert maintenance["labels"] == ["auto-update", "no-RN"]


def test_dev_requirements_minor_and_patch_updates_still_automerge():
    rule = _rule_for("pip_requirements", ["requirements-dev.txt"])
    assert rule["automerge"] is True
    assert set(rule["matchUpdateTypes"]) == {"minor", "patch"}


def _gate_script():
    steps = yaml.safe_load(RENOVATE_WORKFLOW.read_text(encoding="utf-8"))["jobs"]["renovate"]["steps"]
    return next(step["run"] for step in steps if step.get("id") == GATE_ID)


REPO = "MoranaApps/jacoco-report"
PR_NUMBER = "1"
FILES_ENDPOINT = f"repos/{REPO}/pulls/{PR_NUMBER}/files"
# The fake answers only the paginated REST call the gate makes, and records its argv for the test to read.
FAKE_GH = """#!/bin/bash
printf '%s\\n' "$*" > "$GH_RECORD"
printf '%s\\n' "$FAKE_FILES"
exit "${FAKE_GH_EXIT:-0}"
"""


def _run_gate(tmp_path, changed_files, gh_exit=0):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "grep").symlink_to(shutil.which("grep"))
    (fake_bin / "gh").write_text(FAKE_GH, encoding="utf-8")
    (fake_bin / "gh").chmod(0o755)
    output = tmp_path / "output"
    record = tmp_path / "gh-args"
    env = {
        "PATH": str(fake_bin),
        "REPO": REPO,
        "PR_NUMBER": PR_NUMBER,
        "GITHUB_OUTPUT": str(output),
        "GH_RECORD": str(record),
        "FAKE_FILES": "\n".join(changed_files),
        "FAKE_GH_EXIT": str(gh_exit),
    }
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", _gate_script()],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    gh_args = record.read_text(encoding="utf-8").strip() if record.exists() else ""
    return result, output.read_text(encoding="utf-8") if output.exists() else "", gh_args


@pytest.mark.parametrize("changed_files", [["requirements.txt", "README.md"], ["requirements.in"]])
def test_gate_reports_a_runtime_change(tmp_path, changed_files):
    result, output, _ = _run_gate(tmp_path, changed_files)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "runtime-changed=true" in output.splitlines()


def test_gate_reads_the_paginated_file_list_through_rest(tmp_path):
    # `gh pr view --json files` stops at 100 files, so the gate pages through the REST files endpoint instead.
    result, _, gh_args = _run_gate(tmp_path, ["README.md"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert gh_args == f"api --paginate {FILES_ENDPOINT} --jq .[].filename"


def test_gate_reports_no_runtime_change_for_dev_and_other_files(tmp_path):
    # The near misses are not the runtime inputs: Renovate matches file names exactly, and so does the gate.
    result, output, _ = _run_gate(tmp_path, ["requirements-dev.txt", "pyproject.toml", "docs/requirements.txt"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "runtime-changed=false" in output.splitlines()


def test_gate_fails_when_the_file_list_cannot_be_read(tmp_path):
    result, output, _ = _run_gate(tmp_path, ["requirements-dev.txt"], gh_exit=1)
    assert result.returncode != 0
    assert "runtime-changed" not in output


def test_gate_fails_closed_when_the_file_list_is_empty(tmp_path):
    # An empty list must not read as "no runtime change", or a PR whose file list failed to load would be approved.
    result, output, _ = _run_gate(tmp_path, [])
    assert result.returncode != 0
    assert "runtime-changed" not in output
    assert "::error::" in result.stdout


def test_gate_logs_why_approval_and_merge_are_skipped_for_a_runtime_change(tmp_path):
    result, _, _ = _run_gate(tmp_path, ["requirements.txt"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Skipping approval and auto-merge: runtime dependencies (requirements.in/requirements.txt)" in result.stdout
    assert "need a person to review and merge" in result.stdout


def test_gate_stays_quiet_about_the_skip_when_no_runtime_file_changed(tmp_path):
    result, _, _ = _run_gate(tmp_path, ["requirements-dev.txt"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Skipping approval" not in result.stdout


def _renovate_steps():
    return yaml.safe_load(RENOVATE_WORKFLOW.read_text(encoding="utf-8"))["jobs"]["renovate"]["steps"]


def _step_named(name):
    return next(step for step in _renovate_steps() if step.get("name") == name)


def test_approval_and_auto_merge_run_only_when_the_gate_finds_no_runtime_change():
    approve = _step_named(APPROVE_STEP)["if"]
    assert GATE_CLEAR in approve
    assert "env.HAS_REVIEW_TOKEN == 'true'" in approve
    assert GATE_CLEAR in _step_named(MERGE_STEP)["if"]


def test_the_gate_step_runs_before_approval_and_merge():
    names = [step.get("name") for step in _renovate_steps()]
    gate = next(step for step in _renovate_steps() if step.get("id") == GATE_ID)
    assert names.index(gate["name"]) < names.index(APPROVE_STEP) < names.index(MERGE_STEP)
    assert "if" not in gate


def test_code_owners_cover_the_runtime_inputs_and_leave_dev_unowned():
    owners = {}
    for line in CODEOWNERS.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts and not parts[0].startswith("#"):
            owners[parts[0]] = parts[1:]
    assert owners["/requirements.in"], "requirements.in has no code owner"
    assert owners["/requirements.txt"], "requirements.txt has no code owner"
    assert owners["/requirements-dev.txt"] == []
