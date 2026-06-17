# qGoal engine — house rules, variant logic, OpenAI budget, qRev gate

`/qGoal` is the autonomous executor (the **hands**). `/qPlan` is the **brain** it
consults at every real fork. This file is the operating contract: read it in full
at invocation time. It supersedes the old `qPlan/references/auto-mode.md` (that
file and the `/qPlan auto` mode are retired; their execution + optimization role
moved here, where it belongs — a planner must not execute).

The underlying multi-variant engine is the vendored Arbor skill suite (the
`arbor-*` skills, RUC-NLPIR/Arbor, Apache-2.0). qGoal does not re-implement it — it
loads these house rules, then drives `arbor-research-agent` when (and only when) the
task warrants multiple variants. The combination is the point: Arbor's loop
discipline + qPlan's judgment + our tiering / safety / bookkeeping.

## Variant count — decide once, at planning time

qGoal does NOT always fan out. qPlan (phase 1) sets the variant count from the task
shape:
- **Multiple variants** when exploring competing options pays off: a numeric metric
  to climb, or two-plus genuinely different approaches where "best" is unclear.
  Uses the Arbor backend (worktrees, idea tree, merge the winner).
- **Single path** when the task is a deterministic build to a checkable done-state
  with an obvious approach (a webpage, an endpoint, a file migration). No fan-out;
  implement directly in the working tree. qRev at the end still applies.
- Default to single path when in doubt; escalate to multi only with a concrete
  reason qPlan can name. The user may override the count explicitly.

Sections 2, 4, 5 below (worktree, held-out, Arbor caps) apply only to multi-variant
runs. Single-path runs use the plain progress test in section 5b.

## OpenAI budget (the user's rule: with OpenAI while budget lasts, else without)

- At run start set `openai_budget = (OPENAI_API_KEY is set)`. Record it in
  `state.json`.
- Every decision-point call to qPlan passes the flag:
  - `openai_budget == true` -> invoke qPlan with `critic_provider: panel` so the
    `openai` lens (cross-model judgment) is in the fleet.
  - `openai_budget == false` -> invoke qPlan with the `openai` lens removed from
    `panel_lenses` (panel still runs, just Claude-side). qPlan keeps full judgment;
    only the cross-model voice drops.
- If an OpenAI call fails with a quota / billing / auth error (insufficient_quota,
  402/401, "billing"), set `openai_budget = false` for the REST of the run and
  continue degraded. qGoal NEVER aborts for lack of OpenAI — it degrades.
- This degradation is qGoal's explicit choice; it does NOT change qPlan's own
  standalone "fail loud, do not silently fall back" rule. qGoal simply does not
  request the `openai` lens when there is no budget.

## qRev gate (final, the user's rule: review then fix)

After the work converges (single path satisfied, or winner merged), before
closeout:
1. Run `Skill(skill="qRev", args="<scope = the uncommitted diff>")`. qRev returns a
   P0/P1/P2/P3 punch-list (its qMin 5-axis pass + exhaustive fleet).
2. Fix per the list: P0 and P1 are auto-fixed (qMin auto-fix discipline — minimal,
   surgical edits, one-line status each). P2/P3 by scope and judgment; skip with a
   one-line reason when a fix needs a design call or a large refactor.
3. Re-run the success signal (check/metric) to confirm fixes did not break DONE.
4. Repeat qRev -> fix at most **2 passes** total. If P0/P1 still remain after pass
   2, stop and report them as BLOCKED items rather than looping (termination
   guarantee).

## House rules

### 1. Model tiering + GLM caveat
Apply the global "Subagent model routing (tiering)" policy:
- qPlan decision calls, IDEATE, merge/winner DECIDE -> **opus** tier (judgment).
- Executor implementation subagents -> **sonnet** tier.
- Mechanical steps (formatting, file moves, log parsing) -> **haiku** tier.

On GLM (z.ai), honor the GLM CAPABILITY CAVEAT: GLM is weaker at the high-reasoning
parts (IDEATE, architecture, winner DECIDE). Keep those on Claude (Opus), or treat
GLM output there as a draft Claude reviews. GLM is fine for executor implementation
and mechanical work.

### 2. Worktree + branch convention (multi-variant runs)
- Variant worktrees live under `.worktrees/<branch>/` inside the project root, NOT
  ad hoc temp dirs.
