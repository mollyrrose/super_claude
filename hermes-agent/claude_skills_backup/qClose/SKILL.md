---
name: qClose
description: "Close a working session — invoke hermes-learn for any reusable pattern, commit + push pending changes, then generate a per-session unique resume prompt at <project>/.scratch/qclose_resume_<sessid6>.md that a fresh Claude Code window can paste back to pick up exactly where we left off, in the EXACT worktree where the work happened. Invoked via /qClose (canonical) OR any case variant — /qclose, /Qclose, /QClose, /QCLOSE all map to this same skill (case-insensitive). If the user types any of these, treat as a /qClose invocation and proceed with this skill's runbook."
---

# qClose — session-handoff in 7 steps

`/qClose` is what you run before walking away from a working session. It commits anything that's still in flight, learns from the session, and leaves behind a **per-session-unique** markdown file the user (or another Claude Code window) can paste in to resume from exactly where this window stopped — without losing the WHY, the open threads, the in-flight plans, OR the working-tree context.

## Why "per-session unique" matters (the bug this skill defends against)

The previous flat `qclose_resume.md` filename caused four real failures observed across multiple windows:

1. **Two windows on the same project close in the same hour** → the second `/qClose` silently overwrote the first's resume file. The first window's context was lost.
2. **A new window opened the resume file and the original closer's session "didn't remember" creating it** — there was no durable index linking the file back to the session that wrote it. The closer relied on conversational memory, which doesn't survive `/clear` or compaction.
3. **The resume file was opened in the wrong worktree** — the user pasted it into the parent worktree window when the actual work happened in `.worktrees/<branch>/`. Recovery looked fine but pointed at the wrong HEAD.
4. **The closeout block buried the resume path in a list** — easy to miss, easy to paste the wrong line. The user wanted a single, bolded, copy-paste-shaped block.

Every step below maps to one of these failures.

## When to use

- Before `/clear` when you want to be able to resume later.
- Before closing the terminal at end of day.
- When handing off the session to another window or another machine.
- When the user types `/qClose` (or any case variant).

Skip if the session was purely conversational with no code changes, no plans, no TODO updates, no skill-worthy patterns. There's nothing to hand off.

## The runbook (follow in order)

### Step 0 — Cross-window pre-check (NEW, runs FIRST)

Before doing anything else, check `~/.claude/.qclose_index.jsonl` for collisions:

1. If the index file doesn't exist, create an empty one (`touch` equivalent). Continue.
2. Read the last 10 lines. Each line is one prior `/qClose` event.
3. For each recent entry, check: same `project_root` AND same `branch` AND `hb_ts` within the last 30 minutes?
4. If yes, surface to the user:
   ```
   Heads up — another window closed the same branch <N minutes> ago:
     <prior resume path>
   Likely the OTHER window's work. Proceed with /qClose anyway? (yes/no)
   ```
5. Default-stop on `no` or no response. The user decides whether this is a real second close or a duplicate.

This catches the "two-windows-on-one-branch" case before any file gets overwritten.

### Step 1 — Gather window identity (worktree-aware)

Read once and reuse for the rest of `/qClose`. These values go into the resume frontmatter, the closeout block, and the index entry.

```
branch         = git rev-parse --abbrev-ref HEAD       (or "(no-repo)" if git fails)
session_id     = $CLAUDE_SESSION_ID FULL (not truncated) (fallback: a short hash of start_ts + pid)
sessid6        = first 6 hex chars of session_id        (used in the filename + window code)
pid            = current process id
ppid           = parent process id (terminal)
host           = $env:COMPUTERNAME on Windows, hostname on Unix
start_ts       = process start time, ISO 8601 UTC
hb_ts          = current ISO 8601 UTC timestamp
window_code    = w-<branch>-<sessid6>                  (fallback: w-<branch>-pid<ppid>)
project_root   = git rev-parse --show-toplevel         (or current working dir if no repo)
git_common_dir = git rev-parse --git-common-dir         (used to detect worktree)
is_worktree    = (git_common_dir != ".git" AND git_common_dir doesn't end with "/.git")
parent_repo    = if is_worktree, the main repo directory (derived from git_common_dir)
```

