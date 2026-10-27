---
name: commits-and-prs
description: How to split work into commits, write commit messages, and prepare and describe pull requests. Use when committing, writing a commit message, opening or describing a pull request, or splitting a large change.
---

<!-- From agentic-defaults. Kit updates replace this file except a "## This project" section at the end, which belongs to the project. Edit nothing else. Rules for all work go in AGENTS.md "This project". -->

# Commits and pull requests

## Follow the project first

Check the project's conventions before applying this skill: recent messages (`git log --oneline -20`), a pull request template (`.github/pull_request_template.md`), and `CONTRIBUTING.md`. Where they differ from this skill, the project wins.

## Safety

- Commit, push or open a pull request only when the user asked for it.
- Never force-push a shared branch or rewrite pushed history without the user's explicit agreement.
- Never skip hooks (`--no-verify`). If a hook fails, fix the cause.

## Commits

- **One logical change per commit.** Tests go in the same commit as the code they test. Keep refactoring, formatting and behavior changes in separate commits.
- **Every commit builds and passes the tests**, so the history stays usable for `git bisect` and reverts.
- **Stage by path and check what you're committing** (`git diff --staged`). Leave out secrets, local configuration, generated files, debug code, commented-out code and unrelated changes.

## Commit messages

- **Subject**: imperative mood, under about 60 characters, no full stop. Say what the change does: "Reject expired tokens in session middleware", not "Fix bug" or "Update auth.ts".
- **Body**, only when the reason isn't obvious from the subject: why the change was needed, what alternative you rejected, and any side effects. Wrap at about 72 characters. Reference the issue if there is one.
- Don't narrate the process ("fixed tests", "addressed review") or list the files changed; the diff shows that.

## Pull requests

- **One purpose per pull request, small enough to review in one sitting.** Split larger work: put preparatory refactoring in its own pull request first, then the feature. `(production)`: hide unfinished features behind a switch rather than holding back a huge branch.
- **Before opening one**, bring the branch up to date, run the tests, read your own diff once as a reviewer would, and update any affected `CONTEXT.md`.
- **Title**: written like a commit subject.
- **Description**: short, with only the sections that apply:

```markdown
## What and why
Two to four sentences. Link the issue.

## How it was verified
Tests added, commands run and their results, manual steps. Screenshots for UI changes.

## Risks and rollout
Migrations, configuration changes, feature flags, backwards compatibility.

## Notes for reviewers
Where to start reading, what deserves a close look, and what is deliberately out of scope.
```

- **Review comments**: answer every one, either with a change or with a reason for not changing.
