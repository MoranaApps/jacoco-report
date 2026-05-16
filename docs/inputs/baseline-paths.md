# `baseline-paths`

## Theory

`baseline-paths` enables **Δ coverage comparison** — the PR comment gains a **Δ Coverage** column
showing how coverage changed relative to an established reference point, typically the `master`
branch reports stored as build artifacts.

The action matches each scanned report to a baseline report by **title**. Each report must therefore
have a unique title so the pairing is unambiguous. When a report has no matching baseline entry, its
Δ column renders as `0.0%`.

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
- Has no effect on threshold evaluation — thresholds always compare against the configured
  minimum, not the baseline.

## Examples

### Compare against stored master reports

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    baseline-paths: 'baseline/master/jacoco/**/*.xml'
```

### Per-group baselines (via `report-groups`)

See [report-groups.md](report-groups.md) — each group supports its own `baseline-paths` field.

## See also

- [report-groups.md](report-groups.md) — per-group `baseline-paths` configuration
- [comment-level.md](comment-level.md) — interaction with `baseline-paths` (Δ column visibility)
