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
- statusline progress-bar glyphs `U+2588 U+2591` and pace arrows `U+25B2 U+25BC` in `~/.claude/scripts/statusline_with_weekly.js` — that's a UI surface, the chars carry visual state with no plain-text substitute.
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

Instead, every TODO entry you create must be scoped to a **window identifier** so multiple windows can share one file without confusion:

- Pick a short window code at the top of the session and reuse it for every entry that session writes. Examples: `[w-main]`, `[w-feat-auth]`, `[w-2026-06-08-a]`. The codes should be branch-derived or session-derived, not human-readable invective.
- Format each entry as: `- [w-CODE] YYYY-MM-DD — task description`. Always include the date the entry was added.
- When closing or updating an entry, only touch entries whose `[w-CODE]` matches the current session. Don't delete or rewrite another window's entries.
- If you already wrote bare "this window" notes into a shared TODO file in this session, rewrite them in the `[w-CODE] YYYY-MM-DD —` form before moving on.

This rule applies to any shared list file the project uses for cross-session task tracking — not just `TODO.md`. If unsure whether a file is shared, treat it as shared.

## Don't create directories outside the project root, and don't sibling-copy the project folder

When working in a project:

- Don't create new directories outside the project root. Scratch files, experiments, backups, and intermediate artifacts all belong inside the project (typically under a gitignored `.scratch/`, `tmp/`, or similar) — not in the parent directory, not in `~`, not in `/tmp`.
- Don't make sibling copies of the project folder with a suffix or prefix. If the project is `myproject`, do not create `myproject_s`, `myproject_2`, `myproject_backup`, `myproject-old`, `myproject.bak`, `copy_of_myproject`, or any similar near-duplicate next to it. These break tooling that walks the parent directory, confuse the user about which copy is canonical, and accumulate stale state.
- If you need an isolated copy for an experiment, use a **git branch** or **git worktree** inside the project (or under a designated worktree root), not a directory copy. If you need a backup before a destructive operation, commit to a branch first.
- If the user explicitly asks for a sibling copy, confirm the exact path and reason before creating it.

## State files (gitignored, don't commit)

- `~/.claude/.hermes_curator_queue.json`, `.hermes_curator_state.json` — curator queue.
- `~/.claude/.qrev_auto_state.json` — auto-qRev counters.
- `~/.claude/.statusline_baselines.json` — per-session context-bar baselines.
- `~/.claude/.ecc-session-bridge/` — session metrics for the statusline.
- `D:\projects\super_claude\hermes-agent\claude_code_integration\ruvector.db` and the top-level `ruvector.db` — embeddings / skill state.

All of the above are listed in `.gitignore` and must stay there.
