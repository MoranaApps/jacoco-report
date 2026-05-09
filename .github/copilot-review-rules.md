# Copilot Review Rules — jacoco-report

## Default Review

Review every PR in this priority order:

1. **Correctness** — logic errors, wrong conditions, off-by-one, silent failures
2. **Security** — token/secret exposure in logs, injection risks, unvalidated external input
3. **Tests** — missing cases, disabled scenarios left commented out, wrong assertions
4. **Maintainability** — duplication, unclear naming, missing type hints
5. **Style** — formatting, docstring gaps, import order

Group all comments by severity before posting:

- **Blocker** — Must be fixed before merge (correctness or security issue)
- **Important** — Should be fixed; explain the risk if deferred
- **Nit** — Optional improvement; prefix with `Nit:`

Each comment Must state: _what the issue is_ + _why it matters_ + _the minimal fix_.

---

## Double-Check Mode

Apply to PRs that touch: authentication, secrets handling, external API calls,
data persistence, or any backward-incompatible change.

Re-check explicitly:

- Are secrets or tokens logged at any level?
- Are all external calls guarded against pagination / rate limits?
- Is the change idempotent under retries?
- Does the change break any existing callers or action input contracts?
- Are exit codes correct for all failure paths?

---

## Domain-Specific High-Risk Areas

| Area | What to check |
|------|--------------|
| GitHub API calls | Pagination handled for >100 items; rate-limit errors surfaced, not swallowed |
| Token handling | `GITHUB_TOKEN` / PAT never written to logs, comments, or output files |
| PR comment format | Comment header string unchanged — consumers may parse it for deduplication |
| Exit codes | Non-zero exit on threshold failure; zero exit when `fail-on-threshold` list is empty |
| `skip-unchanged` filter | Applied at scan stage, not at display stage — filtering order must not change evaluation totals |

---

## Non-Goals

Do not comment on:

- Formatting already enforced by Black
- Import order already enforced by linters
- Naming that follows the existing project convention consistently
