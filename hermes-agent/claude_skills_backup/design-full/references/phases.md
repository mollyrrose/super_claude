# design-full — phase contract (P0-P8)

This file is the detailed contract for each phase: preconditions, inputs,
outputs, gate rules, and resume behavior. SKILL.md holds the summary; on any
conflict, THIS file wins for phase mechanics.

State file: `<project>/.design-full/state.json`. Synthetic example:

```json
{
  "version": 1,
  "phase": "P4",
  "budget": "standard",
  "project_root": "D:/projects/example-app",
  "intake": {
    "purpose": "teen study-buddy web app",
    "tone": "playful-confident",
    "mobile_scope": "responsive+native",
    "avatars": true,
    "industry": "edtech",
    "constraints": ["mandated logo", "keep green #2FA36B"],
    "axes": {"variance": "high", "motion": "medium", "density": "low"}
  },
  "audit": {"framework": "react", "brandbook_mode": "create"},
  "locked_direction": "B",
  "family_winners": {"shell": "A", "content": "A", "marketing": "C"},
  "gates_done": ["G1"],
  "updated": "2026-07-29T12:00:00Z"
}
```

Dates are ISO-8601 UTC. Write state after every phase transition and every
gate result. Resume rule: on invocation, read state.json; if `phase` exists,
summarize where the run stands in 2-3 sentences and continue from there.
Subcommand jumping ahead of `phase`: warn, list what is missing, use what
exists (do not silently re-run completed phases).

---

## P0 INTAKE

- Precondition: none.
- Do: ask the merged intake questions (`intake-questions.md`) via
  AskUserQuestion (batch to max 4 per call). Propose calibration-axis values
  (`calibration.md`) from the answers; user confirms.
- Output: `state.json` intake block.
- Gate: user answered. No deliverable files yet.

## P1 AUDIT

- Precondition: target root known (cwd or --project).
- Do:
  1. `python <skill>/scripts/inventory_scan.py <root>` -> save to
     `.design-full/scans/inventory.json`.
  2. `python <skill>/scripts/token_extract.py <style files...>` -> save to
     `.design-full/scans/tokens.json`.
  3. `python <skill>/scripts/wcag_check.py .design-full/scans/tokens.json`
     -> contrast findings.
  4. Read TODO/roadmap files from the inventory's `planning_files` list; read
     the main screens' code (entry routes/pages). Build the surface table:
     `| surface | exists? | roadmap source | design need |`.
  5. Brand-book detection order: `docs/design/BRANDBOOK.md`, root `BRAND*.md`,
     `docs/design/DESIGN.md`, `brand/` dir. Found -> `brandbook_mode:
     "update"` else `"create"`.
- Output: `docs/design/AUDIT.md` with sections: Inventory, De-facto tokens,
  Contrast findings, Existing surfaces, Planned surfaces (from
  TODO/roadmap), Framework + component stack, Brand-book status.
- Gate (U): user confirms/edits the in-scope surface list. Record scope in
  state.json.

## P2 BRAND FOUNDATION

- Precondition: P1 scope confirmed.
- Do: build 3 brand boards (A/B/C) as self-contained one-page HTML in
  `.design-full/variants/brand/`. Each board: brand thesis (1 paragraph),
  font pairing with rationale, OKLCH palette (5-7 swatches incl. semantic
  roles), imagery/illustration tone, one signature element (the memorable
  thing), axis setting. Force variant separation: pick 3 DIFFERENT entries
  from the aesthetic-extremes list consistent with intake tone. In
  brandbook_mode=update: A = faithful evolution, B = moderate refresh, C =
  bold rework; each states what it keeps from the existing book.
- Gate (G1): comparative focus gate per `focus-gate.md` (panel-lite at
  standard budget; `--youth-boost` if avatars in scope). Present crosstab
  table + per-variant "who liked it and why" characterization. Then the user
  LOCKS a direction (may specify borrowings, e.g. "B but with A's palette").
- Output: 3 boards, `.design-full/panels/G1/` transcripts,
  G1 section appended to `docs/design/AUDIT.md` or a new
  `docs/design/proposals/web/brand-gate.md`; `locked_direction` in state.

## P3 DESIGN SYSTEM

- Precondition: locked_direction set.
- Do: author `docs/design/DESIGN.md` (route: hermes-design-md skill;
  fallback: write the YAML+markdown spec manually following that skill's
  format). Tokens: color (OKLCH + hex fallback), type scale, spacing scale,
  radii, shadows, motion durations/easings, breakpoints
  (375/768/1024/1440). Run wcag_check on the final palette. If audit found
  Tailwind: also emit `docs/design/tokens.tailwind.json`; if a token
  pipeline exists: DTCG `docs/design/tokens.json`.
  Then produce 3 density expressions (compact/regular/roomy) as one-page
  HTML specimens in `.design-full/variants/system/` (same tokens, different
  scale/density values).
