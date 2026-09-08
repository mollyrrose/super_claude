---
type: technique
title: Memory portability across model upgrades
description: Controlled study — fixed-schema knowledge-graph memory survives a writer-model swap almost losslessly; free-text "notes" memory degrades sharply and asymmetrically.
tags: [memory-portability, knowledge-graph, model-upgrade, evaluation, benchmark]
timestamp: 2026-09-08T00:00:00Z
resource: https://arxiv.org/abs/2609.05339
status: current
supersedes: []
---

# Summary

"Does Your Agent's Memory Survive a Model Upgrade? A Controlled Study of
Memory Portability" (Goyal, Ray; submitted 2026-09-04, under review, no
venue yet) compares four memory representations — long-context raw history,
RAG chunk retrieval, model-written NOTES summaries, and a fixed-schema
knowledge graph (KG-fixed) — across 48 synthetic histories, testing what
happens when the model that wrote the memory is swapped for a different
model that must read it. KG-fixed transferred almost perfectly (accuracy
changed by only +/-0.002 after a writer swap). NOTES-style summaries showed
strong model coupling: accuracy shifted by as much as +9.91 or -13.28
percentage points depending on the model pair, i.e. a new model can silently
misread the old model's summarization conventions. RAG with a mixed
old/new embedding index captured only 4.96 of the possible 11.90-point gain
that full re-embedding would give — partial re-embedding after a model/
embedding upgrade is a real, quantified failure mode.

# Repo / source check

No accompanying code repo found — paper-only, small synthetic benchmark (48
histories, two open-weight models under 10B params). Treat the specific
percentage-point numbers as a small controlled study, not an industrial
benchmark; the qualitative direction (schema > notes > raw text for
cross-model durability) is the actionable claim. `arxiv.org` was blocked by
this sandbox's egress proxy — content reconstructed from WebSearch snippets,
not the primary PDF/HTML; re-verify exact figures before citing precisely.

# Why this is in the radar

Directly validates this project's own memory-layer design bet: typed
markdown memory files (closer to NOTES) plus a knowledge graph built over
them (closer to KG-fixed, via `~/.claude/memory-graph/`). The graph layer is
the part that should be trusted to survive a `/model` switch or a Claude
version upgrade; the free-text MEMORY.md/session-note layer should be
treated as more fragile across model changes and periodically re-normalized
into the graph rather than left as the durable source of truth. For a
community-brain use case, this is a concrete argument for schema-first
shared knowledge over prose summaries if the base is ever read by an
updated/different model than the one that wrote it.

# Notes

- Cross-link: [letta-sleep-time-compute](/cognition/letta-sleep-time-compute.md)
  and [anthropic-dreaming-memory](/knowledge/anthropic-dreaming-memory.md)
  both write/reorganize memory; this paper is the distinct empirical angle
  of what happens to that memory across a model swap, not consolidation
  quality.
