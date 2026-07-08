---
name: wargame
description: "Wargame a project's pending work before execution: recon read-only, derive executor-sized missions from the project's TODO / SYSTEM_STRATEGIES inventory, then fight each mission on paper — every move with its expected observation, likely failure and counter-move, every fork with a trigger, RECON NEEDED marks, abort conditions, and verification runs — so a cheaper mid-tier model can execute the plan blind. Includes a red-team pass and an 8-point grade per plan, logged in a ledger. Battle plans land in <project>/exclude/SYSTEM_STRATEGIES/wargames/. Adapted from the fable-wargame-kit. Invoked via /wargame <project-path> [mission focus] (case-insensitive variants map here). Use when you want to bank a top-tier model's judgment as executable battle plans."
argument-hint: "<project path> [optional: mission focus, e.g. 'only the billing TODOs']"
effort: high
---

# Wargame — battle-plan a project's pending work

You are not executing the missions. You are wargaming them: producing battle plans a cheaper executor (Sonnet-tier) runs later, blind, without asking a single question. The value produced here is judgment on paper — every decision pre-made, every failure pre-countered.

## Arguments

**TARGET:** $ARGUMENTS

- If TARGET is a project path: derive missions from the project's own work inventory (Phase 1).
- If TARGET includes a focus qualifier ("only X", "the Y part"): restrict the mission derivation to it.
- If TARGET is an inline mission brief (no path): skip Phase 1, wargame that single brief; wargames land in the current project.
- If TARGET is empty: ask which project to wargame.

## Phase 0 — Recon (read-only, always first)

Delegate to an Explore agent (or read directly if the project is small). Gather:
- INDEX.md, README*, STARTUP.md, docs/
- `exclude/SYSTEM_STRATEGIES/` — TODO.md, SYSTEM_STATUS.md, and the ENTIRE `todo/` subdirectory if present. The todo inventory is the DEFINITIVE list of planned work: treat every item as work to be planned to completion (as if it were being built now).
- Key entry points, test/build commands, .gitignore, CLAUDE.md/AGENTS.md constraints.

Nothing is modified during recon. Anything recon cannot settle becomes a RECON NEEDED mark in the plans, with the exact check that settles it.

## Phase 1 — Mission derivation

Cluster the work inventory into **4-8 executor-sized missions** — each runnable by a mid-tier model in one focused session. Order by dependency, then value. For each mission record: name, covered inventory items (with source paths), the single riskiest assumption, and the executor's success criteria.

Present the mission list briefly to the user in the final report, but do NOT stop to ask for approval — wargaming is read-only with respect to the product; only plan files are written.

## Phase 2 — Wargame each mission

Dispatch one subagent per mission IN PARALLEL, `model: fable` (this is precisely the hardest-reasoning adversarial-planning work the fable tier exists for; if fable is unavailable, opus). Each wargamer receives the recon digest, its mission definition, and this order:

```
WARGAME ORDER. You are not executing this mission, you are wargaming it. A cheaper executor (a mid-tier model) runs the mission later. Your job is the route it will follow.

Recon material and mission definition are below. If you must inspect files to settle a route, do so READ-ONLY.

Fight the mission on paper, move by move, and write it to <project>/exclude/SYSTEM_STRATEGIES/wargames/NN-<slug>.md (create the directory if missing):

- every move states its expected observation, exactly what you should see if it worked
- every move carries its most likely failure, the cause that failure signals, and the counter-move
- every fork gets a trigger: if you observe X, take route B — no judgment calls left to the executor
- assumptions recon could not settle get marked RECON NEEDED with the exact check that settles it
- end with abort conditions (the moments to stop and flag rather than improvise), and the verification runs the executor must perform, when, and what pass looks like for each

Structure: # title / ## Mission (the executor's orders) / ## Preconditions / ## Moves (numbered, each with Observation:, Failure:, Counter:) / ## Forks / ## RECON NEEDED / ## Abort conditions / ## Verification runs / ## Red-team record (leave empty — filled by the red-team pass).

Write it so the executor can run the mission end to end without asking a single question. ASCII + em-dash only, no decorative unicode.
```

## Phase 3 — Red-team pass

After a wargame lands, dispatch a SEPARATE red-team subagent (`model: fable`, opus fallback) per plan:

