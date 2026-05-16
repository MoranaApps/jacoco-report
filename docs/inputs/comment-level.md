# `comment-level`

## Theory

`comment-level` controls how much information appears in the PR comment posted by the action.
All levels still run coverage evaluation and honour `fail-on-threshold`; only the comment content
differs.

## Valid values

| Level | Global table | Groups table | Reports table | Changed-files table | Filter applied |
|-------|:---:|:---:|:---:|:---:|----------------|
| `none` | — | — | — | — | No comment posted |
| `minimal` | ✅ | — | — | — | None |
| `full` | ✅ | ✅* | ✅ | ✅ | None |
| `changed` | ✅ | ✅* | ✅ | ✅ | Hide rows with zero changed files |
| `failed` | ✅ | ✅* | ✅ | ✅ | Hide rows that pass their threshold |
| `failed-or-changed` | ✅ | ✅* | ✅ | ✅ | Show rows that have changes **or** fail |

\* Groups table is included only when `report-groups` is configured.

Default: `full`

## Level descriptions

### `none`

No PR comment is posted. If `update-comment: true` and a previous JaCoCo comment with the same
title exists, that stale comment is deleted so the PR stays clean.

Use this when you need threshold enforcement in CI but do not want any comment noise.

```yaml
comment-level: 'none'
```

---

### `minimal`

A single global summary table is posted. Individual report and file rows are not shown.

```text
| Metric (Instruction) | Coverage | Threshold | Status |
|----------------------|----------|-----------|--------|
| **Overall**          | 85.2%    | 80.0%     | ✅     |
| **Changed Files**    | 78.4%    | 80.0%     | ❌     |
```

Use this when you only care about the aggregate pass/fail signal.

```yaml
comment-level: 'minimal'
```

---

### `full`

All tables are posted: global summary, groups (if configured), per-report, and per-changed-file.
This is the default.

```text
| Metric (Instruction) | Coverage | Threshold | Δ Coverage | Status |
|----------------------|----------|-----------|------------|--------|
| **Overall**          | 85.2%    | 80.0%     | +1.3%      | ✅     |
| **Changed Files**    | 78.4%    | 80.0%     | -0.3%      | ❌     |

| Report          | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|-----------------|-----------------|------------------|-------------------|---------------|
| `Report 1 name` | 87.5% / 35.2%   | 60.0% / 80.0%    | -0.6% / +1.0%     | ✅/✅          |
| `Report 2 name` | 80.0% / 45.6%   | 40.0% / 82.0%    | +0.3% / -2.1%     | ✅/✅          |
| `Report 3 name` | 76.3% / 76.4%   | 50.0% / 76.0%    | -2.5% / -1.2%     | ❌/✅          |

| File Path    | Coverage | Threshold | Δ Coverage | Status |
|--------------|----------|-----------|------------|--------|
| `File1.java` | 90.1%    | 80.0%     | +0.3%      | ✅     |
| `File2.java` | 70.5%    | 80.0%     | -1.0%      | ❌     |
| `File3.java` | 82.1%    | 80.0%     | +2.7%      | ✅     |
```

> - **(O)** — Overall coverage. **(Ch)** — Coverage for changed files.
> - **Δ Coverage** column appears only when `baseline-paths` is configured.
> - The groups table appears only when `report-groups` is configured.

```yaml
comment-level: 'full'
```

---

### `changed`

Same structure as `full`, but rows in the Groups, Reports, and Changed-files tables where
**changed files = 0** are hidden. The global summary table is always shown in full.

Use this to reduce comment noise in large repos where most modules are untouched in a given PR.

```yaml
comment-level: 'changed'
```

---

### `failed`

Same structure as `full`, but only rows that **fail** their threshold are shown in the Groups,
Reports, and Changed-files tables. The global summary table is always shown in full.

Use this in high-coverage projects where you only want the PR comment to highlight regressions.

```yaml
comment-level: 'failed'
```

---

### `failed-or-changed`

Union of `changed` and `failed`: a row is shown when it either has changed files **or** fails its
threshold. The global summary table is always shown in full.

This is the recommended level for most teams — full visibility into active work and any
regressions, without noise from stable untouched modules.

```yaml
comment-level: 'failed-or-changed'
```

---

## Interaction with `skip-unchanged`

`skip-unchanged: true` runs **before** `comment-level` filtering. Reports with no changed files
are removed from comment rows entirely. With `evaluate-unchanged: true` (default), those filtered
reports can still fail overall thresholds even though they do not appear in tables.

| `skip-unchanged` | `comment-level` | Effect |
|---|---|---|
| `false` | `changed` | Hide zero-changed rows in comment; still evaluated |
| `true` | `full` | Unchanged reports removed from comment rows before comment is built |
| `true` | `changed` | Equivalent to `true` / `full` for unchanged reports; remaining changed rows shown |

## Interaction with `baseline-paths`

When `baseline-paths` is configured, a **Δ Coverage** column appears in all tables.
The column is omitted only when no baseline evaluator data exists at all. Rows without a matching
baseline entry render a `0.0%` delta.

## See also

- [report-groups.md](report-groups.md) — configuring named report groups (affects Groups table)
- [skip-unchanged.md](skip-unchanged.md) — scan-stage filter applied before `comment-level`
- [baseline-paths.md](baseline-paths.md) — enabling the Δ Coverage column
- [v2-v3-migration-guide.md](../v2-v3-migration-guide.md) — upgrading from v2
