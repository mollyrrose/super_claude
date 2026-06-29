---
type: tool
title: HexStrike AI
description: MCP server + autonomous offensive agents orchestrating 150+ pentest tools against LIVE targets — offensive, dynamic, high-caution.
tags: [offensive, pentest, red-team, mcp, ctf, awareness, high-caution]
timestamp: 2026-06-28T00:00:00Z
resource: https://github.com/0x4m4/hexstrike-ai
status: current
supersedes: []
adoption: do-not-auto-recommend
---

# Summary

HexStrike AI is an MCP server (FastMCP, localhost:8888) plus 12+ autonomous
OFFENSIVE agents (BugBounty / CTF / CVE-Intelligence / ExploitGenerator) that
orchestrate 150+ offensive security tools (nmap, rustscan, amass, gobuster, sqlmap,
nuclei, wpscan, ghidra, radare2, gdb, prowler, scout suite, trivy, volatility,
steghide, exiftool, ...). It selects tools, tunes parameters, and chains attacks.

It is **dynamic and offensive**: it attacks LIVE running targets (network services,
web apps, cloud infra) — it does NOT review source code or a diff. v6.0, MIT,
10k+ stars, active development.

# Repo / source check

- Inspected the real repo (not just announcements). Offensive / red-team by design;
  intended for AUTHORIZED pentest, bug-bounty, CTF, red-team only.
- Heavy footprint: 150+ external tools, Chrome/Chromium, a resident service on :8888.
- The project's own docs warn: run in isolated VMs / dedicated security testing
  environments, and "never test systems without permission".
- High caution: widely reported as abused by threat actors in the wild. Treat as a
  dual-use, authorization-gated capability, never an ambient one.
- Pre-trust: a skillspector scan of the repo URL is REQUIRED before any install/use
  (standing scan-before-trust rule). See the AI Radar README intake rule.

# Why this is in the radar

Two reasons, both awareness — NOT a recommendation to wire it into everyday flows:

1. **Defensive threat-intel.** These are the autonomous offensive TTPs (recon ->
   web/app testing -> exploit chaining) that an AI-driven attacker can now run at
   scale. Knowing the shape of this tooling informs the defensive posture.
2. **Correct placement.** It does NOT belong in `/qRev` (static, fast, diff-scoped,
   auto-firing code review) — wrong layer and an autonomy/safety mismatch. If used
   at all, it lives in a separate, manually-invoked, VM-sandboxed,
   authorization-gated pentest skill (`/pentest-hexstrike`), never autonomous,
   never referenced by a hook or by qRev/qRem.

`adoption: do-not-auto-recommend` — `/radar-check` must NEVER surface this as a
"there is something better, adopt it" gate flag; it is an offensive capability, not
a dependency upgrade.
