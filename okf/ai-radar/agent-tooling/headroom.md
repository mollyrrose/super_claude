---
type: tool
title: Headroom (context compressor)
description: Local LLM-context compressor — same niche as our tokenjuice, far more capable, BUT skillspector-blocked (score 100, DO_NOT_INSTALL).
tags: [tokens, compression, context, cost, tokenjuice, blocked]
timestamp: 2026-06-29T00:00:00Z
resource: https://github.com/chopratejas/headroom
status: current
supersedes: []
adoption: BLOCKED-skillspector-do-not-install
destructive: no
---

# Summary

Compresses LLM context (tool outputs, logs, files, RAG chunks, history) BEFORE it
reaches the model — claims 60-95% fewer tokens, "same answers". Apache 2.0, very
active (53k+ stars, releases through 2026-06). Algorithms: SmartCrusher (JSON),
CodeCompressor (AST), Kompress (trained prose model), CacheAligner (KV-cache prefix
stabilization), CCR (reversible — stores originals, LLM calls `headroom_retrieve`).
Modes: library `compress(messages)`, proxy, CLI wrapper, MCP server. Same niche as
our `scripts/tokenjuice.py`, much more capable.

# Repo / source check — BLOCKED (2026-06-29)

`skillspector` scan-before-trust verdict: **score 100, severity CRITICAL,
recommendation DO_NOT_INSTALL** (1135 issues, mostly MEDIUM). Per the standing
scan-before-trust policy (>=70 -> block + ask), Headroom is **NOT installed**.

Caveat for context (not an override): the scan was static-only (`--no-llm`) on a
large, legitimate repo; a compressor that spawns processes, reads files, runs Rust,
and offers a proxy/MCP mode trips many system-level static patterns, so a high score
is partly expected and likely carries false positives. The policy still blocks; any
adoption requires explicit user approval AND a safer path (deeper LLM-backed scan,
and/or isolated VM), never a host install on this verdict.

# Why it was on the radar

A possible upgrade to the tokenjuice opt-in slot (compress known-noisy output). The
gate did its job: it is parked as awareness, `adoption: BLOCKED`, until the user
decides whether to override under sandboxing. NOT a transparent proxy on the main
session regardless (MITM in the critical path).
