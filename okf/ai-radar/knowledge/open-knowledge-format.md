---
type: pattern
title: Open Knowledge Format (OKF) v0.1 -> v0.2
description: Vendor-neutral spec for agent-ready knowledge — markdown + YAML frontmatter, one required field (type). v0.2 (2026-07-25) added provenance/trust/lifecycle fields with two breaking renames.
tags: [okf, knowledge, google, markdown, agent-memory]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
status: current
supersedes: []
---

# What it is

A directory of markdown files with YAML frontmatter. No schema registry, no
central authority, no required tooling. "If you can `cat` a file you can read
OKF; if you can `git clone` a repo you can ship it."

# Frontmatter

| Field | Req? | Meaning |
|-------|------|---------|
| `type` | required | descriptive classifier (e.g. "BigQuery Table", "Playbook") |
| `title` | recommended | human display name |
| `description` | recommended | one-sentence summary |
| `resource` | recommended | URI of the underlying asset |
| `tags` | recommended | YAML list, cross-cutting categorization |
| `timestamp` | recommended | ISO 8601 last-modified |

Reserved files: `index.md` (catalog), `log.md` (history). Concept id = file path
minus `.md`. Cross-link with bundle-relative `/path/concept.md` or `./other.md`.

# Conformance

Consumers MUST tolerate missing optional fields, unknown `type` values, and
broken cross-links. Only hard rule: parseable frontmatter + non-empty `type` in
every non-reserved `.md` file.

# How it differs from RAG

RAG re-searches the same documents on every query. OKF is a living wiki that
agents read AND update — pre-structured relationships, versioned like code,
citations embedded (less hallucination), self-maintaining. See
[llm-wiki-compounding](/knowledge/llm-wiki-compounding.md).

# Repo / source check

Reference impl in the Google Cloud `knowledge-catalog` repo: an enrichment agent
(walks BigQuery, drafts OKF docs), a static HTML graph visualizer (no backend),
and sample bundles (GA4 e-commerce, Stack Overflow, Bitcoin). This very bundle
(`okf/ai-radar/`) is an OKF bundle, so the format is dog-fooded locally.

# Update (2026-08-27 scan): v0.2 released 2026-07-25

Confirmed directly via WebFetch of the spec file: the "Version" line reads
0.2 and a "Changes from v0.1" section lists two BREAKING renames plus new
optional field families:

- `timestamp` -> `generated.at` (breaking)
- body citations -> frontmatter `sources` field (breaking)
- new optional fields: provenance, trust (`generated`/`verified` blocks),
  lifecycle (`status`, `stale_after`), attested computation

`type` remains the only required field — this bundle's existing entries
(which use `timestamp`, `resource`, `status`, `supersedes` per v0.1) remain
valid OKF documents since v0.2 kept those as backward-compatible optional
fields per the conformance rule (consumers must tolerate missing/renamed
optional fields). No v0.3 found as of this scan.

**Flagged, not auto-applied:** migrating this bundle's ~20 entries to the
v0.2 field names (`generated.at`, `sources`) is a deliberate schema
migration, not a lint-safe fix — left for a dedicated pass rather than
applied here.