**Worktree detection matters.** If `is_worktree == true`, the resume file MUST instruct the next window to open Claude Code at the **worktree path**, not the parent repo. The "EXPECTED CWD" line in the resume goes to `project_root` (the worktree), not the parent.

If `project_root` resolves to `~/.claude`, write the resume file to `~/.claude/.qclose_resume_<sessid6>.md` instead — per the global CLAUDE.md "Not for this directory" rule, `~/.claude` is not a project and shouldn't get a `.scratch/`.

### Step 2 — Run hermes-learn

Invoke the existing hermes-learn skill via the Skill tool. Capture its output verbatim.

Outcomes:
- Wrote a `hermes-auto-<slug>` skill -> record path + 1-line description for the resume prompt.
- No skill captured (the expected case most of the time) -> record honestly.
- Crashed -> record `hermes-learn failed: <reason>` and continue. Never block `/qClose` on hermes-learn failure.

### Step 3 — Discover session state (all read-only)

- **Plans in flight**: `Glob ~/.claude/plans/*.md` modified in the last 24h. For each, read the first H1 line; list as `<path> — <H1>`.
- **TODO files**: `Glob <project>/{TODO.md,todo.md,tot.md,TODOS.md}`. For each file, find entries tagged `[w-<window_code>]` (this window's own entries only). For each matching entry, update its `hb:` field to `hb_ts` in the source file AND in the resume prompt. Per CLAUDE.md liveness protocol: do NOT touch entries owned by other windows.
- **AGENTS.md chain**: walk from `project_root` down to the deepest path Claude touched this session. List every AGENTS.md on the route.
- **Recently modified files**: `git ls-files -m -o --exclude-standard` for staged/untracked + `git log --since="24 hours ago" --name-only --pretty=format:` for last-day commits. Dedupe, cap at 20.
- **Worktrees**: `git worktree list`. ALWAYS include in resume prompt (not just when more than one), because the next window needs to see the full layout to know if it's about to open in the wrong place.
- **Background processes**: any background bash jobs (`run_in_background: true`) you started this session that haven't been reported completed. Also any process the user explicitly told you to "watch" or "keep running". If none, omit the section.

### Step 4 — Generate the resume prompt (UNIQUE FILENAME + STRICT PRE-FLIGHT)

**Filename rule (changed):**

| Case | Path |
|---|---|
| Normal project | `<project_root>/.scratch/qclose_resume_<sessid6>.md` |
| `project_root == ~/.claude` | `~/.claude/.qclose_resume_<sessid6>.md` |

The `<sessid6>` suffix makes the filename per-session unique, so two concurrent windows do NOT overwrite each other. Create `.scratch/` if missing — it's already gitignored.

Use this template VERBATIM, filling each placeholder with values from steps 1–3:

```markdown
---
qclose_version: 2
session_id: <full session_id, not truncated>
window_code: <window_code>
pid: <pid>
host: <host>
start_ts: <process start ts>
closed_at: <hb_ts>
project_root: <abs path>
expected_cwd: <abs path — same as project_root, or the worktree path if is_worktree>
branch: <branch>
head_commit: <short_hash>
is_worktree: <true|false>
parent_repo: <only if is_worktree, abs path>
---

# RESUME ACTION REQUIRED — read this first

> Paste this entire file into a fresh Claude Code window.
> Opening Claude in the EXPECTED CWD below is the IDEAL path. If the
> window happens to be in another directory, STEP 0 below will
> automatically switch to abs-path + `git -C` mode and continue —
> the resume file is designed for cross-tree continuation, not for
> blocking. Do NOT ask the user to reopen Claude; just adapt.

## STEP 0 — verify environment (mandatory, do NOT skip)

- **EXPECTED CWD**: `<expected_cwd>`
- **EXPECTED BRANCH**: `<branch>`
- **EXPECTED HEAD**: `<short_hash>` — `<commit subject>`
- **SESSION OF ORIGIN**: `<session_id>` (host `<host>`, pid `<pid>`)
- **IS WORKTREE**: `<true|false>`
- **PARENT REPO** (only if worktree): `<parent_repo>`

Run these three checks BEFORE anything else:

```powershell
# 1. CWD check — WARN + adapt, do NOT stop
# The resume file is designed for cross-tree continuation. If the
# current shell is NOT in the expected_cwd, we switch to abs-path +
# git -C "<expected_cwd>" mode for the rest of the session. Stopping
# and asking the user to reopen Claude defeats the whole point of
# qClose, which exists to enable continuation.
$expected = "<expected_cwd>"
$cwdMismatch = ((Get-Location).Path -ne $expected)
if ($cwdMismatch) {
  Write-Warning @"
CWD mismatch — adapting, NOT stopping.
  current : $((Get-Location).Path)
  expected: $expected

Continuing from this window. Operating rules from here on:
- File edits use ABSOLUTE paths inside $expected.
- Git commands target the expected tree via:  git -C "$expected" <...>
- Worktree-cleanup / merge / INDEX-update steps that legitimately
  live in the PARENT repo (when expected is a worktree) are run
  from the parent's path with its own git -C.

Do NOT ask the user "should I continue here or reopen elsewhere?" —
the answer is always "continue here". That's the qClose contract.
"@
}
# 2. Branch check — use git -C against the expected tree, NOT $PWD,
# so the check is meaningful even when CWD mismatched above.
$branch = (git -C "$expected" rev-parse --abbrev-ref HEAD).Trim()
if ($branch -ne "<branch>") {
  Write-Error @"
WRONG BRANCH at $expected. Expected <branch>, got $branch.

This is a HARD STOP: the expected tree no longer holds the branch the
qClose was written for. Another window or a human likely switched the
worktree's HEAD. Surface this to the user and ask which branch the
session should resume on before doing anything else.
"@
}
# 3. HEAD check (warn if drifted, do not stop — another window may have committed)
$head = (git -C "$expected" rev-parse --short HEAD).Trim()
if ($head -ne "<short_hash>") {
  Write-Warning "HEAD drifted at ${expected}: expected <short_hash>, got $head. Concurrent window may have committed."
}
```

Failure semantics:

- **Check 1 (CWD)** is a soft warn → adapt to abs-paths + `git -C`. Continue.
- **Check 2 (branch)** is a HARD stop → the expected tree no longer holds the expected branch; surface to user and wait for instruction.
- **Check 3 (HEAD)** is a soft warn → another window committed; keep going.

The user does NOT want a yes/no prompt for any of the soft checks. The qClose hand-off exists precisely to make continuation frictionless.

## STEP 0b — project orientation (read FIRST, then continue)

Before resuming the actual work, briefly orient yourself in this project — the same files /qRem would have you read at session start, but interpreted through the qClose lens (worktree-aware, window-aware). These files give you the project's conventions and the cross-session state; they are CONTEXT, not the task. Do NOT let them overshadow the "What this window was doing" section below — that section is the source of truth for what this resumed session must continue.

Read whichever of these exist at `<expected_cwd>`:

- `INDEX.md`  — project overview / structure (treat as static reference)
- `STARTUP.md`  — boot ritual / environment setup, if any
- `TODO.md`, `tot.md`, `TODOS.md`  — cross-session task lists
- `AGENTS.md`  — binding work contract for this subtree; walk the chain down to any path you intend to edit and read every AGENTS.md on the route, per global CLAUDE.md "AGENTS.md handling"
- `CLAUDE.md`  — Claude-specific additive rules at root (the global `~/.claude/CLAUDE.md` is always already loaded; don't re-read it)

**qClose-lens reading rules** — apply these while skimming the above:

- **TODO entries are window-owned.** Per CLAUDE.md "Shared TODO files — per-window entries only", each TODO line carries a `[w-<code>]` tag plus `pid:`/`host:`/`start:`/`hb:` for liveness. Entries owned by OTHER windows are NOT yours to take over unless the live process is dead AND on this host (see "Liveness check + takeover protocol"). On resume, refresh your own `[w-<window_code>]` entries' `hb:` to the current time before doing any other work.
- **Worktree awareness.** If `is_worktree: true` in the frontmatter above, you are in a feature worktree. INDEX.md / STARTUP.md describe the parent repo and may not match your branch state. Trust the "What this window was doing" section and the recent-commits / modified-files lists below for THIS branch's truth.
- **AGENTS.md is binding for your edits.** Read the chain from root down to every path you plan to touch. If a parent AGENTS.md indexes a child you intend to edit under, follow the index. The closest doc wins for local rules; no child may weaken a parent rule or the global CLAUDE.md.
- **Convergence priority.** If orientation files and the qClose hand-off section conflict (e.g. TODO.md hints at different priorities than the "What this window was doing" synthesis), THIS window's hand-off wins — that's the explicit reason a session-handoff exists.

If a listed file doesn't exist, note it once mentally and move on. Do NOT create them; that's not part of resume.

## What this window was doing

<1-2 paragraph synthesis of the session's intent and outcomes — the WHY,
the SO WHAT, and the open question, not a tool-call log. If you can't honestly
write this from memory of the session, say "session intent not captured" and
list the user's most recent 3 prompts verbatim as a fallback.>

## Where we stand

- **Working tree**: clean | dirty (<N> tracked modified, <M> untracked)
- **Upstream**: pushed to `<remote>/<branch>` | local-only | no upstream configured
- **Worktrees on this repo** (full layout):
  - `<path>` @ `<branch>`
  - (every entry from `git worktree list`)

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

- <wrote `hermes-auto-<slug>` -> `~/.claude/skills/hermes-auto-<slug>/SKILL.md`; description: ...>
- (or "no skill captured this session")

## How to identify this file later

If a future window needs to confirm WHICH /qClose wrote this file:
- check `~/.claude/.qclose_index.jsonl` for a line with `session_id: <session_id>`
- the line's `resume_path` field will match this file's path

Do NOT rely on the closer's conversational memory — that's gone after /clear.

---
Generated by /qClose at <hb_ts>. Window: `<window_code>` host:`<host>` pid:`<pid>` session:`<session_id>`.
```

### Step 5 — Append to the durable index (NEW)

Append ONE line to `~/.claude/.qclose_index.jsonl`:

```json
{"ts":"<hb_ts>","session_id":"<session_id>","window_code":"<window_code>","host":"<host>","pid":<pid>,"project_root":"<abs path>","expected_cwd":"<abs path>","branch":"<branch>","head_commit":"<short_hash>","is_worktree":<true|false>,"resume_path":"<abs path of resume md>"}
```

This is the perzistens link the closer's conversational memory cannot lose. Any other window can grep this file to answer "did I write this resume? when? where?".

Never rewrite or truncate the index — append-only. Rotation, if ever needed, is a separate user-driven task.

### Step 6 — Commit + push

If `git status --porcelain` returns nothing: skip; print `commit: no pending changes`.

Otherwise:

- **Stage explicitly** — list the files to add, never `git add -A` / `git add .`. The new `qclose_resume_<sessid6>.md` must NOT be staged (gitignored under `.scratch/`, intentional).
- Commit with this message format:
  ```
  qClose session-handoff <YYYY-MM-DD>

  Resume prompt at .scratch/qclose_resume_<sessid6>.md (gitignored).
  <one short line — what was actually done this session, mined from the
  "What this window was doing" synthesis>.
  ```
- **Do NOT push automatically.** After the commit lands, ask the user explicitly: `Push commit <short_hash> to <remote>/<branch>? (yes/no)`. Default to no-push if the user doesn't answer affirmatively. This is hard-coded — even projects with a standing "push" memory authorization for explicit `push` commands do NOT auto-push on `/qClose`.
- If a pre-commit hook fails: **do not bypass with `--no-verify`** (global project rule). Surface the failure, leave the resume prompt written, exit cleanly. The user resolves the hook and re-runs `/qClose`.

### Step 7 — Print the closeout (NEW FORMAT — copy-paste-shaped)

Final block to the user, in this EXACT shape (use plain ASCII boxes, no decorative unicode):

```
qClose done.
- commit: <short hash>  (or "no pending changes")
- push:   awaiting your confirmation: push <short_hash> to <remote>/<branch>?  (or "pushed", "user said no", "skipped — <reason>")
- learn:  wrote hermes-auto-<slug>  (or "no skill captured")
- index:  appended ~/.claude/.qclose_index.jsonl (session <sessid6>)

**Open Claude Code in this exact directory first:**
**<expected_cwd>**

====================================================================
COPY & PASTE IN THE NEW SESSION:
====================================================================


*****************************************************************
Read and identify with this file: <absolute resume_path>
*****************************************************************


====================================================================
```

Format rules — get them exactly right, the user inspects this block:

- The "Open Claude Code in this exact directory first: <path>" line is **META-instruction** and lives OUTSIDE the box. It tells the user where to open Claude — it's NOT part of what gets pasted.
- The outer ASCII box (`===` borders) brackets the whole paste section.
- Inside that, the actual paste-line `Read and identify with this file: <absolute resume_path>` is wrapped between two `*****` banner rows so it stands out visually as the literal copy-target. Two blank lines sit above the top `*****` row and two below the bottom `*****` row.
- Do NOT add an intermediate "Then paste this prompt:" line — it's redundant. The box header "COPY & PASTE IN THE NEW SESSION:" is the only label needed.
- Use `**...**` markdown bold on the meta-instruction lines (path + label) so they stand out. Use plain ASCII `=` and `*` for borders (per CLAUDE.md "no decorative unicode" rule).

## Edge-case matrix

| Situation | Behaviour |
|---|---|
| Not in a git repo | Skip git steps; still generate resume prompt with `branch: (no-repo)`, `is_worktree: false` |
| `~/.claude/skills/hermes-learn/` missing | Skip Step 2 silently; resume says `hermes-learn skill not installed, skipped` |
| `.scratch/` does not exist | `mkdir -p`; it's gitignored at `.gitignore:40` |
| Multiple worktrees, current is a worktree | `expected_cwd` is the worktree path, NOT the parent repo. Resume STEP 0 enforces it. |
| Multiple worktrees on the same branch | Warn user per CLAUDE.md "Dual-window safety", still generate resume prompt, do NOT commit on shared tree without explicit ok |
| Push fails (network, auth, no upstream) | Commit stays local; closeout shows `push: failed — <reason>` |
| Push always requires explicit user yes | The default is ASK, never auto-push. Applies to every repo without exception. |
| `project_root == ~/.claude` | Write to `~/.claude/.qclose_resume_<sessid6>.md` (not `~/.claude/.scratch/`) per CLAUDE.md "Not for this directory" |
| `~/.claude/.qclose_index.jsonl` doesn't exist | Create it (empty), then append. Don't ask, don't warn — it's expected on first-ever /qClose. |
| Index says another window closed same branch <30 min ago | Step 0 surfaces, default-stops on no-response |
| User has no TODO files at all | Omit the "Open TODO entries" section entirely |
| No plan files in `~/.claude/plans/` touched in 24h | Omit the "Open plan files" section |
| `$CLAUDE_SESSION_ID` unavailable | Fall back to `pid` + `start_ts` hashed; still produces a 6-hex sessid6 |
| Two concurrent /qClose in same window (impossible but defensive) | Filename collision is fine — sessid6 is per-session; same session re-running just overwrites its own file |

## What `/qClose` deliberately does NOT do

- Does NOT enumerate every file Claude read — only the modified ones. Reading is not state.
- Does NOT touch TODO entries owned by other `[w-...]` windows. Heartbeat refresh is window-local.
- Does NOT close any background processes the user wanted to keep running. It just records them.
- Does NOT delete the resume markdown when done — the file is the artifact; the user decides when to clean it up. (`.scratch/` cleanup is the user's concern.)
- Does NOT inject anything into the next session's prompt automatically. The user pastes manually — that's the contract. No hidden state survives a `/clear`.
- Does NOT auto-push, ever, regardless of project memory. The push prompt is unconditional.
- Does NOT rotate or truncate `~/.claude/.qclose_index.jsonl`. Append-only.
- Does NOT trust conversational memory to answer "did I write this resume file?". The `.qclose_index.jsonl` is the only source of truth for that lookup.
