---
type: pattern
title: Open Knowledge Format (OKF) v0.1
description: Vendor-neutral spec for agent-ready knowledge — markdown + YAML frontmatter, one required field (type).
tags: [okf, knowledge, google, markdown, agent-memory]
timestamp: 2026-06-28T00:00:00Z
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
and sample bundles (GA4 e-commerce, Stack Overflow, Bitcoin). Spec is v0.1 —
expect changes; re-confirm fields at scan time. This very bundle (`okf/ai-radar/`)
is an OKF bundle, so the format is dog-fooded locally.
