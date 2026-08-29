---
name: council
description: Thin alias for qPlan's council mode -- anonymized peer-ranking across the cross-model critic roster. Invoked via /council (any case variant). All logic lives in the qPlan skill; this skill only re-invokes it with critic_provider council.
---

# /council -- alias for qPlan council mode

`/council` is a thin alias for `/qPlan` run with `critic_provider: council`.
It exists so the anonymized peer-ranking mode has its own short invocation
without duplicating any of qPlan's logic.

When invoked with args `<X>`, immediately call:

    Skill(skill="qPlan", args="critic_provider: council\n<X>")

Do NOT reimplement any council mechanics here -- anonymization, ranking,
aggregation, and chairman synthesis are defined solely in qPlan's SKILL.md,
section "Council mode (anonymized peer ranking)". This skill is a pure
pass-through: its only job is prepending the `critic_provider: council`
config line and forwarding the rest of the user's args to qPlan unchanged.

If the qPlan skill is missing or cannot be invoked, say so plainly and stop
-- do not fall back to any other provider mode.

Kill switch: delete this directory (`~/.claude/skills/council/`). qPlan's
council mode remains fully reachable via a direct `/qPlan` invocation with
`critic_provider: council` in the config block -- removing this alias only
removes the short command, not the capability.
