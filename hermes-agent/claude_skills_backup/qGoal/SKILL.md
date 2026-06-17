---
name: qGoal
description: Autonomous execute-a-goal-to-DONE engine — the ONLY q-command that touches code. Give it a goal (with a runnable check, a numeric metric, or neither) and it plans via /qPlan, runs MULTIPLE variants when the task warrants it (e.g. metric optimization) or a SINGLE path otherwise (e.g. build a webpage), consults /qPlan at every decision point (with OpenAI while budget lasts, without it otherwise), then runs /qRev at the end and fixes per its findings. Stops at DONE or BLOCKED. NOT plan-only (that is /qPlan). Invoked via /qGoal (canonical) OR any case variant — /qgoal, /Qgoal, /QGoal, /QGOAL all map to this same skill (case-insensitive). If the user types any of these, treat as a /qGoal invocation and proceed with this skill's state machine.
---

# qGoal — Autonomous Execute-to-DONE Engine

> **Invocation aliases.** This skill responds to `/qGoal` (canonical), `/qgoal`,
> `/Qgoal`, `/QGoal`, `/QGOAL` — case-insensitive. If a user message starts with
> any of these, route to this skill's state machine. The harness may not always
> dispatch the lowercase variants; if you see a literal `/qgoal` (any case) and no
> skill was auto-loaded, invoke `Skill(skill="qGoal", args="<rest>")` yourself.

`/qGoal <goal>` is the autonomous executor. It is the **hands**; `/qPlan` is the
**brain**. qGoal never decides alone at a real fork — it asks `/qPlan` (which
brings the multi-lens panel and, while budget lasts, the OpenAI cross-model
critic). qGoal carries the goal to completion: plan -> execute (one path, or
several variants when the task warrants) -> let qPlan pick the winner -> review
with qRev and fix -> stop at DONE or BLOCKED.

This skill **absorbs the retired `/qPlan auto`**: the multi-variant optimization
loop now lives here, where execution belongs, instead of bolted onto the planner.

## When to use

- Any concrete task you want carried to completion autonomously: "wire up the new
  endpoint and make `pytest` pass", "build a landing page", "raise the eval
  pass-rate as high as you can".
- Works with **a runnable check** (test/lint/build -> objective DONE), **a numeric
  metric** (climb it, held-out discipline), or **neither** (qPlan's OpenAI-backed
  judge decides "done" and, if multiple variants ran, "best variant"). A mix is
  fine.

Skip when:
- The task is pure design / architecture deliberation with no execution -> `/qPlan`.
- It is a trivial one-liner -> just do it; the engine overhead is ritual.

## Neighbor routing

| Command | Role | Touches code? |
|---|---|---|
| `/qPlan` | The brain: plan + decide (incl. OpenAI panel). Plan-only. | No |
| `/qGoal` | The hands: execute to DONE, calls qPlan + qRev. | Yes |
| `/qRev` | Deep review of a diff -> P0..P3 punch-list. | No (review) |
| `/qDo` | Permissions snippet (stop Yes/No prompts). | No (config) |

`/qPlan auto` is **retired** — `/qGoal` replaces it. If a user types `/qPlan auto`,
qPlan redirects them here.

## Single path vs multiple variants (adaptive — the key rule)

qGoal does NOT always fan out. The variant count fits the task, and **qPlan
decides it at planning time** (phase 1):

- **Multiple variants** when exploring genuinely competing options pays off:
  a **numeric metric to climb** (optimization), or two-plus real approaches where
  "which is best" is unclear and worth comparing head-to-head. This is the old
  `/qPlan auto` behavior (Arbor engine, isolated worktrees, pick the winner).
- **Single path** when the task is a deterministic build to a checkable done-state
  with an obvious approach — "create a webpage", "wire up this endpoint", "migrate
  these files". Running parallel variants there just burns time and tokens for no
  gain.

When unsure, qGoal asks qPlan; qPlan's plan output states the chosen variant count
and why. The user can override ("try 3 versions" / "just do it once").

## MUST / MUST NOT

- MUST: a futtatas elott allitsd ossze es ird ki a "done-contract"-ot (acceptance
  criteria + a siker-jel: futtathato ellenorzes / metrika / minosegi itelet). Csak
  utana nyulj a kodhoz.
- MUST: minden valodi donteshelyzetben hivd meg a `/qPlan`-t (ez hozza az OpenAI-t
  is, amig van budzse). qGoal egyedul nem dont el variant-szamot, verziovalasztast,
  "kesz?"-t, vagy iranyvaltast.
- MUST: a variant-szam a feladathoz igazodik (lasd fent). Szam-optimalizalasnal /
  valodi versengo megkozelitesnel tobb szal; determinisztikus build feladatnal (pl.
  weblap) egy szal. A dontest a qPlan hozza a tervezeskor.
