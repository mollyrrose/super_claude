---
name: mp-diagnosing-bugs
description: Diagnosis loop for hard bugs and performance regressions. Use when the user says "diagnose"/"debug this", or reports something broken/throwing/failing/slow. Six-phase discipline: build a feedback loop, reproduce, hypothesise, instrument, fix, cleanup.
source: https://github.com/mattpocock/skills/tree/main/skills/engineering/diagnosing-bugs
license: MIT
---

# Diagnosing Bugs

A discipline for hard bugs. Skip phases only when explicitly justified.

When exploring the codebase, read `CONTEXT.md` (if it exists) to get a clear mental model of the relevant modules, and check ADRs in the area you're touching.

## Phase 1 -- Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a **tight** pass/fail signal for the bug -- one that goes red on *this* bug -- you will find the cause. If you don't, no amount of staring at code will save you.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse to give up.**

### Ways to construct one (try in this order)

1. **Failing test** at whatever seam reaches the bug -- unit, integration, e2e.
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
4. **Headless browser script** (Playwright / Puppeteer) -- drives the UI, asserts on DOM/console/network.
5. **Replay a captured trace.** Save a real network request / payload / event log to disk; replay it in isolation.
6. **Throwaway harness.** Spin up a minimal subset of the system that exercises the bug code path.
7. **Property / fuzz loop.** If the bug is "sometimes wrong output," run 1000 random inputs and look for the failure mode.
8. **Bisection harness.** Automate "boot at state X, check, repeat" so you can `git bisect run` it.
9. **Differential loop.** Run the same input through old-version vs new-version and diff outputs.
10. **HITL bash script.** Last resort. If a human must click, drive them with a structured script so the loop is still repeatable.

### Tighten the loop

Once you have a loop, **tighten** it:
- Can I make it faster? (Cache setup, skip unrelated init, narrow the test scope.)
- Can I make the signal sharper? (Assert on the specific symptom, not "didn't crash".)
- Can I make it more deterministic? (Pin time, seed RNG, isolate filesystem, freeze network.)

### Completion criterion -- a tight loop that goes red

Phase 1 is done when you can name **one command** -- a script path, a test invocation, a curl -- that you have **already run at least once**, and that is:
- **Red-capable** -- it drives the actual bug code path and asserts the user's exact symptom.
- **Deterministic** -- same verdict every run.
- **Fast** -- seconds, not minutes.
- **Agent-runnable** -- you can run it unattended.

If you catch yourself reading code to build a theory before this command exists, **stop.** No red-capable command, no Phase 2.

## Phase 2 -- Reproduce + minimise

Run the loop. Watch it go red.

Confirm:
- The loop produces the failure mode the **user** described -- not a different failure nearby.
- The failure is reproducible across multiple runs.
- You have captured the exact symptom.

**Minimise:** Shrink the repro to the smallest scenario that still goes red. Cut inputs, callers, config, data, and steps one at a time, re-running after each cut.

## Phase 3 -- Hypothesise

Generate **3-5 ranked hypotheses** before testing any of them.

Each must be **falsifiable**: "If X is the cause, then changing Y will make the bug disappear / changing Z will make it worse."

If you cannot state the prediction, the hypothesis is a vibe -- discard or sharpen it.

**Show the ranked list to the user before testing.** They often have domain knowledge that re-ranks instantly. Don't block on it -- proceed with your ranking if the user is AFK.

## Phase 4 -- Instrument

Each probe must map to a specific prediction from Phase 3. **Change one variable at a time.**

Tool preference:
1. **Debugger / REPL inspection** if the env supports it. One breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that distinguish hypotheses.
3. Never "log everything and grep."

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at the end becomes a single grep.

**Perf branch.** For performance regressions: establish a baseline measurement first, then bisect. Measure first, fix second.

## Phase 5 -- Fix + regression test

Write the regression test **before the fix** -- but only if there is a **correct seam** for it.

A correct seam is one where the test exercises the **real bug pattern** as it occurs at the call site.

**If no correct seam exists, that itself is the finding.** Note it. The codebase architecture is preventing the bug from being locked down. Flag this for `/improve-codebase-architecture`.

If a correct seam exists:
1. Turn the minimised repro into a failing test at that seam.
2. Watch it fail.
3. Apply the fix.
4. Watch it pass.
5. Re-run the Phase 1 feedback loop against the original (un-minimised) scenario.

## Phase 6 -- Cleanup + post-mortem

Before declaring done:
- Original repro no longer reproduces (re-run the Phase 1 loop)
- Regression test passes (or absence of seam is documented)
- All `[DEBUG-...]` instrumentation removed (`grep` the prefix)
- Throwaway prototypes deleted

**Then ask: what would have prevented this bug?** If the answer involves architectural change (no good test seam, tangled callers, hidden coupling) hand off to `/improve-codebase-architecture` with the specifics. Make the recommendation **after** the fix is in, not before.
