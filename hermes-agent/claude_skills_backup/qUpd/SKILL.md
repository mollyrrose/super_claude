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
   - `exclude/SYSTEM_STRATEGIES/TODO.md` (canonical, gitignored per-project location — check first), else an older `exclude/TODO.md` or root `TODO.md` — work-in-progress and open items
   - `CHANGELOG.md` — release-style notes
   - `exclude/SYSTEM_STRATEGIES/SYSTEM_STATUS.md` (canonical, gitignored location) — current
     "what's running, what's done, what's not" snapshot. **Always maintained** — see the
     "SYSTEM_STATUS + draw.io system map" section below. (Legacy locations like a root
     `STATUS.md` / `SYSTEM_STATUS.md` still count if a project already has one.)
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
- **qGoal multi-variant runs** — if the session ran a `/qGoal` multi-variant loop (the Arbor backend qGoal uses for optimization tasks), the authoritative "what changed" is NOT just the chat: read `<project>/.arbor/sessions/<run>/REPORT.md` and `.coordinator/idea_tree.md` for the final/merged score, the winning branch, and the key insight. Record in INDEX/CHANGELOG: the goal, the metric delta (baseline -> merged, absolute values not deltas), the merged `qgoal/trunk/<run>` branch, and any decision-log entry the run wrote. Do not commit `.arbor/` or `.qgoal/` itself (gitignored run state).

## SYSTEM_STATUS + draw.io system map (maintain every run)

Every project keeps a living system map in **`exclude/SYSTEM_STRATEGIES/`** (the
gitignored `exclude/` folder; create it if missing). Two files, kept in sync:

- **`SYSTEM_STATUS.md`** — the text snapshot: components, what's running / done /
  not, key data flows, current blockers. Refresh it whenever this session changed
  the live state (added/removed a component, changed a flow, shipped/broke a piece).
- **`system_map.drawio`** — the *visual* of the same architecture, generated and
  updated via the **`drawio-skill`** (architecture preset). The `.drawio` XML is
  the source of truth and works on Windows with no extra install; PNG/SVG export
  is optional and only needs the draw.io desktop CLI.

Rules:
1. **Keep the two in agreement.** The diagram must depict exactly the components
   and flows described in `SYSTEM_STATUS.md`. If you edit one because the
   architecture changed, update the other in the same qUpd run.
2. **Missing -> create now, do NOT ask.** If `SYSTEM_STATUS.md` does not exist in
   a project with real structure, CREATE it on THIS qUpd run and write how the
   system is currently built (components, what runs / done / not, key data flows)
   from the repo's present state. Do not merely flag its absence, and do not
   offer to make it "if you want" / "later" — make it. Create `system_map.drawio`
   alongside it in the same run. Only skip for a genuinely trivial/empty project
   (no real structure to describe).
3. **Redraw guard is for UPDATES only.** Once the map exists, regenerate the
   diagram only when the architecture actually changed (new/removed component,
   new/changed data flow) — not for a typo or status-line tweak (ponytail: don't
   redraw for nothing). This guard NEVER blocks the first creation in rule 2:
   "the session only added tooling, not a running component" is a valid reason to
   skip a *redraw*, never a reason to skip *creating* a missing SYSTEM_STATUS.
4. To (re)generate the diagram, invoke the `drawio-skill` with the component list
   from `SYSTEM_STATUS.md` as input; write the output to
   `exclude/SYSTEM_STRATEGIES/system_map.drawio`.
5. **Consolidate + gitignore + rewrite EVERY referrer.** The canonical task list
   also lives in this folder: `exclude/SYSTEM_STRATEGIES/TODO.md`. Ensure
   `exclude/` is in `.gitignore` (mandatory — add it if missing). If an older
   `TODO.md` / `SYSTEM_STATUS.md` / `system_map.drawio` sits at the repo root or
   directly under `exclude/`, MOVE it here (reorganize, no duplicates).

   **Then chase down every reference to the OLD path and rewrite it — not just
   `INDEX.md`.** Moving a file silently breaks any doc or script that still names
   the old location. So after each move:
   - Grep the whole repo for the old path (try every form a file might use:
     the bare name `TODO.md`, the old relative path `exclude/TODO.md`, a root
     `SYSTEM_STATUS.md`, `system_map.drawio`, with both `/` and `\` separators).
   - Rewrite **every** hit to the new `exclude/SYSTEM_STRATEGIES/...` path —
     across `INDEX.md`, `STARTUP.md`, `AGENTS.md`, `README.md`, any `docs/*`, and
     any script (`.py`, `.ps1`, `.sh`, `.js`) that opens or names the file. Do
     not stop at `INDEX.md`; do not leave a "flag: these files may still point at
     the old path" note instead of fixing them — fix them all in this run.
   - Skip only matches that are genuinely about a *different* file (e.g. a
     `TODO.md` belonging to another subproject, or the literal string inside this
     very qUpd skill). When unsure whether a hit is the moved file, open it and
     check before editing.
   - After rewriting, re-grep for the old path to confirm zero stale references
     remain (other than intentional ones), and list each rewritten file in the
     run's output.

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
