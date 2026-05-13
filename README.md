# Jacoco Report GitHub Action

![GitHub tag](https://img.shields.io/github/v/tag/MoranaApps/jacoco-report?label=latest&style=flat-square&color=blue)

- [Requirements](#requirements)
- [Motivation](#motivation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Action Inputs](#action-inputs)
  - [Outputs](#outputs)
  - [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Developer](#developer)
- [License](#license)
- [Donate](#donate)

Automates the publication of JaCoCo coverage reports directly as comments in pull requests.

## Requirements

- **GitHub Token**: A GitHub token with permission to fetch repository data such as Issues and Pull Requests.
- **Python 3.13+**: Ensure you have Python 3.13 installed on your system.

---

## Motivation

Reviewing coverage numbers by hunting through CI logs is tedious. This action posts a structured
coverage report as a PR comment — directly where the review happens — so the whole team can see
which files changed, what their coverage is, and whether thresholds are met, without leaving GitHub.

Key capabilities:

- **Global thresholds** — enforce overall and average-changed minimums in one input.
- **Report groups** — organise multi-module projects into named groups with per-group thresholds.
- **Baseline comparison** — show Δ coverage against a stored baseline (e.g. `main` branch reports).
- **Flexible comment levels** — from a single-line summary to full per-file detail, or no comment at all.
- **Skip-unchanged filter** — remove reports with no changed files from the comment (and optionally from evaluation).

---

## Quick Start

Add the following job fragment to a workflow that already produces a JaCoCo XML report:

```yaml
jobs:
  coverage:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: write
      pull-requests: read
    steps:
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Publish JaCoCo Report
        uses: MoranaApps/jacoco-report@v3
        with:
          token: '${{ secrets.GITHUB_TOKEN }}'
          paths: '**/jacoco.xml'
          global-thresholds: '80*70*0'        # overall * changed-avg * reserved-third
          report-thresholds-default: '0*0*60' # per-changed-file threshold
```

This posts a full PR comment and fails the action if any threshold is not met.
See the [examples/](examples/) directory for more complete workflow files.

---

## Usage

```yaml
name: Publish JaCoCo Report in PR comments

on:
  pull_request:
    types: [opened, synchronize, reopened, edited, labeled, unlabeled]
    branches: [ main ]

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
          python-version: '3.13'

      - name: Publish JaCoCo Report in PR comments
        uses: MoranaApps/jacoco-report@v3
        with:
          token: '${{ secrets.GITHUB_TOKEN }}'
          paths: |
            src/reports/jacoco/jacoco.xml
            **/jacoco.xml
            **/reports/**/*.xml
            ${{ github.workspace }}/**/jacoco.xml
```

---

### Action Inputs

| Name                | Description                                                                                                                                                                                                                    | Required | Default                                          |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|--------------------------------------------------|
| `token`             | GitHub token for authentication with the repository.                                                                                                                                                                           | **Yes**  |                                                  |
| `paths`             | Newline-separated paths to JaCoCo XML files. Supports wildcard glob patterns. Required when `report-groups` is not set.                                                                                                        | No       | `''`                                             |
| `exclude-paths`     | Newline-separated paths to exclude from coverage analysis. Supports glob patterns.                                                                                                                                             | No       | `''`                                             |
| `global-thresholds` | Global thresholds in `overall*changed-files-average*reserved-third` format. Aggregated evaluation uses overall and changed-files-average.                                                                                         | No       | `0.0*0.0*0.0`                                    |
| `report-thresholds-default` | Default thresholds for reports/groups when a group omits a threshold field. Format: `overall*changed-files-average*per-changed-file` (e.g. `75*60*0`). Field-level fallback chain: per-group → this default → 0.0.        | No       | `0.0*0.0*0.0`                                    |
| `title`             | Title for the coverage report comment added to the Pull Request.                                                                                                                                                               | No       | `JaCoCo Coverage Report`                         |
| `pr-number`         | Number of the pull request. If not provided, the action will attempt to determine the PR number from the GitHub context.                                                                                                       | No       | `''`                                             |
| `metric`            | Coverage metric to use (`instruction`, `line`, `branch`, `complexity`, `method`, `class`).                                                                                                                                     | No       | `instruction`                                    |
| `comment-level`     | Comment output level: `none`, `minimal`, `full`, `changed`, `failed`, or `failed-or-changed`. See [docs/comment-level-guide.md](docs/comment-level-guide.md).                                                                 | No       | `full`                                           |
| `report-groups`     | Named report groups as a YAML list. Each entry: `name` (required), `paths` (required list of globs), `thresholds` (optional `O*A*P`), `baseline-paths` (optional list). See [docs/report-groups-format.md](docs/report-groups-format.md). | No  | `''`                                      |
| `skip-unchanged`    | If `true`, reports with no changed files are filtered out from comment rows. With default `evaluate-unchanged=true`, filtered reports can still affect threshold results.                                                        | No       | `false`                                          |
| `evaluate-unchanged` | Applies only when `skip-unchanged=true`. If `true`, filtered reports can still fail overall thresholds. If `false`, they are excluded from threshold evaluation as well.                                                       | No       | `true`                                           |
| `baseline-paths`    | Paths to baseline coverage reports for comparison. Supports wildcard glob patterns.                                                                                                                                            | No       | `''`                                             |
| `update-comment`    | If `true`, updates an existing comment instead of creating a new one.                                                                                                                                                          | No       | `true`                                           |
| `pass-symbol`       | Symbol for passing checks in PR comments (e.g., ✅, **Passed**).                                                                                                                                                               | No       | `✅`                                              |
| `fail-symbol`       | Symbol for failing checks in PR comments (e.g., ❌, **Failed**).                                                                                                                                                               | No       | `❌`                                              |
| `fail-on-threshold` | Comma- or newline-separated list of thresholds that must pass: `overall`, `changed-files-average`, `per-changed-file`. Leave empty to disable.                                                                                | No       | `overall,changed-files-average,per-changed-file` |
| `debug`             | Enables detailed logging. Automatically activated when `ACTIONS_RUNNER_DEBUG=true`.                                                                                                                                            | No       | `false`                                          |

> Hint: default values have been defined to provide maximal possible information in the comment.

Per-changed-file checks are configured by `report-thresholds-default` or per-group `thresholds`,
not by `global-thresholds`.

---

#### Outputs

The following outputs are set by the JaCoCo GitHub Action:

- `coverage-overall`: The overall code coverage percentage.
- `coverage-changed-files`: The code coverage percentage for the changed files.
- `coverage-overall-passed`: A boolean indicating if overall code coverage meets the configured threshold.
- `coverage-changed-files-passed`: A boolean indicating if changed-files average coverage
  meets the configured threshold.
- `reports-coverage`: A JSON string containing the evaluated coverage per report.
- `groups-coverage`: A JSON string containing the evaluated coverage per report group
  (populated when `report-groups` is defined).

---

### Examples

- [Customizing Paths and Exclude Paths](#customizing-paths-and-exclude-paths)
- [Customizing the Global Coverage Thresholds](#customizing-the-global-coverage-thresholds)
- [Customizing the PR Number](#customizing-the-pr-number)
- [Customizing the Report Title](#customizing-the-report-title)
- [Customizing the Report Groups](#customizing-the-report-groups)
- [Customizing the Comment Level](#customizing-the-comment-level)
  - [No Comment](#no-comment)
  - [Minimal Level](#minimal-level)
  - [Full Level](#full-level)
  - [Changed Level](#changed-level)
  - [Failed Level](#failed-level)
  - [Failed-or-Changed Level](#failed-or-changed-level)
- [Customizing the Skip Unchanged Option and Update Comment](#customizing-the-skip-unchanged-option-and-update-comment)
- [Customizing the Baseline Paths](#customizing-the-baseline-paths)
- [Customizing the Symbols and Metric Type](#customizing-the-symbols-and-metric-type)
- [Customizing the Debug Mode](#customizing-the-debug-mode)

#### Customizing Paths and Exclude Paths

The `paths` input allows you to specify the paths to the JaCoCo XML files that should be included in the code coverage
analysis. This input is required only when `report-groups` is not provided.

- You can use wildcard glob patterns to match multiple files.
- Multiple paths must be specified as a newline-separated list.

The `exclude-paths` input allows you to specify files or directories that should be excluded from the code coverage
analysis.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: |
      module-a/target/jacoco/code-coverage.xml
      module-b/target/jacoco/code-coverage.xml
      module-c/target/jacoco/**/*.xml
    exclude-paths: |
      **/temp/**
      **/legacy/**
      module-c/target/**/excluded/**
```

#### Customizing the Global Coverage Thresholds

The `global-thresholds` input defines aggregated thresholds in the format
`overall*changed-files-average*reserved-third`.

Per-changed-file enforcement is configured through `report-thresholds-default` (or per-group
`thresholds` when `report-groups` is used).

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    global-thresholds: '80*70*0'    # 80% overall, 70% changed avg
    report-thresholds-default: '0*0*60' # 60% per changed file
    fail-on-threshold: 'overall,changed-files-average,per-changed-file'
```

To fail only on the overall threshold:

```yaml
    global-thresholds: '80*0*0'
    fail-on-threshold: 'overall'
```

To disable threshold-based failure entirely:

```yaml
    fail-on-threshold: ''
```

#### Customizing the PR Number

The `pr-number` input allows you to specify the number of the pull request. If not provided, the action will attempt
to determine the PR number from the GitHub context.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    pr-number: '${{ github.event.pull_request.number }}'
```

#### Customizing the Report Title

The `title` input lets you specify a custom title for the JaCoCo coverage report comment.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    title: 'Custom Coverage Report Title'
```

#### Customizing the Report Groups

The `report-groups` input groups JaCoCo reports under named groups with optional per-group coverage thresholds and
baseline paths. When defined, each group's `paths` is used for scanning and the top-level `paths` input can be omitted.

Each entry is a YAML mapping with:

- `name` (required): Group name shown in the PR comment groups table.
- `paths` (required): List of glob patterns for JaCoCo XML reports in this group.
- `thresholds` (optional): `overall*changed-files-average*per-changed-file`
  (e.g. `80*70*60`). Missing fields fall back to `report-thresholds-default`, then to 0.0.
  Global thresholds are a separate evaluation pass.
- `baseline-paths` (optional): List of glob patterns for baseline reports for this group.

For the full format reference see [docs/report-groups-format.md](docs/report-groups-format.md).

When multiple groups omit `baseline-paths` while top-level `baseline-paths` is set, inheritance is
treated as ambiguous and grouped baseline scans are skipped for those omitted groups.

> **YAML quoting note**: Any `paths`, `baseline-paths`, or `thresholds` value that begins with `*` must be quoted,
> otherwise YAML interprets the leading `*` as a YAML alias.
>
> ```yaml
> paths:
>   - '**/jacoco.xml'       # leading * — must be quoted
>   - module/**/jacoco.xml  # no leading * — safe without quotes
> thresholds: '80*70*60'    # always quote thresholds
> ```

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

#### Customizing the Comment Level

The `comment-level` input controls how much detail appears in the PR comment.
See [docs/comment-level-guide.md](docs/comment-level-guide.md) for a full description of each level.

##### No Comment

When `comment-level` is set to `none`, no PR comment is posted (threshold evaluation still runs).

```yaml
    comment-level: 'none'
```

##### Minimal Level

When `comment-level` is set to `minimal`, a single global summary table is posted.

###### JaCoCo Coverage Report

| Metric (Instruction) | Coverage | Threshold | Δ Coverage | Status |
|----------------------|----------|-----------|------------|--------|
| **Overall**          | 85.2%    | 80.0%     | +1.3%      | ✅     |
| **Changed Files**    | 78.4%    | 80.0%     | -0.3%      | ❌     |

> Δ Coverage is visible when `baseline-paths` is defined and data is available.

```yaml
    comment-level: 'minimal'
```

##### Full Level

When `comment-level` is set to `full`, all tables are shown: global summary, groups (if configured),
per-report, and per-changed-file.

###### JaCoCo Coverage Report

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

> - **(O)** — Overall coverage.
> - **(Ch)** — Coverage for changed files.
> - **Δ Coverage** is visible when `baseline-paths` is defined and data is available.
> - The groups table is visible only when `report-groups` is configured.
> - `global-thresholds` is always evaluated as a separate pass over aggregated totals.

```yaml
    comment-level: 'full'
```

##### Changed Level

When `comment-level` is set to `changed`, all tables are shown but rows where **changed files = 0**
are hidden in the groups, reports, and changed-files tables.

```yaml
    comment-level: 'changed'
```

##### Failed Level

When `comment-level` is set to `failed`, all tables are shown but only rows that **fail** their
threshold are visible in the groups, reports, and changed-files tables.

```yaml
    comment-level: 'failed'
```

##### Failed-or-Changed Level

When `comment-level` is set to `failed-or-changed`, rows are shown when they either have changed
files **or** fail a threshold — the union of `changed` and `failed`.

```yaml
    comment-level: 'failed-or-changed'
```

#### Customizing the Skip Unchanged Option and Update Comment

`skip-unchanged` and `evaluate-unchanged` work together:

| `skip-unchanged` | `evaluate-unchanged` | Comment rows for unchanged reports | Can unchanged reports fail the action? |
|------------------|----------------------|------------------------------------|----------------------------------------|
| `false`          | any                  | Shown (normal flow)                | Yes (normal evaluation)                |
| `true`           | `false`              | Hidden                             | No                                     |
| `true`           | `true`               | Hidden                             | Yes (overall threshold only)           |

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    skip-unchanged: 'true'
    update-comment: 'true'
```

Hide unchanged reports and exclude them from pass/fail evaluation:

```yaml
    skip-unchanged: 'true'
    evaluate-unchanged: 'false'
```

Hide unchanged reports but still enforce their overall threshold:

```yaml
    report-thresholds-default: '80*0*0'
    skip-unchanged: 'true'
    evaluate-unchanged: 'true'
```

#### Customizing the Baseline Paths

The `baseline-paths` input defines paths to baseline coverage reports, enabling Δ coverage
comparison against an established reference (e.g. the `main` branch).

**Required**: each report must have a unique title that matches the corresponding baseline report.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    baseline-paths: 'baseline/master/jacoco/**/*.xml'
```

#### Customizing the Symbols and Metric Type

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    metric: 'line'         # instruction | line | branch | complexity | method | class
    pass-symbol: '✔️'
    fail-symbol: '❗'
```

#### Customizing the Debug Mode

The `debug` input enables detailed logging. It is automatically enabled when
`RUNNER_DEBUG=1` is set by GitHub Actions runner debug mode.
Use `debug: 'true'` to enable debug logs explicitly regardless of runner settings.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    debug: 'true'
```

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

### `fail-on-threshold: true` shows a deprecation warning

- Boolean values for `fail-on-threshold` are deprecated in v3. Replace with the list form:

  ```yaml
  fail-on-threshold: 'overall,changed-files-average,per-changed-file'
  ```

### Migrating from v2

See [docs/v2-v3-migration-guide.md](docs/v2-v3-migration-guide.md) for a full before/after guide
covering every breaking change.

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
