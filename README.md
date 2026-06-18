# Jacoco Report GitHub Action

![GitHub tag](https://img.shields.io/github/v/tag/MoranaApps/jacoco-report?label=latest&style=flat-square&color=blue)

Automates the publication of JaCoCo coverage reports directly as comments in pull requests.

- [Requirements](#requirements)
- [Motivation](#motivation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Action Inputs](#action-inputs)
  - [Outputs](#outputs)
  - [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Migrating from v2](#migrating-from-v2)
- [Developer](#developer)
- [License](#license)
- [Donate](#donate)

## Requirements

- **GitHub Token**: A GitHub token with permission to fetch repository data such as Issues and Pull Requests.
- **Python 3.14+**: Ensure you have Python 3.14 installed on your system.

---

## Motivation

Reviewing coverage numbers by hunting through CI logs is tedious. This action posts a structured
coverage report as a PR comment — directly where the review happens — so the whole team can see
which files changed, what their coverage is, and whether thresholds are met, without leaving GitHub.

Key capabilities:

- **Global thresholds** — enforce overall and average-changed minimums in one input.
- **Report groups** — organise multi-module projects into named groups with per-group thresholds.
- **Baseline comparison** — show Δ coverage against a stored baseline (e.g. the `master` branch reports).
- **Flexible comment levels** — from a single-line summary to full per-file detail, or no comment at all.
- **Skip-unchanged filter** — remove reports with no changed files from the comment (and optionally from evaluation).

---

## Usage

```yaml
name: Publish JaCoCo Report in PR comments

on:
  pull_request:
    types: [opened, synchronize, reopened, edited]
    branches: [ master ]

jobs:
  generate-report:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: write
      pull-requests: read
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Publish JaCoCo Report in PR comments
        uses: MoranaApps/jacoco-report@v3
        with:
          token: '${{ secrets.GITHUB_TOKEN }}'
          paths: |
            src/reports/jacoco/jacoco.xml
            **/jacoco.xml
            **/reports/**/*.xml
            ${{ github.workspace }}/**/jacoco.xml
          global-thresholds: '80*70'           # overall * changed-files-average

```

---

### Action Inputs

| Name                | Description                                                                                                                                                                                                                    | Required | Default                                          |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|--------------------------------------------------|
| `token`             | GitHub token for authentication with the repository.                                                                                                                                                                           | **Yes**  |                                                  |
| `paths`             | Newline-separated paths to JaCoCo XML reports. Supports wildcard glob patterns. Must be non-empty; the default covers the standard JaCoCo output location.                                                                     | No       | `**/jacoco.xml`                                  |
| `exclude-paths`     | Newline-separated paths to exclude from coverage analysis. Supports glob patterns.                                                                                                                                             | No       | `''`                                             |
| `global-thresholds` | Global thresholds in `overall*changed-files-average` format.                                                                                                                                        | No       | `0.0*0.0`                                        |
| `global-overall-scope` | Controls which reports contribute to the global overall number when `report-groups` is configured. `all` (default): every report found by `paths` is included, even ungrouped ones. `groups-only`: only grouped reports count. See [docs/inputs/global-overall-scope.md](docs/inputs/global-overall-scope.md). | No | `all` |
| `report-thresholds-default` | Default thresholds for reports/groups when a group omits a threshold field. Format: `overall*changed-files-average*per-changed-file` (e.g. `75*60*0`). Field-level fallback chain: per-group → this default → 0.0.        | No       | `0.0*0.0*0.0`                                    |
| `title`             | Title for the coverage report comment added to the Pull Request.                                                                                                                                                               | No       | `JaCoCo Coverage Report`                         |
| `pr-number`         | Number of the pull request. If not provided, the action will attempt to determine the PR number from the GitHub context.                                                                                                       | No       | `''`                                             |
| `metric`            | Coverage metric to use (`instruction`, `line`, `branch`, `complexity`, `method`, `class`).                                                                                                                                     | No       | `instruction`                                    |
| `comment-level`     | Comment output level: `none`, `minimal`, `full`, `changed`, `failed`, or `failed-or-changed`. See [docs/inputs/comment-level.md](docs/inputs/comment-level.md).                                                                 | No       | `full`                                           |
| `report-groups`     | Named report groups as a YAML list. Each entry: `name` (required), `paths` (required list of globs), `thresholds` (optional `O*A*P`), `baseline-paths` (optional list). See [docs/inputs/report-groups.md](docs/inputs/report-groups.md). | No  | `''`                                      |
| `skip-unchanged`    | If `true`, reports with no changed files are filtered out from comment rows. With default `evaluate-unchanged=true`, filtered reports can still affect threshold results.                                                        | No       | `false`                                          |
| `evaluate-unchanged` | Applies only when `skip-unchanged=true`. If `true`, filtered reports can still fail overall thresholds. If `false`, they are excluded from threshold evaluation as well.                                                       | No       | `true`                                           |
| `baseline-paths`    | Paths to baseline coverage reports for comparison. Supports wildcard glob patterns.                                                                                                                                            | No       | `''`                                             |
| `update-comment`    | If `true`, updates an existing comment instead of creating a new one.                                                                                                                                                          | No       | `true`                                           |
| `pass-symbol`       | Symbol for passing checks in PR comments (e.g., ✅, **Passed**).                                                                                                                                                               | No       | `✅`                                              |
| `fail-symbol`       | Symbol for failing checks in PR comments (e.g., ❌, **Failed**).                                                                                                                                                               | No       | `❌`                                              |
| `fail-on-threshold` | List value (comma- or newline-separated) of thresholds that must pass: `overall`, `changed-files-average`, `per-changed-file`, `fail-unchanged`. Leave empty to disable.                                                     | No       | `overall,changed-files-average,per-changed-file` |
| `debug`             | Enables detailed logging. Automatically activated when `RUNNER_DEBUG=1` (GitHub runner debug mode).                                                                                                                             | No       | `false`                                          |

---

### Outputs

The following outputs are set by the JaCoCo GitHub Action:

- `coverage-overall`: The overall code coverage percentage. Example: `85.38`
- `coverage-changed-files`: The code coverage percentage for the changed files. Example: `79.21`
- `coverage-overall-passed`: A boolean indicating if overall code coverage meets the configured threshold. Example: `True`
- `coverage-changed-files-passed`: A boolean indicating if changed-files average coverage
  meets the configured threshold. Example: `True`
- `reports-coverage`: A JSON string containing the evaluated coverage per report. Example:
  ```json
  {
      "path/to/jacoco.xml": {
          "name": "My Report",
          "group_name": "Unknown",
          "overall_passed": true,
          "overall_coverage_reached": 85.38,
          "overall_coverage_threshold": 80.0,
          "overall_coverage": { "missed": 142, "covered": 934 },
          "avg_changed_files_passed": true,
          "avg_changed_files_coverage_reached": 79.21,
          "avg_changed_files_coverage": { "missed": 21, "covered": 80 },
          "changed_files_passed": { "src/main/java/Foo.java": true },
          "changed_files_threshold": 70.0,
          "changed_files_coverage_reached": { "src/main/java/Foo.java": 82.5 },
          "per_changed_file_threshold": 70.0
      }
  }
  ```
- `groups-coverage`: A JSON string containing the evaluated coverage per report group
  (populated when `report-groups` is defined). Example:
  ```json
  {
      "backend": {
          "name": "backend",
          "group_name": "backend",
          "overall_passed": true,
          "overall_coverage_reached": 85.38,
          "overall_coverage_threshold": 80.0,
          "overall_coverage": { "missed": 142, "covered": 934 },
          "avg_changed_files_passed": true,
          "avg_changed_files_coverage_reached": 79.21,
          "avg_changed_files_coverage": { "missed": 21, "covered": 80 },
          "changed_files_passed": { "src/main/java/Foo.java": true },
          "changed_files_threshold": 70.0,
          "changed_files_coverage_reached": { "src/main/java/Foo.java": 82.5 },
          "per_changed_file_threshold": 70.0
      }
  }
  ```

---

### Examples

- [Paths and Exclude Paths](docs/inputs/paths.md)
- [Global Coverage Thresholds, Per-file Thresholds, and Fail-on-Threshold](docs/inputs/thresholds.md)
- [Global Overall Scope](docs/inputs/global-overall-scope.md)
- [Report Groups](docs/inputs/report-groups.md)
- [Comment Level](docs/inputs/comment-level.md)
- [Skip Unchanged and Evaluate Unchanged](docs/inputs/skip-unchanged.md)
- [Baseline Paths](docs/inputs/baseline-paths.md)
- [Symbols and Metric Type](docs/inputs/symbols-and-metric.md)
- [PR Number, Title, and Update Comment](docs/inputs/pr-settings.md)
- [Debug Mode](docs/inputs/debug.md)

---

## Troubleshooting

### The action cannot find any JaCoCo XML files

- Check that your build step runs **before** this action and actually produces the XML files.
- Use `debug: 'true'` to log matched JaCoCo XML files discovered by scanning.
- Verify the `paths` pattern resolves to real files.
  Both repository-relative patterns and absolute `${{ github.workspace }}` paths are supported.
- If the path contains a leading `*` in a `report-groups` YAML block, wrap it in quotes:
  `- '**/jacoco.xml'`.

### No PR comment is posted

- Confirm `comment-level` is not set to `none`.
- Confirm the job token permissions include `issues: write` (comment create/update/delete)
  and `pull-requests: read` (PR files lookup).
- If `skip-unchanged: true` and all reports have no changed files:
  - with `evaluate-unchanged: false`, the action exits cleanly with no comment by design;
  - with `evaluate-unchanged: true` (default), unchanged reports are still evaluated for threshold failures.

### The action fails with a threshold error but the comment shows ✅

- Check whether `fail-on-threshold` lists dimensions that differ from the thresholds you set in
  `global-thresholds` and `report-thresholds-default`.
  By default, `overall`, `changed-files-average`, and `per-changed-file` checks are enabled;
  the per-changed-file check uses report/group thresholds.
- When `report-groups` is used, group thresholds are evaluated separately from `global-thresholds`.

### `fail-on-threshold` selection looks incorrect

- Ensure `fail-on-threshold` is configured as a list value (comma- or newline-separated).
- Example:

  ```yaml
  fail-on-threshold: 'overall,changed-files-average,per-changed-file'
  ```

### Migrating from v2

See [docs/v2-v3-migration-guide.md](docs/v2-v3-migration-guide.md) for a full before/after guide
covering every breaking change.

**Additional changes introduced in v3.x:**

- **`global-overall-scope` defaults to `all`**: when `report-groups` is configured, the action now
  runs a top-level `paths` scan in addition to per-group scans. Reports found by that scan but not
  assigned to any group are included in the global overall number (and a warning is logged for each).
  If this changes your global threshold results unexpectedly, set `global-overall-scope: 'groups-only'`
  to restore the previous behaviour.
- **`paths` defaults to `**/jacoco.xml`**: the input was previously optional when `report-groups` was
  set. It now has a default value. Remove any explicit `paths: ''` overrides — empty paths are
  allowed and fall back to `**/jacoco.xml` at runtime when no groups are configured.

---

## Developer

Follow the [DEVELOPER.md](DEVELOPER.md) guide to set up the development environment.

## License

[Apache License, Version 2.0](./LICENSE)

## Donate

If you find this project useful or interesting, consider supporting it!

Your donation helps me keep building, maintaining and improving this tool — every bit of support
matters and is deeply appreciated.

- [Buy me a coffee on Ko-fi](https://ko-fi.com/mirpo)

Thanks for keeping this project alive.