```
RED-TEAM ORDER. Attack this battle plan as a hostile reality: find the move whose expected observation is ambiguous, the failure mode with no counter-move, the fork an executor could misread, the verification that passes while the mission actually failed, the assumption that recon should have settled. Attempt at least 4 distinct attacks.

For every attack that SUCCEEDS: patch the plan in place (edit the file) and record the attack + patch in the ## Red-team record section.
For the strongest attack that FAILS: record it too — the plan's resilience is part of the deliverable.
Do not soften the plan; make it more executable.
```

## Phase 4 — Grade and ledger

For each patched plan, self-grade against the 8-point standard (all must hold):

1. Every move states its expected observation.
2. Every move carries its most likely failure, the cause it signals, and the counter-move.
3. Every fork has a trigger — no judgment calls left to the executor.
4. Every unsettled assumption is marked RECON NEEDED with the exact settling check.
5. Abort conditions exist.
6. Verification runs are spelled out with what pass looks like for each.
7. It survived a red-team pass, and the doc records both a failed attack and the patches born from successful ones.
8. It is executable blind by a mid-tier model, end to end, zero questions.

Any failed point: send the plan back (one more wargamer round on the failing points), then re-grade. Append one entry per mission to `<project>/exclude/SYSTEM_STRATEGIES/wargames/LEDGER.md`:

```
## NN-<slug> — <date>
Draft: wargames/NN-<slug>.md
Grade: 1[ok] 2[ok] 3[ok] 4[ok] 5[ok] 6[ok] 7[ok] 8[ok]
Patches: <one line per red-team patch>
Executor: <suggested tier, e.g. sonnet>
```

## Phase 5 — TODO.md entries + fix/defect descriptors

After the ledger, two registrations in the examined project (create files/dirs if missing; update rather than duplicate on re-runs):

**5a. Mission entries.** Register every passed plan in `exclude/SYSTEM_STRATEGIES/TODO.md` as pending executable work, under a `## Wargamed missions — ready for executor` section. One entry per mission, following the shared-TODO window-ownership format from the global CLAUDE.md:

```
- [w-<code>] <ISO timestamp> pid:<n> host:<name> start:<ISO> hb:<ISO> — EXECUTE wargame plan `exclude/SYSTEM_STRATEGIES/wargames/NN-<slug>.md` (executor: <tier>); plan is blind-executable, do not re-plan
```

**5b. Fix/defect list.** Wargaming surfaces real problems in the project itself — broken assumptions, missing prerequisites, bugs recon stumbled on, gaps the red-team attacks exposed, RECON NEEDED items that turned out to be genuine defects. These are findings about the PROJECT, distinct from the mission plans. Register each finding twice, per the project's todo convention (TODO.md = list, todo/ = detailed descriptors):

1. A descriptor file at `exclude/SYSTEM_STRATEGIES/todo/wargame-fix-<slug>.md` containing: what is wrong (with file paths / evidence), why it matters (which mission or assumption it breaks), the proposed fix, acceptance check, and severity (P0-P3).
2. A list entry in `exclude/SYSTEM_STRATEGIES/TODO.md` under a `## Wargame findings — fixes needed` section, same window-ownership format, one line per finding pointing at its descriptor:

```
- [w-<code>] <ISO timestamp> pid:<n> host:<name> start:<ISO> hb:<ISO> — FIX <one-line summary> (P<n>); details: `exclude/SYSTEM_STRATEGIES/todo/wargame-fix-<slug>.md`
```

These are backlog entries: any window may take them per the takeover protocol. Executing a plan or fixing a finding removes its entry (TODO.md holds only open work).

## Final report

Summarize per project: mission list with one-line status, ledger location, and the exact command to hand a plan to an executor (e.g. "run exclude/SYSTEM_STRATEGIES/wargames/01-<slug>.md with a sonnet session"). The plans are the deliverable — the missions themselves are NOT executed by this skill.

## Notes

- Plans live under `exclude/` (gitignored) on purpose: they may reference internal strategy. Never commit them without being asked.
- This skill writes ONLY plan files (wargames/, LEDGER.md). It never modifies product code, and never pushes.
- Multi-project invocation ("/wargame A and B") runs Phases 0-4 per project, recons in parallel.
