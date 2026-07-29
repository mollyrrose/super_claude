# design-full — skill routing table (the orchestra)

Rule: for each phase step, INVOKE the primary skill via the Skill tool when it
is installed; use the fallback column when it is not (and note the
substitution in the phase report). Never re-implement a skill's job ad hoc
when the skill is present.

## Local skills (expected installed)

| Phase | Primary skill | Role | Fallback if missing |
|-------|---------------|------|---------------------|
| P0 | design | direction-lock question framework | ask intake-questions.md directly |
| P1 | (scripts only) | inventory, tokens, wcag | manual Glob/Grep survey |
| P2 | hermes-sketch | 2-3 quick HTML variant boards | write boards inline |
| P2 | hermes-claude-design | high-fidelity one-page HTML boards | write boards inline |
| P2 | hermes-popular-web-designs | 54 real design systems as vocabulary/mood refs | inspiration.md heuristics |
| P2/P6 | product-designer | UX research framing, journey notes | condensed UX notes inline |
| P3 | hermes-design-md | DESIGN.md token spec + WCAG lint + Tailwind/DTCG export | author spec manually in same format |
| P4 | shadcn | component library ops (React+Tailwind projects) | plain HTML/CSS components |
| P4 | ecc:frontend-design-direction | aesthetic direction guardrails | calibration.md |
| P4 | ecc:design-system | system consistency review | impeccable-rules.md judgment pass |
| P4/P5 | ecc:accessibility | WCAG audit of proposals | wcag_check.py + manual checklist |
| P4 | ecc:make-interfaces-feel-better | micro-interaction polish pass | scroll-motion.md basics |
| P4 | ecc:motion-foundations / -patterns / -advanced / -ui | motion design per intensity axis | scroll-motion.md basics |
| P4 | ecc:liquid-glass-design | glass aesthetic (only if direction calls for it) | skip |
| P4 (assets) | hermes-p5js | generative backgrounds/art | static SVG patterns |
| P4 (assets) | hermes-baoyu-infographic | data-heavy sections | chart-visualization |
| P4 (assets) | chart-visualization | charts in mockups | inline SVG charts |
| P4 (marketing) | animated-website | video-scroll landing treatment | scroll-motion.md CSS-only |
| P6 | hermes-pixel-art | pixel/retro avatar style set | inline SVG avatars |
| P6 | heygen | video avatars (/v3/avatars) + HyperFrames HTML->MP4 (/v3/hyperframes/renders); needs HEYGEN_API_KEY | static avatars only; note "available with key" |
| P3/P4 gates | show-gallery | browse variant files for U-gates | list file paths to open manually |
| G1-G3 | focus-group | full 215-persona comparative run (G3 standard, all gates at max) | panel-lite via panel_sample.py |
| P8 | qGoal | implementation handoff from DESIGN-PLAN.md | hand the plan to the user |
| P8 | qRev | deep review after implementation (qGoal runs it) | - |

## Official Anthropic skills (NOT installed by default — optional routes)

Verified available in github.com/anthropics/skills (2026-07). If the user
wants them, install AFTER a skillspector-gate scan (standing rule), then
route as below. Until installed, use the fallback.

| Phase | Skill | Role | Fallback |
|-------|-------|------|----------|
| P2/P4 assets | canvas-design | museum-quality static art (posters, hero art, PDF/PNG) | hermes-p5js or static SVG |
| P4 assets | algorithmic-art | seeded parametric/generative art (p5.js) | hermes-p5js (near-equivalent, installed) |
| P3 | theme-factory | 10 curated cross-media themes (docs/slides/landing) | DESIGN.md tokens directly |
| P8 extras | pptx | branded presentation deck of the design package | skip (offer BRANDBOOK.html instead) |

## Built-in Claude Code capability

- **DesignSync tool** (`/design-sync`, deferred tool DesignSync): two-way sync
  between Claude Design and the repo — can import an existing design system
  into Claude Design and push built code back. Offer it at P8 as an OPTIONAL
  integration when the user works with Claude Design; never required for the
  pipeline.

## Dispatch etiquette

- Skill calls that generate variants run as parallel subagents where
  independent (3 variants = up to 3 parallel), respecting the A4 cost gate.
- Panel fleets: see focus-gate.md.
- Model tiering per global CLAUDE.md: variant HTML generation = sonnet-tier
  subagents; brand thesis/synthesis and gate synthesis = opus-tier; panel
  personas = sonnet-tier (they are role-play + short verdict).
