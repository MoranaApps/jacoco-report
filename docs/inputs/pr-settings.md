# `pr-number`, `title`, and `update-comment`

## Theory

These inputs control **how the action identifies the pull request and manages its comment**.

`pr-number` is normally auto-detected from the GitHub Actions event context. The explicit input
exists for workflows where the trigger event does not carry a PR number directly — for example, a
`workflow_run` triggered by a CI job on a non-PR branch that then needs to comment on the originating PR.

`title` is the heading of the PR comment block. It also acts as the **comment identity key**: when
`update-comment: true`, the action searches for an existing comment whose first line matches the
title and updates it in place rather than posting a new one. Two parallel workflow runs with
different `title` values will create two independent comments.

`update-comment` controls whether the action edits an existing comment or always appends a new one.

## Valid values

| Input | Type | Default |
|-------|------|---------|
| `pr-number` | integer string or `''` | `''` (auto-detect) |
| `title` | non-empty string | `JaCoCo Coverage Report` |
| `update-comment` | `true` / `false` | `true` |

## Impact

- `pr-number` — if auto-detection fails (e.g. wrong event type), the action logs an error and fails.
  Set this explicitly to avoid ambiguity.
- `title` — changing the title mid-project creates a new comment; the old one is orphaned unless
  manually deleted.
- `update-comment: false` — each run appends a new comment. Useful for audit trails or when
  multiple parallel jobs each post their own report.

## Examples

### Explicit PR number

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    pr-number: '${{ github.event.pull_request.number }}'
```

### Custom title

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    title: 'Custom Coverage Report Title'
```

### Always post a new comment (no update)

```yaml
    update-comment: 'false'
```

## See also

- [comment-level.md](comment-level.md) — `none` level deletes an existing comment when `update-comment: true`
