---
name: qPlan
description: Run a guaranteed-terminating author↔critic iteration loop to deepen a plan (and optionally code). Each suggestion is tracked in a semantic ledger, each accepted change classified by materiality tier, and the loop stops when real progress ends — not when refinement ends. Invoked via /qPlan (canonical) OR any case variant — /qplan, /Qplan, /QPlan, /QPLAN all map to this same skill (case-insensitive). If the user types any of these, treat as a /qPlan invocation and proceed with this skill's state machine.
---

# qPlan — Author↔Critic Iteration Loop

> **Invocation aliases.** This skill responds to `/qPlan` (canonical), `/qplan`, `/Qplan`, `/QPlan`, `/QPLAN` — case-insensitive. If a user message starts with any of these, do not say "command not recognized"; route to this skill's state machine. The harness may not always dispatch the lowercase variants automatically; if you see a literal `/qplan` (or any case variant) in the user's prompt and no skill was auto-loaded, invoke `Skill(skill="qPlan", args="<rest of the message>")` yourself.

A `/plan`-style design pass deepened with an explicit critic role and a
materiality ledger. Use it when a single planning pass is not enough but you
want a *bounded* deepening process, not an unbounded refinement loop.

The skill's central job is to **separate real progress from increasingly
refined re-formulation**. Pure prose polish does not advance the plan;
structural and behavioral changes do.

## When to use

- The task is non-trivial and worth more than one round of design / critique.
- You want a transcript + audit trail of *why* the plan ended where it did.
- You want to compare planning quality between same-model and cross-model
  critique (the `critic_provider` axis).

Skip for:
- Bug fixes, single-file edits, trivial config tweaks (use `/think`
  Lightweight Mode or just answer directly).
- Tasks where you already know exactly what to do and a critique loop would
  be ritual.



## MUST/MUST NOT:
    - MUST: bemeneti tervet kritikusi iterációba veszi, akkor is ha "implementálni készen" tűnik
    - MUST NOT: tervet execute-ol, fájlokat módosít a kódbázisban, commit-ol — ezek /qDo vagy hasonló feladata
    - Ha az args execution-szerű ("implement", "csináld", "ok", "ok tovább", "tovább", "phase 0→1→2"), stop + 1 kérdés, nem reinterpret
    - MUST: egy `/qPlan` hívás = egy plan-fájl bemenet = egy iteráció run = egy workdir. Ha az args több plan-fájlra hivatkozik, vagy egy run convergencia után egy *új* brainstorming task is megjelenik a payload-ban, **állj meg és kérdezz** (mint Round 0-ban A/B/C disambiguation-nel) — ne chain-elj automatikusan egy második qPlan futtatást ugyanabban a válaszban. Egy futtatás convergencia után = STOP + handoff a user-nek; a user dönti el indít-e új `/qPlan`-t.


## Configuration

The user's `/qPlan` invocation may begin with a YAML config block. Defaults
if absent:

```yaml
critic_provider: panel         # panel | claude | openai
                               # panel (NEW DEFAULT) = multi-lens critic fleet
                               # claude / openai = v1 single-critic backwards-compat
panel_lenses:                  # max-mode default — all 22 lenses on
  # ----- 15 installed-skill lenses -----
  - requirements               # requirements-analyst + ask-questions-if-underspecified
  - architecture               # system/backend/frontend-architect + sc:design + oc-*
  - business                   # business-panel-experts + sc:business-panel
  - spec                       # sc:spec-panel
  - estimation                 # sc:estimate + sc:workflow + sc:task
  - risk                       # root-cause-analyst + sc:reflect + hermes-systematic-debugging
  - brainstorm                 # sc:brainstorm + brainstorming + hermes-ideation + think
  - research                   # learn + sc:research + deep-research-agent
  - prd                        # ecc:plan-prd + ecc:prp-prd + oc-to-prd
  - orchestration              # ecc:plan-orchestrate + ecc:multi-plan + hermes-writing-plans + ecc:gan-planner
  - pragmatism                 # karpathy-guidelines
  - spike                      # hermes-spike
  - decomposition              # oc-to-issues
  - socratic                   # socratic-mentor (questions, not assertions)
  - openai                     # cross-model voice via openai_critic.py
  # ----- 7 research-derived lenses (2024-2026 multi-agent planning research) -----
  - spec-conformance           # MAST: drift vs original ask (21% of multi-agent failures)
  - executable-check           # LLM-Modulo: cheapest thing actually runnable
  - premortem                  # "Could you be wrong" + failure-narrative form
  - test-contract              # MetaGPT QA: acceptance tests pre-implementation
  - drift-anchor               # Counter multi-round debate drift (round-3+ only)
  - pareto-variants            # GEPA: variants on different axes (Phase A only)
  - bias-audit                 # Audit ledger for momentum / suggester-preference (round-4+ only)
panel_parallel: true           # fire lenses in parallel via Agent tool
panel_min_lenses: 7            # below this after mute heuristics → config error
panel_bias_injections: true    # CoVe + negative-constraint + "could you be wrong"
                               # applied to every lens prompt by the orchestrator
openai_backend: api            # api | browser (browser is a stub in v1)
model: <provider default>      # claude: current session; openai: gpt-4o
max_concept_rounds: 8          # Phase A cap
K: 5                           # no_progress cap in Phase B
hard_cap_rounds: 20            # unconditional global cap
author_prefix:  "Erről mit gondolsz?:"
critic_prefix:  "Erről mit gondolsz? Hol javítanád?:"
```

`critic_provider: openai` (and the `openai` lens inside `panel` mode) require
`OPENAI_API_KEY`. The script fails loud if the key is missing — it does NOT
silently fall back to `claude`, because the whole point of provider
comparison is to keep them distinguishable.

`critic_provider: panel` is the default and runs in **max mode**: all 22
lenses from `references/panel-prompts.md` are active by default. 15 of them
come from the installed planning-skill catalog (Claude built-in agents,
SuperClaude `sc:`, ECC `ecc:`, OpenClaw `oc-`, Hermes `hermes-`, plus the
OpenAI cross-model critic). 7 are new lenses derived from 2024-2026 multi-
agent planning research:

- **`spec-conformance`** (MAST taxonomy) — drift vs original ask, the
  single largest under-served multi-agent failure bucket (21.3% of
  failures across 1,600+ traces).
- **`executable-check`** (LLM-Modulo) — what's the cheapest thing actually
  runnable to falsify the plan? Pure-LLM verification is unreliable past
  a certain depth.
- **`premortem`** ("Could you be wrong" debias) — imagine the plan failed
  in 3 months; write the postmortem; what plan change today prevents it?
- **`test-contract`** (MetaGPT QA) — write acceptance tests pre-
  implementation; MetaGPT hits 85.9% Pass@1 partly because of this.
- **`drift-anchor`** (Problem Drift) — counter multi-round debate drift
  (debates drift off-topic around round 3 without an anchor).
- **`pareto-variants`** (GEPA) — produce 2-3 plan variants on different
  axes; counter premature convergence on a single "best" plan.
- **`bias-audit`** (cognitive bias research) — audit the ledger for
  momentum / suggester-preference / sunk-cost contamination.

The panel additionally applies **three cross-cutting bias injections** to
every lens prompt: (a) Chain-of-Verification with independent answering,
50-70% hallucination reduction; (b) negative-constraint phrasing
(Constitutional AI pattern, harder to game than positive preferences);
(c) "Could you be wrong?" metacognitive prompt before final verdict. And
the orchestrator appends an **anti-overlap clause** to every lens spawn,
naming what the adjacent lenses cover (Anthropic multi-agent research
playbook).

The outer author↔critic state machine — ledger, tier rubric, no_progress
counter, termination conditions — is unchanged. Only what counts as a
"critic turn" expanded.

