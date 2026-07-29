# design-full — mobile patterns (P5)

Sources distilled: ux-designer-skill (Laws of UX, breakpoint checklist),
Apple HIG and Material 3 public guidance. See ATTRIBUTION.md.

## Responsive web track (always when scope includes web)

Breakpoints (design at all four, mockup at 375 minimum):
375 (phone) / 768 (tablet) / 1024 (laptop) / 1440 (desktop).

Rules:
- Touch targets >= 44x44 px (AP33 guards the floor).
- Thumb zone: primary actions in the bottom half on phone; destructive
  actions OUT of the easy-reach zone (AJ57).
- Navigation collapse: named pattern per project — top nav -> bottom tab bar
  (app-like), hamburger/drawer (content sites), or priority+overflow.
  The 3 P5 variants are three DIFFERENT collapse strategies.
- Typography: body >= 16px on phone (prevents iOS zoom-on-focus); measure
  45-75 chars via max-width.
- Density: one column default at 375; VISUAL_DENSITY=high means tighter
  spacing, not multi-column phone layouts.
- Hover has no phone equivalent: every :hover affordance needs a visible
  static or :active equivalent.
- Motion: respect reduced-motion; scroll-narrative degrades to static
  sections on phone if MOTION_INTENSITY < high.

## Native app track (when scope includes native)

Mockup viewport: 390x844 (modern phone). Platform chrome must be correct:

| Aspect | iOS (HIG) | Android (Material 3) |
|--------|-----------|----------------------|
| Primary nav | bottom tab bar (2-5 tabs) | bottom navigation bar / nav drawer |
| Back | edge-swipe + top-left chevron | system back + top app bar arrow |
| Type | SF Pro (or brand face + SF fallback) | Roboto-free: brand face + system fallback |
| Corner language | continuous curves, grouped lists | M3 shape scale (4/8/12/16/28) |
| Elevation | translucency + subtle shadow | tonal elevation over shadows |

Cross-platform (Flutter/RN): design once on the brand system, note the two
platform adaptation columns per screen (nav placement, back handling,
haptics) instead of duplicating every mockup.

## Token mapping proposal (docs/design/proposals/mobile/token-mapping.md)

Table format:
```
| DESIGN.md token | CSS var | Flutter ThemeData | RN token |
|-----------------|---------|-------------------|----------|
| color.primary   | --dg-primary | colorScheme.primary | colors.primary |
| radius.card     | --dg-radius-card | CardTheme.shape | radii.card |
```
Every DESIGN.md token gets a row; gaps marked TBD are implementation work
for /qGoal, not silent omissions.

## Mobile checks before the gate

- antipattern_lint on the 375 mockups (AP33, AP18 especially).
- Text truncation review at 320px width (small-phone worst case).
- One-hand reachability note per screen (what the thumb cannot reach).
