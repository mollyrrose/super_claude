---
type: model
title: Claude Sonnet 5
description: Anthropic's mid-tier model; approaches Opus 4.8-level performance at much lower, now-permanent pricing.
tags: [anthropic, claude, sonnet, mid-tier]
timestamp: 2026-08-27T00:00:00Z
resource: https://www.anthropic.com/news/claude-sonnet-5
status: current
supersedes: []
---

# Summary

Claude Sonnet 5 (model id `claude-sonnet-5`) launched 2026-06-30. 1M token
context, 128K max output, adaptive thinking on by default. Launch pricing of
$2/$10 per MTok (input/output) was introductory through 2026-08-31; on
2026-08-10 Anthropic announced it will NOT proceed with the planned hike to
$3/$15 on 2026-09-01, making $2/$10 the permanent rate. Performance approaches
Opus 4.8 at a fraction of the cost, aimed at cheaper agentic workloads.

# Why this is in the radar

This session itself runs on `claude-sonnet-5` (per the environment's model
identity). No existing bundle entry tracked the Sonnet line before this scan;
recorded here as a new current entry rather than a supersession, since the
bundle had no prior `models/claude-sonnet-4-*` entry to supersede.

# Repo / source check

Closed-source model, no GitHub repo to inspect. Grounding: official Anthropic
announcement (`resource`), cross-checked via independent WebSearch against
TechCrunch, Qz, BigGo Finance, and explainx.ai coverage of both the
2026-06-30 launch and the 2026-08-10 permanent-pricing announcement (direct
fetch of anthropic.com/docs.anthropic.com was blocked by this sandbox's
egress proxy).

# Notes

- Re-verify pricing/context at the next scan in case of further changes.
