# design-full — attribution

No external code is vendored in this skill. The reference files distill
ideas, rule lists, and workflow patterns from the sources below, rewritten
in this skill's own words. If any actual code is ever vendored, it must
pass /skillspector-gate first (global rule) and be attributed here with its
license text location.

| Source | License | What was distilled | Into |
|--------|---------|--------------------|------|
| github.com/pbakaus/impeccable | Apache-2.0 | anti-pattern rule ideas (60), audit/subcommand decomposition | impeccable-rules.md, SKILL.md subcommands |
| github.com/Leonxlnx/taste-skill | MIT | DESIGN_VARIANCE / MOTION_INTENSITY / VISUAL_DENSITY calibration axes | calibration.md |
| frontend-design@claude-plugins-official (Anthropic) | Apache-2.0 | 4-question framework, aesthetic extremes, banned-fonts anti-slop rule | intake-questions.md, calibration.md |
| github.com/oso95/scroll-world | MIT | scroll-narrative structure (timeline scrub, scene continuity, dwell, dual-orientation, degradation) | scroll-motion.md |
| github.com/wilwaldon/Claude-Code-Frontend-Design-Toolkit | MIT | ecosystem taxonomy idea behind the routing table | orchestra.md |
| github.com/heygen-com/hyperframes + local heygen skill | Apache-2.0 | HTML->deterministic-MP4 rendering as motion-preview option | scroll-motion.md, customization.md |
| github.com/nextlevelbuilder/ui-ux-pro-max-skill | MIT | industry-aware reasoning + pre-delivery checklist ideas | impeccable-rules.md (judgment tier), phases.md checks |
| github.com/szilu/ux-designer-skill | (upstream) | Laws-of-UX grounding, breakpoint checklist, thumb-zone rules | mobile-patterns.md |
| github.com/arvindrk/extract-design-system | (upstream, permissive) | token reverse-engineering workflow idea | token_extract.py concept |
| canvasui.dev (peel, droplets) | UNVERIFIED | linked as optional effects only; nothing vendored | customization.md |
| Apple HIG / Material 3 public docs | - | platform pattern table | mobile-patterns.md |
| Local skills: design, focus-group, hermes-design-md, hermes-sketch, hermes-claude-design, heygen, etc. | first-party | orchestrated, not copied | orchestra.md |
