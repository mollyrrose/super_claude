# design-full — intake question set (P0)

Merged from the local `design` skill's direction-lock questions and the
official frontend-design plugin's 4-question framework; deduplicated. Ask via
AskUserQuestion, max 4 per call, in the user's language. Skip any question
the user's prompt already answered — restate the inferred answer for
confirmation instead.

## Q1 Purpose
What is this product/page for, and what is the ONE action a visitor should
take? (frontend-design: purpose)

## Q2 Audience
Who uses it — age range, tech comfort, context of use (desk/commute/school)?
If "young users" comes up, note it: it triggers `--youth-boost` panels and
the avatar track default.

## Q3 Tone
Three adjectives for how it should FEEL (e.g. playful-confident-warm vs
precise-calm-premium). (frontend-design: tone)

## Q4 References
2-3 products/sites whose look the user admires (and one they dislike). Used
to seed the aesthetic-extreme picks — NOT to copy.

## Q5 Constraints
Hard constraints: existing logo, mandated colors, fonts already licensed,
accessibility level (default WCAG AA), performance ceilings, browser/device
floor. (frontend-design: constraints)

## Q6 Differentiation
What should make it feel DIFFERENT from the obvious competitors? One real
aesthetic risk the user is willing to take. (frontend-design:
differentiation + official "one justified risk" rule)

## Q7 Mobile scope
web-only / responsive web / native app (which platform: iOS, Android, both,
Flutter/RN cross-platform) / responsive+native. Drives P5 tracks.

## Q8 Customization scope
- Avatars wanted? For whom (young users default)? Video avatars OK (needs
  HEYGEN_API_KEY)?
- Optional effects appetite: none / subtle / playful (peel menu, droplets,
  scroll-narrative)?
- Should a settings Design tab be generated (theme, density, accent, avatar,
  effect toggles)?

## After the answers

Propose calibration-axis values (calibration.md): DESIGN_VARIANCE,
MOTION_INTENSITY, VISUAL_DENSITY — each low/medium/high with a one-line
justification from the answers. User confirms or adjusts. Record everything
in state.json intake block.