`critic_provider: claude` and `critic_provider: openai` keep the v1
single-critic behavior verbatim. Use them when you want to reproduce a
specific v1 run or when you specifically want to compare panel vs single.

## What to do

When `/qPlan <task>` fires, execute the state machine below.

**Workdir**: `<cwd>/.qplan/<run-id>/` if cwd is a project (has `.git`,
`package.json`, `Cargo.toml`, `pyproject.toml`, or similar), else
`~/.claude/qplan/<run-id>/`. Use a short timestamp ID like
`2026-06-05T1234` for the run.

### 1. Initialize

Create the workdir. Write:

- `state.json` — `{"round": 0, "no_progress": 0, "phase": "A", "caps": {…}, "provider": "claude"}`
- `transcript.md` — header (timestamp, task verbatim, config in effect)
- `ledger.jsonl` — empty
- `plan.md` — empty

### 2. Loop

`while round < hard_cap_rounds:`

**a. AUTHOR turn.** Wear the author hat (see `references/role-prompts.md` —
read it; do not paraphrase from memory). Read current `plan.md` + accepted
ledger entries + the task. Produce the next version of `plan.md`. In Phase B,
also Write/Edit code files. Append a `### Round N · author` block to
`transcript.md` with a one-paragraph delta summary — diff-style is fine; do
not re-paste the full plan.

**b. CRITIC turn.**

- `critic_provider: claude` → wear the critic hat (`role-prompts.md`).
  Read the plan + relevant code files. Emit JSON:
  ```json
  { "verdict": "major issue" | "minor issue" | "no material issue",
    "suggestions": [ { "text": "...", "tier_hint": "structural|behavioral|editorial" } ] }
  ```
- `critic_provider: openai` → invoke
  `bash scripts/openai_critic.py` via the Bash tool, passing
  `{task, plan, ledger}` JSON on stdin. Parse the JSON verdict on stdout.
- `critic_provider: panel` → run **all lenses in `panel_lenses`** in
  parallel (see "Panel mode" section below for the full procedure). Merge
  their JSON verdicts into one combined `{verdict, suggestions[]}` where
  each suggestion carries a `source_lens` field. The merged `verdict` is
  the worst of the per-lens verdicts (`major issue` > `minor issue` >
  `no material issue`).

Append a `### Round N · critic` block with the raw JSON. For panel mode,
the block records BOTH the per-lens raw responses (one subsection per
lens) AND the merged suggestion list — the audit trail must preserve
where each suggestion came from before semantic-match collapsed
duplicates.

**c. LEDGER SEMANTIC MATCH.** For each new suggestion, wear the arbiter hat
and ask: *"Is this suggestion semantically the same as any of ledger entries
#1..#N?"* with the ledger pinned verbatim, not summarized. The critic
*rephrases* its repeated points; that is what we must catch.

- Match found → reuse that entry; increment its `repeat_count`.
- No match → append as new entry with status `pending`.

If a matched entry's status is `rejected` and `repeat_count >= 3`, change its
status to `resolved-by-disagreement` and exclude it from further rounds.

**d. AUTHOR REACTS.** For each new (non-resolved) suggestion, mark
`accepted` or `rejected` with a one-line rationale logged in the ledger.
Rejection is allowed and expected — do not absorb every suggestion blindly.

For each `accepted`: apply the change to `plan.md` (and code files in Phase
B).

**e. TIER CLASSIFY.** For each accepted suggestion this round, apply
`references/tier-rubric.md`:

- If the rubric returns a definite tier → use it. Log to ledger.
- If the rubric returns `ambiguous` → wear the arbiter hat, classify with a
  one-line justification, log both the tier and the justification.

Never let the author classify alone (biases toward Editorial → premature
stop). Never let the critic classify alone (biases toward Structural →
never stops).

Then:
- Round had ≥1 Structural OR Behavioral acceptance → `no_progress = 0`.
- Else → `no_progress++`. (Editorial-only, no-change, and all-rejected rounds
  all count as no-progress.)

