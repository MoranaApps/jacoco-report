# `global-thresholds`, `report-thresholds-default`, and `fail-on-threshold`

## Theory

The action runs **two independent threshold passes**:

1. **Global pass** — aggregates all reports into a single overall and changed-files-average
   number and compares them against `global-thresholds`.
2. **Per-report / per-group pass** — evaluates each report or group individually using
   `report-thresholds-default` (or per-group `thresholds` when `report-groups` is configured).

`fail-on-threshold` selects which of the evaluated dimensions actually fail the action. This lets
you evaluate and display all dimensions in the comment while only enforcing a subset in CI.

## Input formats

### `global-thresholds`

```text
overall * changed-files-average
```

```text
80*70  →  overall ≥ 80 %, changed-files average ≥ 70 %
80*0   →  overall only
0*0    →  no global enforcement (default)
```

### `report-thresholds-default`

```text
overall * changed-files-average * per-changed-file
```

**Primary role: field-level fallback for `report-groups`.** When a group omits one or more fields
from its `thresholds`, the missing values come from `report-thresholds-default`. This lets you set
a baseline once and override only where groups differ.

**Threshold resolution order (per field):**

```text
per-group threshold field
    → report-thresholds-default field
        → 0.0
```

`global-thresholds` is a **separate evaluation pass** over the aggregated total and is never part
of this chain.

**Without `report-groups`:** `report-thresholds-default` becomes the threshold applied to each
report file individually. For a single-module project this duplicates `global-thresholds` — the
same data is evaluated twice. For multi-module projects without groups it does add value: a
low-coverage module cannot be masked by others at the global level.

```text
75*60*50   →  overall ≥ 75 %, avg ≥ 60 %, each changed file ≥ 50 %
0*0*60     →  only per-changed-file enforced per report
0*0*0      →  no per-report enforcement (default)
```

### `fail-on-threshold`

Comma- or newline-separated list of dimension names:

| Value | Dimension |
|-------|-----------|
| `overall` | Global overall coverage |
| `changed-files-average` | Global average over changed files |
| `per-changed-file` | Global per-changed-file and per-report / per-group per-changed-file threshold |
| `fail-unchanged` | Unchanged reports filtered by `skip-unchanged` still fail |

Leave empty (`fail-on-threshold: ''`) to disable all threshold-based failures.

Default: `overall,changed-files-average,per-changed-file`

## Impact

- `global-thresholds` drives the global summary row in the PR comment header.
- `report-thresholds-default` (and per-group `thresholds`) drive the per-report and per-group rows.
- `fail-on-threshold` controls the exit code — a dimension can appear as ❌ in the comment
  without failing the action if it is not in the `fail-on-threshold` list.

## When to use which

| Scenario | Use |
|----------|-----|
| Single-module project | `global-thresholds` only. `report-thresholds-default` evaluates the same data and adds no value. |
| Multi-module without `report-groups` | `global-thresholds` for the aggregate; `report-thresholds-default` to prevent a weak module from being masked by stronger ones. |
| Multi-module with `report-groups` | `global-thresholds` for the aggregate; `report-thresholds-default` as the baseline each group inherits when it omits a field; per-group `thresholds` for group-specific overrides. |

## Examples

### Single-module project

Only `global-thresholds` is needed. `report-thresholds-default` would evaluate the same report a
second time and is not set.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco.xml'
    global-thresholds: '80*70'
    fail-on-threshold: 'overall,changed-files-average,per-changed-file'
```

### Multi-module with `report-groups` — shared baseline, group overrides

`report-thresholds-default` sets the baseline all groups inherit. Groups override only where they
differ; `global-thresholds` guards the aggregated total independently.

```yaml
    global-thresholds: '75*0'
    report-thresholds-default: '70*60*50'
    report-groups: |
      - name: backend
        paths:
          - backend/**/jacoco.xml
        thresholds: '80*70*60'   # explicit for all three fields
      - name: frontend
        paths:
          - frontend/**/jacoco.xml
        thresholds: '75**'       # overall=75; avg and per-file from report-thresholds-default
      - name: shared-libs
        paths:
          - libs/**/jacoco.xml
        # no thresholds — fully inherits report-thresholds-default (70*60*50)
```

### Enforce overall only

```yaml
    global-thresholds: '80*0'
    fail-on-threshold: 'overall'
```

### Enforce failures for unchanged reports filtered by `skip-unchanged`

```yaml
    skip-unchanged: 'true'
    fail-on-threshold: 'fail-unchanged'
```

### Disable all threshold failures (comment only)

```yaml
    fail-on-threshold: ''
```

## See also

- [report-groups.md](report-groups.md) — per-group threshold configuration
- [skip-unchanged.md](skip-unchanged.md) — `fail-unchanged` threshold dimension
