# JaCoCo Report — v3.0.0 Task Tracker

> Generated from `SPEC.md` deep analysis. Tracks every task to v3.0.0 completion.
> Ordered by execution dependency: no task should start before its prerequisites are green.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Completed |
| ⬜ | Not started |
| 🔝 | Priority-elevated (do before peers) |
| ❌ | Rejected — company/team decision |
| ⏭️ | Skipped — intentional, documented below |
| 🔒 | Blocked — dependencies not met |

---

## Critical Path to v3.0.0

```
Group 0 (deps) → Task 20 🔝 → Tasks 17/18/21 → Group F (design decisions already made)
    → Task 27 (skip-unchanged) → Task 28 (report-groups) → Task 29 (thresholds-default)
    → Task 30 (comment-level) → Task 31 (fail-on-threshold)
    → Group H (integration tests) → Task 38 (migration guide) → Groups I / J / K / L
```

---

## Quick Overview

| # | Group | Task | Status | Branch | Issue |
|---|-------|------|--------|--------|-------|
| **0a** | Deps | Merge black vulnerability fix | ⬜ | `renovate/pypi-black-vulnerability` | #145 |
| **0b** | Deps | Merge GitHub Actions updates | ⬜ | `renovate/github-actions` | #147 |
| **0c** | Deps | Merge pylint update | ⬜ | `renovate/pypi-pylint` | #150 |
| **0d** | Deps | Merge pytest update | ⬜ | `renovate/pypi-pytest` | #146 |
| **0e** | Deps | Merge pytest-cov update | ⬜ | `renovate/pypi-pytest-cov` | #148 |
| **0f** | Deps | Merge coverage update | ⬜ | `renovate/pypi-coverage` | #149 |
| **0g** | Deps | Merge mypy 2.x (major — last) | ⬜ | `renovate/mypy-2.x` | #151 |
| **1** | A | Create `copilot-instructions.md` | ✅ | `chore/add-copilot-instructions` | new |
| **2** | A | Create `copilot-review-rules.md` | ✅ | `chore/add-copilot-review-rules` | new |
| **3** | B | CI concurrency cancel-in-progress | ✅ | `chore/ci-add-concurrency` | new |
| **4** | B | Fix Black job missing strategy matrix | ✅ | `fix/ci-black-matrix` | new |
| **5** | B | Fix Pylint CI `$GITHUB_OUTPUT` | ✅ | `fix/ci-pylint-github-output` | new |
| **6** | B | Split CI: unit / integration / live | ✅ | `chore/ci-split-test-jobs` | new |
| **7** | B | SHA digest pin actions | ❌ | `chore/ci-digest-pin-actions` | new |
| **8** | C | Black target-version py312 | ✅ | `chore/black-target-version-py312` | new |
| **9** | C | Create `.pylintrc` | ✅ | `chore/add-pylintrc` | new |
| **10** | C | Copyright headers in all `.py` | ❌ | `chore/add-copyright-headers` | new |
| **11** | C | Fix f-string log calls | ✅ | `fix/logging-lazy-format` | new |
| **12** | C | Complete type hints, remove bare `type: ignore` | ✅ | `chore/complete-type-hints` | new |
| **13** | D | Create `CONTRIBUTING.md` | ✅ | `docs/contributing-md` | new |
| **14** | D | Create PR template | ✅ | `docs/pr-template` | new |
| **15** | D | Create issue templates | ✅ | `docs/issue-templates` | new |
| **16** | E2 | Restore `_get_modules()` + scenarios 3–9 | ⏭️ | `fix/restore-get-modules-integration-tests` | new |
| **17** | E1 | Fix `test_violations` data path + re-enable | ✅ | `fix/test-violations-data-path` | new |
| **18** | E1 | Re-enable `modules-thresholds` validation tests | ✅ | `fix/restore-modules-thresholds-tests` | new |
| **19** | E3 | Reorganize tests → `unit/` / `integration/` | ✅ | `chore/reorganize-tests-unit-integration` | new |
| **20** | E3 | Add typed fixture factories to `conftest.py` | ✅ | `chore/add-fixture-factories` | new |
| **21** | E1 | Enforce no private-member access in tests | ✅ | `fix/no-private-access-in-tests` | new |
| **22** | F | `skip-unchanged` filter design | ✅ | N/A | #112 |
| **23** | F | v3 comment table structure design | ✅ | N/A | #108 |
| **24** | F | Baseline mapping design | ✅ | N/A | #108 |
| **25** | F | `report-thresholds-default` precedence design | ✅ | N/A | #113 |
| **26** | F | `fail-on-threshold` boolean deprecation design | ✅ | N/A | #103 |
| **27** | G | Implement `skip-unchanged` scan-stage filter | ✅ | `feature/112-Update-logic-for-input-skip_unchanged` | #112 |
| **28** | G | Implement `report-groups` YAML input | ✅ | `feature/108-report-groups-yaml-input` | #108 |
| **29** | G | Add `report-thresholds-default` input | ✅ | `feature/113-report-thresholds-default` | #113 |
| **30** | G | Expand `comment-level` full option set | ✅ | `feature/102-comment-level-full-option-set` | #102 |
| **31** | G | `fail-on-threshold` boolean deprecation impl | ✅ | `feature/103-fail-on-threshold-deprecation-evaluate-unchanged` | #103 |
| **32** | H | Integration test helpers module | ✅ | `chore/integration-test-helpers` | new |
| **33** | H | Golden snapshot tests | ✅ | `chore/golden-snapshot-tests` | new |
| **34** | H | skip-unchanged × comment-level matrix tests | ✅ | `chore/skip-unchanged-comment-level-matrix-tests` | new |
| **35** | H | Live integration smoke test | ✅ | `chore/live-integration-smoke-test` | new |
| **36** | I | Enhanced logging (thresholds + reached values) | ✅ | `feature/101-enhance-threshold-logging` | #101 |
| **37** | I | PR comment metadata | ✅ | `feature/94-pr-comment-metadata` | #94 |
| **38** | J | v2→v3 migration guide | ✅ | `docs/74-v2-v3-migration-guide` | #74 |
| **39** | J | Create `docs/` directory | ✅ | `docs/improve-docs` | new |
| **40** | J | Update `DEVELOPER.md` | ✅ | `docs/improve-docs` | new |
| **41** | J | Update `README.md` | ✅ | `docs/improve-docs` | #70 |
| **42** | J | Document `report-groups` YAML format | ✅ | `docs/improve-docs` | #98 |
| **43** | J | Create `examples/` directory | ✅ | `docs/improve-docs` | new |
| **44** | K | Remove `# pylint: disable` inline suppressions | 🔒 ⬜ | `fix/95-remove-pylint-inline-disables` | #95 |
| **45** | K | `WRITE_SNAPSHOTS` regeneration guard | 🔒 ⬜ | `chore/snapshot-write-guard` | new |
| **46** | L | Introduce Pydantic for validation | ⬜ | `feature/39-pydantic-input-validation` | #39 |
| **47** | L | SPIKE: auto-detect modules from sbt/mvn | ⬜ | `spike/71-auto-detect-modules-sbt-mvn` | #71 |
| **48** | L | Copilot GitHub Marketplace support | ⬜ | `chore/136-copilot-marketplace-support` | #136 |

