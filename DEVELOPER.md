# JaCoCo Report GitHub Action — Developer Guide

- [Project Setup](#project-setup)
- [Branch Naming Convention](#branch-naming-convention)
- [Run Scripts Locally](#run-scripts-locally)
- [Run Pylint Check Locally](#run-pylint-check-locally)
- [Run Black Tool Locally](#run-black-tool-locally)
- [Run Mypy Locally](#run-mypy-locally)
- [Run Tests](#run-tests)
  - [Unit Tests](#unit-tests)
  - [Integration Tests (offline)](#integration-tests-offline)
  - [Live Integration Tests](#live-integration-tests)
  - [Regenerate Golden Snapshots](#regenerate-golden-snapshots)
- [Code Coverage](#code-coverage)
- [Releasing](#releasing)

---

## Project Setup

### Prepare the Environment

```shell
python3 --version   # Python 3.13+ required
```

### Set Up Python Virtual Environment

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Branch Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/<issue-number>-<short-description>` | `feature/112-skip-unchanged-filter` |
| Bug fix | `fix/<issue-number>-<short-description>` | `fix/95-remove-pylint-disables` |
| Docs | `docs/<short-description>` | `docs/update-developer-md` |
| Chore | `chore/<short-description>` | `chore/add-fixture-factories` |
| Spike | `spike/<issue-number>-<short-description>` | `spike/71-auto-detect-modules` |

---

## Run Scripts Locally

Create a shell script in the project root to simulate a GitHub Actions run locally.

### Create the Shell Script

```shell
touch run_script.sh
chmod +x run_script.sh
```

### Minimal script (no groups)

```bash
#!/bin/sh

export INPUT_TOKEN="ghp_your_personal_access_token"
export INPUT_PATHS="**/jacoco.xml"
export INPUT_EXCLUDE_PATHS=""
export INPUT_GLOBAL_THRESHOLDS="80*70*0"
export INPUT_REPORT_THRESHOLDS_DEFAULT="0*0*60"
export INPUT_TITLE="JaCoCo Coverage Report"
export INPUT_PR_NUMBER="1"
export INPUT_METRIC="instruction"
export INPUT_COMMENT_LEVEL="full"
export INPUT_REPORT_GROUPS=""
export INPUT_SKIP_UNCHANGED="false"
export INPUT_EVALUATE_UNCHANGED="true"
export INPUT_BASELINE_PATHS=""
export INPUT_UPDATE_COMMENT="false"
export INPUT_FAIL_ON_THRESHOLD="overall,changed-files-average,per-changed-file"
export INPUT_PASS_SYMBOL="✅"
export INPUT_FAIL_SYMBOL="❌"
export INPUT_DEBUG="false"

# Required GitHub context variables
export GITHUB_REPOSITORY="MoranaApps/jacoco-report-dev"
export GITHUB_EVENT_NAME="pull_request"
export GITHUB_REF="refs/pull/1/merge"

python3 main.py
```

### Script with report groups

```bash
#!/bin/sh

export INPUT_TOKEN="ghp_your_personal_access_token"
export INPUT_GLOBAL_THRESHOLDS="80*70*0"
export INPUT_REPORT_THRESHOLDS_DEFAULT="75*60*0"
export INPUT_COMMENT_LEVEL="full"
export INPUT_REPORT_GROUPS="
- name: backend
  paths:
    - backend/**/jacoco.xml
  thresholds: '80*70*60'
- name: frontend
  paths:
    - frontend/**/jacoco.xml
  thresholds: '75*65*50'
"
export INPUT_SKIP_UNCHANGED="false"
export INPUT_EVALUATE_UNCHANGED="true"
export INPUT_PR_NUMBER="1"
export INPUT_UPDATE_COMMENT="false"
export INPUT_FAIL_ON_THRESHOLD="overall,changed-files-average,per-changed-file"
export INPUT_PASS_SYMBOL="✅"
export INPUT_FAIL_SYMBOL="❌"
export INPUT_DEBUG="true"

export GITHUB_REPOSITORY="MoranaApps/jacoco-report-dev"
export GITHUB_EVENT_NAME="pull_request"
export GITHUB_REF="refs/pull/1/merge"

python3 main.py
```

### Run the Script

```shell
./run_script.sh
```

---

## Run Pylint Check Locally

This project uses [Pylint](https://pypi.org/project/pylint/) for static code analysis.
Configuration is in `.pylintrc`. The target score is **10.0/10** (`fail-under=10`).

```shell
pylint $(git ls-files '*.py')
```

To lint a single file:

```shell
pylint jacoco_report/jacoco_report.py
```

Expected output example:

```text
------------------------------------------------------------------
Your code has been rated at 10.00/10
```

---

## Run Black Tool Locally

This project uses [Black](https://github.com/psf/black) for code formatting (line length 120,
target Python 3.13). Configuration is in `pyproject.toml`.

Check formatting without modifying files:

```shell
black --check $(git ls-files '*.py')
```

Apply formatting:

```shell
black $(git ls-files '*.py')
```

---

## Run Mypy Locally

This project uses [mypy](https://mypy.readthedocs.io/) for static type checking.
Configuration is in `pyproject.toml`.

```shell
mypy .
```

All source files must pass with zero errors before merging.

---

## Run Tests

### Unit Tests

Unit tests cover individual functions and classes in isolation.

```shell
pytest tests/unit/
```

Run a specific test:

```shell
pytest tests/unit/evaluator/test_coverage_evaluator.py::test_evaluate_overall_coverage
```

### Integration Tests (offline)

Integration tests exercise the full action pipeline without a GitHub token.
They use fixture XML files from `tests/data/` and `tests/data_baseline/`.

```shell
pytest tests/integration/ --ignore=tests/integration/live
```

These tests include:

- **Golden snapshot tests** (`test_golden_snapshots.py`): assert that the generated PR comment
  matches a stored golden file in `tests/integration/fixtures/`.
- **Matrix tests** (`test_matrix_skip_unchanged_comment_level.py`): verify all
  `skip-unchanged` × `comment-level` combinations (12 cases).

### Live Integration Tests

Live tests post a real comment to a GitHub PR and require `GITHUB_TOKEN`, `GITHUB_REPOSITORY`,
and a PR-shaped `GITHUB_REF` (`refs/pull/<n>/merge`).
They are skipped automatically on forks.

```shell
GITHUB_TOKEN=ghp_... \
GITHUB_REPOSITORY=owner/repo \
GITHUB_REF=refs/pull/123/merge \
pytest tests/integration/live/
```

In CI these run only when `github.event.pull_request.head.repo.full_name == github.repository`.

### Regenerate Golden Snapshots

When the PR comment output intentionally changes (e.g. after a feature update), regenerate the
golden snapshot files instead of manually editing them:

```shell
WRITE_SNAPSHOTS=1 pytest tests/integration/test_golden_snapshots.py
```

This writes the current action output to `tests/integration/fixtures/snapshot_*.md`.
Commit the updated files alongside your feature change.

---

## Code Coverage

This project uses [pytest-cov](https://pypi.org/project/pytest-cov/). The minimum coverage
threshold is **80 %** (measured over `tests/unit/` and `tests/integration/` combined,
excluding `tests/integration/live/`).

Generate a coverage report:

```shell
pytest --cov=. tests/ --ignore=tests/integration/live --cov-fail-under=80 --cov-report=html -vv
```

Open the report:

```shell
open htmlcov/index.html
```

Full local QA gate (stricter single command):

```shell
pytest --cov=. tests/ --ignore=tests/integration/live --cov-fail-under=80 && \
pylint $(git ls-files '*.py') && \
black --check $(git ls-files '*.py') && \
mypy .
```

---

## Releasing

This project uses GitHub Actions for release draft creation via `.github/workflows/release_draft.yml`.

1. **Trigger the workflow** — run `release_draft.yml` via `workflow_dispatch`.
2. **Review the draft release** — add a title, description, and changelog notes.
3. **Publish the release** — once the draft is finalised, publish it.

The `v2` tag is moved automatically by `.github/workflows/update-v2-tag.yml` on every
published release.
