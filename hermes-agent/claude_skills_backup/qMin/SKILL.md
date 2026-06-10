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

Produce a short verdict, then auto-fix.

- **Pass** — proceed; no fixes needed.
- **Pass with notes** — list the notes, then auto-fix each note in order.
- **Block** — list the specific issues with `file:line` references, then auto-fix each issue in order.

Keep the verdict tight. One bullet per finding. Do not restate the diff.

## Auto-fix (the user's standing approval)

After printing the verdict, **do not wait for user approval to start fixing**. The user has pre-approved fixes for every `/qMin` run. The flow:

1. Print the verdict (Pass / Pass with notes / Block) and the finding list.
2. Immediately, **without confirmation**, apply fixes for each finding in order (Block first, then Pass-with-notes if any).
3. For each fix, output a one-line status: `- fix [<axis>] <file>:<line>: <what changed>`. `<axis>` is one of `minimal-scope`, `correctness`, `security`, `maintainability`, `quality`.
4. Use minimal, surgical edits per the rules in `~/.claude/CLAUDE.md` ("minimal precise edits", "don't refactor beyond what the task requires").
5. After all fixes are applied, if the project has a type-checker / linter / test command wired up, run it and report the result in one line.

**Skip a finding (do not auto-fix) when ANY of these hold:**
- It requires a design decision the verdict itself flagged as needing a human call.
- The fix would require rewriting tests, touching > 100 LOC across > 5 files, or modifying a public API contract.
- The fix involves removing user-supplied code the user explicitly asked for ("while-I'm-here cleanup" the user requested anyway is still surface-only).

For each skipped finding output: `- skip [<axis>] <file>:<line>: <one-line reason>`.

## Do not

- Do not run multiple passes "for safety" if the diff hasn't changed — one review per state of the diff is enough. (The original instruction to run three times was ritual, not engineering.)
- Do not skip the verdict and jump straight to fixing — the user wants the verdict + finding list visible BEFORE the fix lines, so they can see what's being acted on.
- Do not expand scope by suggesting unrelated improvements.
- Do not undo user-intentional changes (the "minimal scope" axis flags scope-drift; if the user clearly intended that change, the fix is just a note, not a revert).
