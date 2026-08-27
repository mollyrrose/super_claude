---
type: tool
title: DeepSeek Harness (dsh)
description: DeepSeek's open-source, plugin-only TypeScript agent harness — a competing architecture to Claude Code's hooks/skills/MCP model.
tags: [deepseek, agent-harness, open-source, competing-architecture]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/deepseek-ai/deepseek-harness
status: current
supersedes: []
adoption: awareness-only
---

# Summary

DeepSeek released an open-source, TypeScript-based agent harness ("dsh") on
2026-08-13, built on an "everything-is-a-plugin" architecture — the model
adapter, tool registry, session log, and the agent loop itself are all
replaceable plugins — under a design DeepSeek calls "Cordis". This is a
different shape from Claude Code's fixed-harness-plus-hooks/skills/MCP
extension model.

# Repo / source check

Verified directly via the GitHub API (not just README/press claims): owner
is the genuine `deepseek-ai` GitHub organization (org id 148330874, matches
DeepSeek's known org), repo created 2026-08-13, last push 2026-08-27
(actively maintained through the day of this scan), MIT license, 200,003
stargazers / 22,839 forks. `has_pull_requests: false` and
`open_issues_count: 0` — issue/PR tracking appears disabled or redirected to
Discussions, a mild transparency gap worth noting. Real npm package
(`@deepseek-ai/dsh`) with build instructions and docs folders backs the
architecture claim.

The star-count trajectory reported by press (95K -> 200K within two weeks)
could only be cross-checked via a single API snapshot, not historical
star-history data — treat "fastest adoption ever" framing as unverified
marketing even though the repo itself is confirmed legitimate and
code-backed.

# Why this is in the radar

A genuine competing agent-harness architecture worth tracking for design
ideas (plugin-only core vs. fixed-core-plus-hooks), not a recommendation to
switch off Claude Code. `adoption: awareness-only` — this is a landscape
entry, not a "speak up" supersession.
