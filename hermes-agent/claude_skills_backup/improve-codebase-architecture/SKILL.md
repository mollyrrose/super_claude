---
name: improve-codebase-architecture
description: Identify architectural friction points and propose deepening opportunities -- refactors that transform shallow modules into deep ones, improving testability and AI navigability. Use when the codebase has many small modules, repeated cross-file bouncing, or hard-to-test code paths.
source: https://github.com/mattpocock/skills/blob/main/skills/engineering/improve-codebase-architecture/
license: MIT
---

# Improve Codebase Architecture

Identify **deepening opportunities** -- refactors that transform shallow modules into deep ones, improving testability and AI navigability. Use domain vocabulary from `CONTEXT.md` if it exists. Favor terms like "module" and "seam" over "service" or "component."

## Exploration Phase

Examine recent commit history to locate hot spots. Do not apply rigid heuristics -- look at what actually changes together.

**Friction signals:**
- Understanding one concept requires bouncing between many small modules
- Changes require touching many files for a single logical change
- Tests require extensive mocking to test any one unit
- Functions that must be read in a specific mental order to make sense

**The deletion test** validates suspected shallow modules: if deleting one concentrates complexity rather than just relocating it, that is the target signal. Ask: "If we deleted this module, where would its logic go? Is that one place or many?"

## Report Generation

For each candidate, output:

```
## Candidate: <Name>

**Files involved:** `path/to/a.ts`, `path/to/b.ts`

**Problem:** <What makes this hard to understand or change?>

**Deletion test:** <If we deleted X, where would its logic go?>

**Proposed deepening:** <What the refactored structure looks like in plain English>

**Benefits:**
- Locality: <what can now be understood without cross-referencing>
- Leverage: <what future changes become cheaper>
- Testability: <what can now be tested without mocking>

**Recommendation:** Strong | Worth exploring | Speculative

**Incremental path:** <How to do this one caller at a time>
```

Use Mermaid diagrams for before/after when helpful.

## After Selecting a Candidate

The grilling loop -- work through these before committing:
1. What changes at call sites?
2. Does any public API contract change?
3. Can this be done incrementally (one caller at a time)?
4. Is there a correct test seam for the refactored code?

Document decisions in `CONTEXT.md` as terminology sharpens or new module names emerge.

## Deepening Patterns

**Shallow -> deep transformation:**
- Multiple 50-line files that all import from each other -> one well-structured 200-line module
- A "types" file + a "utils" file + a "handlers" file for one feature -> one feature module
- A thin wrapper around an external library -> a rich adapter with the library's concepts mapped to yours

## Anti-Patterns to Surface

| Anti-Pattern | Signal | Fix |
|---|---|---|
| Micro-module explosion | Many files, each 10-30 lines | Consolidate by feature/domain |
| Circular imports | Module A imports B imports A | Identify the shared concept, extract it |
| Shotgun surgery | One logical change touches 8+ files | Find what should own this concept |
| Anemic domain model | Data objects separate from logic | Co-locate behavior with the data it uses |
| Leaky abstractions | Internal implementation details visible at call sites | Narrow the public surface |

## Integration with diagnosing-bugs

When architectural issues prevent writing good regression tests (no correct seam exists), flag the architectural problem here. The `/mp-diagnosing-bugs` skill's Phase 5 explicitly surfaces this: "the codebase architecture is preventing the bug from being locked down."