- MUST: a vegen futtasd a `/qRev`-et a diffre, es javits az eredmenye szerint
  (legalabb P0/P1), majd ellenorizd ujra hogy a javitas nem rontott el semmit.
- MUST: minden futas DONE vagy BLOCKED allapotban er veget; a termination-check
  minden ciklus utan lefut (garantaltan terminal).
- MUST NOT: olyan "kesz"-t fogadj el, amit sem futtathato ellenorzes, sem metrika,
  sem a qPlan/OpenAI biro nem igazol. Claude sajat "szerintem kesz"-e onmagaban
  SOHA nem zar le.
- MUST NOT: autonom modban se nyulj `main`/`master`-hez, repo-n kivuli torleshez,
  vagy kifele hato muvelethez (push, uzenet, PR/komment) megerosites nelkul.

## How it runs (state machine)

Read `references/engine.md` in full at invocation time — it holds the house rules
(tiering, worktree, held-out, durable state, decision-log, safety, closeout), the
variant-count decision, the OpenAI-budget logic, and the qRev-fix loop. The phases:

### 0. Done-contract intake
Extract acceptance criteria and the **success signal** (runnable check / numeric
metric / qualitative). Detect OpenAI availability once (is `OPENAI_API_KEY` set?)
and record an `openai_budget` flag. Write the contract to the workdir and print it
back (visibility, not an approval gate). Workdir: `<cwd>/.qgoal/<run-id>/` (else
`~/.claude/qgoal/<run-id>/`); ensure `.qgoal/`, `.arbor/`, `.worktrees/` are
gitignored.

### 1. Plan via qPlan (decides single vs multi)
Invoke `Skill(skill="qPlan", args=...)` to produce the strategy AND the variant
count (single path vs N competing approaches) per the adaptive rule above. qPlan is
plan-only — it returns a plan; qGoal executes it. Pass the OpenAI-budget flag
through (see engine.md "OpenAI budget").

### 2. Execute
- **Single path**: implement the plan directly in the working tree. Model tiering
  per engine.md section 1.
- **Multiple variants**: spin up the N candidates in isolated worktrees and execute
  each, using the Arbor engine (`arbor-research-agent` +
  `arbor-agent-tools/scripts/arbor_state.py`) as the tree/worktree/merge backend —
  the same engine the old auto mode used.

### 3. Decision points -> qPlan
At every material fork — which variant is best, is the work done, which direction to
branch, whether to merge or prune — call `/qPlan` for the judgment. While
`openai_budget` holds, qPlan's panel includes the OpenAI cross-model lens; once the
budget is gone, qGoal calls qPlan WITHOUT the openai lens (it degrades, never
aborts). See engine.md "OpenAI budget". (Single-path runs still consult qPlan at
real forks — there are just no variant-selection forks.)

### 4. Select + converge
If multiple variants ran, pick the winner per qPlan's verdict (metric value if
numeric; qPlan/OpenAI qualitative verdict otherwise) and merge it to the run trunk.
Termination is the Arbor caps fused with qPlan's progress test (engine.md
section 5); single-path runs converge when the success signal is met.

### 5. qRev + fix (final gate)
Run `Skill(skill="qRev", args=...)` on the resulting uncommitted diff. Apply fixes
per its P0/P1/P2/P3 punch-list (auto-fix P0/P1; P2/P3 by scope/judgment). Re-run
the verification signal to confirm the fixes still satisfy DONE. Repeat qRev->fix
until no P0/P1 remain or a 2-pass cap is hit (guarantees termination).

### 6. Closeout
Decision-log any merge/prune (engine.md section 6); `/qUpd`; `hermes-learn`;
commit per family discipline (explicit staging, name the why) — **never auto-push;
ask first**. Print the result block: status (done/blocked/stalled/hard_cap),
path or variants tried + winner, the verification signal result, qRev punch-list
before/after, workdir path; for blocked/stalled, exactly what is needed to proceed.

## Do not

- Do not decide a real fork without `/qPlan` — that is the whole point of the
  brain/hands split.
- Do not fan out into multiple variants for a deterministic single-approach task;
  do not force a single path onto a real optimization. Match the variant count to
  the task (qPlan decides).
- Do not declare DONE on Claude's own judgment without a check, a metric, or the
  qPlan/OpenAI verdict backing it.
- Do not abort because OpenAI budget ran out — degrade to qPlan-without-OpenAI and
  keep going.
- Do not skip the final qRev + fix pass.
- Do not auto-push, force-push, or `--no-verify`. Routine edits run without
  prompts; destructive / outward-facing / `main`-touching ops still pause.
- Do not loop past the caps "just to try one more thing" — stop and hand back a
  clear BLOCKED/STALLED report.
