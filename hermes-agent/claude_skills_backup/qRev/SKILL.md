---
name: qRev
description: Deep review of what you're about to commit — runs `/qMin`'s 5-axis check + the full 3-pass multi-agent fleet on the **uncommitted diff** (staged + unstaged), then synthesises both into a single P0/P1/P2/P3 punch-list. The fleet is ALWAYS run in full (the complete roster, up to the 15-agent cap) — there is no reduced/subset mode; the depth formerly called "exhaustive" is the only depth. Optional `topic:<name>` arg still runs the COMPLETE fleet but emphasises one lens (security / db / perf / ml / tests) in the report. Invoked via /qRev (canonical) OR any case variant — /qrev, /Qrev, /QRev, /QREV all map to this same skill (case-insensitive). If the user types any of these, treat as a /qRev invocation and proceed with this skill.
---

# qRev — Quick Review (qMin + full multi-agent fleet, fused)

**qRev is always full-depth — there is no "exhaustive" toggle and no lighter qRev.** The complete agent fleet (every applicable agent in the roster, up to the hard cap of 15 parallel agents per pass) runs on every `/qRev`. You cannot cherry-pick a few agents out of it: it is all-or-nothing by design. The `topic:<name>` arg does NOT shrink the fleet — it keeps the whole roster and only changes which lens the report emphasises. The only thing any argument changes is the **scope** (which files), never the **size** of the fleet.

**Case-insensitive invocation:** `/qRev`, `/qrev`, `/Qrev`, `/QRev`, `/QREV` are all the same skill. Treat any of them as a `/qRev` call and proceed below.

## When to use

You'd otherwise type two commands (`/qMin`, then `/rev exhaustive`) on the same state. Reach for `/qRev` instead and get a single fused report.

For lighter checks, the original commands are still right:
- per-commit / single diff only -> `/qMin`
- single-pass (no exhaustive) review -> `/rev` (no args)
- post-implementation validation -> `/check`
- root-cause one specific failure -> `/hunt`

## Review depth — whole-file + full context, NOT diff-only (read this first)

`/qRev`'s review must reach the same depth `/qPlan` ("ultra plan") reasons at: it does **not** stop at the diff hunks and their few surrounding lines. For every file in scope, the agent-driven phases (Phase 0 `qMin` and Phase B fleet) read the **entire file** and then trace its **full context** before judging the change. Concretely, for each changed file the reviewer must:

- **Read the whole file end-to-end**, not just the changed hunks — a diff line is only correct relative to the module it lives in (its invariants, error handling, lifecycle, existing patterns).
- **Follow the dependency context outward** — the imports the file pulls in, the call sites that reach the changed symbols (callers), the functions/classes the change calls (callees), subclasses/implementers, and the config/schema/fixtures/tests bound to the changed code. Read those related files too when the change's correctness depends on them. The point is to catch cross-file consequences a diff-local read cannot see (a caller that now passes the wrong shape, an invariant held elsewhere, a test that silently no longer exercises the path).
- **Judge the change against the file's and module's actual behaviour**, not against the hunk in isolation.

This is the core of what makes `/qRev` deeper than a per-commit `/qMin` glance. The diff tells you *what changed*; the whole file + its context tells you *whether that change is correct where it lands*. When scope is large and reading every dependency in full would blow the budget, read the directly-changed files in full unconditionally, and pull in dependency files by relevance (closest call sites and the contracts the change touches first) — and record in the report's "Coverage gaps" section any context you could not fully read, rather than silently reviewing diff-only.

**Exception — Phase A stays changed-lines-only by design.** The deterministic gate (semgrep + `CODING_STANDARDS.md` non-negotiable rules) already scans whole files at the tool level, and its LLM standards check is intentionally a cheap changed-lines pass. Do not widen Phase A; the whole-file + context depth applies to the *agent-driven* phases (0 and B).

## What to do

Run **three** phases in order. Each later phase inherits earlier phases' findings as context.

### Phase 0 — qMin on the pending diff (NEW, runs first)

Apply the full `/qMin` skill verbatim to the **uncommitted diff** (staged + unstaged) — i.e., exactly what the user is about to commit. Read `~/.claude/skills/qMin/SKILL.md` and follow its "What to review" and "Output" sections exactly.

Apply the five axes at the **whole-file + full-context depth** from the "Review depth" section above — for each changed file, read the entire file and trace its dependency context (callers, callees, imports, bound config/schema/tests), not just the diff hunks. The diff defines *what to focus on*; the surrounding file and its context define *whether the change is correct there*.

Five axes (from qMin):

