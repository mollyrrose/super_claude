---
type: pattern
title: Appsec / vuln-discovery toolchain matrix (non-destructive)
description: Kill-chain phase to best-in-class open-source tool, each flagged destructive yes/no, for the non-destructive /pentest engine.
tags: [pentest, appsec, sast, dast, sca, toolchain, non-destructive]
timestamp: 2026-06-28T00:00:00Z
resource: https://owasp.org/www-project-web-security-testing-guide/
status: current
supersedes: []
adoption: engine-uses-destructive-no-only
---

# Purpose

The `/pentest` engine reads this matrix and runs ONLY tools flagged
`destructive: no`. Distilled from deep-research + four-model lists (OpenAI / Claude
/ GLM / DeepSeek). Each tool must pass a `skillspector-gate` scan before install
(scan-before-trust). Methodology frame: OWASP WSTG + PTES + MITRE ATT&CK for
ordering/coverage.

# Discovery-safe tools the engine USES (destructive: no)

| Phase | Tool | destructive | Notes |
|-------|------|-------------|-------|
| SAST | semgrep | no | already wired in this repo; primary static engine |
| SAST | bandit / gosec / eslint-security / brakeman | no | language-aware, as the stack dictates |
| SCA | trivy fs, osv-scanner, grype | no | dependency CVEs; file-only |
| SCA | npm/pip/cargo audit | no | only the `audit` subcommand |
| Secrets | gitleaks, trufflehog | no | repo secret scanning |
| IaC | checkov, trivy config, tfsec, kics | no | Docker/k8s/terraform misconfig |
| Recon | nmap -sV (+safe NSE), subfinder, amass, theHarvester, httpx | no | service/asset discovery |
| Web discovery | ffuf, gobuster, feroxbuster, whatweb, katana | no | read-only content/endpoint discovery |
| Vuln scan | nuclei (detection templates), nikto | no | exclude dos/intrusive tags |
| Web scan | OWASP ZAP (spider + passive + SAFE active) | no | safe-active policy only, no write/mutate |
| Web scan | sqlmap (DETECTION mode) | no | flag injectable params; NEVER --dump/--os-shell |
| Cloud posture | ScoutSuite, Prowler | no | read-only config/posture audit |

# Attack-class tools the engine NEVER runs (destructive: yes / awareness only)

`destructive: yes` -> excluded by `pentest_policy.py`. Recorded for awareness:

| Phase | Tool | Why excluded |
|-------|------|--------------|
| Exploitation | Metasploit Framework, nmap exploit NSE | runs real exploits (can crash/alter) |
| C2 / post-exploit | Sliver, Mythic, Havoc, Empire | implants / remote control |
| Cred attack | Hydra, Medusa, Hashcat, John | brute/spray (lockout) / cracking |
| AD attack | Responder, ntlmrelayx, CrackMapExec | poisoning / relay / exec |
| Adversary emu | MITRE Caldera, Infection Monkey | executes attack chains on hosts |
| Wireless | Aircrack-ng, Bettercap, Kismet | deauth / MITM |
| Tunneling | Ligolo-ng, Chisel | pivoting (post-exploit) |
| AI orchestrators | HexStrike AI, Dark Moon, CyberStrike, xOffense, PACDOOR, Strix, Briar, CAI, Nebula, PentAGI | autonomous OFFENSIVE engines; see [hexstrike-ai](/devsec-tools/hexstrike-ai.md). Our orchestration brain is Claude Code itself (lowest-autonomy) |

Note: BloodHound is read-only as a COLLECTOR (AD graph), but its purpose is attack-path
planning; the engine does not use it (out of appsec scope).

# Methodology / sequencing

Order phases per OWASP WSTG (web) and PTES: orient -> static (SAST/SCA/secrets/IaC)
-> recon/enumeration -> non-destructive vuln discovery -> report -> auto-fix +
re-verify. NIST 800-115 for assessment rigor. Map findings to CWE/OWASP Top 10.
