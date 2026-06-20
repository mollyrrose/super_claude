---
name: qRev-project
description: Whole-project, context-safe deep review — maps the ENTIRE useful codebase subsystem-by-subsystem via delegated subagents (map-reduce, the repo is never loaded into one context), running qRev's full agent roster on each subsystem at whole-file + full-context depth, and writes a persistent architecture map PLUS an aggregated P0/P1/P2/P3 review punch-list. This is qRev's project-wide sibling: `/qRev` reviews the uncommitted diff; `/qRev project` reviews the whole repo. Invoked via `/qRev project` (canonical) or `/qRev-project`, and any case variant (/qrev project, /QRev-project, ...). If the user types any of these, proceed with this skill.
---

# qRev-project — whole-project deep review (map-reduce + full qRev roster)

**Case-insensitive invocation:** `/qRev project`, `/qrev project`, `/qRev-project`,
`/QRev project`, etc. are all this skill. The trailing `project` keyword on a
`/qRev` call routes here; so does the standalone `/qRev-project`.

## What this is (and is NOT)

- `/qRev` (no `project`) reviews the **uncommitted diff** — what you're about to commit.
- `/qRev project` reviews the **whole project's useful code**, subsystem by subsystem,
  in a **context-safe map-reduce** way, and produces TWO durable artifacts:
  1. a **persistent architecture map** under `docs/architecture/`, and
  2. an **aggregated review punch-list** (P0–P3) under
     `exclude/SYSTEM_STRATEGIES/qrev-project/`.

Use it for: onboarding a large/unfamiliar repo, a pre-release whole-repo audit, a
periodic systematic sweep. For per-commit checks use `/qMin` or `/qRev`; for a
recent-history slice use `/rev exhaustive`.

## HARD RULE — the repo is never loaded into one context

This is the core of the skill. The whole repo must NEVER sit in one context window.
Each subsystem is explored by a **delegated subagent** that reads its files in its
OWN context and returns only a distilled summary. The main thread only writes those
summaries to disk. The final synthesis (reduce) reads ONLY the on-disk summaries —
never the source again. This is what lets a huge / monorepo be reviewed without
overflow. Violating it (pulling raw subsystem source into the main thread) defeats
the skill.

## Scale note (read before launching)

The default depth runs qRev's **full exhaustive roster per subsystem** (~12–15
agents × 3 passes, scoped to that subsystem's files). Across N subsystems that is a
large fleet — but each agent's context is bounded to one subsystem, which is the
point. Cost is covered by the active subscription (no per-token bill); the cost is
wall-clock. If the user wants it lighter, honor:
- `/qRev project fast` — Phase A (semgrep + standards) only per subsystem, no fleet.
- `/qRev project topic:<name>` — full depth but only the topic's lens per subsystem
  (security / db / perf / ml / tests), per `/rev`'s topic table.
State the chosen depth and the rough subsystem count in one line before starting.

## 0. Setup

1. Verify a git repo: `git rev-parse --show-toplevel`. If not a repo, stop and say so.
2. `mkdir -p docs/architecture` and `mkdir -p exclude/SYSTEM_STRATEGIES/qrev-project`
   (ensure `exclude/` is in `.gitignore` — add it if missing; that is a standing rule).
3. Let **PREFIX** be the common label prefix (default `PROJ`; use `PA` if the repo is
   PrivateAssociations — detect via INDEX.md / README / repo name).

## 1. Select the USEFUL code — prune the rest

The scope is "useful code folders and files", NOT everything. Build the candidate
file list cheaply and deterministically:

- Primary source of truth: `git ls-files` (already excludes everything gitignored —
  `node_modules/`, `dist/`, `build/`, `.next/`, `exclude/`, lockfiles in some repos,
  etc.). Prefer this over `find`.
- Then drop files that are not meaningful to review even if tracked. Skip by path /
  extension (non-exhaustive; adapt per repo):
  - vendored / generated: `vendor/`, `third_party/`, `generated/`, `*.min.js`,
    `*.bundle.js`, `*_pb2.py`, `*.g.dart`, snapshots, `*.lock`, `package-lock.json`,
    `poetry.lock`, `yarn.lock`, `Cargo.lock`.
  - binaries / assets: images, fonts, video, audio, `*.pdf`, `*.zip`, `*.db`,
    `*.sqlite`, `*.bin`, `*.onnx`, `*.safetensors`, model weights.
  - pure data / fixtures unless review-relevant: large `*.json`/`*.csv` data dumps.
  - docs-only is reviewed lightly (skip from the code fleet; the architecture map
    already captures structure).
