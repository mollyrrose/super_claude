---
type: tool
title: Claude plugin marketplace repos (official + community)
description: Anthropic's own official and community plugin-directory repos for Claude Code/Cowork, both trending this week on steady organic growth tied to plugin-ecosystem adoption.
tags: [claude-code, plugins, marketplace, anthropic]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/anthropics/claude-plugins-official
status: current
supersedes: []
---

# Summary

Two Anthropic-owned repos surfaced together on GitHub trending:

- **claude-plugins-official** (Apache-2.0, ~3,436 commits, 938 open issues) —
  Anthropic's own curated/vetted directory of Claude Code plugins.
- **claude-plugins-community** (https://github.com/anthropics/claude-plugins-community,
  Apache-2.0, ~2,289 commits) — a read-only mirror of the community plugin
  marketplace for Claude Cowork/Code; submissions go through an external
  portal and an automated security scan before nightly sync.

# Repo / source check

Both alive and legitimate: official Anthropic org repos. `claude-plugins-official`
appeared in both daily (290/day) and weekly (825/week) trending;
`claude-plugins-community` gained +1,759 stars this week — both read as
steady organic growth tied to plugin-ecosystem adoption rather than a single
spike event. Anthropic's own docs note the automated review can't guarantee
every third-party plugin's behavior — a caveat worth carrying into this
repo's own plugin-vetting practice (see the ECC plugin hook-trimming notes
in this repo's CLAUDE.md).

# Why this is in the radar

Direct visibility into the health/growth of the plugin ecosystem this setup
itself participates in (this repo installs plugins like `ecc` and `ruflo`
from adjacent marketplaces). Awareness entry, no action implied.
