---
type: tool
title: Tencent AI-Infra-Guard — red-teaming platform for agents/MCP/skills
description: Scans agents, Skills, and MCP servers plus LLM jailbreak evaluation, backed by a 2,000+ rule CVE library covering 130 components. Best-verified trending finding this sweep (dated release, named org).
tags: [devsec, red-teaming, mcp-security, tencent]
timestamp: 2026-09-08T00:00:00Z
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

# Update (2026-09-08 scan): v4.5.2 and v4.6.0 shipped

Two releases landed since the last scan: v4.5.2 (2026-08-17) added
Skill-Scan `.pyc` bytecode-bypass detection, charset-smuggling defense, MCP
tool-whitelisting RCE prevention in dynamic mode, and a new "SkillJack"
research sub-project; v4.6.0 (2026-08-26) added LLM API poisoning detection
(multi-probe black-box audit for model substitution/backdoor risk), an
Agent-Scan v5.0.0 mutation-engine refactor, and expanded the vuln library
to 146 AI components / 2,000+ CVE rules. Re-verified directly: org-owned
(Tencent), Apache-2.0, 6,186 stars / 580 forks, pushed the same day as this
scan. Stays `awareness-candidate` (dual-use red-team platform, same caution
class as [hexstrike-ai](/devsec-tools/hexstrike-ai.md)) but this is a
substantive feature update worth surfacing.
