---
name: radar-add
description: Add a new finding to the AI Radar OKF knowledge bundle. Distill a URL or note into an OKF entry, ALWAYS inspecting the real GitHub repo (skillspector-gated) when one exists, then merge into existing entries and append to the ingest log. Invoked via /radar-add <url|note> (case-insensitive).
---

# radar-add — manual intake into the AI Radar

Distill one source into the AI Radar OKF bundle and merge it in. This is the
MANUAL half of the hybrid intake; the weekly auto half is `/radar-scan`.

Bundle location (source of truth): `D:\projects\super_claude\okf\ai-radar\`.
Live mirror (read by gates): `~/.claude/okf/ai-radar/`. Write to the repo copy,
then sync the changed files to the live mirror (see "Sync" below).

## When to use

User types `/radar-add <url>` or `/radar-add <free-text note>` (any case). Use it
to capture a tool / technique / model / pattern worth remembering.

## Steps

1. **Identify the thing.** From the URL or note, determine: title, kind (`type`:
   tool | technique | model | pattern), and which topic dir it belongs in —
   `harness/`, `models/`, `knowledge/`, `agent-tooling/`, or `devsec-tools/`.

2. **Read the primary source.** WebFetch the URL (or read the note). Pull the real
   claim, not the marketing.

3. **ALWAYS inspect the real GitHub repo (grounding rule).** If the thing has a
   code repo, you MUST inspect the repo itself, not just the article:
   - First run the `skillspector-gate` skill on the repo URL (standing rule in
     `~/.claude/CLAUDE.md`: scan GitHub code before trusting it). URL-form scan
     does NOT clone into the tree. Apply its verdict policy: score 0-39 proceed;
     40-69 proceed with caution + surface findings; 70-100 or any likely-malicious
     / data-exfil / RCE finding -> BLOCK, mark the entry `status: unverified`, end
     with the USER-INPUT banner, and do not recommend it.
   - Read repo signals: README, last-commit / latest-release date (alive or
     abandoned?), open-issue + star trajectory, license, primary language, and
     whether the code actually backs the claim.
   - If the repo contradicts the marketing (dead, unlicensed, claim not in code),
     SAY SO in the entry — that contradiction is the useful signal. Base your
     `description`, `status`, `supersedes`, and any recommendation on the REPO,
     not the hype.
   - An entry not backed by an inspected repo (and not a closed model / pure
     written pattern) is `status: unverified` and never drives a gate "speak up".

4. **Write / merge the entry.** Path `okf/ai-radar/<topic>/<slug>.md`. Frontmatter:
   `type` (required, non-empty), `title`, `description`, `tags`, `timestamp`
   (today, ISO 8601), `resource` (the repo URL when one exists, else primary
   source), `status` (current | superseded | unverified), `supersedes` (list of
   bundle-relative concept ids this replaces, e.g. `[models/old-thing]`).
   Body: structural markdown (headings, tables) — a `# Summary`, a `# Repo /
   source check` note, and `# Why this is in the radar`.
   - If an entry on the same thing already exists, MERGE (update fields, refresh
     `timestamp`, add detail) rather than duplicating. If this finding supersedes
     an existing entry, set the old one's `status: superseded` and point the new
     entry's `supersedes` at it.

5. **Update the indexes + log.**
   - Add/refresh the entry line in the topic `index.md` and the root `index.md`.
   - Prepend one line to `log.md`: `- <date> — added/updated <topic>/<slug>: <one-line>`.

6. **Sync to the live mirror** so the gates can read it:
   `robocopy "D:\projects\super_claude\okf\ai-radar" "%USERPROFILE%\.claude\okf\ai-radar" /MIR` (or copy the changed files). Skip if the live mirror equals the repo.

7. **Report** one line: what was added/merged, its `status`, and any supersede link.

## Notes

- Kill switch for the whole capability: `AI_RADAR_DISABLE=1` silences the gate
  "speak up"; deleting `okf/` removes everything.
- Do NOT commit or push from this skill — writing to disk is enough; committing is
  a separate, user-gated step.
- Honor the no-nagging rule: this skill only runs when the user invokes it.
