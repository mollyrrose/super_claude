---
type: model
title: GLM-5.3 (Z.ai)
description: Zhipu/Z.ai's GLM-5.3 — a post-training-only upgrade over the GLM-5.2 base, big gains on long-horizon coding tasks.
tags: [glm, zhipu, z.ai, coding, open-weights]
timestamp: 2026-08-27T00:00:00Z
resource: https://www.marktechpost.com/2026/08/14/z-ai-ships-glm-5-3-without-retraining-the-base-model-better-at-complex-coding-and-long-horizon-tasks/
status: current
supersedes: []
---

# Summary

GLM-5.3 released 2026-08-14 by Zhipu/Z.ai. Reuses the GLM-5.2 base model
unchanged (743B params) — all gains come from post-training. Reports a jump
on Terminal-Bench 3.0 from 4.6% to 28.3%, a large improvement on complex,
long-horizon coding/agentic tasks. 1M token context, 128K output. Coding Plan
pricing starts at $18/mo; GLM-5.2/5.1 API requests are auto-routed to 5.3.
Open weights followed ~2026-08-28, alongside a smaller open-weight
"GLM-5.3-Flash" variant released 2026-08-26.

# Why this is in the radar

Not previously tracked in the bundle (no prior GLM entries existed). This
setup has GLM (z.ai) alternate-provider groundwork already (see the global
`~/.claude/CLAUDE.md` "GLM (z.ai)" section and `scripts/claude-glm.ps1`), so a
GLM lineage update is directly relevant to that integration's model choice.

# Repo / source check

Model weights, not a tool repo in the usual sense; open-weights release is
imminent/rolling out as of this scan (~2026-08-28) rather than already
public. Grounding: MarkTechPost and explainx.ai coverage via WebSearch (direct
fetch of marktechpost.com was blocked by this sandbox's egress proxy — this
entry is corroborated via search-aggregated summaries, not a primary fetch).
Marked `current` on the strength of two independent outlet write-ups, not yet
independently verified against an official Z.ai model card.

# Notes

- Confirm open-weight availability and license terms once released
  (~2026-08-28) at the next scan.