---

## Skipped Tasks

### ⏭️ Task 16 — E2: Restore `_get_modules()` and scenarios 3–9

**Decision:** Skip this task intentionally.

**Rationale in SPEC.md (§6 E2):** This task's only purpose was to make v2 module behaviour green so
that task 28 (`report-groups`) could verify parity before deleting v2 code. Because task 16 is being
skipped, task 28 implementation must instead:
- Define its own acceptance baseline from the v3 design documents (§5 G3–G6)
- Not rely on a passing v2 integration test suite as a reference
- Ensure equivalent test coverage through the new `report-groups` integration tests (tasks 32–34)

**Impact on downstream tasks:**
- Task 28 (`report-groups`) — no longer has a v2 green baseline to compare against; must document this explicitly in its PR
- Task 18 (already ✅) — `modules-thresholds` validation tests have been re-enabled; their adaptation to `report-groups` format is still required as part of task 28
- No other tasks are blocked by this skip

---

## Rejected Tasks

### ❌ Task 7 — SHA digest pin GitHub Actions
**Reason:** Company policy prohibits SHA-pinning of action references.

### ❌ Task 10 — Copyright/license headers in all `.py` files
**Reason:** Avoided by explicit team decision.

---

## Detailed Task Descriptions

---

### Group 0 — Dependency Updates (user merges Renovate PRs)