- Gate (U): review specimens via show-gallery (fallback: list file paths for
  manual open). User picks density. No persona panel.
- Output: DESIGN.md (+ exports), density choice in state, BRANDBOOK draft via
  `python <skill>/scripts/brandbook_assemble.py <project>/.design-full`.

## P4 SCREEN PROPOSALS (web)

- Precondition: DESIGN.md exists.
- Do: group in-scope surfaces into <=4 families. Per family, 3 full HTML
  mockups in `docs/design/proposals/web/<family>/variant-{a,b,c}.html`
  applying DESIGN.md tokens (inline as CSS custom properties). Apply
  scroll/motion treatments per `scroll-motion.md` where intake asked for it.
  Before showing: `python <skill>/scripts/antipattern_lint.py
  docs/design/proposals/web/` and fix all findings (re-run until clean or
  justify remaining as JUDGMENT-rule exceptions).
- Gate (G2): ONE comparative panel-lite run covering all families; crosstab
  per family; user picks per family. Record `family_winners`.
- Output: linted variants, `.design-full/panels/G2/`, gate report in
  `docs/design/proposals/web/screen-gate.md`.

## P5 MOBILE

- Precondition: family_winners set; skip only if intake mobile_scope is
  "none" (web desktop only — rare; confirm before skipping).
- Do (responsive track, always when scope includes web): 375px versions of
  each winning family mockup in `docs/design/proposals/mobile/web-375/`;
  follow `mobile-patterns.md` (touch targets >=44px, thumb zones, nav
  collapse rules).
  Do (native track, when scope includes native app): app-screen mockups at
  390x844 viewport in `docs/design/proposals/mobile/app/` using
  platform-correct chrome (HIG or Material per intake target platform), and
  `docs/design/proposals/mobile/token-mapping.md` (CSS var -> Flutter
  ThemeData / RN StyleSheet token table).
  Produce 3 variants of the NAVIGATION/layout approach only (e.g. A tab bar,
  B drawer, C gesture-first) — not 3x every screen.
- Gate (U): review; the nav choice is also included in G3's brief.
- Output: mobile proposals + nav choice preliminarily in state.

## P6 CUSTOMIZATION

- Precondition: DESIGN.md exists (can run parallel to P5).
- Do:
  1. Avatars: 3 style sets (e.g. flat-geometric, hand-drawn, pixel/retro —
     pick styles fitting the locked direction) x 4-6 sample avatars each, as
     SVG (preferred) or PNG in `docs/design/proposals/avatars/<style>/`.
     Spec in `customization.md`. Youth-oriented: expressive, customizable
     parts (hair/color/accessory params documented per set). Optional video
     avatars via heygen skill if HEYGEN_API_KEY present and user opts in.
  2. Effects registry: write `docs/design/design-config.json` per the schema
     in `customization.md` — theme modes, density, accent, avatar set, and
     optional effects (peel-menu, droplets, scroll-narrative, ...), each
     with `enabled`, `fallback`, `reduced_motion_behavior`.
  3. Design tab: `python <skill>/scripts/design_tab_scaffold.py
     --framework <detected> --config docs/design/design-config.json`
     -> `docs/design/proposals/design-tab/` (component + apply helper +
     WIRING.md). Never write into src/.
- Gate (U): quick review; avatar style choice + effect defaults go into G3.
- Output: avatar sets, design-config.json, design-tab scaffold.

## P7 FINAL GATE (G3)

- Precondition: P2-P6 outputs exist (whatever subset the run covered).
- Do: assemble the package brief (locked brand + density + family winners +
  mobile nav options + avatar styles + effect defaults + remaining open
  choices as explicit A/B/C questions). Budget standard: invoke the
  `/focus-group` SKILL once with the comparative brief (template in
  `focus-gate.md`). Budget lite: panel-lite instead. Budget max: full 215
  comparative. Save transcripts to `.design-full/panels/G3/`; run crosstab.
- Output: `docs/design/FOCUS-REPORT.md` — crosstab tables, per-segment
  narratives, resolved open choices, dissent worth noting (segments that
  disliked the winner and what would win them back).
- Gate: user signs off on final choices.

## P8 HANDOFF

- Precondition: G3 done (or user explicitly skipped it).
- Do: finalize BRANDBOOK.md (assemble script; update-mode diff section),
  DESIGN.md, and write `docs/design/DESIGN-PLAN.md` from
  `design-plan-template.md`: phased implementation roadmap, each item
  mapping proposal -> concrete target files (from the audit inventory) ->
  size estimate -> dependency order -> which roadmap/TODO feature it serves.
- `apply` subcommand: print the exact `/qGoal` invocation (goal = implement
  DESIGN-PLAN.md phase 1..N, check = antipattern_lint clean + visual parity
  with proposals), ask explicit confirmation, then invoke. design-full
  itself never edits styles.
- Output: final deliverable set; state.phase = "DONE".