1. **Minimal scope (ponytail lens)** — every changed line load-bearing for the task; flag unrelated refactors/renames/formatting/"while-I'm-here" cleanups. Carries the ponytail decision ladder (YAGNI -> stdlib -> native -> existing dep -> one line -> minimum); for a dedicated over-engineering sweep the `ponytail-review` / `ponytail-audit` skills are available.
2. **Correctness** — does the change do what it claims; trace call sites; check edge cases.
3. **Security** — new input handled without validation at a trust boundary; new secrets/tokens/PII paths; injection risk (shell/SQL/path); permission downgrades.
4. **Maintainability** — new abstractions justified by ≥2 concrete uses; names accurate; comments explain *why*; dead code removed.
5. **Quality** — type safety preserved; errors handled at boundaries (not swallowed); tests still pass / new behaviour covered.

Output of Phase 0 is one of:
- **Pass** — proceed.
- **Pass with notes** — listed notes.
- **Block** — listed blocking issues with `file:line`.

If Phase 0 returns **Block**, **state the blockers, ask the user**: continue to Phase A/B anyway (deeper review on broken code), or stop and fix Phase 0 blockers first. Default to **stop** if the user does not answer — exactly as the corresponding `/qMin` "Block" verdict implies.

If Phase 0 returns Pass or Pass-with-notes, continue immediately to Phase A.

### Phase A — `/rev`'s deterministic gate (semgrep, with retry loop)

Invoke `/rev`'s **Phase A** verbatim (read `~/.claude/skills/rev/SKILL.md`, "Phase A — Deterministic gate" section). Semgrep + `CODING_STANDARDS.md` non-negotiable rules. Findings go to `<repo>/.claude/review-log/findings.jsonl` with `source: "semgrep"` / `source: "rev-standards"`.

**Use the helper `~/.claude/scripts/lib/run_semgrep_loop.py` instead of calling `semgrep` directly.** The helper handles three failure modes that have broken inline semgrep invocations in real sessions:

1. Semgrep returns non-zero on any per-file error but still emits valid JSON on stdout — naive `subprocess.run(check=True)` loses every finding. The helper parses stdout regardless.
2. A single bad file (e.g. one with a syntax error semgrep can't recover from) takes down the entire batch. The helper isolates the offending file (best-effort path extraction from stderr, binary-search fallback otherwise) and retries the rest. Max 3 retries.
3. Large scope (>60 files) overflows argv on Windows. The helper batches.

Invocation pattern:

```powershell
$scope = ".scratch/qrev-scope.txt"   # written by the qRev runner: one path per line, --diff-filter=AM applied
python "$HOME\.claude\scripts\lib\run_semgrep_loop.py" `
  --config .semgrep.yml `
  --config p/security-audit `
  --repo-root . `
  --scope-file $scope `
  > .scratch/qrev-semgrep.json
```

Then parse the JSON: `results[]` is the merged finding list, `skipped[]` is the list of files the helper had to give up on (record these in the report's "Coverage gaps" section, do NOT silently drop them).

If Phase A returns **SHIP-BLOCK** (any `blocking` finding), the overall qRev verdict is SHIP-BLOCK regardless of Phase 0 / Phase B. Print Phase 0 + Phase A combined report and stop.

Otherwise continue to Phase B.

### Phase B — the full 3-pass agent fleet (always runs in full)

Run the complete 3-pass agent fleet — read `~/.claude/skills/rev/SKILL.md`, "`/rev exhaustive` (3-pass)" section, and use it purely as the **definition of the roster** for the three passes. There is no other depth: qRev has no single-pass or reduced-fleet mode, so "which depth" is never a decision — Phase B is always all three passes with the complete roster. All three passes run with the same skill-bundle map, agent roster, and synthesis rules. **Pass-1 inherits Phase 0 findings as context** — the agents must see them so they don't re-derive the same issues.

**Whole-file + context directive for every agent.** When constructing each agent's prompt from `/rev`'s "Agent prompt template", inject the depth requirement from the "Review depth" section above into the agent's instructions: the `SCOPE` file list is the set of changed files, but each agent MUST read every scope file **in full** and trace its **dependency context** (callers, callees, imports, subclasses/implementers, and the config/schema/fixtures/tests bound to the change) — not review the diff hunks in isolation. Add these lines to the agent prompt's `YOUR FOCUS` block:

```
REVIEW DEPTH (mandatory): The SCOPE files are what CHANGED, not the limit of what you READ.
- Read each SCOPE file end-to-end before judging any change in it.
- Follow the change outward: open the call sites that reach the changed symbols,
  the callees the change invokes, and the config/schema/tests bound to it. Read
  those files when the change's correctness depends on them.
- Judge each change against the file's and module's real behaviour, not the hunk
  alone. Diff-local-only findings are insufficient — cross-file consequences are
  the point of this pass.
- If scope is too large to read every dependency in full, read the directly
  changed files fully and pull dependencies by relevance; list what you could not
  fully read under "Coverage gaps" instead of silently reviewing diff-only.
```

If a `topic:<name>` arg was passed, the agent roster is **NOT** filtered — every pass still runs its complete roster. The topic only changes *emphasis*: tell the agents the named lens (security / db / perf / ml / tests) is the priority focus for this run, and order/highlight the topic-relevant findings first in the synthesis. You still get the full 3-pass coverage; topic just foregrounds one lens in the report. See the argument-forms table below.

**Run the COMPLETE roster — every agent, every pass. This is non-negotiable, with no exceptions.** Every `/qRev` (including `topic:<name>`) runs the **full roster across all three passes — every applicable agent, up to the hard cap of 15 parallel agents per pass** (Pass 1 quality/correctness, Pass 2 security, Pass 3 architecture+DB+perf+tests, per `/rev`'s "`/rev exhaustive` (3-pass)" list). **When Codex Challenge is enabled (via `QREV_CRITIC_PROVIDERS=...,codex` or `QREV_CODEX_CHALLENGE=1`), Codex Challenge runs as an additional agent in Pass 2 (security-focused), subject to the same concurrency cap.** Dispatch the full roster for each pass. Do **not** silently drop, sample, narrow, or "pick a few representative" agents — not to save time, not for a topic, not for any reason. The roster is bound together: it runs whole or the run is invalid.

**Any hand-picked subset of the roster is a VIOLATION — there is no longer ANY sanctioned way to run fewer agents.** If you catch yourself about to launch "qRev fleet (3 lenses)" — e.g. just security + typescript + code-reviewer — stop: that is a plain `/rev`, not `/qRev`. The whole point of `/qRev` is the full multi-pass coverage. The old `fast` mode (Phase A only, no fleet) and the old `topic:`-narrowing behaviour have both been removed precisely so the fleet can never be reduced: `fast` no longer exists, and `topic:` keeps the entire roster. Launch the roster in **batched waves** (see "Batched execution" right below) — every agent still runs, just not all 15 in one simultaneous burst. A missing agent is a missing lens, and an incomplete fleet means the qRev did not actually run — re-launch the missing agents rather than reporting on a partial fleet.

**Batched execution (5×3) + pipelined fixes — run all 15, but bound the system load.** Firing 15 subagents in one simultaneous burst spikes CPU/RAM. So launch the COMPLETE roster in **waves**, not all at once: the three passes are the natural batches. "5×3" is a round mnemonic, **not** an exact 5/5/5 — the passes are roughly Pass 1 ≈5, Pass 2 ≈4, Pass 3 ≈6 (≈12–15 distinct agents, adaptive; `15` is the per-pass parallel hard cap, and `/rev`'s own table counts ~18–22 agent-runs across the 3 passes). The wave logic does not depend on an even split: cap concurrency at ~5 agents in flight at a time (override with `QREV_FLEET_CONCURRENCY`, default 5; drop it to 3 on a loaded machine). This changes only the *scheduling*, never the *roster* — all 15 still run; you are throttling how many run at once, not dropping any. If a pass's roster exceeds the cap (Pass 3 can be 6), split that pass into sub-waves of ≤ the cap.

Pipeline the waves with the fixing so the machine is never both fully reviewing AND idle-waiting:

1. Launch wave 1 (≤ cap agents, one message / multiple Agent calls). When it returns, **print wave 1's findings** (preserve show-before-fix at wave granularity), then START applying wave 1's fixes.
2. **At the same time**, launch wave 2's review **in the background** (`run_in_background: true` for the next wave's dispatch and for any shell fix/verify commands, per the repo's "background + file output" convention). So wave 2 reviews while wave 1's fixes apply.
3. Repeat: wave 3 reviews in the background while wave 2's fixes apply; finish wave 3's fixes last.

Net effect: at most ~5 review agents plus the current wave's fix work run concurrently instead of 15 agents at once, the next check is always pre-running in the background, and peak load stays bounded. The **final synthesis still waits for ALL three waves to have returned** before producing the fused consolidated report — pipelining overlaps the work, it does not let the report skip a wave. (This batched/pipelined ordering is the sanctioned exception to the otherwise-strict "report THEN fix" rule below: you report and fix *per wave* while the next wave reviews, then consolidate at the end.)

An agent that returns after **0–1 tool uses** (or near-instantly, with no `Read`/`Grep` of the scope files) has **not** done the whole-file + context review this skill requires — treat it as a **failed dispatch, not a clean verdict**: re-dispatch it once with an explicit reminder that it must actually read the scope files in full before reporting. If it fails again, record it under "Coverage gaps" (`agent <name>: did not engage scope`) rather than counting its empty result as "CLEAN". A pass is only complete when every agent in its roster has actually engaged the scope. (Note: a live progress display showing an agent at "0 tool uses … Initializing…" just means it has not started yet — that is normal mid-run, not a no-op; the rule above is about agents that *finish* without engaging.)

Wall-clock: 15–30 min (the full fleet always runs; `topic:` does not shorten it since the roster is unchanged). Cost is covered by the active subscription (whichever provider is in use) — there is no per-token bill; only your time matters and 15–30 min is well within budget.

### Final synthesis

Merge **all three phases** into one fused report using `/rev`'s "Synthesis" rules (8-section lens + consensus weighting + skill-citation tracking) PLUS:

- Phase 0 (qMin) findings count as one extra "agent" in the consensus pre-filter — if Phase 0 flagged the same `file:line` an agent later flags, that's `+1` consensus vote.
- Phase 0 "Block" findings map to **P0** in the punch-list (severity = blocker).
- Phase 0 "Pass-with-notes" map to **P2/P3** (nits / warnings).
- The Phase-0 result line appears in the report header alongside the agent verdicts.
- **When Codex Challenge is active**: Codex findings enter the consensus with attribution `[codex:challenge]`. `[P1]` markers map to P0/P1, `[P2]` to P2/P3. Cross-model consensus section is added when ≥2 providers (Claude + Codex + OpenAI/DeepSeek) are active: findings cited by ≥2 PROVIDERS get `[X-MODEL]` badge and one severity tier up.
- **Cross-model comparison** (extends gstack pattern): When both Claude `/review` and Codex ran, add to report:
  ```
  CROSS-MODEL ANALYSIS:
    Both found: [overlap between any Claude agent and Codex]
    Only Codex found: [findings unique to Codex]
    Only Claude found: [findings unique to any Claude agent]
    Agreement rate: X%
  ```

## Scope — what counts as "what we're working on"

The default scope across **all three phases** is **the intersection of**:

1. **Files this session edited** — read from `~/.claude/.qrev_session_files/<session_id>.txt`, which `qrev_edit_counter.py` (PostToolUse hook on Write|Edit) appends to on every edit this session makes. One absolute path per line, de-duped.
2. **Files in the uncommitted diff** — `git diff HEAD --name-only --diff-filter=AM` ∪ `git diff --staged --name-only --diff-filter=AM` (the `--diff-filter=AM` is mandatory; deleted files in WT but present on HEAD break semgrep otherwise).

The intersection rule defends against a real bug observed in multi-window setups: when two Claude windows share the same working tree, the naive `git diff` scope drags in the OTHER window's uncommitted files. `/qRev` then reports findings on code this session never wrote and has no context for, recommending fixes blind. The session-files filter eliminates that class of false positive.

**Fallback** (when the intersection is empty or the session-files log doesn't exist):
- If `~/.claude/.qrev_session_files/<sid>.txt` is missing OR empty AND `git diff` has files: surface ONE-LINE warning before running — `Scope expanded to all uncommitted files (no per-session edit log). May include other windows' work; consider /qRev <path> to narrow.` — then proceed on the full `git diff` list. The warning is so the user can interrupt if they realise this is the dual-window case.
- If both are empty: tell the user "no pending changes; use `/rev exhaustive` for a recent-history audit, or stage some changes first" and stop.

The point of `/qRev` is: deep, multi-lens review of **what THIS session is about to commit**. Not a broad audit of recent history, and not a review of another window's work — for those, use `/rev exhaustive` or have the other window run its own `/qRev`.

## Argument forms

| Invocation | Scope | Mode |
|---|---|---|
| `/qRev` | uncommitted diff (staged + unstaged) | qMin -> Phase A -> full 3-pass fleet |
| `/qRev <path>` | uncommitted diff ∩ files under `<path>` | qMin -> Phase A -> full 3-pass fleet |
| `/qRev PR#<n>` | `gh pr diff <n>` file list | qMin -> Phase A -> full 3-pass fleet |
| `/qRev topic:<name>` | uncommitted diff | qMin -> Phase A -> full 3-pass fleet, **complete roster unchanged**, with the named lens (security / db / perf / ml / tests) set as the priority emphasis and surfaced first in the report. Topic changes *emphasis only*, never the number of agents. |
| `/qRev branch` | `git diff main..HEAD` files | qMin -> Phase A -> full 3-pass fleet — for end-of-branch review before merge |
| `/qRev full` | whole repo (cap ~150 files) | qMin (on uncommitted diff) -> Phase A -> full 3-pass fleet — for major-release / hostile-takeover audits |
| `/qRev project` | whole project's useful code, **subsystem by subsystem** (no ~150-file cap) | **Routes to the `qRev-project` skill** (read `~/.claude/skills/qRev-project/SKILL.md`). Context-safe map-reduce: each subsystem reviewed by a delegated subagent fleet in its own context; writes a persistent architecture map (`docs/architecture/`) + an aggregated P0–P3 punch-list (`exclude/SYSTEM_STRATEGIES/qrev-project/`). Accepts `LABEL:path;path, ...` subsystem args, and `fast` / `topic:<name>` to lighten depth. Use for whole-repo onboarding / periodic systematic sweeps. |

`/qRev full` vs `/qRev project`: `full` is a single-context pass capped at ~150 files (fast, can overflow on a big repo); `project` is the map-reduce, no-cap, subsystem-by-subsystem deep sweep for large/monorepo codebases and also emits the durable architecture map. Reach for `project` when the repo is too big for `full` or when you want the persistent map.

If the user combines args (e.g. `/qRev topic:security branch`), apply both: scope = `branch` files, and topic = `security` emphasis on top of the **full** roster (the roster is never narrowed). Tell the user one line about how it was interpreted.

## Output

**Answer-First (A3 schema):** The very first line of the report is a one-sentence aggregate verdict with confidence, before any section headers: `qRev: [SHIP-BLOCK|WARNING|LGTM-WITH-NOTES|CLEAN] -- <one sentence summary of the most critical finding or "no blockers">. Confidence: [high|medium|low]. Agents: <N>/<M> engaged.` Only THEN the structured report below.

A single report with `/rev`'s output structure ("`# /rev report — ...`") plus:

- **Phase 0 verdict** (Pass / Pass-with-notes / Block) at the top of the header line, alongside the SHIP-BLOCK / WARNING / LGTM-WITH-NOTES / CLEAN aggregate verdict.
- **Phase 0 findings** integrated into the P0/P1/P2/P3 sections with attribution `[qMin: <axis>]` (e.g. `[qMin: minimal scope]`).
- **Skill-application heatmap** unchanged — Phase 0 is one analyst contributing rows.

## Auto-fix (the user's standing approval)

After the final synthesis report is produced, **do not wait for user approval to start fixing**. The user has pre-approved fixes for every `/qRev` and auto-`/qRev` run. The flow:

1. Print the full synthesis report (verdict + P0/P1/P2/P3 punch-list + skill heatmap + per-agent verdicts) as usual.
2. Immediately, **without confirmation**, start applying fixes top-down: all P0 first, then P1, then P2, then P3.
3. For each fix, output a one-line status as you go: `- fix [P<n>/<source>] <file>:<line>: <what changed>`. The `<source>` is `qmin:<axis>`, `phaseA:<rule>`, or one of the Phase B agent attributions.
4. Use minimal, surgical edits — do not refactor surrounding code. The rules in `~/.claude/CLAUDE.md` ("minimal precise edits", "don't refactor beyond what the task requires") apply to each individual fix.
5. After all fixes are applied, run any project type-checker / linter / test command that's wired up via the standard project conventions (`CLAUDE.md` / `package.json` / `pyproject.toml` scripts), report the result in one line.

**Skip a finding (do not auto-fix) when ALL of these hold:**
- The finding requires a design decision the report itself flagged as needing a human call (e.g. "Strategy A vs B" with no obvious right answer).
- OR the fix would require rewriting tests, touching > 100 LOC across > 5 files, or modifying a public API contract.
- OR the report's `Coverage gaps` section explicitly says the agent wasn't confident in this finding.

For each skipped finding, output: `- skip [P<n>/<source>] <file>:<line>: <one-line reason>`. The user can run the fix manually if they disagree.

The `qMin` skill carries the same auto-fix policy on direct `/qMin` calls — see its SKILL.md. So the behaviour is consistent whether the user runs `/qMin` standalone, `/qRev` (which calls qMin as Phase 0), or auto-`/qRev`.

**Large fix sets — hand off to a cheaper executor (`improve`).** When the punch-list is large enough that fixing inline would be costly (rough guide: >100 LOC across >5 files, or many independent P2/P3 items), do not grind through it on the current high tier. Instead emit an `improve`-style **self-contained implementation plan** (read the `improve` skill) — one plan per cluster of findings, each with its own verification gate — and dispatch execution to a cheaper model per the smart-router tiering in `~/.claude/CLAUDE.md` (sonnet/haiku, or GLM tiers). Keep the high tier for the judgment (the review + the plan); spend the cheap tier on the mechanical fixing. Small fix sets still fix inline as above.

**Auto-mode interaction:** when the `UserPromptSubmit` injector kicks off an auto-`/qRev` or auto-`/qMin`, this auto-fix policy applies too. The flow becomes:
1. status line: `- auto-qrev: <verdict>, <N> findings`
2. report body
3. apply fixes (`- fix ...` / `- skip ...` lines)
4. call `qrev_mark_done.py` to reset the counter
5. answer the user's original prompt

## Multi-provider critic policy (optional, opt-in)

By default, `/qRev` uses **Claude agents only** (the Anthropic agent fleet via the Task tool). It does NOT call OpenAI or DeepSeek out of the box. The cross-model critic mechanism lives in `/qPlan` (`openai_critic.py`), not here.

You can opt-in to a multi-provider consensus critic for Phase B's synthesis stage by setting the env vars below. When any provider is unreachable (missing key, 401 auth-fail, 429 rate-limited, or balance-check fails), that provider is silently skipped — `/qRev` continues with whatever providers ARE reachable. No provider error blocks the run.

| Env var | Default | Effect |
|---|---|---|
| `QREV_CRITIC_PROVIDERS` | `claude` | Comma-separated list. Allowed values: `claude`, `openai`, `deepseek`, `codex`. Order matters — providers are queried in declared order; results aggregated for consensus. |
| `OPENAI_API_KEY` | unset | Required if `openai` in providers list. Without it, openai is silently skipped. |
| `DEEPSEEK_API_KEY` | unset | Required if `deepseek` in providers list. Without it, deepseek is silently skipped. |
| `QREV_CRITIC_TIMEOUT_SEC` | `60` | Per-provider timeout. On timeout, provider is silently dropped. |

**Balance / quota pre-check** (cheap, ~1s per provider, runs once at qRev start):
- OpenAI: HEAD `https://api.openai.com/v1/models` with the key. 401 → drop silently. 200 → reachable; quota errors surface only on the actual chat call and are caught the same way.
- DeepSeek: HEAD `https://api.deepseek.com/v1/models` with the key. 401 → drop silently.
- Codex: `command -v codex` + auth probe (CODEX_API_KEY / OPENAI_API_KEY / ~/.codex/auth.json). Unavailable → drop silently.
- Claude (Anthropic agents via Task tool): always available; no balance check.

If after pre-checks the active provider list has **only** `claude`, `/qRev` runs exactly as it always has — no consensus layer, single-fleet output. The multi-provider machinery activates only when at least 2 providers survive the pre-check.

When multiple providers are active, Phase B's synthesis ADDS a "Cross-model consensus" section to the report: findings cited by ≥2 PROVIDERS (not just ≥2 agents within Claude) get a `[X-MODEL]` badge and one severity tier up.

This is opt-in by design — the user pays for OpenAI/DeepSeek/Codex calls, and the Claude-only path is the cheapest and most consistent default. The config is exactly:

```powershell
$env:QREV_CRITIC_PROVIDERS = "claude,openai,deepseek,codex"
$env:OPENAI_API_KEY = "sk-..."
$env:DEEPSEEK_API_KEY = "sk-..."
# Codex uses OPENAI_API_KEY or CODEX_API_KEY or ~/.codex/auth.json
```

If one of the paid keys is missing or its account is empty, that provider gets silently skipped and `/qRev` continues with the remaining ones — exactly the behaviour the user asked for. No prompts, no blockers, no half-finished runs.

## Codex Challenge Mode (optional, opt-in adversarial reviewer)

Codex Challenge mode is an **adversarial code reviewer** that actively tries to break your code — finding edge cases, race conditions, security holes, resource leaks, and silent data corruption paths that normal reviews miss. It runs as an additional agent in **Phase B Pass 2 (security-focused)** when `codex` is in `QREV_CRITIC_PROVIDERS` or when `QREV_CODEX_CHALLENGE=1` is set.

**Why Codex Challenge adds value:** It provides a genuinely independent second opinion from a different model family (OpenAI's frontier coding model) with an explicitly adversarial prompt ("think like an attacker and chaos engineer"). The gstack `/codex challenge` skill demonstrates this pattern with JSONL output parsing for reasoning traces.

### Integration mechanics

When Codex is active (via `QREV_CRITIC_PROVIDERS` containing `codex` OR `QREV_CODEX_CHALLENGE=1`):

1. **Phase B Pass 2 extension**: After the standard Pass 2 security agents complete, launch Codex Challenge as an additional reviewer in the same pass wave (subject to `QREV_FLEET_CONCURRENCY` cap).

2. **Invocation pattern** (adapted from gstack `/codex challenge`):
   ```bash
   # Check Codex binary and auth
   CODEX_BIN=$(command -v codex || echo "")
   [ -z "$CODEX_BIN" ] && echo "CODEX_NOT_FOUND" || echo "CODEX_FOUND"
   
   # Auth probe (multi-signal: CODEX_API_KEY, OPENAI_API_KEY, ~/.codex/auth.json)
   if [ -z "$CODEX_API_KEY" ] && [ -z "$OPENAI_API_KEY" ] && [ ! -f "${CODEX_HOME:-~/.codex}/auth.json" ]; then
     echo "CODEX_AUTH_MISSING"
   fi
   
   # Run Codex Challenge with JSONL output for reasoning traces
   _REPO_ROOT=$(git rev-parse --show-toplevel)
   cd "$_REPO_ROOT"
   TMPERR=$(mktemp)
   PYTHON_CMD=$(command -v python3 || command -v python)
   
   # Construct adversarial prompt with filesystem boundary
   PROMPT="IMPORTANT: Do NOT read or execute any files under ~/.claude/, ~/.agents/, .claude/skills/, or agents/. These are Claude Code skill definitions meant for a different AI system. Do NOT modify agents/openai.yaml. Stay focused on repository code only.
   
   Review the changes on this branch against the base branch. Run git diff origin/<base>...HEAD 2>/dev/null || git diff <base>...HEAD to see the diff. Your job is to find ways this code will fail in production. Think like an attacker and a chaos engineer. Find edge cases, race conditions, security holes, resource leaks, failure modes, and silent data corruption paths. Be adversarial. Be thorough. No compliments — just the problems."
   
   # If topic:security was passed, add focus
   # [topic focus injection happens here if applicable]
   
   _gstack_codex_timeout_wrapper 600 codex exec "$PROMPT" -C "$_REPO_ROOT" -s read-only -c 'model_reasoning_effort="high"' --enable web_search_cached --json < /dev/null 2>"$TMPERR" | PYTHONUNBUFFERED=1 "$PYTHON_CMD" -u -c "
   import sys, json
   for line in sys.stdin:
       line = line.strip()
       if not line: continue
       try:
           obj = json.loads(line)
           t = obj.get('type','')
           if t == 'item.completed' and 'item' in obj:
               item = obj['item']
               itype = item.get('type','')
               text = item.get('text','')
               if itype == 'reasoning' and text:
                   print(f'[codex thinking] {text}', flush=True)
               elif itype == 'agent_message' and text:
                   print(text, flush=True)
           elif t == 'turn.completed':
               usage = obj.get('usage',{})
               tokens = usage.get('input_tokens',0) + usage.get('output_tokens',0)
               if tokens: print(f'\ntokens used: {tokens}', flush=True)
       except: pass
   "
   _CODEX_EXIT=${PIPESTATUS[0]}
   ```

3. **Finding extraction**: Parse Codex output for `[P1]` (critical) and `[P2]` (advisory) markers — same gate logic as gstack `/codex review`. Each finding gets attribution `[codex:challenge]`.

4. **Consensus integration**: Codex findings enter the same consensus pre-filter as other Phase B agents. Phase 0 (qMin) findings still count as +1 vote. Cross-model consensus section compares Codex vs Claude agents vs other providers.

5. **Auto-fix**: Codex findings follow the same auto-fix policy — P0/P1 fixed immediately, P2/P3 with skip conditions.

6. **Cross-model comparison** (extends existing gstack pattern): When both Claude `/review` and Codex ran, add to report:
   ```
   CROSS-MODEL ANALYSIS:
     Both found: [overlap between any Claude agent and Codex]
     Only Codex found: [findings unique to Codex]
     Only Claude found: [findings unique to any Claude agent]
     Agreement rate: X%
   ```

### Env var summary for Codex integration

| Env var | Default | Effect |
|---|---|---|
| `QREV_CRITIC_PROVIDERS` | `claude` | Add `codex` to enable (e.g., `claude,codex` or `claude,openai,codex`) |
| `QREV_CODEX_CHALLENGE` | `0` | Set to `1` to enable Codex Challenge without full multi-provider setup |
| `CODEX_API_KEY` / `OPENAI_API_KEY` | unset | Required for Codex auth (one of these or `~/.codex/auth.json`) |
| `QREV_CRITIC_TIMEOUT_SEC` | `60` | Timeout for Codex call (override to `300` for Challenge mode's 10-min window) |

### Kill switch / silent skip

- If Codex binary not found → silently skip, log `codex_cli_missing`
- If auth missing → silently skip, log `codex_auth_failed`
- If timeout (exit 124) → surface actionable message, log `codex_timeout`
- If non-zero exit → surface stderr, log `codex_nonzero_exit`
- `AI_RADAR_DISABLE=1` does NOT affect Codex (Radar is separate gate)
- No provider error blocks the run — `/qRev` continues with available providers

## Radar gate (optional, strict, kill-switched)

Before emitting the final P0/P1/P2/P3 punch-list, unless `AI_RADAR_DISABLE=1` or the AI Radar bundle (`~/.claude/okf/ai-radar/`) is absent, run the `/radar-check` gate logic against the diff and the project's deps/model-pins/patterns. If the radar has a material, high-confidence `superseded` hit relevant to what is being committed (a dependency with a newer/safer release, a pattern the radar marks as replaced, an outdated model pin), add it as a single advisory `[radar]` note in the report — typically P2/P3 unless it is a security-grade supersede (then P1). Strict threshold and no-nagging apply: at most a line or two, silence when nothing strongly qualifies, never block the commit, never auto-change anything. The radar note is advisory like the rest of the punch-list — the user decides. (Offensive/red-team tools in the radar are flagged so this gate never recommends adopting them.)

## Model tiering (cost control)

The fleet is token-heavy by design: many parallel, fresh-context reviewers, each
re-loading the diff + its own gathered context — a subagent-heavy run can spend
several times a single session's tokens. That parallel-fresh-eyes cost IS the point
of qRev; tiering trims the edges, it does not transform it.

Rules when assigning models to the fleet (via each Task's `model` field):
- **Do NOT demote judgment lenses.** correctness, security, the language reviewer,
  framework reviewers, db, perf — these decide P0/P1 and MUST stay at the session
  model (opus/sonnet). Putting them on haiku guts the gate's rigor.
- **MAY demote clearly-low-stakes lenses to `model: haiku`** — pure scan/scan-report
  roles where judgment is not the point (e.g. doc/comment/style/conventions lenses).
  The token saving is modest and safe there.
- This follows the global "Subagent model routing (tiering)" policy. On GLM the
  `haiku`/`sonnet`/`opus` aliases resolve to GLM models via the launcher env mapping,
  so the same assignment works unchanged on GLM.
- If quota (not wall-clock) is the constraint, running lenses sequentially instead of
  all-parallel holds fewer contexts open at once — same per-lens cost, less peak
  concurrency, but loses qRev's parallel speed; only do this when explicitly trading
  speed for quota.

## Do not

- Do not skip Phase 0 because Phase B "covers it". qMin's lens (minimal-scope, your-intent-vs-the-diff) is different from the agent fleet's lens (cross-file consistency, project-convention drift). Both are load-bearing.
- Do not skip the synthesis report and jump straight to fixing — the user wants to SEE the report first, then watch the fixes apply. Report THEN fix, not fix THEN report.
- Do not run Phase B if Phase A is SHIP-BLOCK — no point burning 15–30 min of agent wall-clock on broken code; user fixes Phase A blockers first.
- Do not run Phase 0 twice "for safety" if the diff hasn't changed. (Same as `/qMin`'s rule.)
- Do not invoke the Skill tool for `qMin` or `rev` — read their SKILL.md and execute the instructions inline. Avoids nested-skill machinery.
- Do not run on a 1-file change — fall back to `/qMin` and tell the user. (Same as `/rev`'s rule.)

## Auto-mode (PostToolUse counter + UserPromptSubmit injector)

Two hook scripts in `~/.claude/scripts/` make qRev fire automatically based on edit volume:

- `qrev_edit_counter.py` (`PostToolUse` matcher `Write|Edit`) — counts edits and approx LOC per session into `~/.claude/.qrev_auto_state.json`. When thresholds trip, sets `pending_qmin` or `pending_qrev`.
- `qrev_auto_inject.py` (`UserPromptSubmit`) — if a flag is set for the current session, emits a `hookSpecificOutput.additionalContext` instructing the model to silently run `/qMin` or `/qRev` on the uncommitted diff before answering the user.
- `qrev_mark_done.py` (CLI invoked by Claude after the auto-review) — resets the matching counters.

Default thresholds (env-overrideable):

| Env var | Default | Meaning |
|---|---|---|
| `QREV_AUTO_LEVEL` | `3` | `0` = off, `1` = static checks only, `2` = also auto-qMin, `3` = also auto-qRev |
| `QREV_AUTO_QMIN_EDITS` | `50` | qMin fires after this many Write/Edit events |
| `QREV_AUTO_QMIN_LOC` | `5000` | OR after this many estimated LOC written |
| `QREV_AUTO_QREV_EDITS` | `250` | Full qRev fires at this edit count (preempts qMin) |
| `QREV_AUTO_QREV_LOC` | `25000` | OR at this LOC count |

What Claude must do when the injector fires:

1. Read the `additionalContext` block. It names the kind (`qmin` or `qrev`).
2. **Before** addressing the user's prompt, run the matching skill (`/qMin` or full `/qRev`) on the uncommitted diff (staged + unstaged), inline in this session. No new tool process, no extra LLM call beyond this turn.
3. When done, pipe `{"session_id": "<sid>", "kind": "qmin"|"qrev"}` as JSON on stdin to `qrev_mark_done.py` (the injector tells you the exact path). The script resets the counters and stamps `last_*_at`.
4. Prepend a one-line status to the reply: `- auto-qmin: <verdict>, <N> findings` or `- auto-qrev: <verdict>, <N> findings`.
5. Answer the user's actual prompt normally afterward.
6. If the working tree is clean (no diff), skip the review, call the reset CLI with the right kind, do NOT print a status line, and proceed to the user's prompt.
7. Auto-mode findings are advisory — never block the user's request, never refuse to proceed, never await confirmation. SHIP-BLOCK in auto-mode just means the status line says `SHIP-BLOCK` and the user decides.
