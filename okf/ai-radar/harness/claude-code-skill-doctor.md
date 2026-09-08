---
type: pattern
title: Claude Code /skill-doctor — skill usage/context-cost auditor
description: New built-in slash command shows which loaded skills go unused and what they cost in context, so users can prune bloat.
tags: [claude-code, skills, context-management, cli]
timestamp: 2026-09-08T00:00:00Z
resource: https://code.claude.com/docs/en/changelog
status: current
supersedes: []
---

# Summary

Shipped in Claude Code v2.1.261 (2026-09-04). `/skill-doctor` inspects the
skills currently loaded in a session and reports which ones the agent
hasn't actually invoked, plus their context-token footprint, letting a user
trim `~/.claude/skills/` or plugin-provided skills that are dead weight.

# Repo / source check

Closed-source CLI; verified via the official Anthropic changelog page,
which is the primary/authoritative source for Claude Code release notes.
No repo to inspect since the CLI binary itself is not open source.

# Why this is in the radar

Directly relevant to this project's skill-lifecycle tooling (curator,
`claude_skills_backup/`'s ~165 skills) — gives an official, built-in way to
see skill context cost instead of relying only on custom hermes-curate
tooling. Worth running periodically alongside the curator to cross-check
findings.
