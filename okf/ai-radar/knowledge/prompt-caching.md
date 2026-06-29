---
type: technique
title: Anthropic prompt caching (cache_control ephemeral)
description: Prefix cache that bills repeated prompt prefixes at ~0.1x — real cost saver, but the main Claude Code session is already cached by the harness.
tags: [anthropic, caching, cost, tokens, api]
timestamp: 2026-06-29T00:00:00Z
resource: https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
status: current
supersedes: []
adoption: narrow-our-direct-api-scripts-only
---

# What it is

`cache_control: {type: "ephemeral"}` marks a breakpoint in the request; the matching
PREFIX is cached. Cache reads bill at ~0.1x input price (up to ~90% off the cached
span); writes 1.25x (5-min TTL, default) or 2x (1h TTL). Max 4 breakpoints.
Prefix-match: any byte change anywhere in the prefix invalidates everything after it.
TypeScript: same field `cache_control: { type: "ephemeral" }` in `@anthropic-ai/sdk`;
verify via `usage.cache_read_input_tokens`.

# Minimum cacheable prefix (the gotcha)

A prefix below the model minimum silently does NOT cache (no error, just
`cache_creation_input_tokens: 0`): Opus 4.8/4.7/4.6 + Haiku 4.5 = 4096 tok;
Fable 5 / Sonnet 4.6 = 2048 tok; Sonnet 4.5/3.7 = 1024 tok.

# Does it apply to US? (assessed 2026-06-29)

- **Main Claude Code session: already cached by the harness.** We do NOT author those
  API calls; nothing to "write into the .py" for the main session.
- **Our own direct-API scripts: only where a LARGE stable prefix repeats.** Inventory
  found the qPlan Claude critic
  (`hermes-agent/claude_skills_backup/qPlan/scripts/claude_critic.py`) as the main
  direct caller. Its stable part (`CRITIC_PROMPT`) is ~150 tokens — far below the
  4096-tok minimum, and the bulk (task/plan/ledger) is volatile per call. So
  `cache_control` would cache nothing there. **No actionable caching win in our code.**
- **Conflict with memory ops?** None — orthogonal. Caching is about the request
  *prefix*; memory recall is *content*. Discipline only: stable content first,
  volatile (timestamps, freshly-recalled memory) after the last breakpoint.

# Repo / source check

Authoritative: the `claude-api` skill's `shared/prompt-caching.md`. No repo to scan.
Verdict: real technique, narrow applicability to us — recorded, not bolted onto
harness-managed calls.
