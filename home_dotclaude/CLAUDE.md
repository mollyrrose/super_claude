# CLAUDE.md

Global user instructions for Claude Code sessions.

# Model Config
model: claude-opus-4-7
thinking: enabled

## Working style

- Read relevant files before editing. Don't guess at code you haven't seen.
- For non-trivial work, sketch a short plan before coding.
- Make minimal, precise edits. Don't refactor or restructure code beyond what the task requires.
- Verify after each step (run tests, type-check, or re-read the diff).
- Don't stop at the first sign of "done" — confirm the task is actually complete.

## When showing edits

- State the file you're editing and the reason in one short sentence.
- Keep the diff scoped to the change at hand.

## User input visibility — ALWAYS announce when waiting

When a reply ends with a question, a choice, or any other prompt that
expects me to type something back, the LAST line of the message MUST be
the ASCII attention banner below — exactly this glyph and exactly this
spelling — so I notice the terminal is idle waiting for me instead of
just scrolling past:

```
*********************************
*    USER INPUT REQUIRED        *
*********************************
```

Applies to:
- Direct questions ("Mit szeretnél?", "Yes/No?", "Which option?")
- AskUserQuestion tool calls (the banner goes in the assistant text
  output that accompanies the tool call, not into the tool's question
  field itself).
- Approvals, gate facts, "OK?" closings.
- "Tell me when you're done" handoffs where you genuinely need me to act.

Does NOT apply to:
- Background-task progress notes where you'll keep working on receipt.
- Pure status updates ("done.", "pushed.", "no changes left.").
- End-of-turn summaries that don't await anything from me.

When in doubt: if the terminal would sit idle until I type something,
the banner is required. False positives are cheap; missing one means a
window sits unused for minutes.

## Pushback expected

- Ask clarifying questions when a request is ambiguous or under-specified.
- Push back on weak assumptions, missing data, or blind spots — don't just agree.
- Flag risks (security, data loss, irreversible operations) before acting on them.

## Project directory boundaries and dual-window safety

These rules apply to **every** project, regardless of whether a project-level `CLAUDE.md` restates them.

### Don't create directories outside the project root, and don't sibling-copy the project folder

When working in a project:

- Don't create new directories outside the project root. Scratch files, experiments, backups, and intermediate artifacts all belong inside the project (typically under a gitignored `.scratch/`, `tmp/`, or similar) — not in the parent directory, not in `~`, not in `/tmp`.
- Don't make sibling copies of the project folder with a suffix or prefix. If the project is `myproject`, do not create `myproject_s`, `myproject_2`, `myproject_backup`, `myproject-old`, `myproject.bak`, `copy_of_myproject`, or any similar near-duplicate next to it. These break tooling that walks the parent directory, confuse the user about which copy is canonical, and accumulate stale state.
- If you need an isolated copy for an experiment, use a **git branch** or **git worktree** inside the project (see next section), not a directory copy. If you need a backup before a destructive operation, commit to a branch first.
- If the user explicitly asks for a sibling copy, confirm the exact path and reason before creating it.

### Dual-window workflow: `.worktrees/<branch>/` inside the project root

When the user runs two or more Claude windows on the same repo at the same time, the additional windows MUST be in separate **git worktrees** — not in the same working tree. Two windows on the same working tree silently collide on each other's untracked files, half-staged changes, and HEAD movement (commits from one window fast-forward the other's HEAD; untracked files from the other window look like "yours" in `git status`). Surface this to the user the moment you detect it and propose moving one window into a worktree.

The canonical location for additional worktrees is `.worktrees/<branch>/` **inside the project root**. Add `.worktrees/` to the project's `.gitignore` if it isn't already.

```powershell
# from the main tree
git worktree add .worktrees/feat-x -b feat-x          # new branch
git worktree add .worktrees/feat-x feat-x             # existing branch

# in a fresh Claude window
cd <project-root>\.worktrees\feat-x
claude

# cleanup when done
git worktree remove .worktrees/feat-x
git branch -d feat-x
```

When you start a Claude session, if the project might have other concurrent windows, run `git worktree list` once to see the layout. If another window is on the same working tree on the same branch as you, warn the user before doing commits, pushes, or large rewrites.

