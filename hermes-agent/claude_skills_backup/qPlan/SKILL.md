---
name: qPlan
description: Run a guaranteed-terminating author↔critic iteration loop to deepen a plan. qPlan is the BRAIN — it plans and decides (including the OpenAI cross-model panel) and is strictly PLAN-ONLY; it never executes or modifies the codebase. Each suggestion is tracked in a semantic ledger, each accepted change classified by materiality tier, and the loop stops when real progress ends — not when refinement ends. To EXECUTE a plan (autonomously, with or without variants), use /qGoal, which calls qPlan for its decisions. Invoked via /qPlan (canonical) OR any case variant — /qplan, /Qplan, /QPlan, /QPLAN all map to this same skill (case-insensitive). If the user types any of these, treat as a /qPlan invocation and proceed with this skill's state machine.
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

**Related skills.** To *seed* a plan from an existing codebase, run the `improve`
skill first — it audits read-only and emits prioritized, self-contained plans;
feed those into `/qPlan` as the input plan to deepen. The `pragmatism` lens above
carries the **ponytail** minimal-code discipline; for a standalone over-engineering
pass on a draft use `ponytail-review`. Net: `improve` finds *what* is worth doing,
`/qPlan` hardens *how*, and ponytail keeps it from bloating.



## MUST/MUST NOT:
    - MUST: bemeneti tervet kritikusi iterációba veszi, akkor is ha "implementálni készen" tűnik
    - MUST NOT: tervet execute-ol, fájlokat módosít a kódbázisban, commit-ol — a végrehajtás a /qGoal feladata (az hívja vissza a qPlan-t a döntésekhez). qPlan SOHA nem hajt végre.
    - Ha az args execution-szerű ("implement", "csináld", "ok", "ok tovább", "tovább", "phase 0→1→2"), stop + 1 kérdés, nem reinterpret — vagy javasold a /qGoal-t, ha a user tényleg végrehajtást kér
    - MUST: egy `/qPlan` hívás = egy plan-fájl bemenet = egy iteráció run = egy workdir. Ha az args több plan-fájlra hivatkozik, vagy egy run convergencia után egy *új* brainstorming task is megjelenik a payload-ban, **állj meg és kérdezz** (mint Round 0-ban A/B/C disambiguation-nel) — ne chain-elj automatikusan egy második qPlan futtatást ugyanabban a válaszban. Egy futtatás convergencia után = STOP + handoff a user-nek; a user dönti el indít-e új `/qPlan`-t.


## `/qPlan auto` is RETIRED — use `/qGoal`

The old `/qPlan auto` mode (an Arbor-fused autonomous optimization loop that
executed code) has been **removed**. Execution does not belong in the planner:
qPlan is the brain, `/qGoal` is the hands. Everything `/qPlan auto` did — running
code, multiple variants, metric optimization, merging winners — now lives in
`/qGoal`, which calls qPlan back for its decisions (so qPlan still drives the
judgment, including OpenAI, it just no longer executes).

Routing: if the user's invocation is `/qPlan auto ...` (or `auto` is the first
arg, any case), do NOT run the state machine below. Tell the user it moved and
hand off: "`/qPlan auto` is now `/qGoal` — running `/qGoal <goal>`," then invoke
`Skill(skill="qGoal", args="<goal>")`. Everything else (`/qPlan <plan>` with no
`auto`) runs the plan-only state machine in this file, and the MUST NOT-execute
rule holds.

## Configuration

The user's `/qPlan` invocation may begin with a YAML config block. Defaults
if absent:

