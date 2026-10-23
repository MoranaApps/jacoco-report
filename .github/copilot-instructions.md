# Copilot Instructions — jacoco-report

Primary rules: [`AGENTS.md`](../AGENTS.md) (the working agreement, shared with Claude Code) and
[`CONTEXT.md`](../CONTEXT.md) (what the code is, its structure and conventions). Read both first.
This file adds only what's specific to this project and not already covered there.

---

## Language and logging

- Must use type hints on all public functions and classes.
- Must use `logging` — never `print()`.
- Must use lazy `%` formatting in log calls: `logger.info("value: %s", val)`.
- Must not use f-strings or `.format()` inside a log call. Prefer f-strings for every other string.
- Imports grouped: stdlib → third-party → local.

---

## Docstrings

- Must include a short one-line summary.
- Structured sections where applicable: `Parameters`, `Returns`, `Raises`.
- Must not include tutorials, usage examples, or narrative prose.

---

## Testing

- Must not access private members (`_name`) in tests — test only the public API.
- Shared fixtures Must live in the nearest `conftest.py`.
- Fixture factory return types Must be annotated as `Callable[..., T]`.
- `MockerFixture` parameters Must be type-annotated.

---

## Inputs and validation

- Action inputs Must be read exclusively through `ActionInputs` — never `os.environ` directly
  elsewhere for inputs.
- Must not duplicate validation logic across modules.

---

## Code quality

- Must not introduce a bare `# type: ignore` without an inline justification comment.
- Must not add `# pylint: disable` inline — use `.pylintrc`'s `[MESSAGES CONTROL]` instead, each
  entry with a comment explaining why.

---

## QA gate

Run before marking any task done (same commands as `AGENTS.md` → "This project"):

```shell
pytest --cov=. tests/ --ignore=tests/integration/live --cov-fail-under=80
pylint $(git ls-files '*.py')
black --check $(git ls-files '*.py')
mypy .
```

All four Must pass before a PR is opened.

---

## Common pitfalls

- Avoid commenting out code and leaving it — delete or implement.
- Avoid `continue-on-error: true` in CI steps that gate correctness.
- Avoid storing inter-step values in `$GITHUB_ENV` — use `$GITHUB_OUTPUT`.

---

## Pull requests

Follow [`.github/pull_request_template.md`](pull_request_template.md) and `CONTRIBUTING.md` →
"Pull Request Process": Overview, Release Notes (no "TBD" placeholders), Related issue.
