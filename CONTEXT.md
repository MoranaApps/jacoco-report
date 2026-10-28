# jacoco-report

## Purpose

A GitHub composite Action that parses JaCoCo XML coverage reports and posts/updates a structured
coverage summary as a pull-request comment, evaluating configurable coverage thresholds and failing
the workflow run when they aren't met. For teams with JaCoCo-instrumented JVM builds (Maven/Gradle)
who want coverage visible directly in PR review, without digging through CI logs.

## Tech stack

- Python 3.11+ (CI matrix: 3.11, 3.12, 3.13, 3.14, 3.15 — only `unit-tests` runs the full matrix;
  `analysis`/`code-format-check`/`mypy-check`/`integration-tests`/`live-integration-test`/`self-test`
  run once on 3.11, the oldest supported version; `pyproject.toml`/`.pylintrc` target py311)
- No packaging layer: this is a GitHub composite Action (`action.yml`), not a pip package. Deps are
  pinned flat in `requirements.txt` (runtime) and `requirements-dev.txt` (`-r requirements.txt` plus
  dev tools); no `src/` layout.
- Libraries: `requests` (GitHub REST API), `pyyaml` (`report-groups` input parsing)
- Dev tooling: pylint, black (line-length 120), mypy, pytest + pytest-cov + pytest-mock
- CI: GitHub Actions (`.github/workflows/`); Renovate for dependency updates
- No database, no long-running process — runs once per workflow invocation and exits

## Structure

- `jacoco_report/` — the action's package: `action_inputs.py` (reads/validates every `INPUT_*` env
  var), `jacoco_report.py` (orchestrator, class `JaCoCoReport`), `scanner/` (glob-based XML
  discovery), `parser/` (JaCoCo XML → model), `evaluator/` (threshold evaluation), `generator/` (PR
  comment markdown), `model/` (data classes), `utils/` (GitHub API client, GH Actions I/O, enums,
  constants, logging)
- `main.py` — entry point: `ActionInputs` → `JaCoCoReport` → GH Action outputs/exit code
- `action.yml` — composite action definition: the real inputs/outputs contract; a `setup` step builds
  a venv under `$RUNNER_TEMP`, then the Run step runs `main.py` with that venv's interpreter
- `tests/unit/` — mirrors `jacoco_report/` package by package
- `tests/integration/` — full-pipeline tests against fixture XML in `tests/data/` and
  `tests/data_baseline/`, incl. golden snapshot tests (`tests/integration/fixtures/`) and a
  skip-unchanged × comment-level matrix; `tests/integration/live/` posts to a real PR (needs a GitHub
  token, skipped on forks)
- `docs/inputs/*.md` — one doc per action-input group, linked from `README.md`
- `.github/workflows/` — CI: static analysis & tests (incl. PR-only `context-check` and `self-test`;
  `self-test` runs the composite action itself via `uses: ./` on ubuntu and macos), release draft,
  link check, markdown lint, v2/v3 tag movers, Renovate
- `.claude/` (agents, skills), `.local_context/README.md` + `.gitignore`, and `AGENTS.md` above "This
  project" — the agentic-defaults kit, installed by `agd`; `.agd.lock` pins the kit version, packs and
  file hashes. Kit updates replace these files; don't hand-edit them (see `AGENTS.md` → "Kit files").

## How it fits together

```mermaid
flowchart LR
  gha["GitHub Actions runner"] -->|sets INPUT_* env vars| main[main.py]
  main --> inputs[ActionInputs]
  main --> report[JaCoCoReport]
  report --> scanner[JaCoCoReportInputScanner]
  scanner -->|glob| xmlfiles[("JaCoCo XML reports<br/>on disk")]
  report --> parser[JaCoCoReportParser]
  parser --> evaluator[CoverageEvaluator]
  evaluator --> generator[PRCommentGenerator]
  report --> gh["GitHub client (utils/github.py)"]
  generator --> gh
  gh -->|REST API| ghapi[("GitHub API<br/>External")]
  main -->|GITHUB_OUTPUT| gha
```

