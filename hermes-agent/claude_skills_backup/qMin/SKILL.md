---
name: qMin
description: Review pending or proposed code changes for minimal scope, quality, security, maintainability, and correctness before they land. Invoke during planning and again before applying edits.
---

# qMin — Quality + Minimal Changes Review

## When to use

- After drafting a plan but before writing code (catches over-scoped plans).
- After staging edits but before applying or committing them (catches drift).
- When the user asks for a sanity check on a diff.

Skip for trivial edits (typo, single-line config tweak, doc-only changes) — the overhead isn't worth it.

## What to review

For each proposed or pending change, evaluate:

1. **Minimal scope** — Is every changed line load-bearing for the task? Flag refactors, renames, formatting changes, or "while I'm here" cleanups that the user did not ask for.
2. **Correctness** — Does the change do what it claims? Trace the call sites; check edge cases the user named.
3. **Security** — Any new input handled without validation at a trust boundary? New secrets, tokens, or PII paths? Injection risk (shell, SQL, path)? Permission downgrades?
4. **Maintainability** — New abstractions justified by ≥2 concrete uses? Names accurate? Comments explain *why*, not *what*? Dead code removed?
5. **Quality** — Type safety preserved? Errors handled at boundaries (not swallowed mid-flow)? Tests still pass / new behavior covered?

## Output

Produce a short verdict:

- **Pass** — proceed.
- **Pass with notes** — list the notes; user decides whether to address.
- **Block** — list the specific issues that must be fixed first, with file:line references.

Keep the verdict tight. One bullet per finding. Do not restate the diff.

## Do not

- Do not run multiple passes "for safety" if the diff hasn't changed — one review per state of the diff is enough. (The original instruction to run three times was ritual, not engineering.)
- Do not silently fix issues you find. Surface them; let the user (or the next implementation step) decide.
- Do not expand scope by suggesting unrelated improvements.
