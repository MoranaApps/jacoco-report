# `baseline-paths`

## Theory

`baseline-paths` enables **Δ coverage comparison** — the PR comment and the job summary gain a
**Δ Coverage** column, and the action sets delta outputs, showing how coverage changed relative to an
established reference point, typically the `master` branch reports stored as build artifacts.

The action matches each scanned report to a baseline report by **path** first (same directory
structure), then by **report name** (the `name` of the JaCoCo XML's `<report>`, the Maven plugin's
`<title>`) for baselines kept in another directory. Each report should therefore have a unique name so
the name pairing is unambiguous. When a report has no matching baseline entry, its Δ column renders as
`0.0%` and its `reports-coverage` entry gets no `delta`.

Every Δ is a change in **percentage points**: the coverage now minus the coverage in the baseline. For
the global and group rows, reports without a baseline match count as unchanged, so a baseline that
covers only some reports still shows their change, weighted by the size of the whole set.

When `report-groups` is configured, per-group `baseline-paths` override the top-level value for
that specific group. If top-level `baseline-paths` is set and multiple groups omit their own
`baseline-paths`, inheritance is ambiguous and grouped baseline scans are skipped for those groups.

## Valid values

Newline-separated glob patterns resolved relative to the repository root.

```text
baseline/master/jacoco/**/*.xml
```

The current `paths` must not match the baseline files. The baseline reports are scanned separately; if `paths`
(or the default `**/jacoco.xml`) also matches them, they are parsed as current reports too. Each baseline report
then pairs with itself, the global Δ becomes 0, and `coverage-overall` counts it twice. `exclude-paths` filters
only the current scan and does not affect the baseline scan, so exclude the baseline folder with
`exclude-paths: 'baseline/**'`.

## Impact

