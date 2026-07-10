# Base44 local code handoff - free-path runbook

Written 2026-07-10. Goal: work on Base44 apps as *code* from Claude Code (pull
down, edit locally, push back) instead of only the web UI, on the **free path**
(no paid Builder plan). Full two-way GitHub sync + backend deploy need Builder
(~$40/mo annual); that upgrade path is noted at the end.

## What is already installed

- **base44 CLI** (`npm install -g base44@latest`, v0.1.2). `base44 --version` OK.
- **Official Base44 skills** in `~/.claude/skills/` (from github.com/base44/skills):
  `base44-cli`, `base44-sdk`, `base44-remote-dev`, `base44-sandbox`,
  `base44-troubleshooter`. They auto-trigger when you work on a Base44 app.
- **Local frontend scaffold**: `github.com/yairm210/base44-site-template` cloned
  to `D:\projects\base44-site-template` (Vite + shadcn) for running exported JSX
  locally.

## Two steps YOU must run (interactive / permissioned - I cannot do these for you)

```
# 1. Authenticate the CLI (opens a browser OAuth flow)
base44 login

# 2. (optional) Register the no-auth Base44 Docs MCP so Claude can search Base44
#    docs live. This is a persistent user-scope integration, so run it yourself:
claude mcp add --transport http --scope user base44-docs https://docs.base44.com/mcp
```

The OAuth *project-management* MCP (`https://app.base44.com/mcp`) is optional and
also needs `base44 login`-style auth; add it the same way with a different name if
you want Claude to manage projects/entities directly.

## Free-path workflows

### A. Pull an existing web-editor app down to code
- `base44 eject` - forks the app locally: React frontend, entity schemas
  (`base44/entities/`), backend functions (`functions/`), config. **It creates a
  NEW app id with an empty database**; the original web app is untouched and does
  NOT stay in sync. One-time fork.
- Starter-plan alternative with no eject: open the in-app **Code Tab**, copy each
  file into the local `base44-site-template` scaffold by hand.

### B. Edit + preview locally
- Frontend: drop exported JSX into the `base44-site-template` `src/` and
  `npm run dev` for a local preview (entity/SDK calls forward to the hosted app).
- Or `base44 dev` - local server: backend functions auto-reload (Deno), entities
  in an in-memory DB, frontend dev server auto-started. Note: OAuth/social login,
  SendEmail, InvokeLLM (AI), and custom integrations still forward to the deployed
  app during `base44 dev`.

### C. Get changes back
- Frontend on free path: re-paste into the Code Tab, or continue in the ejected
  fork.
- `base44 functions deploy` / `base44 entities push` exist but backend functions
  are a **Builder+** platform feature, so expect these to be unavailable below
  Builder.

## Hard limits of the free path (be honest about these)

- No GitHub two-way sync (Builder+ only; and once connected it is **permanent/
  irreversible**).
- No backend `functions deploy` below Builder.
- `base44 dev` forwards auth, AI, email, and custom integrations to the hosted
  app; they do not run locally.
- `eject` copies entity *schemas*, not data records.

## DO NOT USE - security/ToS

`github.com/vmpprotect/base44-free-ai` is an **exploit proxy** that bypasses
Anthropic/OpenAI auth via an unprotected Base44 endpoint. Using it violates
Anthropic, OpenAI, AND Base44 ToS and may breach computer-fraud law. Do not clone,
install, or run it. (It was in the original link list; it is excluded on purpose.)

## When Builder ($40/mo annual) is worth it

- Real two-way GitHub sync (edit locally, `git push origin main`, auto-syncs).
- Backend functions deploy from the CLI.
- ZIP code export button.
If you move to Builder, the same CLI + skills here cover the full workflow; only
the plan gate changes.

## The official skills - what triggers what

- `base44-cli` - resource config (entities, functions, agents), init, deploy.
- `base44-sdk` - the `@base44/sdk` library for talking to remote resources.
- `base44-remote-dev` - drive a Base44 cloud sandbox from Claude Code over MCP or
  the `base44 sandbox` CLI subcommands.
- `base44-sandbox` - author app code directly in the cloud sandbox (no local
  checkout; writing a file ships it).
- `base44-troubleshooter` - debug production via backend function logs.
