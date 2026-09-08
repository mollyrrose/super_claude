---
type: tool
title: Maximem Synap SDK — agent memory layer, self-reported benchmarks
description: New, small vendor SDK claiming to beat mem0 on LongMemEval/LoCoMo via a public eval harness; numbers are self-reported, not third-party audited.
tags: [agent-memory, benchmark, unverified, vendor]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/maximem-ai/maximem_synap_sdk
status: unverified
supersedes: []
---

# Summary

Maximem (maximem.ai) is a new vendor with two products — "Synap" (agent
memory layer with framework integrations for LangChain/LlamaIndex/CrewAI/
Google ADK/AutoGen/OpenAI Agents/Semantic Kernel/Haystack/Pydantic AI) and
"Vity" (a personal cross-platform memory Chrome extension). The Synap SDK
repo claims 92% LongMemEval / 93.2% LoCoMo, positioned as beating "leading
published memory systems... run through the same open-source evaluation
harness on identical hardware," and links a public
`memory_and_context_eval_harness` repo plus a benchmark-results blog post.

# Repo / source check — unverified

Apache-2.0, 64 stars, 75 commits, cloud-API-key required (no self-hosted
option). Publishing a reproducible harness is a step better than a bare
marketing claim, but the numbers are still self-reported and not
third-party audited. `maximem.ai` was blocked by this sandbox's egress
proxy — this entry is built from the GitHub repo and search-engine
snippets, not a direct site read.

# Why this is in the radar

Same self-reported-superiority pattern as the existing
[mem0-agent-memory-benchmark-2026](/knowledge/mem0-agent-memory-benchmark-2026.md)
entry, but from a new, much smaller vendor — a second data point on how
noisy/gameable these leaderboard claims are getting, and notable for at
least shipping a public harness rather than only a claim.
