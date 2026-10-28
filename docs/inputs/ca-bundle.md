# `ca-bundle`

## Theory

`ca-bundle` points the action at a PEM file of CA certificates to trust. The action uses it for two things:

1. Its own `pip install` of the action's dependencies (passed to pip as `PIP_CERT`).
2. Every GitHub API request the action makes (passed to `requests` as `verify=<path>`).

Use it on a self-hosted runner behind a TLS-intercepting proxy, where the proxy re-signs `https://api.github.com`
with a corporate root CA that the default trust store does not contain.

The value is a **path** to the file, not the certificate content. It is absolute, or relative to the workspace
(`GITHUB_WORKSPACE`). Prefer an absolute path to a file on the runner image; see [Security](#security).

## Security

- Take the CA file from the runner image or from trusted content, such as the base branch. Never take it from
  a file a pull request can change.
- Why: a PR that replaces the bundle can make the action send the token over a connection verified against an
  attacker's CA. This applies to `pull_request_target` with a PR checkout, and to any job that checks out PR head.
- A workspace path (`${{ github.workspace }}/...`) is safe only when the job does not check out the PR's copy of
  that file.

## Valid values

| Value | Effect |
|-------|--------|
| `''` (default) | No custom bundle. Behavior is unchanged. |
| Path to an existing file | The file is the trust source for pip and for the GitHub API calls. |
| Path to a missing file | The action fails. See [Impact](#impact). |

## Trust rules

- For GitHub API calls the file is the **only** trust source. It must contain every CA needed to reach
  `api.github.com` from the runner.
- Behind a proxy that intercepts all HTTPS traffic, the file is the proxy's root CA.
- If some traffic bypasses the proxy, append the public roots too, so both paths verify:

  ```bash
  cat corp-root.pem "$(python -c 'import certifi; print(certifi.where())')" > bundle.pem
  ```

  You can also append the OS bundle instead of certifi's.
- pip 24.2 or newer adds the file to its OS and certifi trust. Older pip replaces its default trust with the file,
  so include the public roots as above.

## Precedence

- If `ca-bundle` is set, it wins over `REQUESTS_CA_BUNDLE` and `CURL_CA_BUNDLE` for both pip and the API calls.
- If `ca-bundle` is empty, nothing changes. A `REQUESTS_CA_BUNDLE` set on the action's step `env:` still works.
  This is a **legacy fallback**: prefer `ca-bundle`, which is explicit, documented and covered by the action's tests.

## Impact

- The action checks the file before it installs anything. If the path is not a file, the `setup` step fails with an
  `::error::` annotation and no venv is created.
- A local run (see [DEVELOPER.md](../../DEVELOPER.md)) also rejects a missing file at input validation.
- Proxy variables such as `HTTPS_PROXY` keep working; `ca-bundle` only changes which CAs are trusted.

## Example

Self-hosted runner whose image provides the corporate root CA at `/etc/ssl/certs/corp-root-ca.pem` (illustrative path):

```yaml
name: Publish JaCoCo Report in PR comments

on:
  pull_request:
    types: [opened, synchronize, reopened, edited]

jobs:
  generate-report:
    runs-on: self-hosted
    permissions:
      contents: read
      issues: write
      pull-requests: read
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - uses: actions/setup-python@v7
        with:
          python-version: '3.11'

      - name: Publish JaCoCo Report in PR comments
        uses: MoranaApps/jacoco-report@v3
        with:
          token: '${{ secrets.GITHUB_TOKEN }}'
          ca-bundle: /etc/ssl/certs/corp-root-ca.pem
```

## See also

- [README: Self-hosted runner behind a corporate proxy](../../README.md#self-hosted-runner-behind-a-corporate-proxy)
- [README: Troubleshooting](../../README.md#troubleshooting)
