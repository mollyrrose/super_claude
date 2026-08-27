---
type: tool
title: Snyk agent-scan (formerly invariantlabs-ai/mcp-scan)
description: Scans agents, MCP servers, and Claude-style skills on disk for prompt injection, tool poisoning, and credential mishandling.
tags: [mcp, security, scanner, skills, snyk, prompt-injection]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/snyk/agent-scan
status: current
supersedes: []
adoption: awareness-candidate
---

# Summary

`agent-scan` (the former `invariantlabs-ai/mcp-scan`, now folded into Snyk
under Apache-2.0) scans agents, MCP servers, and Claude/other "skills" on
disk for prompt injection, tool poisoning, and credential mishandling.

# Why this is in the radar

This repo has ~165 skills installed under `~/.claude/skills/` plus multiple
MCP servers — exactly the surface this tool targets. A non-dual-use,
defensive scanner worth evaluating for periodic auditing of the skill
backup directory and MCP server list.

# Repo / source check

Strong legitimacy signals: 3,000 stars, 261 forks, 728 commits, signed
releases + SBOM, a visible security policy. Apache-2.0. No dual-use concerns
— it is a defensive scanner, not an offensive tool.

# Notes

- `adoption: awareness-candidate` — not yet run against this repo's own
  skill/MCP inventory; that would be a deliberate follow-up, not an
  automatic change from this scan.
