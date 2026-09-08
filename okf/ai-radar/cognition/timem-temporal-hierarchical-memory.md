---
type: tool
title: TiMem — Temporal-Hierarchical Memory Consolidation
description: Open-source 5-level temporal memory tree (segment/session/day/week/profile) with complexity-aware recall; ACL 2026 Findings, SOTA on LoCoMo/LongMemEval-S.
tags: [hierarchical-memory, consolidation, temporal, agent-memory, benchmark]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/TiMEM-AI/timem
status: current
supersedes: []
---

# Summary

TiMem organizes conversation history into a 5-level "Temporal Memory Tree"
(raw fragments -> session summaries -> daily patterns -> weekly trends ->
stable profile) using semantic-guided consolidation across levels without
fine-tuning, plus a "complexity-aware recall" planner that decides how deep
into the hierarchy to search based on query difficulty. Claims SOTA on
LoCoMo (75.30%) and LongMemEval-S (76.88%) while cutting recalled memory
length by 52% on LoCoMo versus baselines. Paper originally posted January
2026, accepted to ACL 2026 Findings (2026.findings-acl.1091), with a
v1.1.0 GitHub release in May 2026.

# Repo / source check

Live and maintained: ~176 stars, ~9 forks, dual Apache-2.0 (core) / MIT
(tools) license. v1.1.0 release restored missing modules and references the
ACL acceptance — an actively maintained project, not a one-shot paper dump,
and backed by a peer-reviewed publication (a stronger verification bar than
most memory repos in this space). Roadmap includes multi-agent
collaboration features.

# Why this is in the radar

The segment -> session -> day -> week -> profile hierarchy is a close
template for how this project's own markdown memory files could be
organized (currently closer to a flat MEMORY.md + graph), and
"complexity-aware recall" (deciding search depth by query difficulty) is
directly applicable to tuning `memgraph query`'s BFS depth. For a
community-brain use case, its pattern of keeping intermediate abstraction
tiers with provenance back to raw data — rather than consolidating
everything straight to the top — is more concretely engineerable than most
survey papers in this space.

# Notes

- Related to the [dual-process-graph-memory-research-2026](/cognition/dual-process-graph-memory-research-2026.md)
  cluster (also hierarchical/graph memory) but distinct enough (maintained
  code + a peer-reviewed benchmark result) to stand as its own entry.
