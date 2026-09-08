---
type: tool
title: ZenBrain — 7-layer neuroscience-inspired memory architecture
description: Zero-dependency TypeScript memory library with FSRS spaced repetition, Hebbian graph learning, and a sleep-consolidation loop; ships an MCP server. Small install base, self-reported benchmarks.
tags: [hierarchical-memory, sleep-consolidation, typescript, mcp-server, unverified]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/zensation-ai/zenbrain
status: unverified
supersedes: []
---

# Summary

ZenBrain unifies 15 neuroscience-derived mechanisms — two-factor synaptic
consolidation, FSRS spaced repetition, Hebbian knowledge-graph learning, a
"simulation-selection sleep loop" modeling hippocampal replay, emotional-
salience tagging, Bayesian confidence propagation — under one
`MemoryCoordinator`, shipped as composable `@zensation/*` npm packages plus
an MCP server and a Vercel AI SDK middleware. The accompanying paper
(arXiv 2604.23878) reports winning all nine head-to-head comparisons
against Mem0, Letta, and A-Mem on a LongMemEval-500 slice.

# Repo / source check — unverified

Real, live repo — Apache-2.0, 23 stars, a legitimate package structure
(`@zensation/core`, `@zensation/algorithms`, Postgres/SQLite adapters, MCP +
AI-SDK integrations). A "9,228 passing tests" figure circulating in
secondary sources does not match the repo's own stated "528 tests" (429
algorithm + 99 core) — treat the larger number as an error in secondary
coverage, not the repo's own claim. Benchmark superiority claims are
self-reported by the same team that built the library, with Zenodo
reproduction packages offered but no independent third-party replication
found. Small star count means low community traction even though the code
and paper both look legitimate on inspection.

# Why this is in the radar

Ships an MCP server out of the box — the natural integration point for a
Claude Code memory layer — and its Hebbian-learning-on-a-knowledge-graph
mechanism is a specific, code-level pattern the existing memgraph/graphify
setup doesn't implement. Overlaps in ambition with
[letta-sleep-time-compute](/cognition/letta-sleep-time-compute.md) and this
project's own memgraph/graphify stack.

# Notes

- `status: unverified` — watch, don't adopt, given the small install base
  and self-reported benchmarks.
