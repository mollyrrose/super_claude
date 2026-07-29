# design-full — Design tab generator (P6 track 3)

## What it is

A generated PROPOSAL for a "Design" tab in the target project's settings UI,
exposing: theme mode, density, accent, avatar set, and optional-effect
toggles — everything declared in docs/design/design-config.json. The user's
end-users get full customization alongside the main design.

## Framework detection

Take `framework.name` from `.design-full/scans/inventory.json`
(inventory_scan.py output). Mapping for the scaffold:

| Detected | --framework arg |
|----------|-----------------|
| react, next, react-native (settings web view) | react |
| vue, nuxt | vue |
| svelte, angular, flutter, plain, unknown | plain (universal vanilla version + a note to port) |

## Invocation

```
python <skill>/scripts/design_tab_scaffold.py --framework react \
  --config docs/design/design-config.json \
  --out docs/design/proposals/design-tab
```

Output files (react): DesignSettings.tsx, applyDesignConfig.ts,
design-config.json (copy), WIRING.md. Vue: DesignSettings.vue,
applyDesignConfig.js. Plain: design-settings.html (standalone demo),
design-settings.js.

## Behavior contract of the generated code

- Applies choices as `data-theme`, `data-density`, `data-effect-<id>`
  attributes on document.documentElement plus `--dg-accent` CSS variable —
  the target's stylesheets react to attributes; the component never injects
  styles into app CSS.
- Persists choices to localStorage key `design-config-choices`.
- `prefers-reduced-motion: reduce` force-disables every effect whose
  `reduced_motion_behavior` is "disable", overriding the stored toggle.
- Avatar picker only renders when `avatars.enabled` is true.

## Review checklist for the proposal

- Open the plain demo page in a browser: every control changes the demo
  surface live.
- Keyboard: all controls reachable and operable, visible focus.
- The WIRING.md names the real settings-page file (from the audit) where the
  component would mount — integration itself is /qGoal Phase 4 work.
