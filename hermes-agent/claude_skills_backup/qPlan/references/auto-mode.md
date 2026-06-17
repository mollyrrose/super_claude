# qPlan Auto mode — Arbor-fused autonomous optimization

`/qPlan auto <goal>` runs an **autonomous, metric-driven optimization loop**. It
is a DIFFERENT contract from default `/qPlan`: default qPlan is plan-only and
must NOT touch the codebase; **auto mode DOES execute** — it edits code, runs
evals, creates branches/worktrees, and merges verified winners. Use it only when
the user explicitly types `/qPlan auto` (or `auto` as the first arg).

The engine underneath is the vendored Arbor skill suite (the 11 `arbor-*`
skills, RUC-NLPIR/Arbor, Apache-2.0). Auto mode does NOT re-implement that loop —
it loads our house rules below, then drives `arbor-research-agent`, keeping the
run inside our conventions. The combination is the point: Arbor's loop discipline
+ our tiering / safety / bookkeeping.

## When to use / not use

USE when ALL of these hold:
- There is a **measurable objective** — a score, a loss, a pass-rate, a metric a
  command can print. No metric -> no auto mode.
- The work tolerates **many autonomous iterations** (minutes-to-overnight), not a
  single interactive pass.
- A held-out check is possible (a dev/test split, or at least a repeatable eval).

DO NOT use for:
- Interactive design / architecture deliberation -> default `/qPlan` (the
  author-critic panel) is the right tool.
- One-shot edits, bug fixes, or anything without a number to climb.
- Tasks where running code autonomously is unsafe or unauthorized.

## How it runs

1. Read THIS file (house rules) before anything else.
2. Invoke `Skill(arbor-research-agent, args="<goal>")`. It performs intake, forms
   the research contract (target, metric+direction, B_dev/B_test, baseline, eval
   command, permissions, budget, scope, HITL mode), then loads
   `arbor-agent-orchestrator` and the phase skills.
3. Because this environment has no native `arbor` CLI, the loop uses
   `arbor-agent-tools/scripts/arbor_state.py` (stdlib-only) as the Idea-Tree /
   eval / worktree / merge / report backend. No `pip install` is required.
4. Enforce the house rules below for the entire run, then run closeout.

## House rules (our augmentation — what makes the combo smarter)

### 1. Model tiering + GLM caveat
Apply the global "Subagent model routing (tiering)" policy to the Arbor phases:
- Coordinator strategy, IDEATE, and merge DECIDE turns -> **opus** tier (judgment).
- Executor implementation subagents -> **sonnet** tier.
- Mechanical steps (formatting, file moves, log parsing) -> **haiku** tier.

If the active provider is GLM (z.ai), honor the GLM CAPABILITY CAVEAT from the
global CLAUDE.md: GLM is weaker at the high-reasoning parts (IDEATE, architecture
choices, merge DECIDE). Keep those phases on the Claude (Opus) subscription, or
treat GLM's output there as a draft Claude reviews. GLM is fine for the executor
implementation and mechanical work. This matters because Arbor's own numbers show
the SMALLEST gains exactly on the "design" rows — the parts GLM is weakest at.

### 2. Worktree + branch convention
Map Arbor's experiment isolation onto our project-boundary rules:
- Experiment worktrees live under `.worktrees/<branch>/` inside the project root
  (our standard), NOT ad hoc temp dirs.
- Experiment branches: `arbor/<run-name>/<node-id>`. Trunk: `arbor/trunk/<run-name>`.
- `main`/`master` are PROTECTED base branches, never merge targets (Arbor already
  refuses them; we restate it).
- Before the run starts, confirm `.arbor/`, `.worktrees/`, and `.qplan/` are
  gitignored; add them if missing. Never commit run state.

### 3. Held-out discipline (the core guardrail)
- B_dev for ALL iteration and idea selection. B_test ONLY at merge verification
  and final report. Never iterate against B_test.
- If B_test diverges from B_dev, do not hand-wave — investigate overfitting, eval
  contamination, or split mismatch. This same dev/held-out discipline applies to
  our OWN eval work (smart-router tuning, context-budget thresholds): split the
  data, tune on dev, report on held-out.

### 4. Idea Tree as durable memory (resumability)
- Run state lives on disk in `.arbor/sessions/<run>/.coordinator/idea_tree.json`,
  never in transient chat. Propagate child insights upward (TreePropagate).
- Because state is durable, a long auto run SURVIVES a `/clear` or auto-compact:
  on resume, `arbor-research-agent` re-orients from the tree instead of INIT.

### 5. Termination = Arbor caps fused with qPlan's progress test
Stop when EITHER fires:
- Arbor's cycle cap / budget reached, OR
- **No real progress**: K consecutive cycles with no B_dev score improvement AND
  no pending high-expected-value leaves. This is qPlan's "separate real progress
  from refinement" principle applied to scores — do not keep spawning ideas just
  because you can. (Default K=3; the contract's max-cycles is the hard cap.)

### 6. Decision-log on hard-to-reverse moves
When the loop MERGES a verified winner into trunk, or PRUNES an entire strategy
branch, log it (these are exactly the "non-trivial, hard-to-reverse" decisions):
- Append to `<project>/docs/decisions/log.md` (newest on top), and
- Pipe the same fields as JSON to the decision stream:
  `"C:\Python313\python.exe" "D:\Projects\super_claude\hermes-agent\claude_code_integration\decision_log_cli.py"`
  with `revisit_if` like "B_test regresses below trunk" or "metric assumption changes".
Routine per-cycle iteration is NOT logged — only merges and strategy-level prunes.

### 7. Context-budget handling
Long autonomous loops consume context. The run is checkpointed (Arbor resume), so
on the context-budget qClose nudge: checkpoint, then either `/clear` and resume,
or hand off. Do not fight auto-compact — the on-disk Idea Tree is the real memory,
so a compaction is recoverable.

### 8. No decorative unicode
Every generated code literal, eval command, branch name, regex, and tool input is
plain ASCII (global hard rule), even though Arbor's own prose may use arrows/emoji
in comments. Comments/notes may keep them; runnable strings/commands must not.

### 9. Safety gates (Intern Rule + kill switch)
- Default to SMOKE mode for "try / test / validate / demo" goals: no real
  training, downloads, package installs, GPU jobs, or full eval until the user
  authorizes them or the contract clearly permits.
- Use the narrowest permissions that work; protected data/eval/private paths are
  off-limits.
- Kill switch: abort a run by deleting `.arbor/sessions/<run>` and the
  `arbor/<run>/*` and `arbor/trunk/<run>` branches. Nothing the loop does touches
  `main`/`master`, so abort is always clean.

### 10. Closeout
At run end:
- Finalize the decision-log entries with an `outcome` (held/reversed/open).
- `/qUpd` the project's INDEX.md and `exclude/TODO.md` if real progress landed.
- Invoke `hermes-learn` for any genuinely reusable pattern the run surfaced.
- Report durable artifact paths (REPORT.md, idea_tree.md, best branch + score)
  and any caveats. Then STOP — do not keep polishing reports or running extra
  cycles past the budget.

## One-line mental model

Arbor is the autonomous optimization *loop*; this file is the *house rules* that
keep that loop tiered correctly, safe, resumable, logged, and honest about
held-out scores. Default `/qPlan` plans; `/qPlan auto` optimizes.
