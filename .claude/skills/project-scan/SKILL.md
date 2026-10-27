---
name: project-scan
description: Survey a repository to learn what it does, which technologies it uses, how it is structured, and how to build, test and run it, then record that in the root CONTEXT.md and AGENTS.md. Use when starting in an unfamiliar project, when there is no root CONTEXT.md, or when asked to refresh the project overview.
---

<!-- From agentic-defaults. Kit updates replace this file except a "## This project" section at the end, which belongs to the project. Edit nothing else. Rules for all work go in AGENTS.md "This project". -->

# Project scan

The goal is the lay of the land: a short root `CONTEXT.md` and working build and test commands in `AGENTS.md`, so that every later task starts informed instead of rediscovering the project.

## Steps

1. **Run the survey** from the repository root: `bash <this skill's folder>/survey.sh`, using the path of [survey.sh](survey.sh) next to this file. It is read-only and prints a compact overview: languages, structure, build and CI files, scripts, test locations, existing docs, installed packs, recent commits, most-changed files and local notes. If you can't run it, gather the same facts with file listings and searches.
2. **Read only what the survey points to**, in this order:
   - the README and existing `CONTEXT.md` or `AGENTS.md` files,
   - the main build or dependency file,
   - the CI workflow, which shows the real build and test commands,
   - the contracts the survey lists (API specs, schemas), skimmed for what they cover,
   - the entry points (`main`, server start-up, CLI, app root),
   - one or two representative modules, especially the most-changed ones,
   - notes in `.local_context/` about the project as a whole.

   **Budget:** about 25 file reads after the survey, more only for a large monorepo. Stop reading once you can fill the shape below. Read docs written for people only to confirm facts you are writing down. Report conflicts you notice, but don't audit those docs line by line.
3. **Verify the commands.** Run the test command, and the build if it's quick. If a command fails or needs services you don't have, record it as unverified with a one-line reason. Don't install anything without asking.
4. **Write or refresh the root `CONTEXT.md`** in the shape below, following the `context-md` skill: written for agents, stable facts only. Keep content that is still correct. When existing docs disagree with the code or with each other, trust the code and note the conflict. Mark anything you inferred rather than confirmed with "(unverified)".
5. **Add area `CONTEXT.md` files** (for example `backend/`, `ui/`, each service) where the detail an agent needs would push the root past about 150 lines. Each starts with `Parent: ../CONTEXT.md`, adds only its own detail, and links the real documents (decision records, specs, guides) instead of restating them.
6. **Fill in the "This project" section of `AGENTS.md`**: the profile, proposed from evidence as the `project-profile` skill describes and marked "(proposed)" until the user confirms it; the standard commands (`make setup`, `run`, `build`, `test`, `lint`, `format`, `check`) and what each runs, plus anything else that must pass before work counts as done. Write commands and what they need, never results: pass counts, durations, dates and current failures go stale and belong in your report. Add "(unverified)" to a command you couldn't run.
7. **Standard commands.** The survey lists missing standard targets. Don't add them yourself. In your report, propose the missing targets, each wrapping the project's real command, using [Makefile.template](Makefile.template) as the shape. Until they exist, list the real commands under the standard names in "This project".
8. **Installed packs.** The survey's "Installed packs" section lists the packs agd installed. Compare each with the stack you found. A pack named after a framework, platform or datastore (for example `flask`, `react`, `spring`, `relational-database`, `terraform`, `aws`, `heroku`) is unused when no dependency, build file, configuration or code uses that technology. For each unused pack, propose `agd remove <pack>` in your report, with one line of evidence. Never run it yourself. Never propose removing `core`, a pack that isn't about a technology (such as `research` or `copilot-hook`), or a pack you aren't sure about. Skip this step when the section says None.
9. **Report** briefly: the proposed profile and its evidence, what you wrote, what is unverified, the conflicts you found, the standard targets to add, the packs to remove, and questions only a person can answer.

Don't rewrite `README.md` or other docs written for people. If they are wrong, list what's wrong in your report.

## Root CONTEXT.md shape

An index for agents: enough to orient, with pointers to area files for detail.

```markdown
# <Project name>

## Purpose
What the system does and for whom, in two or three sentences.

## Tech stack
Languages, frameworks, datastores, messaging, infrastructure. Versions only where they matter.

## Structure
One line per top-level directory or service, linking its CONTEXT.md if it has one.

## How it fits together
A Mermaid diagram of the main parts and external systems (see the `diagrams` skill), plus two or three sentences.

## Domain
Core entities and their relationships (an erDiagram if it helps), roles, lifecycles.

## Contracts
API specs, message formats, schemas and shared types, with paths and who owns each.

## Running it
Point to the commands in AGENTS.md. Note required services, environment variables and seed data.

## Conventions
Rules that hold across the whole codebase.

## Key decisions
One line each, linking decision records if the project keeps them.

## Invariants and gotchas
```

## Useful tools

Use these when installed; fall back to git and plain searches when not. Never install tools without asking.

| Tool | Use it for |
|---|---|
| `git ls-files`, `git log` | What's tracked, what changed recently, the history of a file |
| `rg` (ripgrep) | Fast code search that respects `.gitignore` |
| `fd` | Finding files by name |
| `tree -L 2 --gitignore` | A quick picture of the directory layout |
| `ast-grep` | Structural search, such as every call to a function or every class implementing an interface |
| `scc` or `tokei` | Size by language (the survey uses them when present) |
| `jq`, `yq` | Reading JSON and YAML configuration |
