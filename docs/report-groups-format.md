# `report-groups` YAML Format Reference

The `report-groups` input lets you organise JaCoCo reports from multi-module projects into named
groups, each with its own path globs, optional thresholds, and optional baseline paths.

---

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
| `baseline-paths` | No | list of strings | Glob patterns for baseline XMLs for this group. When present, overrides top-level `baseline-paths` for this group. If omitted, top-level `baseline-paths` can be inherited only when exactly one group omits `baseline-paths`; otherwise inheritance is ambiguous and grouped baseline scans are skipped for omitted groups. |

---

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

---

## YAML quoting rules

Any glob or threshold value that begins with `*` must be wrapped in quotes to prevent YAML from
interpreting it as a YAML alias.

```yaml
report-groups: |
  - name: backend
    paths:
      - '**/jacoco.xml'       # leading * — quotes required
      - backend/**/jacoco.xml # no leading * — quotes optional
    thresholds: '80*70*60'    # always quote thresholds (first char after * could be *, too)
```

---

## Validation rules

The action raises a `ValueError` during startup if:

- Any group has an empty or missing `name`.
- Any two groups share the same `name`.
- Any group has an empty or missing `paths` list.
- Any path in `paths` or `baseline-paths` is an empty string.
- Any threshold field is not a number in `[0, 100)`.
- The YAML block is not valid YAML.

---

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

All groups inherit from `report-thresholds-default` (default `0*0*0` → no enforcement).

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
    thresholds: '75**'       # overall=75; avg and per-file from report-thresholds-default (60 and 0)
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
      - baseline/backend/**/jacoco.xml   # overrides top-level baseline-paths for this group
  - name: frontend
    paths:
      - frontend/**/jacoco.xml
    thresholds: '75*65*50'
    baseline-paths:
      - baseline/frontend/**/jacoco.xml

# Note: if top-level baseline-paths is set and multiple groups omit baseline-paths,
# grouped baseline inheritance is ambiguous and those groups will skip grouped baseline diffs.
```

---

### Combined with global thresholds

`global-thresholds` always runs as a separate pass over all reports combined.
It is independent of group thresholds.

```yaml
- uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    global-thresholds: '70*0*0'          # aggregated overall must be ≥ 70 %
    report-thresholds-default: '60*50*0' # default for all groups
    report-groups: |
      - name: core
        paths:
          - core/**/jacoco.xml
        thresholds: '80*70*60'           # stricter per-group enforcement
      - name: plugins
        paths:
          - plugins/**/jacoco.xml
        # no thresholds — uses report-thresholds-default (60*50*0)
```

---

## PR comment structure when groups are configured

When `report-groups` is non-empty the PR comment includes a Groups table between the Global
summary and the Reports table:

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

When `report-groups` is empty the Groups table is omitted and the three-table structure is used.

---

## See also

- [comment-level-guide.md](comment-level-guide.md) — controlling comment verbosity
- [v2-v3-migration-guide.md](v2-v3-migration-guide.md) — migrating `modules` / `modules-thresholds` to `report-groups`
- [examples/report-groups.yml](../examples/report-groups.yml) — complete workflow example
