# Crush vs Claude Code - honest analysis + how we use it here

Written 2026-07-10. Source: sourced web research (Crush repo docs, DeepWiki,
hands-on reviews) + a local install/trial. This answers "why does the pasted
comparison claim Crush is better, and how do we improve our workflow with it."

## TL;DR

The pasted comparison table (10/10 vs 9/10 scores, "2-5x faster commits", "builds
its own index", "auto build-fix loop") is **mostly fabricated**. Crush is NOT a
smarter coder than Claude Code - it is a different *front-end* that can drive many
models. Running Claude through Crush uses the exact same Claude model, so
"Crush > Claude" is a category error. Crush does have a few **real**
differentiators (multi-model, LSP tools, native Windows) that make it worth
keeping as a **secondary** tool. Claude Code stays primary because the entire
super_claude harness (hooks, coord, q* skills, statusline) is Claude-Code-only.

## What Crush is

- Terminal AI coding agent by Charmbracelet (Bubble Tea authors), written in Go.
- License FSL-1.1-MIT (source-available, converts to MIT after 2 years).
- Very active (multiple releases/week). ~26k stars.
- A workflow/agent shell, model-agnostic - not a model.

## The pasted table, claim by claim

| Claim in the pasted table | Verdict | Reality |
| --- | --- | --- |
| "10/10 vs 9/10" benchmark scores | FABRICATED | No such benchmark exists in any source. |
| "2-5x faster git commits" | FABRICATED | Zero basis anywhere; git integration is comparable in design. |
| "Builds its own index" | FABRICATED | Crush has NO persistent project index. It generates an AGENTS.md once; uses LSP for semantic context. |
| "Auto runs builds and fixes errors" loop | FABRICATED | Does not exist. Issue #1734 is a *request* for build/plan modes. |
| "Continuously watches the project" | MISLEADING | The only watcher feeds LSP state, not agent context, and has scaling problems on big trees (issue #1039). |
| "100-file refactor / monorepo: Crush wins" | CONTRADICTED | The one hands-on review says Crush "drifts on refactors past ~50 files"; reviewers recommend Windsurf, not Crush, for large monorepos. |

## Real differentiators (these are true and useful)

- **Multi-model.** Anthropic, OpenAI, Gemini, Bedrock, OpenRouter, and any
  OpenAI-compatible endpoint: Ollama, LM Studio, llama.cpp, GLM (z.ai). Mid-session
  model switching. Claude Code is Anthropic-only.
- **LSP as agent tools.** `lsp_diagnostics`, `lsp_references`, `lsp_restart` give
  the agent compiler-grade type info and error diagnostics. Claude Code has no
  equivalent structured LSP surface.
- **Native Windows** (no WSL). Reads CLAUDE.md, AGENTS.md, CRUSH.md, GEMINI.md.

## The critical caveat before adopting

- **Crush removed Anthropic OAuth in Jan 2026** (PR #1783, at Anthropic's request).
  It can NOT use your Claude subscription - only an API key or a custom endpoint.
- None of the super_claude ecosystem carries over: hooks, coord board, q* skills,
  statusline, the banner rule - all Claude-Code-specific.

Conclusion: run Crush against a **free local model** (your llama.cpp "Ornith"
server) or GLM, NOT per-token Anthropic API. Keep Claude Code primary.

## How it is wired up here

- Installed via the official npm package: `npm install -g @charmland/crush`
  (v0.84.0; newer than the winget package). `crush --version` confirms.
- `crush.json` (gitignored; template is `crush.json.example`) defines three
  providers:
  - `local-llama` -> `http://localhost:8080/v1` (llama.cpp OpenAI-compatible,
    the Ornith GGUF). This is the default `large`/`small` model.
  - `glm-zai` -> `https://api.z.ai/api/anthropic` (DORMANT until `ZAI_API_KEY`).
  - `anthropic-apikey` -> per-token API (DORMANT until `ANTHROPIC_API_KEY`).
- `CRUSH.md` at the repo root tells Crush it is secondary and must not touch
  Claude Code state files.

## How to run the trial (local + free)

Start the llama.cpp server (port 8080), then:

```
# non-interactive, auto-accept file ops, against the local model
crush --yolo run -c .scratch/crush-trial "Create adder.py with add(a,b) and mul(a,b)."

# or interactive TUI
crush
```

Because the default model is the local llama.cpp server, this costs nothing.
(Note: a large local model like the 35B Ornith is slow; use it to exercise the
*workflow*, not to benchmark code quality.)

## When to reach for which

| Situation | Tool |
| --- | --- |
| Anything in this repo (hooks, skills, coord, q* flows) | Claude Code |
| Day-to-day coding on your Claude subscription | Claude Code |
| Want to run a task on a LOCAL/free model or GLM | Crush |
| Want compiler-grade LSP diagnostics/references as agent tools | Crush |
| Comparing model behaviour across providers on one task | Crush (mid-session switch) |
| Deep multi-file refactor, autonomous long task | Claude Code (Crush drifts past ~50 files) |

## Kill switch

`npm uninstall -g @charmland/crush` (or `winget uninstall charmbracelet.crush` if
installed that way), then delete `crush.json` and `CRUSH.md`. Nothing else depends
on Crush.
