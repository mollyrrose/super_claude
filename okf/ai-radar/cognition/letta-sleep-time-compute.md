---
type: tool
title: Letta (MemGPT lineage) — "sleep-time compute" memory consolidation
description: Reframes memory management as an asynchronous "sleep-time agent" separate from the conversational agent, converting raw context into learned context during idle time.
tags: [agent-memory, memgpt, async-consolidation]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/letta-ai/letta
status: current
supersedes: []
adoption: conceptual-only
---

# Summary

Letta (MemGPT lineage) reframes memory management as an asynchronous
"sleep-time agent" that runs separately from the conversational agent,
converting "raw context" into "learned context" during idle time — the same
consolidation-during-downtime shape as Anthropic's Dreaming primitive and
this project's own async curator/memgraph loop.

# Repo / source check

Mature: ~24.5k stars, Apache-2.0. Note: the `letta-ai/letta` repo itself is
now mostly a landing page — active code has moved to `letta-ai/letta-code`,
which was not independently checked in this pass. Re-verify against the
`letta-code` repo directly before citing specific implementation details.

# Why this is in the radar

Conceptually adjacent to
[anthropic-dreaming-memory](/knowledge/anthropic-dreaming-memory.md) and this
project's own async curator/memgraph loop — another independent instance of
the same "consolidate during idle time, not synchronously" pattern
converging across vendors. Conceptual-only for either downstream consumer
until `letta-code` itself is checked.
