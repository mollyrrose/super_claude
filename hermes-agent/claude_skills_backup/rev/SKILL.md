---
name: rev
description: Multi-agent project review with skill-bundle injection. Launches 12–15 specialist agents in parallel, each pre-loaded with a curated 4–6 skill bundle relevant to its role, against the current repo or a scoped slice (PR, branch-diff, path, topic). Produces a severity-sorted P0/P1/P2/P3 punch list with skill-citation tracking. Use at sprint close, before tagged release, or after a stack of merges. Not for per-commit checks — use /qMin or /check there.
---

# /rev — Project Multi-Agent Review (v2: skill-bundle injection)

Comprehensive, independent, parallel review across security, backend integrity, FastAPI/web patterns, DB, language idioms, silent failures, test coverage, performance, ML, type design. Designed to surface what `/qMin` (single-diff) and CR/Bugbot (single-PR) miss: cross-file consistency, missed cascade modules, structural drift, and project-convention violations.

The v2 expansion: each agent is launched with an explicit **skill-bundle** of 4–6 reference checklists they must read and apply. The bundle is curated per agent role and adapted to detected project topics. Repo-specific conventions (`.cursorrules`, `CLAUDE.md`, `INDEX.md`) override generic best-practice in every bundle.

## Argument forms

| Invocation | Scope | Mode |
|---|---|---|
| `/rev` | Last 20 commits + open PRs + uncommitted diff | default single-pass (Phase A + Phase B) |
| `/rev fast` | Same scope as default | **Phase A only** (Semgrep + standards) — pre-PR gate, no agent fleet |
| `/rev PR#<n>` | A single PR's files (`gh pr diff <n> --name-only`) | default |
| `/rev branch` | `git diff main..HEAD` files | default |
| `/rev <path>` | Tree under `<path>` (e.g. `src/api/`) | default |
| `/rev recent` | Last 10 commits' touched files | default |
| `/rev full` | Whole repo (cap ~150 files) | default |
| `/rev exhaustive` | Multi-pass: quality → security → arch+perf → tests | 3 passes |
| `/rev topic:<name>` | Only agents/skills relevant to topic (e.g. `topic:security`) | focused |
| `/rev topic:ml` | ML/MLE deep dive | focused |
| `/rev topic:db` | Database deep dive | focused |
| `/rev topic:perf` | Performance deep dive | focused |

## Phase A — Deterministic gate (NEW, runs first)

Cheap, fast, always-on. Runs **before** the agent fleet (Phase B). On `/rev fast`, this is the only phase that runs.