Merge in strict order to avoid conflicts. Each PR is a Renovate auto-PR; no code changes required.

#### 0a — Black vulnerability fix ⬜
- **PR:** #145 | **Branch:** `renovate/pypi-black-vulnerability`
- **Why first:** Security fix — must land before any code formatting runs.

#### 0b — GitHub Actions updates ⬜
- **PR:** #147 | **Branch:** `renovate/github-actions`
- **Why:** Infra — applies to CI workflow files only.

#### 0c — pylint update ⬜
- **PR:** #150 | **Branch:** `renovate/pypi-pylint`
- **Why:** Tooling — may surface new lint warnings; address before code changes.

#### 0d — pytest update ⬜
- **PR:** #146 | **Branch:** `renovate/pypi-pytest`

#### 0e — pytest-cov update ⬜
- **PR:** #148 | **Branch:** `renovate/pypi-pytest-cov`

#### 0f — coverage update ⬜
- **PR:** #149 | **Branch:** `renovate/pypi-coverage`

#### 0g — mypy 2.x (major) ⬜
- **PR:** #151 | **Branch:** `renovate/mypy-2.x`
- **Why last:** Major version bump — may require source-level fixes to pass `mypy .`. Merge only after all other deps are stable.

---

### Group A — AI Tooling ✅ (all done)

| Task | Status |
|------|--------|
| 1 — `.github/copilot-instructions.md` | ✅ |
| 2 — `.github/copilot-review-rules.md` | ✅ |

---

### Group B — CI / Build Fixes ✅ (all done except task 7 which is rejected)

| Task | Status |
|------|--------|
| 3 — Concurrency cancel-in-progress | ✅ |
| 4 — Black job matrix fix | ✅ |
| 5 — Pylint `$GITHUB_OUTPUT` | ✅ |
| 6 — Split CI jobs | ✅ |
| 7 — SHA digest pins | ❌ |

---

### Group C — Code Quality Foundation ✅ (all done except task 10 which is rejected)

| Task | Status |
|------|--------|
| 8 — Black target-version py312 | ✅ |
| 9 — `.pylintrc` | ✅ |
| 10 — Copyright headers | ❌ |
| 11 — Fix f-string log calls | ✅ |
| 12 — Complete type hints | ✅ |

---

### Group D — GitHub Repository Setup ✅ (all done)

| Task | Status |
|------|--------|
| 13 — `CONTRIBUTING.md` | ✅ |
| 14 — PR template | ✅ |
| 15 — Issue templates | ✅ |

---

### Group E — Test Restoration

#### E1 — Current test bugs ✅ (all done)

| Task | Status |
|------|--------|
| 17 — Fix `test_violations` data path + re-enable 4 scenarios | ✅ |
| 18 — Re-enable `modules-thresholds` validation tests (10 cases) | ✅ |
| 21 — Enforce no private-member access in tests | ✅ |

#### E2 — v2 baseline restoration

| Task | Status |
|------|--------|
| 16 — Restore `_get_modules()` + scenarios 3–9 | ⏭️ Skipped (see Skipped Tasks section) |

#### E3 — v3 test infrastructure

| Task | Status |
|------|--------|
| 19 — Reorganize tests → `unit/` / `integration/` | ✅ |
| 20 — Add typed fixture factories to `conftest.py` | ✅ |

---

### Task 20 — Typed fixture factories in `conftest.py` ✅

**Priority:** Elevated — unblocks tasks 33 and 34; reduces boilerplate for all feature tests.
**Branch:** `chore/add-fixture-factories`
**Issue:** new — "Chore: add typed fixture factories to conftest.py"

**Why:** Every test file inline-constructs `ReportFileCoverage`, `Module`, and `EvaluatedCoverage` objects.
A field rename or constructor change cascades edits across all of them. Typed factories are also a
prerequisite for golden snapshot tests (task 33) and the combination matrix (task 34).

