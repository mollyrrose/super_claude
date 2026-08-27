---
type: tool
title: claude-mem — cross-session memory plugin for Claude Code
description: Adds persistent cross-session memory to Claude Code by capturing tool observations, AI-compressing them, and reinjecting relevant context in later sessions. Repo star count looks like a scraping artifact — treat as unverified.
tags: [claude-code, agent-memory, cross-session]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/thedotmack/claude-mem
status: unverified
supersedes: []
---

# Summary

claude-mem adds persistent cross-session memory to Claude Code and other
agents: it captures tool observations, compresses them with an AI pass, and
reinjects relevant context in later sessions. Single-command install
(`npx claude-mem install`), optional cloud sync, Apache-2.0, ~2,440 commits.
Surfaced via GitHub trending (+260 stars/day on 2026-08-27) — solves the
exact "agent forgets everything between sessions" pain point this project's
own memgraph layer targets.

# Repo / source check

Directionally alive and active (real commit history, multi-platform support
for Claude Code and OpenClaw). However, the fetched total star count
(~92.2k) looks implausibly high for this repo's apparent scale/maturity —
flagged as a likely scraping artifact. Per this bundle's "be conservative"
rule, `status: unverified` until a manual github.com check confirms the real
star count and general legitimacy; do not recommend adoption at this scan.

# Why this is in the radar

Directly overlaps this project's own level-5 memory layer design goal.
Worth a manual re-check (real star count, closer README read) before any
recommendation either way — currently in the radar for awareness only, not
as a validated recommendation.
