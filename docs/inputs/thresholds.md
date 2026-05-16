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
overall * changed-files-average * reserved-third
```

The third field is reserved and ignored by the evaluator. Set to `0`.

```text
80*70*0   →  overall ≥ 80 %, changed-files average ≥ 70 %
80*0*0    →  overall only
0*0*0     →  no global enforcement (default)
```

### `report-thresholds-default`

```text
overall * changed-files-average * per-changed-file
```

This is the fallback for any threshold field not explicitly set in a group's `thresholds`.

```text
75*60*50   →  overall ≥ 75 %, avg ≥ 60 %, each changed file ≥ 50 %
0*0*60     →  only per-changed-file enforced
```

### `fail-on-threshold`

Comma- or newline-separated list of dimension names:

| Value | Dimension |
|-------|-----------|
| `overall` | Global overall coverage |
| `changed-files-average` | Global average over changed files |
| `per-changed-file` | Per-report / per-group per-changed-file threshold |
| `fail-unchanged` | Unchanged reports filtered by `skip-unchanged` still fail |

Leave empty (`fail-on-threshold: ''`) to disable all threshold-based failures.

Default: `overall,changed-files-average,per-changed-file`

## Impact

- `global-thresholds` drives the global summary row in the PR comment header.
- `report-thresholds-default` (and per-group `thresholds`) drive the per-report and per-file rows.
- `fail-on-threshold` controls the exit code — a dimension can appear as ❌ in the comment
  without failing the action if it is not in the `fail-on-threshold` list.

## Examples

### Standard setup — overall + changed average + per file

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    global-thresholds: '80*70*0'
    report-thresholds-default: '0*0*60'
    fail-on-threshold: 'overall,changed-files-average,per-changed-file'
```

### Enforce overall only

```yaml
    global-thresholds: '80*0*0'
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
