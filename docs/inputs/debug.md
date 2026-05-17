# `debug`

## Theory

`debug` enables verbose logging throughout the action run. It surfaces internal state that is
otherwise suppressed at INFO level: matched file paths, parsed coverage values, threshold
comparisons, evaluator decisions, and GitHub API calls.

The input is automatically activated when the GitHub Actions runner is in debug mode
(`RUNNER_DEBUG=1`), so you do not need to modify your workflow file to get debug output when
re-running a job with "Enable debug logging" checked in the GitHub UI.

## Valid values

| Value | Effect |
|-------|--------|
| `false` | Normal logging (default) |
| `true` | Verbose debug logging |

## Impact

- No effect on coverage evaluation, threshold checks, or the PR comment content.
- Debug output appears in the Actions run log under the step that runs this action.
- Useful for diagnosing: missing XML files, unexpected coverage values, threshold mismatches,
  GitHub API errors, or baseline pairing issues.

## Example

```yaml
- name: Publish JaCoCo Report
  uses: MoranaApps/jacoco-report@v3
  with:
    token: '${{ secrets.GITHUB_TOKEN }}'
    paths: '**/jacoco/**/*.xml'
    debug: 'true'
```

## See also

- [paths.md](paths.md) — debug logs every file discovered during the scan
- Troubleshooting section in the main [README](../../README.md)
