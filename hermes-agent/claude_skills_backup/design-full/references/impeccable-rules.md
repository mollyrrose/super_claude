# design-full — anti-pattern rules (distilled from pbakaus/impeccable, Apache-2.0)

Two tiers. AUTOMATED rules (AP01-AP35) are enforced by
`scripts/antipattern_lint.py` — run it on every P4/P5 proposal batch and fix
findings before any gate. JUDGMENT rules (AJ36-AJ60) are applied by reading
the proposal with the rule list in hand (route through ecc:design-system /
ecc:make-interfaces-feel-better when installed).

A finding may be waived only with a stated reason in the phase report
("AP32 waived: nav labels are 3-letter caps by design").

## AUTOMATED (checked by antipattern_lint.py, IDs are load-bearing)

- AP01 transition-all: `transition: all` used.
- AP02 no-focus-visible: interactive elements styled, no `:focus-visible`.
- AP03 pure-black: #000 as large surface/body background.
- AP04 pure-white-text-on-black: #fff on #000 body text.
- AP05 tiny-font: font-size below 12px.
- AP06 bounce-easing: overshoot cubic-bezier / bounce/back keywords on UI.
- AP07 no-reduced-motion: animations present, no prefers-reduced-motion.
- AP08 overused-font: Inter/Roboto/Arial/Space Grotesk/Open Sans/Lato as primary face.
- AP09 cliche-indigo: #6366f1/#8b5cf6/#7c3aed brand usage.
- AP10 uniform-radius: one radius value everywhere (>=8 uses, no variation).
- AP11 harsh-shadow: zero-blur or alpha>0.5 box-shadows.
- AP12 tight-body-leading: body line-height under 1.4.
- AP13 unbounded-measure: long text without max-width.
- AP14 low-contrast-gray: #999 or lighter body text.
- AP15 gradient-text-overuse: more than 2 background-clip:text uses.
- AP16 emoji-in-ui: emoji used as UI icons/labels.
- AP17 lorem-ipsum: placeholder copy left in.
- AP18 missing-viewport-meta: HTML without viewport meta.
- AP19 no-hover: buttons styled with zero :hover states.
- AP20 no-active-focus: zero :active AND zero :focus styles.
- AP21 fixed-width-container: fixed px width >=600 without max-width.
- AP22 img-no-alt: images without alt.
- AP23 heading-skip: h1 -> h3 with no h2.
- AP24 multiple-h1: more than one h1.
- AP25 slow-animation: 1-10s non-ambient durations.
- AP26 too-many-infinite: more than 5 infinite animations.
- AP27 extreme-z: z-index above 1000.
- AP28 important-overuse: more than 5 !important.
- AP29 inline-style-overuse: more than 10 style= attributes.
- AP30 nested-cards: card-in-card hierarchy.
- AP31 bad-letterspacing: negative tracking on body / loose tracking on lowercase.
- AP32 long-all-caps: uppercase transform on long text.
- AP33 tiny-touch-target: explicit button height under 32px.
- AP34 color-explosion: more than 12 distinct non-gray colors.
- AP35 font-count: more than 3 font families.

## JUDGMENT (human/LLM review pass)

- AJ36 gray-on-color: gray text sitting on a colored surface.
- AJ37 hierarchy-flat: no clear primary element per view; everything shouts.
- AJ38 alignment-drift: elements 1-4px off a shared grid line.
- AJ39 spacing-arrhythmia: spacing values outside the DESIGN.md scale.
- AJ40 orphan-widow: headings/paragraphs breaking to single-word lines.
- AJ41 fake-depth: shadows implying inconsistent light sources.
- AJ42 icon-style-mix: outline and filled icon styles mixed.
- AJ43 border-and-shadow: both border and shadow doing the same separation job.
- AJ44 centered-long-text: center-aligned multi-line body copy.
- AJ45 cta-competition: two equally-weighted primary CTAs in one view.
- AJ46 empty-state-neglect: lists/dashboards with no designed empty state.
- AJ47 loading-state-neglect: async content with no skeleton/spinner design.
- AJ48 error-state-neglect: forms with no visible error treatment.
- AJ49 dark-mode-afterthought: dark theme = naive color inversion.
- AJ50 motion-without-meaning: animation that communicates nothing.
- AJ51 novelty-over-usability: signature effect obstructs a core task.
- AJ52 density-mismatch: view density contradicts the VISUAL_DENSITY axis.
- AJ53 tone-drift: copy/visuals contradict the intake tone adjectives.
- AJ54 inconsistent-corners: mixed radius language without system.
- AJ55 stock-photo-smell: generic imagery clashing with the brand direction.
- AJ56 breakpoint-cliff: layout that breaks awkwardly between breakpoints.
- AJ57 thumb-hostile: key mobile actions outside the thumb zone.
- AJ58 contrast-theater: passes WCAG numerically but reads muddy in situ.
- AJ59 brand-amnesia: screen could belong to any product (no signature element).
- AJ60 last-2-percent: missing favicons, selection colors, focus rings,
  scrollbar styling — the polish layer that compounds.
