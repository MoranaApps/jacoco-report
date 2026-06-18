# `report-groups`

## Theory

`report-groups` organises JaCoCo reports from multi-module projects into named groups. Each group
defines its own file globs, optional per-group thresholds, and optional baseline paths.

When `report-groups` is set, each group's own `paths` list controls which reports belong to that
group and which thresholds apply. The top-level `paths` input (default `**/jacoco.xml`) is used
separately to determine the **global overall coverage** — see
[global-overall-scope.md](global-overall-scope.md). The top-level `global-thresholds` runs as a
**separate aggregated pass** over all reports, independent of group thresholds.

## Schema

```yaml
report-groups: |
  - name: <string>            # required — group label shown in the PR comment
    paths:                    # required — one or more glob patterns
      - <glob>
      - <glob>
    thresholds: '<O>*<A>*<P>' # optional — overall * changed-avg * per-file
    baseline-paths:           # optional — baseline glob patterns for this group
      - <glob>
```

### Field reference

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | **Yes** | string | Non-empty group label. Appears as a row header in the Groups table. |
| `paths` | **Yes** | list of strings | Glob patterns for JaCoCo XML files belonging to this group. At least one non-empty entry required. |
| `thresholds` | No | string | `overall*changed-files-average*per-changed-file` (e.g. `80*70*60`). Each field is a float in `[0, 100)` or empty. Missing fields fall back to `report-thresholds-default`, then to 0.0. |
| `baseline-paths` | No | list of strings | Glob patterns for baseline XMLs for this group. Overrides top-level `baseline-paths` for this group. |

If top-level `baseline-paths` is set and multiple groups omit `baseline-paths`, inheritance is
ambiguous and grouped baseline scans are skipped for those groups.

## Threshold format

The `thresholds` value is three floats separated by `*`:

```text
overall * changed-files-average * per-changed-file
```

| Position | Dimension | Example |
|----------|-----------|---------|
| 1 | Overall coverage (all files in group) | `80` |
| 2 | Average coverage across changed files | `70` |
| 3 | Minimum coverage per individual changed file | `60` |

A field may be left empty to inherit from `report-thresholds-default`:

```text
80**       →  overall=80, avg=default, per-file=default
*70*       →  overall=default, avg=70, per-file=default
80*70*     →  overall=80, avg=70, per-file=default
```

### Threshold resolution order (per field)

```text
per-group threshold field
    → report-thresholds-default field
        → 0.0
```

`global-thresholds` is a **separate evaluation pass** over aggregated totals and is never part of
this fallback chain.

## YAML quoting rules

Any glob or threshold value that begins with `*` must be wrapped in quotes to prevent YAML from
interpreting it as a YAML alias.

```yaml
report-groups: |
  - name: backend
    paths:
      - '**/jacoco.xml'       # leading * — quotes required
      - backend/**/jacoco.xml # no leading * — quotes optional
    thresholds: '80*70*60'    # always quote thresholds
```

## Validation rules

The action fails at startup if:

- Any group has an empty or missing `name`.
- Any two groups share the same `name`.
- Any group has an empty or missing `paths` list.
- Any path in `paths` or `baseline-paths` is an empty string.
- Any threshold field is not a number in `[0, 100)`.
- The YAML block is not valid YAML.

## PR comment structure

When `report-groups` is non-empty and `comment-level` is a detail level (`full`, `changed`,
`failed`, `failed-or-changed`), the PR comment includes a Groups table between the Global summary
and the Reports table:

```text
| Metric (instruction) | Coverage | Threshold | Status |
|…| ← Global summary (always present)

| Group   | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|…| ← Groups table (present only when report-groups is non-empty)

| Report  | Coverage (O/Ch) | Threshold (O/Ch) | Status (O/Ch) |
|…| ← Reports table

| File Path | Coverage | Threshold | Status |
|…| ← Changed-files table
```

When `report-groups` is empty, or when `comment-level` is `minimal` / `none`, the Groups table
is omitted.

## Examples

### Minimal — two groups, no per-group thresholds

```yaml
report-groups: |
  - name: backend
    paths:
      - backend/**/jacoco.xml
  - name: frontend
    paths:
      - frontend/**/jacoco.xml
```

All groups inherit from `report-thresholds-default` (default `0*0*0` — no enforcement).

---

### Per-group thresholds

```yaml
report-thresholds-default: '75*60*0'
report-groups: |
  - name: backend
    paths:
      - backend/**/jacoco.xml
    thresholds: '80*70*60'   # explicit for all three fields
  - name: frontend
    paths:
      - frontend/**/jacoco.xml
    thresholds: '75**'       # overall=75; avg and per-file from report-thresholds-default
```

---

### Per-group baseline paths

```yaml
report-groups: |
  - name: backend
    paths:
      - backend/**/jacoco.xml
    thresholds: '80*70*60'
    baseline-paths:
      - baseline/backend/**/jacoco.xml
  - name: frontend
    paths:
      - frontend/**/jacoco.xml
    thresholds: '75*65*50'
    baseline-paths:
      - baseline/frontend/**/jacoco.xml
```

---

### Combined with global thresholds

`global-thresholds` always runs as a separate pass. By default (`global-overall-scope: all`) it
covers every report found by the top-level `paths` scan — including any module not assigned to a
group. Set `global-overall-scope: groups-only` to restrict it to grouped reports only.

```yaml
- uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco.xml'                # scanned for global overall (default value)
    global-thresholds: '70*0'             # aggregated overall must be ≥ 70 %
    global-overall-scope: 'all'           # default — includes ungrouped reports in global overall
    report-thresholds-default: '60*50*0'  # default for all groups
    report-groups: |
      - name: core
        paths:
          - core/**/jacoco.xml
        thresholds: '80*70*60'            # stricter per-group enforcement
      - name: plugins
        paths:
          - plugins/**/jacoco.xml
        # no thresholds — uses report-thresholds-default (60*50*0)
```

---

### With all features combined

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    report-thresholds-default: '75*60*0'
    report-groups: |
      - name: Core
        paths:
          - core/target/site/jacoco/jacoco.xml
        thresholds: '80*70*60'
      - name: Modules
        paths:
          - module-a/target/site/jacoco/jacoco.xml
          - module-b/target/site/jacoco/jacoco.xml
        thresholds: '75*65*'
        baseline-paths:
          - baseline/modules/**/*.xml
```

## See also

- [thresholds.md](thresholds.md) — `global-thresholds`, `report-thresholds-default`, threshold resolution
- [global-overall-scope.md](global-overall-scope.md) — controlling which reports count toward global overall
- [comment-level.md](comment-level.md) — Groups table visibility
- [baseline-paths.md](baseline-paths.md) — top-level baseline configuration
- [v2-v3-migration-guide.md](../v2-v3-migration-guide.md) — migrating `modules` / `modules-thresholds` to `report-groups`
- [examples/report-groups.yml](../examples/report-groups.yml) — complete workflow example
