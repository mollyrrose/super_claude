# CLAUDE.md — super_claude project

This file extends the global `~/.claude/CLAUDE.md` with rules specific to this repo.

## Project shape

`super_claude` is the personal Claude Code setup: hook scripts in `~/.claude/scripts/`, the curator and skill-lifecycle Python modules under `hermes-agent/claude_code_integration/`, and a `claude_skills_backup/` of ~165 skills that get installed into `~/.claude/skills/`. See `README.md` for the full feature catalog.

## No decorative unicode

This rule mirrors the global rule and is restated here so it's visible inside the project too.

Don't put characters like the rightward arrow (U+2192), checkmark (U+2713/U+2714), cross (U+2717/U+2718), bullets (U+2022/U+25CF/U+25E6), stars (U+2605/U+2606) or pointing triangles (U+25B6/U+25BC) into source files, markdown, comments, commit messages, or PR bodies.

The same rule covers **emoji-style** decorative glyphs and any visually similar character. Forbidden emoji (non-exhaustive — the principle covers anything in the same family):
- check / OK: `✅` (U+2705), `✔️` (U+2714 U+FE0F), `☑` (U+2611)
- fail / wrong: `❌` (U+274C), `❎` (U+274E)
- warning / alert: `⚠️` (U+26A0), `⛔` (U+26D4), `🚨` (U+1F6A8)
- status dots: `🟢🔴🟡🔵` (U+1F7E2..U+1F7E6) and the larger circle family
- thumbs / pointing hands: `👍👎` (U+1F44D/U+1F44E), `👉👈👆👇`
- decoration: `✨` (U+2728), `⭐🌟`, `🔥` (U+1F525), `🚀` (U+1F680), `🎉🎊`, `💯`
- notes / ideas: `💡` (U+1F4A1), `📝` (U+1F4DD), `📌` (U+1F4CC), `📚`, `📋`

Rule of thumb: if a character is outside Basic Latin / Latin-1 and isn't on the functional allowlist below, treat it as decoration and drop it.

Reasons:
- Windows cp1252 console crashes on emit (`UnicodeEncodeError`); test smoke scripts have already hit this.
- ripgrep / grep with default ASCII expectations miss them.
- They render differently across terminals, editors, and chat tools.
- Emoji especially blow up log files, JSONL session captures, and any tool that assumes single-byte text.
- They add no information vs plain ASCII (`[ok]`, `[fail]`, `[warn]`, `note:` carry the same meaning and grep cleanly).

ASCII equivalents:
- arrow: `->`
- pass: `[ok]` or `(ok)` or just write "pass"
- fail: `[fail]` or `(bad)`
- bullets: `-` or `*`
- note: `[i]` or `note:`

Exceptions that ARE allowed because they're functional, not decorative:
- statusline progress-bar glyphs `U+2588 U+2591` and pace arrows `U+25B2 U+25BC` in `scripts/statusline_with_weekly.js` (installed to `~/.claude/scripts/statusline_with_weekly.js`) — that's a UI surface, the chars carry visual state with no plain-text substitute.
- em-dash `U+2014` in prose, because plain `--` collides with CLI flag syntax.

When in doubt: if removing the character wouldn't reduce the meaning a plain-text reader picks up, the character is decoration and shouldn't be there.

## Hooks (don't break them)

`~/.claude/settings.json` chains these hook scripts:

- `PostToolUse(Write|Edit)`: `semgrep_postedit_hook.py` then `qrev_edit_counter.py`
- `UserPromptSubmit`: `curator_prompt_hook.py`, `smart_router_prompt_hook.py`, `context_budget_gate.py`, `qrev_auto_inject.py`
- `Stop`: `curator_stop_hook.py`
- `PreCompact`: `curator_precompact_hook.py`
- `SessionEnd`: `rev_learn_sessionend.py` (async)

Changes to these scripts should:
1. Always preserve the `silent no-op on missing / malformed stdin` pattern (see `semgrep_postedit_hook.py:42-50`). A hook that crashes on a bad payload would block every Write/Edit.
2. Exit 0 by default; reserve non-zero for genuinely blocking conditions.
3. Be tested with the matching `_smoketest.py` next door before wiring.

## Shared TODO files — per-window entries only

