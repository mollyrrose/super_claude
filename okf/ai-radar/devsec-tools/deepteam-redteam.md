---
type: tool
title: DeepTeam
description: Org-backed open-source LLM/agent red-teaming framework (jailbreak, prompt injection, multi-turn exploitation, PII leakage, 50+ vulnerability types) from the DeepEval team.
tags: [red-team, llm-security, agent-security, python, offensive]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/confident-ai/deepteam
status: current
supersedes: []
adoption: awareness-candidate
---

# Summary

Org-backed (confident-ai, makers of DeepEval) framework for simulating
attacks against LLM apps, RAG pipelines, and agents, runnable via CLI/YAML
or programmatically. Not brand-new (created 2025-03), but shipped a real
update on 2026-08-21 and is actively maintained with a large community.

# Repo / source check

Apache-2.0, 2,764 stars / 446 forks / 64 open issues, org-owned, pushed
2026-08-21, updated at time of check. No red flags; well-documented,
standard OSS governance.

# Why this is in the radar

Fills a gap in this bundle: existing agent/MCP-scanning entries
([mcp-scanner-cisco](/devsec-tools/mcp-scanner-cisco.md),
[snyk-agent-scan](/devsec-tools/snyk-agent-scan.md),
[ai-infra-guard](/devsec-tools/ai-infra-guard.md)) are static/dynamic
*scanners*; DeepTeam is an active *red-teaming/attack-simulation*
framework, the "test your defenses" counterpart. Same dual-use caution
class as [hexstrike-ai](/devsec-tools/hexstrike-ai.md) and
`ai-infra-guard`, but targets LLM-application-level attacks rather than
network/infra pentesting.

# Notes

- `adoption: awareness-candidate` — not yet evaluated hands-on against this
  repo's own MCP/skill surface.