**Implementation:**
- Add factory functions to nearest `conftest.py`
- Each factory signature: `make_<type>(**overrides) -> <Type>`
- Return type annotation: `Callable[..., T]`
- Cover at minimum: `make_report_file_coverage`, `make_module`, `make_evaluated_coverage`
- All `MockerFixture` parameters must be type-annotated

**QA gate:**
```shell
pytest --cov=. tests/ --cov-fail-under=80
mypy .
```

---

### Group F — Design Research ✅ (all decided, no implementation yet)

All Group F tasks are design decisions documented in `SPEC.md §5`. No code is written in Group F tasks;
implementation lives in Group G.

| Task | Design decision | Implemented in |
|------|----------------|----------------|
| 22 — `skip-unchanged` filter semantics | §5 G3 — Option B: scan-stage filter with INFO log | Task 27 |
| 23 — v3 comment table structure | §5 G5 — dynamic 3/4-table structure with Groups table | Task 28 |
| 24 — Baseline-to-group mapping | §5 G6 — existing name-matching sufficient | Task 28 |
| 25 — `report-thresholds-default` precedence | §5 G4 — field-level fallback chain | Task 29 |
| 26 — `fail-on-threshold` boolean deprecation | §5 G8 — Option B: defer `fail-unchanged`, deprecate booleans | Task 31 |

---

### Group G — Core Feature Implementation

All Group G tasks require Group F decisions (all ✅). Run QA gate after each task.

```shell
pytest --cov=. tests/ --cov-fail-under=80
pylint $(git ls-files '*.py')
black --check $(git ls-files '*.py')
mypy .
```

---

#### Task 27 — `skip-unchanged` scan-stage filter ✅

**Branch:** `feature/112-Update-logic-for-input-skip_unchanged` *(exists — one in-progress commit)*
**Issue:** #112 | **Depends on:** Task 22 (design ✅)

**Implementation:**
1. In `jacoco_report.py`: after XML scan, remove any `ReportFileCoverage` where `changed_files_coverage == {}`; log each at INFO: `"Skipping report '<name>': no changed files."`
2. If all reports filtered: exit cleanly with log message; no comment posted; no violations raised
3. Remove late-filter logic from:
   - `pr_comment_generator.py:65` — skip-comment-if-no-changed-files block
   - `coverage_evaluator.py:170–173` — skip-violations-if-no-changed-files block
4. Add deprecation warning for boolean `fail-on-threshold` values (G8 decision)
5. Full unit tests for every `comment-level` × `skip-unchanged` combination (2 × 6 = 12 cases)

**Acceptance criteria:**
- [ ] Filter runs before evaluation, not inside generator or evaluator
- [ ] Each filtered report appears in logs at INFO
- [ ] All-filtered scenario exits cleanly without posting a comment
- [ ] Old late-filter logic deleted from both files
- [ ] 12 combination tests pass

---

#### Task 28 — `report-groups` YAML input ✅

**Branch:** `feature/108-report-groups-yaml-input`
**Issue:** #108 | **Depends on:** Tasks 23, 24 (design ✅). Note: task 16 skipped — no v2 baseline.

**YAML schema (per group entry):**
```yaml
- name: backend           # required string
  paths:                  # required list of glob strings
    - backend/**/jacoco.xml
  thresholds: "80*70*60"  # optional; O*Avg*PerFile; missing fields → task 29 fallback
  baseline-paths:         # optional list; overrides top-level baseline-paths for this group
    - baseline/backend/**/jacoco.xml
```

**Implementation:**
1. **Parser layer (`ActionInputs`)**: parse `report-groups` YAML string; validate each entry (non-empty name, at least one non-empty path glob, threshold floats 0–100 or absent)
2. **Scanner**: for each group's `paths` list, glob XML files → tag resulting `ReportFileCoverage` objects with `group_name`
3. **Evaluator**: aggregate per-group totals → `evaluated_groups_coverage: dict[str, EvaluatedCoverage]` (mirrors `evaluated_modules_coverage`)
4. **Generator** (per §5 G5):
   - When groups defined: insert Groups table between Global and Reports tables; add section-separator rows in Reports table per group
   - When no groups: existing three-table structure unchanged
