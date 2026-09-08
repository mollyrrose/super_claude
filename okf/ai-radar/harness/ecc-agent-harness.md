---
type: tool
title: affaan-m/ECC — agent-harness performance-optimization stack
description: Performance-optimization plugin stack (68 agents/286 skills/94 commands) for Claude Code, Codex, Cursor — already installed and partially hook-disabled in this project for performance reasons.
tags: [claude-code, agent-harness, skills, mcp, github-trending, unverified]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/affaan-m/ECC
status: unverified
supersedes: []
---

# Summary

Surfaced via GitHub trending on both the daily (#4) and weekly (#2, largest
gain of the sweep at +7,735) overall boards. README cites a v2.1 refresh
adding a "Plan Canvas" browser-based plan reviewer, Kimi-harness support,
and self-hosted GPU integration ("Itô") as recent drivers. MIT license,
2,667 commits.

# Repo / source check — unverified

254k stars / 38k forks is disproportionate to the repo's commit depth/age —
part of the same stars-vs-commits mismatch pattern flagged in
[trending-skillpack-star-inflation-pattern](/agent-tooling/trending-skillpack-star-inflation-pattern.md).
Star/growth numbers are marked `unverified` accordingly. However, the
plugin's *functionality* is independently corroborated: this project's own
CLAUDE.md documents having the ECC plugin installed with several of its
hooks (`pre:observe`, `stop:check-console-log`, etc.) explicitly disabled
via `ECC_DISABLED_HOOKS` after they caused spawn timeouts and Stop-hook
errors under load — i.e. this is a real, in-the-wild tool actually running
in this environment, not vaporware, even though its growth metrics are
unconfirmed.

# Why this is in the radar

Already a live dependency of this repo (see the project CLAUDE.md's "ECC
plugin hooks disabled on this setup" section) — tracking its upstream
releases matters directly for whether the local hook-trimming workaround
needs re-applying after a plugin-cache update.