If a project has a shared `TODO.md` / `todo.md` / `tot.md`, multiple Claude Code windows (different branches, different worktrees, different sessions) may all read and write the same file. **Don't** write notes like "NOT this window (other branch, other window)" or "ignore — different session" into shared TODO files. Those notes are meaningless to the other window reading the same file, and they collide.

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

### Entry format — pid + host + start + heartbeat

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

### Liveness check + takeover protocol

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

   If `$alive` (or the Unix equivalent) → owner is still running. Do not take over. You may still add a *new* entry with your own `[w-...]` if you have related work, but do not touch theirs.

3. **Heartbeat fallback.** If the PID lookup is unavailable (no permission, exotic harness, no shell access), use the heartbeat: treat the entry as alive if `hb:<ISO>` is within the last 6 hours, dead otherwise. Document a different threshold inline if you must deviate, so future sessions can audit the call.

4. **Takeover rule.** Only after step 2 says dead, or step 3 says heartbeat is stale beyond 6 hours, may you:
   - Rewrite the `[w-...]` tag to your own window code.
   - Overwrite `pid:`, `host:`, `start:`, and `hb:` with your own values.
   - Append a `// taken over from [w-prev-code] on YYYY-MM-DD` audit note inline so the trail survives.

5. **Heartbeat update.** Every time you touch your own entry — reading it for status, adding a sub-bullet, marking progress — refresh `hb:` to the current ISO timestamp before saving. Stale heartbeats are how takeovers happen, so keeping yours fresh is the only thing preserving your claim.

This protocol applies to any shared list file the project uses, not just `TODO.md`. If unsure whether a file is shared, treat it as shared.

This rule applies to any shared list file the project uses for cross-session task tracking — not just `TODO.md`. If unsure whether a file is shared, treat it as shared.

## Don't create directories outside the project root, and don't sibling-copy the project folder

When working in a project:

- Don't create new directories outside the project root. Scratch files, experiments, backups, and intermediate artifacts all belong inside the project (typically under a gitignored `.scratch/`, `tmp/`, or similar) — not in the parent directory, not in `~`, not in `/tmp`.
- Don't make sibling copies of the project folder with a suffix or prefix. If the project is `myproject`, do not create `myproject_s`, `myproject_2`, `myproject_backup`, `myproject-old`, `myproject.bak`, `copy_of_myproject`, or any similar near-duplicate next to it. These break tooling that walks the parent directory, confuse the user about which copy is canonical, and accumulate stale state.
- If you need an isolated copy for an experiment, use a **git branch** or **git worktree** inside the project (or under a designated worktree root), not a directory copy. If you need a backup before a destructive operation, commit to a branch first.
- If the user explicitly asks for a sibling copy, confirm the exact path and reason before creating it.

**Allowed:** `.worktrees/<branch>/` inside the project root. This is the project's canonical location for `git worktree add` checkouts when the user runs two or more Claude windows on different branches simultaneously. `.worktrees/` is in `.gitignore`. The rule above still holds for everything outside `.worktrees/` — sibling-suffixed copies of the project folder (`super_claude_2`, `super_claude.bak`, etc.) remain forbidden, and directories outside the project root remain forbidden.

The canonical dual-window workflow is:

```powershell
# from the main tree
git worktree add .worktrees/feat-x -b feat-x          # new branch
git worktree add .worktrees/feat-x feat-x             # existing branch

# in a fresh Claude window
cd D:\projects\super_claude\.worktrees\feat-x
claude

# cleanup when done
git worktree remove .worktrees/feat-x
git branch -d feat-x
```

Hooks and per-session state files in `~/.claude/` (curator queue, qrev counters, statusline baselines, ecc-session-bridge) are keyed by `session_id`, not by working-tree path. Two concurrent worktrees do not race on those. Each worktree gets its own `.claude/settings.local.json` (fresh permission prompts the first time — that's expected, not a bug).

## State files (gitignored, don't commit)

- `~/.claude/.hermes_curator_queue.json`, `.hermes_curator_state.json` — curator queue.
- `~/.claude/.qrev_auto_state.json` — auto-qRev counters.
- `~/.claude/.statusline_baselines.json` — per-session context-bar baselines.
- `~/.claude/.ecc-session-bridge/` — session metrics for the statusline.
- `D:\projects\super_claude\hermes-agent\claude_code_integration\ruvector.db` and the top-level `ruvector.db` — embeddings / skill state.

All of the above are listed in `.gitignore` and must stay there.
