# design-full — focus gate protocol (G1, G2, G3)

Purpose: every gate answers two questions with evidence: (1) which variant
wins overall, (2) WHICH KINDS of people prefer which variant and WHY (broad
strokes). Never present a gate result without the per-segment breakdown.

## Budgets

| Budget | G1 (brand) | G2 (screens) | G3 (final) |
|--------|-----------|--------------|------------|
| lite | panel-lite ~24 | panel-lite ~24 | panel-lite ~24 |
| standard (default) | panel-lite ~24 | panel-lite ~24 | full /focus-group (215) |
| max | full comparative | full comparative | full comparative |

Before dispatching ANY fleet: state agent count and rough token estimate
(A4 cost gate). Panel-lite ~24 agents x ~2-4k tokens; full 215 x ~2-4k.

## Comparative single run (the core trick)

All 3 variants go into ONE brief; each persona ranks them. Never one run per
variant (3x cost, no direct ranking).

## Panel-lite procedure (G1/G2 at standard)

1. `python <skill>/scripts/panel_sample.py --n 24 [--youth-boost] [--seed 42]`
   -> persona list. --youth-boost whenever avatars/young audience in scope.
2. For each sampled persona, read their block from the focus-group skill's
   reference file (path is in the JSON) and dispatch ONE subagent (sonnet
   tier) — all in parallel — with:
   - the persona block verbatim ("you ARE this person; react in their voice"),
   - the comparative brief (below),
   - the variant artifacts (inline the 3 boards' key facts, or file paths +
     a faithful text description of each variant: aesthetic extreme, palette,
     fonts, signature element, one screenshot-level description),
   - output contract: 80-200 words of in-character reaction, then the final
     line EXACTLY:
     `VERDICT | <id> <name> | <panel> | RANK: X>Y>Z | <one-line why>`
3. Save each response to `.design-full/panels/<gate>/<id>.md`.
4. `python <skill>/scripts/crosstab.py .design-full/panels/<gate> --json
   .design-full/panels/<gate>/crosstab.json`
5. Report = crosstab markdown verbatim + your characterization (below).

## Full-gate procedure (G3 at standard; every gate at max)

Invoke the `/focus-group` SKILL once with a comparative topic argument, e.g.:
"Compare three design directions for <product> and rank them. Variant A:
<extreme, palette, fonts, signature, feel>. Variant B: <...>. Variant C:
<...>. Also decide the open choices: <mobile nav A/B/C>, <avatar style
A/B/C>, <effect defaults>. For every persona: rank the variants and give a
one-line reason in the form RANK: X>Y>Z."
Then collect the per-persona responses from its report into
`.design-full/panels/G3/` and run crosstab the same way. If focus-group's
output lacks parseable RANK lines for some personas, count what parses and
say how many were unparseable — do not invent rankings.

## Comparative brief template

```
DESIGN GATE <G1|G2|G3> — <project name>
Product: <one line>  Audience: <one line>  Tone: <3 adjectives>
Evaluate the three variants below AS THE PERSONA YOU ARE. Consider first
impression, trust, appeal, and whether you would use/recommend it.
VARIANT A (<extreme>): <compact factual description>
VARIANT B (<extreme>): <...>
VARIANT C (<extreme>): <...>
Open choices (G3 only): <list>
End with exactly one line:
VERDICT | <your id and name> | <your panel> | RANK: X>Y>Z | <one-line why>
```

## Reporting the gate (mandatory format)

1. Crosstab tables (overall + per-segment) from crosstab.py, verbatim.
2. Per-variant characterization, 3-5 sentences each, plain language:
   "Variant B won with the achiever/rationalist segments (Spiral Orange, NT
   types) — they cited density and clarity. Variant C carried the youth and
   early-adopter personas on the avatars and motion. Variant A was the safe
   choice for traditionalist and high-context-culture personas; nobody
   hated it, nobody loved it."
3. Dissent note: the strongest argument AGAINST the winner, quoted.
4. Recommendation + what to borrow from the losers.

The user always makes the final pick; the gate informs, it does not decide.