```yaml
critic_provider: panel         # panel | claude | openai
                               # panel (DEFAULT) = max-mode multi-lens critic fleet
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
  - pragmatism                 # karpathy-guidelines + ponytail (YAGNI / minimal-code: does this need to exist? stdlib/native/one-line before custom)
  - spike                      # hermes-spike
  - decomposition              # oc-to-issues
  - socratic                   # socratic-mentor (questions, not assertions)
  - openai                     # cross-model voice via openai_critic.py (OPENAI_API_KEY)
  - deepseek                   # cross-model voice via deepseek_critic.py (DEEPSEEK_API_KEY)
  - subq                       # FULL-CONTEXT voice via subq_critic.py (SUBQ_API_KEY) — ~1M/12M ctx, feed it large context
  - subq-free                  # same subq_critic.py, free tier (tier:free) — the no-key/free-endpoint full-context voice
  - claude-direct              # TRUE Claude voice via claude_critic.py — independent of session provider; the real-Claude lens when running on GLM
  - glm                        # TRUE GLM voice via glm_critic.py (GLM_API_KEY/ZAI_API_KEY) — paid flagship; the real-GLM lens when running on Claude
  - glm-free                   # same glm_critic.py, free tier (model: glm-4-flash) — a free GLM voice alongside the paid one
  # ----- 7 research-derived lenses (2024-2026 multi-agent planning research) -----
  - spec-conformance           # MAST: drift vs original ask (21% of multi-agent failures)
  - executable-check           # LLM-Modulo: cheapest thing actually runnable
  - premortem                  # "Could you be wrong" + failure-narrative form
  - test-contract              # MetaGPT QA: acceptance tests pre-implementation
  - drift-anchor               # Counter multi-round debate drift (round-3+ only)
  - pareto-variants            # GEPA: variants on different axes (Phase A only)
  - bias-audit                 # Audit ledger for momentum / suggester-preference (round-4+ only)
panel_parallel: true           # fire the INTERNAL (Claude-side) lenses in parallel via Agent tool
panel_min_lenses: 7            # below this after mute heuristics → config error
panel_bias_injections: true    # CoVe + negative-constraint + "could you be wrong"
                               # applied to every lens prompt by the orchestrator
provider_relay: true           # cross-model AI voices critique SEQUENTIALLY, not all at once:
                               # send the plan to ONE AI, apply its fixes, pass the IMPROVED
                               # plan to the NEXT AI, around the circle until it comes back
                               # (see "Provider relay mode"). false = every voice sees the same
                               # plan version (legacy parallel merge). Independent of
                               # panel_parallel, which still governs the internal Claude lenses.
relay_order:                   # order the provider voices take their turn (active + available only;
                               # the orchestrator dedups so each provider appears once per lap)
  - claude-direct              # the real Claude voice (or the session `claude` lens on Anthropic)
  - openai
  - deepseek
  - glm                        # paid GLM (or the session `claude`=GLM voice when running on GLM)
  - glm-free
  - subq
  - subq-free                  # free SubQ voice (tier:free) — joins the circle when configured/keyless
openai_backend: api            # api | browser
                               #   api     = OpenAI HTTP API (needs OPENAI_API_KEY)
                               #   browser = drive the logged-in ChatGPT web
                               #             session via Playwright — NO API key
                               #             (rides your ChatGPT subscription).
                               #             One-time: `python scripts/openai_critic.py --login`.
                               #             Also set via env QPLAN_OPENAI_BACKEND=browser.
model: <provider default>      # claude: current session
                               # openai: auto-pick best /v1/models entry
                               # (gpt-5.5 > gpt-5.1 > gpt-5 > o3-pro > o3 > ...,
                               # cached 24h in ~/.claude/.qplan_openai_model_cache.json;
                               # set this field to lock a specific model)
max_concept_rounds: 8          # Phase A cap
K: 5                           # no_progress cap in Phase B
hard_cap_rounds: 20            # unconditional global cap
author_prefix:  "Erről mit gondolsz?:"
critic_prefix:  "Erről mit gondolsz? Hol javítanád?:"
```

`critic_provider: openai` (and the `openai` lens inside `panel` mode) need
EITHER an OpenAI credential path, depending on `openai_backend`:

- **`api` (default)** — requires `OPENAI_API_KEY`. The script fails loud if the
  key is missing — it does NOT silently fall back to `claude`, because the whole
  point of provider comparison is to keep them distinguishable.
- **`browser`** — requires NO API key. It drives the **logged-in ChatGPT web
  session** via Playwright, riding your ChatGPT subscription. One-time setup:
  `python scripts/openai_critic.py --login` (opens a browser; log in once, the
  session persists in `~/.claude/.qplan_chatgpt_profile`). Then run qPlan with
  `openai_backend: browser` (or env `QPLAN_OPENAI_BACKEND=browser`). Needs
  Playwright: `pip install playwright` then `playwright install chromium`.
  HONEST CAVEAT: automating the ChatGPT web UI is against OpenAI's ToS, is
  brittle (UI / Cloudflare changes can break it), and is slower than the API —
  any failure just **mutes** the lens (exit 2) instead of crashing the round.
  Env knobs: `QPLAN_OPENAI_BROWSER_HEADLESS=1` (try headless; ChatGPT often
  blocks it, default is headed), `QPLAN_CHATGPT_PROFILE_DIR` (override/kill the
  saved profile location).

