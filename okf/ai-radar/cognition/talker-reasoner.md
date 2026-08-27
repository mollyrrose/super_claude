---
type: pattern
title: Talker-Reasoner — foundational dual-process agent architecture
description: Google DeepMind design paper splitting an agent into a fast "Talker" (System-1) and a slower deliberate "Reasoner" (System-2); the most-cited fast/slow agent architecture underlying 2026 dual-process memory work.
tags: [dual-process, system1-system2, cognitive-architecture, deepmind]
timestamp: 2026-08-27T00:00:00Z
resource: https://arxiv.org/abs/2410.08328
status: current
supersedes: []
---

# Summary

Talker-Reasoner (Christakopoulou, Mourad, Matarić — DeepMind, October 2024)
splits an agent into a "Talker" (System-1 analog: fast, fluent conversational
responses) and a "Reasoner" (System-2 analog: slower, deliberate
planning/tool-use/multi-step reasoning), so the agent stays responsive while
a slower process can intervene on complex decisions. Demonstrated on a
sleep-coaching agent use case. Older than this radar's usual freshness
window, included as foundational: it is the paper most 2026 dual-process
agent-memory work (see
[dual-process-graph-memory-research-2026](/cognition/dual-process-graph-memory-research-2026.md))
cites as its architectural ancestor.

# Repo / source check

No official code repo — this is a design paper, not a shipped project. No
repo-legitimacy check applies.

# Why this is in the radar

Not directly adoptable as code, but conceptually validates a pattern this
project already implements structurally: fast per-turn
`UserPromptSubmit`/`PostToolUse` hooks via the consolidated dispatcher
(`scripts/hook_dispatch.py`) act as the "Talker" layer, while the slower,
deliberate `/qRev` full-review pass acts as the "Reasoner" layer. Useful as a
citation/frame for that existing design choice rather than something to
build from scratch.
