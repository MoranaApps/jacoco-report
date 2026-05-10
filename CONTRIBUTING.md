# Contributing to jacoco-report

Thank you for your interest in contributing! This guide covers everything you need to get started.

---

## Table of Contents

- [Reporting Bugs](#reporting-bugs)
- [Requesting Features](#requesting-features)
- [Branch Naming Convention](#branch-naming-convention)
- [Commit Message Convention](#commit-message-convention)
- [Pull Request Process](#pull-request-process)
- [Local Setup](#local-setup)

---

## Reporting Bugs

Use the **[Bug Report](.github/ISSUE_TEMPLATE/bug_report.md)** template when opening a new issue.

Please include:
- A clear description of the bug and what you expected to happen.
- Steps to reproduce (workflow YAML, input values, error output).
- The action version and Python version if running locally.

---

## Requesting Features

Use the **[Feature Request](.github/ISSUE_TEMPLATE/feature_request.md)** template when opening a new issue.

Please include:
- Background: the limitation or pain point driving the request.
- A description of the desired behaviour.
- An example (workflow YAML snippet or expected comment output) if applicable.

---

## Branch Naming Convention

All branches must use one of the following prefixes:

| Prefix | Purpose |
|--------|---------|
| `feature/` | New user-facing functionality |
| `fix/` | Bug fixes |
| `docs/` | Documentation changes only |
| `chore/` | Maintenance, CI, tooling, refactoring |
| `spike/` | Research and investigation tasks |

The suffix should reference the issue number and a short description:

```
feature/108-report-groups-yaml-input
fix/test-violations-data-path
docs/74-v2-v3-migration-guide
chore/add-pylintrc
spike/71-auto-detect-modules-sbt-mvn
```

Verify your branch name before pushing:

```shell
git branch --show-current | grep -E '^(feature|fix|docs|chore|spike)/'
```

---

## Commit Message Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>
```

**Types:** `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`

**Examples:**

```
feat(report-groups): add YAML parser for report-groups input
fix(evaluator): correct threshold fallback when field is absent
docs(readme): align examples to v3 inputs
chore(ci): add concurrency cancel-in-progress
```

Rules:
- Subject line: imperative mood, no trailing period, ≤72 characters.
- Body (optional): explain the *why*, not the *what*.
- Reference the issue: `Closes #108` on its own line at the end.

---

## Pull Request Process

1. **One PR per issue.** Each pull request must address exactly one issue.
2. **Branch from `master`** unless the PR depends on another in-progress branch.
3. **All CI checks must pass** before requesting review. This includes:
   - `pytest --cov=. tests/ --cov-fail-under=80`
   - `pylint $(git ls-files '*.py')`
   - `black --check $(git ls-files '*.py')`
   - `mypy .`
4. **Fill out the PR template.** Do not leave "TBD" placeholders in the Release Notes section.
5. **Squash merge** — the maintainer will squash commits on merge. Keep your commits tidy but do not worry about a perfect history; the squash commit message is what matters.
6. **Request review** from a code owner (see [CODEOWNERS](.github/CODEOWNERS)).

---

## Local Setup

See [DEVELOPER.md](DEVELOPER.md) for full setup instructions, including:
- Python environment setup
- Running Pylint, Black, mypy, and pytest locally
- Running the action script locally with a shell script
- Code coverage reporting
