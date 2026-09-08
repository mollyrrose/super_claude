---
type: pattern
title: Star-count / commit-depth mismatch across trending "agent skill pack" repos
description: An unusual cluster of Claude-Code/Codex "skill pack" repos this week show 130k-280k stars against 200-700 commits and low-profile single maintainers — genuine viral moment or star-gaming is unresolved.
tags: [github-trending, skills, unverified, awareness, lint]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/trending
status: unverified
supersedes: []
---

# Summary

This week's GitHub-trending sweep surfaced an unusually consistent pattern:
several "AI agent skill" repos show very high total star counts paired with
thin commit histories and a single, low-profile maintainer —
`obra/superpowers` (283k stars / 681 commits), `mattpocock/skills` (257k
stars / 459 commits), `DietrichGebert/ponytail` (132k stars / 222 commits),
`tt-a1i/archify` (54k stars / 236 commits, anonymous author), and
`blader/humanizer` (45k stars / 75 commits) all show the same shape. Two of
these (`ponytail`, `archify`) posted the two largest single-week star gains
of anything AI-related in this sweep (+12,834 and +14,946 respectively).

# Repo / source check — unverified

This pattern recurs across unrelated authors, which reads either as (a) a
genuine September-2026 zeitgeist around Claude Code/Codex skill packs
pushing organic virality far beyond normal curves, or (b) coordinated
star-gaming/bot amplification of the trending algorithm. This sweep could
not resolve which — that needs a star-history.com pull or the GitHub API's
`/stargazers` timestamps, neither of which WebFetch-based trending-page
summarization can give reliably. Where an author has independent public
reputation (`obra/superpowers` — Jesse Vincent; `mattpocock/skills` — a
well-known TypeScript educator; `cathrynlavery/diagram-design` — identified
founder), the code/functionality itself looks legitimate even if the growth
curve is unconfirmed; the two most extreme mismatches
(`ponytail`, `archify`) have unknown/anonymous authors and are the ones
most worth an independent check before citing their popularity anywhere.

# Why this is in the radar

This is a lint-relevant finding about the trending-repo signal itself, not
a recommendation for or against any one of these tools: treat "trending
Claude Code skill pack" star counts as unverified until independently
confirmed, and prefer commit depth / issue engagement / author reputation
over raw star count when judging real adoption. Recorded as one entry
rather than five near-duplicate ones per the bundle's dedup convention.

# Notes

- Repos in scope: `obra/superpowers`, `mattpocock/skills`,
  `DietrichGebert/ponytail`, `tt-a1i/archify`, `blader/humanizer`,
  `cathrynlavery/diagram-design` (smaller mismatch, identified author).
- Re-check star trajectories at the next scan (ideally via the GitHub API
  rather than WebFetch) to see whether the growth curves normalize or keep
  compounding.
