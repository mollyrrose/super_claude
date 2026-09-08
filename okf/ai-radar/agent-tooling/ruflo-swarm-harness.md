---
type: tool
title: ruvnet/ruflo — swarm agent meta-harness
description: Multi-agent swarm/orchestration meta-harness with adaptive memory and RAG-backed workflows, native Claude/GPT/Gemini/local-model integration. Already installed and hands-on patched in this project.
tags: [multi-agent, swarm, mcp, rag, github-trending]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/ruvnet/ruflo
status: current
supersedes: []
---

# Summary

Surfaced via GitHub trending (weekly-overall, daily-TS, weekly-TS — 3 of 6
views checked). Recent driver: a new web UI beta (flo.ruv.io) plus a
goal-planning interface. MIT license, 7,415 commits (deep history,
consistent with its ~71.6k star count), 656 issues / 295 open PRs — an
active community, not a stars-only spike.

# Repo / source check

Corroborated out-of-band: this project's own CLAUDE.md documents a hands-on
patch to `ruflo-hook.cjs` for a real cmd.exe argument-quoting bug (stray
numeric files appearing in a project root from an unquoted `-c` argument on
Windows), confirming the plugin is genuinely installed and used here, not
just a trending-page artifact. Commit depth relative to star count is one of
the more credible ratios seen in this sweep's trending pull (compare the
star-inflation pattern flagged in
[trending-skillpack-star-inflation-pattern](/agent-tooling/trending-skillpack-star-inflation-pattern.md)).

# Why this is in the radar

Already a live dependency of this repo's own tooling (see the project
CLAUDE.md's "Ruflo plugin hook shim patched" section) — tracking its
upstream trajectory directly matters for whether the local patch needs
re-applying after an update.
