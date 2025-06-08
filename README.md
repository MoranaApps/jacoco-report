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
- **Python 3.12+**: Ensure you have Python 3.12 installed on your system.

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
          python-version: '3.12'

      - name: Publish JaCoCo Report in PR comments
        uses: MoranaApps/jacoco-report@v1
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

| Name                   | Description                                                                                                                                                                                                                                                                                    | Required                         | Default                                                                                                   |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------|-----------------------------------------------------------------------------------------------------------|
| `paths`                | Comma-separated paths to the generated Jacoco XML files. Supports wildcard glob patterns.                                                                                                                                                                                                      | **Yes**                          |                                                                                                           |
| `exclude-paths`        | Comma-separated paths to exclude from coverage analysis. Supports glob patterns.                                                                                                                                                                                                               | No                               | ''                                                                                                        |
| `global-thresholds`    | Global coverage thresholds for the overall, average changed files, and changed file coverage. <br> Format: `overall*average-changed-files*changed-file`.                                                                                                                                       | No                               | `0.0*0.0*0.0`                                                                                             |
| `title`                | Title for the coverage report comment added to the Pull Request.                                                                                                                                                                                                                               | No                               | single: `JaCoCo Coverage Report` <br> multi: `Report: {report name}` <br> module: `Module: {module name}` |
| `pr-number`            | Number of the pull request. If not provided, the action will attempt to determine <br> the PR number from the GitHub context.                                                                                                                                                                  | No                               | ''                                                                                                        |
| `metric`               | A metric to use for coverage calculation (`instruction`, `line`, `branch`, `complexity`, `method`, `class`).                                                                                                                                                                                   | No                               | `instruction`                                                                                             |
| `sensitivity`          | Control the sensitivity of the coverage evaluation to the thresholds (`minimal,` `summary,` or `detail`).                                                                                                                                                                                      | No                               | `detailed`                                                                                                |
| `comment-mode`         | Mode of the comment (`single` for one comment, `multi` for comments per jacoco.xml file, `module` for comment per each module).                                                                                                                                                                | No                               | `single`                                                                                                  |
| `modules`              | List of modules and their unique paths (e.g., `management: context/management`).<br>Required when `comment-mode` set to `module`. <br> Optional when `comment-mode` set to `single`.                                                                                                           | If `comment-mode` is `module`    | ''                                                                                                        |
| `modules-thresholds`   | List of modules and their coverage thresholds (e.g., `core: 80`). Optional when `comment-mode` set to `module`.                                                                                                                                                                                | No                               | ''                                                                                                        |
| `skip-unchanged`       | If enabled (true), filters JaCoCo-related comments and violations to show only relevant changes.<br>It does not print unchanged lines from module and report tables, similarly does not output violations and skips entire comments for unmodified modules and reports, reducing noise in PRs. | No                               | false                                                                                                     |
| `baseline-paths`       | Paths to baseline coverage reports for comparison. Supports wildcard glob patterns.<br>Paths have to be valid for modules if used.                                                                                                                                                             | No                               | ''                                                                                                        |
| `update-comment`       | If enabled (true), ensures the action updates an existing comment with the latest coverage <br> data instead of creating a new comment. Prevents comment clutter in pull requests.                                                                                                             | No                               | true                                                                                                      |
| `pass-symbol`          | Symbol displayed next to passing checks in the pull request comments (e.g., ✅, **Passed**).                                                                                                                                                                                                    | No                               | ✅                                                                                                         |
| `fail-symbol`          | Symbol displayed next to failing checks in the pull request comments (e.g., ❌, **Failed**).                                                                                                                                                                                                    | No                               | ❌                                                                                                         |
| `fail-on-threshold`    | Defines which thresholds must be met to pass the check. Accepts `true` (fail on any threshold), `false` (never fail), or a choice of **the** following values (in a list): `overall`, `changed-files-average`, `changed-file`.                                                   | No                               | true (fail on overall, changed-files-average, and per-changed-file)                                       |
| `debug`                | Enables detail logging for debugging purposes. Automatically activated if the GitHub <br> workflow is run in debug mode (ACTIONS_RUNNER_DEBUG=true).                                                                                                                                           | No                               | false                                                                                                     |

> Hint: default values have been defined to provide maximal possible information in the comment.

#### Outputs

The following outputs are set by the JaCoCo GitHub Action:

- `coverage-overall`: The overall code coverage percentage.
- `coverage-changed-files`: The code coverage percentage for the changed files.
- `coverage-overall-passed`: A boolean indicating if the overall code coverage meets the minimum threshold.
- `coverage-changed-files-passed`: A boolean indicating if the code coverage for the changed files meets the minimum
threshold.
- `reports-coverage`: A JSON string containing the evaluated coverage reports.
- `modules-coverage`: A JSON string containing the evaluated coverage modules.
- `violations`: A list of violations encountered during the coverage evaluation.
  
