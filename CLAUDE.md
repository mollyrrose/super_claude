# CLAUDE.md — super_claude project

This file extends the global `~/.claude/CLAUDE.md` with rules specific to this repo.

## Project shape

`super_claude` is the personal Claude Code setup: hook scripts in `~/.claude/scripts/`, the curator and skill-lifecycle Python modules under `hermes-agent/claude_code_integration/`, and a `claude_skills_backup/` of ~165 skills that get installed into `~/.claude/skills/`. See `README.md` for the full feature catalog.

## No decorative unicode

This rule mirrors the global rule and is restated here so it's visible inside the project too.

Don't put characters like the rightward arrow (U+2192), check marks (U+2713/U+2714/U+2705/U+2611/U+1F5F8/U+1F5F9), crosses or X marks (U+2715/U+2716/U+2717/U+2718/U+274C/U+274E/U+2612/U+1F5D9/U+1F5F4/U+1F5F5/U+1F5F7), info source (U+2139/U+1F6C8), bullets (U+2022/U+25CF/U+25E6), stars (U+2605/U+2606) or pointing triangles (U+25B6/U+25BC) into source files, markdown, comments, commit messages, PR bodies, **shell commands, regex patterns, or any other tool input**.

The same rule covers **emoji-style** decorative glyphs and any visually similar character. Forbidden emoji (non-exhaustive — the principle covers anything in the same family):
- check / OK / pipa (all colors, weights, and box variants): U+2713, U+2714, U+2714 U+FE0F, U+2705, U+2611, U+1F5F8, U+1F5F9
- fail / wrong / X mark (all colors, weights, and box variants): U+2715, U+2716, U+2717, U+2718, U+274C, U+274E, U+2612, U+1F5D9, U+1F5F4, U+1F5F5, U+1F5F7
- info source: U+2139, U+1F6C8
- warning / alert: `⚠️` (U+26A0), `⛔` (U+26D4), `🚨` (U+1F6A8)
- status dots: `🟢🔴🟡🔵` (U+1F7E2..U+1F7E6) and the larger circle family
- thumbs / pointing hands: `👍👎` (U+1F44D/U+1F44E), `👉👈👆👇`
- decoration: `✨` (U+2728), `⭐🌟`, `🔥` (U+1F525), `🚀` (U+1F680), `🎉🎊`, `💯`
- notes / ideas: `💡` (U+1F4A1), `📝` (U+1F4DD), `📌` (U+1F4CC), `📚`, `📋`

Even when filtering output that contains these glyphs (e.g. `grep` over a `node:test` reporter stream that emits check variants `✓ ✔ ✅ ☑ 🗸 🗹` (U+2713 / U+2714 / U+2705 / U+2611 / U+1F5F8 / U+1F5F9), X variants `✕ ✖ ✗ ✘ ❌ ❎ ☒ 🗙 🗴 🗵 🗷` (U+2715 / U+2716 / U+2717 / U+2718 / U+274C / U+274E / U+2612 / U+1F5D9 / U+1F5F4 / U+1F5F5 / U+1F5F7), or info-source variants `ℹ 🛈` (U+2139 / U+1F6C8)), write the filter using ASCII keywords like `fail|error|pass` — **never quote the glyph itself** in a pattern. The reporter also emits ASCII status words alongside the glyphs (`fail 0`, `pass 12`); match those.

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

## Multi-window safety and project boundaries

The generic rules — `.worktrees/<branch>/` dual-window workflow, no sibling-copies of the project folder, no directories outside the project root, and the per-window TODO ownership / liveness / takeover protocol — live in the global `~/.claude/CLAUDE.md` under "Project directory boundaries and dual-window safety". They apply here unchanged.

Super_claude-specific notes:
- `.worktrees/` is already listed in this repo's `.gitignore`.
- The canonical worktree path here is `D:\projects\super_claude\.worktrees\<branch>\`.

## State files (gitignored, don't commit)

- `~/.claude/.hermes_curator_queue.json`, `.hermes_curator_state.json` — curator queue.
- `~/.claude/.qrev_auto_state.json` — auto-qRev counters.
- `~/.claude/.statusline_baselines.json` — per-session context-bar baselines.
- `~/.claude/.ecc-session-bridge/` — session metrics for the statusline.
- `D:\projects\super_claude\hermes-agent\claude_code_integration\ruvector.db` and the top-level `ruvector.db` — embeddings / skill state.

All of the above are listed in `.gitignore` and must stay there.