### Cross-model lenses are opt-in — mute, don't fail, when a key/backend is missing

Each cross-model lens has its own provider script and credential. A lens whose
credential/backend is unavailable is **silently muted** from the panel for that
run (it does NOT fail the round — same spirit as `/qRev`'s multi-provider policy).

**Budget-exhaustion fallback (a valid key but a dead balance must NOT stop the
round).** When a paid provider's key is present but its balance/quota is
exhausted (HTTP 402, or 429 with an insufficient-quota/-balance body), the round
keeps going by switching that provider to a keyless/free path where one exists,
rather than just muting:

- **`openai`** — on budget exhaustion the api backend automatically falls back
  to the **browser** backend (the logged-in ChatGPT web session, no balance
  needed). Disable with `QPLAN_OPENAI_NO_BROWSER_FALLBACK=1` (then it mutes).
  Needs the one-time `--login`; if not logged in it mutes.
- **`glm`** — on budget exhaustion it retries on the **free model**
  (`glm-4-flash`, override `GLM_FREE_MODEL`) on the same key. Disable with
  `QPLAN_GLM_NO_FREE_FALLBACK=1`.
- **`deepseek`** — has **no** free/keyless tier, so there is nothing to fall
  back to: budget exhaustion mutes just this one lens and the round continues
  with the remaining providers.

The roster of external voices:

| Lens | Script | Needs | Notes |
|---|---|---|---|
| `openai` | `scripts/openai_critic.py` | `OPENAI_API_KEY` (api backend) **or** a one-time `--login` (browser backend, no key) | api backend auto-picks highest gpt-5.x / o-series. `openai_backend: browser` rides the logged-in ChatGPT web session via Playwright instead (no key, ToS-gray, brittle, mutes on any failure). |
| `deepseek` | `scripts/deepseek_critic.py` | `DEEPSEEK_API_KEY` | auto-picks highest DeepSeek |
| `subq` | `scripts/subq_critic.py` | `SUBQ_API_KEY` | OpenAI-compatible (`https://api.subq.ai/v1`, model `subq-preview`). **Full-context lens** — ~1M (12M gated). Feed it MORE context than other models can hold: whole files, large reference docs, prior rounds. "Use the huge budget cleverly" = route the big-context judgment here. Override base/model via `SUBQ_BASE_URL` / `SUBQ_MODEL`. |
| `subq-free` | `scripts/subq_critic.py` | `SUBQ_FREE_API_KEY` **or** `SUBQ_FREE_BASE_URL` | Same script, **free** tier for the no-paid-key case: call with `tier: "free"`. Sends WITHOUT an `Authorization` header when keyless, so it lights up the moment SubQ offers a free key or a keyless free endpoint. Honest limit: SubQ has no known keyless free tier today, so `subq-free` mutes until `SUBQ_FREE_API_KEY` or `SUBQ_FREE_BASE_URL` (+ optional `SUBQ_FREE_MODEL`) is set. |
| `claude-direct` | `scripts/claude_critic.py` | `ANTHROPIC_API_KEY` **or** the `claude` CLI | TRUE Claude voice, independent of the session provider. Backend auto-select: `api` if `ANTHROPIC_API_KEY` set, else `cli` = shells out to `claude -p` with the GLM env stripped, using the Claude **subscription**. CLI model chain opus->sonnet->haiku (graceful fallback so a $20/Pro plan that lacks Opus still yields a Claude voice); override the head with `CLAUDE_CRITIC_CLI_MODEL` or per-call `model`. Force backend with `CLAUDE_CRITIC_BACKEND=api\|cli`. |
| `glm` | `scripts/glm_critic.py` | `GLM_API_KEY` **or** `ZAI_API_KEY` | TRUE GLM voice, independent of the session provider — the RECIPROCAL of `claude-direct`: a real GLM opinion when qPlan runs on Claude. Paid flagship, auto-discovered (glm-5.x > glm-4.6 ...). OpenAI-compatible endpoint `GLM_BASE_URL` (default z.ai). Lock a model with `GLM_MODEL` or per-call `model`. |
| `glm-free` | `scripts/glm_critic.py` | `GLM_API_KEY` **or** `ZAI_API_KEY` | Same script, **free** tier: pass `model: glm-4-flash` (override via `GLM_FREE_MODEL`). A free GLM voice that runs alongside the paid `glm` lens, so the panel hears both the paid and the free GLM. |

### GLM-awareness — get a real Claude voice even while running on GLM

When the session runs on GLM (z.ai) — launched via `claude-glm.ps1`, detectable
because `ANTHROPIC_BASE_URL` points at z.ai / bigmodel, `ZAI_API_KEY` is set, or
the active model id is a GLM id — the built-in `claude` lens ("current session")
is actually **GLM**, not Claude. So on GLM, qPlan must reason with EVERY available
model rather than letting the GLM session stand in for Claude:

1. The `claude` lens = the GLM session voice (keep it; it is the running model).
2. ADD the `claude-direct` lens so a genuine highest-Claude-model voice is in the
   panel. With no `ANTHROPIC_API_KEY`, `claude_critic.py` uses the `cli` backend:
   it spawns `claude -p` with the GLM overrides stripped, so that subprocess runs
   on the Claude **subscription** (the "use my Claude subscription while running
   in Claude Code on GLM" path the user asked for).
3. Keep `openai`, `deepseek`, and `subq` lenses on (whichever keys exist).

Net effect on GLM: qPlan's decisions are cross-checked against GLM (session) +
real Claude (subscription via `claude -p`) + OpenAI + DeepSeek + SubQ
(full-context) — every AI tool that is reachable. On Anthropic (normal launch)
the `claude` lens already IS the real Claude, so `claude-direct` is redundant and
may be dropped unless you explicitly want a second, differently-prompted Claude
pass — but the `glm` and `glm-free` lenses are NOT redundant there: they add the
reciprocal GLM voice so a Claude-launched qPlan still asks GLM (paid + free) for
an opinion, mirroring the GLM->Claude path. This cross-provider awareness applies
transitively to `/qGoal`, which calls qPlan for its decisions.

**Reciprocal (Claude session -> consult GLM).** The mirror of the path above: on
a normal Anthropic launch, `glm_critic.py` reaches z.ai independently of the
session, so the panel hears GLM even while running on Claude. `glm` = the paid
flagship (auto-discovered); `glm-free` = the same script with `model: glm-4-flash`
so a FREE GLM voice sits alongside the paid one. Both need only `GLM_API_KEY` (or
the launcher's existing `ZAI_API_KEY`); with no key, both mute. Honest limit on
the OTHER direction: a Claude **subscription is not an API key**, so the GLM-side
session can only get a real Claude voice through `claude -p` (the `cli` backend),
which requires Claude Code to be permitted on that plan — a $20/Pro plan runs it
on Sonnet (Opus limited), so `claude-direct` lands on Sonnet there via the
fallback chain; if Claude Code is blocked on the plan entirely, the only Claude
paths left are an `ANTHROPIC_API_KEY` (pay-per-token) or manual copy-paste.

Caveats (state them honestly, do not over-promise): the `cli` subscription path
assumes `claude -p` headless mode is available (Claude Code >= 2.x) and that
stripping the GLM env restores the subscription auth — if that subprocess fails
for any reason, the lens is muted (never blocks the round). The SubQ 12M tier is
gated to research/enterprise; `subq-preview` (~1M) is the default. Kill switches:
unset the relevant key, drop the lens from `panel_lenses`, or
`CLAUDE_CRITIC_BACKEND` / `SUBQ_MODEL` overrides.

**Model auto-discovery.** When no `model:` is set in the config block, the
OpenAI critic queries `GET /v1/models` once per 24 h and picks the highest-
priority chat model the key can reach, walking the `MODEL_PRIORITY` table in
`scripts/openai_critic.py` (`gpt-5.5` > `gpt-5.1` > `gpt-5` > `o3-pro` > `o3`
> `gpt-5-mini` > `gpt-4.1` > `o1` > `o3-mini` > `gpt-4.1-mini` > `gpt-4o` >
`gpt-4o-mini` > `o1-mini`). Within a family the un-dated stable alias wins,
so as OpenAI re-points e.g. `gpt-5` at a new snapshot the critic follows
without code changes. Pick is cached in
`~/.claude/.qplan_openai_model_cache.json`; force a refresh with
`QPLAN_OPENAI_MODEL_REFRESH=1` or by deleting the file. Set `model:` in the
config block to lock a specific model and skip discovery entirely.

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

Max mode is deliberately costlier than a single-critic turn — the trade is
breadth of coverage. The ledger's cross-lens semantic match collapses
duplicate points into single entries with `source_lenses: [...]` and
`repeat_count` rising faster, so cross-lens corroboration becomes a
stronger "this is real" signal than any single critic could produce. For
trivial work (config tweaks, one-file edits), use `critic_provider: claude`
or just `/think` — the panel is overkill there.

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

### 4. Emit curator signal

After the closing summary is written (and BEFORE you hand the chat back to
the user), call the curator-emit helper with the workdir path:

```bash
"C:\Python313\python.exe" "C:\Users\[USER]\.claude\scripts\qplan_curate_emit.py" "<absolute workdir path>"
```

The helper distills the highest-signal parts of this run's `state.json` +
`ledger.jsonl` (accepted Structural/Behavioral suggestions, rejected
suggestions with `repeat_count >= 3`) and appends them to
`~/.claude/.hermes_qplan_curator_queue.json`. The `hermes-curate` skill
picks these up the next time it drains. The helper is fail-soft: if it
prints `{"status": "skipped"...}` because there were no Structural/
Behavioral acceptances and no repeated rejections in this run, that's a
valid outcome — do not retry, do not panic. Just continue.

Do NOT mention the emit call to the user; it is silent bookkeeping like
the closing summary. The user only sees the one-screen chat summary.

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

### Provider relay mode (sequential cross-model refinement)

When `provider_relay: true` (default), the **cross-model AI voices do NOT all
critique the same plan version at once**. Instead the orchestrator (the Claude
working in Claude Code) sends the plan to ONE provider at a time, applies that
provider's accepted fixes, and passes the IMPROVED plan to the next provider —
around the circle until it comes back. This is the "egyenként, javítva,
továbbküldve, míg körbeér" behavior: each later voice reviews an already-better
plan, so corroboration and incremental refinement accumulate instead of N
providers redundantly flagging the same first-draft issues.

This applies ONLY to the cross-model **provider** voices (the distinct AIs:
`claude-direct`, `openai`, `deepseek`, `glm`, `glm-free`, `subq`, and the session
`claude` voice). The 22 internal Claude-side lenses (architecture, risk, premortem,
…) are NOT separate AIs and still run per `panel_parallel` — relay does not change
them.

**Relay procedure** (replaces step 3's parallel fan-out for the provider voices
when `provider_relay: true`):

1. **Build the lap order.** Take `relay_order`, drop any voice whose
   key/backend is unavailable (mute, exactly as in parallel mode), and dedup so
   the active provider is represented once — on Anthropic the session `claude`
   lens stands in for `claude-direct`; on GLM the session `claude` lens stands in
   for `glm`, and `claude-direct` supplies the real Claude. If fewer than 2
   provider voices survive, relay is pointless: fall back to the normal
   single/parallel critic turn for this round and note it in the transcript.
2. **Seed.** `current_plan = plan.md` at the start of the lap.
3. **For each provider voice V in lap order:**
   a. Send V the **current** plan + task + ledger (V's own script/agent, same
      per-voice prompt + bias injections as parallel mode). Get its
      `{verdict, suggestions[]}`.
   b. Run the ledger semantic-match (loop step `c`) on V's suggestions against
      the live ledger, tagging `source_lens: V`. Cross-lap duplicates collapse
      and bump `repeat_count` just as before.
   c. **Author reacts and applies** (loop step `d`): accept/reject each new
      suggestion with a one-line rationale; apply accepted ones to `plan.md`
      (and code files in Phase B). Tier-classify accepted changes (step `e`).
      This produces an improved plan.
   d. `current_plan = plan.md` (the improved version) — and THAT is what the
      next voice V+1 receives. Record a `#### Round N · relay · <V>` subsection
      in the transcript with V's raw verdict and the resulting plan delta.
4. **Lap close ("körbeér").** One full pass = one critic turn. The round's
   merged verdict is the worst of the per-voice verdicts. `no_progress` updates
   from the lap's accepted tiers, and the termination check fires in the normal
   order. If the loop continues, the next round runs another lap (the circle goes
   around again on the now-better plan) until qPlan converges or a cap trips.

**Honest trade-off.** Relay is slower and more token-heavy than parallel (voices
run in series, and the plan is re-sent, growing, each hop), and the *first* voice
in the order never sees another AI's improvements within a lap — order has mild
influence, which is why `relay_order` leads with the strongest general voice.
In exchange you get cumulative cross-model refinement and far less duplicate
noise. For a quick pass set `provider_relay: false` (parallel merge) or use
`critic_provider: claude`.

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
