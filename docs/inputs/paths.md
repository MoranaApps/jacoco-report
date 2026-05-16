# `paths` and `exclude-paths`

## Theory

`paths` tells the action where to find JaCoCo XML report files. It is the primary way to point the
action at your build output. Glob patterns are resolved relative to the repository root; both
repository-relative patterns and absolute `${{ github.workspace }}` paths are supported.

`exclude-paths` is applied after `paths` — any XML file whose path matches an exclude glob is
dropped from the scan before evaluation begins.

`paths` is required when `report-groups` is not configured. When `report-groups` is set, each
group's own `paths` list is used instead and the top-level `paths` input can be omitted.

## Valid values

Both inputs accept a **newline-separated list** of glob patterns. Leading `*` values are safe here
(unlike inside a `report-groups` YAML block).

## Impact

- Only files matched by `paths` and not matched by `exclude-paths` are parsed and evaluated.
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

- [report-groups.md](report-groups.md) — alternative to top-level `paths` for multi-module projects
- [debug.md](debug.md) — enable verbose file-scan logging
