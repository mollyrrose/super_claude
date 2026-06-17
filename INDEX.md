# INDEX — super_claude

Orientation map for a fresh session. For the full feature catalog see `README.md`.

## What this is

`super_claude` is the personal Claude Code setup: hook scripts, the curator /
skill-lifecycle Python, a backup of the installed skills, and the project-level
rules in `CLAUDE.md`. Editing here changes how every Claude Code session behaves.

## Key entry points

- `CLAUDE.md` — project rules (extends the global `~/.claude/CLAUDE.md`).
- `~/.claude/settings.json` — the live hook chain (not in this repo). Hooks point
  at `~/.claude/scripts/*` and `hermes-agent/claude_code_integration/*`.
- `scripts/` — tracked copies of hook/runtime scripts, installed to
  `~/.claude/scripts/`. Notably `context_budget_gate.py` (+ smoketest),
  `statusline_with_weekly.js`, and `claude-glm.ps1` (GLM/z.ai launcher).
- `hermes-agent/claude_code_integration/` — curator, `smart_router_*`,
  `decision_log_cli.py`, `mark_drained_cli.py`.
- `hermes-agent/claude_skills_backup/` — backup of installed skills, including the
  `q*` commands (qPlan/qRev/qMin/qClose/qRem/qUpd/qDo/qContent), the vendored
  `arbor-*` engine, `ponytail*`, `improve`, `drawio-skill`, `skillspector-gate`.
- `~/.claude/tools/skillspector/` — the security scanner (not in this repo).
- `docs/decisions/log.md` — decision log (ADR-style).

## How to run / test

- Hooks run automatically via `~/.claude/settings.json`; changing a hook means
  editing the tracked copy in `scripts/` and copying it to `~/.claude/scripts/`.
- Smoke tests live next to their scripts, e.g.
  `python scripts/context_budget_gate_smoketest.py` (6 cases).
- `/qPlan auto <goal>` runs the Arbor optimization loop (backend:
  `arbor-agent-tools/scripts/arbor_state.py`, stdlib-only).
- Before installing any external GitHub skill, the `skillspector-gate` rule scans
  it first.

## Local-only state (gitignored)

`exclude/TODO.md` (task list), `exclude/SYSTEM_STRATEGIES/` (SYSTEM_STATUS.md +
system_map.drawio), `.arbor/`, `.qplan/`, `.scratch/`. See `.gitignore`.
