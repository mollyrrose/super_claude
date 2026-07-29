# design-full — inspiration sources (no-scraping policy)

HARD RULE: never scrape or bulk-fetch 21st.dev, behance.net, dribbble.com,
awwwards.com, canvasui.dev (ToS + fragility). Use: (a) the curated
heuristics below, (b) parameterized search links handed to the USER to open,
(c) the user pastes/screenshots what they like and the pipeline reacts.

## Curated trend heuristics (encoded, refresh occasionally by hand)

What award-winning 2025-2026 work tends to share:
- Generous whitespace even in dense designs; hierarchy from size contrast
  (not weight alone).
- Distinctive display face + workhorse text face pairing; variable fonts
  for weight animation.
- One signature interaction per page, executed perfectly, instead of many
  mediocre ones.
- Purposeful micro-interactions on state change; ambient motion only as
  background texture.
- Color: restrained base palette + one saturated accent doing the work;
  OKLCH-consistent lightness ramps.
- Photography/illustration committed to ONE treatment (duotone, grain,
  hand-drawn) — not mixed.
- Scroll-driven storytelling on marketing pages; app UIs stay still.

## Search links to hand the user (fill the <terms>)

- 21st.dev components: https://21st.dev/?q=<terms> (shadcn-registry format
  components; per-item licenses — check before adopting any single one)
- Dribbble: https://dribbble.com/search/<terms>
- Behance: https://www.behance.net/search/projects?search=<terms>
- Awwwards: https://www.awwwards.com/websites/<category>/
- CanvasUI catalog: https://canvasui.dev/components (peel:
  /docs/components/peel, droplets: /docs/components/droplets)

Suggested term seeds per aesthetic extreme: e.g. neo-brutalist -> "brutalist
web", editorial-magazine -> "editorial layout web", playful-toylike ->
"playful ui kids app". Give the user 2-3 concrete links per variant during
P2 so they can calibrate taste with real examples.

## How inspiration enters the pipeline

- P2 boards may cite references BY NAME + link ("type treatment inspired by
  <site>") — cite, never copy assets.
- If the user pastes a screenshot they like: run the design skill's
  screenshot-reaction flow, extract the liked qualities into the board's
  rationale.
- Component sourcing (21st.dev / shadcn ecosystems) is an IMPLEMENTATION
  concern: note candidate components in DESIGN-PLAN.md items; adoption
  happens in /qGoal with per-component license check.
