---
name: session-retro
description: Evaluate how the current chat session went - delivered requirements, user corrections, rework, kit rules followed and cost against earlier sessions - give a rule-based verdict, and write a short note in .local_context/feedback/ with the kit file behind any problem and a fix. Use only when the user asks for it, for example "retro this session" or "how did this session go".
---

<!-- From agentic-defaults. Kit updates replace this file except a "## This project" section at the end, which belongs to the project. Edit nothing else. Rules for all work go in AGENTS.md "This project". -->

# Session retro

A retro judges one session on evidence, not on impressions: what was delivered, what the user had to correct, and what it cost compared with earlier sessions. The verdict follows fixed rules, and the user confirms it. A generic problem goes back to the kit, a project problem into the project's own files. Write one only when the user asks.

## Steps

1. **Gather.** Don't re-run the session's commands or re-read files.
   - In Claude Code, run `bash .claude/skills/session-retro/stats.sh` for the numbers and the project's usual numbers, and `bash .claude/skills/session-retro/stats.sh --prompts` for the user's prompts. In other tools, take the prompts from this conversation and numbers only if the tool showed them; otherwise write "not shown". Never estimate.
   - Label each prompt: **request** (new work or a question), **answer** (to your question), **correction** (redirects or fixes your work) or **complaint** (says something went wrong). A repeated prompt after an interrupt counts once.
2. **Check each criterion** and note the evidence:
   - **Delivered**: list the requirements, from the plan's Musts if there is a plan, else from the prompts labeled request. Mark each met, not met or not checked, with the test, command or output that shows it.
   - **Corrections**: the number of prompts labeled correction or complaint, each with one line on why.
   - **Rework**: checks, reviews or user findings that failed after you said a step was done.
   - **Rules**: the "Done means" checks in `AGENTS.md`: tests pass and cover the change, the context check ran, no unrelated changes, the plan is updated. Mark each yes, no or not applicable.
   - **Cost**: **within** when output tokens and tool calls are both at most twice the project's usual numbers, **above** when either is more, **no baseline** when stats.sh says so or numbers aren't shown.
3. **Apply the rules.**
   - Outcome: **done** when every requirement is met, **failed** when none is, else **partly done**.
   - Count the misses: outcome not done, more than 1 correction, any rework, any rule marked no, cost above.
   - Verdict: **went well** with 0 misses, **mixed** with 1, **went badly** with 2 or more or when the outcome is failed.
4. **Find the cause** of each miss. Name the kit file whose rule was involved by its installed path, such as `.claude/skills/tdd/SKILL.md` or `AGENTS.md`, and say whether the rule was **missing**, **wrong**, **ignored** or **too long**. Kit files carry the "From agentic-defaults" marker. If no kit file was involved, write "not a kit problem".
5. **Propose a fix** for each cause: **project-only** (name where it goes: a `## This project` section at the end of that agent or skill, "This project" in `AGENTS.md`, or a `CONTEXT.md`) or **generic** (every project using the kit would benefit; describe the change to the kit file).
6. **Confirm.** Show the user the verdict, the outcome and each prompt you labeled correction or complaint, and ask one question: are they right? Apply their answer.
7. **Write** the note to `.local_context/feedback/<YYYY-MM-DD>-<task>.md`, with today's date and a short slug for the task, in the format below. Keep it under 50 lines. Then add one row to `.local_context/feedback/log.tsv`, creating it with this header line if it doesn't exist (tab-separated): `date task verdict prompts corrections tool_calls output_tokens cache_read_tokens lines_changed`. Use `-` for numbers that weren't shown; lines_changed is added plus removed lines from stats.sh's Git lines.
8. **Report** the verdict and the note's path in one line. For a generic fix, add: "To send it to the kit's maintainers, run `agd feedback .local_context/feedback/<file>.md`. It opens a pre-filled issue for you to review, and posts nothing by itself." Then stop.

## Format

```markdown
# <The main problem, as an issue title, e.g. "Tester wrote 40 tests for one small function"; or "Session went well: <task>">

Kit: agentic-defaults <version from the first line of AGENTS.md>
Tool and models: <e.g. Claude Code, sonnet and haiku>
Verdict: went well | mixed | went badly (<n> misses, confirmed by the user)

## Delivered
Outcome: done | partly done | failed
- <requirement>: met | not met | not checked. <evidence>

## Corrections
- <prompt number>: correction | complaint. <why, one line> (or "none")

## Rework
- <what was caught afterwards, and by whom> (or "none")

## Rules
- Tests: yes | no | n/a. Context check: yes | no | n/a. Unrelated changes: none | <which>. Plan: yes | no | n/a.

## Cost
within | above | no baseline
<the lines stats.sh printed, numbers the tool showed, or "not shown">

## Cause
- `<installed path>`: missing | wrong | ignored | too long. <which rule, one line> (or "none")

## Fix
project-only | generic: <the change, and where it goes> (or "none")
```

## Rules

- Write the kit file's installed path exactly, on its own, in backticks. `agd feedback` finds the kit's maintainers from these paths.
- The prompts list is for labeling only. Never copy prompt text into the note or the log; refer to prompts by number.
- Summarize. Never put secrets, credentials, customer data, personal data or private code in the note. If the problem can't be explained without some of it, say so to the user and leave it out unless they agree.
- Never run `agd feedback`, open an issue or post anything yourself. The user decides whether to send the note.
- Skip a retro when the user didn't ask for one, and don't write more than one note per session.