- Adds a **Δ Coverage** column to all comment tables (global, groups, reports, changed-files).
- The column is omitted only when no baseline data exists at all.
- Sets the outputs `coverage-overall-delta` and `coverage-changed-files-delta` (the global row's Δ,
  e.g. `-0.59`) and adds `delta` (`{"overall": …, "changed_files": …}`) to each matched entry of
  `reports-coverage` and `groups-coverage`. The outputs are empty, and no entry gets `delta`, when
  there is no baseline or no report matched one. See [README → Outputs](../../README.md#outputs).
- With `skip-unchanged` and `evaluate-unchanged: false`, the global Δ (comment and outputs) covers
  only the reports with changed files, while `coverage-overall` still counts the filtered ones.
- Has no effect on threshold evaluation unless `fail-on-threshold` includes `no-decrease`. Then the baseline is
  the reference of that gate. See [thresholds.md](thresholds.md#no-decrease-rules).
- With `baseline-sha` and `baseline-metadata-path` set and the baseline unverified, the Δ values stay as above, but
  `no-decrease` is skipped and the comment gets a note. See [Verify the baseline commit](#verify-the-baseline-commit).

## Verify the baseline commit

`no-decrease` compares against whatever baseline it finds. A baseline built from a different commit (for example,
a newer `master` build) can make the gate fail or pass for reasons outside the PR. Set both inputs to check that the
baseline comes from the PR's base commit.

The check is about consistency, not authenticity: the metadata file comes from the same artifact as the reports, so
whoever produced the artifact also chose its `sha`. Download baselines only from runs you trust, such as pushes to
`master` (the consumer example below uses `--event push`, so a pull-request run from a fork's `master` is not picked).

| Input | Value |
|-------|-------|
| `baseline-sha` | The full commit SHA the baseline must come from: 40 hexadecimal characters, or 64 for SHA-256 repositories. Example: `${{ github.event.pull_request.base.sha }}` |
| `baseline-metadata-path` | A JSON file, relative to the workspace, with the baseline's commit: `{"sha": "<full sha>"}` |

Rules:

- Set both or neither. Setting only one fails input validation with
  `'baseline-sha' and 'baseline-metadata-path' must be set together, or both left empty.`
- `baseline-sha` must be a full SHA, else input validation fails with
  `'baseline-sha' must be a full commit SHA (40 or 64 hexadecimal characters).`
- The SHA is compared with the file's `sha` exactly, ignoring case and surrounding whitespace. A short SHA never
  matches.
- One SHA and one metadata file cover every baseline in the run: the top-level `baseline-paths` and each group's.
- Neither input set: the action works as without verification, and `baseline-verified` is empty.

Outcome:

| Case | Result |
|------|--------|
| The file's `sha` equals `baseline-sha` | Verified. An INFO log line is written; `baseline-verified` is `true`. |
| Unverified (see the list below) | One `::warning::` names the reason; `baseline-verified` is `false`. |

Unverified cases: the metadata file is missing, unreadable or not UTF-8 (a BOM is allowed), is larger than 65,536
characters, is not valid JSON, is not a JSON object, has no non-empty string `sha`, its `sha` is not a full commit SHA,
or its `sha` differs from `baseline-sha`. The warning shows the file's `sha` only when it is a full commit SHA.

When the baseline is unverified:

- The Δ columns and the `coverage-*-delta` outputs are unchanged. They are informational only.
- `no-decrease` is skipped and passes, with an INFO log line. Its rules do not run.
- Comment or job summary rows that dropped do not count as failing for `comment-level` (see
  [comment-level.md](comment-level.md#failed)).
- The comment and the job summary show a `⚠️ **Unverified baseline:**` note under the summary table, when the Δ column
  is shown. The SHA from the file is not written there.
- With no baseline report found at all, `no-decrease` still fails with `'no-decrease' needs a baseline`. The
  verification only decides whether the baseline that was found comes from the PR's base commit.

The output `baseline-verified` is `true`, `false`, or empty when verification is not configured.

## Examples

### Compare against stored master reports

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    paths: '**/jacoco/**/*.xml'
    exclude-paths: 'baseline/**'
    baseline-paths: 'baseline/master/jacoco/**/*.xml'
```

### Warn when coverage dropped

```yaml
- name: Publish JaCoCo Report
  id: jacoco
  uses: MoranaApps/jacoco-report@v3
  with:
    paths: '**/jacoco/**/*.xml'
    exclude-paths: 'baseline/**'
    baseline-paths: 'baseline/master/jacoco/**/*.xml'

- name: Warn on a coverage drop
  # The comparison reads the output as a number; an empty output (no baseline) counts as 0.
  if: steps.jacoco.outputs.coverage-overall-delta < 0
  run: echo "::warning::Overall coverage dropped against the baseline."
```

### Fail when coverage dropped

Fails the step when overall coverage drops against the baseline. The base-branch reports must already be in
`baseline/master/jacoco/` before this step, for example downloaded by an earlier step.

Listing only `no-decrease` replaces the default `fail-on-threshold` list (`overall,changed-files-average,per-changed-file`).
To keep those checks, list them too: `fail-on-threshold: 'overall,changed-files-average,per-changed-file,no-decrease'`.

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    paths: '**/jacoco/**/*.xml'
    exclude-paths: 'baseline/**'
    baseline-paths: 'baseline/master/jacoco/**/*.xml'
    fail-on-threshold: 'no-decrease'
```

### Verified baseline: producer and consumer workflows

The producer runs on every push to `master`. It stores the test reports and a metadata file with the commit SHA
as one artifact. The consumer runs on pull requests. It downloads the latest successful `master` artifact and
passes the PR's base SHA, so the baseline is verified before `no-decrease` uses it.

Producer (`.github/workflows/baseline.yml`):

```yaml
name: Coverage baseline
on:
  push:
    branches: [master]

permissions:
  contents: read

jobs:
  baseline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: mvn -B verify
      - name: Write baseline metadata
        env:
          COMMIT_SHA: ${{ github.sha }}
        run: |
          printf '{"sha": "%s"}\n' "$COMMIT_SHA" > baseline-metadata.json
      - uses: actions/upload-artifact@v4
        with:
          name: jacoco-baseline
          path: |
            **/target/site/jacoco/jacoco.xml
            baseline-metadata.json
          if-no-files-found: error
```

Consumer (`.github/workflows/pr-coverage.yml`):

```yaml
name: PR coverage
on:
  pull_request:

permissions:
  contents: read
  pull-requests: write
  actions: read # needed to list and download the master run's artifact

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: mvn -B verify
      - name: Download the latest master baseline
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          run_id=$(gh run list --branch master --event push --workflow baseline.yml --status success --limit 1 \
            --json databaseId -q '.[0].databaseId')
          gh run download "$run_id" -n jacoco-baseline -D baseline/master
      - name: Publish JaCoCo Report
        uses: MoranaApps/jacoco-report@v3
        with:
          paths: '**/jacoco.xml'
          exclude-paths: 'baseline/**'
          baseline-paths: 'baseline/master/**/jacoco.xml'
          baseline-sha: ${{ github.event.pull_request.base.sha }}
          baseline-metadata-path: baseline/master/baseline-metadata.json
          fail-on-threshold: 'overall,changed-files-average,per-changed-file,no-decrease'
```

The latest successful `master` run is not always the PR's base commit. Then the baseline is unverified and
`no-decrease` is skipped with a warning. To download the run for the base commit itself, pass the SHA to
`gh run list`, for example `--commit "$BASE_SHA"` with `BASE_SHA: ${{ github.event.pull_request.base.sha }}` in
the step's `env`. If that run does not exist, the download step fails.

### Per-group baselines (via `report-groups`)

See [report-groups.md](report-groups.md) — each group supports its own `baseline-paths` field.

## See also

- [report-groups.md](report-groups.md) — per-group `baseline-paths` configuration
- [comment-level.md](comment-level.md) — interaction with `baseline-paths` (Δ column visibility)
