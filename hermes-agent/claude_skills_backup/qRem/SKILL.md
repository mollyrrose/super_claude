---
name: qRem
description: Refresh project orientation — read INDEX.md, STARTUP.md, exclude/SYSTEM_STRATEGIES/TODO.md and survey the latest 5 git commits — before starting non-trivial work in a project repo.
---

# qRem — Quick Remember

## When to use

Invoke at the start of a session, or before non-trivial work in an unfamiliar project. Skip in tiny one-shot tasks where the context is already obvious from the user's message.

## What to do

1. Check whether the working directory is a git repo (`git rev-parse --is-inside-work-tree`). If not, stop and tell the user — qRem is repo-scoped.
2. Find the task list first: read `exclude/SYSTEM_STRATEGIES/TODO.md` if it exists (the canonical location), else an older `exclude/TODO.md`, else a root `TODO.md`. Then read whichever of these also exist: `INDEX.md`, `STARTUP.md`, `AGENTS.md`, and `exclude/SYSTEM_STRATEGIES/SYSTEM_STATUS.md` (`INDEX.md` is at the project root). Read `README.md` only as a fallback when `INDEX.md` is absent (it is the narrative source of last resort). If any are missing, note it once; do not create them unless the user asks.
3. Run `git log -5 --oneline` (or `--stat` if the user wants more detail) to see the latest five commits.
4. Produce a 4–8 line orientation summary: project purpose (from INDEX/README if available), what's in flight (from TODO, current branch name), what changed recently (from git log), and any immediate concerns or open threads.
5. **Radar gate (optional, strict, kill-switched).** Unless `AI_RADAR_DISABLE=1` or the AI Radar bundle (`~/.claude/okf/ai-radar/`) is absent, run the `/radar-check` gate logic: compare this project's model pins / key deps / named patterns against radar entries marked `status: superseded` or carrying a `supersedes`. Append AT MOST one or two `[radar] ...` lines for material, high-confidence hits ("you use X; Y is now better/safer because Z — resource"). If nothing strongly qualifies, emit nothing. Honor no-nagging: silence is the default; never interrupt, never auto-change anything.

## Do not

- Do not edit `INDEX.md` / `STARTUP.md` / `exclude/SYSTEM_STRATEGIES/TODO.md` / `TODO.md` automatically. Updates to these files happen only when the user explicitly asks, or when work in this session has materially changed their content and the user has confirmed.
- Do not run this skill repeatedly inside one session unless the user requests a re-orient (e.g. after a branch switch).
- Do not invent these files where they do not exist.
