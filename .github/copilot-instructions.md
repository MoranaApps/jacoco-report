# Copilot Instructions — jacoco-report

## Purpose

This file defines the coding contract for all AI-assisted sessions (Copilot, Claude Code) on this project.
Rules use constraint words: **Must** / **Must not** / **Prefer** / **Avoid**.

---

## TDD Workflow (highest priority)

1. Before writing any code, create or update `SPEC.md` in the relevant package directory.
2. Propose the full test-case table (name · one-line intent · input summary · expected output) and wait for confirmation.
3. Write all failing tests first (red), then implement until green.
4. After all tests pass, update `SPEC.md` with the confirmed test-case table.

Must not write implementation code before the test-case table is approved.

---

## Output Discipline

- Responses Must be concise — prefer ≤10 lines of prose outside code blocks.
- Must end each change with three lines: _What changed_ / _Why_ / _How to verify_.
- Must not paste large unchanged code blocks; show only the diff-relevant lines.
- PR body Must be treated as a changelog. Append new entries under `## Update [YYYY-MM-DD]` with the commit hash. Never rewrite the entire body.

---

## Language Rules

- Python 3.12+ syntax. Must use type hints on all public functions and classes.
- Must use `logging` — never `print()`.
- Must use lazy `%` formatting in all log calls: `logger.info("value: %s", val)`.
- Must not use f-strings or format strings inside logging calls.
- Prefer f-strings for all other string templates.
- Imports Must be at the top of the file, grouped: stdlib → third-party → local.

---

## Docstrings

- Must include a short one-line summary.
- Structured sections where applicable: `Parameters`, `Returns`, `Raises`.
- Must not include tutorials, usage examples, or narrative prose.

---

## Testing Rules

- Must not access private members (`_name`) in tests — test only the public API.
- Shared fixtures Must live in the nearest `conftest.py`.
- Fixture factory return types Must be annotated as `Callable[..., T]`.
- `MockerFixture` parameters Must be type-annotated.
- Must not add free-standing comments between test methods; use `# --- section ---` separators only.

---

## Inputs and Validation

- Action inputs Must be read exclusively from environment variables.
- Parsing and validation Must be centralised in one layer (`ActionInputs`).
- Must not duplicate validation logic across modules.

---

## Code Quality

- Every `.py` file including `__init__.py` Must carry the project copyright header.
- Must not introduce bare `# type: ignore` without an inline justification comment.
- Must not add `# pylint: disable` inline — use `.pylintrc` entries instead.

---

## QA Gate Commands

Run these before marking any task done:

```shell
pytest --cov=. tests/ --cov-fail-under=80
pylint $(git ls-files '*.py')
black --check $(git ls-files '*.py')
mypy .
```

All four Must pass with no errors before a PR is opened.

---

## Common Pitfalls

- Avoid commenting out code and leaving it — delete or implement.
- Avoid `continue-on-error: true` in CI steps that gate correctness.
- Avoid storing inter-step values in `$GITHUB_ENV` — use `$GITHUB_OUTPUT`.
- Avoid tag-pinned GitHub Actions (`@v3`) — prefer SHA digest pins.