5. **Remove** `modules` and `modules-thresholds` from `action.yml` and `ActionInputs`
6. Adapt task 18's re-enabled validation tests to `report-groups` YAML format

**Groups table columns:**
`Group | Coverage (O/Ch) | Threshold (O/Ch) | [Δ Coverage (O/Ch)] | Status (O/Ch)`

**Acceptance criteria:**
- [x] `report-groups` YAML parsed and validated
- [x] Invalid YAML raises a clear `ValueError` in `ActionInputs`
- [x] Each group's paths are resolved independently
- [x] Groups table appears only when `report-groups` is non-empty
- [x] `modules` and `modules-thresholds` removed from `action.yml`
- [x] Existing three-table structure intact when no groups configured
- [x] `report-groups` validation failure tests (from task 18) pass in new format

---

#### Task 29 — `report-thresholds-default` input ⬜

**Branch:** `feature/113-report-thresholds-default`
**Issue:** #113 | **Depends on:** Task 25 (design ✅), Task 28 (evaluator exists)

**Input spec:**
- Name: `report-thresholds-default`
- Default: `0*0*0`
- Format: same `O*Avg*PerFile` as `global-thresholds`

**Threshold resolution (field-level fallback):**
```
per-group threshold field → report-thresholds-default field → 0.0
```
Example: `report-thresholds-default: "75*60*0"`, group sets `thresholds: "80**"`.
Result → overall=80, avg-changed=60 (from default), per-file=0 (from default).

**Important:** `global-thresholds` is a **separate** evaluation pass — it is never in this fallback chain.

**Acceptance criteria:**
- [ ] New input accepted and parsed in `ActionInputs`
- [ ] Field-level fallback applied correctly per-group
- [ ] `global-thresholds` evaluation path unchanged
- [ ] Unit tests cover all three fallback levels (explicit / default / zero)

---

#### Task 30 — Expand `comment-level` to full option set ⬜

**Branch:** `feature/102-comment-level-full-option-set`
**Issue:** #102 | **Depends on:** Task 23 (table structure ✅), Task 28 (groups table exists)

**New levels (implement in `pr_comment_generator.py`):**

| Level | Behaviour |
|-------|-----------|
| `none` | Return after title — no tables, no GitHub comment posted |
| `minimal` | Global summary table only (existing — unchanged) |
| `full` | All tables (existing — unchanged) |
| `changed` | All tables; hide groups/reports/files with zero changed files |
| `failed` | All tables; show only rows failing their threshold |
| `failed-or-changed` | Union of `changed` + `failed` row sets |

**Acceptance criteria:**
- [ ] All six levels accepted and validated in `ActionInputs`
- [ ] `none` results in no comment posted to GitHub
- [ ] `changed` and `failed` correctly filter rows (not entire tables)
- [ ] Empty-result edge case handled gracefully for each level
- [ ] Full unit tests per level

---

#### Task 31 — `fail-on-threshold` boolean deprecation + `evaluate-unchanged` input ✅

**Branch:** `feature/103-fail-on-threshold-deprecation-evaluate-unchanged`
**Issue:** #103 | **Depends on:** Task 27 (scan-stage filter)

**Sub-task A — Boolean deprecation:**
- Detect `fail-on-threshold: true` or `false` in `ActionInputs`
- Log deprecation warning: `"WARNING: Boolean value for fail-on-threshold is deprecated. Use list form: [overall, changed-files-average, per-changed-file]"`
- Convert internally: `true` → `[overall, changed-files-average, per-changed-file]`; `false` → `[]`

