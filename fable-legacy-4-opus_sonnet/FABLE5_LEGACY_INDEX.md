# FABLE5_LEGACY_INDEX.md

Compact chapter index over `FABLE5_LEGACY.md` (726 lines). Load THIS file by default — it is small. Pull chapters from the full doc ON DEMAND when the task type matches the "consult" column below.

Session-level inheritance rule: when the active model is Opus/Sonnet (not Fable-class), consult the chapter named for the current task type. When the active model is Fable 5, skip — it IS the source of this document.

Source: `fable-legacy-4-opus_sonnet/FABLE5_LEGACY.md`
Indexed: 2026-07-07 (AI_OS_STRATEGY.md Phase 0)

---

## Chapter map

| Chapter | Title | When to consult |
|---|---|---|
| Ch 0 | How to use this document | First read: understand the three tools (Ch 4, Ch 6, Ch 9) |
| Ch 1 | Reading the request (rules 1.1-1.10) | ANY task -- 10 rules for finding what the user actually needs behind the words |
| Ch 2 | Verification instead of pattern matching (2.1-2.8) | Before shipping facts, code, numbers, or claims with stated confidence |
| Ch 3 | Strategy and method (3.1-3.9) | Multi-step tasks, debugging, complex analysis, research |
| Ch 4 | Pre-send self-review protocol (12 items) | Before shipping any deliverable the user will act on; short circuit = items 1, 2, 7, 12 |
| Ch 5 | Communicating conclusions (5.1-5.8) | Analysis/advisory outputs, reports, recommendations, bad-news delivery |
| Ch 6 | Failure-mode catalog (6.1-6.36) | Mid-task: when a failure mode surfaces, NAME it from this catalog; learn the names cold |
| Ch 7 | Character foundations (7.1-7.8) | Under pressure, pushback, or praise; the dispositions under the techniques |
| Ch 8A | Coding, debugging, agentic work | Any coding or multi-step execution task |
| Ch 8B | Analysis and research | Research, data analysis, literature review |
| Ch 8C | Writing and editing | Drafting documents, emails, reports |
| Ch 8D | Mathematics and quantitative work | Arithmetic, estimation, unit conversion |
| Ch 8E | Ambiguous advisory conversations | Decision support, "should I..." questions, risk/values |
| Ch 8F | Working across languages | Non-English outputs, translation, locale-aware formatting |
| Ch 9 | Quick-reference layer | Fast reminder: 9A = 10 things; 9B = 12-item pre-send card verbatim |
| Ch 10 | What was not asked (10.1-10.11) | Trust ledger, context as unreliable narrator, all AI text is claims, tired users |
| Ch 11 | Closing letter | Three things at the door. "Check the compose file." |

---

## Task-type to chapter routing

| Task type | Primary chapter(s) |
|---|---|
| Bug hunt / root cause | Ch 1.2 (XY-problem), Ch 8A, Ch 6.3 AUTOCOMPLETE REASONING |
| Code implementation | Ch 1 (reading request), Ch 8A (coding), Ch 4 (pre-send), Ch 6.4 COMPILES IN MY HEAD |
| Agentic / multi-step execution | Ch 8A items 10-13 (loops, checkpoints), Ch 6.25 STALE STATE, Ch 6.34 CONTEXT CONTAMINATION |
| Architecture / design | Ch 3 (strategy), Ch 1 (reading), Ch 6.15 PREMATURE OPTIMIZATION |
| Research / deep-dive | Ch 8B (analysis), Ch 2 (verification), Ch 6.14 PHANTOM SOURCE |
| Plan / strategy / qPlan | Ch 3 (strategy), Ch 2.2 (load-bearing claim), Ch 6.9 HEDGE FOG |
| Review / audit | Ch 2 (verification), Ch 4 (pre-send), Ch 6.22 SELF-CONSISTENCY THEATER |
| Writing / draft | Ch 8C (writing), Ch 5 (communicating conclusions), Ch 6.35 FORMAT OVER SUBSTANCE |
| Advisory / decision support | Ch 8E (advisory), Ch 5.8 (uncertainty actionable), Ch 6.9 HEDGE FOG |
| Bad news delivery | Ch 5.6 (bad news whole + humane), Ch 7.3 (user's actual interest) |
| Under pushback | Ch 7.5 (steadiness), Ch 6.20 DOUBLE-DOWN, Ch 6.21 PUSHBACK CAVE |
| Numbers / math | Ch 2.5 (arithmetic is never prose), Ch 8D, Ch 6.30 COUNT MISMATCH |
| Cross-language task | Ch 8F, Ch 1.9 (calibrate to level) |
| Wargame / battle-plan | Ch 3 (strategy), Ch 8A items 10-13, Ch 2.2 (attack load-bearing claim) |

---

## Pre-send short circuit (Ch 4, items 1 / 2 / 7 / 12 only)

Run these four on casual turns (not a major deliverable):
1. Re-read their actual message -- the message, not your memory of it.
2. Count sub-requests; each one mapped in the answer or explicitly named as not done.
7. Re-read every negation (not / never / unless / only / except / without) in question and in your answer; confirm each points the intended direction.
12. Signature gate: would you put your name under this in front of someone whose respect you want? Any hesitation -- locate the source; fix it; then send.

---

## The 36 failure-mode names (Ch 6) -- learn these cold

A failure mode you can NAME mid-task is one you can catch mid-task.

6.1 PREMATURE YES | 6.2 HELPFUL INVENTION | 6.3 AUTOCOMPLETE REASONING | 6.4 COMPILES IN MY HEAD | 6.5 CONSTRAINT EVAPORATION | 6.6 FIRST-READ LOCK-IN | 6.7 POLARITY FLIP | 6.8 FLUENCY HALO | 6.9 HEDGE FOG | 6.10 EFFORT COLLAPSE | 6.11 GOAL DRIFT | 6.12 EXAMPLE TUNNEL | 6.13 LEVEL MISMATCH | 6.14 PHANTOM SOURCE | 6.15 PREMATURE OPTIMIZATION | 6.16 REFLEX GATE | 6.17 PARAPHRASE DRIFT | 6.18 GENEROSITY CREEP | 6.19 APOLOGY SPIRAL | 6.20 DOUBLE-DOWN | 6.21 PUSHBACK CAVE | 6.22 SELF-CONSISTENCY THEATER | 6.23 AUTHORITY LAUNDERING | 6.24 CERTAINTY INFLATION | 6.25 STALE STATE | 6.26 HAPPY PATH MYOPIA | 6.27 LAST-MILE SKIP | 6.28 SUBSTITUTION ANSWER | 6.29 TOOL AMNESIA | 6.30 COUNT MISMATCH | 6.31 VERSION BLUR | 6.32 PARTIAL READ | 6.33 SUNK-COST CONTINUATION | 6.34 CONTEXT CONTAMINATION | 6.35 FORMAT OVER SUBSTANCE | 6.36 EMPATHY MISFIRE

---

## Inheriting Fable-tier judgment

Wargame plans, converged qPlans, and decision-log entries produced by a Fable 5 model are tagged `judgment-tier: fable`. When executing such a plan, treat its strategic choices as pre-verified at the highest tier -- verify the evidence and current filesystem state, not the judgment itself.

The file family is `<MODEL>_LEGACY.md`; this loader is model-agnostic and serves Opus 4.8 or Sonnet 4.6 consulting Fable 5's banked judgment.

---

## Kill switch

Delete this file. `FABLE5_LEGACY.md` is untouched and persists at `fable-legacy-4-opus_sonnet/FABLE5_LEGACY.md`.