1. **Verify repo:** `git rev-parse --show-toplevel`. If not a git repo → stop.
2. **Seed check — `.semgrep.yml`:** if the repo has no `.semgrep.yml` at root:
   - Offer once per repo: "Seed `.semgrep.yml` + `.semgrepignore` + `.semgrep/packs.txt` from `~/.claude/templates/`?"
   - On consent: copy templates, uncomment packs matching detected languages (from the existing Topic detector grep matrix), create `.semgrep/custom/` dir with `~/.claude/templates/semgrep_custom_README.md`.
   - On decline: skip Phase A this run, fall through to Phase B (with a one-line note in the report's "Coverage gaps" section).
3. **Seed check — `CODING_STANDARDS.md`:** if the repo has no `CODING_STANDARDS.md` at root:
   - Offer once per repo: "Seed `CODING_STANDARDS.md` from `~/.claude/templates/CODING_STANDARDS.template.md`?"
   - On consent: copy. Print the line `@CODING_STANDARDS.md` for the user to paste into their per-repo `CLAUDE.md` (do not auto-edit user CLAUDE.md).
   - On decline: skip the standards-violation check; Semgrep still runs.
4. **Run Semgrep on scope files:**
   ```
   semgrep --config .semgrep.yml \
           --config <each non-comment line from .semgrep/packs.txt> \
           --config .semgrep/custom/   # if dir exists and non-empty
           --json --error <scope-file-list>
   ```
   On scope file lists >200 files, batch in groups of 100 to stay under the CLI argv limit.
5. **Read CODING_STANDARDS.md** and LLM-check the diff (changed lines only, not the full files) against the **"Non-negotiable rules"** section. One violation per rule per line, severity = `blocking`. Skip the "Per-language patterns" + "Style notes" sections for Phase A (those are Phase B fodder).
6. **Append all findings** to `<repo>/.claude/review-log/findings.jsonl` with schema:
   ```json
   {"ts": "<iso8601>", "source": "semgrep" | "rev-standards",
    "rule": "<check_id or non-negotiable-N>",
    "file": "<abs path>", "line": N,
    "severity": "blocking" | "warning" | "nit",
    "message": "<one-line>",
    "status": "open", "fix_commit": null}
   ```
   Create the `.claude/review-log/` directory if missing.
7. **Verdict:**
   - Any `blocking` finding → **Phase A FAIL** → entire `/rev` verdict is `SHIP-BLOCK`. Skip Phase B (no point running the agent fleet on broken code; user fixes Phase A blockers then re-runs).
   - Only `warning`/`nit` findings → **Phase A PASS-WITH-NOTES** → continue to Phase B.
   - No findings → **Phase A CLEAN** → continue to Phase B.

On `/rev fast`, stop after step 7 and print a Phase-A-only report (no agent verdict section, no skill-citation heatmap).

Phase B findings (from the agent fleet, post-synthesis) are also appended to the same `findings.jsonl` with `source: "rev"`, severity mapped from agent P0/P1/P2/P3 to `blocking`/`blocking`/`warning`/`nit`. This feeds the `/rev-learn` loop.

## Preflight (BEFORE launching agents)

1. **Verify repo**: `git rev-parse --show-toplevel`. If not a git repo → stop.
2. **Detect project type** (language + framework — see Step 3 below).
3. **Topic detector (NEW)** — grep matrix, deterministic, ~1s:

   | Topic | Detection grep / glob |
   |---|---|
   | `python` | `*.py` exists |
   | `typescript` | `*.ts` / `*.tsx` / `tsconfig.json` |
   | `rust` | `Cargo.toml` |
   | `go` | `go.mod` |
   | `java` | `pom.xml` / `build.gradle` |
   | `csharp` | `*.csproj` |
   | `swift` | `Package.swift` / `*.xcodeproj` |
   | `kotlin` | `*.kt` |
   | `fastapi` | grep `from fastapi import` |
   | `django` | `manage.py` or grep `from django` |
   | `flask` | grep `from flask import` |
   | `spring` | `org.springframework` in `pom.xml`/`build.gradle` |
   | `quarkus` | `io.quarkus` |
   | `laravel` | `artisan` file |
   | `pg` | `psycopg2` / `asyncpg` / `pg_` imports / `*.sql` |
   | `mysql` | `mysql.connector` / `pymysql` / `mysql2` |
   | `redis` | `redis` import |
   | `clickhouse` | `clickhouse_driver` / `clickhouse-connect` |
   | `mongodb` | `pymongo` / `mongoose` |
   | `pytorch` | `import torch` |
   | `sklearn` | `from sklearn` |
   | `transformers` | `from transformers` |
   | `llm_sdk` | `anthropic` / `openai` / `cohere` / `langchain` |
   | `trading_agent` | `trading` + `llm_sdk` co-occurrence |
   | `crypto_hmac` | `hmac.compare_digest` / `hashlib.sha256` |
   | `jwt_auth` | `PyJWT` / `jsonwebtoken` |
   | `solidity` | `*.sol` |
   | `mt5` | `MetaTrader5` import |
   | `stripe` | `stripe` import |
   | `solana` | `solana` / `anchor` import |
   | `react` | `react` in `package.json` |
   | `vue` | `vue` in `package.json` |
   | `embedded_js` | `<script>` blocks in `*.py` / `*.html` of FastAPI/Django templates |
   | `docker` | `Dockerfile` / `docker-compose.yml` |
   | `gha` | `.github/workflows/*.yml` |
   | `mcp` | `mcp_server` / `@modelcontextprotocol` |
   | `phi_hipaa` | `PHI` / `HIPAA` / `patient` in code |
   | `type_widening` | grep `-> Any:` count >5 → flag for type-design-analyzer |
   | `n_plus_one_risk` | `for ... in ... :` followed by `cur.execute` / `.query(` |
   | `silent_except` | grep `except Exception:\s*pass` |

4. **Build scope file list** (the agents' input):
   - Resolve argument to concrete file list
   - Default mode: cap at ~80 files
   - `exhaustive` / `full`: cap at ~150 files
   - If larger, narrow to changed-only via `git diff --name-only`
5. **Read context files**: `INDEX.md`, `TODO.md`, `STARTUP.md`, `CLAUDE.md`, `.cursorrules`, `ARCHITECTURE.md`, `README.md`. These get baked into every agent's prompt as project-convention authority.
6. **Secret-leak preflight**: before sharing scope with agents, grep the scope file list for staged `*.env*`, `*.pem`, `*.key`, `id_rsa*`, hardcoded `sk-`, `Bearer ` literals. If any match → abort, warn user, do not launch agents (defence-in-depth — never broadcast secrets into the agent fleet).
7. **State the plan** to the user in 3–5 lines: scope (which files), agents (count + names), skill bundles (per-agent skill count), mode, expected wall-clock (~5–12 min single-pass, ~15–30 min exhaustive).

Do NOT launch on a 1-file change — fall back to `/qMin` and tell the user.

## Agent roster — base + adaptive

**Base 6 (mandatory, always launched):**
- `security-engineer` — secrets, SQL injection, command injection, OWASP top-10
- `backend-architect` — race conditions, transaction integrity, idempotency, fault tolerance
- `ecc:code-reviewer` — SOLID, error-handling boundaries, maintainability, anti-fingerprint
- `ecc:silent-failure-hunter` — swallowed errors, bad fallbacks, masked failures
- `ecc:security-reviewer` — vuln detection (different methodology, useful overlap with security-engineer)
- `ecc:pr-test-analyzer` — test coverage, behavioral vs structural assertions

**Language reviewer (auto, exactly 1):**
- `python` → `ecc:python-reviewer`
- `typescript` → `ecc:typescript-reviewer`
- `go` → `ecc:go-reviewer`
- `rust` → `ecc:rust-reviewer`
- `java` → `ecc:java-reviewer`
- `csharp` → `ecc:csharp-reviewer`
- `swift` → `ecc:swift-reviewer`
- `kotlin` → `ecc:kotlin-reviewer`
- `fsharp` → `ecc:fsharp-reviewer`
- `cpp` → `ecc:cpp-reviewer`
- `flutter`/`dart` → `ecc:flutter-reviewer`

**Framework reviewer (auto, ≤2):**
- `fastapi` → `ecc:fastapi-reviewer`
- `django` → `ecc:django-reviewer`
- (no dedicated reviewer for Flask/Spring/Quarkus/Laravel — handled via skill-bundle on language reviewer)

**Topic-conditional (added when topic detected, up to ~5 total):**
- `pg`/`mysql`/`mongodb`/`clickhouse`/SQL files → `ecc:database-reviewer`
- `pytorch` + (`sklearn`/`transformers`) → `ecc:mle-reviewer`
- `n_plus_one_risk` OR `pytorch` hot path → `performance-engineer`
- `type_widening` ≥5 hits → `ecc:type-design-analyzer`
- `phi_hipaa` → `ecc:healthcare-reviewer`
- `embedded_js` substantial volume → light frontend pass via `frontend-architect` agent
- `solidity` → custom security-engineer prompt with `ecc:defi-amm-security` skill (no dedicated agent)

**Hard cap: 15 parallel agents.** If more would apply, drop the lowest-relevance ones (typically `ecc:type-design-analyzer` and `ecc:healthcare-reviewer` first if borderline) and note which were dropped in the report's "Coverage gaps" section.

## Skill-bundle map (≤7 skills per agent)

Every bundle implicitly includes the repo's **convention files** (`.cursorrules`, `CLAUDE.md`, `INDEX.md` if present) — those count as 0 against the cap because they're authority, not reference. Soft cap is 7; agents pick relevance from the bundle and are not required to apply every skill.

| Agent | Skill bundle (read at session start, apply checklists) |
|---|---|
| `security-engineer` | `code-security`, `ecc:security-review`, `ecc:llm-trading-agent-security` *(if trading_agent)*, `ecc:django-security`/`ecc:springboot-security`/`ecc:laravel-security`/`ecc:quarkus-security` *(framework-keyed)*, `ecc:defi-amm-security` *(if solidity)*, `ecc:hipaa-compliance` *(if phi_hipaa)* |
| `ecc:security-reviewer` | `security-auditor`, `security-analyzer`, `ecc:security-bounty-hunter`, `ecc:security-scan`, `ecc:code-security`, language-security skill *(if any)* |
| `backend-architect` | `ecc:backend-patterns`, `ecc:hexagonal-architecture`, `ecc:error-handling`, `ecc:api-design`, framework-patterns skill *(`ecc:fastapi-patterns`/`ecc:django-patterns`/`ecc:springboot-patterns`/etc.)*, `logging-best-practices`, `hermes-codebase-inspection`, `hermes-writing-plans`, `oc-architecture-review` |
| `ecc:code-reviewer` | `code-review-and-quality`, `code-review-expert`, `simplify`, `solid`, `ecc:plankton-code-quality`, `karpathy-guidelines`, `hermes-requesting-code-review`, `hermes-systematic-debugging`, `hermes-spike`, `oc-refactor`, `oc-git-workflow` |
| `ecc:silent-failure-hunter` | `ecc:error-handling`, `logging-best-practices`, `ecc:hunt`, `karpathy-guidelines`, `ecc:silent-failure-hunter` *(self-ref)*, `hermes-systematic-debugging`, `oc-diagnose` |
| `ecc:pr-test-analyzer` | language-testing skill *(`ecc:python-testing`/`ecc:csharp-testing`/`ecc:kotlin-testing`/etc.)*, `ecc:tdd-workflow`, framework-tdd *(`ecc:django-tdd`/`ecc:springboot-tdd`/`ecc:laravel-tdd`)*, `frontend-testing-best-practices` *(if frontend)*, `ecc:e2e-testing` *(if e2e exists)*, `hermes-test-driven-development`, `oc-tdd-mattpocock`, `oc-tdd-mfranzon` |
| `ecc:python-reviewer` | `ecc:python-patterns`, `ecc:python-testing`, `ecc:tdd-workflow`, `solid`, `karpathy-guidelines`, `ecc:error-handling`, `hermes-python-debugpy`, `hermes-jupyter-live-kernel`, `oc-py-complexity`, `oc-py-code-health` |
| `ecc:typescript-reviewer` | `typescript-best-practices`, `ecc:typescript-best-practices`, `frontend-testing-best-practices`, `solid`, `karpathy-guidelines`, `ecc:error-handling`, `hermes-node-inspect-debugger` |
| `ecc:go-reviewer` | `ecc:golang-patterns`, `ecc:golang-testing`, `solid`, `karpathy-guidelines`, `ecc:error-handling` |
| `ecc:rust-reviewer` | `ecc:rust-patterns`, `ecc:rust-testing`, `solid`, `karpathy-guidelines`, `ecc:error-handling` |
| `ecc:java-reviewer` | `ecc:java-coding-standards`, `ecc:jpa-patterns`, framework-patterns, `solid`, `karpathy-guidelines`, `ecc:error-handling` |
| `ecc:csharp-reviewer` | `ecc:dotnet-patterns`, `ecc:csharp-testing`, `solid`, `karpathy-guidelines`, `ecc:error-handling` |
| `ecc:swift-reviewer` | `ecc:swift-concurrency-6-2`, `ecc:swift-actor-persistence`, `ecc:swift-protocol-di-testing`, `solid`, `karpathy-guidelines` |
| `ecc:kotlin-reviewer` | `ecc:kotlin-patterns`, `ecc:kotlin-coroutines-flows`, `ecc:kotlin-testing`, `solid`, `karpathy-guidelines`, `ecc:error-handling` |
| `ecc:fastapi-reviewer` | `ecc:fastapi-patterns`, `ecc:api-design`, `ecc:error-handling`, `logging-best-practices`, `ecc:python-patterns`, `ecc:python-testing` |
| `ecc:django-reviewer` | `ecc:django-patterns`, `ecc:django-security`, `ecc:django-tdd`, `ecc:django-celery` *(if Celery)*, `ecc:api-design`, `logging-best-practices` |
| `ecc:database-reviewer` | `postgres`, `ecc:postgres-patterns`, `ecc:database-migrations`, `ecc:mysql-patterns` *(if MySQL)*, `ecc:clickhouse-io` *(if CH)*, `ecc:redis-patterns` *(if Redis)* |
| `ecc:mle-reviewer` | `ecc:mle-workflow`, `ecc:pytorch-patterns`, `ecc:llm-trading-agent-security` *(if trading)*, `ecc:agent-introspection-debugging`, `ecc:cost-aware-llm-pipeline`, `karpathy-guidelines`, `hermes-jupyter-live-kernel`, `hermes-llm-wiki` |
| `performance-engineer` | `ecc:benchmark`, `ecc:postgres-patterns` *(N+1)*, `ecc:pytorch-patterns` *(if ML hot path)*, `logging-best-practices`, `ecc:content-hash-cache-pattern` |
| `ecc:type-design-analyzer` | language-patterns skill, `solid`, `karpathy-guidelines` |
| `ecc:healthcare-reviewer` | `ecc:hipaa-compliance`, `ecc:healthcare-phi-compliance`, `ecc:healthcare-cdss-patterns`, `ecc:healthcare-emr-patterns`, `ecc:healthcare-eval-harness` |
| `frontend-architect` *(light pass)* | `ecc:frontend-patterns`, `frontend-testing-best-practices`, `ecc:design-system`, `ecc:accessibility`, `ecc:click-path-audit`, `hermes-design-md` |

**Skill list is "if available" — agent does not fail on missing skill, only logs which were not found.**

## Agent prompt template

```
You are doing an INDEPENDENT review on <repo-name>. No other agent's context is shared with you. Fresh eyes — that is the value.

PROJECT CONTEXT (one sentence): <generated from INDEX.md / README.md>
RECENT CHANGE SUMMARY (3–5 lines): <git log + open PR titles>

SCOPE (absolute paths, ~<N> files):
<file list>

PROJECT CONVENTIONS (authoritative — override generic best-practice):
- Read: <abs path>/CLAUDE.md
- Read: <abs path>/.cursorrules
- Read: <abs path>/INDEX.md

SKILL BUNDLE (read at session start, apply each skill's checklist to the scope):
- ~/.claude/skills/<skill-1>/SKILL.md
- ~/.claude/skills/<skill-2>/SKILL.md
- ... (≤6)

If a skill file does not exist, note it and continue with the rest.

YOUR FOCUS (agent-specific): <focus paragraph>

OUTPUT CONTRACT:
1. Single-line verdict: CLEAN | N issues found | WARNING | SHIP-BLOCK
2. Findings sorted P0 → P1 → P2 → P3
3. For each finding:
   - file:line
   - 1-sentence root cause
   - 1-sentence fix
   - CITATION: which skill checklist item this violates (e.g. "ecc:python-patterns §async-correctness")
4. No restating the diff.
5. Hard word cap: 1500.

PROVE you applied the bundle: each P0/P1 finding MUST have at least one skill citation. The synthesis phase tracks citation rate per agent — agents returning 0 citations get flagged "skill bundle not applied".
```

## Modes

### Default (single-pass)
- 12–15 parallel agents
- Bundles capped at 6 skills each
- ~5–12 min wall-clock
- ~$5–10 token cost
- **Use case**: sprint close, pre-release, after a stack of merges

### `/rev exhaustive` (3-pass)
- **Pass 1 — Quality + correctness**: `ecc:code-reviewer`, language-reviewer, `ecc:python/typescript-reviewer`, `ecc:silent-failure-hunter`, `ecc:type-design-analyzer`
- **Pass 2 — Security deep-dive**: `security-engineer`, `ecc:security-reviewer`, `security-auditor` (skill-only), domain-security (defi/llm-trading/hipaa)
- **Pass 3 — Architecture + DB + Perf + Tests**: `backend-architect`, `ecc:database-reviewer`, `ecc:fastapi/django-reviewer`, `performance-engineer`, `ecc:mle-reviewer`, `ecc:pr-test-analyzer`
- Each pass synthesises before the next; pass-N inherits pass-(N–1) findings as context
- ~15–30 min wall-clock, ~$15–25 token cost
- **Use case**: major release, post-incident audit, hostile-takeover branch audit

### `/rev topic:<name>` (focused)
- Only agents + skills relevant to that topic
- Examples:
  - `topic:security` → security-engineer + ecc:security-reviewer + framework-security skills, ~4 agents, ~3 min
  - `topic:db` → ecc:database-reviewer + backend-architect with DB-focused bundle, ~2 agents, ~3 min
  - `topic:perf` → performance-engineer + ecc:database-reviewer (N+1) + ecc:mle-reviewer (if ML), ~3 agents
  - `topic:ml` → ecc:mle-reviewer + security-engineer (LLM injection) + ecc:python-reviewer, ~3 agents
  - `topic:tests` → ecc:pr-test-analyzer + ecc:code-reviewer, ~2 agents

## Synthesis (AFTER all agents return)

Apply the **DeepSeek 8-section lens** (per user's global memory) PLUS consensus weighting PLUS skill-citation tracking:

1. **Consensus pre-filter**: any finding cited by ≥2 agents → auto-elevate one severity tier. ≥3 agents → "high-confidence" badge.
2. **Skill-citation audit**: per agent, count P0+P1 findings WITH a skill citation vs. without. If citation-rate < 30% for an agent → flag "skill bundle possibly not applied" in coverage gaps (this is the falsifier signal for the v2 expansion).
3. **De-dupe by `file:line`** — same finding from multiple angles gets merged with attribution: `[security-engineer + backend-architect + ecc:database-reviewer]`.
4. **8-section grouping** for the final output:
   - Crashes / data loss
   - Logic correctness
   - Security
   - Performance
   - Duplication / DRY
   - Tooling / CI
   - Synergies (suggested combined fixes spanning ≥2 sections)
   - Quick-wins (≤10 LOC, ≤1 file)
5. **Severity-sorted master punch-list** at the top: P0/P1/P2/P3 with `file:line` + agent attribution + skill citation + 1-sentence fix.
6. **Consensus highlights**: explicitly call out findings flagged by ≥3 agents — these are the highest-confidence items.
7. **Skill-application heatmap**: short table showing which skills were cited most → confirms (or refutes) which checklists were actually load-bearing for this run.
8. **Files NOT reviewed**: note any scope gap.
9. **Suggested PR slicing**: group P0/P1 items into 2–5 logical PR-sized chunks.

## Output structure

```
# /rev report — <repo-name>, scope: <argument>, mode: <default|exhaustive|topic-X>
<wall-clock duration> · <N agents> · <M total findings> · <K skills applied>

## Verdict
<SHIP-BLOCK | WARNING | LGTM-WITH-NOTES | CLEAN>
<1–2 sentence summary>

## P0 — blockers (<count>)
[severity-sorted table with file:line | cause | fix | agents | skill-cite]

## P1 — high (<count>)
[...]

## P2 — medium (<count>)
[...]

## P3 — low (<count>)
[...]

## Consensus highlights (≥3 agents flagged the same issue)
[bullet list]

## Skill-application heatmap
| Skill | Citations | Top contributing finding |
| ecc:python-patterns | 14 | api_*.py async/sync mismatch |
| ecc:error-handling | 11 | str(e) leak in 4 modules |
| ...

## Suggested PR slicing
- PR A: <title> — <files, ~LOC>
- PR B: ...

## Coverage gaps
[files / areas not reviewed by any agent]
[agents with citation-rate < 30% — bundle injection may have failed]

## Per-agent verdicts (collapsed)
- security-engineer: <verdict + count + citation-rate>
- backend-architect: <verdict + count + citation-rate>
- ...
```

## What NOT to do

- **Don't** run on a working tree with uncommitted secrets — preflight Step 6 enforces this.
- **Don't** propose fixes inline in `/rev` output — `/rev` SURFACES findings; the user (or `/think` + implementation) decides the fix.
- **Don't** run repeatedly on the same state. If invoked twice without new commits, ask the user if they want a re-run or to view the cached report.
- **Don't** promise findings the agents didn't return — if the report is thin, say so explicitly.
- **Don't** run on hostile / unverified code — agents Read arbitrary file content; assume the working dir is trusted.
- **Don't** auto-create issues / PRs from the findings — output a punch-list only.
- **Don't** force every agent to use every skill in its bundle — agents pick relevance from the bundle. Some skills won't apply to a given scope; that's fine. The 30% citation-rate threshold is the safety net.
- **Don't** invoke the Skill tool itself for the bundles — agents READ the skill files at start, they don't execute them as Skill-tool calls (that would launch nested skill machinery and break the parallel-agent isolation).

## Cost / runtime notes

| Mode | Agents | Wall-clock | Approx token cost |
|---|---|---|---|
| default | 12–15 | 5–12 min | $5–10 |
| exhaustive | 18–22 (across 3 passes) | 15–30 min | $15–25 |
| topic:* | 2–5 | 2–5 min | $1–3 |

- For per-commit checks, prefer `/qMin` (single diff) or `/check` (post-impl).
- For "is one specific PR safe to merge", prefer Cursor Bugbot or CR — `/rev` is overkill for one PR.

## Failure modes / recovery

| Symptom | Cause | Recovery |
|---|---|---|
| Agent returns "scope too large" | >80 files default / >150 exhaustive | Narrow to changed-only via `git diff --name-only` |
| Agent returns "couldn't access path" | Wrong CWD | `pwd` first, pass absolute paths to all agents |
| Two agents return contradicting verdicts | Different scope cuts | Flag both in the synthesis; the user decides |
| Skill file missing | Skill uninstalled or renamed | Agent logs "skill not found", continues with rest; synthesis notes which skills missed |
| Skill-citation rate < 30% | Bundle injection failed (e.g. agent ignored prompt) | Synthesis flags it. If persistent across runs, fall back to v1 behaviour (no bundles) by invoking `/rev no-bundles` |
| Output exceeds context | Too many findings | Truncate P2/P3 to top 5 each, full list saved to `.rev_reports/<timestamp>.md` |
| One agent hard-fails | Tool error / timeout | Continue without it; note in coverage gaps |
| Wall-clock > 20 min in default mode | Harness throttling or agent stuck | Kill any agent past 15 min, synthesise with the rest |

## Self-falsifier

The v2 expansion's load-bearing claim is "agents that get skill bundles produce better reviews than agents without". To test this empirically:

1. After each `/rev` run, the synthesis records per-agent skill-citation-rate.
2. If the median citation-rate across all runs in a sprint drops below 30%, **revert to v1 behaviour**: launch the same agents but with no skill bundle (just `.cursorrules` + `CLAUDE.md` as before). This is the `/rev no-bundles` mode.
3. Compare next run's findings quality (P0/P1 count, consensus rate) against the previous bundle-enabled run.
4. If no-bundle run finds equal-or-more P0/P1, the bundle injection isn't paying off — keep no-bundles as default.

## Related skills

- `/qMin` — single-diff minimal-scope review (much smaller, ~$0.20/run)
- `/check` — post-impl validation
- `/qRem` — session orientation (run before `/rev` if you don't know the repo state)
- `/think` — design-phase review (run BEFORE coding; `/rev` runs AFTER)
- `/hunt` — root-cause for a specific error/regression
- `/sc:analyze` — alternative single-agent comprehensive analysis (faster, lower coverage)
- `/ecc:agent-architecture-audit` — agent/LLM-app stack audit (overlap with `/rev topic:ml` for LLM apps)
- `/ecc:harness-audit` — Claude Code harness audit (not project code review)
- `/ultrareview` — user-triggered cloud review (different beast, billed); `/rev` is the local equivalent

## Language-aware reviewer reminders (appendix)

Cross-cutting reviewer hints that supplement (don't replace) the agent-specific skill bundles above. Apply when the diff contains files of the matching language.

**Python**
- `yaml.load` on untrusted input → must be `yaml.safe_load`. P0/P1.
- New `subprocess` call with `shell=True` → code smell unless explicitly justified.
- New async function → every awaitable must be `await`ed; bare coroutine returns are bugs.
- Type hints in new code: PEP 604 `X | None` over `Optional[X]`, `list[int]` over `List[int]`.
- `pickle.loads` / `eval` / `exec` on untrusted input → P0 unless sandboxed.

**TypeScript / JavaScript**
- New `any` cast → ask if `unknown` plus narrowing fits. Severity = `consider` at minimum.
- `JSON.parse` on user input without try/catch → bug.
- New Promise without `await` → confirm "fire-and-forget" is intentional, not a missed await.
- React: new effect without dependency array → almost always a bug.

**Go**
- Returned `error` ignored anywhere → P0 unless explicitly documented why.
- Goroutine without a way to terminate → leak risk.
- `defer` inside a loop → look hard; usually wrong.

**Rust**
- New `unsafe` block → must have a safety comment naming the invariants it relies on.
- `.unwrap()` / `.expect()` in non-test code → severity `consider` at minimum.
- `Arc<Mutex<T>>` introduced — could it be `Arc<RwLock<T>>` or a channel?

**SQL / DB**
- String concatenation into a query → P0, use parameterised queries.
- New query inside a loop → N+1 candidate; flag for `ecc:database-reviewer`.
- Migration that drops a column → reversible? Has it been backfilled? P1 if either is unclear.

**Cross-language secrets / OWASP reminders (no tool catches all of these)**
- SSRF: user-supplied URLs fed to `requests`/`fetch`/`http.get` without an allowlist.
- Auth bypass: new route/endpoint that skips the auth decorator or middleware.
- CSRF: state-mutating verb (POST/PUT/DELETE) without a token check.
- Insecure defaults: `verify=False`, `ssl=False`, weak hashing (`md5`/`sha1` for passwords).
- Hardcoded credentials: even base64'd — flag for human review.

## Hungarian / English

Match the user's invocation language for the report body. Default to English for `file:line` references, severity labels, and skill names (they're cross-language identifiers).
