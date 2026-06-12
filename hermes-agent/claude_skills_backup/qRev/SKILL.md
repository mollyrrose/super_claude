---
name: qRev
description: Deep review of what you're about to commit — runs `/qMin`'s 5-axis check + `/rev exhaustive`'s 3-pass multi-agent fleet on the **uncommitted diff** (staged + unstaged), then synthesises both into a single P0/P1/P2/P3 punch-list. Optional `topic:<name>` arg keeps exhaustive depth but narrows the agent lens (security / db / perf / ml / tests). Invoked via /qRev (canonical) OR any case variant — /qrev, /Qrev, /QRev, /QREV all map to this same skill (case-insensitive). If the user types any of these, treat as a /qRev invocation and proceed with this skill.
---

# qRev — Quick Review (qMin + rev exhaustive, fused)

**Case-insensitive invocation:** `/qRev`, `/qrev`, `/Qrev`, `/QRev`, `/QREV` are all the same skill. Treat any of them as a `/qRev` call and proceed below.

## When to use

You'd otherwise type two commands (`/qMin`, then `/rev exhaustive`) on the same state. Reach for `/qRev` instead and get a single fused report.

For lighter checks, the original commands are still right:
- per-commit / single diff only -> `/qMin`
- single-pass (no exhaustive) review -> `/rev` (no args)
- post-implementation validation -> `/check`
- root-cause one specific failure -> `/hunt`

## What to do

Run **three** phases in order. Each later phase inherits earlier phases' findings as context.

### Phase 0 — qMin on the pending diff (NEW, runs first)

Apply the full `/qMin` skill verbatim to the **uncommitted diff** (staged + unstaged) — i.e., exactly what the user is about to commit. Read `~/.claude/skills/qMin/SKILL.md` and follow its "What to review" and "Output" sections exactly.

Five axes (from qMin):

1. **Minimal scope** — every changed line load-bearing for the task; flag unrelated refactors/renames/formatting/"while-I'm-here" cleanups.
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

### Phase B — `/rev exhaustive`'s 3-pass agent fleet

Invoke `/rev` with mode `exhaustive` (read `~/.claude/skills/rev/SKILL.md`, "`/rev exhaustive` (3-pass)" section). All three passes run with the same skill-bundle map, agent roster, and synthesis rules. **Pass-1 inherits Phase 0 findings as context** — the agents must see them so they don't re-derive the same issues.

If a `topic:<name>` arg was passed, **each pass's agent roster is filtered** to the topic-relevant agent list from `/rev`'s "topic:*" table (intersected with the pass's normal roster). This gives an exhaustive 3-pass *depth* but narrowed to one *lens*. See the argument-forms table below.

Wall-clock: 15–30 min (default scope), 5–10 min (topic-filtered exhaustive). Cost is covered by the Claude Pro/Max subscription — there is no per-token bill; only your time matters and 15–30 min is well within budget.

### Final synthesis

Merge **all three phases** into one fused report using `/rev`'s "Synthesis" rules (8-section lens + consensus weighting + skill-citation tracking) PLUS:

- Phase 0 (qMin) findings count as one extra "agent" in the consensus pre-filter — if Phase 0 flagged the same `file:line` an agent later flags, that's `+1` consensus vote.
- Phase 0 "Block" findings map to **P0** in the punch-list (severity = blocker).
- Phase 0 "Pass-with-notes" map to **P2/P3** (nits / warnings).
- The Phase-0 result line appears in the report header alongside the agent verdicts.

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
| `/qRev` | uncommitted diff (staged + unstaged) | qMin -> Phase A -> exhaustive 3-pass |
| `/qRev <path>` | uncommitted diff ∩ files under `<path>` | qMin -> Phase A -> exhaustive 3-pass |
| `/qRev PR#<n>` | `gh pr diff <n>` file list | qMin -> Phase A -> exhaustive 3-pass |
| `/qRev topic:<name>` | uncommitted diff | qMin -> Phase A -> exhaustive 3-pass **with agent roster filtered to topic-relevant agents** (intersect each pass's normal roster with the topic table in `/rev` SKILL.md). Use when you want exhaustive *depth* but only the chosen *lens* (security / db / perf / ml / tests). |
| `/qRev fast` | uncommitted diff | qMin -> Phase A only, skip Phase B (no agent fleet) |
| `/qRev branch` | `git diff main..HEAD` files | qMin -> Phase A -> exhaustive 3-pass — for end-of-branch review before merge |
| `/qRev full` | whole repo (cap ~150 files) | qMin (on uncommitted diff) -> Phase A -> exhaustive 3-pass — for major-release / hostile-takeover audits |

If the user combines incompatible args (e.g. `/qRev topic:security branch`), apply both: scope = `branch` files, topic-filter on the agent roster, exhaustive mode. Tell the user one line about how it was interpreted.

## Output

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
| `QREV_CRITIC_PROVIDERS` | `claude` | Comma-separated list. Allowed values: `claude`, `openai`, `deepseek`. Order matters — providers are queried in declared order; results aggregated for consensus. |
| `OPENAI_API_KEY` | unset | Required if `openai` in providers list. Without it, openai is silently skipped. |
| `DEEPSEEK_API_KEY` | unset | Required if `deepseek` in providers list. Without it, deepseek is silently skipped. |
| `QREV_CRITIC_TIMEOUT_SEC` | `60` | Per-provider timeout. On timeout, provider is silently dropped. |

**Balance / quota pre-check** (cheap, ~1s per provider, runs once at qRev start):
- OpenAI: HEAD `https://api.openai.com/v1/models` with the key. 401 → drop silently. 200 → reachable; quota errors surface only on the actual chat call and are caught the same way.
- DeepSeek: HEAD `https://api.deepseek.com/v1/models` with the key. 401 → drop silently.
- Claude (Anthropic agents via Task tool): always available; no balance check.

If after pre-checks the active provider list has **only** `claude`, `/qRev` runs exactly as it always has — no consensus layer, single-fleet output. The multi-provider machinery activates only when at least 2 providers survive the pre-check.

When multiple providers are active, Phase B's synthesis ADDS a "Cross-model consensus" section to the report: findings cited by ≥2 PROVIDERS (not just ≥2 agents within Claude) get a `[X-MODEL]` badge and one severity tier up.

This is opt-in by design — the user pays for OpenAI/DeepSeek calls, and the Claude-only path is the cheapest and most consistent default. The "feltöltöttem pénzzel az OpenAI-t és a Deepseek-et" config is exactly:

```powershell
$env:QREV_CRITIC_PROVIDERS = "claude,openai,deepseek"
$env:OPENAI_API_KEY = "sk-..."
$env:DEEPSEEK_API_KEY = "sk-..."
```

If one of the two paid keys is missing or its account is empty, that provider gets silently skipped and `/qRev` continues with the remaining ones — exactly the behaviour the user asked for. No prompts, no blockers, no half-finished runs.

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
