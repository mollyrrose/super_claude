---
type: Log
title: AI Radar — ingest log
description: Append-only timeline of ingests and changes to the AI Radar bundle.
timestamp: 2026-06-28T00:00:00Z
---

# Ingest log

Newest first. Each line: date — what changed.

- 2026-08-27 — Weekly radar-scan (cloud sandbox, 5 parallel research agents,
  one per topic). **harness**: added claude-code-aug2026-updates (subagent
  forking on by default + cross-session messaging + rolling MCP/hook
  reliability pass v2.1.232-2.1.247 + SendFeedback tool), deepseek-harness
  (competing plugin-only agent harness, awareness), mcp-2026-07-28-spec
  (MCP "stateless core" revision). **models**: claude-opus-4-8 marked
  superseded — Claude Opus 5 shipped 2026-07-24 and is the current flagship;
  added claude-opus-5, claude-sonnet-5 (permanent $2/$10 pricing as of
  2026-08-10), glm-5-3, gemini-3-7-flash, gpt-5-6 (first GPT/Gemini/GLM
  entries in the bundle). **knowledge**: open-knowledge-format updated to
  note OKF v0.2 (2026-07-25, two breaking field renames, not auto-migrated
  here); added anthropic-dreaming-memory (first-party validation of
  continuous-learning-loop's direction), gbrain (production-scale
  compounding-wiki reference impl), graphiti-zep, cognee (knowledge-graph
  memory cluster), mem0-agent-memory-benchmark-2026 (unverified — primary
  source blocked by sandbox egress proxy). **agent-tooling**: added
  agent-lightning (Microsoft RL training framework; not-applicable, no
  training loop here) and nooa (NVIDIA object-oriented agents; promising but
  pre-1.0 research-alpha, no scanner available to verify sandboxing safety).
  **devsec-tools**: added mcp-scanner-cisco and snyk-agent-scan (both
  awareness-candidate defensive MCP/skill scanners) and
  npm-shai-hulud-scanner (unverified, do-not-recommend — 15 stars/4
  forks/13 commits, flagged pending proper review). Lint pass: no
  contradictions found; flagged appsec-toolchain and hexstrike-ai as ~60
  days old against devsec-tools' ~30-day freshness window (re-verification
  noted, status unchanged, judgmental call left unmade); added missing
  cross-links (continuous-learning-loop <-> anthropic-dreaming-memory,
  llm-wiki-compounding <-> gbrain); no orphans after refreshing all 5 topic
  indexes + top-level index. Coverage gaps (be honest): no YouTube/arXiv
  tooling available in this sandbox (two arXiv agent-memory/agent-tooling
  papers noted by a research agent were not turned into entries — no repo,
  abstract-only, deferred); several primary sources were blocked by the
  sandbox's network egress proxy (claude.com, docs.anthropic.com,
  marktechpost.com, mem0.ai, arxiv.org, ai.google.dev direct-fetch) — those
  findings are corroborated via independent WebSearch-aggregated sources
  instead of a single primary fetch, and are flagged as such in each entry;
  two devsec-tools MCP-scanner candidates (getjavelin/ramparts, "ScanMCP")
  were surfaced but not repo-checked, deferred to next scan.
- 2026-07-02 — Headroom follow-through: synced the 2026-06-29 manual-audit text
  from the live copy into the repo entry (agent-tooling/headroom), then ported
  the audited compression logic into `scripts/tokenjuice_condense.py`
  (stdlib-only; JSON schema preservation, code signature fallback, log
  error/trace selection, entropy secret preservation, fallback detector) and
  wired it into tokenjuice as the `condense` strategy + `--condense` flag.
  Package itself stays do-not-install (proxy/plugin/daemon layer rejected).
- 2026-06-29 — Token/memory-optimization assessment: added knowledge/prompt-caching
  (narrow applicability — harness already caches the main session; our critic prefix
  is sub-minimum), knowledge/attention-residuals (model-architecture, not-applicable),
  knowledge/continuous-learning-loop (Sona/RuVector — validates direction, no build),
  agent-tooling/headroom (context compressor; skillspector BLOCKED score 100,
  do-not-install — manual file-by-file audit deferred per context). Finding: qRev
  fleet has no per-lens model tiering (all judgment reviewers at session model).
- 2026-06-28 — Added devsec-tools/hexstrike-ai (awareness entry, do-not-auto-recommend):
  offensive MCP pentest framework. Decision: NOT wired into qRev (wrong layer +
  autonomy/safety mismatch); awareness via radar + a separate gated `/pentest-hexstrike`
  skill instead. Re-applied the qRev "Radar gate" section (a prior Write had failed).
- 2026-06-28 — Phase 2: added `/radar-scan` (web + YouTube keyword-search &
  transcript + arXiv multi-modal sweep) and the lint pass (contradictions, stale,
  orphans, missing links). Installed `youtube-transcript-api`; yt-dlp keyword
  search verified working. GitHub-repo inspection (skillspector-gated) applies to
  scan findings too.
- 2026-06-28 — Bundle created (phase 1). Seeded: models/claude-opus-4-8,
  knowledge/open-knowledge-format, knowledge/llm-wiki-compounding. Added topic
  indexes for harness, models, knowledge, agent-tooling, devsec-tools. Intake
  rule added: always inspect the real GitHub repo (skillspector-gated) before
  trusting a new thing.
