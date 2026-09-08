---
type: tool
title: context-mode — MCP context-budget sandboxing server
description: MCP server that sandboxes tool output, persists session memory in SQLite/FTS5, and enforces context-safe routing across 17 coding-agent platforms; claims 98% tool-output reduction.
tags: [mcp, context-window, agent-harness, sqlite, github-trending]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/mksglu/context-mode
status: current
supersedes: []
---

# Summary

Surfaced via GitHub trending (daily-overall, daily-TS, weekly-TS — 3 of 6
views). Addresses the same "context budget" problem this project's own
`context_budget_gate.py`/`tokenjuice.py` solve for locally, but as a
standalone MCP server: claims 98% tool-output reduction (a cited 315KB ->
5.4KB example) and BM25-search session-memory restore after compaction.

# Repo / source check

ELv2 (Elastic License v2 — not fully open-source/permissive; worth flagging
for anyone evaluating redistribution), 2,174 commits, 113 open issues / 104
open PRs (active), real `src/`/`tests/`/`hooks/` structure visible. Its
~21k star count is plausible relative to commit depth — one of the less
suspicious trending-repo profiles in this sweep (contrast with
[trending-skillpack-star-inflation-pattern](/agent-tooling/trending-skillpack-star-inflation-pattern.md)).

# Why this is in the radar

Directly comparable to this project's own context-budget approach
(`context_budget_gate.py`, `tokenjuice.py`) but solves it at the MCP-server
layer instead of hooks — worth a look for design ideas (its BM25 session-
memory restore in particular), not necessarily an adoption candidate given
the non-permissive license.
