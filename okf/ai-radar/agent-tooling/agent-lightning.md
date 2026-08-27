---
type: tool
title: Agent Lightning (Microsoft)
description: RL training framework that decouples agent execution from training via a proxy layer — trains LangChain/AutoGen/OpenAI-SDK/no-framework agents with near-zero code changes.
tags: [microsoft, reinforcement-learning, agent-training, orchestration]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/microsoft/agent-lightning
status: current
supersedes: []
adoption: not-applicable-no-training-loop
---

# Summary

Microsoft's Agent Lightning reached v1.0 (2026-08-17, "completely
refactored" per its changelog). It decouples agent execution from training
via a proxy layer, so agents built on LangChain, AutoGen, the OpenAI Agents
SDK, or no framework at all can be trained (RL, automatic prompt
optimization, SFT) with near-zero code changes. Uses a hierarchical
algorithm ("LightningRL") with credit assignment to decompose multi-agent
trajectories into training transitions. Native Kubernetes job support;
claims backed by a published technical report (arXiv:2508.03680).

# Repo / source check

MIT license, 17.9k stars, 650 commits, v1.0 explicitly framed as a stability
milestone, working docs/quickstart. Verified — mature repo, permissive
license, credible star count and documentation depth.

# Why this is in the radar

This setup does not train models (we use a frozen hosted Claude model via
API — same category mismatch already noted in
[continuous-learning-loop](/knowledge/continuous-learning-loop.md)), so
`adoption: not-applicable-no-training-loop`. Recorded for landscape
awareness: this is the maturing state of the art for "train agents built on
any framework" tooling, useful context if that constraint ever changes.
