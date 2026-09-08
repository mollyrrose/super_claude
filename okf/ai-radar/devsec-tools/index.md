---
type: Index
title: devsec-tools — linters / scanners / supply-chain
description: Developer and security tooling — linters, scanners, supply-chain checks.
tags: [security, linters, supply-chain]
timestamp: 2026-09-08T00:00:00Z
---

# devsec-tools

Linters, scanners, supply-chain and security tooling relevant to the harness.

## Entries

- [mcp-scanner-cisco](/devsec-tools/mcp-scanner-cisco.md) — Cisco vendor-backed MCP server/tool scanner; re-verified active and healthy
- [snyk-agent-scan](/devsec-tools/snyk-agent-scan.md) — scans agents/MCP servers/skills for prompt injection & tool poisoning; re-verified, strong trajectory
- [deepteam-redteam](/devsec-tools/deepteam-redteam.md) — org-backed LLM/agent red-teaming/attack-simulation framework, complements the scanners above
- [ai-infra-guard](/devsec-tools/ai-infra-guard.md) — Tencent red-team platform for agents/MCP/skills; v4.5.2/v4.6.0 shipped (LLM API poisoning detection)
- [api-relay-audit](/devsec-tools/api-relay-audit.md) — audits LLM API relays/proxies for tampering (prompt injection, model substitution); unverified
- [malskanner](/devsec-tools/malskanner.md) — scans repos for hidden prompt-injection payloads before agent ingestion; unverified, stale, do-not-recommend
- [hexstrike-ai](/devsec-tools/hexstrike-ai.md) — offensive MCP pentest framework (awareness; do-not-auto-recommend); re-verified, adoption scale grown to 11.6k stars
- [appsec-toolchain](/devsec-tools/appsec-toolchain.md) — phase->tool matrix (destructive flag) the /pentest engine reads; partially re-verified
- [npm-shai-hulud-scanner](/devsec-tools/npm-shai-hulud-scanner.md) — npm supply-chain worm scanner; unverified, do-not-recommend pending review; unchanged
