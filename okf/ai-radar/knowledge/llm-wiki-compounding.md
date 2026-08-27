---
type: technique
title: Compounding LLM wiki (vs static RAG)
description: A persistent, LLM-maintained wiki that compounds knowledge over time instead of re-deriving it per query.
tags: [karpathy, llm-wiki, rag, knowledge, maintenance]
timestamp: 2026-06-28T00:00:00Z
resource: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
status: current
supersedes: []
---

# Core idea

Move beyond per-query RAG to a persistent, LLM-maintained wiki that COMPOUNDS:
"the wiki is a persistent, compounding artifact. The cross-references are already
there. The contradictions have already been flagged."

# Three layers

1. Raw sources (immutable) — curated documents, articles, papers.
2. The wiki — LLM-generated markdown: summaries, entity pages, cross-references.
3. The schema — a config doc (like `CLAUDE.md`) governing maintenance workflows.

# Operations

- Ingest: read new sources, extract, integrate — update 10-15 pages in one pass.
- Query: search relevant pages, synthesize with citations, file new discoveries back.
- Lint (maintenance): periodically health-check for contradictions, stale claims,
  orphan pages, missing cross-references. LLMs don't get bored doing this, so the
  wiki stays current without human effort — solving what kills human wikis.

# Why it matters here

This is the engine behind the AI Radar: the radar is exactly this compounding
wiki, scoped to "what is new / better in AI". The lint pass is the planned
`/radar-scan` health step. OKF (see
[open-knowledge-format](/knowledge/open-knowledge-format.md)) is the file format;
this technique is the maintenance loop that keeps it alive.

# Repo / source check

Karpathy gist (no installable package) — it is a written pattern, not a tool, so
the GitHub-inspection rule reduces to "read the gist as the source of truth".
Grounding source verified: the gist itself (`resource`).

# Related implementation (2026-08-27 scan)

[GBrain](/knowledge/gbrain.md) is a concrete, popular, production-scale
open-source implementation of this exact thesis (compounding markdown
knowledge graph vs. vector-only RAG) — worth cross-referencing as a
reference implementation, though its own benchmark numbers are self-reported
and unverified.