- Variant branches: `qgoal/<run-name>/<node-id>`. Trunk: `qgoal/trunk/<run-name>`.
- `main`/`master` are PROTECTED base branches, never merge targets.
- Before the run, confirm `.arbor/`, `.worktrees/`, `.qgoal/` are gitignored; add
  them if missing. Never commit run state.

### 3. Held-out discipline (numeric-metric runs only)
- B_dev for ALL iteration and variant selection. B_test ONLY at final verification
  and report. Never iterate against B_test.
- If B_test diverges from B_dev, investigate overfitting / eval contamination /
  split mismatch — do not hand-wave.

### 4. Durable state (resumability)
- Run state lives on disk: `.qgoal/<run-id>/state.json`, and for multi-variant runs
  the Arbor idea tree at `.arbor/sessions/<run>/.coordinator/idea_tree.json`. Never
  in transient chat.
- Because state is durable, a long run survives `/clear` or auto-compact: on resume,
  re-orient from disk instead of restarting.

### 5. Termination
**5a. Multi-variant:** stop when EITHER fires — Arbor's cycle cap / budget reached,
OR no real progress (K consecutive cycles with no metric/quality improvement AND no
pending high-value leaf). Default K=3; the contract max-cycles is the hard cap.

**5b. Single path:** stop when the success signal is satisfied (DONE), or BLOCKED
(needs a human decision / missing input / unauthorized op), or `no_progress >= K`
(default K=4) consecutive steps with no advance (STALLED), or `step >=
hard_cap_steps` (default 40). The check runs every step, in that order, hard cap
first.

Either way the qRev gate (above) runs before closeout, and its own 2-pass cap keeps
it terminal.

### 6. Decision-log on hard-to-reverse moves
When the run MERGES a winner into trunk, or PRUNES a whole strategy branch, log it:
- Append to `<project>/docs/decisions/log.md` (newest on top), and
- Pipe the same fields as JSON to the decision stream:
  `"C:\Python313\python.exe" "D:\Projects\super_claude\hermes-agent\claude_code_integration\decision_log_cli.py"`
  with `revisit_if` like "B_test regresses below trunk" or "requirement changes".
Routine per-step / per-cycle iteration is NOT logged — only merges and
strategy-level prunes.

### 7. Context-budget handling
Long runs consume context. The run is checkpointed on disk (resume), so on the
context-budget nudge: checkpoint, then either `/clear` and resume, or hand off. Do
not fight auto-compact — the on-disk state is the real memory.

### 8. No decorative unicode
Every generated code literal, eval command, branch name, regex, and tool input is
plain ASCII (global hard rule). Comments / notes may keep arrows or emoji; runnable
strings / commands must not.

### 9. Safety gates (Intern Rule + kill switch)
- Default to SMOKE mode for "try / test / validate / demo" goals: no real training,
  downloads, package installs, GPU jobs, or full eval until the user authorizes or
  the contract clearly permits.
- Narrowest permissions that work; protected data/eval/private paths are off-limits.
- Kill switch: abort by deleting `.qgoal/<run-id>`, `.arbor/sessions/<run>`, and the
  `qgoal/<run>/*` + `qgoal/trunk/<run>` branches. Nothing the run does touches
  `main`/`master`, so abort is always clean.

### 10. Closeout
At run end:
- Finalize decision-log entries with an `outcome` (held/reversed/open).
- `/qUpd` the project's INDEX.md and `exclude/SYSTEM_STRATEGIES/TODO.md` if real
  progress landed.
- Invoke `hermes-learn` for any genuinely reusable pattern the run surfaced.
- Report durable artifact paths (workdir, idea_tree.md for multi-variant, winning
  branch + result), the qRev before/after, and any caveats. Then STOP — do not keep
  polishing or running extra cycles past the budget.
- Commit per family discipline (explicit staging, message names the why, standard
  `Co-Authored-By` trailer). Do NOT auto-push — ask the user first, even where a
  standing "push" authorization exists (same rule as `/qClose`).

## One-line mental model

qPlan is the brain (plans + decides, brings OpenAI while budget lasts); qGoal is the
hands (executes — one path or several variants as the task warrants — and consults
qPlan at every fork); qRev is the final inspector qGoal fixes against. The retired
`/qPlan auto` is now just "qGoal on a multi-variant task."
