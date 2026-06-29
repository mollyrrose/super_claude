---
type: model
title: Claude Opus 4.8
description: Anthropic's current flagship Opus model; the latest in the Opus 4.x line.
tags: [anthropic, claude, opus, flagship]
timestamp: 2026-06-28T00:00:00Z
resource: https://docs.anthropic.com/en/docs/about-claude/models
status: current
supersedes: [models/claude-opus-4-7, models/claude-opus-4-6]
---

# Summary

Claude Opus 4.8 is the current flagship in the Opus 4.x family. Model id
`claude-opus-4-8` (1M-context variant id seen as `claude-opus-4-8[1m]`). It is
the most capable tier for hard judgment work (architecture, design, deep
root-cause, security audit) — the top of the haiku < sonnet < opus ladder.

# Why this is in the radar

The local setup still pins an older Opus in places:

- `~/.claude/CLAUDE.md` "Model Config" sets `model: claude-opus-4-7`.

So when `/qRem` or `/qRev` runs in a project that pins or selects an Opus model,
the radar can surface one line: "config pins claude-opus-4-7; claude-opus-4-8 is
the current flagship — consider updating the pin." This entry exists to
demonstrate the `supersedes` -> "speak up" mechanic against real config.

# Repo / source check

Anthropic models are closed-source (no public GitHub repo to inspect). The
GitHub-inspection intake rule applies to open-source tools/frameworks; for
closed models the grounding source is the official model docs (`resource`) and
the published model id list. Verified against the Anthropic model docs surface.

# Notes

- Verify the exact current flagship id against the docs at scan time — the Opus
  line moves; this entry's `status` must be re-confirmed by `/radar-scan`.