**f. PHASE TRANSITION.** If this round was the first to create/edit a code
file, set `phase = "B"`.

**g. TERMINATION CHECK** — in this order, (1) is unconditional:

1. `round >= hard_cap_rounds` → STOP, reason `hard_cap`.
2. Phase A: STOP if (no Structural/Behavioral suggestion this round AND every
   new suggestion matched the ledger) OR `round >= max_concept_rounds`.
   Reasons: `phase_a_converged` or `max_concept_rounds`.
3. Phase B: STOP if `no_progress >= K`. Reason `no_progress`.
4. Also STOP if `verdict == "no material issue"` AND every new suggestion
   matched the ledger. Reason `verdict_converged`.

Update `state.json` after each round.

### 3. On stop

Append a closing summary section to `transcript.md`:

```
## Closing summary
- Rounds: N
- Stop reason: <reason>
- Final phase: A | B
- Accepted: <count> (struct: X, behav: Y, edit: Z)
- Rejected: <count>
- Resolved-by-disagreement: <count>
- Deferred (frozen for v1.1): <list>
```

Present the same one-screen summary to the user in chat, plus the workdir
path and the final `plan.md`.

## Role prompts and rubric

These live in separate reference files so SKILL.md stays scannable. Read them
**at invocation time**, not from memory:

- `references/role-prompts.md` — author / critic / arbiter prompts
- `references/tier-rubric.md` — mechanical decision table
- `references/panel-prompts.md` — per-lens prompts for `critic_provider: panel`

The critic prompt contains the explicit instruction that `no material issue`
is a *valid and correct* outcome, not a failure to find something. Models are
pulled to find "one more thing" by default; this counters that pull. The
backstop is still the ledger + counters — the verdict alone does not suffice.

## Panel mode

When `critic_provider: panel`, step `b. CRITIC turn` runs a fleet of
planning-specialist lenses in parallel instead of a single critic. This
matches the structural move `/rev` made on the code-review side and gives
`/qPlan` the depth of an "ultra plan" command without giving up the v1
termination guarantees.

### Procedure

1. **Resolve the lens roster.** Read `panel_lenses` from the config. For
   each lens, consult `references/panel-prompts.md` for the mute heuristic
   and apply it to this task (e.g. mute the `business` lens for a pure
   internal-engineering task with no user-facing surface). The resulting
   roster is the *active* lens set for this round.

2. **Min-lens guard.** If the active roster is shorter than
   `panel_min_lenses`, STOP the run with a clear config-error message to
   the user. Do not silently proceed with too few critics — that defeats
   the panel's purpose.

