---
type: tool
title: Hive (Aden)
description: Apache-2.0 multi-agent framework that has an LLM generate its own agent topology from a stated goal and evolve it at runtime on repeated failure.
tags: [multi-agent-orchestration, self-organizing-topology, open-source, human-in-the-loop]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/aden-hive/hive
status: unverified
supersedes: []
---

# Summary

Surfaced via a Show HN post from Aden, a YC-backed team. Rather than
requiring developers to hand-wire agent graphs, Hive has an LLM generate the
node graph and connection code directly from a natural-language goal, and
re-generates/evolves that graph when a node fails repeatedly. The README
frames it as a production multi-agent runtime: "Colonies" of Queen + Worker
agents, crash-safe park/resume state persistence, cost enforcement,
real-time observability, a "Sentinel" human-in-the-loop layer wired to
Slack/Telegram, and model-agnostic access to 100+ providers via LiteLLM.

# Repo / source check — unverified

Confirmed via direct GitHub fetch: Apache-2.0, 11k stars, 5.7k forks, 3,377
commits — active development. 922 open issues relative to 11k stars is
worth flagging as a maturity signal (could mean healthy engagement or a
maintenance backlog outpacing the team; issue age wasn't checked). The
"production reliability" framing is the project's own claim, not
independently benchmarked. `news.ycombinator.com` was blocked by this
sandbox's egress proxy, so the original Show HN thread's reception is
unconfirmed.

# Why this is in the radar

A distinct pattern from every other framework in this bundle — dynamic,
LLM-generated topology instead of a fixed graph (LangGraph-style) or fixed
roles (CrewAI-style) — complementary to
[nooa](/agent-tooling/nooa.md) and [deepagents](/agent-tooling/deepagents.md)
as a third distinct orchestration philosophy.

# Notes

- Re-check the open-issue count/age at the next scan to see whether it's a
  fast-growing healthy project or accumulating maintenance debt.