- Keep: source in the project's languages, config that affects behavior (CI,
  Dockerfiles, infra-as-code, `*.toml`/`*.yml` that wire the app), schema/migrations,
  tests.

If unsure whether a directory is "useful code", include it — a subagent can note it
is noise faster than you can miss real code.

## 2. Decide the subsystem list

`$ARGUMENTS` (after the `project` keyword) may be a comma-separated list of
`LABEL:path` entries; one label may map to several `;`-separated paths
(e.g. `PROJ_api:src/api;src/routes, PROJ_db:src/db`).

- If **non-empty**: use exactly those entries.
- If **empty**: infer **3–7** (more for a big monorepo) logical subsystems from the
  top-level layout / packages, grouping related dirs. Print the proposed list as
  `LABEL -> paths`, then **ask the user to confirm or edit before mapping** — do not
  launch the fleet until confirmed (the fleet is expensive; a wrong decomposition
  wastes it). Use the dual-layer plain-language form + the USER INPUT REQUIRED banner
  when you ask.

## 3. Map+review phase — one subsystem at a time (STRICTLY SEQUENTIAL)

For EACH subsystem, in order, with a CLEAN main context between iterations:

**a. Launch the qRev roster scoped to this subsystem.** Per the chosen depth:
- default: the full `/rev exhaustive` 3-pass roster (read `~/.claude/skills/rev/SKILL.md`),
  but `SCOPE` = only this subsystem's pruned file list.
- `fast`: Phase A only (semgrep + CODING_STANDARDS) on the subsystem.
- `topic:<name>`: the topic's roster only.

Every agent gets qRev's **whole-file + full-context** directive (read
`~/.claude/skills/qRev/SKILL.md`, "Review depth" + the Phase B "REVIEW DEPTH
(mandatory)" block): read each scope file in full and trace its dependency context
(callers, callees, imports, bound config/schema/tests) — including dependencies that
live in OTHER subsystems (the agent may READ across the boundary for context, but its
findings stay scoped to this subsystem). Each agent returns a DISTILLED summary only —
never raw file dumps.

**b. Require each subsystem subagent to report exactly these sections** (architecture
map + review fused):

1. **Purpose / responsibility**
2. **Key components & their roles**
3. **Internal data flow**
4. **Public interface / entry points**
5. **External dependencies** (libraries, services, and which *other subsystems* it
   calls or is called by)
6. **Risks / open questions / TODO-FIXME hotspots**
7. **Review punch-list** — P0/P1/P2/P3 findings (qRev style: `file:line`, 1-line root
   cause, 1-line fix, skill citation for P0/P1), de-duplicated within the subsystem.

**c. Write two files, tidied (not re-expanded):**
- `docs/architecture/<LABEL>.md` — sections 1–6, top line
  `> Mapped: <ISO-date> · paths: <paths> · depth: <full|fast|topic:x>`.
- `exclude/SYSTEM_STRATEGIES/qrev-project/<LABEL>_REVIEW.md` — section 7 (the punch-list).

**d. Do NOT carry the subagent's raw findings into the next iteration** — only the
on-disk summaries persist. If context feels heavy, say so and recommend `/compact`
before continuing. Optionally publish progress for the statusline:
`node ~/.claude/scripts/process_progress.js --id qrevproj --label "qRev project" --pct <done/total*100>`
and `--done` at the end (see the global CLAUDE.md "Running-process progress bars").

## 4. Reduce phase — synthesis (single pass, reads ONLY the on-disk summaries)

ultrathink.

Read ONLY the per-subsystem `.md` files just written — **do NOT re-read source code.**
Produce:

**A. `docs/architecture/<PREFIX>_OVERVIEW.md`** (the architecture map):
- one-paragraph system summary;
- a **mermaid `flowchart`** with subsystems as nodes and dependency edges (who
  calls / feeds whom);
