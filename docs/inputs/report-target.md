# `report-target`

## Theory

`report-target` controls **where** the report goes:

- `comment`: a PR comment. This is the default.
- `summary`: the job summary of the workflow run (Actions → the run → Summary). It is not the PR description,
  which the action never reads or changes.
- `both`: the PR comment and the job summary.

`summary` is an optional second channel, not a replacement for the comment. It is also the way to get the report
without write permission, because it makes no comment API call (see [Permissions](#permissions)).

`comment-level` controls **what** the report contains and applies to both channels. For a given `comment-level`,
the comment and the job summary get the same content. They differ only in the length limit and in the note that
appears when the report is cut. See [comment-level.md](comment-level.md).

## Valid values

| Value | Effect |
|-------|--------|
| `comment` (default) | PR comment only |
| `summary` | Job summary only. No PR comment is created, updated or removed. |
| `both` | PR comment and job summary |
| `''` | Same as `comment` |

The value is trimmed and lowercased before it is checked. Any other value fails input validation, like the other inputs.

## Comment channel (`comment`, `both`)

- `update-comment` and `comment-level` decide whether a comment is created, updated or deleted (see
  [pr-settings.md](pr-settings.md) and [comment-level.md](comment-level.md)).
- The comment is limited to 65,536 characters. When the report is cut, the note says `see the job log`
  (`comment`), or links to the job summary (`both`, when the summary was written).

## Summary channel (`summary`, `both`)

- The action appends the report to the file in `GITHUB_STEP_SUMMARY`. The content is the same markdown as the
  comment for the chosen `comment-level`. It is not cut unless it is over the limit.
- The limit is 1 MiB (1,048,576 bytes of UTF-8) per step. It is not the 65,536-character comment limit.
- Over the limit, rows are cut from the end, in the same order as for the comment. The summary then notes the
  omitted rows and links to the job log:
  `… N rows omitted (GitHub's 1 MiB job summary limit), the full report is in the job log.`
  The job log gets the full, uncut report.
- With `comment-level: none`, nothing is written to the job summary.
- When `skip-unchanged` removes every report, the summary shows the title and a short message that all reports are
  unchanged, followed by the footer. A comment from earlier runs is not deleted with `summary`.
- `GITHUB_STEP_SUMMARY` is set by the runner for each step. It is not an input. It is missing outside a GitHub
  Actions runner (for example, a local run) and on GitHub Enterprise Server older than 3.6. If it is missing, or the
  write fails, the action logs a warning, the job result is unchanged and nothing is written.
- Each step has its own job summary file, so a later step cannot read what this action wrote.

## `comment-level` with each target

| `comment-level` | Content | Comment (`comment`, `both`) | Job summary (`summary`, `both`) |
|-----------------|---------|-----------------------------|---------------------------------|
| `none` | no report | no comment (an old comment is deleted if `update-comment: true`) | nothing written |
| `minimal` | global table only | comment with the global table | same global table |
| `full` | all tables and rows | comment, cut above 65,536 characters | same content, cut only above 1 MiB |
| `changed`, `failed`, `failed-or-changed` | tables filtered by row | comment, cut above 65,536 characters | same content, cut only above 1 MiB |

**The default `comment-level` is `full`.** `summary` without `comment-level` therefore writes the full report.
`none` means "no report" and applies to both channels.

Combinations:

- `summary` + `none`: no report is written anywhere. The action still evaluates thresholds, sets the outputs and
  fails the job if needed. `update-comment` has no effect.
- `both` + `none`: the comment channel behaves as with `comment`, and the job summary stays empty.
- `comment` + any level: only the PR comment, as [comment-level.md](comment-level.md) describes.

## Job result

`report-target` changes where the report goes, not when the job fails. Outputs are the same for every target.

| Situation | Job result |
|-----------|------------|
| Thresholds not met (`fail-on-threshold`) | failed, for every target |
| Operational error (event is not `pull_request`, no PR number, no XML files, changed files cannot be read) | failed, for every target |
| Invalid input, including `report-target` | failed |
| Comment cannot be posted (for example, 403) | warning, job result unchanged |
| Job summary cannot be written (`GITHUB_STEP_SUMMARY` missing or write fails) | warning, job result unchanged |
| Job summary cut above 1 MiB | warning, job result unchanged |

## Switching from `comment` to `summary`

Open PRs keep the last comment posted by earlier runs. With `summary`, the action no longer updates it, and it does
not delete it. Delete that comment by hand.

## Permissions

The action always reads the PR's changed files, which needs `contents: read` and `pull-requests: read`. Only the
comment needs write permission.

| `report-target` | Token permissions needed |
|-----------------|--------------------------|
| `comment` | `contents: read`, `pull-requests: read`, `issues: write` |
| `both` | `contents: read`, `pull-requests: read`, `issues: write`. Without `issues: write` the comment fails with a warning and the job summary is still written. |
| `summary` | `contents: read`, `pull-requests: read` |

With `summary`, the action makes no comment API call, so there is no 403 error and no warning for a missing write
permission.

## Example

Job summary only, with the minimum permissions:

```yaml
name: Publish JaCoCo Report in the job summary

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  generate-report:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - uses: actions/setup-python@v7
        with:
          python-version: '3.11'

      - name: Publish JaCoCo Report
        uses: MoranaApps/jacoco-report@v3
        with:
          token: '${{ secrets.GITHUB_TOKEN }}'
          report-target: summary
```

Comment and job summary:

```yaml
      - name: Publish JaCoCo Report
        uses: MoranaApps/jacoco-report@v3
        with:
          token: '${{ secrets.GITHUB_TOKEN }}'
          report-target: both
```

## See also

- [comment-level.md](comment-level.md): what the report contains, for both channels
- [pr-settings.md](pr-settings.md): `update-comment` and `title`
- [README: Requirements](../../README.md#requirements): token permissions