### Examples

- [Customizing the Exclude Paths](#customizing-paths-and-exclude-paths)
- [Customizing the Global Coverage Thresholds](#customizing-the-global-coverage-thresholds)
- [Customizing the PR Number](#customizing-the-pr-number)
- [Customizing the Report Title and Sensitivity](#customizing-the-report-title-and-sensitivity)
- [Customizing the Comment Mode and Modules](#customizing-the-comment-mode-and-modules)
  - [Minimal Sensitivity](#minimal-sensitivity)
  - [Summary Sensitivity](#summary-sensitivity)
  - [Detailed Sensitivity](#detailed-sensitivity)
- [Customizing the Skip Unchanged Option and Update Comment](#customizing-the-skip-unchanged-option-and-update-comment)
- [Customizing the Baseline Paths](#customizing-the-baseline-paths)
- [Customizing the Symbols and Metric Type](#customizing-the-symbols-and-metric-type)
- [Customizing the Debug Mode](#customizing-the-debug-mode)

#### Customizing Paths and Exclude Paths

The `paths` input allows you to specify the paths to the JaCoCo XML files that should be included in the code coverage
analysis.

- You can use wildcard glob patterns to match multiple files:
  - `**/*.xml` will match all XML files in the repository.
- You can specify final list of paths separated by commas.

The `exclude-paths` input allows you to specify files or directories that should be excluded from the code coverage
analysis.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v1
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

- `overall*average-changed-files*changed-file`

Where:

- `overall`: Minimum overall coverage percentage required.
- `average-changed-files`: Minimum average coverage percentage required for changed files.
- `changed-file`: Minimum coverage percentage required for each individual changed file.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v1
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
  uses: MoranaApps/jacoco-report@v1
  with:
    token: '${{ secrets.TOKEN }}'
    paths: **/jacoco/**/*.xml
    pr-number: ${{ github.event.pull_request.number }}
 ```

#### Customizing the Report Title and Sensitivity

The `title` input lets you specify a `custom title` for the JaCoCo coverage report comment.

- `single`: `{custom title}`
- `multi`: `{custom title}{report name}`
- `module`: `{custom title}{report name}`

> **Hint:** `{report name}` is required to produce unique titles for each report.

The `sensitivity` input allows you to choose between a `minimal,` `summary` or `detail` sensitivity levels. This
setting control:

- `minimal`: Only the overall coverage and changed files coverage are displayed.
- `summary`: The overall coverage, changed files coverage, and module coverage are displayed.
- `detail`: The overall coverage, changed files coverage, module coverage, and file coverage are displayed.

With increased sensitivity and more detailed comments, the number of detectable violations increases, too.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v1
  with:
    token: '${{ secrets.TOKEN }}'
    paths: **/jacoco/**/*.xml
    title: 'Custom Coverage Report Title'
    sensitivity: 'summary'  # Select a summary sensitivity of the coverage report
```

#### Customizing the Comment Mode and Modules

The `comment-mode` input controls how the comments are organized:

- `single`: One comment for the entire report.
- `multi`: Multiple comments, one for each xml file.
- `module`: Individual comments for each module and its xml files.

The `modules` input specifies a list of modules and their unique paths. Required when `comment-mode` is set to `module`.
**Hint:** When using baseline fature keep in mind that the module path should be same for baseline and current report.

The `modules-thresholds` input allows you to set custom coverage thresholds for each module. Optional when
`comment-mode` is set to `module`. Missing thresholds values will use the global thresholds.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v1
  with:
    token: '${{ secrets.TOKEN }}'
    paths: **/jacoco/**/*.xml
    sensitivity: 'minimal'      # Select a minimal sensitivity of the coverage report
    comment-mode: 'single'      # Add a single comment for the all reports
    modules: |
      core: core
      module-a: context/module_a
      module-b: module_b
      utils: utils
    modules-thresholds: |
      core:80.5**                # Custom threshold for core module only for overall
      utils:*70.0*               # Custom threshold for utils module only for changed files
      module-a:80.0*70.0*        # Custom thresholds for common module for overall and changed files
      module c:80.0*70.0*25.0    # Custom thresholds for common module for overall, changed files and per changed file
```

##### Minimal Sensitivity

The `minimal` sensitivity level displays only the overall coverage and coverage for changed files.

- When the `comment-mode` is set to `single`, one comment is added to the pull request representing the overall and
changed files coverage for all detected report files.
- When the `comment-mode` is set to `multi`, multiple comments are added to the pull request, one for each detected
report file.
- When the `comment-mode` is set to `module`, individual comments are added to the pull request for each module and its
detected report files.

###### JaCoCo Coverage Report

| Metric (Instruction) | Coverage | Threshold | Δ Coverage | Status |
|----------------------|----------|-----------|------------|--------|
| **Overall**          | 85.2%    | 80%       | +1.3%      | ✅      |
| **Changed Files**    | 78.4%    | 80%       | -0.3%      | ❌      |

> Δ Coverage is visible when `baseline-paths` defined and data is available.

##### Summary Sensitivity

- When the `comment-mode` is set to `single`, one comment is added to the pull request representing the overall and
changed files coverage for all detected report files.
- When the `comment-mode` is set to `multi`, multiple comments are added to the pull request, one for each detected
report file.
  - The module table is not visible in the `multi` mode as there is no module information available.
- When the `comment-mode` is set to `module`, individual comments are added to the pull request for each module and its
detected report files.
  - The module table is not visible in the `module` mode as the overall and changed files coverage represent the module
coverage.

###### JaCoCo Coverage Report

| Metric (Instruction) | Coverage | Threshold | Δ Coverage | Status |
|----------------------|----------|-----------|------------|--------|
| **Overall**          | 85.2%    | 80%       | +1.3%      | ✅      |
| **Changed Files**    | 78.4%    | 80%       | -0.3%      | ❌      |

| Module      | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|-------------|-----------------|------------------|-------------------|---------------|
| `module-1`  | 87.5% / 35.2%   | 60% / 80%        | -0.6% / +1.0%     | ✅/✅           |
| `module-2`  | 80.0% / 45.6%   | 40% / 82%        | +0.3% / -2.1%     | ✅/✅           |
| `module-3`  | 76.3% / 76.4%   | 50% / 76%        | -2.5% / -1.2%     | ❌/✅           |

| Report          | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|-----------------|-----------------|------------------|-------------------|---------------|
| `Report 1 name` | 87.5% / 35.2%   | 60% / 80%        | -0.6% / +1.0%     | ✅/✅           |
| `Report 2 name` | 80.0% / 45.6%   | 40% / 82%        | +0.3% / -2.1%     | ✅/✅           |
| `Report 3 name` | 76.3% / 76.4%   | 50% / 76%        | -2.5% / -1.2%     | ❌/✅           |

> - **(O)** - Overall coverage.
> - **(Ch)** - Coverage for changed files.
> - **Δ Coverage** is visible when `baseline-paths` are defined and data is available.
> - Module table visible when input `modules` is defined and `comment-mode` is `single`.
> - The report table is always visible. When `modules` and `modules-thresholds` are defined, the module's thresholds
> are used; otherwise, the minimal thresholds are used.

##### Detailed Sensitivity

- When the `comment-mode` is set to `single`, one comment is added to the pull request representing the overall and
changed files coverage for all detected report files.
- When the `comment-mode` is set to `multi`, multiple comments are added to the pull request, one for each detected
report file.
  - The module table is not visible in the `multi` mode as there is no module information available.
- When the `comment-mode` is set to `module`, individual comments are added to the pull request for each module and its
detected report files.
  - The module table is not visible in the `module` mode as the overall and changed files coverage represent the module
coverage.

###### JaCoCo Coverage Report

| Metric (Instruction) | Coverage | Threshold | Δ Coverage | Status |
|----------------------|----------|-----------|------------|--------|
| **Overall**          | 85.2%    | 80%       | +1,3%      | ✅      |
| **Changed Files**    | 78.4%    | 80%       | 0.3%       | ❌      |

| Module      | Coverage (O/Ch) | Threshold (O/Ch) | Δ Coverage (O/Ch) | Status (O/Ch) |
|-------------|-----------------|------------------|-------------------|---------------|
| `module-1`  | 87.5% / 35.2%   | 60% / 80%        | -0.6% / +1.0%     | ✅/✅           |
| `module-2`  | 80.0% / 45.6%   | 40% / 82%        | +0.3% / -2.1%     | ✅/✅           |
| `module-3`  | 76.3% / 76.4%   | 50% / 76%        | -2.5% / -1.2%     | ❌/✅           |

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
> - Module table visible when input `modules` is defined and `comment-mode` is `single`.
> - The report table is always visible. When `modules` and `modules-thresholds` are defined, the module's thresholds
> are used; otherwise, the minimal thresholds are used.

#### Customizing the Skip Unchanged Option and Update Comment

The `skip-unchanged` input, when set to true, optimizes JaCoCo-related comments by focusing only on relevant changes
in the pull request. It removes unchanged lines from the modules table and reduces the number of generated comments by
skipping entire modules and reports with no modified files.

The `update-comment` input, when set to true, updates an existing comment with the latest coverage data instead of
creating a new comment.
The comment is identified by the title.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v1
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
  uses: MoranaApps/jacoco-report@v1
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
  uses: MoranaApps/jacoco-report@v1
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
  uses: MoranaApps/jacoco-report@v1
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
