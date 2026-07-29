# design-full — calibration axes and aesthetic vocabulary

Sources (distilled, see ATTRIBUTION.md): Leonxlnx/taste-skill (MIT) for the
three axes; frontend-design@claude-plugins-official (Apache-2.0) for the
aesthetic-extremes vocabulary and the banned-fonts rule.

## The three axes (set at P0, recorded in state.json)

- **DESIGN_VARIANCE** — how experimental the layout/composition may be.
  low: conventional grids, expected placements. medium: one unconventional
  move per screen. high: asymmetry, overlap, editorial layouts allowed.
- **MOTION_INTENSITY** — animation depth.
  low: opacity/transform micro-transitions only (<200ms). medium: purposeful
  entrances, scroll reveals. high: scroll-narrative, ambient motion,
  signature animated moments.
- **VISUAL_DENSITY** — information per viewport.
  low: generous whitespace, one idea per view. medium: balanced. high:
  dense, data-rich, editorial-compact.

Rule: axes constrain ALL variants; variants differ in AESTHETIC direction,
not by silently moving the axes. If a variant needs an axis exception, it
must say so on its board.

## Variant separation rule (3 versions per phase)

Pick 3 DIFFERENT entries from the extremes list below, each compatible with
the intake tone. Never three flavors of the same extreme. Name the extreme
on each variant board/mockup header.

## Aesthetic extremes vocabulary

brutally-minimal | maximalist-chaos | retro-futuristic | organic-natural |
luxury-refined | playful-toylike | editorial-magazine | neo-brutalist |
art-deco | soft-pastel | industrial-utilitarian | cyberpunk-neon |
warm-analog | swiss-international | hand-crafted-zine | glass-translucent

## Banned defaults (the anti-slop floor)

- Fonts, as PRIMARY face: Inter, Roboto, Arial, Space Grotesk, Open Sans,
  Lato. (System stacks are allowed for UI chrome; the display/brand face
  must be distinctive and justified.)
- The indigo-violet gradient cliche (#6366f1 / #8b5cf6 / #7c3aed family) as
  brand color.
- Bounce easings on UI transitions; `transition: all`.
- Emoji as icons.
- Every choice on a brand board needs a stated reason tied to Q1-Q6 answers;
  "it looks nice" is not a reason.

## Youth-audience modifier (when intake flags young users)

Bias allowed extremes toward playful-toylike, cyberpunk-neon, hand-crafted-
zine, retro-futuristic; MOTION_INTENSITY floor = medium; avatar track on by
default; still keep WCAG AA — youthful is not an accessibility waiver.
