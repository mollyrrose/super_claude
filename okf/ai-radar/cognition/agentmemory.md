---
type: tool
title: agentmemory (rohitg00) — hook-based persistent memory for 20+ coding agents
description: SQLite-backed persistent memory using semantic search + knowledge graphs across Claude Code, Cursor, Copilot, Gemini CLI and more. Benchmark and cost-savings claims are self-reported — treat as unverified.
tags: [agent-memory, knowledge-graph, multi-agent-support]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/rohitg00/agentmemory
status: current
supersedes: []
adoption: awareness-only-claims-unverified
---

# Summary

agentmemory is a persistent, hook-based memory system for 20+ coding agents
(Claude Code, Cursor, Copilot, Gemini CLI, etc.) using semantic search plus
knowledge graphs, self-contained on SQLite (no external DB required).
Ships a real-time viewer and roughly 54 MCP tools. Claims strong benchmark
numbers (95.2% R@5 on LongMemEval-S, 92% fewer tokens vs. baseline) and a
large cost-reduction pitch (~$500/yr -> ~$10/yr in token costs). Surfaced via
GitHub TypeScript trending (119 stars/day) under a "#1 persistent memory"
framing.

# Repo / source check

Apache-2.0, ~482 commits — repo itself looks active and legitimately
maintained with a real commit history. The benchmark and cost-savings
figures are self-reported by the author, not independently reproduced —
treat those claims specifically as unverified, distinct from the repo's own
legitimacy (which checks out on the signals available here).

# Why this is in the radar

Multi-agent (not Claude-Code-only) hook-based memory approach worth
comparing against this project's own dispatcher-based hook architecture and
memgraph loop. Awareness only — the repo is real, but the marketed
performance numbers should not be repeated as validated fact until
reproduced independently.
