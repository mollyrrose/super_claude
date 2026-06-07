# CLAUDE.md — super_claude project

This file extends the global `~/.claude/CLAUDE.md` with rules specific to this repo.

## Project shape

`super_claude` is the personal Claude Code setup: hook scripts in `~/.claude/scripts/`, the curator and skill-lifecycle Python modules under `hermes-agent/claude_code_integration/`, and a `claude_skills_backup/` of ~165 skills that get installed into `~/.claude/skills/`. See `README.md` for the full feature catalog.

## No decorative unicode

This rule mirrors the global rule and is restated here so it's visible inside the project too.

Don't put characters like the rightward arrow (U+2192), checkmark (U+2713/U+2714), cross (U+2717/U+2718), bullets (U+2022/U+25CF/U+25E6), stars (U+2605/U+2606) or pointing triangles (U+25B6/U+25BC) into source files, markdown, comments, commit messages, or PR bodies.

Reasons:
- Windows cp1252 console crashes on emit (`UnicodeEncodeError`); test smoke scripts have already hit this.
- ripgrep / grep with default ASCII expectations miss them.
- They render differently across terminals, editors, and chat tools.
- They add no information vs plain ASCII.

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

## State files (gitignored, don't commit)

- `~/.claude/.hermes_curator_queue.json`, `.hermes_curator_state.json` — curator queue.
- `~/.claude/.qrev_auto_state.json` — auto-qRev counters.
- `~/.claude/.statusline_baselines.json` — per-session context-bar baselines.
- `~/.claude/.ecc-session-bridge/` — session metrics for the statusline.
- `D:\projects\super_claude\hermes-agent\claude_code_integration\ruvector.db` and the top-level `ruvector.db` — embeddings / skill state.

All of the above are listed in `.gitignore` and must stay there.
