---
name: radar-check
description: Compare the current project against the AI Radar bundle and surface high-signal "there is something better / worth learning" flags. Used as the on-demand deep check (/radar-check) and as the strict, kill-switched gate step inside /qRem and /qRev. Honors no-nagging — only strong, superseded/security-grade hits are reported. Invoked via /radar-check [--deep] (case-insensitive).
---

# radar-check — does the radar know something better?

Compares what THIS project uses against the AI Radar knowledge bundle and reports
only high-signal flags. Two modes:

- **Gate mode** (called from `/qRem` and `/qRev`): cheap, strict, at most a couple
  of one-line flags, never interrupts. This is the "speak up" the user asked for.
- **Deep mode** (`/radar-check --deep`, on demand): a fuller pass — read more of
  the project, list every superseded dependency / pattern with the radar's
  recommendation and `resource` link.

Radar bundle (read-only here): `~/.claude/okf/ai-radar/` (live mirror).

## Kill switch (check FIRST)

If `AI_RADAR_DISABLE=1` (or the bundle dir is absent), do NOTHING and emit nothing.
This is the no-nagging guarantee.

## Steps

1. **Kill-switch / availability check.** If disabled or no bundle -> silent exit.
2. **Gather the project's signals** (cheap in gate mode):
   - declared model pins (e.g. `model:` in a `CLAUDE.md` / config),
   - key dependencies (package.json, requirements.txt, pyproject, go.mod, Cargo.toml),
   - obvious patterns named in INDEX/README (RAG, hooks, scanners, frameworks).
3. **Match against radar entries** that have `status: superseded` or a non-empty
   `supersedes`, or a security-grade flag. Only count a match when:
   - the project actually uses the superseded thing (the `supersedes` target), AND
   - the radar entry is `status: current` and backed (not `unverified`), AND
   - the improvement is material (newer flagship, fixed CVE, clearly-better
     approach) — NOT a cosmetic or taste difference.
4. **Emit flags** — gate mode: at most ~2 lines, format:
   `[radar] you use <X>; <Y> is now <better/safer> because <Z> — <resource>`.
   If nothing qualifies, emit nothing (gate) / "radar: no superseded usage found"
   (deep mode only).
5. **Never auto-change anything.** radar-check only reports. Acting on a flag is the
   user's call. (Honors decision-gate + no-nagging.)

## Notes

- Strict threshold is the whole point: a false "you should switch" is worse than a
  missed one, because the user rejected nagging. When unsure, stay silent.
- Deep mode may also surface "worth learning from" entries (a notable new
  technique relevant to the project), clearly labeled as learning, not a defect.
