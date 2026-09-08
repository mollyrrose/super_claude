---
type: model
title: Meta Muse Glimmer
description: Meta's return to open-weight releases — a 30B-param, Apache-2.0 agentic model built to run locally on one consumer GPU.
tags: [meta, open-weight, agentic, on-device, release, apache-2.0]
timestamp: 2026-09-08T00:00:00Z
resource: https://venturebeat.com/technology/meta-returns-to-open-source-with-muse-glimmer-an-apache-2-0-licensed-30b-parameter-ai-model-optimized-for-agents-available-now
status: unverified
supersedes: []
---

# Summary

Released 2026-08-10 by Meta Superintelligence Labs — a 30B-parameter,
Apache-2.0-licensed open-weight model, Meta's first open-weight
frontier-adjacent release since the proprietary "Muse Spark" model earlier
in 2026 (which itself broke from the Llama lineage). 131,072-token context.
Headline claim is full local agentic capability (planning, tool calls,
multi-step reasoning, self-checking, failure recovery) on a single
24-32GB consumer GPU or Mac unified-memory system, quantized to ~4-bit
(under 20GB). Includes a 1.8B vision encoder and ~100-language support.
Reported to lead its size class on MCP-Atlas (75.5) and DeepSearch QA
(74.6) but trails Qwen3.6-27B on OSWorld-Verified and Terminal-Bench 2.1.

# Repo / source check — unverified

Open-weight — a Hugging Face model card should exist per secondary sources
(InfoQ, VentureBeat, DataCamp), but this pass did not directly fetch it to
confirm license text, file listing, or upload date. Marked `unverified`
pending that check, per the bundle's grounding rule.

# Why this is in the radar

Meta/Llama is otherwise untracked in this bundle; this is Meta's first
notable open-weight release in the sweep window and a genuine on-device/
local-agent alternative to closed frontier models.

# Notes

- Fetch the Hugging Face repo directly at the next scan to confirm license
  and promote out of `unverified`.
