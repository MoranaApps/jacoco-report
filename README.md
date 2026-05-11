# Jacoco Report GitHub Action

![GitHub tag](https://img.shields.io/github/v/tag/MoranaApps/jacoco-report?label=latest&style=flat-square&color=blue)
![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/MoranaApps/jacoco-report?utm_source=oss&utm_medium=github&utm_campaign=MoranaApps%2Fjacoco-report&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)

- [Usage](#usage)
  - [Action Inputs](#action-inputs)
  - [Outputs](#outputs)
  - [Examples](#examples)
- [Developer](#developer)
- [License](#license)
- [Donate](#donate)

Automates the publication of JaCoCo coverage reports directly as comments in pull requests.

Requirements

- **GitHub Token**: A GitHub token with permission to fetch repository data such as Issues and Pull Requests.
- **Python 3.13+**: Ensure you have Python 3.13 installed on your system.

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
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - uses: actions/setup-python@v5.1.1
        with:
          python-version: '3.13'

      - name: Publish JaCoCo Report in PR comments
        uses: MoranaApps/jacoco-report@v3
        with:
          token: '${{ secrets.TOKEN }}'
          paths: |
            src/reports/jacoco/jacoco.xml                         # Path to the JaCoCo XML report in the repository
            **/jacoco.xml                                         # Match all Jacoco XML files in the repository
            **/reports/**/*.xml                                   # Match all XML files in the reports directory       
            ${{ github.workspace }}/**/jacoco.xml                 # Match all Jacoco XML files in the workspace
            ${{ github.workspace }}/**/build/reports/**/*.xml     # Match all XML files in the build/reports directory
            /home/runner/work/<repo-name>/<repo-name>/jacoco.xml  # Absolute path to the Jacoco XML report
```

---

### Action Inputs

| Name                | Description                                                                                                                                                                                                                    | Required | Default                                          |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|--------------------------------------------------|
| `token`             | GitHub token for authentication with the repository.                                                                                                                                                                           | **Yes**  |                                                  |
| `paths`             | Newline-separated paths to JaCoCo XML files. Supports wildcard glob patterns. Required when `report-groups` is not set.                                                                                                        | No       | `''`                                             |
| `exclude-paths`     | Newline-separated paths to exclude from coverage analysis. Supports glob patterns.                                                                                                                                             | No       | `''`                                             |
| `global-thresholds` | Global coverage thresholds in `overall*changed-files-average*changed-file` format. Evaluated independently as a separate pass over aggregated totals.                                                                         | No       | `0.0*0.0*0.0`                                    |
| `report-thresholds-default` | Default thresholds for reports/groups when a group omits a threshold field. Format: `overall*changed-files-average*per-changed-file` (e.g. `75*60*0`). Field-level fallback chain: per-group → this default → 0.0.        | No       | `0.0*0.0*0.0`                                    |
| `title`             | Title for the coverage report comment added to the Pull Request.                                                                                                                                                               | No       | `JaCoCo Coverage Report`                         |
| `pr-number`         | Number of the pull request. If not provided, the action will attempt to determine <br> the PR number from the GitHub context.                                                                                                  | No       | `''`                                             |
| `metric`            | Coverage metric to use (`instruction`, `line`, `branch`, `complexity`, `method`, `class`).                                                                                                                                     | No       | `instruction`                                    |
| `comment-level`     | Comment output level: `none`, `minimal`, `full`, `changed`, `failed`, or `failed-or-changed`. `changed`, `failed`, and `failed-or-changed` keep the global summary table and filter lower tables by row.                     | No       | `full`                                           |
| `report-groups`     | Named report groups as a YAML list. Each entry: `name` (required), `paths` (required list of globs), `thresholds` (optional `O*A*P`, e.g. `80*70*60`), `baseline-paths` (optional list). When set, group `paths` are used. | No       | `''`                                             |
| `skip-unchanged`    | If `true`, skips entire reports with no changed files in the PR, reducing comment noise.                                                                                                                                       | No       | `false`                                          |
| `baseline-paths`    | Paths to baseline coverage reports for comparison. Supports wildcard glob patterns.                                                                                                                                            | No       | `''`                                             |
| `update-comment`    | If `true`, updates an existing comment instead of creating a new one, preventing clutter.                                                                                                                                      | No       | `true`                                           |
| `pass-symbol`       | Symbol for passing checks in PR comments (e.g., ✅, **Passed**).                                                                                                                                                               | No       | `✅`                                              |
| `fail-symbol`       | Symbol for failing checks in PR comments (e.g., ❌, **Failed**).                                                                                                                                                               | No       | `❌`                                              |
| `fail-on-threshold` | Comma- or newline-separated list of thresholds that must pass: `overall`, `changed-files-average`, `per-changed-file`. Leave empty to disable.                                                                                | No       | `overall,changed-files-average,per-changed-file` |
| `debug`             | Enables detailed logging. Automatically activated when `ACTIONS_RUNNER_DEBUG=true`.                                                                                                                                            | No       | `false`                                          |

> Hint: default values have been defined to provide maximal possible information in the comment.

#### Outputs

The following outputs are set by the JaCoCo GitHub Action:

- `coverage-overall`: The overall code coverage percentage.
- `coverage-changed-files`: The code coverage percentage for the changed files.
- `coverage-overall-passed`: A boolean indicating if the overall code coverage meets the minimum threshold.
- `coverage-changed-files-passed`: A boolean indicating if the code coverage for the changed files meets the minimum
threshold.
- `reports-coverage`: A JSON string containing the evaluated coverage per report.
- `groups-coverage`: A JSON string containing the evaluated coverage per report group (populated when `report-groups` is defined).
  
### Examples

- [Customizing the Exclude Paths](#customizing-paths-and-exclude-paths)
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

- You can use wildcard glob patterns to match multiple files:
  - `**/*.xml` will match all XML files in the repository.
- You can specify final list of paths separated by commas.

The `exclude-paths` input allows you to specify files or directories that should be excluded from the code coverage
analysis.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.TOKEN }}'
    paths: |
      module-a/target/jacoco/code-coverage.xml,
      module-b/target/jacoco/code-coverage.xml,
      module-c/target/jacoco/**/*.xml
    exclude-paths: |
      **/temp/**,                       # Exclude temporary files in all directories
      **/legacy/**,                     # Exclude legacy files in all directories
      module-c/target/**/excluded/**    # Exclude specific paths in module-c
```

#### Customizing the Coverage Thresholds

The `global-thresholds` input allows you to define global coverage thresholds for the overall, average changed files,
and each changed file coverage. This input is a string in the format:

- `overall*changed-files-average*changed-file`

Where:

- `overall`: Minimum overall coverage percentage required.
- `changed-files-average`: Minimum average coverage percentage required for changed files.
- `changed-file`: Minimum coverage percentage required for each individual changed file.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.TOKEN }}'
    paths: **/jacoco/**/*.xml
    global-thresholds: 80*70*60  # Min coverage: 80% overall, 70% changed avg, 60% per file

    fail-on-threshold: true  # Fail the GitHub action if any of the thresholds is not reached
```

The user can also specify which thresholds should be used to fail the GitHub action.

```yaml
    # Fail the GitHub action if overall or changed files average threshold is not reached
    fail-on-threshold:
      overall
      changed-files-average 
 ```

#### Customizing the PR Number

The `pr-number` input allows you to specify the number of the pull request. If not provided, the action will attempt
to determine the PR number from the GitHub context.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.TOKEN }}'
    paths: **/jacoco/**/*.xml
    pr-number: ${{ github.event.pull_request.number }}
 ```

#### Customizing the Report Title

The `title` input lets you specify a `custom title` for the JaCoCo coverage report comment.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.TOKEN }}'
    paths: **/jacoco/**/*.xml
    title: 'Custom Coverage Report Title'
```

#### Customizing the Report Groups

The `report-groups` input groups JaCoCo reports under named groups with optional per-group coverage thresholds and
baseline paths. When defined, each group's `paths` is used for scanning and the top-level `paths` input can be omitted.

Each entry is a YAML mapping with:
- `name` (required): Group name shown in the PR comment groups table.
- `paths` (required): List of glob patterns for JaCoCo XML reports in this group.
- `thresholds` (optional): `overall*changed-files-average*per-changed-file` (e.g. `80*70*60`). Missing fields fall back to `report-thresholds-default`, then to 0.0. Global thresholds are a separate evaluation pass.
- `baseline-paths` (optional): List of glob patterns for baseline reports for this group. Falls back to `baseline-paths`.

> **YAML quoting note**: Any `paths`, `baseline-paths`, or `thresholds` value that begins with `*` (e.g. `**/jacoco.xml` or `*70*60`) must be quoted, otherwise YAML interprets the leading `*` as an alias and raises an "undefined alias" error.
> ```yaml
> paths:
>   - '**/jacoco.xml'     # quoted — safe
>   - module/**/jacoco.xml  # no leading * — safe without quotes
> thresholds: '80*70*60'    # quoted — safe
> ```

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.TOKEN }}'
    report-groups: |
      - name: Core
        paths:
          - core/target/site/jacoco/jacoco.xml
        thresholds: 80*70*60
      - name: Modules
        paths:
          - module-a/target/site/jacoco/jacoco.xml
          - module-b/target/site/jacoco/jacoco.xml
        thresholds: 75*65*
        baseline-paths:
          - baseline/modules/**/*.xml
```

#### Customizing the Comment Level

##### No Comment

- When the `comment-level` is set to `none`, no PR comment is posted.

##### Minimal Level

- When the `comment-level` is set to `minimal`, one comment is added to the pull request representing the overall and
changed files coverage for all detected report files.

###### JaCoCo Coverage Report

| Metric (Instruction) | Coverage | Threshold | Δ Coverage | Status |
|----------------------|----------|-----------|------------|--------|
| **Overall**          | 85.2%    | 80%       | +1.3%      | ✅      |
| **Changed Files**    | 78.4%    | 80%       | -0.3%      | ❌      |

> Δ Coverage is visible when `baseline-paths` defined and data is available.

##### Full Level

- When the `comment-level` is set to `full`, one comment is added to the pull request representing the overall and
changed files coverage for all detected report files.

###### JaCoCo Coverage Report

| Metric (Instruction) | Coverage | Threshold | Δ Coverage | Status |
|----------------------|----------|-----------|------------|--------|
| **Overall**          | 85.2%    | 80%       | +1,3%      | ✅      |
| **Changed Files**    | 78.4%    | 80%       | 0.3%       | ❌      |

| Report          | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|-----------------|-----------------|------------------|-------------------|---------------|
| `Report 1 name` | 87.5% / 35.2%   | 60% / 80%        | -0.6% / +1.0%     | ✅/✅           |
| `Report 2 name` | 80.0% / 45.6%   | 40% / 82%        | +0.3% / -2.1%     | ✅/✅           |
| `Report 3 name` | 76.3% / 76.4%   | 50% / 76%        | -2.5% / -1.2%     | ❌/✅           |

| File Path              | Coverage | Threshold | Δ Coverage | Status |
|------------------------|----------|-----------|------------|--------|
| `File1.java`           | 90.1%    | 80%       | +0.3%      | ✅      |
| `File2.java`           | 70.5%    | 80%       | -1.0%      | ❌      |
| `File3.java`           | 82.1%    | 80%       | +2.7%      | ✅      |

> - **(O)** - Overall coverage.
> - **(Ch)** - Coverage for changed files.
> - **Δ Coverage** is visible when `baseline-paths` are defined and data is available.
> - The report table is always visible. When `report-groups` is defined, each group's thresholds are used (with field-level fallback to `report-thresholds-default`); otherwise, reports use `report-thresholds-default` (per-field fallback to 0.0).
> - The groups table is visible when `report-groups` is defined.
> - `global-thresholds` is always evaluated independently as a separate pass over aggregated totals and is never part of the group fallback chain.

##### Changed Level

- When the `comment-level` is set to `changed`, the global summary table is kept and only group, report, and file rows with changed files are shown.

##### Failed Level

- When the `comment-level` is set to `failed`, the global summary table is kept and only rows failing their threshold are shown.

##### Failed-or-Changed Level

- When the `comment-level` is set to `failed-or-changed`, the global summary table is kept and rows are shown when they either have changed files or fail a threshold.

#### Customizing the Skip Unchanged Option and Update Comment

The `skip-unchanged` input, when set to true, filters reports with no changed files before evaluation and comment
generation. This reduces comment noise by removing unchanged reports entirely.

The `update-comment` input, when set to true, updates an existing comment with the latest coverage data instead of
creating a new comment.
The comment is identified by the title.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.TOKEN }}'
    paths: **/jacoco/**/*.xml
    skip-unchanged: true  # Skip commenting for unchanged files
    update-comment: true  # Update the existing comment with the latest coverage data
```

#### Customizing the Baseline Paths

The `baseline-paths` input allows you to define paths to baseline coverage reports. This enables comparing the pull
request coverage with an established baseline, such as the main branch.

**Required**: Each report has defined unique report name (report title). The report name is used to match the baseline
report with the current report.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.TOKEN }}'
    paths: |
      **/jacoco/**/*.xml
    baseline-paths: |
      baseline/master/jacoco/**/*.xml              # Match all baseline reports in master directory for jacoco 
```

#### Customizing the Symbols and Metric Type

The `pass-symbol` and `fail-symbol` inputs allow you to define custom symbols for passing and failing checks in the
pull request comments.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.TOKEN }}'
    paths: **/jacoco/**/*.xml
    metric: 'LINE'            # Select 'line' coverage metric
    pass-symbol: '✔️'         # Custom symbol for passing checks
    fail-symbol: '❗'         # Custom symbol for failing checks
```

#### Customizing the Debug Mode

The `debug` input enables detailed logging for debugging. This is automatically enabled in debug mode
(`ACTIONS_RUNNER_DEBUG=true`).

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.TOKEN }}'
    paths: **/jacoco/**/*.xml
    debug: true  # Enable detailed logging
```

## Developer

Follow the [DEVELOPER.md](DEVELOPER.md) guide to setup the development environment.

## License

[Apache License, Version 2.0](./LICENSE)

## Donate

If you find this project useful or interesting, consider supporting it!

Your donation helps me keep building, maintaining and improving this tool — every bit of support matters and is deeply
appreciated.

- [Buy me a coffee on Ko-fi](https://ko-fi.com/mirpo)

**Thanks for keeping this project alive!**
