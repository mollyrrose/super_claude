# SUPER CLAUDE AI-OS — Strategy

Status: finalized 2026-07-07 via a qPlan author<->critic panel run (3 rounds: major -> minor -> converged; lenses = spec-conformance, architecture, pragmatism, premortem, executable-check, plus a local Ornith 35B voice). Audit trail: `.qplan/2026-07-07T2037/` (transcript.md + ledger.jsonl).

Companion documents:
- `second_Brain.md` — the Second Brain design (this doc's Section 8, expanded).
- `FABLE5_LEGACY.md` — incorporated by reference (Section 5); untouched.

Design stance in one line: build the LEAST operating system that closes super_claude's concrete gaps, keep every existing capability intact (Section 11), and gate every speculative layer behind a felt-pain trigger — so the OS gets better as models improve (Bitter Lesson Engineering), not worse.

## 0. Vezetoi osszefoglalo (magyar)

A super_claude ma egy eros, de szalakra bomlo kepesseg-gyujtemeny: 208 skill, 3 tanulasi adatfolyam, onkurator-rendszer, multi-window koordinacio, token-kompresszio, wargame- es focus-group-szintu iteletbankolas. Ket dolog hianyzik. Eloszor: nehany konkret lyuk (nincs lekerdezo reteg a tanulasi adatfolyamok folott; a flottak koltseget senki nem becsli inditas elott; 208 skill rossz felfedezhetoseg; a Fable-tudas nincs indexelve). Masodszor, es fontosabb: nincs egyetlen szervezo elv, ami minden munkat ugyanazon a hurkon hajt at (jelen allapot -> ideal allapot, ellenorizheto kilepesi feltetellel).

Ez a strategia NEM egy nagy uj gepezetet epit a meglevo tetejere. A vezerelv a felhasznalo sajat hazi szabalya: "a legkevesebb autonomia, ami mukodik", "eloszor szuntesd meg, aztan automatizald", "boring is beautiful", es minden komponensnek kill switch. Ezert a terv KET reszre valik szet:

1. **Least-OS (most, biztosan megepul):** ~6 alacsony-kockazatu, onalloan ertekes darab, amelyek a konkret lyukakat zarjak be, es MINDEGYIK onmagaban is hasznos a tobbi nelkul. Ha a projekt itt megall, akkor is nyertunk.
2. **Kernel es identitas-reteg (opcionalis, felt-pain-trigger utan):** az univerzalis hurok (`/aios`), a TELOS identitas-doksi, a Second Brain osszekoto szovet — ezek ALAPERTELMEZETTEN KI vannak kapcsolva, opt-in modon hivhatok, es csak akkor epulnek tovabb, ha egy valos faidalom igazolja oket.

A vezerfilozofia a Bitter Lesson Engineering: kimenetet specifikalunk, nem vegrehajtasi utat — igy a rendszer minden okosabb modellel automatikusan jobb lesz, nem rosszabb. Es a legfontosabb garancia: SEMMI meglevo nem vesz el. Minden mai kepesseg megkapja a helyet (11. szakasz megorzesi terkepe), minden invokacio valtozatlanul mukodik, es minden uj darab kill switch-csel es "ha itt megallunk, koherens allapot marad" felteltellel erkezik.

Egy day-30 lekapcsolo (abort tripwire): ha 30 nap utan egyetlen uj reteg sincs napi, keretlen hasznalatban, az OS-erofeszites LEALL, es csak azok az onallo eszkozok maradnak, amelyek megszolgaltak a helyuket.

## 1. Guiding philosophy (the constitution of the constitution)

Three sources fuse into the design stance. Every later section is checkable against these, AND against the user's own standing house rules (lowest autonomy that works; eliminate before automating; deterministic before AI; boring is beautiful; kill switch for everything; token discipline).

1. **Bitter Lesson Engineering** (Miessler, 2026-02): human scaffolding — heuristics, step-by-step recipes, curated methodologies — caps results below the model ceiling and DEGRADES as models improve. Adopted as design law: specify desired outcomes and anti-outcomes, never execution paths; never hard-code a human decision heuristic where a model judgment call will do better next year; shift scaffolding from execution instructions to *preferences*; give the best tools to the best model.
2. **The Last Algorithm** (Miessler, 2026-01): ASI-like outcomes come from *loops*, not new models. The universal loop: define IDEAL STATE (exit condition: would it produce Euphoric Surprise in the requestor?), then OBSERVE -> THINK -> PLAN -> BUILD -> EXECUTE -> VERIFY -> LEARN until current == ideal. Verifiability is the hill-climbing gradient.
3. **Designed to be replaced:** every component ships with (a) a kill switch and (b) a one-line statement of the outcome it exists to produce, so a future audit — triggered concretely on every Opus/Fable major version bump, not just "monthly" — can ask per component: "does the bare model now do this better?" and drop it if yes.

**The BLE self-check (this OS must not become the scaffolding BLE warns against).** The named GAPS are small and concrete (a query CLI, a cost gate, an index, cross-links). The speculative LAYERS (kernel, constitution reword, council) are large. That mismatch is the central risk. Resolution baked into the roadmap: build the least-OS that closes the concrete gaps first; defer every speculative layer behind a specific felt-pain trigger; and on each model bump, each speculative layer re-justifies its existence or is pulled.

**Tension managed explicitly:** the existing CLAUDE.md is full of execution-prescriptive rules (pipe X through Y, run Z before W). BLE prefers outcome-specs. Resolution: infrastructure discipline (tokenjuice, coord, banners, hook mechanics) stays prescriptive because it encodes *harness limits*, not intelligence, and is FROZEN VERBATIM; only genuine judgment rules are candidates for outcome-spec rewriting, and that rewriting is deferred and done one rule at a time with sign-off (Section 6).

## 2. Current-state assessment (the OBSERVE output)

From the recon inventory (2026-07-07, 3-agent sweep).

**Ten load-bearing capabilities (gems):**
1. FABLE5_LEGACY.md — 726-line distilled intelligence protocol (36 failure modes, 12-point pre-send review, 8 character foundations). An epistemology, not just instructions.
2. Three-tier auto-review (semgrep -> qMin -> qRev) with standing pre-approval to fix.
3. Brain/hands separation: qPlan (panel critic, terminating ledger) / qGoal (execute-to-DONE).
4. Wargame system: fable-tier judgment banked as blind-executable battle plans.
5. Self-curating skill ecosystem: hermes-learn -> hermes-curate -> hermes-auto-*; rev-learn -> semgrep rules; skill-lifecycle archiver.
6. Hot-path hook consolidation (hook_dispatch.py, 3-4x latency win).
7. 46-persona (soon 130+) focus group.
8. tokenjuice + condense deterministic compression.
9. coord.py cross-window coordination with decision-gate.
10. Learning data streams: .smart_router_eval.jsonl, .qrev_verdict_log.jsonl, .decision_log.jsonl (data-first, algorithm-later).

**Ten gaps (the least-OS closes the first tier of these):**
1. No query layer over the learning streams. 2. ruvector.db dormant. 3. No cost estimate before fleet dispatch. 4. Wargame skill and kit unlinked. 5. No CI/CD integration. 6. AI Radar has no scheduled refresh. 7. Focus-group/wargame output doesn't feed the curator. 8. 208 skills, weak discoverability. 9. Cross-model critics optional. 10. No health/trend view over the JSONL streams.

**Data-sufficiency caveat (executable-check lens):** before building the query layer, we run a one-liner counting rows in the three JSONL streams TODAY. If any has <20 rows, "useful answers from brain_query" is not yet true and that item drops down the priority list — we do not build a query tool for empty data.

## 3. Architecture — substrate layers, cross-cutting aspects, edit-lists

Round 1 called everything a "layer." That inflated the design. Round 2 separates three genuinely different kinds of thing, and states the dependency direction explicitly so the "individually droppable" claim is verifiable.

**Legend.** [LEAST-OS] ships in the committed scope. [GATED] builds only after a named felt-pain trigger fires. [ASPECT] is cross-cutting behavior (a convention or a set of skill-text edits), not a substrate. [FROZEN] is existing and untouched.

**Dependency rule:** substrate layers depend only DOWNWARD (S0 lowest). Aspects attach across layers but own no store. No substrate layer may depend on an aspect. This kills the Round-1 L3<->L4 cycle by construction.

### Substrate layers (things that own a store or a durable surface)

- **S0 — Constitution** [LEAST-OS, additive only]. Outcome: deterministic rule-conflict resolution. Mechanism: a numbered CONSTITUTIONAL block header added to `~/.claude/CLAUDE.md` marking the ~8-12 non-overridable rules; everything else stays a plain rule. Step 1 is ADDITIVE ONLY (insert tier headers, reword nothing); the BLE reword is a separate GATED step (Section 6). Kill switch: delete the headers -> flat rules return. Depends on: nothing.
- **S1 — Identity / TELOS** [GATED: trigger = the user asks for cross-session goal-awareness OR two sessions in a row re-derive the same context]. Outcome: the model knows who it serves and toward what without re-deriving it. Mechanism: `memory/TELOS.md` with per-section HTML staleness markers and per-section cadences; anchored at the top of MEMORY.md; memory files link in with [[name]]. No daemon — qRem/qUpd read it. Kill switch: delete the file. Depends on: S0 only (as a plain-rule surface).
- **S2 — Learning fabric / brain_query** [LEAST-OS]. Outcome: one queryable whole over the existing stores; nothing stored twice; every store has a reader. Mechanism: `scripts/brain_query.py` (deterministic, no LLM) over the three JSONL streams + memory dir + staleness markers. Subcommands in Section 8. Kill switch: it is read-only; delete it. Depends on: the existing streams (S-independent).
- **S3 — Kernel / `/aios`** [GATED: trigger = a real multi-step task where the user explicitly wants the full loop, OR repeated "it declared done but wasn't" misses]. Outcome: a task runs current->ideal with binary, tool-verifiable exit criteria; the model cannot declare victory without evidence. Mechanism: a NEW additive `/aios` orchestrator skill (NOT an in-place qGoal rewrite — see Section 4). DEFAULT OFF, opt-in per invocation; the router may SUGGEST it, never auto-inject. Kill switch: don't invoke it; all q* commands work standalone exactly as today. Depends on: qRem/qPlan/qGoal/qRev/qClose (composes them; adds no new store except per-task ISA files).
- **S4 — Code-structure memory** [GATED: trigger = a concrete task where grep + ecc:code-explorer demonstrably fail to answer a cross-file "what calls this / blast radius" question]. Mechanism: codebase-memory-mcp binary installed MANUALLY and registered by hand in .mcp.json; its auto-installer (which writes an uninvited PreToolUse hook) is NEVER run. Prerequisite spike gates it: a throwaway Windows + multi-worktree index-scope test with an explicit go/no-go. brain_query (S2) must deliver full learning-memory value WITHOUT this — S4 is strictly optional so its failure can never discredit S2. Kill switch: deregister the MCP server.

### Cross-cutting aspects (behavior; own no store)

- **A1 — Router extension** [LEAST-OS, additive to the existing hook]. Outcome: every prompt lands on the right mode + effort tier + model tier + skill before work starts. Mechanism: extend smart_router_rules.py (deterministic-first) to also emit mode (MINIMAL / NATIVE / ALGORITHM) and effort (E1-E5), logged in the existing eval stream; plus a `suggest-skill` meta-skill holding the 208-skill taxonomy, invocable by user and router. Gate: a 15-prompt fixture (prompt -> expected {mode, effort, tier}) must pass before the hook change goes live. Kill switch: existing hook kill; the meta-skill is just a skill.
- **A2 — Council mode** [LEAST-OS as a qPlan option, not a new skill]. Outcome: high-stakes decisions cross-checked by genuinely different models, brand-bias-free. Mechanism: add ANONYMIZED peer-ranking (the one thing qPlan's relay lacks) as a `critic_provider: council` option over the EXISTING critic scripts; a thin `/council` alias just invokes qPlan in that mode. Pre-req falsifier: smoke-test each existing critic script with an invalid key and assert it exits 0 with an empty/None result (graceful degradation) before trusting "a dead provider never fails the council." Kill switch: keys absent -> voices mute (existing policy).
- **A3 — Proactivity** [ASPECT: edits to qRem/qPlan/qClose, not a layer]. Outcome: the OS suggests better ideas than asked, then can SOLVE them — without daemons or nagging. Mechanism, split by autonomy so the least-OS only adds a suggestion, not an autonomous actor:
  - [LEAST-OS, suggest-only] (1) qRem gains a closing PROACTIVE block naming 1-3 concrete unasked improvements (from TELOS + ISA gaps + radar + decision-log patterns), each one line with an effort estimate; (3) qPlan gains Euphoric Surprise Prediction; (4) Answer-First output schema (Section 8) on all analytical verdicts.
  - [GATED, trigger = the user asks the OS to act on its own suggestions] (2) the proactive-SOLVE path — the OS advances a non-destructive, within-theme suggestion to a DRAFT artifact (a proposal file or a background worktree branch), never an irreversible op, always surfaced. This is autonomy beyond what any named gap needs, so it stays behind a felt-pain gate (like S3); the committed scope is suggest-only.
  - Kill switch: each is an individually revertable skill-text edit.
- **A4 — Fleet & token discipline** [ASPECT: constitutional + skill-text edits]. Outcome: fleets don't collide or overspend, and the OS never raises the per-turn token floor. Mechanism: (1) before dispatching >4 agents, state estimated token cost and check remaining quota; (2) any fleet writes a manifest first (the pattern this week's wargame run proved when quota walls killed agents mid-flight); (3) council and fleets default to sequential + single-provider unless the user escalates; (4) a PER-TURN TOKEN BUDGET is a first-class OS invariant: net always-on injected context per turn must NOT increase after the OS work vs today's baseline — every new always-on injection (TELOS, legacy index, proactive block) must justify its cost or load ON-DEMAND only. Kill switch: revert the edits.
- **A5 — Portability** [ASPECT: documentation tags + concrete OpenCode writes]. Outcome: the OS runs on Claude Code fully, and MODIFIES OpenCode as a first-class target as far as its harness allows. Mechanism: every component tagged [CC-only] / [portable-as-text] / [portable-as-CLI]; AND concrete OpenCode deliverables — the constitution + kernel text written into OpenCode's AGENTS.md, and the enumerated OpenCode config/settings edits (single-action-template rule respected per docs/opencode-port.md). Statusline stays; the trend view (gap #10) is a brain_query subcommand printing text, not a web dashboard. LifeOS Pulse: skip. Kill switch: tags are docs; OpenCode edits are reversible config writes.

### Faster + token-efficient coding (the superset answer — its own outcome-spec)

The user asked specifically for faster, more token-efficient programming beyond tokenjuice/compress. This gets a first-class outcome-spec, not a footnote.
- Outcome (measurable target): for a mechanical multi-file edit task, cut wall-clock and total tokens vs the current single-window serial approach; target -30% tokens and parallel throughput on independent sub-edits.
- Mechanisms: (1) **worktree-per-agent** (superset's primitive, generalizing the existing dual-window rule) — independent code-mutating sub-tasks each get a `.worktrees/<task>` branch so a fleet edits without collision and review is a clean diff; the Electron app itself is skipped. (2) **Context minimization for edit tasks** — route mechanical edits (rename, format, version bump) to a cheap tier with only the target file + a tight instruction, never the whole session context. (3) **Batching** — group independent edits into one subagent turn instead of N round-trips. (4) tokenjuice/condense stay the compression floor underneath all of it. This composes with A4's token budget: the coding path must LOWER tokens, consistent with the user's standing token discipline.

## 4. The kernel decided: additive `/aios`, not a qGoal rewrite

Architecture-lens finding, accepted: qGoal is only the BUILD/EXECUTE/VERIFY cluster (it calls qPlan then qRev). It does not own OBSERVE (qRem) or LEARN (qClose). So "qGoal as the whole-loop kernel" is a category mismatch, and an in-place rewrite has no clean kill switch — violating the OS's own droppability law.

Decision: the kernel is a NEW, thin `/aios` orchestrator that COMPOSES the existing skills, adds no store except per-task ISA files, and whose kill switch is "don't invoke it."

- **Loop, reconciled to the 5 skills the harness actually distinguishes** (not a forced 7->skill map): OBSERVE = qRem + recon + radar-check; PLAN = qPlan (+ /wargame for high-stakes; battle plans ARE ISA+moves); EXECUTE = qGoal (which itself still internally plans+builds+reviews); VERIFY = qMin / qRev / check + Live-Probe + Re-Read; LEARN = hermes-learn/curate/rev-learn/decision_log + the Learning Router. THINK folds into PLAN and BUILD folds into EXECUTE — stated honestly rather than listed as separate phases against the same skill.
- **ISA/ISC, de-ceremonied:** the BINDING artifact is a lightweight binary ISC checklist per task, written to a PER-TASK file `exclude/SYSTEM_STRATEGIES/isa/<task-slug>.md` (per-task, so concurrent windows/coord never clobber one shared ISA.md). The 12-section prose ISA is OPTIONAL/progressive, not mandatory. Each ISC is one binary tool probe (the Splitting Test), with `Anti:` and `Antecedent:` kinds. Live-Probe: no ISC flips to [x] without tool evidence in the same block. Re-Read: re-read the user's literal ask before declaring complete.
- **Effort gating:** the ISA artifact appears only at E4+ or an explicit `/aios` call — never E3-and-maybe, so fast iterative work is never taxed. E1-E2 skip the kernel entirely.
- **Adoption ISC (self-policing):** after 2 weeks, count ISAs created without being asked that the user kept. If near zero, the kernel is ceremony and gets pulled. This is the kernel's own "designed to be replaced" check.
- **Live observability:** wire the existing process_progress statusline bar to `/aios` phase transitions and ISC flips, so a long run shows where it stands (reuses existing machinery; no new surface).
- **Learning Router (all-or-nothing):** classifies each learning (knowledge / rule / gotcha / state / doctrine / hook) and routes to its ONE canonical surface (memory dir / CLAUDE.md constitutional-or-plain / semgrep rule / TELOS / skill). Invariant: a learning lives in exactly one store; links, not copies. Until it is fully wired, learnings keep going to today's surfaces unchanged — never half-migrated.

## 5. The Fable Legacy mechanism (knowledge inheritance across model generations)

FABLE5_LEGACY.md is 726 lines — too big to inject every turn, too valuable to leave unread. And the pattern generalizes: every top-tier model's judgment should be bankable for cheaper/later models.
1. **Legacy Index** [LEAST-OS]: add `FABLE5_LEGACY_INDEX.md` (one line per chapter / failure-mode cluster). qRem loads the INDEX (small); the full chapter is pulled ON DEMAND when the task type matches — consistent with the A4 token budget (never inject 726 lines by default).
2. **Session-level inheritance:** when the active model is Opus/Sonnet, the router hint includes "legacy: consult FABLE5_LEGACY section N for this task type." When the active model is Fable-class, skip (it IS the source).
3. **Legacy update protocol:** wargame plans, converged qPlans, and decision-log entries produced BY a Fable-tier model are already banked judgment — tag their artifacts `judgment-tier: fable` so a later audit can measure whether fable-tier plans actually outperform (data exists in LEDGER.md grades + qrev verdicts).
4. **Generalization:** the file family is `<MODEL>_LEGACY.md`; the loader is model-agnostic, so it serves Opus 4.8 -> Opus 5 later.

## 6. Constitution refactor — split into two disjoint steps

Highest-risk seam: CLAUDE.md is the global file every hook/skill depends on, and several hooks detect it by LITERAL SUBSTRING (the "USER INPUT REQUIRED" banner, the tokenjuice discipline text). Rewording the wrong line breaks behavior silently, the user reverts everything, and trust in the OS is poisoned. So:
- **Step 1 (LEAST-OS, Phase 1a) — additive tiering ONLY.** Insert a CONSTITUTIONAL header marking the ~8-12 non-overridable rules (decision-gate on irreversible ops; push-only-with-ask; privacy/scoped-access; kill-switch mandate; no-destructive-without-approval; banner-on-questions; same-project coord scoping; skillspector gate). Reword NOTHING. Fully reversible (delete the headers). Verify with a grep index: capture each rule's first 12 words before and after; a non-empty diff beyond the inserted headers = a rule changed = fail.
- **Step 2 (GATED) — BLE reword, deferred.** Only after Step 1 is stable: rewrite judgment-prescriptive plain rules toward outcome-specs, ONE rule at a time, each with explicit user sign-off. The infrastructure/prescriptive rules the user explicitly demanded (tokenjuice-pipe-everything, the banner, coord protocol, hook mechanics) are FROZEN VERBATIM and exempt from the reword.
- The CONSTITUTIONAL block is mirrored verbatim into OpenCode's AGENTS.md (A5).

## 7. Reference-repo integration verdicts

| Repo | Verdict | What we take | Scope |
|---|---|---|---|
| LifeOS | selective | TELOS+staleness, constitutional tiers, router mode/effort, _ALLCAPS privacy boundary, provenance field. The 49 ourlifeos skills: review-list first (RECON), import only non-overlapping. Skip Pulse dashboard, TS tooling. | S0/S1/A1/A5 |
| llm-council | pattern | 3-stage anonymized council as a qPlan OPTION over existing critic scripts (not a new skill). Skip OpenRouter, UI. | A2 |
| TheAlgorithm | selective | ISA/ISC (de-ceremonied), Splitting Test, Re-Read Check, Euphoric Surprise, Learning Router, E1-E5. Skip version-snapshot system. | S3/A3 |
| gstack | inspiration | ETHOS-style injectable philosophy (= constitution), gate-vs-periodic split for hook smoketests. Defer tmpl pipeline. No openclaw. | S0 |
| substrate | selective | Answer-First schema, numbered falsifiable premises for major claims, stable IDs (DEC-/AR- prefixes) in the decision log. Skip data pipelines. (Full substrate = later PA conflict-resolution candidate, out of scope here.) | A3/S2 |
| fabric | selective | suggest_pattern router (-> suggest-skill), ALL-CAPS output sections, create_pattern self-extension (align with existing create-skill). Skip Go CLI. | A1/L7-conventions |
| codebase-memory-mcp | GATED | binary + manual .mcp.json only, NEVER the auto-installer; behind a go/no-go spike. | S4 |
| Agent-Reach | DECLINE (surface to user) | backend-fallback channel pattern as inspiration only; overlaps hermes-xurl/youtube/exa, Chinese channels niche. Recorded as an explicit decline, not silently dropped. | - |
| fable-orchestration | import-all | SKILL.md + prompt kit + the hard-don't (never tell Fable to "show your reasoning" — trips the reasoning-extraction classifier and silently reroutes to Opus). | S3/L6 |
| agency-agents | selective | import ~6 genuinely non-overlapping (multi-agent-systems-architect, mcp-builder, prompt-engineer, minimal-change-engineer, agents-orchestrator, workflow-architect); CATALOG the rest for on-demand import via suggest-skill rather than bulk-importing 20 duplicates. | L6/A1 |
| anthropics frontend-design | import-all | 2 files; behavioral persona under ui-ux-pro-max (already installed). | L7 |
| superset | pattern | worktree-per-agent primitive (Section 3 coding block); skip the Electron app. | coding |

**Explicit out-of-scope guard (do NOT reintroduce in any later phase):** RobotsDisallowed, Daemon, threshold, OpenMontage, markitdown — excluded per the user's follow-up. A later phase that wants any of these must get fresh user approval.

## 8. Second Brain (extract to second_Brain.md on convergence)

Kept deliberately lean (pragmatism lens): the load-bearing content is brain_query.py and one invariant; the framing prose is minimized.
- **Thesis:** the Second Brain is the connective tissue over the stores that already exist, plus TELOS as its spine — NOT a new store. Invariant: A LEARNING LIVES IN EXACTLY ONE STORE; links, not copies.
- **CODE map (one line each):** Capture = memory writes + decision_log_cli + curator queues + ISA changelogs. Organize = MEMORY.md index + TELOS sections + per-project exclude/SYSTEM_STRATEGIES/. Distill = hermes-curate + rev-learn + the Learning Router (the classifier deciding each learning's one home). Express = qRem orientation + brain_query + statusline + the PROACTIVE block.
- **Query layer (brain_query.py subcommands):** `decisions [--reversed|--open|--since]`; `router [--misses]`; `verdicts [--trend]`; `facts <topic>`; `stale [--telos|--memory]` (staleness-marker scan); `health` (the gap-#10 text dashboard). Deterministic, no LLM, read-only.
- **Integrity rules:** every store has exactly one writer path and >=1 reader; monthly stale-marker scan via the self-audit; no store without a kill switch.

## 9. Phased roadmap — each phase leaves a coherent resting state if abandoned

Design rule (premortem lens): the roadmap is ordered so that STOPPING at any phase boundary leaves a consistent, usable system — never a half-migrated one. Each phase ships self-contained wins; nothing later phase depends on breaks an earlier resting state.

- **Phase 0 — zero-risk wins in one sitting (hours) [LEAST-OS].** fable-orchestration skill + its prompt kit into CLAUDE.md's Fable section; anthropics frontend-design; the ~6 non-overlapping agency-agents; FABLE5_LEGACY_INDEX.md; wargame<->kit cross-link (gap #4). END-TO-END SLICE: route one real small task through the smart-router -> confirm fable-orchestration is actually invoked and returns a result (not just "skills listed"). Resting state: pure additions, everything else unchanged.
- **Phase 1 — cost gate, query layer, discoverability (the three gaps that hurt today) [LEAST-OS].** A4 fleet cost-gate + manifest rule (the quota-death fix, most acute); brain_query.py + smoketest (after the data-sufficiency one-liner passes); suggest-skill meta-skill (gap #8); Answer-First schema into qRev/qMin outputs. Phase 1a: S0 additive constitution tiering + grep-index verification. Resting state: six standalone tools, each useful alone; CLAUDE.md only gained headers.
- **Phase 2 — router extension + council option [LEAST-OS].** A1 mode/effort emission (behind the 15-prompt fixture gate) + eval-schema extension; A2 anonymized-ranking qPlan option (after the None-degradation smoke-test). Resting state: router richer, qPlan richer; both revert cleanly.
- **Phase 3 — kernel + telos, opt-in [GATED].** Only if a felt-pain trigger fired: `/aios` orchestrator (default OFF) + per-task ISA/ISC + Live-Probe/Re-Read + adoption ISC + process_progress wiring; TELOS.md + staleness; Learning Router (all-or-nothing). Resting state: kernel is opt-in, so not building it changes nothing; TELOS unread is harmless.
- **Phase 4 — gated heavy / polish [GATED].** codebase-memory-mcp ONLY after its go/no-go spike passes; ourlifeos 49-skill review+import; _ALLCAPS/provenance conventions; A5 OpenCode parity writes; radar piggyback on the self-audit; (only if drift actually bites) gstack tmpl pipeline. second_Brain.md finalized. Resting state: each item independent.
- **Phase 5 — the predictor [GATED: when the streams have enough rows].** Train/evaluate the router+verdict+decision predictor the streams were built for; council-grade it before trusting.

Each phase ends with: its own verification runs (smoketests for scripts, invocation checks for skills, a qMin on any code), a decision-log entry, and a one-line "resting state if we stop here" note.

**Day-30 abort tripwire (ISC #0) — with an enforcer, not just armed:** at day 30, if zero new components are in unprompted daily use, the OS effort STOPS; only the standalone tools that earned their keep survive. No phase may have a markdown file as its ONLY artifact. An unpulled tripwire is theatre, so it is BOUND to existing recurring surfaces that will actually fire it: (a) a dated `radar-check` item; (b) a decision-log entry with `revisit_if: day-30-adoption`; and (c) one line added to the monthly `/ecc:harness-audit` checklist to read the note and decide abort-vs-continue. The check fires on an owner, not on hope.

## 10. Risks and premortem (top 7, each with its baked-in mitigation)

1. **Shelved-doc failure** (becomes an unread doc like FABLE5_LEGACY): deliverable redefined to "tools in daily use"; day-30 abort tripwire; Phase 0 = one visible win; no phase ships only a .md.
2. **Quota economics** (OS multiplies spend where the user is already quota-bound): per-turn token budget as a first-class ISC; council/fleets default sequential + single-provider; always-on injections load on-demand; the coding path must LOWER tokens.
3. **Attention competition** (meta-work loses to PA/aQAI): committed scope is Phase 0-2 (all [LEAST-OS] items — zero-risk imports, the cost-gate/query/discoverability tools, and the additive router+council options, all low-cost and independently useful); Phase 3+ are explicitly GATED, opportunistic, no timeline, abandonment-safe. (The legend's [LEAST-OS] tag and this line agree: committed == every [LEAST-OS] item == Phases 0-2.)
4. **BLE self-violation** (the OS becomes the clever scaffolding BLE warns against): least-OS-first; speculative layers deferred behind felt-pain triggers; per-layer re-justification on every model bump.
5. **Constitution regression** (a reword breaks substring-detecting hooks): additive tiering and BLE reword split into disjoint steps; infra rules frozen verbatim; grep-index before/after.
6. **Kernel-ceremony rot** (ISA taxes the fast work the user values): kernel default OFF, opt-in, E4+ only, never auto-injected; 2-week adoption ISC pulls it if unused.
7. **Half-built-OS / MCP trust-poison:** each phase leaves a coherent resting state; Learning Router all-or-nothing; codebase-memory-mcp gated behind a throwaway go/no-go spike so one bad experience can't discredit the memory layer.

## 11. Preservation map (semmi nem vesz el)

Every existing capability -> its home: hooks/dispatch -> A1 + FROZEN mechanics; tokenjuice/condense -> A4 floor (FROZEN); coord -> A4 (FROZEN); q* commands -> composed by S3, invocation UNCHANGED; wargame+kit -> PLAN + L6 (now linked); focus-group -> L6 (unchanged; synthesis gains Answer-First); hermes-* skills -> L7 (unchanged); curator/learn/rev-learn -> LEARN + L7; memory dir/MEMORY.md -> S2 (gains TELOS anchor when S1 builds); decision log -> S2 (gains IDs + query); statusline -> A5 + S3 observability; watchdog/stall/load_retry -> FROZEN infra; radar -> A3 (self-audit piggyback); skillspector -> L7 gate (constitutional); FABLE5_LEGACY -> S0/S2 via index loader; GLM/provider groundwork -> A2/A5; pentest+policy -> L6/L7; AI-video/ComfyUI/MCP servers -> L7 (unchanged). REPLACED (not lost): nothing is deleted; ruvector.db is ARCHIVED (moved, recoverable) not removed, and only if suggest-skill's deterministic taxonomy proves sufficient. Any future replacement candidate must be named in a decision-log entry before action.

## 12. Success criteria (OS-level ISCs — binary, tool-verifiable, blind-executable)

Each names the exact probe and pass criterion so a mid-tier executor can run it.
1. [ ] `#0 abort tripwire armed`: a dated note exists listing which components must be in daily use by day 30. Probe: file exists with a date and a component list.
2. [ ] `nothing broke`: for each name in `scripts/smoke_skills.txt` (the 25 significant skills, listed explicitly), invoking it returns non-empty output and exit 0. Probe: run the sweep script; assert 25/25 pass.
3. [ ] `token floor held` (Anti): net always-on injected tokens per turn after Phase 2 <= baseline captured before Phase 0. Probe: instrument hook_dispatch.py to log the byte/token size of the MERGED UserPromptSubmit additionalContext it emits each turn; diff THAT log before/after (the statusline tracks total remaining context dominated by conversation length, so it cannot isolate the injection delta this ISC is about). Fail if the injected-context size rose >0.
4. [ ] `no latency regression` (Anti): hot-path hook count unchanged; dispatch timing within 10% of baseline. Probe: time hook_dispatch before/after.
5. [ ] `brain_query health`: prints counts + trends from all three JSONL streams. Probe: run `brain_query.py health`; assert non-empty for each stream that had >=1 row.
6. [ ] `data sufficiency gate`: the three streams' row counts are recorded; brain_query features requiring a stream are enabled only if that stream has >=20 rows. Probe: the row-count one-liner output is saved.
7. [ ] `council degrades`: a qPlan council run with one provider key unset returns a chairman synthesis from >=2 remaining voices, exit 0. Probe: unset one key, run a seeded question.
8. [ ] `router determinism`: the 15-prompt fixture maps each prompt to its expected {mode, effort, tier}. Probe: run the fixture against smart_router_rules; assert all match.
9. [ ] `constitution additive-only`: the pre/post grep-index of CLAUDE.md rule texts differs ONLY by inserted headers. Probe: diff the two grep captures.
10. [ ] `kernel opt-in` (Anti): no session auto-enters the /aios loop; the router only ever SUGGESTS it. Probe: grep the router output on a normal prompt for auto-invocation; assert absent.
11. [ ] `every new script has a kill switch + passing smoketest`. Probe: grep each new script header for a kill-switch line; run its _smoketest.
12. [ ] `MCP gated`: codebase-memory-mcp is absent from .mcp.json until its spike's go/no-go note records a PASS. Probe: if present in .mcp.json, the PASS note must exist.

## 13. RECON NEEDED (unsettled by this round)

1. ourlifeos.ai 49-skill list vs existing 208 — overlap matrix (Phase 4 gate).
2. ruvector.db actual content/schema — confirms archive-vs-wire (default: archive).
3. codebase-memory-mcp Windows + 6-live-worktree behavior — the go/no-go spike (prerequisite to S4).
4. Exact three-stream row counts TODAY — gates which brain_query features are worth building now (the one-liner in Section 2).
5. OpenCode current template/single-action limits vs the constitution + kernel text size (A5 gate).
6. Which existing critic scripts already exit-0-on-bad-key vs raise — the None-degradation smoke-test (prerequisite to A2).
