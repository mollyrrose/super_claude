---
type: tool
title: Cognee — graph-native agent memory framework
description: Graph-native memory framework for agents; large, active repo. Funding/deployment claims unverified.
tags: [knowledge-graph, agent-memory, open-source]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/topoteretes/cognee
status: current
supersedes: []
---

# Summary

Cognee is a graph-native agent memory framework. Repo confirmed active:
Apache-2.0, ~30.3k stars, 9,790 commits. Secondary sources report a $7.5M
seed round and 70+ production deployments — these funding/adoption figures
were NOT visible on the repo page itself and are unverified.

# Repo / source check

Repo and license verified directly. Funding and deployment-count claims are
unverified (secondary-source only); do not cite them as confirmed.

# Why this is in the radar

Same knowledge-graph-for-agent-memory cluster as
[gbrain](/knowledge/gbrain.md) and [graphiti-zep](/knowledge/graphiti-zep.md)
— complements rather than contradicts either. Landscape awareness only, no
adoption recommendation.

# Notes (2026-08-27 refresh)

Mechanism, made concrete: an ECL (Extract-Cognify-Load) pipeline turns
arbitrary data into a queryable graph combining vector embeddings, graph
reasoning, and ontology generation, with multi-tenant support (per-user/
per-dataset isolation). Cross-linked from the new
[cognition](/cognition/index.md) topic: the multi-tenant, dataset-isolated
design is built for a shared "community-brain" use case specifically, more
so than a single personal memory layer — heavier infra than needed here.
