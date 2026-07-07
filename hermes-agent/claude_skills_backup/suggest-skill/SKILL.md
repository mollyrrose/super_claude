---
name: suggest-skill
description: "Meta-skill: given a task description, suggest the 2-4 best-fit skills from the 208+ installed. Fast matchmaker between what you want and what handles it."
argument-hint: "<task description> — e.g. 'audit this codebase for over-engineering' or 'I want a deep dive on this topic'"
---

# suggest-skill

Given a task description, return the 2-4 best-fit skills with a one-line reason each.
Invoked via `/suggest-skill <task>` or suggested automatically by the smart router.

---

## Usage

```
/suggest-skill review my PR for security issues
/suggest-skill I want to understand this research paper deeply
/suggest-skill plan out the next sprint
/suggest-skill                    <- no arg: show this taxonomy + ask for task
```

If called with no argument: print the taxonomy below and ask the user to describe their task.

---

## Matching heuristics

When given a task description, apply these in order:

1. **Is it a review / quality gate on code you just wrote?** -> `/qMin` (quick, every edit) or `/qRev` (major change, 15-agent parallel sprint)
2. **Is it a planning problem (what to build, architecture, priorities)?** -> `/think` (one round) or `/qPlan` (iterated with critics) or `/wargame` (adversarial battle plan)
3. **Is it research / learning about a topic (not code)?** -> `/learn`
4. **Is it a root-cause / bug hunt?** -> `/hunt`
5. **Is it a full sprint end-to-end execution?** -> `/qGoal`
6. **Is it a security audit or pentest?** -> `/pentest`
7. **Is it documentation / status update?** -> `/qUpd`
8. **Is it writing prose, content, or a document?** -> `/write` or `/rewrite`
9. **Is it about a skill or the harness itself?** -> `/hermes-curate`, `/create-skill`, `/find-skills`
10. **Does it need a multi-persona / focus-group critique?** -> `/focus-group`

Suggest the minimum number of skills that cover the task. 2 is ideal. 4 is the max.
For each suggestion, give: **skill name** + one sentence on why it fits and what it does differently from the others.

---

## Skill taxonomy

### Planning / Thinking
- `/think` -- single-round design/architecture decision with a validated plan; use for "how should I approach X?"
- `/qPlan` -- author+critic iteration loop with multi-model panel; use when you want pushback on your plan before committing
- `/qGoal` -- end-to-end goal execution (brain/hands separation); use when you know the goal and want it done
- `/wargame` -- adversarial battle-plan via Fable-tier judgment; use for "tear this apart before I do it"
- `/improve` -- codebase audit that produces prioritized, self-contained improvement plans
- `/ponytail` -- YAGNI/minimal-code over-engineering pass; use to kill unnecessary complexity

### Code Review / Quality
- `/qRev` -- full 15-agent parallel sprint review, 3-pass; use for major PRs and big changes
- `/qMin` -- quick mandatory post-edit review; use after every non-trivial edit
- `/rev` -- sprint-close multi-agent code audit; use at end of a feature branch
- `/check` -- pre-release/pre-merge review against project constraints
- `/hunt` -- root-cause analysis for bugs and regressions; give it a symptom, it finds the cause

### Research / Learning
- `/learn` -- 6-phase structured deep-dive into a topic; builds a mental model, not just a summary
- `/hermes-learn` -- in-session skill capture from the current conversation; use when you notice a recurring pattern this session
- `/hermes-curate` -- drain the curator queue and promote recurring cross-session patterns into new skills

### Skills / Self-Improvement
- `/hermes-curate` -- auto-curate patterns into new skills (cross-session)
- `/hermes-learn` -- in-session skill capture (within this conversation)
- `/create-skill` -- scaffold a new skill file interactively
- `/find-skills` -- search installed skills by keyword
- `/suggest-skill` -- this skill: task -> best-fit skill (you are here)
- `/rev-learn` -- extract learnings from qRev results into semgrep rules and memory

### Orchestration / Agents
- `/fable-orchestration` -- set up Fable 5 as architect with Opus 4.8 executor fleet; use for complex multi-step plans that need top-tier reasoning at the design stage
- `/qDo` -- one-shot task execution, lighter than qGoal; use for a bounded task with clear scope

### Documentation / Status
- `/qRem` -- session-start orientation + proactive improvement block; run at the start of a new session
- `/qUpd` -- update INDEX.md, TODO.md, SYSTEM_STATUS.md, and the draw.io diagram
- `/qClose` -- sprint close: review + commit + push + handoff note
- `/qContent` -- extract structured content (decisions, todos, facts) from the current conversation
- `/drawio-skill` -- generate or update architecture diagrams in draw.io XML format

### Multi-Persona / Analysis
- `/focus-group` -- multi-persona critique of ideas, content, or UX; use when you want diverse viewpoints, not just one
- `/qPlan` (panel mode) -- multi-critic analysis with cross-model voices; use when you want a plan stress-tested

### Security
- `/pentest` -- penetration testing and security audit; use before shipping or for a security-focused review pass
- `/skillspector-gate` -- scan a GitHub repo or skill before installing; use any time you're about to pull in external code

### Wargame / Battle Plans
- `/wargame` -- full wargame cycle: recon -> missions -> red-team -> grade -> ledger; use when the stakes are high and you want adversarial pre-mortems

### Writing / Content
- `/write` -- draft a document, email, or structured written piece
- `/rewrite` -- rewrite for clarity, tone, or style; preserves intent, improves delivery
- `/translate-book` -- book or long-document translation
- `/title-gen` -- generate title options for a piece of content

### Specialized
- `/graphify` -- build a queryable knowledge graph from code, docs, papers, or images
- `/radar-scan` -- monitor the AI tool landscape for new or changed tools
- `/radar-check` -- check a specific tool or library against the radar
- `/hermes-spike` -- time-boxed technical spike; use to explore feasibility of one specific thing before committing

---

## Output format (when a task is given)

```
Task: <restate the task in one line>

Best fits:
1. /skill-name -- reason it fits this task specifically (1 sentence)
2. /skill-name -- reason it fits (1 sentence)
[3. /skill-name -- if a third genuinely adds value]

To run: /skill-name <optional args>
```

Do not pad. Do not list skills that don't apply. If one skill is clearly the right answer, say so and name the runner-up only if it adds something distinct.
