---
type: tool
title: Tencent AI-Infra-Guard — red-teaming platform for agents/MCP/skills
description: Scans agents, Skills, and MCP servers plus LLM jailbreak evaluation, backed by a 2,000+ rule CVE library covering 130 components. Best-verified trending finding this sweep (dated release, named org).
tags: [devsec, red-teaming, mcp-security, tencent]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/Tencent/AI-Infra-Guard
status: current
supersedes: []
adoption: awareness-candidate
---

# Summary

AI-Infra-Guard is a red-teaming platform from Tencent's Zhuque Lab: scans
agents, Skills, and MCP servers plus AI infra, plus LLM jailbreak evaluation,
backed by a 2,000+ rule CVE library covering 130 components. Apache-2.0.

# Repo / source check

Alive and legitimate — large corporate security-lab org, dated v4.6.0
release (2026-08-26, one day before this sweep) adding API-relay-abuse
detection, multi-turn jailbreak attacks, and a skills-marketplace scan
feature; also cites a Black Hat Europe 2025 conference appearance. Surfaced
via GitHub trending (+1,267 stars this week). Best-verified entry from this
week's trending sweep: concrete dated release plus a named, checkable org,
unlike several of the self-reported-benchmark entries elsewhere in this
sweep.

# Why this is in the radar

Same defensive-scanner category as
[mcp-scanner-cisco](/devsec-tools/mcp-scanner-cisco.md) and
[snyk-agent-scan](/devsec-tools/snyk-agent-scan.md) — a skills-marketplace
scan feature is directly relevant to this repo's own plugin-vetting concerns
(the ECC plugin hook-trimming notes in this repo's CLAUDE.md). Awareness
candidate, not yet evaluated hands-on.
