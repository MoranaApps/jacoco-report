# `paths` and `exclude-paths`

## Theory

`paths` tells the action where to find JaCoCo XML report files. It is the primary way to point the
action at your build output. Glob patterns are resolved relative to the repository root; both
repository-relative patterns and absolute `${{ github.workspace }}` paths are supported.

`exclude-paths` is applied after `paths` — any XML file whose path matches an exclude glob is
dropped from the scan before evaluation begins.

`paths` defaults to `**/jacoco.xml` and must always be non-empty. When `report-groups` is
configured each group's own `paths` list controls which reports belong to that group, but the
top-level `paths` is still used to compute the global overall coverage (see
[global-overall-scope.md](global-overall-scope.md)).

## Valid values

Both inputs accept a **newline-separated list** of glob patterns. Leading `*` values are safe here
(unlike inside a `report-groups` YAML block).

## Impact

- Only files matched by `paths` and not matched by `exclude-paths` are parsed and evaluated.
- Files excluded via `exclude-paths` are not subject to `evaluate-unchanged` — they are removed before parsing, so they never enter threshold evaluation.
- If no files are found after filtering, the action logs an error and fails.
- Use `debug: 'true'` to log every file discovered by the scan.

## Examples

### Basic glob

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco.xml'
```

### Multiple explicit paths

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: |
      module-a/target/jacoco/code-coverage.xml
      module-b/target/jacoco/code-coverage.xml
      module-c/target/jacoco/**/*.xml
```

### With exclusions

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

## See also

- [report-groups.md](report-groups.md) — organise multi-module projects into named groups
- [global-overall-scope.md](global-overall-scope.md) — how `paths` interacts with `report-groups` for global overall coverage
- [debug.md](debug.md) — enable verbose file-scan logging
