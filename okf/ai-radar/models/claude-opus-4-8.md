---
type: model
title: Claude Opus 4.8
description: Anthropic's former flagship Opus model; superseded by Opus 5 (2026-07-24).
tags: [anthropic, claude, opus, flagship, superseded]
timestamp: 2026-08-27T00:00:00Z
resource: https://docs.anthropic.com/en/docs/about-claude/models
status: superseded
supersedes: [models/claude-opus-4-7, models/claude-opus-4-6]
---

# Summary

Claude Opus 4.8 was Anthropic's flagship in the Opus 4.x family (model id
`claude-opus-4-8`, 1M-context variant `claude-opus-4-8[1m]`). **Superseded
2026-07-24 by [Claude Opus 5](/models/claude-opus-5.md)** (`claude-opus-5`) —
see that entry for current flagship details.

# Why this is in the radar

Kept as a superseded marker so `/qRem`/`/qRev` can flag any config still
pinning `claude-opus-4-8` (or the older `claude-opus-4-7`) and point at
Opus 5 instead. This entry demonstrates the `supersedes` -> "speak up"
mechanic against real config.

# Repo / source check

Anthropic models are closed-source (no public GitHub repo to inspect). The
GitHub-inspection intake rule applies to open-source tools/frameworks; for
closed models the grounding source is the official model docs (`resource`)
and the published model id list.

# Notes

- Re-confirmed superseded 2026-08-27 via `/radar-scan`: WebSearch results
  (MarkTechPost, TechCrunch, Fortune coverage of the 2026-07-24 Opus 5
  launch) cross-checked against the model docs surface — `docs.anthropic.com`
  itself was not directly fetchable from this sandbox (egress-proxy block),
  so this is corroborated via independent search rather than a single-source
  fetch.
