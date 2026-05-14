# v2 → v3 Migration Guide

This guide covers every breaking change between v2.1.x and v3.0.0.
Each section shows a before/after workflow snippet and explains the new behaviour.

---

## Summary of breaking changes

| # | Area | v2 input | v3 replacement |
|---|------|----------|---------------|
| 1 | Threshold inputs | `min-coverage-overall` / `min-coverage-changed-files` / `min-coverage-per-changed-file` | `global-thresholds` (overall + changed-files-average) + `report-thresholds-default` or group `thresholds` (per-changed-file) |
| 2 | Comment verbosity | `sensitivity` | Removed — detail is always on |
| 3 | Comment mode | `comment-mode` | Removed — single comment always |
| 4 | Module grouping | `modules` + `modules-thresholds` | `report-groups` (YAML) |
| 5 | Unchanged reports | `skip-unchanged` | Reworked — now a scan-stage filter |
| 6 | Threshold failure | `fail-on-threshold: true/false` | Deprecated — use list form |
| 7 | Comment detail level | `comment-level: minimal/full` | Expanded to six levels |

---

## 1. Threshold inputs mapping in v3

In v3, overall and changed-files-average thresholds map to `global-thresholds`.
Per-changed-file thresholds map to `report-thresholds-default` (or per-group `thresholds`).

**v2:**
```yaml
- uses: MoranaApps/jacoco-report@v2
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    paths: '**/jacoco.xml'
    min-coverage-overall: '80'
    min-coverage-changed-files: '70'
    min-coverage-per-changed-file: '60'
```

**v3:**
```yaml
- uses: MoranaApps/jacoco-report@v3
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    paths: '**/jacoco.xml'
    global-thresholds: '80*70*0'
    report-thresholds-default: '0*0*60'
```

`global-thresholds` uses `overall*changed-files-average*reserved-third`.
The aggregated evaluation uses overall and changed-files-average values.
Per-changed-file checks come from report/group thresholds.

---

## 2. `sensitivity` — removed

The `sensitivity` input (`detail` / `summary` / `minimal`) no longer exists.
Detail output is always produced. Remove the input from your workflow.

**v2:**
```yaml
    sensitivity: 'summary'
```

**v3:**
```yaml
    # Remove — detail output is always on.
    # Use comment-level (see section 7) to control what rows appear.
```

---

## 3. `comment-mode` — removed

The `comment-mode` input (`single` / `multi` / `module`) no longer exists.
A single unified PR comment is always produced. Remove the input.

**v2:**
```yaml
    comment-mode: 'single'
```

**v3:**
```yaml
    # Remove — single comment is the only mode.
```

---

## 4. `modules` + `modules-thresholds` → `report-groups`

Module grouping is replaced by the `report-groups` input, which takes an inline YAML block.
Each group defines its own paths, optional per-group thresholds, and optional baseline paths.

**v2:**
```yaml
    modules: |
      backend=backend/**/jacoco.xml
      frontend=frontend/**/jacoco.xml
    modules-thresholds: |
      backend=80*70*60
      frontend=75*65*50
```

**v3:**
```yaml
    report-groups: |
      - name: backend
        paths:
          - backend/**/jacoco.xml
        thresholds: '80*70*60'
      - name: frontend
        paths:
          - frontend/**/jacoco.xml
        thresholds: '75*65*50'
```

### Group fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Group label shown in the PR comment |
| `paths` | Yes | List of glob patterns for JaCoCo XML files |
| `thresholds` | No | `overall*avg*per-file`; missing fields fall back to `report-thresholds-default` |
| `baseline-paths` | No | Per-group baseline XMLs; overrides top-level `baseline-paths` for this group |

### `report-thresholds-default`

A new `report-thresholds-default` input sets the fallback threshold for any field not specified
per group. The resolution order per field is:

```
per-group threshold field  →  report-thresholds-default field  →  0.0
```

`global-thresholds` is always a separate evaluation pass and is never part of this chain.

**Example:**
```yaml
    report-thresholds-default: '75*60*0'
    report-groups: |
      - name: backend
        paths:
          - backend/**/jacoco.xml
        thresholds: '80**'   # overall=80, avg=60 (from default), per-file=0 (from default)
```

### When no groups are configured

If `report-groups` is empty or absent, the action behaves as in v2: the three-table PR comment
structure (Global / Reports / Changed files) is unchanged.

---

## 5. `skip-unchanged` — scan-stage filter (breaking semantic change)

In v2, `skip-unchanged` suppressed comment output and violation reporting for reports with no
changed files, but only at the comment and evaluation layers (late filter).

