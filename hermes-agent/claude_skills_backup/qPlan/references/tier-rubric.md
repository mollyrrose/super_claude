# Tier rubric — Structural / Behavioral / Editorial

Apply these rules mechanically. Only fall back to the arbiter when every rule
below returns `ambiguous`. Log both the tier and the rule (or arbiter
justification) into the ledger.

## Structural

Returns **Structural** if ANY of these is true for the accepted change:

- Adds, removes, or merges a top-level section of the plan (a phase, a
  layer, a major decision).
- Changes the chosen algorithm, data structure, or architecture pattern
  (e.g. "use a queue" → "use a stream", "monolith" → "split into services").
- Adds, removes, or changes a top-level dependency (new package, new
  service, new external API, new language/runtime).
- Changes the order of phases / steps that affect what gets built first.
- Reverses an earlier decision logged in the ledger as accepted.

## Behavioral

Returns **Behavioral** if Structural does not apply AND ANY of these is true:

- Adds, removes, or renames a function/method that has call sites.
- Changes a function signature (parameters added, removed, reordered, or
  re-typed).
- Changes a return shape or output schema.
- Changes a configuration default value (not just the field's documentation).
- Changes a control-flow branch (new `if`, removed `if`, swapped condition).
- Changes test-pass/fail status under the same input.
- Adds, removes, or changes validation logic.
- Changes an error message *that callers parse* (not human-only).

## Editorial

Returns **Editorial** if neither Structural nor Behavioral applies AND ANY of
these is true:

- Pure rename without call-site impact.
- Comment add / remove / edit.
- Whitespace, formatting, ordering of import lines.
- Label, caveat, or section-title text change without semantic change.
- Wording polish, typo fix, grammatical improvement.
- Adding or removing a footnote, link, or aside.

## Ambiguous → arbiter

Return `ambiguous` ONLY if:

- A change has both Structural and Editorial properties and it is not clear
  which dominates (e.g. a renamed section that also reorders content).
- A change might be Behavioral but only because of an effect on observers
  that aren't yet known (e.g. a logging change that downstream parsers may
  or may not depend on).

When ambiguous, the arbiter hat picks one tier and logs a single-sentence
justification. Arbiter bias rules:

- If the only behavioral effect is hypothetical, lean Editorial.
- If the only structural effect is cosmetic, lean Editorial.
- Do not invent Structural to keep the loop running.
- Do not invent Editorial to stop the loop early.

## Worked examples

| Change | Tier | Rule |
|---|---|---|
| "Split Phase B into B1 + B2" | Structural | new phase |
| "Switch from Redis to Postgres for the lock" | Structural | dependency change |
| "Rename `handle()` to `process()` and update 12 callers" | Behavioral | renamed function with call sites |
| "Add a `timeout: int = 30` parameter to `fetch()`" | Behavioral | parameter added |
| "Add a `// TODO: maybe refactor` comment" | Editorial | comment |
| "Rephrase 'we should use X' → 'we will use X'" | Editorial | wording polish |
| "Reorder the bullet list under Approach" | Editorial | ordering |
| "Rename internal helper `_x` → `_y` (no external callers)" | Editorial | rename without call-site impact |
| "Change log line format that ops scripts may parse" | Ambiguous → arbiter | unknown observers |
