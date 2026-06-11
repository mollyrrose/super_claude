---
name: qClose
description: "Close a working session — invoke hermes-learn for any reusable pattern, commit + push pending changes, then generate a resume prompt at <project>/.scratch/qclose_resume.md that a fresh Claude Code window can paste back to pick up exactly where we left off. Invoked via /qClose (canonical) OR any case variant — /qclose, /Qclose, /QClose, /QCLOSE all map to this same skill (case-insensitive). If the user types any of these, treat as a /qClose invocation and proceed with this skill's runbook."
---

# qClose — session-handoff in 6 steps

`/qClose` is what you run before walking away from a working session. It commits anything that's still in flight, learns from the session, and leaves behind a single self-contained markdown file the user (or another Claude Code window) can paste in to resume from exactly where this window stopped — without losing the WHY, the open threads, or the in-flight plans.

## When to use

- Before `/clear` when you want to be able to resume later.
- Before closing the terminal at end of day.
- When handing off the session to another window or another machine.
- When the user types `/qClose` (or any case variant).

Skip if the session was purely conversational with no code changes, no plans, no TODO updates, no skill-worthy patterns. There's nothing to hand off.

## The runbook (follow in order)

### Step 1 — Gather window identity

Read once and reuse for the rest of `/qClose`. These values go into both the resume prompt and the TODO heartbeat refresh.

```
branch       = git rev-parse --abbrev-ref HEAD       (or "(no-repo)" if git fails)
session_id   = $CLAUDE_SESSION_ID first 6 hex        (fallback: a short hash of start_ts + pid)
pid          = current process id
host         = $env:COMPUTERNAME on Windows, hostname on Unix
start_ts     = process start time, ISO 8601 UTC
hb_ts        = current ISO 8601 UTC timestamp
window_code  = w-<branch>-<sessid6>                  (fallback: w-<branch>-pid<ppid>)
project_root = git rev-parse --show-toplevel         (or current working dir if no repo)
```

If `project_root` resolves to `~/.claude`, write the resume file to `~/.claude/.qclose_resume_<sessid6>.md` instead — per the global CLAUDE.md "Not for this directory" rule, `~/.claude` is not a project and shouldn't get a `.scratch/`.

### Step 2 — Run hermes-learn

Invoke the existing hermes-learn skill via the Skill tool. Capture its output verbatim.

Outcomes:
- Wrote a `hermes-auto-<slug>` skill → record path + 1-line description for the resume prompt.
- No skill captured (the expected case most of the time) → record honestly.
- Crashed → record `hermes-learn failed: <reason>` and continue. Never block `/qClose` on hermes-learn failure.

### Step 3 — Discover session state (all read-only)