In v3, `skip-unchanged` filters at the **scan stage** — any `ReportFileCoverage` with no changed
files is removed before evaluation begins. Each filtered report is logged at INFO:

```
Skipping report '<name>': no changed files.
```

If all reports are filtered, the action exits cleanly: no comment is posted and no violations
are raised.

**v2:**
```yaml
    skip-unchanged: 'true'
    # Effect: unchanged reports were hidden in comment and excluded from violations,
    # but still evaluated internally.
```

**v3:**
```yaml
    skip-unchanged: 'true'
    # Effect: unchanged reports are removed before any evaluation.
    # They do not appear in the comment or contribute to any threshold check.
```

### `evaluate-unchanged` (new)

To keep threshold evaluation for filtered reports while still hiding them from the comment, use
the new `evaluate-unchanged` input:

```yaml
    skip-unchanged: 'true'
    evaluate-unchanged: 'true'   # default; filtered reports still checked against their threshold
```

Set `evaluate-unchanged: 'false'` to fully exclude filtered reports from all evaluation
(equivalent to the simplest v2 skip behaviour).

### Interaction with `comment-level`

`skip-unchanged: 'true'` removes reports before `comment-level` filtering applies.
Using `comment-level: changed` without `skip-unchanged` shows only reports that have changed
files in the comment, but still evaluates all reports.

---

## 6. `fail-on-threshold` — list form only

Boolean `true` / `false` values for `fail-on-threshold` are not supported in v3.
Use a comma- or newline-separated list, or `''` to disable threshold-based failure.

| v2 value | v3 equivalent | Meaning |
|----------|--------------|---------|
| `true` | `overall,changed-files-average,per-changed-file` | Fail on any threshold breach |
| `false` | `''` | Never fail on threshold breach |

**v2:**
```yaml
    fail-on-threshold: 'true'
```

**v3 (comma-separated):**
```yaml
  fail-on-threshold: 'overall,changed-files-average,per-changed-file'
```

To fail only on the overall dimension (global overall plus report/group overall checks):
```yaml
  fail-on-threshold: 'overall'
```

Note: `overall` is not global-only; report/group overall failures also fail the action.

To enforce threshold failures for unchanged reports filtered by `skip-unchanged: 'true'`:
```yaml
  skip-unchanged: 'true'
  fail-on-threshold: 'fail-unchanged'
```

To disable threshold-based failure entirely:
```yaml
  fail-on-threshold: ''
```

---

## 7. `comment-level` — expanded option set

v3 adds four new levels. The existing `minimal` and `full` levels are unchanged.

| Level | What is shown |
|-------|--------------|
| `none` | Title only — no tables, no comment posted to GitHub |
| `minimal` | Global summary table only |
| `full` | All tables (Global, Groups if configured, Reports, Changed files) *(default)* |
| `changed` | All tables; rows with no changed files are hidden |
| `failed` | All tables; only rows failing their threshold are shown |
| `failed-or-changed` | All tables; union of `changed` and `failed` row sets |

**v2:**
```yaml
    comment-level: 'full'
```

**v3 — suppress comment entirely:**
```yaml
    comment-level: 'none'
```

**v3 — show only failing rows:**
```yaml
    comment-level: 'failed'
```

**v3 — show rows with changes or failures:**
```yaml
    comment-level: 'failed-or-changed'
```

---

## Complete before/after example

### v2 workflow
```yaml
- uses: MoranaApps/jacoco-report@v2
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    paths: '**/jacoco.xml'
    min-coverage-overall: '80'
    min-coverage-changed-files: '70'
    min-coverage-per-changed-file: '60'
    sensitivity: 'detail'
    comment-mode: 'single'
    modules: |
      backend=backend/**/jacoco.xml
      frontend=frontend/**/jacoco.xml
    modules-thresholds: |
      backend=80*70*60
      frontend=75*65*50
    skip-unchanged: 'true'
    fail-on-threshold: 'true'
    comment-level: 'full'
```

### v3 workflow
```yaml
- uses: MoranaApps/jacoco-report@v3
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    paths: '**/jacoco.xml'
    global-thresholds: '80*70*0'
    report-thresholds-default: '75*65*50'
    report-groups: |
      - name: backend
        paths:
          - backend/**/jacoco.xml
        thresholds: '80*70*60'
      - name: frontend
        paths:
          - frontend/**/jacoco.xml
        thresholds: '75*65*50'
    skip-unchanged: 'true'
    fail-on-threshold: 'overall,changed-files-average,per-changed-file'
    comment-level: 'full'
```
