---
type: tool
title: malskanner
description: CLI/MCP-server/GitHub Action that deterministically scans repo files for hidden prompt-injection payloads before an AI coding agent reads them. Thin adoption, stale since creation.
tags: [prompt-injection, agent-security, npm, typescript, mcp, unverified]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/Octolabo/malskanner
status: unverified
supersedes: []
adoption: do-not-recommend-pending-review
---

# Summary

Deterministic (no-LLM-in-the-loop by default) scanner targeting the class
of attack where malicious instructions are hidden in doc files via
invisible Unicode or encoding tricks, meant to run before Claude
Code/Cursor-style agents ingest a repo. Optional `--ai` flag adds sandboxed
zero-temperature LLM analysis. Claims "0 false positives across 5,620
files" from major OSS projects.

# Repo / source check — unverified

MIT license, created 2026-07-21, essentially no activity since 2026-07-22
(~7 weeks stale as of this scan) — only 5 stars, 0 forks, 0 issues.
`package.json` bin/scripts look normal (standard `tsc` build, `tsx` dev, a
standard test runner) with no suspicious postinstall hooks. Single
unverified author account. Traction is too thin and recent to call this
vetted.

# Why this is in the radar

Direct fit for the "AI code security tool" search seed — addresses a real,
currently-hyped attack class (hidden-instruction files poisoning coding
agents) — but needs another sweep or two to see if it gains real
adoption/maintenance before recommending.

# Notes

- `adoption: do-not-recommend-pending-review` — re-check activity at the
  next scan; a still-stale repo after another sweep is a stronger signal to
  drop this entry rather than keep carrying it.
