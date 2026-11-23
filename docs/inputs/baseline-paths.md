# `baseline-paths`

## Theory

`baseline-paths` enables **Δ coverage comparison** — the PR comment and the job summary gain a
**Δ Coverage** column, and the action sets delta outputs, showing how coverage changed relative to an
established reference point, typically the `master` branch reports stored as build artifacts.

The action matches each scanned report to a baseline report by **path** first (same directory
structure), then by **report name** (the `name` of the JaCoCo XML's `<report>`, the Maven plugin's
`<title>`) for baselines kept in another directory. Each report should therefore have a unique name so
the name pairing is unambiguous. When a report has no matching baseline entry, its Δ column renders as
`0.0%` and its `reports-coverage` entry gets no `delta`.

Every Δ is a change in **percentage points**: the coverage now minus the coverage in the baseline. For
the global and group rows, reports without a baseline match count as unchanged, so a baseline that
covers only some reports still shows their change, weighted by the size of the whole set.

When `report-groups` is configured, per-group `baseline-paths` override the top-level value for
that specific group. If top-level `baseline-paths` is set and multiple groups omit their own
`baseline-paths`, inheritance is ambiguous and grouped baseline scans are skipped for those groups.

## Valid values

Newline-separated glob patterns resolved relative to the repository root.

```text
baseline/master/jacoco/**/*.xml
```

## Impact

- Adds a **Δ Coverage** column to all comment tables (global, groups, reports, changed-files).
- The column is omitted only when no baseline data exists at all.
- Sets the outputs `coverage-overall-delta` and `coverage-changed-files-delta` (the global row's Δ,
  e.g. `-0.59`) and adds `delta` (`{"overall": …, "changed_files": …}`) to each matched entry of
  `reports-coverage` and `groups-coverage`. The outputs are empty, and no entry gets `delta`, when
  there is no baseline or no report matched one. See [README → Outputs](../../README.md#outputs).
- With `skip-unchanged` and `evaluate-unchanged: false`, the global Δ (comment and outputs) covers
  only the reports with changed files, while `coverage-overall` still counts the filtered ones.
- Has no effect on threshold evaluation unless `fail-on-threshold` includes `no-decrease`. Then the baseline is
  the reference of that gate. See [thresholds.md](thresholds.md#no-decrease-rules).

## Examples

### Compare against stored master reports

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    paths: '**/jacoco/**/*.xml'
    baseline-paths: 'baseline/master/jacoco/**/*.xml'
```

### Warn when coverage dropped

```yaml
- name: Publish JaCoCo Report
  id: jacoco
  uses: MoranaApps/jacoco-report@v3
  with:
    paths: '**/jacoco/**/*.xml'
    baseline-paths: 'baseline/master/jacoco/**/*.xml'

- name: Warn on a coverage drop
  # The comparison reads the output as a number; an empty output (no baseline) counts as 0.
  if: steps.jacoco.outputs.coverage-overall-delta < 0
  run: echo "::warning::Overall coverage dropped against the baseline."
```

### Fail when coverage dropped

Fails the step when overall coverage drops against the baseline. Listing `no-decrease` replaces the default
`fail-on-threshold` list, so add the other dimensions if you want them enforced too.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    paths: '**/jacoco/**/*.xml'
    baseline-paths: 'baseline/master/jacoco/**/*.xml'
    fail-on-threshold: 'no-decrease'
```

### Per-group baselines (via `report-groups`)

See [report-groups.md](report-groups.md) — each group supports its own `baseline-paths` field.

## See also

- [report-groups.md](report-groups.md) — per-group `baseline-paths` configuration
- [comment-level.md](comment-level.md) — interaction with `baseline-paths` (Δ column visibility)
