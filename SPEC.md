# JaCoCo Report — v3.0.0 Migration Specification

## Table of Contents

- [1. Starting Point — Release v2.1.2](#1-starting-point--release-v212)
- [2. Current Master State (mid-dev, pre-v3.0.0)](#2-current-master-state-mid-dev-pre-v300)
- [3. v3.0.0 Final Expectations](#3-v300-final-expectations)
- [4. v2→v3 Migration Guide Outline](#4-v2v3-migration-guide-outline)
- [5. Design Decisions Log](#5-design-decisions-log)
- [6. Ordered Task List](#6-ordered-task-list)
- [7. Reference Standards Gap Analysis](#7-reference-standards-gap-analysis)
- [8. Confirmed Test Cases (2026-05-12)](#8-confirmed-test-cases-2026-05-12)

---

## 1. Starting Point — Release v2.1.2

**Branch:** `support/2.1.x` | **Released:** 2025-09-04

### Architecture

Three comment generation modes, selected by `comment-mode`:

- `single` — one comment covering all reports aggregated
- `multi` — one comment per report file
- `module` — one comment per module (requires `modules` input)

Implemented by a factory + four classes: `PRCommentGeneratorFactory`, `SinglePRCommentGenerator`,
`MultiPRCommentGenerator`, `ModulePRCommentGenerator`.

Two output verbosity levels controlled by `sensitivity`: `detail` / `summary` / `minimal`.

### Inputs

| Input | Default | Notes |
|---|---|---|
| `token` | — | Required |
| `paths` | — | Required |
| `exclude-paths` | `''` | |
| `min-coverage-overall` | `0.0` | |
| `min-coverage-changed-files` | `0.0` | |
| `min-coverage-per-changed-file` | `0.0` | |
| `title` | — | |
| `pr-number` | `''` | |
| `metric` | `instruction` | |
| `sensitivity` | `detail` | `detail` / `summary` / `minimal` |
| `comment-mode` | `single` | `single` / `multi` / `module` |
| `modules` | `''` | Required when `comment-mode=module` |
| `modules-thresholds` | `''` | |
| `skip-unchanged` | `false` | Filters comment output to changed modules/reports |
| `baseline-paths` | — | |
| `update-comment` | `true` | |
| `pass-symbol` | `✅` | |
| `fail-symbol` | `❌` | |
| `fail-on-threshold` | `true` | `true` / `false` / list of `overall`, `changed-files-average`, `per-changed-file` |
| `debug` | `false` | |

### Outputs

`coverage-overall`, `coverage-changed-files`, `coverage-overall-passed`, `coverage-changed-files-passed`,
`reports-coverage`, `modules-coverage`, `violations`

---

## 8. Confirmed Test Cases (2026-05-12)

| Test name | Intent | Input summary | Expected output |
|---|---|---|---|
| `test_run_failed_to_retrieve_changed_files_marks_threshold_flags_failed` | Ensure operational failure path marks threshold flags as failed | `GitHub.get_pr_changed_files()` returns `None` | Violation is added and all `reached_threshold_*` flags are `False` |
| `test_run_failed_to_retrieve_changed_files` | Keep existing failure-message assertion while adding threshold assertions | Same as above | Existing violation assertion remains valid and threshold flags are `False` |
| `test_run_failed_to_retrieve_changed_files` formatting cleanup | Remove trailing whitespace-only lines in the new test block | N/A (format-only change) | No lint/format noise from trailing whitespace |
| `test_capture_run_clears_preexisting_ci_env_keys` | Ensure stale CI/action env vars do not leak into integration helper execution | Pre-existing `INPUT_*`/`GITHUB_*` vars in `os.environ`, call `capture_run()` with partial overrides | Stale `INPUT_*`/`GITHUB_*` vars are absent during `main.run()` |
| `test_capture_run_closes_handlers_added_during_run` | Ensure handlers attached during the run are closed during teardown | `main.run()` adds a custom root logger handler | Handler is removed and its `close()` is called in `capture_run()` finally block |

---

## 2. Current Master State (mid-dev, pre-v3.0.0)

### Completed Migration Steps

| Done | Change | Issue |
|---|---|---|
| ✅ | Removed `sensitivity` — always "detail" mode | #107 |
| ✅ | Removed `comment-mode` — single comment is the only mode | #107 |
| ✅ | Deleted `MultiPRCommentGenerator`, `ModulePRCommentGenerator`, `SinglePRCommentGenerator`, `PRCommentGeneratorFactory` | #107 |
| ✅ | Merged `min-coverage-overall` + `min-coverage-changed-files` + `min-coverage-per-changed-file` → `global-thresholds` (`overall*avg*per-file` format) | #105, #106 |
| ✅ | Added `comment-level` (`minimal` / `full`) replacing sensitivity | #107 |
| ✅ | Added pagination for fetching existing PR comments | #99 |
| ✅ | Bug fix: changed file default-pass when filtered out | #118 |

### Critical Migration Gaps (broken or stubbed)

- `jacoco_report/jacoco_report.py:78` — `_get_modules()` is **commented out**; the `modules` and
  `modules-thresholds` inputs are accepted but completely ignored at runtime
- `skip-unchanged` input still exists but uses old wide-scope semantics; not yet reworked per #112
- Open feature branch `feature/112-Update-logic-for-input-skip_unchanged` — one in-progress commit
- Open feature branch `feature/70-Improve-README` — documentation in progress

### Current Inputs

| Input | Default | Status |
|---|---|---|
| `token` | — | Required |
| `paths` | — | Required |
| `exclude-paths` | `''` | |
| `global-thresholds` | `0*0*0` | New in v3 (replaces 3 separate threshold inputs) |
| `title` | — | |
| `pr-number` | `''` | |
| `metric` | `instruction` | |
| `comment-level` | `full` | `minimal` / `full` — partial; more levels planned (#102) |
| `modules` | `''` | **Deprecated** — accepted, but ignored at runtime |
| `modules-thresholds` | `''` | **Deprecated** — accepted, but ignored at runtime |
| `skip-unchanged` | `false` | **Deprecated** semantics — rework pending (#112) |
| `baseline-paths` | — | |
| `update-comment` | `true` | |
| `pass-symbol` | `✅` | |
| `fail-symbol` | `❌` | |
| `fail-on-threshold` | `true` | |
| `debug` | `false` | |

---

## 3. v3.0.0 Final Expectations

### Core Architectural Change

Replace the **module-based model** with a **report-groups model**:

- **v2**: separate XML paths + `modules` mapping + per-module thresholds → multi-class generator factory
- **v3**: `report-groups` — each group bundles paths + thresholds in one input; single generator produces
  one unified comment

### Planned New / Changed Inputs

| Input | Default | Description |
|---|---|---|
| `global-thresholds` | `0*0*0` | Kept. Global overall / avg-changed-files / per-changed-file. Always evaluated as a separate pass over aggregated totals. |
| `report-thresholds-default` | `0*0*0` | **New.** Per-group/report threshold fallback. Field-level precedence: per-group → this default → 0.0 (#113, G4) |
| `report-groups` | `''` | **New.** Replaces `modules` + `modules-thresholds` (#108). Format: **YAML** (decided — see §5 G5/G6). Example: `- name: backend\n  paths: [backend/**/jacoco.xml]\n  thresholds: "80*70*60"\n  baseline-paths: [baseline/backend/**/jacoco.xml]` |
| `comment-level` | `full` | **Expanded.** `none` / `minimal` / `full` / `changed` / `failed` / `failed-or-changed` (decided — see §5 G5) |
| `skip-unchanged` | `false` | **Reworked.** Filter at scan stage — removes `ReportFileCoverage` with no changed files before evaluation. Each filtered report logged at INFO. (#112, G3) |
| `evaluate-unchanged` | `true` | **New.** When `skip-unchanged=true`, controls whether filtered reports contribute to global threshold evaluation. `false` = fully excluded. (#103) |
| `fail-on-threshold` | list | Boolean `true`/`false` **deprecated** — emits deprecation warning; treated as full list / `[]`. List values: `overall`, `changed-files-average`, `per-changed-file`. `fail-unchanged` deferred to v3.x. (#104, G8) |

### Inputs to Remove (Breaking Changes vs v2)

| Removed Input | Replacement |
|---|---|
| `min-coverage-overall` | `global-thresholds` (position 1) |
| `min-coverage-changed-files` | `global-thresholds` (position 2) |
| `min-coverage-per-changed-file` | `global-thresholds` (position 3) |
| `sensitivity` | Removed — detail is the only mode |
| `comment-mode` | Removed — single comment is the only mode |
| `modules` | `report-groups` |
| `modules-thresholds` | `report-groups` |

### Remaining Work

| Issue | Description | Priority |
|---|---|---|
| #112 | Rework `skip-unchanged`: filter reports before evaluation | Core |
| #108 | Design + implement `report-groups` input (replaces modules) | Core |
| #113 | Add `report-thresholds-default` input | Core |
| #102 | Expand `comment-level` options | Feature |
| #103 | Setting for unchanged-module evaluation | Feature |
| #101 | Enhanced logging with thresholds and reached values | QoL |
| #94 | More metadata in PR comments | QoL |
| #74 | Migration guide v2→v3 (also tracked in notes.txt) | Docs |
| #70 | README improvements (open branch) | Docs |
| #98 | Document modules threshold format | Docs |
| #95 | Refactor — remove pylint ignores | Tech debt |
| #39 | Introduce Pydantic | Tech debt |
| #71 | SPIKE: auto-detect modules from sbt/mvn | Research |

### Outputs (unchanged)

`coverage-overall`, `coverage-changed-files`, `coverage-overall-passed`, `coverage-changed-files-passed`,
`reports-coverage`, `modules-coverage`, `violations`

---

## 4. v2→v3 Migration Guide Outline

Users upgrading from v2.1.x to v3 will need to:

1. **Threshold inputs** — replace three separate inputs with one:
   ```yaml
   # v2
   min-coverage-overall: '80'
   min-coverage-changed-files: '70'
   min-coverage-per-changed-file: '60'

   # v3
   global-thresholds: '80*70*60'
   ```

2. **Remove `sensitivity`** — the input no longer exists; detail output is always used.

3. **Remove `comment-mode`** — the input no longer exists; a single unified comment is always produced.

4. **Replace `modules` + `modules-thresholds` with `report-groups`** — exact format to be defined in #108.

5. **Review `comment-level`** — if currently using `skip-unchanged` to reduce comment noise, the
   expanded `comment-level` values (`changed`, `failed`, `failed-or-changed`) will replace that use case.

6. **Review `skip-unchanged`** — the reworked semantics filter reports before evaluation, not just
   before comment output. Behavior may differ for users who relied on v2 semantics.

---

## 5. Design Decisions Log

Records confirmed decisions and open research items.

### Decided

| ID | Topic | Decision |
|---|---|---|
| G1 | `report-groups` input format | **YAML** (human-readable, supports multi-line paths and named thresholds per group) |
| G2 | `comment-level` naming | **`none` / `minimal` / `full` / `changed` / `failed` / `failed-or-changed`** — use `full` (not `detailed`) and `failed` (not `failing`) |

### Research Findings

---

#### G3 — `skip-unchanged` rework semantics

**Current v2 behavior** (wide-scope, problematic):
- `pr_comment_generator.py:65` — if `skip_unchanged=true` AND `changed_files_count() == 0`, skip comment generation
- `coverage_evaluator.py:170–173` — if `skip_unchanged=true` AND no changed files, skip global violation reporting
- Effect: the filter is applied late, inconsistently across evaluation and comment paths

**Proposed v3 behavior — Option A: Filter at scan stage (pre-evaluation)**
After scanning XML files, before evaluation, remove any `ReportFileCoverage` where `changed_files_coverage == {}`.
Evaluation, violations, and comment are all computed only on the remaining (changed) reports.
If all reports are filtered, the action exits cleanly with a log message; no comment is posted, no violations raised.
- Pro: single filtering point, consistent, easy to reason about
- Pro: aligns exactly with issue #112 ("filter out detected reports without changes before evaluation is done")
- Con: users lose visibility into unchanged reports that may be below threshold → addressed by G8

**Option B: Filter evaluation but log filtered reports at INFO**
Same as A, but log each filtered report name at INFO level: `"Skipping report '<name>': no changed files."`.
- Same semantic as A, adds traceability with zero code complexity cost
- **Recommended — adopt as the v3 implementation of #112**

**Option C: Keep filter in comment layer only (v2 behavior)**
Explicitly rejected — this is the current "too wide" behavior that issue #112 targets.

**Interaction with `comment-level`**: When `skip-unchanged=true`, filtered reports are absent entirely.
`comment-level=changed` without `skip-unchanged` shows only reports with changes in the comment.
`comment-level=changed` with `skip-unchanged=true` is redundant (filter already removes unchanged).

**Decision → Option B**: filter at scan stage, log skipped reports. Update task 22 and task 27.

---

#### G4 — `report-thresholds-default` precedence

**Two separate threshold dimensions** (must not conflate):
- `global-thresholds` → applied to the aggregated totals (Overall row, Changed Files row in the global summary table). Always evaluated. Never overridden by per-group settings.
- `report-thresholds-default` + per-group threshold → applied per report/group row in the Reports/Groups table.

**Precedence for per-group/report threshold** (field-level resolution):

```
per-group threshold field  →  highest priority (explicit)
       ↓ missing field?
report-thresholds-default  →  fallback for missing fields
       ↓ still missing / not set?
0.0 (no enforcement)       →  lowest priority
```

Example: `report-thresholds-default: "75*60*0"`, group sets `thresholds: "80**"`.

---

## 8. ActionInputs Thresholds Presence Validation (2026-05-11)

Confirmed test-case table for `ActionInputs.validate_report_groups()` key-presence validation of `thresholds`:

| Test name | Intent | Input summary | Expected output |
|---|---|---|---|
| `test_validate_report_groups_thresholds_non_string_number` | Reject numeric `thresholds` value when key is present | YAML report group with `thresholds: 0` | Validation error: `thresholds` must be a non-empty string in `O*A*P` format |
| `test_validate_report_groups_thresholds_non_string_boolean` | Reject boolean `thresholds` value when key is present | YAML report group with `thresholds: false` | Validation error: `thresholds` must be a non-empty string in `O*A*P` format |
| `test_validate_report_groups_thresholds_empty_string` | Reject empty-string `thresholds` value when key is present | YAML report group with `thresholds: ''` | Validation error: `thresholds` must be a non-empty string in `O*A*P` format |
| `test_validate_report_groups_thresholds_whitespace_only` | Reject whitespace-only `thresholds` value when key is present | YAML report group with `thresholds: '   '` | Validation error: `thresholds` must be a non-empty string in `O*A*P` format |
| `test_validate_report_groups_thresholds_missing_key_is_allowed` | Preserve behavior when `thresholds` key is absent | YAML report group without `thresholds` key | No `thresholds`-related validation error |

## 9. ActionInputs Threshold Label Consistency (2026-05-11)

Confirmed test-case table for `ActionInputs.validate_report_groups()` threshold component labels in error messages:

| Test name | Intent | Input summary | Expected output |
|---|---|---|---|
| `test_validate_report_groups_invalid_threshold_value_overall_label` | Invalid first threshold component reports `overall` label | YAML report group with `thresholds: 'x*70*60'` | Error includes `thresholds overall value 'x'` |
| `test_validate_report_groups_invalid_threshold_value_changed_files_average_label` | Invalid second threshold component uses documented label | YAML report group with `thresholds: '80*x*60'` | Error includes `thresholds changed-files-average value 'x'` |
| `test_validate_report_groups_invalid_threshold_value_changed_file_label` | Invalid third threshold component uses documented label | YAML report group with `thresholds: '80*70*x'` | Error includes `thresholds changed-file value 'x'` |
Result for that group: overall=80, avg-changed=60 (from default), per-changed=0 (from default).

`global-thresholds` is always evaluated independently and is never in this fallback chain.

**Decision → field-level fallback chain**: per-group → `report-thresholds-default` → 0.0. `global-thresholds` is always a separate evaluation pass. Update task 25 and task 29.

## 10. Threshold Parsing & Docs Consistency (Confirmed, 2026-05-11)

Confirmed test-case table for warning/message wording consistency, strict component-count validation, and evaluator docstring correctness:

| Test name | Intent | Input summary | Expected output |
|---|---|---|---|
| `test_get_report_thresholds_default_two_components_warns_per_changed_file` | Ensure 2-part report-thresholds-default warning uses documented third-component naming | `report-thresholds-default='80*70'` | Warning includes `per-changed-file threshold`; parsed tuple is `(80.0, 70.0, 0.0)` |
| `test_get_global_thresholds_two_components_warns_changed_file` | Preserve global-thresholds-specific warning wording for 2-part input | `global-thresholds='80*70'` | Warning includes `changed file threshold`; parsed tuple is `(80.0, 70.0, 0.0)` |
| `test_validate_inputs_global_thresholds_more_than_three_components_rejected` | Enforce exactly 3 components for global-thresholds after optional 2-part padding path | `global-thresholds='1*2*3*4'` | Validation error: `global-thresholds` format requires exactly 3 components |
| `test_validate_inputs_global_thresholds_two_components_still_allowed_with_padding` | Preserve existing compatibility path for 2-part global-thresholds values | `global-thresholds='1*2'` | No component-count error; warning logged; third value defaults to `0.0` |
| `test_evaluate_report_docstring_mentions_report_thresholds_default_fallback` | Keep runtime/documentation alignment for report-level threshold fallback chain | Inspect `CoverageEvaluator._evaluate_report.__doc__` | Docstring states group → `report-thresholds-default` fallback and that global thresholds are separate |

## 11. Threshold Parse Error Logging Consistency (Confirmed, 2026-05-11)

Confirmed test-case table for consistent log severity wording and accurate third-component labeling in parse-conversion errors:

| Test name | Intent | Input summary | Expected output |
|---|---|---|---|
| `test_get_global_thresholds_invalid_component_logs_warning_without_warning_prefix` | Ensure conversion failures are logged at warning level with severity-congruent message text | `global-thresholds='x*1*2'` | `logger.warning` called; message does not contain literal `Warning:` prefix |
| `test_get_report_thresholds_default_invalid_third_component_logs_per_changed_file_label` | Ensure third-component conversion failure references documented report field name | `report-thresholds-default='1*2*x'` | warning message identifies invalid `per-changed-file` component |
| `test_get_global_thresholds_invalid_third_component_logs_changed_file_label` | Preserve global-thresholds third-component label | `global-thresholds='1*2*x'` | warning message identifies invalid `changed file` component |

## 12. README Threshold Docs + Non-Behavioral Test Cleanup (Confirmed, 2026-05-11)

Confirmed test-case table for README/input docs alignment and removal of brittle docstring wording assertions:

| Test name | Intent | Input summary | Expected output |
|---|---|---|---|
| `test_readme_action_inputs_lists_report_thresholds_default` | Ensure README documents the new input already available in `action.yml` | README Action Inputs table | Includes `report-thresholds-default` with format `overall*changed-files-average*per-changed-file` and default `0*0*0` |
| `test_readme_report_groups_threshold_fallback_chain_matches_runtime` | Ensure README fallback wording matches evaluator behavior | README report-groups section and comment-level notes | States group thresholds fall back to `report-thresholds-default` (then `0.0`), and `global-thresholds` is a separate evaluation pass |
| `remove_test_evaluate_report_docstring_mentions_report_thresholds_default_fallback` | Remove brittle test tied to phrasing/line-wrap, not runtime behavior | Unit test file `tests/unit/evaluator/test_coverage_evaluator.py` | Docstring wording assertion test removed; behavioral fallback chain tests remain |

## 13. Skip-Unchanged All-Filtered Evaluate Path Fix (Confirmed, 2026-05-12)

Confirmed test-case table for all-filtered `skip-unchanged=true` + `evaluate-unchanged=true` behavior and stale-comment cleanup consistency:

| Test name | Intent | Input summary | Expected output |
|---|---|---|---|
| `test_skip_unchanged_all_filtered_evaluate_unchanged_true_uses_unchanged_reports_for_global_threshold` | Prevent false global failure when unchanged reports are evaluated in result-only path | `skip-unchanged=true`, `evaluate-unchanged=true`, all reports unchanged, global overall threshold > 0, unchanged overall coverage above threshold | Global overall passes from unchanged report totals; no global overall violation is produced |
| `test_skip_unchanged_all_filtered_evaluate_unchanged_true_still_fails_global_when_unchanged_totals_below_threshold` | Preserve real global-threshold failure when unchanged totals are below minimum | `skip-unchanged=true`, `evaluate-unchanged=true`, all reports unchanged, global overall threshold > 0, unchanged overall coverage below threshold | Global overall fails with threshold violation and failed status |
| `test_skip_unchanged_all_filtered_evaluate_unchanged_true_deletes_stale_comment` | Keep stale-comment cleanup behavior aligned across both early-return branches | `skip-unchanged=true`, `evaluate-unchanged=true`, all reports filtered, `update-comment=true`, existing JaCoCo comment | Existing JaCoCo comment is deleted once before return |

## 14. Strict Boolean Inputs + Skip-Log Wording (Confirmed, 2026-05-12)

Confirmed test-case table for raw boolean validation and skip-unchanged logging clarity when `evaluate-unchanged` is enabled:

| Test name | Intent | Input summary | Expected output |
|---|---|---|---|
| `test_get_skip_unchanged_mixed_case_true` | Accept canonical boolean values case-insensitively | `skip-unchanged=' TrUe '` | Returns `True` |
| `test_get_skip_unchanged_invalid_literal_raises_value_error` | Reject non-boolean literal for strict boolean parser | `skip-unchanged='yes'` | Raises `ValueError` with `true/false` guidance |
| `test_get_evaluate_unchanged_invalid_literal_raises_value_error` | Reject non-boolean literal for evaluate-unchanged | `evaluate-unchanged='on'` | Raises `ValueError` with `true/false` guidance |
| `test_get_update_comment_invalid_literal_raises_value_error` | Reject non-boolean literal for update-comment | `update-comment='enabled'` | Raises `ValueError` with `true/false` guidance |
| `test_get_debug_invalid_literal_raises_value_error` | Reject non-boolean literal for debug | `debug='1'` | Raises `ValueError` with `true/false` guidance |
| `test_validate_inputs_rejects_invalid_skip_unchanged_literal` | Ensure input validation surfaces strict boolean parse failures | Strict parser raises for `skip-unchanged` | Validation logs the boolean error and exits with code 1 |
| `test_skip_unchanged_evaluate_unchanged_true_logs_threshold_result_clarification` | Clarify unchanged-report filtering semantics in logs | `skip-unchanged=true`, `evaluate-unchanged=true`, unchanged report | Log says report is filtered from comment rows/changed-files evaluation while overall threshold checks may still apply |

## 15. Mixed Skip+Evaluate Global Result Correctness (Confirmed, 2026-05-12)

Confirmed test-case table for `skip-unchanged=true` + `evaluate-unchanged=true` mixed inputs where unchanged reports are filtered from comment rows but must still influence global threshold outcomes:

| Test name | Intent | Input summary | Expected output |
|---|---|---|---|
| `test_skip_unchanged_evaluate_unchanged_true_mixed_input_uses_all_reports_for_global_result` | Ensure global totals and threshold pass/fail are computed from changed+unchanged reports in mixed input flow | One unchanged low-coverage report + one changed high-coverage report, `skip-unchanged=true`, `evaluate-unchanged=true`, global overall threshold above changed-only total and above union total boundary | Global overall equals union total, global threshold failure/violation is reported from union; unchanged report remains absent from rendered report rows |
| `test_skip_report_names_hides_specified_reports_from_rendered_rows` | Verify that a report named in `skip_report_names` is absent from rendered report rows in the PR comment body | `PRCommentGenerator` constructed with one report in `skip_report_names`; evaluator has two reports | Comment body contains the non-skipped report row, does not contain the skipped report row |
| `test_skip_report_names_global_summary_still_shows_evaluator_totals` | Verify global summary table in comment reflects the evaluator totals even when report rows are filtered | Evaluator has specific `total_coverage_overall`; one report in `skip_report_names` | Global summary contains the evaluator's total, not the value it would have without the skipped report |
| `test_skip_report_names_empty_set_does_not_hide_any_reports` | Confirm default empty `skip_report_names` leaves all report rows visible | `PRCommentGenerator` with default `skip_report_names`; two reports in evaluator | Both report names appear in the comment body |

---

#### G5 — v3 comment table structure

**Current master structure** (from `pr_comment_generator.py:80–86`):
```
[1] Global summary table   (Overall + Changed Files — always shown)
[2] Reports table          (one row per XML file — FULL mode only)
[3] Changed files table    (one row per changed file — FULL mode only)
```

**v3 target structure** (dynamic based on whether `report-groups` is configured):

```
Without report-groups (default):
[1] Global summary table
[2] Reports table
[3] Changed files table

With report-groups defined:
[1] Global summary table
[2] Groups table          ← NEW (replaces Module table from v2)
[3] Reports table         ← kept; each row tagged with group name
[4] Changed files table   ← kept
```

**Groups table columns** (mirrors v2 Module table):
`Group | Coverage (O/Ch) | Threshold (O/Ch) | [Δ Coverage (O/Ch)] | Status (O/Ch)`

**Reports table when groups are active**: add a `Group` column as the first column, or render group name as a section separator row (e.g., `**backend**` as a full-width row before its reports). Section separator is simpler to implement.

**comment-level interaction**:
- `minimal` → Global summary only, no Groups/Reports/Changed-files tables
- `full` → all four tables (or three when no groups)
- `changed` → all tables, but reports/groups with no changed files are hidden
- `failed` → all tables, but only failing rows shown
- `failed-or-changed` → union of `changed` + `failed` rows

**Decision → dynamic four-table structure**: Groups table is added between Global and Reports only when `report-groups` input is provided. Update task 23 and task 28.

---

#### G6 — Baseline-to-group mapping

**Existing matching mechanism**: `CoverageEvaluator` already matches baseline reports to current reports by XML report `name` attribute. This is name-based, not path-based. It works independently of how files are discovered.

**Consequence**: the baseline matching does not need to change when `report-groups` is introduced — it continues to match by report name. A baseline XML named `"Module Large Report"` will be matched to the current XML named `"Module Large Report"` regardless of which group either belongs to.

**Top-level `baseline-paths` behavior** remains: scan and load all matched baseline XMLs into a flat list. The name-matching during evaluation assigns them to the correct report automatically.

**Optional enhancement (Group-embedded baseline-paths)**:
For users who want explicit per-group baseline control, add an optional `baseline-paths` field inside the `report-groups` YAML entry:
```yaml
report-groups: |
  - name: backend
    paths:
      - backend/**/jacoco.xml
    thresholds: "80*70*60"
    baseline-paths:                     # optional override
      - baseline/backend/**/jacoco.xml
```
When present, the group's baseline-paths replace the top-level `baseline-paths` for that group's reports.
When absent, the top-level `baseline-paths` is used (existing behavior, backward compatible).

**Decision → existing name-matching is sufficient for v3**; group-embedded `baseline-paths` is an optional field in the YAML schema and is implemented/wired for baseline scan selection when provided. Update task 24 and task 28.

---

#### G7 — Migration guide content

Prerequisite: tasks 27–30 (all core features done). Content is fully determinable — see §4 for outline. No further research needed. Confirmed as a documentation writing task, not a design decision.

---

#### G8 — `fail-on-threshold: fail-unchanged` scope

**Problem statement**: with `skip-unchanged=true` and G3's Option B, a report with no changed files is filtered before evaluation. That report's overall coverage is therefore never checked. A project that drops to 10% overall in a module with no PR changes would pass silently.

**Option A: Include `fail-unchanged` in v3 scope**
Add `fail-unchanged` as a valid value in the `fail-on-threshold` list.
Semantic: when `fail-unchanged` is in the list AND `skip-unchanged=true`, reports filtered from comment/evaluation still have their **overall** coverage checked against `report-thresholds-default` (or their group threshold). Only overall is checked — changed-files metrics are not applicable.

`fail-on-threshold` list after change:
`overall` | `changed-files-average` | `per-changed-file` | `fail-unchanged`

Boolean `true` / `false` values for `fail-on-threshold` are deprecated in v3 (issue #104 "remove support of boolean input").

**Option B: Defer `fail-unchanged` to v3.x**
Ship v3 with simpler semantics: `skip-unchanged=true` always filters completely. Add `fail-unchanged` after user feedback.

**Additional decision from #104**: Remove boolean support for `fail-on-threshold`.
- `fail-on-threshold: true` → deprecated, treated as `[overall, changed-files-average, per-changed-file]`
- `fail-on-threshold: false` → deprecated, treated as `[]`
- Issue a deprecation warning in the log when boolean is detected.

**Decision → Option B for `fail-unchanged` (defer to v3.x)**; **boolean deprecation is in v3 scope**. Update task 26 and the `fail-on-threshold` input row in §3.

---

## 6. Ordered Task List

Ordered by impact: items that unlock the most downstream work come first.
v3.0.0 is complete when all items are done.

---

### Group 0 — Dependency Updates (user merges Renovate PRs)

Merge in this order to avoid conflicts:

| Step | PR | Branch | Change | Priority |
|------|-----|--------|--------|----------|
| 0a | #145 | `renovate/pypi-black-vulnerability` | black vulnerability fix | Security — merge first |
| 0b | #147 | `renovate/github-actions` | GitHub Actions updates | Infra |
| 0c | #150 | `renovate/pypi-pylint` | pylint update | Tooling |
| 0d | #146 | `renovate/pypi-pytest` | pytest update | Test infra |
| 0e | #148 | `renovate/pypi-pytest-cov` | pytest-cov update | Test infra |
| 0f | #149 | `renovate/pypi-coverage` | coverage update | Test infra |
| 0g | #151 | `renovate/mypy-2.x` | mypy 1.x → 2.0 (major) | Last — may need source fixes |

---

### Group A — AI Tooling (shapes all subsequent work)

1. ✅ **[§7.1] Create `.github/copilot-instructions.md`**
   Establishes the TDD workflow, coding contract, output discipline, and QA gate commands for all future work.
   Content: purpose, structure, coding guidelines, string formatting, docstrings, patterns, testing rules, tooling, quality gates, common pitfalls. (See §7.1 for full content list.)
   Branch: `chore/add-copilot-instructions`
   Issue: new — "Add .github/copilot-instructions.md coding contract"

2. ✅ **[§7.1] Create `.github/copilot-review-rules.md`**
   Defines default and double-check review modes, severity grouping (Blocker / Important / Nit), and domain-specific high-risk areas (GitHub API pagination, token leakage, comment-format contract, exit codes).
   Branch: `chore/add-copilot-review-rules`
   Issue: new — "Add .github/copilot-review-rules.md review contract"

---

### Group B — CI / Build Fixes (trustworthy pipeline before any code changes)

3. ✅ **[§7.2] Add `concurrency: cancel-in-progress: true` to `static_analysis_and_tests.yml`**
   Stops redundant CI runs when new commits are pushed to an open PR.
   Branch: `chore/ci-add-concurrency`
   Issue: new — "CI: add concurrency cancel-in-progress to prevent redundant runs"

4. ✅ **[QA6 / §7.2] Fix `code-format-check` job — add missing `strategy: matrix` block**
   The Black job references `${{ matrix.python-version }}` but has no matrix; it runs once against default Python. Add `strategy: matrix: ${{fromJson(needs.set-matrix.outputs.matrix)}}`.
   Branch: `fix/ci-black-matrix`
   Issue: new — "Fix: code-format-check CI job missing strategy matrix block"

5. ✅ **[§7.2] Fix Pylint CI step — store score via `$GITHUB_OUTPUT` not `$GITHUB_ENV`**
   Replace `echo "PYLINT_SCORE=..." >> $GITHUB_ENV` with `echo "score=..." >> "$GITHUB_OUTPUT"` and reference it as `${{ steps.analyze-code.outputs.score }}`.
   Branch: `fix/ci-pylint-github-output`
   Issue: new — "Fix: Pylint CI step should use GITHUB_OUTPUT not GITHUB_ENV"

6. ✅ **[§7.2] Split CI into separate job types: `unit-tests`, `integration-tests`, `live-integration-test`**
   - `unit-tests`: `pytest --ignore=tests/integration --cov=. tests/ --cov-fail-under=80 --cov-report=html`
   - `integration-tests` (offline, no token): `pytest tests/integration/ --ignore=tests/integration/live`
   - `live-integration-test`: guarded by `if: github.event.pull_request.head.repo.full_name == github.repository`; requires `GITHUB_TOKEN`
   Branch: `chore/ci-split-test-jobs`
   Issue: new — "CI: split test jobs into unit / integration / live-integration"

7. ❌ ~~**[§7.2] Switch action version tags to SHA digest pins**~~
   ~~Replace `actions/checkout@v6` style refs with digest-pinned refs (e.g., `actions/checkout@<sha>`) for supply-chain security.~~
   Rejected — company policy prohibits SHA-pinning of actions.
   Branch: `chore/ci-digest-pin-actions`
   Issue: new — "Security: pin GitHub Actions to SHA digests"

---

### Group C — Code Quality Foundation (before adding more code)

8. ✅ **[§7.4] Update `pyproject.toml` Black target-version from `py311` to `py312`**
   Aligns Black with the project's minimum supported Python version.
   Superseded — already on `py314`.
   Branch: `chore/black-target-version-py312`
   Issue: new — "Chore: align Black target-version with minimum supported Python 3.12"

9. ✅ **[§7.4] Create `.pylintrc` at repo root**
   Move all per-file `# pylint: disable` directives into a central config. Exclude `tests/` from Pylint scope. Reduces scatter and makes suppression rationale visible.
   Branch: `chore/add-pylintrc`
   Issue: new — "Chore: introduce central .pylintrc and remove inline pylint disables"

10. ❌ ~~**[§7.4] Add copyright / license header to every source file including `__init__.py`**~~
    ~~Add the project license header block to all `.py` files that are missing it.~~
    Rejected — avoided by team decision.
    Branch: `chore/add-copyright-headers`
    Issue: new — "Chore: add Apache-2.0 copyright header to all source files"

11. ✅ **[§7.4] Fix all f-string logging calls — replace with lazy `%` formatting**
    Audit every `logger.*` call in `jacoco_report/`. Replace `logger.info(f"...")` with `logger.info("...", ...)`.
    Already clean — zero f-string logger calls in codebase.
    Branch: `fix/logging-lazy-format`
    Issue: new — "Fix: replace f-string logging with lazy % formatting"

12. ✅ **[§7.4 / QA9] Complete type hints on all public functions; remove `# type: ignore` suppressions**
    Add missing return types and parameter annotations. Document any remaining `# type: ignore` with inline justification.
    Branch: `chore/complete-type-hints`
    Issue: new — "Chore: complete type hints on public API and remove bare type: ignore"

---

### Group D — GitHub Repository Setup (process + contributor experience)

13. ✅ **[§7.5] Create `CONTRIBUTING.md`**
    Include: bug reporting, feature request process, PR process, commit message convention, and **branch naming rule** (`feature/`, `fix/`, `docs/`, `chore/`) with verification snippet.
    Branch: `docs/contributing-md`
    Issue: new — "Docs: create CONTRIBUTING.md with branch naming and PR conventions"

14. ✅ **[§7.5] Create `.github/pull_request_template.md`**
    Three sections: Overview (what it solves), Release Notes (bullet list, no TBD placeholders), Related (closes #issue).
    Branch: `docs/pr-template`
    Issue: new — "Docs: add pull request template with structured sections"

15. ✅ **[§7.5] Create `.github/ISSUE_TEMPLATE/` structured YAML templates**
    Minimum set: `bug_report.yml`, `feature_request.yml`, `spike_task.yml`, `technical_debt.yml`. Optional: `devops_task.yml`, `documentation_task.yml`, `pointer.yml`.
    Branch: `docs/issue-templates`
    Issue: new — "Docs: add structured GitHub issue templates (bug, feature, spike, tech-debt)"

---

### Group E — Test Restoration (safety net before feature work)

> **Nature of this group — three distinct sub-groups:**
> - **E1** — bugs in the current test suite that are wrong regardless of v3 (fix unconditionally).
> - **E2** — v2 functionality that was silently disabled during migration; restoring it creates the acceptance
>   baseline that task 28 (`report-groups`) must match before v2 code is deleted.
> - **E3** — new test infrastructure that is not broken today but is required before v3 feature work begins.

---

#### E1 — Current test bugs (wrong today, unrelated to v3)

17. ✅ **[QA1 + QA5] Re-enable `test_violations` scenarios and fix data path**
    - Fix `test_violations` data path: `"data/test_project/**"` → `"tests/data/test_project/**"` (`tests/test_jacoco_report.py:2250`)
    - Restore the four commented-out entries in `more_source_files_scenarios` at `tests/test_jacoco_report.py:2236–2243`
    Branch: `fix/test-violations-data-path`
    Issue: new — "Fix: test_violations broken data path and re-enable disabled violation scenarios"

    **Why (current bug):** `test_violations` uses the wrong relative path `"data/test_project/**"` instead of
    `"tests/data/test_project/**"` (confirmed at `tests/test_jacoco_report.py:2250`). The scanner finds zero
    XML files, the test body is a no-op, and no violations are ever produced. All four parametrised scenarios
    are additionally commented out, so `test_violations` runs with an empty parameter list and provides zero
    coverage signal. Violation detection sets the action's exit code and drives CI failure; a regression here
    would ship unnoticed regardless of any v3 work.

18. ✅ **[QA3] Re-enable `modules-thresholds` validation tests**
    Uncomment the 10 failure cases in `tests/test_action_inputs.py:61–73`. Adapt to final `report-groups` format once task 28 is done.
    Branch: `fix/restore-modules-thresholds-tests`
    Issue: new — "Fix: re-enable commented-out modules-thresholds validation test cases"

    **Why (current bug):** All 10 failure cases for `get_modules_thresholds` are commented out with a
    `# TODO - uncomment when new format of modules thresholds will be supported` note
    (`tests/test_action_inputs.py:61–73`). These cases cover invalid-type, missing-separator, empty-name,
    empty-threshold, and non-float-value inputs. Without them the validation layer has no test coverage for
    bad input, meaning malformed values pass `ActionInputs` silently today. They must be re-enabled and
    adapted to the `report-groups` YAML format (task 28) before that input ships.

21. **[§7.3] ✅ Enforce no private-member access in tests**
    Audit all test files for accesses to `_`-prefixed members. Replace with calls to public API or add dedicated test helpers.
    Branch: `fix/no-private-access-in-tests`
    Issue: new — "Fix: remove private member (_name) access from test files"

    **Why (current wrong practice):** Private-member access is present across three test modules today:
    - `tests/evaluator/test_coverage_evaluator.py` — directly sets `evaluator._global_min_coverage_overall`,
      `evaluator._global_min_coverage_changed_files`, and calls `evaluator._review_violations()` and
      `evaluator._evaluate_module()` (lines 65–66, 80–271).
    - `tests/utils/test_github.py` — calls `github._send_request()` directly (lines 40–110).
    - `tests/test_jacoco_report.py` — patches `JaCoCoReport._scan_jacoco_xml_files` to control file
      discovery (lines 1910–1976).
    This violates the coding contract established in task 1. It also makes the suite fragile against the v3
    refactors (tasks 27–28): any internal rename breaks these tests even when public behaviour is unchanged.

---

#### E2 — v2 baseline restoration (temporarily disabled during migration; sets the bar for task 28)

16. **[QA2] Restore `_get_modules()` call and all commented-out integration test scenarios**
    - Uncomment `modules: dict[str, Module] = self._get_modules()` at `jacoco_report/jacoco_report.py:78`
    - Re-enable scenarios 3–9 in `tests/test_jacoco_report.py:1998–2009`: modules with thresholds, partial modules, multiple changed files per report, `skip_unchanged` combinations
    Branch: `fix/restore-get-modules-integration-tests`
    Issue: new — "Fix: restore _get_modules() call and re-enable commented-out integration test scenarios"

    **Why (temporary state, not a permanent fix):** `jacoco_report.py:76` hard-codes `modules = {}` and
    skips `_get_modules()` entirely — module-path mapping, parser module-tagging, and per-module threshold
    evaluation are all silently dead at runtime. Scenarios 3–9 were the only tests that exercised this path.
    Restoring them does not fix a permanent gap: `modules` + `modules_thresholds` are v2 inputs being
    replaced by `report-groups` in task 28. The purpose of this task is to make the v2 behaviour green and
    observable so that task 28 can verify its implementation matches before the v2 code is deleted.
    Once task 28 is merged, these scenarios will be replaced by equivalent `report-groups` scenarios.

---

#### E3 — v3 test infrastructure (not broken today; required before feature work begins)

19. **[§7.3] ✅ Reorganize tests into `tests/unit/` and `tests/integration/` directories**
    Move existing tests to `tests/unit/`. Create empty `tests/integration/` and `tests/integration/live/` stubs. Update all `pytest` commands and CI references.
    Branch: `chore/reorganize-tests-unit-integration`
    Issue: new — "Chore: reorganize tests into unit/ and integration/ directory structure"

    **Why (v3 preparation):** The current flat `tests/` tree is not broken, but the CI unit/integration job
    split introduced in task 6 is not structurally enforced — both jobs point at the same directory. Without
    a `tests/unit/` vs `tests/integration/` split it is impossible to run only fast tests locally or in CI,
    coverage thresholds apply equally to both buckets, and `tests/integration/live/` (stub for task 35) has
    no peers and is unreachable from any existing pytest invocation.

20. **[§7.3] Add typed fixture factories to `conftest.py`**
    Create factory functions (`make_report_file_coverage`, `make_module`, etc.) typed with `Callable[..., T]` return annotations. Reuse across test files.
    Branch: `chore/add-fixture-factories`
    Issue: new — "Chore: add typed fixture factories to conftest.py"

    **Why (v3 preparation):** The current `conftest.py` has only three fixtures: `mock_logging_setup`,
    `github`, and `jacoco_report`. Every test file constructs `ReportFileCoverage`, `Module`, and
    `EvaluatedCoverage` objects inline, duplicating boilerplate across `test_jacoco_report.py`,
    `test_coverage_evaluator.py`, `test_pr_comment_generator.py`, and the parser tests. A model field rename
    or constructor change requires edits across all of them. Typed factories are also a prerequisite for the
    golden snapshot tests in task 33 and the combination matrix in task 34.

---

### Group F — Design Research (must complete before implementing the corresponding feature)

22. **[G3 — DECIDED] Implement `skip-unchanged` as scan-stage filter** → documented in §5 G3
    ~~Research semantic options.~~ **Decision made**: filter at scan stage (Option B) — remove `ReportFileCoverage` objects with `changed_files_coverage == {}` before evaluation. Log each filtered report at INFO. If all reports are filtered, no comment, no violations, clean exit. Remove the late-filter logic currently in `pr_comment_generator.py:65` and `coverage_evaluator.py:170–173`.
    Branch: N/A (design decision — implementation in task 27)
    Issue: N/A (tracked via #112)

23. **[G5 — DECIDED] v3 comment table structure defined** → documented in §5 G5
    ~~Research table layout.~~ **Decision made**: dynamic four-table structure — Groups table (new) is inserted between Global and Reports only when `report-groups` is configured. Without groups: three-table structure unchanged. Group rows show aggregated `O/Ch` coverage per group. Report rows are tagged with their group name (section-separator row). `comment-level` filters rows within tables.
    Branch: N/A (design decision — implementation in task 28)
    Issue: N/A (tracked via #108)

24. **[G6 — DECIDED] Baseline mapping: existing name-matching is sufficient** → documented in §5 G6
    ~~Research mapping strategy.~~ **Decision made**: existing XML report-name-based matching in the evaluator handles baselines correctly regardless of groups. Top-level `baseline-paths` continues to work unchanged. Group-embedded `baseline-paths` is an optional YAML field and is wired into baseline scanning/parsing when provided.
    Branch: N/A (design decision — implementation in task 28)
    Issue: N/A (tracked via #108)

25. **[G4 — DECIDED] `report-thresholds-default` uses field-level fallback chain** → documented in §5 G4
    ~~Research precedence rule.~~ **Decision made**: per-group threshold field → `report-thresholds-default` field → 0.0. Applied field-by-field (missing fields fall through). `global-thresholds` is always a separate evaluation pass and is never part of this chain.
    Branch: N/A (design decision — implementation in task 29)
    Issue: N/A (tracked via #113)

26. **[G8 — DECIDED] Deprecate `fail-on-threshold` booleans in v3; defer `fail-unchanged` to v3.x** → documented in §5 G8
    ~~Binary scope decision.~~ **Decision made**: (1) Boolean `true`/`false` for `fail-on-threshold` is deprecated in v3 — emit a deprecation warning to the log; treat `true` as `[overall, changed-files-average, per-changed-file]` and `false` as `[]`. (2) The `fail-unchanged` value is **deferred to v3.x** — v3 ships with the simpler model where `skip-unchanged=true` filters everything.
    Branch: N/A (design decision — implementation in task 31)
    Issue: N/A (tracked via #103)

---

### Group G — Core Feature Implementation (the v3 deliverables)

27. ✅ **[#112] Implement reworked `skip-unchanged` scan-stage filter**
    Depends on: task 22 (decided — §5 G3). Close feature branch `feature/112-Update-logic-for-input-skip_unchanged`.
    Implementation steps:
    - In `jacoco_report.py`, after scanning XML files, filter out any `ReportFileCoverage` where `changed_files_coverage == {}`; log each at INFO.
    - Remove late-filter logic from `pr_comment_generator.py:65` and `coverage_evaluator.py:170–173`.
    - Add deprecation warning for boolean `fail-on-threshold` values (G8 decision).
    - Full unit test coverage for every `comment-level` × `skip-unchanged` combination.
    Branch: `feature/112-Update-logic-for-input-skip_unchanged` *(exists)*
    Issue: #112 *(exists)*

28. ✅ **[#108] Implement `report-groups` input in YAML format**
    Depends on: tasks 23 (table structure — §5 G5), 24 (baseline mapping — §5 G6). Replaces `modules` + `modules-thresholds`.
    Implementation steps:
    - Parse `report-groups` YAML: fields per entry: `name` (required), `paths` (required list), `thresholds` (optional `O*A*P`), `baseline-paths` (optional list).
    - Validate: each path glob is a non-empty string; threshold fields are floats 0–100 or absent.
    - Wire into scanner: each group's `paths` list produces a named set of `ReportFileCoverage` objects tagged with `group_name`.
    - Evaluator: aggregate per-group totals → `evaluated_groups_coverage` dict (mirrors current `evaluated_modules_coverage`).
    - Generator: when groups are defined, insert Groups table between Global and Reports tables; report rows show group section separators. When no groups, existing three-table structure unchanged.
    - Remove `modules` and `modules-thresholds` inputs from `action.yml` and `ActionInputs`.
    Branch: `feature/108-report-groups-yaml-input`
    Issue: #108 *(exists)*

29. **[#113] Add `report-thresholds-default` input**
    Depends on: task 25 (precedence — §5 G4). New input, default `0*0*0`, same format as `global-thresholds`.
    Implementation: in evaluator, for each group/report apply threshold resolution: group threshold field → `report-thresholds-default` field → 0.0.
    `global-thresholds` evaluation path is unchanged (separate pass over aggregated totals).
    Branch: `feature/113-report-thresholds-default`
    Issue: #113 *(exists)*

30. **[#102] Expand `comment-level` to full option set**
    Depends on: G2 (naming decided) and task 23 (table structure — §5 G5).
    New levels to implement in `pr_comment_generator.py`:
    - `none` — return immediately after title; no tables; no GitHub comment posted.
    - `changed` — show only groups/reports/files that have at least one changed file.
    - `failed` — show only groups/reports/files that are failing their threshold (regardless of changed status).
    - `failed-or-changed` — union of `changed` and `failed` row sets.
    Existing `minimal` (global table only) and `full` (all tables) remain unchanged.
    Full unit tests per level, including empty-result edge cases.
    Confirmed test-case table:

    | Test name | Intent | Input summary | Expected output |
    |---|---|---|---|
    | `test_validate_inputs_accepts_all_comment_levels` | Accept all six values in input validation | `comment-level = none/minimal/full/changed/failed/failed-or-changed` | `validate_inputs()` succeeds for each |
    | `test_validate_inputs_rejects_unknown_comment_level` | Keep enum validation strict | `comment-level = invalid value` | Validation logs one error listing all six allowed values |
    | `test_generate_skips_github_comment_for_none` | `none` means no PR comment is posted | `comment-level = none`, evaluator has data | No `add_comment()` and no `update_comment()` call |
    | `test_none_deletes_existing_comment_when_update_comment_enabled` | `none` cleans up stale coverage comments when updates are enabled | `comment-level = none`, existing comment present, `update-comment = true` | Matching coverage comment is deleted; no `update_comment()` or `add_comment()` call |
    | `test_none_leaves_existing_comment_when_update_comment_disabled` | `none` does not delete comments when updates are disabled | `comment-level = none`, existing comment present, `update-comment = false` | No `delete_comment()`, `update_comment()`, or `add_comment()` call |
    | `test_minimal_comment_contains_only_global_table` | `minimal` stays summary-only | `comment-level = minimal` | Global table present, groups/reports/files tables absent |
    | `test_full_comment_contains_all_tables` | `full` keeps current detailed behavior | `comment-level = full` with groups/reports/files data | Global plus groups/reports/files tables present |
    | `test_changed_filters_group_report_and_file_rows_without_changes` | `changed` shows only changed rows | `comment-level = changed`, mixed changed/unchanged groups and reports | Only rows with changed files remain; table headers still present when rows exist |
    | `test_failed_filters_only_failing_rows` | `failed` shows only threshold failures | `comment-level = failed`, mixed pass/fail rows | Only failing group/report/file rows remain |
    | `test_failed_or_changed_filters_union_of_rows` | `failed-or-changed` is a union filter | `comment-level = failed-or-changed`, rows split across fail/change states | Rows included when changed or failing |
    | `test_changed_empty_result_is_handled_gracefully` | `changed` handles zero matching rows | `comment-level = changed`, no changed rows in evaluated data | Comment posts title plus global table and empty-state text, no crash |
    | `test_failed_empty_result_is_handled_gracefully` | `failed` handles zero matching rows | `comment-level = failed`, all rows passing | Comment posts title plus global table and empty-state text, no crash |
    | `test_failed_or_changed_empty_result_is_handled_gracefully` | Union filter handles zero matches | `comment-level = failed-or-changed`, all rows unchanged and passing | Comment posts title plus global table and empty-state text, no crash |
    | `test_comment_level_skip_unchanged_matrix_posts_for_non_none_when_changed_reports_exist` | Extend current matrix from 4 to 12 cases | `skip-unchanged true/false × all six levels`, with at least one changed report | `none` posts no comment; other five levels post exactly one comment |
    | `test_comment_level_skip_unchanged_matrix_none_still_suppresses_comment` | `none` remains dominant over `skip-unchanged` | `skip-unchanged true/false`, `comment-level = none` | No comment in both cases |
    | `test_comment_level_final_pr_body_matrix` | Assert final PR body shape for all non-`none` values | Shared evaluator fixture, `comment-level = minimal/full/changed/failed/failed-or-changed` | Each level renders the expected combination of global/groups/reports/files rows |
    | `test_none_comment_content_is_title_only` | Cover the render contract for `none` directly | `comment-level = none` | `_get_comment_content()` returns title-only content with no tables |
    | `test_filtered_comment_levels_empty_result_do_not_render_detail_table_headers` | Tighten empty-result output contract | `comment-level = changed/failed/failed-or-changed`, no matching rows | Global table + empty-state text only; no detail table headers |
    | `test_validate_inputs_rejects_noncanonical_comment_level_aliases` | Reject issue-text aliases in favor of canonical names | `comment-level = failing/change and failing/detailed` | Validation exits with the canonical allowed-values error |
    Branch: `feature/102-comment-level-full-option-set`
    Issue: #102 *(exists)*

31. **[#103] Implement `fail-on-threshold` boolean deprecation + unchanged-module evaluation**
    Depends on: task 27 (#112). Two sub-tasks:
    - **Boolean deprecation**: when `fail-on-threshold` value is `true` or `false`, log a deprecation warning and convert to the list form internally.
    - **Unchanged evaluation setting** (#103): add a new input `evaluate-unchanged` (bool, default `true`) that controls whether reports filtered by `skip-unchanged` still contribute to global threshold evaluation. When `false` (default for `skip-unchanged=true` behavior), filtered reports are excluded entirely. When `true`, filtered reports' overall coverage is checked against their group/default threshold. (This is the scoped-down version of `fail-unchanged` that stays within v3.)
    Proposed test-case table (pending confirmation):

    | Test name | Intent | Input summary | Expected output |
    |---|---|---|---|
    | `test_get_fail_on_threshold_true_emits_deprecation_warning` | Keep backward compatibility for deprecated boolean `true` | `fail-on-threshold=true` | Warning logged; returns `[overall, changed-files-average, per-changed-file]` |
    | `test_get_fail_on_threshold_false_emits_deprecation_warning` | Keep backward compatibility for deprecated boolean `false` | `fail-on-threshold=false` | Warning logged; returns `[]` |
    | `test_get_evaluate_unchanged_true` | Parse new input enabled value | `evaluate-unchanged=true` | Returns `True` |
    | `test_get_evaluate_unchanged_false` | Parse new input disabled value | `evaluate-unchanged=false` | Returns `False` |
    | `test_validate_inputs_rejects_non_boolean_evaluate_unchanged` | Enforce strict boolean validation | `evaluate-unchanged` invalid literal / type | Validation logs error and exits |
    | `test_skip_unchanged_true_evaluate_unchanged_false_excludes_unchanged_from_evaluation` | Preserve current skip behavior when explicit opt-out | `skip-unchanged=true`, `evaluate-unchanged=false`, mixed changed+unchanged reports | Unchanged reports absent from evaluator inputs and no unchanged-overall violations |
    | `test_skip_unchanged_true_evaluate_unchanged_true_keeps_unchanged_for_threshold_eval` | Enable unchanged report threshold evaluation without restoring them to comment rows | `skip-unchanged=true`, `evaluate-unchanged=true`, mixed changed+unchanged reports with unchanged failing overall threshold | Action run includes violation for unchanged report overall threshold while keeping changed-only comment surface |
    | `test_skip_unchanged_true_evaluate_unchanged_true_all_unchanged_still_evaluates` | Avoid early clean exit when unchanged evaluation is enabled | `skip-unchanged=true`, `evaluate-unchanged=true`, only unchanged reports | Run does not take all-filtered early return path; evaluator runs and sets outputs/violations based on thresholds |
    | `test_skip_unchanged_false_ignores_evaluate_unchanged_and_has_no_regression` | Guarantee unchanged default flow remains stable | `skip-unchanged=false`, `evaluate-unchanged=true/false` | Same evaluation/violations behavior as current non-skip path |
    Branch: `feature/103-fail-on-threshold-deprecation-evaluate-unchanged`
    Issue: #103 *(exists)*

---

### Group H — Integration Test Infrastructure (validate the features end-to-end)

32. **[§7.3] Add integration test helpers module (`tests/integration/helpers.py`)**
    Provide `capture_run()` (sets env vars, calls `jacoco_report.run()`, returns output) and fixture assembly helpers. Pattern after reference repo.
    Branch: `chore/integration-test-helpers`
    Issue: new — "Chore: add integration test helpers module and fixture assembly utilities"

33. **[§7.3] Add golden snapshot tests for comment output**
    Store the expected full-comment string for canonical inputs in `tests/integration/fixtures/`. Add `WRITE_SNAPSHOTS=1` env-var gate to regenerate. Guards against comment-format regressions.
    Branch: `chore/golden-snapshot-tests`
    Issue: new — "Chore: add golden snapshot tests for PR comment output with WRITE_SNAPSHOTS guard"

34. **[QA8] Add tests covering all `skip-unchanged` × `comment-level` combinations**
    Covers the new filter-before-evaluation behavior (task 27) across all six `comment-level` values.
    Branch: `chore/skip-unchanged-comment-level-matrix-tests`
    Issue: new — "Test: cover all skip-unchanged × comment-level combination cases"

35. **[QA10 / §7.2] Add live integration smoke test under `tests/integration/live/`**
    Verifies comment creation, pagination, token validation against a real or HTTP-stubbed GitHub API. Gate with `if: github.event.pull_request.head.repo.full_name == github.repository` in CI.
    Branch: `chore/live-integration-smoke-test`
    Issue: new — "Test: add live integration smoke test gated on repo-owner check"

---

### Group I — QoL Features

36. **[#101] Enhance logging — include thresholds and reached values in log output**
    Branch: `feature/101-enhance-threshold-logging`
    Issue: #101 *(exists)*

37. **[#94] Add metadata to PR comments**
    Define what metadata (run ID, timestamp, trigger, action version) is appended to comments.
    Branch: `feature/94-pr-comment-metadata`
    Issue: #94 *(exists)*

---

### Group J — Documentation

38. **[G7 / #74] Write v2→v3 migration guide**
    Depends on: tasks 27–30 (all features done). No additional research needed (§5 G7).
    Content: every breaking change with before/after YAML. Must cover:
    - `min-coverage-overall/changed-files/per-changed-file` → `global-thresholds: "O*A*P"`
    - `sensitivity` → removed (detail is always on)
    - `comment-mode` → removed (single comment always)
    - `modules` + `modules-thresholds` → `report-groups` YAML block
    - `skip-unchanged` → new scan-stage semantics (filter before evaluation, not after)
    - `fail-on-threshold: true/false` → deprecated; use list form
    - `comment-level` → new values: `none`, `changed`, `failed`, `failed-or-changed`
    Branch: `docs/74-v2-v3-migration-guide`
    Issue: #74 *(exists)*

39. **[§7.5] Create `docs/` directory with extended documentation**
    Move migration guide here. Add mode diagrams and format reference for `report-groups` YAML.
    Branch: `docs/extended-docs-directory`
    Issue: new — "Docs: create docs/ directory with format reference and mode diagrams"

40. **[§7.6] Update `DEVELOPER.md`**
    Add: integration test section (offline + live), branch naming convention, `WRITE_SNAPSHOTS=1` snapshot regeneration step, updated `mypy` and `pylint` commands.
    Branch: `docs/update-developer-md`
    Issue: new — "Docs: update DEVELOPER.md with integration tests, snapshot regen, and v3 commands"

41. **[#70 / §7.6] Update `README.md`**
    Close open branch `feature/70-Improve-README`. Add Motivation section, Troubleshooting section, move Quick Start earlier. Align examples to v3 inputs.
    Branch: `feature/70-Improve-README` *(exists)*
    Issue: #70 *(exists)*

42. **[#98] Document `report-groups` YAML format and threshold format**
    Replaces the open issue about `modules-thresholds` format. Add to README and `docs/`.
    Branch: `docs/98-report-groups-format-docs`
    Issue: #98 *(exists)*

43. **[§7.5] Create `examples/` directory**
    Add at minimum: basic usage, v3 `report-groups` with YAML, v2→v3 migration before/after YAML.
    Branch: `docs/examples-directory`
    Issue: new — "Docs: add examples/ directory with basic, report-groups, and migration examples"

---

### Group K — Code Quality Cleanup

44. **[#95 / §7.4] Refactor — remove `# pylint: disable` inline suppressions**
    After `.pylintrc` is in place (task 9), replace inline disables with proper code fixes or `.pylintrc` entries with documented justification.
    Branch: `fix/95-remove-pylint-inline-disables`
    Issue: #95 *(exists)*

45. **[§7.3] Add `WRITE_SNAPSHOTS` regeneration guard to snapshot tests**
    Ensure golden snapshots (task 33) can be updated safely without manual file editing.
    Branch: `chore/snapshot-write-guard`
    Issue: new — "Chore: add WRITE_SNAPSHOTS=1 env-var guard for snapshot regeneration"

---

### Group L — Tech Debt

46. **[#39] Introduce Pydantic for model / input validation**
    Replace manual validation in `ActionInputs` with Pydantic models.
    Branch: `feature/39-pydantic-input-validation`
    Issue: #39 *(exists)*

47. **[#71] SPIKE — auto-detect modules from sbt/mvn**
    Research feasibility; produce a findings doc in `docs/`.
    Branch: `spike/71-auto-detect-modules-sbt-mvn`
    Issue: #71 *(exists)*

48. **[#136] Copilot GitHub Marketplace support**
    Enable Copilot integration per GitHub guidance once the feature is generally available.
    Branch: `chore/136-copilot-marketplace-support`
    Issue: #136 *(exists)*

---

## 6.1 Proposed Issue Bodies (new issues only)

Issues marked `new` in §6 do not yet exist in GitHub. Use these bodies when creating them.

---

### Tasks 1–2: AI Tooling files

**Title:** Add `.github/copilot-instructions.md` coding contract
**Labels:** `chore`, `documentation`
**Body:**
```
## Problem
There is no AI coding contract to guide Copilot / Claude Code sessions toward the project's testing and quality standards.

## Goal
Create `.github/copilot-instructions.md` and `.github/copilot-review-rules.md` based on the reference standard
from AbsaOSS/generate-release-notes. The files must encode:
- TDD workflow (SPEC → test-case table approval → red-green cycle)
- Output discipline (concise responses, no large pastes)
- Coding rules (type hints, lazy-% logging, f-strings in code not logs, no print())
- QA gate commands (pytest, pylint, black, mypy)
- Review severity grouping (Blocker / Important / Nit)

## Acceptance criteria
- [ ] `.github/copilot-instructions.md` exists with all sections documented in SPEC.md §7.1
- [ ] `.github/copilot-review-rules.md` exists with default and double-check modes
- [ ] Both files lint-clean and pass CI
```

---

### Tasks 3–5: CI quality gate fixes

**Title:** Fix CI quality gate bugs in `static_analysis_and_tests.yml`
**Labels:** `fix`, `ci`
**Body:**
```
## Problem
Three bugs in the CI pipeline reduce its reliability:

1. No concurrency group — redundant runs pile up on open PRs.
2. `code-format-check` job references `${{ matrix.python-version }}` but has no `strategy: matrix` block —
   it silently runs against the runner's default Python only.
3. Pylint step stores score with `$GITHUB_ENV` instead of `$GITHUB_OUTPUT`, which is deprecated.

## Goal
Fix all three in a single PR:
1. Add `concurrency: group: ${{ github.workflow }}-${{ github.ref }}` + `cancel-in-progress: true`
2. Add `strategy: matrix: ${{fromJson(needs.set-matrix.outputs.matrix)}}` to `code-format-check`
3. Replace `>> $GITHUB_ENV` with `>> "$GITHUB_OUTPUT"` in the Pylint score step

## Acceptance criteria
- [ ] Black job runs against both Python 3.12 and 3.13
- [ ] Duplicate runs are cancelled on new push to an open PR
- [ ] Pylint score referenced via `${{ steps.analyze-code.outputs.score }}`
```

---

### Task 6: Split CI test jobs

**Title:** CI: split test jobs into unit / integration / live-integration
**Labels:** `chore`, `ci`
**Body:**
```
## Goal
Separate the monolithic test job into three distinct jobs for faster feedback and clearer failure attribution:

- `unit-tests`: `pytest --ignore=tests/integration --cov=. tests/ --cov-fail-under=80 --cov-report=html`
- `integration-tests` (offline): `pytest tests/integration/ --ignore=tests/integration/live`
- `live-integration-test`: guarded by `if: github.event.pull_request.head.repo.full_name == github.repository`;
  requires `GITHUB_TOKEN`

## Acceptance criteria
- [ ] Three separate CI jobs exist and run independently
- [ ] Live test job is skipped on forks
- [ ] Coverage threshold enforced only on unit-tests job
```

---

### Task 7: Digest-pin GitHub Actions

**Title:** Security: pin all GitHub Actions to SHA digest refs
**Labels:** `chore`, `security`
**Body:**
```
## Problem
Actions pinned by tag (e.g. `actions/checkout@v6`) can silently change if the tag is moved.
This is a supply-chain risk.

## Goal
Replace all tag-pinned action refs in `.github/workflows/` with immutable SHA digest pins.
Use a tool such as `pin-github-action` or manually look up each SHA.

## Acceptance criteria
- [ ] All `uses:` lines in workflow files reference a full 40-char SHA
- [ ] A comment on the same line shows the human-readable tag for maintainability
```

---

### Tasks 8–9: Python tooling alignment

**Title:** Chore: align Black and Pylint config with Python 3.12 minimum
**Labels:** `chore`
**Body:**
```
## Goal
Two small tooling config fixes:

1. `pyproject.toml`: change `target-version = ["py311"]` to `["py312"]` in `[tool.black]`
2. Create `.pylintrc` at repo root:
   - Move all per-file `# pylint: disable` directives to central config
   - Set `ignore=tests/` to exclude test files from pylint scope
   - Document each suppression with a justification comment

## Acceptance criteria
- [ ] Black no longer targets py311 syntax
- [ ] `.pylintrc` exists and Pylint passes without inline disables
```

---

### Tasks 10–12: Code quality foundation

**Title:** Chore: copyright headers, lazy-% logging, and complete type hints
**Labels:** `chore`
**Body:**
```
## Goal
Three code-quality baseline items before new feature work begins:

1. **Copyright headers** — add Apache-2.0 header block to every `.py` file including `__init__.py`
2. **Lazy logging** — replace all `logger.info(f"...")` calls in `jacoco_report/` with
   `logger.info("...", arg)` lazy-% formatting
3. **Type hints** — add missing return types and parameter annotations on all public functions;
   replace bare `# type: ignore` with inline justification comment

## Acceptance criteria
- [ ] `grep -r "Copyright" jacoco_report/` shows a header in every file
- [ ] `grep -rn 'logger\.\(info\|debug\|warning\|error\)(f"' jacoco_report/` returns nothing
- [ ] `mypy .` passes with 0 errors and 0 bare `# type: ignore`
```

---

### Task 13: CONTRIBUTING.md

**Title:** Docs: create CONTRIBUTING.md
**Labels:** `documentation`
**Body:**
```
## Goal
Add a `CONTRIBUTING.md` that covers:
- How to report bugs (link to bug_report issue template)
- How to request features (link to feature_request template)
- PR process: one PR per issue, squash merge, passes CI
- Commit message convention: `<type>(<scope>): <subject>` (Conventional Commits)
- Branch naming: `feature/`, `fix/`, `docs/`, `chore/`, `spike/` prefixes
- Local setup commands (from DEVELOPER.md — link or copy)

## Acceptance criteria
- [ ] File exists at repo root
- [ ] Branch naming section matches the convention used in §6 of SPEC.md
```

---

### Tasks 14–15: GitHub templates

**Title:** Docs: add PR template and structured issue templates
**Labels:** `documentation`
**Body:**
```
## Goal
Add GitHub-managed templates:

**PR template** (`.github/pull_request_template.md`):
- Overview: what problem does this PR solve
- Release Notes: bullet list of user-facing changes (no "TBD" placeholders)
- Related: `Closes #<issue>`

**Issue templates** (`.github/ISSUE_TEMPLATE/`):
Minimum: `bug_report.yml`, `feature_request.yml`, `spike_task.yml`, `technical_debt.yml`

## Acceptance criteria
- [ ] PR template appears when opening a new PR
- [ ] Issue templates appear as a form in the "New Issue" picker
```

---

### Tasks 16–18: Test restoration

**Title:** Fix: restore module integration and re-enable all disabled test scenarios
**Labels:** `fix`, `test`
**Body:**
```
## Problem
Multiple test scenarios were commented out when v2→v3 migration began, leaving the test suite
with known gaps:

1. `jacoco_report/jacoco_report.py:78` — `_get_modules()` call is commented out, so all
   module-path logic is untested.
2. `tests/test_jacoco_report.py:1998-2009` — scenarios 3–9 (modules, partial modules,
   skip_unchanged combos) are disabled.
3. `tests/test_jacoco_report.py:2250` — `test_violations` uses wrong data path
   `"data/test_project/**"` instead of `"tests/data/test_project/**"`.
4. `tests/test_jacoco_report.py:2236-2243` — 4 violation scenario entries are commented out.
5. `tests/test_action_inputs.py:61-73` — 10 `get_modules_thresholds` failure cases are disabled.

## Goal
Restore all items above. Adapt `modules-thresholds` tests (#5) to the final `report-groups`
format once task 28 is merged.

## Acceptance criteria
- [ ] `_get_modules()` is called at `jacoco_report.py:78`
- [ ] All 9 `more_source_files_scenarios` are active
- [ ] `test_violations` data path is correct and all 4 entries are active
- [ ] 10 `report-groups` validation failure cases run and pass
- [ ] `pytest --cov=. tests/` coverage does not decrease
```

---

### Tasks 19–21: Test structure

**Title:** Chore: reorganize tests into unit/ and integration/ directories
**Labels:** `chore`, `test`
**Body:**
```
## Goal
Split the flat `tests/` directory into:

```
tests/
  unit/           ← existing test_*.py files moved here
  integration/
    helpers.py    ← capture_run() and fixture assembly
    live/         ← tests requiring GITHUB_TOKEN
  conftest.py     ← typed fixture factories (make_report_file_coverage, etc.)
```

Additional rules:
- No `_`-prefixed member access in any test file (access via public API only)
- Fixture factories use `Callable[..., T]` return annotations

Update all `pytest` invocations in CI and `DEVELOPER.md`.

## Acceptance criteria
- [ ] `tests/unit/` and `tests/integration/` directories exist
- [ ] CI `pytest` commands updated
- [ ] `grep -rn '\._' tests/` returns only legitimate underscore usage (not private access)
```

---

### Tasks 32–34: Integration test infrastructure

**Title:** Chore: add integration test infrastructure — helpers, snapshots, and combination coverage
**Labels:** `chore`, `test`
**Body:**
```
## Goal
Three items that form the integration test layer:

1. **Helpers module** (`tests/integration/helpers.py`):
   `capture_run(env_overrides) -> ActionResult` — sets env vars, calls `jacoco_report.run()`,
   returns stdout/stderr/exit-code. Plus fixture assembly helpers.

2. **Golden snapshot tests** (`tests/integration/fixtures/`):
   Store canonical full-comment strings for a set of reference inputs.
   Gate regeneration with `WRITE_SNAPSHOTS=1` env var.
   Run as part of offline integration job (no GitHub token needed).

3. **Combination coverage** (`tests/integration/test_skip_unchanged_x_comment_level.py`):
   All 2 × 6 = 12 `skip-unchanged` × `comment-level` combinations, verifying filter-before-
   evaluation semantics from task 27.

## Acceptance criteria
- [ ] `helpers.py` exists with typed `capture_run`
- [ ] At least 3 golden snapshot fixtures cover: no-groups, with-groups, skip-unchanged
- [ ] All 12 skip-unchanged × comment-level matrix cases covered and green
```

---

### Task 35: Live integration smoke test

**Title:** Test: add live integration smoke test gated on repo-owner check
**Labels:** `test`, `ci`
**Body:**
```
## Goal
Add `tests/integration/live/test_smoke.py` that verifies end-to-end against a real GitHub API:
- Comment is created on a test PR
- Pagination handled correctly (>100 comments)
- Invalid token produces a clear error, not a silent failure

CI job `live-integration-test` runs this file only when
`github.event.pull_request.head.repo.full_name == github.repository` (skipped on forks).
Requires `GITHUB_TOKEN` secret.

## Acceptance criteria
- [ ] Smoke test file exists under `tests/integration/live/`
- [ ] CI job skips on forks
- [ ] Test passes against a designated test repository
```

---

### Tasks 39, 40, 43: Documentation structure

**Title:** Docs: create docs/ and examples/ directories with extended reference material
**Labels:** `documentation`
**Body:**
```
## Goal
Add structured documentation directories:

**`docs/`:**
- v2→v3 migration guide (move from task 38)
- `report-groups` YAML format reference (from task 42 / #98)
- `comment-level` mode diagrams

**`examples/`:**
- `basic.yml` — minimal action config with `global-thresholds`
- `report-groups.yml` — multi-group YAML with per-group thresholds
- `migration-v2-to-v3.yml` — before/after side-by-side

**`DEVELOPER.md` updates:**
- Integration test section (offline + live)
- `WRITE_SNAPSHOTS=1` snapshot regeneration step
- Updated `mypy` and `pylint` commands for v3

## Acceptance criteria
- [ ] `docs/` directory with migration guide and format reference
- [ ] `examples/` directory with at least three workflow examples
- [ ] `DEVELOPER.md` updated sections pass review
```

---

### Tasks 33 / 45: Snapshot regeneration guard

*(Covered by "Integration test infrastructure" issue above — tasks 33 and 45 are part of the same body.)*

---

## 7. Reference Standards Gap Analysis

Comparison against [AbsaOSS/generate-release-notes](https://github.com/AbsaOSS/generate-release-notes).
Each item states what the reference repo has, what jacoco-report currently has, and what to apply.

---

### 7.1 Copilot / AI Tooling

**Reference has — jacoco-report has nothing.**

| File | Reference | jacoco-report | Action |
|---|---|---|---|
| `.github/copilot-instructions.md` | Full coding contract (style, testing, TDD, QA gates, output discipline) | Missing | Create |
| `.github/copilot-review-rules.md` | Review modes (default / double-check), severity grouping, non-goals | Missing | Create |

**Copilot instructions content to adopt:**

- **Purpose / Structure**: bullet lists, constraint words (`Must / Must not / Prefer / Avoid`), one blank line at end.
- **Output discipline**: concise responses ≤10 lines; end each change with _What changed / Why / How to verify_; no large pastes.
- **PR body management**: treat description as changelog; append under `## Update [YYYY-MM-DD]`; reference commit hash; never rewrite the whole body.
- **Inputs rule**: read via env vars in CI; centralise parsing and validation in one layer; no duplicate validation across modules.
- **Language rules**: Python 3.12+; type hints on all public functions; `logging` not `print`; lazy `%` formatting in log calls; imports at top.
- **String formatting**: prefer f-strings for templates (note: reference uses t-strings for Py3.14+; jacoco-report stays on 3.12 so f-strings apply); never f-strings/t-strings in logging calls.
- **Docstrings**: short summary line; structured sections (Parameters / Returns / Raises); no tutorials.
- **TDD workflow** (highest priority rule to adopt):
  1. Create or update `SPEC.md` in the relevant package directory before writing any code.
  2. Propose the full test-case table (name + one-line intent + input summary + expected output) and wait for confirmation.
  3. Write all failing tests first (red), then implement until green.
  4. Update `SPEC.md` after all tests pass with the confirmed test-case table.
- **Test rules**: no private-member access (`_name`) in tests; shared fixtures in nearest `conftest.py`; annotate `MockerFixture` and `Callable[..., T]`; no comments outside test methods (use `# --- section ---` separators only).
- **Copyright header**: every code file including `__init__.py` must carry the standard license header.

**Copilot review rules content to adopt:**

- Default review priority: correctness → security → tests → maintainability → style.
- Group comments by severity: **Blocker** (must fix) / **Important** (should fix) / **Nit** (optional).
- Double-check mode for high-risk PRs: re-check auth, secrets, persistence, external calls, idempotency, backward compat.
- Each comment must state: _what the issue is_ + _why it matters_ + _minimal fix_.
- Domain-specific high-risk areas to call out explicitly: GitHub API pagination/rate limits, token leakage in logs, comment-format contract strings, exit codes.

---

### 7.2 CI / Quality Gates

| Area | Reference | jacoco-report | Gap |
|---|---|---|---|
| Workflow trigger | `pull_request` only; `concurrency: cancel-in-progress: true` | `push: master` + `pull_request`; no concurrency cancel | Missing concurrency cancel; push-to-master runs are redundant |
| Action pin style | SHA digest pins (`actions/checkout@de0fac2...`) | Version tag only (`actions/checkout@v6`) | Reference uses digest pinning for supply-chain security |
| Python version | Single: `3.14` (no matrix) | Matrix: `3.12`, `3.13` | Reference chooses freshest stable; jacoco-report tests compat range — both are valid; choose one strategy and be consistent |
| Black job matrix bug | Not applicable (no matrix in Black job) | `code-format-check` job references `${{ matrix.python-version }}` but has **no** `strategy: matrix:` — runs once against default Python | Fix the matrix bug (Task QA6) |
| Test job separation | `unit-test` + `offline-integration-tests` + `integration-test-real-api` (three separate jobs) | Single `python-tests` job covering everything | Split into unit and integration jobs |
| Coverage command | `pytest --ignore=tests/integration --cov=. tests/ --cov-fail-under=80` | `pytest --cov=. -v tests/ --cov-fail-under=80` | Exclude integration tests from unit coverage; add `--cov-report=html` |
| Pylint scope | `pylint --ignore-paths='^tests/.*' $(git ls-files '*.py')` via `.pylintrc` | `pylint $(git ls-files '*.py')` with inline `# pylint: disable` scattered across source | Adopt `.pylintrc`; exclude tests from pylint run |
| Live integration gate | `if: github.event.pull_request.head.repo.full_name == github.repository` guards live API test | No live integration test at all | Add guarded live smoke test (aligned with Task QA10) |
| Pylint output variable | Stored in `$GITHUB_OUTPUT` (`score=…`) | Stored in `$GITHUB_ENV` (`PYLINT_SCORE=…`) | Prefer `$GITHUB_OUTPUT` (env is deprecated for inter-step sharing) |

---

### 7.3 Test Structure

| Area | Reference | jacoco-report | Action |
|---|---|---|---|
| Directory layout | `tests/unit/`, `tests/integration/`, `tests/integration/live/` | Flat `tests/` with domain subdirs but no unit/integration split | Reorganise into `tests/unit/` and `tests/integration/` |
| Fixture factories | Typed factory functions in `conftest.py` (`make_issue`, `make_pr`, etc.) with `Callable[..., T]` return types | `conftest.py` has minimal fixtures; no typed factories | Add typed factory fixtures to `conftest.py` |
| Integration test helpers | `helpers.py` with `build_mined_data()` and `capture_run()` | None | Add integration helpers module |
| Golden snapshot tests | `fixtures/test_full_pipeline_snapshot.md`; regenerated via `WRITE_SNAPSHOTS=1` env var | None | Add golden snapshot for full-comment output (critical for comment-format regressions) |
| Private member access | Prohibited in tests | Several tests access or mock internal paths | Enforce: test only public API |
| Section separators in tests | `# --- section ---` only; no free-standing comments | Inline comments scattered throughout test files | Align to convention |

---

### 7.4 Code Style Rules

| Rule | Reference | jacoco-report | Action |
|---|---|---|---|
| Copyright header | Every `.py` including `__init__.py` | None | Add Apache 2.0 header (or project license) to all source files |
| Logging format | Lazy `%` formatting: `logger.info("msg %s", val)` | Mix: some f-strings in log calls (e.g., `logger.info(f"...")`) | Audit and fix all f-string log calls |
| Type hints | Required on all public functions/classes | Partially present; `# type: ignore` suppressions used | Complete type coverage; remove suppressions or document each |
| `.pylintrc` | Dedicated config file at repo root | No `.pylintrc`; config only via inline `# pylint: disable` | Create `.pylintrc`; move inline disables there with justifications |
| Black target version | `py314` in `pyproject.toml` | `py311` in `pyproject.toml` | Update to match minimum supported Python (`py312`) |

---

### 7.5 GitHub Repository Files

| File | Reference | jacoco-report | Action |
|---|---|---|---|
| `CONTRIBUTING.md` | Full guide: bug reporting, feature request, PR process, **branch naming convention** | Missing | Create; include branch naming rule (`feature/`, `fix/`, `docs/`, `chore/`) |
| `.github/pull_request_template.md` | Overview + Release Notes + Related sections | Missing | Create with same three sections |
| `.github/ISSUE_TEMPLATE/` | 9 structured YAML templates: bug, feature, devops, epic, operative, spike, tech-debt, pointer, documentation | Only Renovate's dependency dashboard issue | Create structured templates; minimum: bug, feature, spike, tech-debt |
| `dependabot.yml` / `renovate.json` | Dependabot with grouped pip + github-actions; `no RN` label on auto-PRs | Renovate with `renovate.json` | Both are valid; ensure auto-update PRs are labelled to skip release notes check |
| `CODEOWNERS` | `* @miroslavpojer @tmikula-dev` | `.github/CODEOWNERS` exists (2 owners) | Already present — verify it is up to date |
| `docs/` directory | Exists with motivation and extended docs | Missing | Create for extended docs (migration guide, mode diagrams) |
| `examples/` directory | Exists with workflow examples | Missing | Create with at minimum the v2→v3 migration example |

---

### 7.6 Documentation Standards

| Area | Reference README | jacoco-report README | Action |
|---|---|---|---|
| Structure | Overview → Motivation → Quick Start → Feature detail → Troubleshooting → Developer guide → License | Usage → Inputs → Outputs → Examples → Developer → License | Add Motivation and Troubleshooting sections; move Quick Start earlier |
| Badges | Version + Marketplace | Tag + CodeRabbit Reviews | Add Marketplace badge when v3 is published |
| Motivation section | Separate `docs/motivation.md` linked from README | None | Add at minimum a paragraph; create `docs/` for extended content |
| DEVELOPER.md | Covers: setup, pylint, black, mypy, **unit tests**, **integration tests** (offline + live), coverage, run-locally script, **branch naming** | Covers: setup, pylint, black, unit tests, coverage, run-locally script | Add: integration test section (offline + live), branch naming convention, `WRITE_SNAPSHOTS` regeneration step |
| Branch naming | Defined in both `CONTRIBUTING.md` and `DEVELOPER.md`; verification shell snippet provided | Not defined anywhere | Add to `CONTRIBUTING.md` and `DEVELOPER.md` |
