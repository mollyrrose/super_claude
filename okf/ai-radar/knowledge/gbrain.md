---
type: tool
title: GBrain — self-wiring markdown knowledge graph
description: Zero-LLM-call entity/edge extraction on every markdown write, building a knowledge graph over people/company/deal pages. Active, popular, self-reported benchmarks unverified.
tags: [knowledge-graph, markdown, rag-alternative, open-source]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/garrytan/gbrain
status: current
supersedes: []
---

# Summary

GBrain (open-sourced 2026-04-05, v0.12 update reported week of 2026-08-03) is
a self-wiring markdown knowledge graph: zero-LLM-call entity/edge extraction
runs on every markdown write, and the tool performs "synthesis, graph
traversal, gap analysis" over people/company/deal pages. Claims +31.4 point
P@5 lift vs. vector-only RAG (P@5 49.1%, R@5 97.9%).

# Repo / source check

MIT license, 1,039 commits, reported ~24.6k stars / 3.5k forks by mid-2026 —
confirmed real and active via direct WebFetch of the README. However, the
performance numbers come from a **sibling `gbrain-evals` repo the project
maintains itself** — self-reported, not independently reproduced by a third
party. Treat the specific benchmark figures as unverified even though the
project and its mechanism are real.

# Why this is in the radar

A concrete, popular, production-scale implementation of exactly the thesis
in [llm-wiki-compounding](/knowledge/llm-wiki-compounding.md) — "compounding
markdown knowledge, not a vector store" — and directly relevant to
[open-knowledge-format](/knowledge/open-knowledge-format.md)'s knowledge-graph
angle. Worth watching as a reference implementation; this bundle's own
`memgraph`/`graphifyy` setup already does a similar thing over a different
graph engine.

# Notes

- Re-verify the P@5/R@5 numbers against an independent benchmark if one
  surfaces; do not cite them as confirmed until then.