- a cross-subsystem dependency table;
- **Consistency checks** — where the mapped data flow contradicts the project's
  invariants: generic = layering / module-boundary violations and circular
  dependencies. If the repo is **PA (PrivateAssociations)**, ALSO flag anything that
  could break PA-blindness — a subsystem that can read *plaintext* user content,
  issues an *external runtime API call*, or stores content outside the NIP-59
  gift-wrap path (any deviation from the locked self-hosted-LLM / no-external-runtime-API
  rule);
- a deduplicated **"open questions for the architect"** list.

**B. `exclude/SYSTEM_STRATEGIES/qrev-project/PROJECT_REVIEW.md`** (the aggregated review):
- single aggregate verdict (CLEAN / WARNING / SHIP-BLOCK);
- merged P0/P1/P2/P3 punch-list across all subsystems, with `[<LABEL>]` attribution;
- consensus elevation: a finding raised in ≥2 subsystems (same root cause, e.g. a
  shared util misused everywhere) is elevated one severity tier and tagged
  `[systemic]`;
- a "Coverage gaps" section: any subsystem an agent couldn't fully read, any path
  skipped, any subsystem run at reduced depth.

## 5. Wire into project memory

If `CLAUDE.md` exists and doesn't already reference `docs/architecture/`, append:

```
## Architecture map
See docs/architecture/<PREFIX>_OVERVIEW.md and the per-subsystem maps.
Load these instead of re-scanning the repo. Re-run /qRev project after major
structural changes; the P0-P3 review is at exclude/SYSTEM_STRATEGIES/qrev-project/.
```

Also refresh `INDEX.md` if the project keeps one (point it at the overview).

## 6. Fixing — REPORT first, do NOT mass-auto-fix a whole repo

Unlike `/qRev` (which has standing auto-fix approval on a single diff), a
whole-project sweep is a large, far-reaching change set. So:

1. Print the aggregate verdict + the top of the punch-list (full list is on disk).
2. **Do not silently auto-apply fixes across the whole repo.** Default to producing
   `improve`-style self-contained implementation plans (read the `improve` skill) —
   one plan per cluster of related findings, each with its own verification gate —
   and dispatch execution to a cheaper tier per the smart-router tiering in
   `~/.claude/CLAUDE.md` (sonnet/haiku, or GLM tiers). Keep the high tier for the
   review + the plans.
3. Small, obviously-safe P0s (a one-line fix, no API/contract change) MAY be applied
   inline as in `/qRev`, but anything touching > a handful of files, a public
   contract, or needing a design call is a plan, not an inline edit.
4. Ask the user before kicking off a large fix batch (the dual-layer plain-language
   form + the USER INPUT REQUIRED banner).

## 7. Report

List every file written under `docs/architecture/` and
`exclude/SYSTEM_STRATEGIES/qrev-project/` with a one-line note each, give the
aggregate verdict and the P0 count, and remind the user to re-run `/qRev project`
after significant structural changes.

## Runs on GLM too

This skill works identically when the session runs on GLM (z.ai) instead of
Anthropic — it is a markdown skill executed by whatever model is active, and its
delegated subagents go through the Task tool, which inherits the active provider
(per the global `~/.claude/CLAUDE.md` "GLM (z.ai)" + "q* commands under GLM"
rules). So under the GLM launcher every subsystem fleet runs on GLM, and any tier
a sub-agent delegates to resolves to a GLM model via the per-tier mapping. No
special-casing is needed. One caveat carried from that GLM section: GLM is weaker
than Anthropic Opus at the hardest architecture/audit judgment, so for a
high-stakes whole-repo audit, prefer running this on the Claude subscription —
or, if you want a real Claude voice while on GLM during the planning of fixes,
note that `/qPlan` (which the fix-planning in section 6 uses) carries the
`claude-direct` cross-model lens that reaches the Claude subscription via
`claude -p` even on GLM.

## Do not

- Do not load the whole repo into one context (the hard rule).
- Do not re-read source in the reduce phase — summaries only.
- Do not skip the subsystem-confirmation gate when subsystems were auto-inferred.
- Do not run on a tiny project — fall back to `/qRev` or `/rev exhaustive` and say so.
- Do not invoke the Skill tool for `qRev` / `rev` / `improve` — read their SKILL.md
  and execute inline (avoids nested-skill machinery).
- Do not mass-auto-fix without the go-ahead (section 6).
