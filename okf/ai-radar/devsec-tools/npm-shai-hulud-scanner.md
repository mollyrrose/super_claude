---
type: tool
title: npm-shai-hulud-scanner (Drasrax)
description: Detects npm/PyPI packages compromised by the Shai-Hulud worm family — detailed detection logic, but thin adoption signals.
tags: [npm, supply-chain, scanner, unverified]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/Drasrax/npm-shai-hulud-scanner
status: unverified
supersedes: []
adoption: do-not-recommend-pending-review
---

# Summary

Detects packages compromised by the Shai-Hulud npm worm family (tracks
7,965 compromised versions across 3,693 npm + 103 PyPI packages, 514 malware
hashes; typosquat/Levenshtein checks; C2-pattern detection including
blockchain-based C2). Built in response to the ~2026-08-04 Keyv/cacheable npm
supply-chain compromise (a maintainer-account takeover that pushed a
credential-stealing preinstall hook across 1,300+ package versions, ~2B
monthly downloads affected — see Wiz and Microsoft's incident writeups).

# Repo / source check — unverified

MIT license, but only 15 stars / 4 forks / 13 commits — a single small repo
with thin adoption signals. The detection logic looks detailed and
cross-references legitimate feeds (OSV, OSSF malicious-packages feed,
JFrog/Wiz/Socket/Microsoft/Snyk reports) and documents false-positive testing
against 44 legit packages, but low star/commit/contributor count means
maintainer trustworthiness cannot be confirmed, and — per the AI Radar
grounding rule — a claim not backed by independently-verifiable repo signals
must be marked `status: unverified`. No skillspector or equivalent scanner
was available in this sandbox to do a deeper trust check.

# Why this is in the radar

The underlying incident (Shai-Hulud / "ChainDrop") is a real and significant
npm supply-chain compromise worth being aware of; this specific scanner is
recorded as a candidate response, explicitly NOT recommended, pending a
proper review (ideally a skillspector-gate scan) before any adoption.

# Notes

- `status: unverified`, `adoption: do-not-recommend-pending-review` —
  `/radar-check` must never surface this as an adopt-it recommendation.
