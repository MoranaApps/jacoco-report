---
name: project-profile
description: The project profile (stage, audience, team, sensitive data) and which practices it calls for, so the engineering fits this project instead of a large enterprise. Use when deciding how much rigor a change needs, when a skill item carries a profile tag such as (production), when proposing a profile in a project scan, or when a design feels heavier than the project.
---

<!-- From agentic-defaults. Kit updates replace this file except a "## This project" section at the end, which belongs to the project. Edit nothing else. Rules for all work go in AGENTS.md "This project". -->

# Project profile

Not every project needs every practice. The profile in the "This project" section of `AGENTS.md` says what kind of project this is, and that decides which costly practices apply. Cheap correctness and safety always apply.

## The four dimensions

| Dimension | Values |
|---|---|
| Stage | `prototype` (exploring, may be thrown away), `early` (first real users), `production` (people depend on it), `mature` (long-lived, many dependents) |
| Audience | `personal`, `internal` (your own organization), `customer` (specific clients, often under contract), `public` (anyone on the internet) |
| Team | `solo`, `small` (one team), `several` (teams depending on each other's code) |
| Handles | `none`, or any of `money`, `personal data`, `regulated data`, `safety` |

If the profile is missing, assume `early`, `internal`, `small`, `none`, and say so.

## Tags

Items in the kit's skills marked with a tag apply only when the profile matches. Items without a tag always apply. An item with several tags applies when any one of them matches, and a tag on a heading covers everything under it.

| Tag | Applies when |
|---|---|
| `(production)` | Stage is `production` or `mature` |
| `(external)` | Audience is `customer` or `public` |
| `(public)` | Audience is `public` |
| `(teams)` | Team is `several` |
| `(sensitive)` | Handles is anything but `none` |

## Always, whatever the profile

- Validate input, check access to the specific record, use parameterized queries, keep secrets out of code.
- Test the behavior you change, and never weaken a test.
- Stop before anything that loses data or can't be undone, and never apply infrastructure changes or deploy yourself.
- End every task with the context check.

## What each value adds or relaxes

- **Stage `prototype`**: test-first for logic you will keep; glue code and layout may go untested. Breaking changes are fine. A root `CONTEXT.md` is enough. Say which code is throwaway.
- **Stage `early`**: the kit's defaults, without the tagged items.
- **`(production)`**: migrations that keep live data and running code working, no breaking change without a migration path, and switches for unfinished features.
- **`(external)`**: versioned, documented API contracts; contract tests for what clients use; a security review for every change to authentication, permissions or input handling.
- **`(public)`**: also abuse limits (rate limits, input size caps) and accessibility checks.
- **`(teams)`**: decision records for choices other teams depend on; contracts first, with contract tests, between teams.
- **`(sensitive)`**: a security review for changes that touch that data, an audit trail of who changed it, and a backup before migrations that change it.

## Don't build for a bigger project

Skip a practice whose cost outweighs what it prevents here, and say so in one line. Signs of building for a bigger project than this one:

- layers, interfaces or base classes with a single implementation,
- generic repositories, event buses, plugin systems, configuration frameworks,
- separate services, queues or infrastructure that no requirement asks for,
- practices tagged for a profile this project doesn't have.

## Proposing a profile

In a project scan, propose a profile from evidence, mark it "(proposed)", and ask the user to confirm it:

- **Stage**: deployment files, deploy steps in CI, release tags, a live URL in the README.
- **Audience**: how users sign in, public endpoints, client names in the README or tickets.
- **Team**: the survey's contributor count, a `CODEOWNERS` file.
- **Handles**: payment, billing or rate fields, personal data in the models, compliance notes.