**Sub-task B — `evaluate-unchanged` input (#103):**
- New input: `evaluate-unchanged` (bool, default `true`)
- When `skip-unchanged=true` AND `evaluate-unchanged=false`: filtered reports are excluded entirely (current default behavior)
- When `skip-unchanged=true` AND `evaluate-unchanged=true`: filtered reports' overall coverage is still checked against their group/default threshold

**Note:** `fail-unchanged` as a `fail-on-threshold` list value is **deferred to v3.x** (§5 G8 Option B).

**Acceptance criteria:**
- [ ] Boolean `fail-on-threshold` triggers a deprecation log warning
- [ ] `evaluate-unchanged=false` excludes filtered reports from global threshold evaluation
- [ ] `evaluate-unchanged=true` checks overall coverage of filtered reports
- [ ] No regression in standard (non-skip) evaluation path

---

### Group H — Integration Test Infrastructure

All Group H tasks depend on at least one Group G task being complete.

---

#### Task 32 — Integration test helpers module ✅

**Branch:** `chore/integration-test-helpers`
**Issue:** new | **Depends on:** Task 19 (directory structure ✅)

**Deliverables (`tests/integration/helpers.py`):**
- `capture_run(env_overrides: dict[str, str]) -> ActionResult` — sets env vars, calls `jacoco_report.run()`, captures stdout/stderr/exit-code
- Fixture assembly helpers for constructing canonical test inputs
- All functions fully type-annotated

---

#### Task 33 — Golden snapshot tests ✅

**Branch:** `chore/golden-snapshot-tests`
**Issue:** new | **Depends on:** Tasks 20, 28, 30, 32

**Deliverables:**
- `tests/integration/fixtures/` directory with canonical full-comment strings
- At minimum three snapshots: no-groups, with-groups, skip-unchanged active
- Regeneration gate: `WRITE_SNAPSHOTS=1` env var skips assertion and writes file instead
- Run as part of offline integration job (no GitHub token)

---

#### Task 34 — skip-unchanged × comment-level matrix tests ✅

**Branch:** `chore/skip-unchanged-comment-level-matrix-tests`
**Issue:** new | **Depends on:** Tasks 20, 27, 30

**Coverage:** All 2 × 6 = 12 `skip-unchanged` × `comment-level` combinations.
Verifies filter-before-evaluation semantics from task 27 across all six `comment-level` values.

---

#### Task 35 — Live integration smoke test ⬜

**Branch:** `chore/live-integration-smoke-test`
**Issue:** new | **Depends on:** Task 32

**Deliverables (`tests/integration/live/test_smoke.py`):**
- Comment creation on a test PR
- Pagination handling (>100 comments)
- Invalid token produces a clear error (not silent failure)

**CI gate:** `if: github.event.pull_request.head.repo.full_name == github.repository` (skip on forks).
Requires `GITHUB_TOKEN` secret.

---

### Group I — QoL Features

Both tasks depend on Group G being substantially complete.

#### Task 36 — Enhanced logging ⬜

**Branch:** `feature/101-enhance-threshold-logging` | **Issue:** #101

Include threshold values and reached values in log output for each evaluation step.

#### Task 37 — PR comment metadata ✅

**Branch:** `feature/94-pr-comment-metadata` | **Issue:** #94

Append to PR comments: run ID, timestamp, trigger event, action version.

---

### Group J — Documentation

Task 38 is gated on tasks 27–30 being complete. Tasks 39–43 may proceed in parallel after task 38.

#### Task 38 — v2→v3 migration guide ⬜

**Branch:** `docs/74-v2-v3-migration-guide` | **Issue:** #74
**Depends on:** Tasks 27, 28, 29, 30 (all core features done)

**Required content (before/after YAML for each breaking change):**
1. `min-coverage-overall/changed-files/per-changed-file` → `global-thresholds: "O*A*P"`
2. `sensitivity` → removed (detail is always on)
3. `comment-mode` → removed (single comment always)
4. `modules` + `modules-thresholds` → `report-groups` YAML block
5. `skip-unchanged` → new scan-stage semantics (filter before evaluation, not after)
6. `fail-on-threshold: true/false` → deprecated; use list form
7. `comment-level` → new values: `none`, `changed`, `failed`, `failed-or-changed`

#### Task 39 — Create `docs/` directory ✅

**Branch:** `docs/improve-docs` | **Issue:** new
- `docs/comment-level-guide.md` — level descriptions with visual table examples
- `docs/report-groups-format.md` — full YAML schema and field reference
- `docs/v2-v3-migration-guide.md` — already existed (task 38)

#### Task 40 — Update `DEVELOPER.md` ✅

**Branch:** `docs/improve-docs` | **Issue:** new
- Branch naming convention table
- v3-accurate local script examples (removed `modules`/`modules-thresholds`)
- Integration test section (offline + live)
- `WRITE_SNAPSHOTS=1` snapshot regeneration step
- `mypy .` command and full QA gate

#### Task 41 — Update `README.md` ✅

**Branch:** `docs/improve-docs` | **Issue:** #70
- Added Motivation section
- Added Quick Start section (before Usage)
- Added Troubleshooting section
- All examples aligned to v3 inputs
- Comment-level and report-groups sections link to `docs/`

#### Task 42 — Document `report-groups` YAML format ✅

**Branch:** `docs/improve-docs` | **Issue:** #98
- Created `docs/report-groups-format.md` with full schema, field reference, threshold resolution, quoting rules, and examples
- README `report-groups` section links to the new doc

#### Task 43 — Create `examples/` directory ✅

**Branch:** `docs/improve-docs` | **Issue:** new
- `examples/basic.yml` — minimal config with `global-thresholds`
- `examples/report-groups.yml` — multi-group YAML with per-group thresholds and baseline
- `examples/migration-v2-to-v3.yml` — annotated before/after side-by-side

---

### Group K — Code Quality Cleanup

#### Task 44 — Remove `# pylint: disable` inline suppressions ⬜

**Branch:** `fix/95-remove-pylint-inline-disables` | **Issue:** #95
**Depends on:** Task 9 (`.pylintrc` ✅)

Replace inline disables with proper code fixes or `.pylintrc` entries with documented justification.

#### Task 45 — `WRITE_SNAPSHOTS` regeneration guard ⬜

**Branch:** `chore/snapshot-write-guard` | **Issue:** new
**Depends on:** Task 33

Ensure golden snapshots can be updated safely via `WRITE_SNAPSHOTS=1` without manual file editing.

---

### Group L — Tech Debt (post-v3.0.0)

These tasks are not on the critical path for v3.0.0 and can proceed in parallel or after release.

#### Task 46 — Introduce Pydantic ⬜

**Branch:** `feature/39-pydantic-input-validation` | **Issue:** #39

Replace manual validation in `ActionInputs` with Pydantic models.

#### Task 47 — SPIKE: auto-detect modules from sbt/mvn ⬜

**Branch:** `spike/71-auto-detect-modules-sbt-mvn` | **Issue:** #71

Research feasibility; produce a findings doc in `docs/`.

#### Task 48 — Copilot GitHub Marketplace support ⬜

**Branch:** `chore/136-copilot-marketplace-support` | **Issue:** #136

Enable Copilot integration per GitHub guidance once generally available.

---

## Dependency Map

```
Task 20 ────────────────────────────┐
                                    ↓
Task 27 ──────────────────► Task 31
    │                           │
    │   Task 28 ─────────────── │ ──────────────► Task 38
    │       │                   │                     │
    │   Task 29 ─────────────── │                     │
    │       │                   │                     ↓
    │   Task 30 ────────────────┤          Tasks 39–43 (docs)
    │       │                   │
    └───────┴────────────────► Tasks 32–35 (integration tests)
                                    │
                                    ↓
                             Tasks 36–37 (QoL)
                                    │
                                    ↓
                             Tasks 44–45 (cleanup)
```

---

## v3.0.0 Completion Checklist

- [ ] All Group 0 Renovate PRs merged
- [ ] Task 20 (fixture factories) done
- [x] Task 27 (`skip-unchanged`) done
- [x] Task 28 (`report-groups`) done
- [ ] Task 29 (`report-thresholds-default`) done
- [ ] Task 30 (full `comment-level`) done
- [ ] Task 31 (`fail-on-threshold` deprecation + `evaluate-unchanged`) done
- [ ] Tasks 32–35 (integration test infrastructure) done
- [x] Task 38 (migration guide) done
- [x] Tasks 39–43 (documentation) done
- [ ] QA gate passes on `main`: `pytest --cov=. tests/ --cov-fail-under=80 && pylint $(git ls-files '*.py') && black --check $(git ls-files '*.py') && mypy .`