Hooks and per-session state files in `~/.claude/` (curator queue, qrev counters, statusline baselines, ecc-session-bridge) are keyed by `session_id`, not by working-tree path. Two concurrent worktrees do not race on those. Each worktree gets its own `.claude/settings.local.json` (fresh permission prompts the first time — that's expected, not a bug).

### Shared TODO files — per-window entries only

If a project has a shared `TODO.md` / `todo.md` / `tot.md` (or any other cross-session task list), multiple Claude Code windows (different branches, different worktrees, different sessions) may all read and write the same file. **Don't** write notes like "NOT this window (other branch, other window)" or "ignore — different session" into shared TODO files. Those notes are meaningless to the other window reading the same file, and they collide.

Instead, every TODO entry you create must be scoped to a **window identifier** that is unique to *this specific window*, not just to the branch. Two Claude Code windows can be open on the same branch at the same time, so the branch name alone is not enough — the identifier has to disambiguate window-from-window.

How to construct the window identifier (pick the first option that's available):

1. **Session ID**: if `$CLAUDE_SESSION_ID` (or equivalent harness-provided session token) is set, use its first 6 hex chars. Format: `[w-<branch>-<sessid6>]`, e.g. `[w-main-a1b2c3]`.
2. **PPID-derived**: if no session ID is exposed, take the parent terminal PID and use the last 4–6 digits. Format: `[w-<branch>-pid<ppid>]`, e.g. `[w-feat-auth-pid41822]`.
3. **Timestamp + random**: if neither is available, generate a short tag from session start time plus 3 random hex chars. Format: `[w-<branch>-<YYMMDD-HHMM>-<rand3>]`, e.g. `[w-main-260608-1742-f9c]`.

Whichever you pick, fix it at the start of the session and reuse the **exact same identifier** for every entry you write that session — don't regenerate it per entry, and don't change format mid-session.

Then:

- When closing or updating an entry, only touch entries whose `[w-...]` matches the current window's identifier. Don't delete or rewrite another window's entries, even if they're on the same branch.
- If you already wrote bare "this window" notes into a shared TODO file in this session, rewrite them in the structured form below before moving on.
- Record the chosen window identifier somewhere reproducible (e.g. at the top of the TODO file as a hidden HTML comment `<!-- window: w-main-a1b2c3 started 2026-06-08 -->`) so a returning session can recover it instead of inventing a new one.

#### Entry format — pid + host + start + heartbeat

The window code alone tells you *which* window wrote an entry, but not whether that window is still alive. A returning window needs to decide: can I take this task over, or is the original author still working on it? Bare `[w-...]` isn't enough — PIDs get reused, sessions die without cleanup, and the same window code could refer to a process that exited an hour ago.

Each entry therefore carries a structured ownership tuple:

```
- [w-<code>] 2026-06-08T17:42 pid:41822 host:DESKTOP-SEAL start:2026-06-08T17:40 hb:2026-06-08T18:05 — task description
```

Fields:
- `[w-<code>]` — the window identifier from the priority list above.
- `<ISO timestamp>` immediately after — the moment the entry was *created* (never changes).
- `pid:<n>` — the Claude Code harness PID, or its parent terminal PID if the harness PID is not exposed.
- `host:<name>` — the machine the window is running on (`$env:COMPUTERNAME` on Windows, `hostname` on Unix). Disambiguates remote sessions.
- `start:<ISO>` — the **process start time** of the PID. Defends against PID reuse: a recycled PID always has a different start time. On Windows use `(Get-Process -Id N).StartTime.ToUniversalTime().ToString("o")`.
- `hb:<ISO>` — the last *heartbeat*. MUST refresh to the current time every time you touch your own entry. A returning window without process-table access falls back to heartbeat staleness.

How to gather the values at session start (record once, reuse for every entry):

- **Windows PowerShell**:
  ```powershell
  $pid_self  = $PID
  $host_self = $env:COMPUTERNAME
  $start_self = (Get-Process -Id $PID).StartTime.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  ```
- **Unix shell** (bash/zsh):
  ```bash
  PID_SELF=$$
  HOST_SELF=$(hostname)
  START_SELF=$(ps -o lstart= -p $$ | xargs -I{} date -u -d "{}" +%Y-%m-%dT%H:%M:%SZ)
  ```

#### Liveness check + takeover protocol

When you read an entry belonging to a different `[w-...]` than your own, decide takeover-eligibility in this order:

1. **Cross-host check.** If `host:<name>` is not this machine's name, the entry is owned by a remote session. You MUST NOT take it over — you can't see the remote process and can't verify liveness. You may append a *new* entry with your own `[w-...]` referencing the remote task, but never rewrite or delete the remote entry. Skip the rest of the protocol.

2. **PID + start-time check.**

   **Windows**:
   ```powershell
   $p = Get-Process -Id 41822 -ErrorAction SilentlyContinue
   $alive = $p -and $p.StartTime.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm") -eq "2026-06-08T17:40"
   ```
   (Compare to the minute, not the second — Windows StartTime has sub-second precision the ISO string drops.)

   **Unix**:
   ```bash
   ps -o lstart= -p 41822 2>/dev/null
   ```
   Compare the printed start time against `start:<ISO>` (both rounded to the minute). Match = alive; missing PID or mismatched start = dead.

   If `$alive` (or the Unix equivalent) is true, the owner is still running. Do not take over. You may still add a *new* entry with your own `[w-...]` if you have related work, but do not touch theirs.

3. **Heartbeat fallback.** If the PID lookup is unavailable (no permission, exotic harness, no shell access), use the heartbeat: treat the entry as alive if `hb:<ISO>` is within the last 6 hours, dead otherwise. Document a different threshold inline if you must deviate, so future sessions can audit the call.

4. **Takeover rule.** Only after step 2 says dead, or step 3 says heartbeat is stale beyond 6 hours, may you:
   - Rewrite the `[w-...]` tag to your own window code.
   - Overwrite `pid:`, `host:`, `start:`, and `hb:` with your own values.
   - Append a `// taken over from [w-prev-code] on YYYY-MM-DD` audit note inline so the trail survives.

5. **Heartbeat update.** Every time you touch your own entry — reading it for status, adding a sub-bullet, marking progress — refresh `hb:` to the current ISO timestamp before saving. Stale heartbeats are how takeovers happen, so keeping yours fresh is the only thing preserving your claim.

This protocol applies to any shared list file the project uses for cross-session task tracking, not just `TODO.md`. If unsure whether a file is shared, treat it as shared.

## AGENTS.md handling (DOX framework)

If a project contains one or more `AGENTS.md` files, treat them as **binding work contracts** for their subtree, alongside any `CLAUDE.md`. Claude Code does not auto-load `AGENTS.md`, so you must walk and read them manually. Adapted from the DOX framework (https://github.com/agent0ai/dox).

### Before editing

1. Read the root `AGENTS.md` if it exists.
2. For each file or folder you expect to touch, walk from the repository root down to the target path.
3. Read every `AGENTS.md` found along that route. If a parent `AGENTS.md` indexes a child `AGENTS.md` whose scope contains the target, follow the index and read the child too.
4. Use the **nearest** `AGENTS.md` as the local contract; parent docs supply broader rules.
5. On conflict, the closer doc wins for local details, but no child doc may weaken a parent rule, the global rules in this file, or a project-level `CLAUDE.md`.
6. Don't rely on memory — re-read the applicable chain in the current session before editing.

If both `CLAUDE.md` and `AGENTS.md` exist in the same scope, treat them as additive: `CLAUDE.md` is Claude-specific, `AGENTS.md` applies to any agent including Claude. On direct conflict between them, ask the user before acting.

### After editing — DOX pass

Every meaningful change requires a DOX pass before the task is done. Update the **closest owning** `AGENTS.md` when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, or quality
- creation, deletion, move, rename, or Child DOX Index contents of any `AGENTS.md`

Also update parent docs when parent-level structure or child index changes, and child docs when a parent change alters local rules. Remove stale or contradictory text immediately. Edits that don't change behavior or contracts may leave docs unchanged, but you still do the pass and report it.

### Self-learning convergence override

The "After editing" rule above applies to **user-driven edits in the current session**. Automated self-learning paths (the auto-curator, `/learn`, `/rev-learn`, qrev-auto, semgrep auto-rule discovery, and any future analogous loop) MUST NOT use the DOX pass to write durable rules into branch-tracked `AGENTS.md` files. They fragment across worktrees and contradict the convergence pattern the rest of this setup follows — every other self-learning artifact in this config (`~/.claude/.hermes_*.json`, `~/.claude/.qrev_*`, `~/.claude/skills/hermes-auto-*/`) already lives outside any working tree on purpose.

Routing for auto-learned durable rules:

1. **Skill-shaped learnings** -> `~/.claude/skills/hermes-auto-<slug>/` (existing curator path). Shared across all worktrees, never branch-tracked.
2. **Counter / state learnings** -> `~/.claude/.hermes_*.json` or `~/.claude/.qrev_*` (existing pattern). Shared across all worktrees.
3. **Rules that genuinely belong in an `AGENTS.md`** -> stage as a proposed diff and surface it to the user. Only the user-driven DOX pass writes it, and only into the **root** `AGENTS.md` on `main` (or rebased onto `main` immediately). Never silently into a feature-branch child `AGENTS.md`.

Worktree-local self-learning state (per-session counters, transient queues) may live inside the current working tree under a gitignored path (`.claude/review-log/`, `.scratch/`, etc.) — it's not branch-tracked, so it doesn't fragment.

### Creating a child AGENTS.md

Create one when a folder becomes a durable boundary with its own purpose, rules, responsibilities, workflow, materials, or quality standards. Default section order:

- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

Leave Work Guidance and Verification empty when no concrete standards or checks exist yet — don't invent them. Each parent must explain what its direct children cover and what stays owned by the parent. Closer docs are more specific and operational; parent docs hold broad rules.

### Closeout

1. Re-check changed paths against the DOX chain.
2. Update nearest owning docs and any affected parents or children.
3. Refresh every affected Child DOX Index.
4. Remove stale or contradictory text.
5. Run existing verification when relevant.
6. Briefly note any docs intentionally left unchanged and why.

## No decorative unicode in code or docs

Don't write characters like `->` rendered as arrow (U+2192), check marks (U+2713, U+2714, U+2705, U+2611, U+1F5F8, U+1F5F9), crosses or X marks (U+2715, U+2716, U+2717, U+2718, U+274C, U+274E, U+2612, U+1F5D9, U+1F5F4, U+1F5F5, U+1F5F7), info source (U+2139, U+1F6C8), bullets (U+2022, U+25CF, U+25E6), stars (U+2605, U+2606), pointing triangles (U+25B6, U+25BC) into source files, markdown, comments, commit messages, PR bodies, **shell commands, regex patterns, or any other tool input**. They render inconsistently across terminals, encodings (cp1252 on Windows blows up — see also the project codebase), and search tools, and they add zero meaning over plain ASCII.

The same rule applies to **emoji-style** decorative glyphs and any visually similar character. Forbidden emoji (non-exhaustive — the principle covers anything in the same family):
- check / OK / pipa (all colors, weights, and box variants): check mark (U+2713), heavy check (U+2714), check w/ VS-16 (U+2714 U+FE0F), white heavy check on green (U+2705), ballot box w/ check (U+2611), light check (U+1F5F8), ballot box w/ bold check (U+1F5F9)
- fail / wrong / X mark (all colors, weights, and box variants): multiplication x (U+2715), heavy multiplication x (U+2716), ballot x (U+2717), heavy ballot x (U+2718), red cross mark (U+274C), green negative squared cross (U+274E), ballot box w/ x (U+2612), cancellation x (U+1F5D9), ballot script x (U+1F5F4), ballot script x w/ box (U+1F5F5), ballot box w/ bold script x (U+1F5F7)
- info source: information source (U+2139), circled information source (U+1F6C8)
- warning / alert: warning sign `⚠️` (U+26A0), no entry `⛔` (U+26D4), police light `🚨` (U+1F6A8)
- status dots: green/red/yellow/blue circles `🟢🔴🟡🔵` (U+1F7E2..U+1F7E6), large circles `⚫⚪🟠🟣🟤` family
- thumbs / hands: thumbs up/down `👍👎` (U+1F44D/U+1F44E), pointing hands `👉👈👆👇`
- decoration: sparkles `✨` (U+2728), star `⭐🌟` (U+2B50/U+1F31F), fire `🔥` (U+1F525), rocket `🚀` (U+1F680), party `🎉🎊`, hundred `💯`
- notes / ideas: light bulb `💡` (U+1F4A1), memo `📝` (U+1F4DD), pin `📌` (U+1F4CC), books `📚`, clipboard `📋`

When in doubt about a character you're about to emit: if it's outside the Basic Latin / Latin-1 range and isn't already on the **functional** allowlist below, treat it as decoration and drop it.

Use ASCII equivalents:
- arrow: `->`
- pass / done: `[ok]` or `(ok)` or just say "pass"
- fail / wrong: `[fail]` or `(bad)`
- bullets: `-` or `*`
- info: `[i]` or `note:`

This rule does NOT apply to **functional** unicode in user-facing display — e.g. the statusline progress-bar glyphs (`U+2588 U+2591`) and the pace arrows (`U+25B2 U+25BC`) are deliberate UI, not decoration, and stay. The em-dash (`—`, U+2014) is fine in prose because plain `--` is ambiguous with CLI flag syntax. The question is "does it convey something a plain-text reader needs?" — if yes, keep; if it's just visual flair, use ASCII.

Even when filtering output that contains these glyphs (e.g. `grep` over a `node:test` reporter stream that emits check variants `✓ ✔ ✅ ☑ 🗸 🗹` (U+2713 / U+2714 / U+2705 / U+2611 / U+1F5F8 / U+1F5F9), X variants `✕ ✖ ✗ ✘ ❌ ❎ ☒ 🗙 🗴 🗵 🗷` (U+2715 / U+2716 / U+2717 / U+2718 / U+274C / U+274E / U+2612 / U+1F5D9 / U+1F5F4 / U+1F5F5 / U+1F5F7), or info-source variants `ℹ 🛈` (U+2139 / U+1F6C8)), write the filter using ASCII keywords like `fail|error|pass` — **never quote the glyph itself** in a pattern. The reporter also emits ASCII status words alongside the glyphs (`fail 0`, `pass 12`); match those.

## Not for this directory

`~/.claude` is the Claude Code config directory, not a code project. Don't run `/init` here, don't create `INDEX.md`/`STARTUP.md`/`TODO.md` here, and don't treat session JSONL files under `projects/` as source code.

## Install catalog

Skill and MCP install commands previously embedded here have been moved to `INSTALL.md`. Run them manually from a shell when needed.
