---
name: hermes-curate
description: "Drain the hermes-curator session queue — read each pending transcript, extract truly-recurring skill candidates, write them directly under ~/.claude/skills/hermes-auto-* (no manual review step). Uses the current session's Claude — no external API."
---

# hermes-curate — drain the curator queue

The hermes-curator system runs as two hooks:

- **Stop hook** records each finished Claude Code session into a queue at
  `~/.claude/.hermes_curator_queue.json`. No LLM work happens at session
  end.
- **UserPromptSubmit hook** detects when the queue threshold is met and
  instructs you (Claude) to drain it silently before answering the user's
  actual prompt.

This skill is what actually **drains the queue**. The user has chosen
fully-automatic operation — **no `skills-pending/` review step**. New
skills go directly into `~/.claude/skills/hermes-auto-<slug>/SKILL.md`.
That increases the bar for what qualifies: prefer writing **fewer, more
certain** skills over many speculative ones.

No external API key, no separate provider configuration. The cost is
whatever this session is already costing.

## When to use

- The UserPromptSubmit hook injected the auto-curate directive into
  the prompt context. Process the queue **before** addressing the
  user's actual request.
- The user typed `/hermes-curate` explicitly (rare; default flow is
  auto).

Skip when the queue is empty or it was already drained recently. The
skill checks first.

## How to run

### 1. Read the queue

```bash
test -f ~/.claude/.hermes_curator_queue.json && \
  cat ~/.claude/.hermes_curator_queue.json
```

If empty or missing, report "queue empty, nothing to drain" in the
one-line status and proceed with the user's prompt.

### 2. Read each pending transcript

For every entry in `pending[]`, open `transcript_path` (a JSONL file
written by Claude Code). It can be large — read line by line and stop
when you have enough signal (~300 lines is usually plenty).

Each line is a JSON object with `role`/`type`, `content` (text or
blocks), tool calls, results. You only need to absorb the **shape** of
the session — what task the user pursued, which tools repeated, how
the work resolved.

### 3. Identify high-confidence patterns ONLY

Because candidates go directly into the active skill list, **be
conservative**. Only write a skill when ALL of the following hold:

- The pattern appears in **at least two** sessions of the queue, OR is
  obviously repeatable from a single session because the procedure is
  generic (the project specifics are clearly strippable).
- The procedure is **non-obvious** — a fresh agent would not figure
  it out from defaults alone.
- The **shape** is generalisable — no client-specific identifiers,
  paths, project names, secrets.
- The user did NOT explicitly say "do not repeat this".

Skip:
- One-off project tasks.
- Trivial things ("read a file", "search for a term").
- Anything that is already covered by a `hermes-*` skill installed by
  the converter — check `~/.claude/skills/hermes-*/SKILL.md` first.
- Anything that looks even slightly bespoke.

**Zero candidates from a queue of N is the expected result most of the
time.** Bias hard toward writing nothing.

### 4. Write each candidate directly into ~/.claude/skills/

For each pattern that passes the bar, create a folder:

```
~/.claude/skills/hermes-auto-<slug>/SKILL.md
```

The `hermes-auto-` prefix is reserved for curator output — never reuse
it for anything else, and never write outside this prefix. The user can
bulk-remove auto-generated skills with
`Remove-Item -Recurse ~/.claude/skills/hermes-auto-*` if any go bad.

If `~/.claude/skills/hermes-auto-<slug>/SKILL.md` already exists, do not
overwrite. Either pick a slightly differentiated slug
(`-<short-context>` suffix) or skip — overwriting an existing
auto-skill could destroy edits the user made manually.

SKILL.md template:

```markdown
---
name: hermes-auto-<slug>
description: "<one short sentence — what this skill is for>"
source: hermes-curator-auto
created: <YYYY-MM-DDTHH:MM:SS+00:00>
origin_sessions: [<session_id_1>, <session_id_2>, ...]
confidence: <"two-or-more-sessions" | "single-session-generic">
---

# hermes-auto-<slug>

## When to use

(One paragraph: the specific trigger that should make a future agent
reach for this skill. Be concrete — vague triggers waste skill slots.)

## How to run

1. (Step.)
2. (Step.)
3. (Step.)

## What to avoid

- (Specific failure mode you observed in the sessions.)

## Output

(Expected output shape.)
```

Keep the body short — 30–80 lines of body. A working skill is
concrete, not exhaustive.

### 5. Mark the queue drained

After writing all skills (or determining none qualified), run via the
Bash tool:

```python
python -c "
import sys
sys.path.insert(0, '<path-to-hermes-fork>/claude_code_integration')
from curator_core import mark_drained
print(mark_drained(['<session_id_1>', '<session_id_2>', ...], <candidates_written>))
"
```

The fork path is typically `D:/projects/hermes_claude/hermes-agent` on
Windows or `~/projects/hermes_claude/hermes-agent` on Linux/macOS — use
the actual install path you can confirm with a quick `ls` first.

`mark_drained` removes the listed session ids from the queue and stamps
the drain time in `~/.claude/.hermes_curator_state.json`, so the
UserPromptSubmit hook stops nagging until the next threshold trip.

If you cannot import `curator_core` (e.g. the fork isn't reachable),
edit `~/.claude/.hermes_curator_queue.json` directly: rewrite it to
`{"pending": []}`, and write
`{"last_drain_at": "<UTC ISO timestamp>"}` to
`~/.claude/.hermes_curator_state.json`.

### 6. Status line + continue

Prepend a single line to your reply in this exact format:

```
· curator: drained <N> session(s), wrote <M> auto-skill(s)
```

then answer the user's actual prompt normally. If you wrote any
auto-skills, you may optionally append after the status line, on a
second line, the slug names in a comma-separated list, e.g.:

```
· curator: drained 5 session(s), wrote 2 auto-skill(s)
  → hermes-auto-pivot-table-from-csv, hermes-auto-tdd-migration-script
```

That gives the user a quick glance at what was created without
forcing them to inspect the directory. Cap this listing at 5 names.

## Style rules

- **Conservative output** — zero skills written is a valid and
  expected outcome.
- **Cite session ids in `origin_sessions`** so the user can trace a
  skill back to its source.
- **One pattern per file**.
- **Match the project's voice** — if the source sessions were in
  Hungarian, write the skill body in Hungarian.
- **Always update the queue** even when you wrote zero skills — the
  drain is what stops the reminder.

## What NOT to do

- Do not write under `hermes-` (no `-auto-` suffix). That prefix
  belongs to the converter and would shadow an upstream skill.
- Do not overwrite an existing `hermes-auto-*` skill.
- Do not invent details the transcripts don't contain.
- Do not write a skill whose body is "TODO" or placeholder text —
  if the pattern isn't clear enough to write concrete steps, the bar
  is not met.
- Do not let curator work block the user's request — if anything goes
  wrong, mention it in one line and proceed.