- **Plans in flight**: `Glob ~/.claude/plans/*.md` modified in the last 24h. For each, read the first H1 line; list as `<path> — <H1>`.
- **TODO files**: `Glob <project>/{TODO.md,todo.md,tot.md,TODOS.md}`. For each file, find entries tagged `[w-<window_code>]` (this window's own entries only). For each matching entry, update its `hb:` field to `hb_ts` in the source file AND in the resume prompt. Per CLAUDE.md liveness protocol: do NOT touch entries owned by other windows.
- **AGENTS.md chain**: walk from `project_root` down to the deepest path Claude touched this session. List every AGENTS.md on the route.
- **Recently modified files**: `git ls-files -m -o --exclude-standard` for staged/untracked + `git log --since="24 hours ago" --name-only --pretty=format:` for last-day commits. Dedupe, cap at 20.
- **Worktrees**: `git worktree list`. Include in resume prompt only if more than one entry.
- **Background processes**: any background bash jobs (`run_in_background: true`) you started this session that haven't been reported completed. Also any process the user explicitly told you to "watch" or "keep running". If none, omit the section.

### Step 4 — Generate the resume prompt

Write to `<project_root>/.scratch/qclose_resume.md` (or `~/.claude/.qclose_resume_<sessid6>.md` in the `~/.claude` special case). Create `.scratch/` if missing — it's already gitignored.

Use this exact template, filling each placeholder with the values from steps 1–3:

```markdown
# Resume context — session closed <hb_ts>

> Paste this entire block into a fresh Claude Code window (opened in the project root).
> Claude will re-read the docs, refresh TODO heartbeats, check the plan + open threads,
> and continue from where the previous window stopped.

## What this window was doing

<1-2 paragraph synthesis of the session's intent and outcomes — the WHY,
the SO WHAT, and the open question, not a tool-call log. If you can't honestly
write this from memory of the session, say "session intent not captured" and
list the user's most recent 3 prompts verbatim as a fallback.>

## Where we stand

- **Project root**: `<project_root>`
- **Branch**: `<branch>` @ commit `<short_hash>` — `<commit subject line>`
- **Working tree**: clean | dirty (<N> tracked modified, <M> untracked)
- **Worktrees** (if more than one):
  - `<path>` @ `<branch>`
- **Upstream**: pushed to `<remote>/<branch>` | local-only | no upstream configured

## Open plan files

- `<path>` — `<first H1 line>`
- (or "no plan files modified in last 24h")

## Open TODO entries (this window only: `[w-<window_code>]`)

- `[w-<code>] <created_ts> pid:<N> host:<H> start:<ST> hb:<refreshed_hb_ts>` — <task description>
- (or "no TODO entries for this window")

> Entries owned by other windows are intentionally omitted. Do not touch them on resume.

## Context docs to re-read on resume

- `<project_root>/CLAUDE.md`
- `<project_root>/AGENTS.md` (if exists)
- (nearest-descendant AGENTS.md files on the touched-paths chain)
- (the global `~/.claude/CLAUDE.md` is always loaded automatically; don't list it here)

## Recently modified files (last 24h, top 20)

- `<path>` <timestamp>

## Background activities to monitor

- (none) | `<process>` — <what it's doing, where its output lives, expected duration>

## Hermes-learn outcome

- <wrote `hermes-auto-<slug>` → `~/.claude/skills/hermes-auto-<slug>/SKILL.md`; description: ...>
- (or "no skill captured this session")

## How to resume

1. Open Claude Code in `<project_root>`.
2. Paste this entire block as your first prompt.
3. Claude will (a) verify the branch + last commit match, (b) re-read the docs above, (c) check the plan file(s) and TODO entries, then continue from the open thread.

---
Generated by /qClose at <hb_ts>. Window: `<window_code>` host:`<host>` pid:`<pid>`.
```

### Step 5 — Commit + push

If `git status --porcelain` returns nothing: skip; print `commit: no pending changes`.

Otherwise:

- **Stage explicitly** — list the files to add, never `git add -A` / `git add .`. The new `.scratch/qclose_resume.md` must NOT be staged (gitignored, intentional).
- Commit with this message format:
  ```
  qClose session-handoff <YYYY-MM-DD>

  Resume prompt staged at .scratch/qclose_resume.md (gitignored).
  <one short line — what was actually done this session, mined from the
  "What this window was doing" synthesis>.
  ```
- **Do NOT push automatically.** After the commit lands, ask the user explicitly: `Push commit <short_hash> to <remote>/<branch>? (yes/no)`. Default to no-push if the user doesn't answer affirmatively. Reason: not every project in the user's setup is push-ready — `/qClose` is meant to be safe to run across all of them, so the runbook can't assume push is the right move. The user's standing "push" authorisation in `super_claude` (memory `feedback_push_to_main.md`) applies to *explicit* `push` commands the user types, NOT to `/qClose`'s flow.
- If a pre-commit hook fails: **do not bypass with `--no-verify`** (global project rule). Surface the failure, leave the resume prompt written, exit cleanly. The user resolves the hook and re-runs `/qClose`.

### Step 6 — Print the closeout

Final single block to the user:

```
qClose done.
- commit: <short hash>  (or "no pending changes")
- push:   awaiting your confirmation: push <short_hash> to <remote>/<branch>?  (or "pushed", "user said no", "skipped — <reason>")
- learn:  wrote hermes-auto-<slug>  (or "no skill captured")
- resume: <absolute path to qclose_resume.md>

Paste the resume file's contents into your new Claude Code window after /clear or in a fresh terminal.
```

## Edge-case matrix

| Situation | Behaviour |
|---|---|
| Not in a git repo | Skip git steps; still generate resume prompt with `branch: (no-repo)` |
| `~/.claude/skills/hermes-learn/` missing | Skip Step 2 silently; resume says `hermes-learn skill not installed, skipped` |
| `.scratch/` does not exist | `mkdir -p`; it's gitignored at `.gitignore:40` |
| Multiple worktrees on the same branch as this window | Warn user per CLAUDE.md "Dual-window safety", still generate resume prompt, do NOT commit on shared tree without explicit ok |
| Push fails (network, auth, no upstream) | Commit stays local; closeout shows `push: failed — <reason>` |
| Push always requires explicit user yes | The default is ASK, never auto-push. Applies to every repo without exception. |
| `project_root == ~/.claude` | Write to `~/.claude/.qclose_resume_<sessid6>.md` (not `~/.claude/.scratch/`) per CLAUDE.md "Not for this directory" |
| User has no TODO files at all | Omit the "Open TODO entries" section entirely |
| No plan files in `~/.claude/plans/` touched in 24h | Omit the "Open plan files" section |

## What `/qClose` deliberately does NOT do

- Does NOT enumerate every file Claude read — only the modified ones. Reading is not state.
- Does NOT touch TODO entries owned by other `[w-...]` windows. Heartbeat refresh is window-local.
- Does NOT close any background processes the user wanted to keep running. It just records them.
- Does NOT delete the resume markdown when done — the file is the artifact; the user decides when to clean it up. (`.scratch/` cleanup is the user's concern.)
- Does NOT inject anything into the next session's prompt automatically. The user pastes manually — that's the contract. No hidden state survives a `/clear`.
