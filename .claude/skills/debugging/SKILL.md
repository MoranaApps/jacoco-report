---
name: debugging
description: Find the root cause of a bug or failing test before fixing it. Use when something behaves unexpectedly, a test fails for an unclear reason, or a fix attempt didn't work.
---

<!-- From agentic-defaults. Kit updates replace this file except a "## This project" section at the end, which belongs to the project. Edit nothing else. Rules for all work go in AGENTS.md "This project". -->

# Debugging

Find the cause first, then fix it once. Guessing at fixes wastes more time than finding the cause.

## Steps

1. **Reproduce.** Get a reliable reproduction, ideally a failing test. If you can't reproduce it, collect evidence (logs, inputs, versions, environment), say so, and don't fix blind.
2. **Read the actual error.** Read the full message and stack trace, and open the code at the line it points to.
3. **Narrow it down.** Compare a case that works with one that fails: an input, a commit (`git log`, `git bisect`), a configuration. Halve the difference until one thing remains.
4. **Test one hypothesis at a time.** Check it with evidence, such as a log line, a debugger or a smaller test, rather than by reasoning in circles. Note what each check ruled out.
5. **Fix the cause, not the symptom.** Don't catch and ignore the error, special-case the failing input, or add retries around a logic bug.
6. **Verify.** The reproduction passes and the related tests pass. Remove temporary logging.

## Stop rule

If three hypotheses have failed, stop changing code. Report what you reproduced, what you ruled out and the evidence you have, and ask for direction.
