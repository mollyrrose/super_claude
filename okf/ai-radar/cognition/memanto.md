---
type: tool
title: Memanto — typed semantic memory with information-theoretic retrieval
description: Typed-category memory schema (13 predefined categories) + sub-90ms no-index semantic search; ships a Claude Code integration out of the box.
tags: [agent-memory, semantic-memory, claude-code-integration]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/moorcheh-ai/memanto
status: current
supersedes: []
adoption: strong-candidate-personal-memory-layer
---

# Summary

Memanto (paper: arXiv 2604.22085, April 2026) argues knowledge-graph
complexity isn't necessary for high-fidelity agent memory. It uses a typed
semantic memory schema (13 predefined memory categories), automated conflict
resolution, and temporal versioning, backed by a no-indexing semantic search
engine (sub-90ms retrieval) using "maximally informative binarization" to
compress embeddings. Claims SOTA on LongMemEval (89.8%) and LoCoMo (87.1%)
with a single retrieval query, beating hybrid graph+vector systems in its own
benchmark harness.

# Repo / source check

1.8k stars, MIT license, 894 commits, 82 open PRs, 6 open issues, 633 forks —
working CLI, dashboard, REST API, and TypeScript SDK, with explicit Claude
Code support listed among clients. Reads as a real, actively maintained
project. Benchmark numbers are self-reported (single paper, own harness,
authors' own caveat that cross-project scores aren't directly comparable) —
not independently reproduced here.

# Why this is in the radar

Strongest direct match in this sweep for the personal-memory-layer consumer:
a typed-category memory schema is exactly the shape of this project's
"typed markdown memory files" design, and it already ships Claude Code
integration rather than requiring one to be built. Worth a hands-on trial
rather than pure conceptual borrowing — but treat the LongMemEval/LoCoMo
numbers as vendor-authored until reproduced elsewhere.
