# `global-overall-scope`

## Theory

When `report-groups` is configured the action scans each group's own `paths` list to find reports
for group evaluation. Without extra configuration this means a JaCoCo XML file that exists in the
repository but is not matched by any group's `paths` pattern is invisible to the global overall
coverage number — potentially masking low-coverage modules.

`global-overall-scope` controls which reports are included in the **global overall** counter:

| Value | Behaviour |
|-------|-----------|
| `all` **(default)** | The top-level `paths` scan runs in addition to the group scans. Every report found by `paths` contributes to the global overall number, even if it is not part of any group. Ungrouped reports are not evaluated against group thresholds and do not appear in the Groups table — only the global number is affected. |
| `groups-only` | Only reports matched by a group's `paths` pattern count toward global overall. No additional top-level scan is performed. This was the behaviour before this input was introduced. |

This input has no effect when `report-groups` is not configured: the top-level `paths` scan is
always used in that case.

## Ungrouped report warning

When `global-overall-scope: all` and a report is found by the top-level `paths` scan but matched
by no group, the action emits a `WARNING` in the run log:

```
WARNING: Report 'infra/target/jacoco.xml' is not assigned to any report group.
         Including in global overall coverage (global-overall-scope=all).
```

Use these warnings to discover modules that are present in your repository but missing from your
group configuration.

## Valid values

`all` | `groups-only`

## Default

`all`

## Examples

### Default — global overall includes every report

The default `paths: '**/jacoco.xml'` picks up all JaCoCo reports in the repository. Reports
matched by a group contribute to both the group row and the global overall. Reports outside all
groups contribute only to the global overall, with a warning.

```yaml
- uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    # paths defaults to '**/jacoco.xml' — no need to set it explicitly
    global-thresholds: '75*0'
    report-groups: |
      - name: backend
        paths:
          - backend/**/jacoco.xml
        thresholds: '80*70*60'
      - name: frontend
        paths:
          - frontend/**/jacoco.xml
        thresholds: '75*65*50'
    # infra/**/jacoco.xml — not in any group, but still counted in global overall
```

---

### Restrict global overall to grouped reports only

Use `groups-only` to reproduce the pre-default behaviour: global overall is the aggregate of
exactly the reports belonging to defined groups.

```yaml
- uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    global-thresholds: '75*0'
    global-overall-scope: 'groups-only'
    report-groups: |
      - name: backend
        paths:
          - backend/**/jacoco.xml
      - name: frontend
        paths:
          - frontend/**/jacoco.xml
```

---

### Narrow global overall to a subset of modules

Set `paths` to a specific glob and `global-overall-scope: all` to control exactly which modules
feed the global number, independently of group membership.

```yaml
- uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: |
      core/**/jacoco.xml
      api/**/jacoco.xml
    global-thresholds: '80*0'
    global-overall-scope: 'all'
    report-groups: |
      - name: core
        paths:
          - core/**/jacoco.xml
      - name: api
        paths:
          - api/**/jacoco.xml
      - name: infra
        paths:
          - infra/**/jacoco.xml   # counted in groups table but NOT in global overall
```

## See also

- [paths.md](paths.md) — top-level paths scan
- [report-groups.md](report-groups.md) — group configuration and thresholds
- [thresholds.md](thresholds.md) — `global-thresholds` and the global evaluation pass
