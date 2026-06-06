---
name: hermes-learn
description: "In-session skill capture — pull a fresh skill out of THIS conversation while the context is hot. Writes directly to ~/.claude/skills/hermes-auto-<slug>/. Conservative bar; zero output is a valid outcome."
---

# hermes-learn — capture a skill from the current session

Companion to `hermes-curate`. The curator works after-the-fact off
transcript queues; `hermes-learn` works **right now**, with the live
session context still in your head, which means the captured skill is
usually higher-quality than what the queue-driven analysis would
produce hours later.

## When to use

- The user just walked you through something non-obvious and asks "save
  this".
- You (Claude) notice you've solved the same shape of problem in this
  session that you'd want to remember next time.
- The user typed `/hermes-learn`.

Skip when:
- The pattern is project-specific with nothing transferable.
- The conversation is still mid-flight and you're not sure how it
  resolves.
- A `hermes-*` or `hermes-auto-*` skill already covers it. Check
  `ls ~/.claude/skills/` first.

## How to run

### 1. Identify the pattern from THIS session

Look at the last 20–60 turns. What is the **reusable shape**?

A pattern qualifies when:
- The procedure is non-obvious enough that a fresh agent benefits from
  written guidance.
- It generalises — strip project specifics, keep the structure.
- It is concrete — you can write the steps without inventing details.

If the session is still in progress and the pattern is half-formed,
**defer**. Tell the user "let's run /hermes-learn once this is
finished".

### 2. Write the skill

Pick a slug: `kebab-case`, descriptive, under 40 chars. Avoid
collisions:

```bash
ls ~/.claude/skills/ | grep -i <slug>
```

If anything matches, suffix the slug (`-v2`, `-pg`, `-windows`) or
pick a different stem entirely.

Create `~/.claude/skills/hermes-auto-<slug>/SKILL.md`:

```markdown
---
name: hermes-auto-<slug>
description: "<one short sentence — what this skill is for>"
source: hermes-learn-in-session
created: <YYYY-MM-DDTHH:MM:SS+00:00>
origin_session: <session_id_if_known_else_omit>
---

# hermes-auto-<slug>

## When to use

(Specific trigger that should make a future agent reach for this skill.)

## How to run

1. (Step.)
2. (Step.)
3. (Step.)

## What to avoid

- (Failure mode you observed in this session.)

## Output

(Expected output shape.)
```

Body length: 30–80 lines. Concrete beats exhaustive.

### 3. Report

One block to the user:

```
/hermes-learn: wrote hermes-auto-<slug>
  -> ~/.claude/skills/hermes-auto-<slug>/SKILL.md
  description: <description>
```

Then continue with whatever the user was doing.

## Style rules

- Match the user's voice. If the session was in Hungarian, write the
  skill body in Hungarian.
- Cite this session's id in `origin_session` (Claude Code exposes it as
  `$CLAUDE_SESSION_ID` in some hook contexts; otherwise omit the field).
- Be honest about confidence: if a step is uncertain, leave it out
  rather than guess.

## What NOT to do

- Do not write under `hermes-` (no `-auto-` suffix). That prefix is
  reserved for the converter; collision will silently break.
- Do not overwrite an existing `hermes-auto-*` skill. Pick a different
  slug.
- Do not write multiple skills in one invocation. One pattern, one
  skill, one call.
- Do not capture work-in-progress. If the pattern isn't resolved yet,
  say so and defer.
