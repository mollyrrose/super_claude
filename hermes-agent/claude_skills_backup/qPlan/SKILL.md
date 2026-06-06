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
critic_provider: claude        # claude | openai
openai_backend: api            # api | browser (browser is a stub in v1)
model: <provider default>      # claude: current session; openai: gpt-4o
max_concept_rounds: 8          # Phase A cap
K: 5                           # no_progress cap in Phase B
hard_cap_rounds: 20            # unconditional global cap
author_prefix:  "Erről mit gondolsz?:"
critic_prefix:  "Erről mit gondolsz? Hol javítanád?:"
```

`critic_provider: openai` requires `OPENAI_API_KEY`. The script fails loud if
the key is missing — it does NOT silently fall back to `claude`, because the
whole point of provider comparison is to keep them distinguishable.

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

Append a `### Round N · critic` block with the raw JSON.

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

The critic prompt contains the explicit instruction that `no material issue`
is a *valid and correct* outcome, not a failure to find something. Models are
pulled to find "one more thing" by default; this counters that pull. The
backstop is still the ledger + counters — the verdict alone does not suffice.

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
