# `skip-unchanged` and `evaluate-unchanged`

## Theory

In a typical PR only a subset of modules have changed files. Without filtering, all reports appear
in the PR comment — including modules nobody touched — which adds noise and can cause threshold
failures on modules irrelevant to the PR.

`skip-unchanged: true` removes reports with **no changed files** from the scan at the earliest
possible stage (before evaluation begins), not just from the comment. This is the key difference
from v2, where unchanged reports were still evaluated internally even when hidden.

`evaluate-unchanged` gives back control over the threshold pass for those filtered reports.
When `true` (the default), filtered reports still contribute to overall threshold evaluation even
though they do not appear in the PR comment. When `false`, they are completely excluded from
evaluation as well.

If all reports are filtered, the action exits cleanly: no comment is posted and no threshold
failures are raised.

## Valid values

| Input | Values | Default |
|-------|--------|---------|
| `skip-unchanged` | `true` / `false` | `false` |
| `evaluate-unchanged` | `true` / `false` | `true` |

`evaluate-unchanged` has no effect when `skip-unchanged` is `false`.

## Impact

| `skip-unchanged` | `evaluate-unchanged` | Comment rows for unchanged reports | Can unchanged reports fail the action? |
|------------------|----------------------|------------------------------------|----------------------------------------|
| `false`          | any                  | Shown (normal flow)                | Yes (normal evaluation)                |
| `true`           | `false`              | Hidden                             | No                                     |
| `true`           | `true`               | Hidden                             | Yes (overall threshold only)           |

## Examples

### Hide unchanged reports, keep threshold evaluation

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    skip-unchanged: 'true'
    update-comment: 'true'
```

### Hide unchanged reports and exclude from pass/fail evaluation

```yaml
    skip-unchanged: 'true'
    evaluate-unchanged: 'false'
```

### Hide unchanged reports but still enforce their overall threshold

```yaml
    report-thresholds-default: '80*0*0'
    skip-unchanged: 'true'
    evaluate-unchanged: 'true'
```

### Fail the action when unchanged filtered reports drop below threshold

```yaml
    skip-unchanged: 'true'
    fail-on-threshold: 'fail-unchanged'
```

## See also

- [thresholds.md](thresholds.md) — `fail-unchanged` threshold dimension
- [comment-level.md](comment-level.md) — interaction between `skip-unchanged` and `comment-level`