3. **Fire lenses in parallel.** With `panel_parallel: true` (default), send
   all lens invocations in a single tool-call batch so they run
   concurrently. For each lens, the orchestrator constructs the prompt as
   four blocks in this order:

   a. **Cross-cutting bias injections** (verbatim from
      `references/panel-prompts.md` § "Cross-cutting bias injections"):
      Chain-of-Verification, negative-constraint phrasing, "Could you be
      wrong?" metacognitive check. These three apply to EVERY lens; do
      not skip.
   b. **Per-lens body** (verbatim from the corresponding section of
      `references/panel-prompts.md`).
   c. **Anti-overlap clause** (verbatim from
      `references/panel-prompts.md` § "Anti-overlap boundary clauses"),
      with the list of other-lens names + 1-line summaries filled in
      from the active roster.
   d. **Task + plan + ledger payload** as input to the lens.

   Then dispatch:
   - For lenses backed by an `Agent`: call `Agent` with the corresponding
     `subagent_type`.
   - For lenses backed by skills (e.g. `sc:spec-panel`, `sc:estimate`):
     call the skill via `Skill(...)` with the constructed prompt as
     args, or drive a sub-turn with the prompt directly if the skill
     doesn't support a one-shot critic contract.
   - For `openai`: `bash scripts/openai_critic.py` exactly as in v1
     (the cross-cutting injections are already baked into the openai
     critic's own prompt; do not double-inject).
   - For the 7 inline lenses (#16-22): inline the constructed prompt as
     a sub-turn in the qPlan run, since no installed skill backs them.

4. **Per-lens JSON.** Each lens returns the contract from
   `panel-prompts.md`:
   ```json
   { "verdict": "...", "suggestions": [ { "text": "...", "tier_hint": "..." } ] }
   ```
   Record each raw response under its own subsection in `transcript.md`:
   `#### Round N · critic · <lens>`.

5. **Merge.**
   - Concatenate all per-lens `suggestions[]` into one list. Tag each
     suggestion with `source_lens: "<lens name>"`.
   - Compute the merged `verdict` as the worst of the per-lens verdicts:
     `major issue` > `minor issue` > `no material issue`.
   - Pass the merged list into the existing ledger semantic-match step
     (loop step `c. LEDGER SEMANTIC MATCH`). The ledger collapses cross-
     lens duplicates: two lenses raising the same point semantically
     become one ledger entry with `repeat_count` += 1 and a
     `source_lenses: ["<a>", "<b>"]` list on the ledger entry.

6. **From here, run the v1 loop unchanged.** The author reacts
   (accept/reject + apply), the tier rubric classifies accepted
   suggestions, `no_progress` updates, and the termination check fires
   in the same order.

### When to use which provider

- **`panel` (default)** — non-trivial design / architecture work that
  benefits from multiple specialist lenses.
- **`claude`** — quick deepening pass on a small plan where the panel
  overhead is not worth it, or when reproducing a v1 run for comparison.
- **`openai`** — explicit cross-model provider check, no panel. Useful
  when the v1 OpenAI critic already surfaced a real disagreement worth
  isolating.

### Failure modes specific to panel mode

- **Lens unavailable.** If a lens's backing agent or skill doesn't exist
  on this install (e.g. `business-panel-experts` missing), log a one-line
  note in the transcript, drop that lens from this round's roster, and
  continue — provided the min-lens guard still passes after the drop.
- **Lens returns malformed JSON.** Log the raw output, drop the lens for
  this round, and re-check the min-lens guard.
- **All lenses return `no material issue`.** This is a strong convergence
  signal. The merged verdict is `no material issue`. The loop still runs
  the termination check; do not skip it.
- **OpenAI key missing.** The `openai` lens fails loud. The user can opt
  out by removing `openai` from `panel_lenses`; the panel does NOT
  silently drop it.

## Do not

- Do not skip the termination check after a round, even if the critic
  verdict is `no material issue`. The verdict alone does not suffice — the
  ledger + counters are the backstop.
- Do not classify your own changes as Editorial just to make the loop stop,
  or as Structural to justify another round. The rubric or arbiter decides;
  you log.
- Do not match ledger entries lexically — the critic rephrases. Always do
  the semantic check with the ledger pinned verbatim.
- Do not silently fall back from `openai` to `claude` when the API key is
  missing. The whole point is provider comparison; failing loud preserves
  signal.
- Do not edit code files in Phase A. The transition to Phase B is the moment
  a code file is touched, and that flips the termination rule from
  `max_concept_rounds` to `no_progress >= K`.
- Do not add features beyond v1: no outcome attribution, no embedding
  similarity service, no browser-based OpenAI access. These are on the
  user's deferred list and get decided after running the prototype on real
  tasks.
- Do not auto-chain a second `/qPlan` run in the same response after one
  converges. Even if the args appear to contain a second plan or a fresh
  brainstorming task, the convergence of run #1 ends your turn. Surface the
  closing summary, name the apparent second task explicitly ("I notice the
  args also contain X — should I start a fresh `/qPlan` on it?"), and wait
  for the user. Auto-chaining hides scope from the user and silently
  reinterprets the invocation, which is the same failure mode the
  MUST/MUST NOT block was added to prevent.
