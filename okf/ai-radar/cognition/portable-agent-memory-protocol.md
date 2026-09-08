---
type: pattern
title: Portable Agent Memory protocol
description: Design proposal for a provenance-verified, model-agnostic memory-transfer format across heterogeneous AI agents/platforms — sits alongside MCP and A2A as a third interoperability layer.
tags: [interoperability, protocol, provenance, security, cross-agent-memory, unverified]
timestamp: 2026-09-08T00:00:00Z
resource: https://arxiv.org/abs/2605.11032
status: unverified
supersedes: []
---

# Summary

Proposes a JSON-first (optional CBOR) serialization for a five-component
memory model (Episodic, Semantic, Procedural, Working, Identity), with
content-addressable entries in a Merkle-DAG for tamper-evident provenance,
capability-scoped disclosure of memory segments, and an "injection-resistant
rehydration" step meant to stop recalled memory content from acting as a
prompt-injection vector when replayed into a different model. Posted May
2026, framed as sitting alongside MCP (tools) and A2A (agent-to-agent) as a
third interoperability layer specifically for memory.

# Repo / source check — unverified

No implementation or repo surfaced — this is a protocol/spec paper, not
shipped code. `arxiv.org` was blocked by this sandbox's egress proxy;
content reconstructed from WebSearch snippets, not the primary text. Treat
as a design proposal, not adoptable, until an implementation exists.

# Why this is in the radar

A community-brain concern more than a personal-memory-layer one: if a
shared knowledge base is ever read by multiple different agent stacks (not
just Claude Code), a portable, provenance-verified transfer format — and
specifically its injection-resistant rehydration idea — is worth informing
schema design before the community brain grows past a single consumer.
Also reinforces [memory-portability-model-upgrade-2026](/cognition/memory-portability-model-upgrade-2026.md)'s
KG-fixed-over-notes conclusion from an interoperability angle rather than a
pure-accuracy one.
