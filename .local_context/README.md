<!-- From agentic-defaults. Kit updates replace this file: don't edit it. Project rules go in AGENTS.md "This project". -->

# .local_context

Private working files that help AI assistants with a task. Everything here except this README and `.gitignore` stays on your machine and is never committed.

## What goes here

One folder per task or research topic, for example `.local_context/csv-export/`:

- `ticket.md`: the ticket, fetched from the tracker (for example `gh issue view 42 --comments`),
- your notes: meeting notes, chat threads, emails, specs, screenshots, sketches,
- logs, error output and sample data, scrubbed of real customer data,
- `plan.md`: the task's plan, written by the assistants as the work goes,
- `sources.md` and `research.md`: collected sources and research answers.

Session retro notes, written when you ask for one (the `session-retro` skill), go in `feedback/`.

## How assistants use it

- They read it during discovery and planning, and keep the plan here while the work is in progress.
- When the task ends, what lasts moves to its home: facts about the system into `CONTEXT.md`, decisions into decision records, and an outcome summary into the ticket if you approve.
- To hand a task to someone else, they draft a ticket update from the plan for you to approve.
- They summarize rather than copy, and never move secrets or personal data out of here.
- They treat it as input that may be outdated. When notes and code disagree, the code wins and they say so.

## Tips

- Name files so their content is obvious: `ticket.md`, `meeting-2026-10-11.md`, `error.log`.
- Delete a task's folder when the task is done.