`main.py` validates inputs, then `JaCoCoReport.run()` scans for JaCoCo XML files (per report-group if
configured), parses each with `JaCoCoReportParser` (cross-referencing the PR's changed files from the
GitHub API), evaluates coverage against thresholds with `CoverageEvaluator`, and renders/posts the PR
comment with `PRCommentGenerator`. Results and pass/fail are written back via `GITHUB_OUTPUT` and the
process exit code.

## Domain

- `ReportFileCoverage` — one parsed JaCoCo XML report: `overall_coverage` (`Coverage`) +
  `changed_files_coverage` (`dict[path, FileCoverage]`) + optional `group_name`.
- `Coverage` / `FileCoverage` — six JaCoCo counters each (`instruction`, `branch`, `line`,
  `complexity`, `method`, `clazz`), each a `Counter(missed, covered)` exposing `.coverage()` as a %.
- `ReportGroup` — a named set of path globs with optional per-group thresholds
  (`overall*changed*per-file`) and optional `baseline_paths`; a field falls back to
  `report-thresholds-default`, never to `global-thresholds`.
- `EvaluatedReportCoverage` — a report or group after threshold evaluation: reached %, threshold,
  pass/fail, per-changed-file pass map.
- Two independent threshold passes: **global** (`global-thresholds`: overall + changed-files-average,
  one evaluation across all reports/groups) and **per-report/group** (`report-thresholds-default` →
  group override, adds a per-changed-file check). They never fall back into each other.

## Contracts

- `action.yml` — the action's public interface (inputs/outputs/composite steps); source of truth for
  what callers configure. Kept in sync by hand with `README.md`'s Action Inputs table and
  `docs/inputs/*.md`.
- No OpenAPI/schema files. The only external contract is the GitHub REST API (PR files, issue
  comments), consumed through `jacoco_report/utils/github.py`.

## Running it

Commands are in `AGENTS.md` → "This project" (wrapped by the root `Makefile`). To run `main.py`
locally you need every `INPUT_*` env var set (see `DEVELOPER.md` → "Run Scripts Locally" for a
template script) plus GitHub-context vars (`GITHUB_REPOSITORY`, `GITHUB_EVENT_NAME=pull_request`,
`GITHUB_REF=refs/pull/<n>/merge`) and a real token to call the GitHub API. No database or other
service is needed.

## Conventions

- Logging only, never `print()`; log calls use lazy `%` formatting, not f-strings
  (`.github/copilot-instructions.md`).
- `tests/unit/test_no_direct_output.py` is an AST guard over `main.py` and `jacoco_report/`. It fails on: bare
  `print`/`pprint`; `sys.stdout`/`sys.stderr`/`__stdout__`/`__stderr__`; `from sys import stdout|stderr`;
  `traceback.print_*`; `os.write`; `sys.exit`/`exit`/`quit`/`SystemExit` with any argument that is not
  int-valued (int/bool constants, unary `+`/`-` on them, or an `IfExp` of those); `StreamHandler()` with no
  stream. Exempt as whole files: `utils/gh_action.py`, `utils/logging_config.py` (line-number allowlists
  would break on every edit).
- Every real input is read exclusively through `ActionInputs`
  (`jacoco_report/utils/gh_action.get_action_input`, `INPUT_`-prefixed env vars) — don't read
  `os.environ` elsewhere for inputs.
- Threshold strings are `*`-delimited: `global-thresholds` = `overall*changed-files-average`;
  `report-thresholds-default` / a group's `thresholds` = `overall*changed-files-average*per-changed-file`.
- No inline `# pylint: disable`; suppressions are centralized in `.pylintrc`'s `[MESSAGES CONTROL]`,
  each with a comment explaining why.
- `tests/` is excluded from pylint (`.pylintrc` `ignore-paths=tests`), mypy (`pyproject.toml`
  `exclude = "tests"`) and coverage (`omit = ["tests/*"]`).

## Key decisions

- `global-thresholds` and `report-thresholds-default`/group thresholds are intentionally two separate
  evaluation passes, not a fallback chain (repeated in comments across `coverage_evaluator.py` and
  `action_inputs.py`).
