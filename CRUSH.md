# CRUSH.md - Crush-specific notes for super_claude

Crush (charmbracelet/crush) reads this file automatically when run in this repo.
Claude Code does NOT read it. Crush-only guidance lives here; shared project rules
stay in `CLAUDE.md` (Crush reads that too).

## Status: secondary tool, Claude Code is primary

This repo's whole harness - the hooks in `~/.claude/settings.json`, the coord
board, the `q*` skills, the statusline, the USER INPUT REQUIRED banner - is
Claude-Code-specific and does NOT run under Crush. When operating as Crush:

- Do NOT assume any hook, curator, smart-router, coord, or qRev automation is
  active. None of it fires under Crush.
- Do NOT read, write, or delete Claude Code state files:
  `~/.claude/.hermes_*`, `~/.claude/.coord/`, `~/.claude/.qrev_*`,
  `~/.claude/.statusline_baselines.json`, `~/.claude/.ecc-session-bridge/`.
  They belong to the Claude Code windows and Crush touching them corrupts
  cross-window coordination.
- Follow `CLAUDE.md`'s "No decorative unicode" rule and working-style rules -
  those are tool-agnostic and still apply to code you write here.

## Model provider

Default to the local, free provider so a trial costs nothing:

- `local-llama` -> llama.cpp OpenAI-compatible server on `http://localhost:8080/v1`
  (the "Ornith" GGUF). Start it before running Crush; confirm with
  `curl http://localhost:8080/v1/models`.
- `glm-zai` and `anthropic-apikey` are wired in `crush.json` but DORMANT (need
  `ZAI_API_KEY` / `ANTHROPIC_API_KEY`). Crush cannot use the Claude Code
  subscription - Anthropic OAuth was removed from Crush in Jan 2026 (PR #1783).

Copy `crush.json.example` to `crush.json` (gitignored) and adjust the local model
`id` to match what `/v1/models` reports if your llama-server build requires it.

## Security

`crush.json` is trusted code: any `$(...)` in it runs at load time with your
shell's privileges. Keep API keys as plain `$ENV_VAR` references (never inline a
secret, never use `$(...)` to fetch one here). The real `crush.json` is gitignored
so keys/paths are never committed.

## Kill switch

Remove Crush entirely: `winget uninstall Charmbracelet.Crush`, then delete
`crush.json` and this `CRUSH.md`. Nothing else in the repo depends on Crush.
