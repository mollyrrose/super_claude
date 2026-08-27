---
type: tool
title: Graphiti (Zep) — temporal knowledge graph for agent memory
description: Bi-temporal fact tracking (event time vs. ingest time) as the differentiator over flat vector memory; cited at ICLR 2026's MemAgents workshop.
tags: [knowledge-graph, agent-memory, temporal, zep]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/getzep/graphiti
status: current
supersedes: []
---

# Summary

Graphiti is Zep's open-source temporal knowledge-graph library for agent
memory: it tracks bi-temporal facts (when something happened vs. when the
system learned it), which is its differentiator over flat vector-store
memory. Cited at ICLR 2026's MemAgents workshop. Secondary sources report Zep
retired its self-hosted Community Edition in July 2026, pushing users toward
the managed product — this specific claim was NOT found on the repo page
itself and is unverified.

# Repo / source check

Repo and Apache-2.0 license confirmed via direct WebFetch. The
CE-retirement claim is unverified (only appears in secondary blogs, not on
the repo page) — do not treat it as confirmed when deciding whether Graphiti
remains self-hostable.

# Why this is in the radar

Background/comparison context for the knowledge-graph-for-agent-memory
cluster alongside [gbrain](/knowledge/gbrain.md) and
[cognee](/knowledge/cognee.md). No direct conflict with any tracked entry.

# Notes (2026-08-27 refresh)

The differentiator, made concrete: each edge tracks explicit bi-temporal
intervals (`t_valid`/`t_invalid`), i.e. when a fact was true in the world vs.
when the system ingested it — not just a single timestamp. Retrieval fuses
cosine similarity + BM25 + graph traversal + reranking; supported backends
are Neo4j, FalkorDB, and Neptune. Star count refreshed to ~30.4k. Cross-
linked from the new [cognition](/cognition/index.md) topic: the bi-temporal
edge model is a genuine upgrade path over this project's own
`graphifyy`-based memgraph, which does not currently track validity
intervals per edge.
