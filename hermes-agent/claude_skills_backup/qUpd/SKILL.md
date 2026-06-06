---
name: qUpd
description: Update a project's tracking docs (INDEX.md, TODO.md, CHANGELOG.md) to reflect what changed in the current session. Run at the end of a working session, or before a commit, when there is real progress worth recording. Skip for trivial edits.
---

# qUpd — Quick Doc Update from Session State

## When to use

- End of a working session that produced non-trivial code, feature, fix, or design decision.
- Before a commit, when the project has tracking docs (INDEX.md / TODO.md / CHANGELOG.md / similar).
- When the user explicitly asks to "update INDEX/TODO" or "log this session".

Skip when nothing meaningful changed (read-only exploration, single-line tweaks, doc-only edits).

## How to run

1. **Reconstruct the session** from the actual conversation context — completed tasks, files edited (with line refs), decisions made, blockers found, follow-ups identified. Do not invent details. If a fact is uncertain, leave it out.

2. **Locate the project's tracking docs.** Look for files in the project root or a docs folder:
   - `INDEX.md` — narrative project overview / session log
   - `TODO.md` or `tot.md` — work-in-progress and open items
   - `CHANGELOG.md` — release-style notes
   - `STATUS.md` / `SYSTEM_STATUS.md` (e.g. under `SYSTEM_STRATEGIES/` for AI EA) — current
     "what's running, what's done, what's not" snapshot. **Often goes stale — refresh it
     whenever the session changes the live state of components.**
   - `STARTUP.md`, `AGENTS.md`, project-specific equivalents
   If a doc doesn't exist, do not create it unless the user asks.

3. **Match each finding to the right doc and the right section.** Read the existing doc to learn its style (Hungarian / English, bullet hierarchy, date format, section header conventions, code-fence usage). Mirror it. Do not impose a new format on an old doc.

4. **Make minimal, additive edits.** Add new entries; mark resolved items resolved; update "last updated" / dátum / version stamps. Do not rewrite paragraphs that didn't change. Do not delete history.

5. **For each edit, surface a one-line summary** so the user sees what landed where (e.g. `INDEX.md: appended 2026-05-05 session bullet under "Korábbi session összefoglalók"`).

## What to capture

- **Completed work** — features shipped, bugs fixed, decisions made (with the *why*).
- **State changes** — DB row counts, throughput, ETA estimates that materially shifted.
- **New artifacts** — new files, scripts, endpoints, schemas (with paths).
- **Verification evidence** — measurements, test pass/fail, observed runtime behavior.
- **Open follow-ups** — items the session identified but did not resolve. Move them to TODO.md, do not bury them in INDEX.md prose.
- **Reversal of prior plans** — if the session abandoned an earlier approach, mark the corresponding TODO entry resolved/obsolete with a one-line reason.

## Commit + push at the end

After the doc edits land, treat the session as a unit of progress and commit it.

1. **Always commit** — once the doc updates are written, follow the standard git commit flow (see the Bash tool's "Committing changes with git" section): inspect `git status` / `git diff` / `git log`, draft a concise message that names the *why*, stage only the relevant files (avoid `git add -A` to skip stray secrets/binaries), and create the commit with the standard `Co-Authored-By: Claude …` trailer. Never amend an existing commit unless the user asks. If a pre-commit hook fails, fix the underlying issue and create a new commit — never `--no-verify`.

2. **Push only when a topic closes.** A "topic closes" means the work the user named is finished, not just that one doc was updated. Examples that warrant a push: a feature shipped end-to-end, a bug fix verified, a planned blokk in TODO.md marked done. Do not push for mid-session checkpoints, partial work, or doc-only refactors. When in doubt, ask. Never force-push (`--force` / `-f`) or push to a branch you don't own.

3. **Show the user what you did.** One line per action: `commit <hash> on <branch>: <subject>` and `pushed to <remote>/<branch>`. If you skipped the push, say so and why ("topic still in progress").

If the repo has no remote configured, or the user has explicitly asked you not to push, commit only. Surface the choice.

## What NOT to do

- Do not invent metrics, dates, or commit hashes. Use only what was verified in the session.
- Do not restate the entire diff — write a session-level summary, not a code review.
- Do not add aspirational items ("we should also do X") unless the user explicitly raised them.
- Do not change the doc's voice or language. If the doc is in Hungarian, write in Hungarian.
- Do not move large blocks around for tidiness. Append, don't reorganize.
- Do not push for partial work. Topic-closure is the bar — when uncertain, ask the user.

## Output

After the edits, give the user:

- One bullet per file touched, with the section name and the gist of what was added.
- A flag if you couldn't find an obvious place for some finding (so the user can decide where it belongs).
- Nothing else. No closing summary, no "let me know if…".
