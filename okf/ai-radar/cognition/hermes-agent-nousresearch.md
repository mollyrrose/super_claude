---
type: tool
title: Hermes Agent (NousResearch) — self-improving agent with closed learning loop
description: Open-source agent that creates/self-improves its own skills, writes agent-curated facts to MEMORY.md, and does FTS5 cross-session recall. Naming collision with this repo's own hermes-agent/ directory.
tags: [agent-memory, self-improving, nousresearch, naming-collision]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/nousresearch/hermes-agent
status: current
supersedes: []
adoption: worth-a-side-by-side-comparison
---

# Summary

NousResearch's Hermes Agent is an open-source agent built around a "closed
learning loop": it creates skills from experience, self-improves skills
during use, writes agent-curated facts to `MEMORY.md` with periodic nudges to
persist durable knowledge, does FTS5 session search with LLM summarization
for cross-session recall, and layers in "Honcho dialectic user modeling" to
build a deepening model of the user over time. Deployable from a $5 VPS up to
GPU clusters.

# Repo / source check

MIT license, 25,868 commits, 5k+ open issues (large, active community).
**Flag:** WebFetch reported 237.3k stars for this repo, which is implausibly
high for this project's apparent profile — likely a scraping artifact
(possibly a wrong badge/number picked up from the page). Treat the star
count specifically as unverified; the architecture description is
corroborated across multiple independent write-ups (Substack, Medium,
aibuilderclub.com), so the project's existence and design are credible even
though the popularity metric is not confirmed.

# Why this is in the radar

Closest real-world open-source analog found to this project's own
curator + skill-lifecycle architecture (`hermes-agent/claude_code_integration/`
in this repo predates and is unrelated to this NousResearch project — the
name overlap is coincidental, not a fork relationship, but worth flagging so
nobody conflates the two in search results or docs). The `MEMORY.md`-nudge +
autonomous-skill-creation-and-self-repair pattern is close enough to this
project's design that a side-by-side comparison could surface concrete
improvements — e.g. their FTS5 cross-session search, or the "skills
self-improve when outdated/wrong" loop.
