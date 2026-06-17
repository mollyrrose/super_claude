---
name: qRem
description: Refresh project orientation — read INDEX.md, STARTUP.md, TODO.md / tot.md and survey the latest 5 git commits — before starting non-trivial work in a project repo.
---

# qRem — Quick Remember

## When to use

Invoke at the start of a session, or before non-trivial work in an unfamiliar project. Skip in tiny one-shot tasks where the context is already obvious from the user's message.

## What to do

1. Check whether the working directory is a git repo (`git rev-parse --is-inside-work-tree`). If not, stop and tell the user — qRem is repo-scoped.
2. Find the task list first: read `exclude/TODO.md` if it exists (the canonical location — `exclude/` is the gitignored per-project folder), otherwise fall back to a root `TODO.md` / `tot.md`. Then read whichever of these also exist: `INDEX.md`, `STARTUP.md`, `AGENTS.md` (location of `INDEX.md` doesn't matter — check the root, then `exclude/`). Read `README.md` only as a fallback when `INDEX.md` is absent (it is the narrative source of last resort). If any are missing, note it once; do not create them unless the user asks.
3. Run `git log -5 --oneline` (or `--stat` if the user wants more detail) to see the latest five commits.
4. Produce a 4–8 line orientation summary: project purpose (from INDEX/README if available), what's in flight (from TODO/tot, current branch name), what changed recently (from git log), and any immediate concerns or open threads.

## Do not

- Do not edit `INDEX.md` / `STARTUP.md` / `exclude/TODO.md` / `TODO.md` / `tot.md` automatically. Updates to these files happen only when the user explicitly asks, or when work in this session has materially changed their content and the user has confirmed.
- Do not run this skill repeatedly inside one session unless the user requests a re-orient (e.g. after a branch switch).
- Do not invent these files where they do not exist.
