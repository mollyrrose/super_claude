---
type: tool
title: OpenAI Codex — competing terminal coding agent harness
description: OpenAI's lightweight terminal coding agent (Rust core) with VS Code/Cursor/Windsurf integrations; largest single weekly star gain across GitHub trending this sweep.
tags: [openai, agent-harness, competing-product]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/openai/codex
status: current
supersedes: []
---

# Summary

OpenAI's Codex is a lightweight terminal coding agent with a Rust core
(~9,900 commits) and editor integrations for VS Code, Cursor, and Windsurf,
with low-friction install paths (npm, Homebrew) across platforms.

# Repo / source check

Alive and legitimate: official OpenAI org repo, active commit volume,
Apache-2.0 license. Surfaced via GitHub daily trending with +12,120 stars
this week — the single largest weekly gain across all trending views
checked in this sweep. Could not confirm one discrete trigger event for the
spike (no specific release/announcement pinned down); the broadened editor
integrations and easy install paths are the likely drivers, but that
attribution is inferred, not confirmed.

# Why this is in the radar

Direct competing product to Claude Code — awareness entry, alongside
[deepseek-harness](/harness/deepseek-harness.md), for tracking what
competing agent harnesses are shipping. No action implied.

# Update (2026-09-08 scan): GPT-6 Astra default, plugin tiers, delegation controls

[gpt-6-astra](/models/gpt-6-astra.md) became Codex's recommended default
model on 2026-09-03 (bundled as default in CLI v0.153.4). `/plugins` now
sorts remote plugins into "OpenAI Curated," "Workspace," and "Shared with
me," with some turns proactively recommending/installing a relevant
plugin. App-server clients can set multi-agent delegation to disabled /
explicit-request-only / proactive at thread or turn granularity.
Configurable rollout token budgets track usage per agent thread, warn as
they deplete, and abort turns on exhaustion. An indexed web-search mode
restricts direct page fetches to server-approved URLs. Repo re-verified:
Apache-2.0, 122.5k stars, 10,428 commits on main, 5,000+ open issues, 170
open PRs — clearly active, though the exact v0.153.4 tag/date was not
independently confirmed from inside the repo itself.
