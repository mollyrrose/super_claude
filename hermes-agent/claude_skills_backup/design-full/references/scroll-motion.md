# design-full — scroll and motion patterns (P4/P5)

Sources distilled: oso95/scroll-world (MIT) for scroll-narrative structure;
local ecc:motion-* skills carry the implementation depth — route to them
when installed (orchestra.md). See ATTRIBUTION.md.

## When scroll-narrative applies

Only when intake tone/differentiation asks for immersive/storytelling AND
MOTION_INTENSITY is high. Marketing/landing families are the natural home;
never in app-shell or forms families (AJ51).

## Scroll-narrative pattern (from scroll-world, CSS/JS re-expression)

- Scroll position maps to a TIMELINE, not to page offset: a scrub value
  0..1 per section drives transforms/opacity (vanilla JS,
  IntersectionObserver + rAF; no library dependency in mockups).
- Scene-to-scene continuity: adjacent sections share a visual anchor (a
  color, a shape, the signature element) that transforms across the
  boundary — the "connector clip" idea, done with CSS.
- Dwell points: key messages get a scroll-dwell (section taller than
  viewport; content pinned via position: sticky) so reading is not raced.
- Dual-orientation: design the narrative for portrait AND landscape;
  phone portrait gets shorter scenes and larger anchors.
- Degradation ladder: reduced-motion or low-power -> static stacked
  sections with the same content order; no information may live only in
  motion.

## Motion defaults by MOTION_INTENSITY (used in mockups)

| Axis | Durations | What moves |
|------|-----------|------------|
| low | 120-200ms | opacity/transform micro-feedback only |
| medium | 200-400ms entrances | staggered reveals on scroll-into-view |
| high | up to 700ms signature moments | narrative scenes, ambient layers |

Easing: standard ease-out for entrances, ease-in-out for morphs; never
bounce/back on UI controls (AP06). Everything inside
`@media (prefers-reduced-motion: no-preference)` guards (AP07).

## Route-outs

- ecc:motion-foundations / -patterns / -advanced / -ui: real motion design
  depth per component.
- animated-website skill: video-frame scroll sites (needs a source video).
- HyperFrames (heygen skill, /v3/hyperframes/renders): render an HTML+CSS+JS
  animation to deterministic MP4 — useful to give focus-group panels a
  MOVING preview of a motion-heavy variant instead of a static description.
  Optional, needs HEYGEN_API_KEY.
