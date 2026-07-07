# Second Brain — super_claude memory fabric

Status: finalized 2026-07-07 alongside `AI_OS_STRATEGY.md` (this is that doc's Section 8, expanded into a standalone design). Companion to `AI_OS_STRATEGY.md` (substrate layer S2) and `FABLE5_LEGACY.md`.

## Thesis (read this first)

The Second Brain is NOT a new store. super_claude already has nine persistent stores; the failure mode is that they are scattered, some have no reader, and the same learning can land in two places. The Second Brain is the CONNECTIVE TISSUE over those stores plus TELOS as its spine, governed by ONE invariant:

> A LEARNING LIVES IN EXACTLY ONE STORE. Links, not copies.

Everything below is either an existing store (kept, named, given a reader) or the thin new glue (`brain_query.py` + the Learning Router) that makes the whole thing queryable. Per the project's "lowest autonomy that works" and "eliminate before automating" rules, we add the least glue that turns nine stores into one brain.

## The stores (what already exists — none is replaced)

| Store | Path | Role | Writer | Reader(s) today |
|---|---|---|---|---|
| File-based memory | `~/.claude/projects/.../memory/*.md` | durable user/feedback/project/reference facts | Write tool (curation) | MEMORY.md index, qRem |
| Memory index | `memory/MEMORY.md` | one-line pointer per memory | curation | every session (loaded) |
| Decision log | `~/.claude/.decision_log.jsonl` | decisions + rationale + revisit_if + outcome | decision_log_cli.py | (GAP: no query -> brain_query) |
| Router eval stream | `~/.claude/.smart_router_eval.jsonl` | prompt features -> suggestion vs actual | smart_router hook | (GAP: predictor-only -> brain_query) |
| qRev verdict stream | `~/.claude/.qrev_verdict_log.jsonl` | review kind -> P0-P3 + fix/skip counts | qrev_mark_done.py | (GAP -> brain_query) |
| Curator queue | `~/.claude/.hermes_curator_queue.json` | sessions awaiting skill extraction | curator stop hook | curator prompt hook |
| Coord board | `~/.claude/.coord/<repo-key>/` | live cross-window state | coord.py | coord prompt hook |
| Radar bundle | `~/.claude/okf/ai-radar/` | superseded-tool freshness | radar-add/scan | qRem, qRev |
| ISA files (new, gated) | `<project>/exclude/SYSTEM_STRATEGIES/isa/<slug>.md` | per-task done-state | /aios kernel | /aios, qRev |
| TELOS (new, gated) | `memory/TELOS.md` | user identity/mission spine | qUpd, curation | qRem, proactive block |

The three JSONL streams were built data-first (accumulate now, learn later). The Second Brain's first job is to give them a READER so they stop being write-only.

## CODE map (Capture -> Organize -> Distill -> Express)

- **Capture** (write): memory-dir writes; `decision_log_cli.py`; curator queue enqueue; ISA changelog entries; TELOS section updates. Each has exactly one writer path.
- **Organize** (structure): `MEMORY.md` index + TELOS sections (with per-section HTML staleness markers) + per-project `exclude/SYSTEM_STRATEGIES/`. These are existing conventions, now named as one system.
- **Distill** (compress to reusable): `hermes-curate` (session patterns -> `hermes-auto-*` skills); `rev-learn` (accepted review findings -> semgrep candidate rules); and the NEW **Learning Router** — the classifier that decides each learning's ONE canonical home.
- **Express** (surface on demand): qRem orientation; `brain_query.py` CLI; the statusline; the qRem PROACTIVE block.

## The Learning Router (the only genuinely new judgment component)

Every candidate learning at LEARN time is classified into exactly one type and routed to exactly one surface:

| Type | Canonical surface |
|---|---|
| knowledge (a durable fact about the user/world/project) | file-based memory dir + MEMORY.md pointer |
| rule (how the assistant should behave) | CLAUDE.md — constitutional block if non-overridable, else plain rule |
| gotcha (a recurring code/tooling trap) | semgrep candidate rule (via rev-learn) |
| state (current project status/next-task) | `exclude/SYSTEM_STRATEGIES/TODO.md` or the ISA file |
| doctrine (a distilled reusable method) | a skill under `~/.claude/skills/` (via create-skill / curate) |
| hook (something that should fire automatically) | a settings.json hook (deterministic; only when a manual step proved it) |

Invariant enforcement: before writing, the router checks the other surfaces for a semantic duplicate; if found, it LINKS (`[[name]]` / a path reference) instead of copying. **All-or-nothing:** the router is either fully wired or not used at all — it must never half-migrate stores (a partial router would double-store or drop learnings). Until fully wired, learnings keep going to today's surfaces unchanged.

## Query layer — `scripts/brain_query.py`

Deterministic, stdlib-only, READ-ONLY. No LLM. Closes gaps #1 and #10 (no query layer, no trend view). Subcommands:

```
brain_query.py decisions [--reversed | --open | --since <date>]   # decision-log slices
brain_query.py router [--misses]                                  # router prediction vs actual
brain_query.py verdicts [--trend]                                 # qRev P0-P3 counts over time
brain_query.py facts <topic>                                      # memory-dir grep by topic
brain_query.py stale [--telos | --memory]                         # staleness-marker scan
brain_query.py health                                             # counts + trends across all streams
```

**Data-sufficiency gate (build-order rule):** before building any subcommand, run the row-count one-liner over the three JSONL streams. A subcommand whose stream has <20 rows is not worth building yet — do not build a query tool for empty data. `health` always works (it just reports the counts).

Kill switch: it is read-only and standalone; delete the file and every store behaves exactly as today.

## Integrity rules

1. Every store has exactly one writer path and at least one reader. (Adding `brain_query` gives the three orphan streams a reader.)
2. A monthly stale-marker scan runs via the existing `/ecc:harness-audit` self-audit — no new cron.
3. No store without a kill switch.
4. The Learning Router's one-store invariant is checked at write time, not after.

## What this deliberately is NOT

- Not a vector database (ruvector.db stays ARCHIVED unless the deterministic 208-skill taxonomy proves insufficient — see strategy Section 11).
- Not codebase-memory-mcp (that is a SEPARATE, gated, structural-code-graph store — strategy S4 — orthogonal to this learning/fact fabric; it never blocks this).
- Not a web dashboard (the "trend view" is `brain_query health` printing text; LifeOS Pulse is skipped).
- Not a daemon (nothing polls; qRem/qUpd read on their normal cadence).

## Build order (from the strategy roadmap)

1. Phase 1 [LEAST-OS]: `brain_query.py` + smoketest, after the data-sufficiency one-liner passes. This alone delivers the Second Brain's core value (a reader over the orphan streams).
2. Phase 3 [GATED]: TELOS.md + staleness markers + the Learning Router (all-or-nothing), only if a felt-pain trigger fires.
3. Phase 4 [GATED]: finalize this document against what actually got built; wire the stale-marker scan into the self-audit.

The Second Brain earns its place at Phase 1 with one read-only script. Everything past that is opt-in.
