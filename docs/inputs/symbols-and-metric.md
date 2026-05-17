# `pass-symbol`, `fail-symbol`, and `metric`

## Theory

These three inputs control the **visual appearance** of the PR comment. They have no effect on
threshold evaluation or the action exit code.

`metric` selects which JaCoCo counter is used for all coverage calculations. JaCoCo XML files
contain multiple counter types; this input picks one to use throughout the entire run.

`pass-symbol` and `fail-symbol` replace the default ✅ / ❌ emoji with any string — useful for
teams that prefer text labels, alternative emoji, or need plain-text output.

## Valid values

### `metric`

| Value | Counter |
|-------|---------|
| `instruction` | Bytecode instruction count (default) |
| `line` | Source code line count |
| `branch` | Branch count (if/else, switch) |
| `complexity` | Cyclomatic complexity |
| `method` | Method count |
| `class` | Class count |

### `pass-symbol` / `fail-symbol`

Any non-empty string. Examples: `✅`, `✔️`, `**Passed**`, `OK`, `❌`, `❗`, `**Failed**`.

## Impact

- `metric` changes the percentage values shown in all comment tables and used in threshold
  comparisons. The column header reflects the selected metric (e.g. `Metric (line)`).
- `pass-symbol` / `fail-symbol` appear in the **Status** column of every table row.

## Example

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    metric: 'line'
    pass-symbol: '✔️'
    fail-symbol: '❗'
```

## See also

- [comment-level.md](comment-level.md) — controlling which rows and tables appear in the comment
