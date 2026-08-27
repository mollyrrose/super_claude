---
type: tool
title: Cisco mcp-scanner
description: Vendor-backed scanner for MCP servers/tools — threat inspection via YARA rules, LLM-based analysis, and a sandboxed package scanner.
tags: [mcp, security, scanner, supply-chain, cisco]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/cisco-ai-defense/mcp-scanner
status: current
supersedes: []
adoption: awareness-candidate
---

# Summary

Cisco AI Defense's `mcp-scanner` scans MCP servers/tools for threats using an
inspect API, YARA rules, and LLM-based analysis. Releases v4.8.0 (2026-07-14)
through v4.8.3 (2026-08-07) added a Docker-sandboxed PyPI/npm package scanner
with behavioral analysis (v4.8.0) and dynamic tool-registration detection
(v4.8.3).

# Why this is in the radar

Directly relevant to this setup's MCP surface (multiple MCP servers wired
into Claude Code sessions). A defensive, non-dual-use scanner — worth
evaluating as a periodic check on MCP servers before trusting them, parallel
to the existing skillspector-gate discipline for GitHub repos.

# Repo / source check

Backed by Cisco's named AI Defense org, active weekly release cadence,
changelog discipline (dependency bumps, config fixes) consistent with a real
engineering team. License/star count not independently confirmed beyond
release-cadence signals in this pass — treat as verified-by-vendor-identity
rather than fully independently audited.

# Notes

- `adoption: awareness-candidate` — a plausible addition to the appsec
  toolchain, not yet formally evaluated against
  [appsec-toolchain](/devsec-tools/appsec-toolchain.md)'s
  `destructive: no` bar. Needs a deliberate look before wiring in.