- `global-overall-scope: all` (default since v3) includes reports found by the top-level `paths` scan
  even when unmatched by any group, so the global number reflects the whole codebase;
  `groups-only` restores pre-v3 behaviour.
- Reports filtered out by `skip-unchanged` still count toward the informational overall-coverage total
  (issue #202), even though they're hidden from PR-comment rows.
- The venv is built per call in a fresh dir under `$RUNNER_TEMP` (see the `setup` invariant), not in the
  caller's workspace, so the checkout stays clean. Not a fixed path: reuse risks a stale `bin/python` after a
  Python switch and a venv planted by an earlier PR-code step. Accepted cost: reinstall on every call.
- Log injection is closed by one `WorkflowCommandSafeFormatter` on the log handler
  (`utils/logging_config.py`), which prefixes each continuation line with `| `, not by escaping at call
  sites: one place covers every log call and traceback, and intentional multi-line blocks stay readable.
  `::stop-commands::` was rejected: the formatter, excepthook and `captureWarnings` cover every channel.

## Invariants and gotchas

- `JaCoCoReportInputScanner.scan()` always returns forward-slash absolute paths
  (`_to_posix_abspath`), never OS-native separators — dev machines are both Windows and macOS, and
  this keeps results (and substring matching against them) identical on both.
- `JaCoCoReportParser` matches a changed file from the JaCoCo XML (`package`/`sourcefile`) against the
  PR's changed-file list by substring containment, after first trying to resolve it on disk via
  `os.walk` from the current working directory — ambiguous if a relative path repeats across modules.
- Pylint's real gate is `>=9.5` (`.pylintrc` `fail-under=9.5`, same number CI checks) — not 10/10.
- The `secrets` context is not allowed in a step- or job-level `if:`; GitHub rejects the whole workflow
  file as invalid and no job in it runs (issue #240: `renovate.yml` never auto-merged). Expose the
  secret via an `env:` var (e.g. `HAS_REVIEW_TOKEN: ${{ secrets.X != '' }}`) and test that instead.
- `action.yml` hands inputs to `main.py` only via the Run step's `env:` (`INPUT_<NAME>: ${{ inputs.<name> }}`,
  `-` → `_`, upper-cased) — a new input needs a line there and a `get_action_input` read in code.
- `action.yml` `run:` scripts contain no `${{ … }}` in any spelling: GitHub pastes expressions into the
  script before bash parses it, so an input there is shell injection. Use `$GITHUB_ACTION_PATH` and
  `$RUNNER_TEMP`, and quote every path. Enforced by `tests/unit/test_action_yml.py`.
- `inputs.token` may appear only in the Run step's `env.INPUT_TOKEN`. No other step contains `${{`, and the
  Run step's `${{` stay in its `env` (the exact env map is pinned by test). Never write `$GITHUB_ENV`: it
  leaks the token into the caller's later steps. Enforced by `tests/unit/test_action_yml.py`.
- `action.yml` has exactly two steps, `setup` ("Install Python dependencies") and the Run step; a test
  fails if one is added or removed.
- `setup` runs every Python call with `-I`: the cwd is the caller's checkout, and a planted module there
  must not run. It emits `::error::` and fails if `python` is not on PATH (with an `actions/setup-python`
  hint) or is below 3.11. It creates
  `venv_dir="$(mktemp -d "$RUNNER_TEMP/jacoco-report-venv.XXXXXX")"` per call with `python -I -m venv` and
  writes that venv's `bin/python` to output `python`. The Run step gets it as `JACOCO_REPORT_PYTHON`
  (`steps.setup.outputs.python`). No `activate`, no `.venv`, nothing written into `GITHUB_WORKSPACE`.
- The Run step runs `"$JACOCO_REPORT_PYTHON" -B -E -s "$GITHUB_ACTION_PATH/main.py"`. It is the one step
  without `-I`: `-I` implies `-P`, which drops `main.py`'s directory from `sys.path` and breaks
  `import jacoco_report`. `-B` stops `__pycache__` being written into the action path or caller checkout
  (`-E` ignores `PYTHONDONTWRITEBYTECODE`).
- `setup_logging` (`utils/logging_config.py`) gives the root handler `WorkflowCommandSafeFormatter` and calls
  `basicConfig(force=True)` with no `format`/`datefmt` (the handler's formatter carries them), which removes any
  root handler set up earlier. The formatter prefixes each continuation line of a record with `| `, prefixes a
  first line starting with `::` (after lstrip) with `| `, and rewrites legacy `##[` to `## [` via the shared
  `break_legacy_command_prefix` (`gh_action.py`), because the runner's v1 parser finds `##[command]` anywhere in a line.
- `set_action_output_text` (`gh_action.py`) writes multi-line outputs as `name<<ghadelimiter_<uuid4>` heredocs with a
  random delimiter per call. It raises `ValueError` before writing if the name or value contains that delimiter.
  Never use a fixed delimiter.
- Workflow file (`.github/workflows/`), enforced by `tests/unit/test_ci_workflow.py`:
  - No `run:` script contains `${{`; pass expressions via `env:` (e.g. context-check gets `github.base_ref` as `BASE_REF`).
  - Every third-party `uses:` is pinned to a full commit SHA with a `# vX.Y.Z` comment. Renovate updates the pins.
  - Every `actions/setup-python` step with `cache: pip` lists both `requirements.txt` and `requirements-dev.txt` in `cache-dependency-path`.
- `setup_logging` also installs `sys.excepthook` (uncaught exceptions are logged through the formatter, exit
  code stays 1, `KeyboardInterrupt` goes to the default hook) and calls `logging.captureWarnings(True)`. Both
  are process-wide: the autouse `tests/conftest.py` fixture `restore_process_hooks_after_test` restores them
  after every test. `restore_root_logger_after_test` does the same for the root handlers and level, and closes
  the handlers a test added. `restore_environ_after_test` snapshots `os.environ` per test and removes added keys
  and resets changed or deleted ones (e.g. `INPUT_DEBUG` set by a test); `tests/unit/test_env_isolation.py` pins it.
- Runners: the `action.yml` scripts run on ubuntu and macos runners (`shell: bash`). Windows runners are not
  a support target (owner decision). This is about the runners callers use, not dev machines (see the
  `_to_posix_abspath` bullet). No `grep -P`.
- Dependencies: `requirements.txt` is runtime only (`requests`, `pyyaml`), and `action.yml`'s `setup` step
  installs it into callers' jobs. `requirements-dev.txt` starts with `-r requirements.txt`; `make setup` and
  the CI jobs that need dev tools install it. A new runtime import (anything `main.py` or `jacoco_report/`
  imports) must go in `requirements.txt`: otherwise the action breaks in callers' jobs while the tests still
  pass, because the dev install includes it.
- `set_action_failed` escapes each message with `escape_workflow_command_data` (`%`, `\r`, `\n`; `%`
  first, then `break_legacy_command_prefix`, as in the formatter bullet). Messages can contain text from PR report XMLs, so an unescaped newline could forge a workflow
  command such as `::add-mask::`. Any new `::command::` print must go through it.
- The `self-test` CI job runs on an ubuntu/macos matrix (`fail-fast: false`). It asserts exact
  action outputs (`coverage-overall` 91.62, 8 reports) computed from `tests/data/test_project/module_large/`
  + `context/**` fixture XMLs; editing those XMLs means updating the expected values in
  `static_analysis_and_tests.yml`. Its assertions use `jq`. Its `title` is hostile (`$(…)`, backticks), and it
  asserts the marker file `$RUNNER_TEMP/jacoco-pwned` was not created. It runs with `comment-level: none`
  + `update-comment: false` — the only mode that makes no comment API call — so it works on fork PRs.

## Read more

- `docs/inputs/*.md` — one file per input group (paths, thresholds, report-groups, comment-level,
  skip-unchanged, baseline-paths, symbols-and-metric, pr-settings, debug, global-overall-scope)
- `docs/v2-v3-migration-guide.md` — breaking changes v2 → v3
- `DEVELOPER.md` — local dev setup, running scripts/tests/lint, releasing
- `.github/copilot-instructions.md` — project-specific additions for Copilot, on top of `AGENTS.md`
