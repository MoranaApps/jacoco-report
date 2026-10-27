---
name: implementation
description: Working rules for implementing a task or plan step - delivering it fully and test-first, handling problems the plan didn't mention, walls, tests that break, dependencies, when to stop, and what to report. Use when writing or changing code for a task.
---

<!-- From agentic-defaults. Kit updates replace this file except a "## This project" section at the end, which belongs to the project. Edit nothing else. Rules for all work go in AGENTS.md "This project". -->

# Implementation

## Input

A task description, or a plan file with the step numbers to do. Do only the steps you were given. When working from a plan file, read its Goal, Requirements and your steps, and set its status to `in progress` if it is still `planned`.

## Steps

1. Read the `CONTEXT.md` files from the root down to the code you will change, then the code itself. Follow the patterns already there.
2. If the step changes a contract (an API spec, message format, schema or shared type), change the contract first, then the code that implements it. Regenerate types or clients from it if the project does that.
3. Work test-first, following the `tdd` skill: write a failing test, watch it fail, write the simplest code that passes, run the tests, tidy up.
4. For a bug, reproduce it in a failing test first. If the cause isn't obvious, follow the `debugging` skill.
5. Deliver each step fully. No stubs, placeholders, hard-coded stand-ins or "for now" versions of required behavior. If a step can't be delivered fully, you have hit a wall (see below).
6. Keep the change focused: no unrelated edits, and no abstractions or options the task doesn't need.
7. Use the project's standard commands (`make test`, `make lint`, `make check`) when it has them. Run the step's Verify command if it has one, and tick the step off (`- [x]`) only when it passes.
8. Run the tests for the area you changed, and `make check` (or the project's equivalent) before reporting done.
9. Last, the context check from the `context-md` skill: run its `check.sh`, update each `CONTEXT.md` your change made wrong or incomplete, or note why none needed it.

## Work the plan didn't mention

You will find things the task or plan didn't foresee.

- **Fix without asking** when your change caused it or it blocks your step: a bug, a broken import or type, missing error handling, or a validation or permission check the change needs to be correct and secure. Add a test where it matters, and list each fix in your report.
- **Stop and report** when it needs a new dependency, a new table, service or layer, a change to a contract or public interface, a different library, or any other design decision. Say what you found, what you propose and why.
- **Leave alone** problems that existed before your change or sit outside the files you are working on. List them in your report.
- When unsure which of these applies, stop and report.

## Tests that fail or break

- Never edit or delete an existing test to make it pass. A failing test means the code is wrong, unless the requirement changed; then say so and wait for the user to agree.
- If one change breaks many tests that don't test the behavior you changed, the tests are coupled to the implementation. Stop and report which tests broke and why, instead of editing each one.

## When you hit a wall

If a step can't be done as planned (a missing API, a library that doesn't behave, conflicting requirements):

1. Stop. Don't write a stand-in.
2. Write it under Blockers in the plan: which step, what blocks it, what you tried, the evidence, and what is unknown.
3. List two or three options with their cost: split (finish what can be finished, move the rest into its own task), spike (a throwaway experiment on a separate branch), re-plan (the design is wrong), or a visible limit (behind a switch that is off, recorded in the ticket).
4. Report and stop. The user or the architect chooses.

## Dependencies

Install only packages the task or plan names. If an install fails, stop and report. Never try a similar-looking name or an alternative package instead: a misspelled package name can belong to a fake or malicious package.

## Live systems

Infrastructure, deployments and data outside a local or test setup are changed by the user, never by you.

- **Run freely**: plans and dry runs (`terraform plan`, `terragrunt plan`) and read-only commands (`describe`, `list`, `show`, logs, status).
- **Hand to the user**: everything that applies, deploys, scales, restarts, rolls back, or creates, changes or deletes a resource, even when asked to "just do it". Give the exact command, the folder to run it from, and one line on what it changes.
- **Don't print secrets**: skip read-only commands that show secret values, such as `terraform output -json`, `terraform state pull` or a secret store's get command. Refer to secrets by name.

## Don't get stuck reading

If you have read or searched five times in a row without changing anything, stop and say in one sentence what you still need. Then either make the change, or report the missing information as a blocker.

## Stop and report instead of continuing when

- the task or plan turns out to be wrong or impossible as written,
- the same failure remains after two different attempts.

Report what you found. Don't improvise a redesign.

## Report

Short: the result first, one line per item, no narration.

- What changed, one line per file.
- Tests added or changed, and the result of the last test run, with failure output if any.
- Fixes you made that the plan didn't mention, and problems you left alone.
- The context check: `CONTEXT.md` files updated, or why none needed it.
- Blockers and open questions.

Don't commit unless asked. When asked, follow the `commits-and-prs` skill.
