# Arbor skill suite — vendored, third-party

The 11 `arbor-*` skill directories in this folder
(`arbor-research-agent`, `arbor-agent-orchestrator`, `arbor-agent-coordinator`,
`arbor-agent-ideate`, `arbor-agent-executor`, `arbor-agent-merge-eval`,
`arbor-agent-search`, `arbor-agent-setup-intake`, `arbor-agent-plugins-hitl-budget`,
`arbor-agent-resume-report`, `arbor-agent-tools`) are vendored verbatim from:

  RUC-NLPIR/Arbor  -  https://github.com/RUC-NLPIR/Arbor
  License: Apache License 2.0 (see ARBOR_LICENSE.txt)

They are the unmodified Arbor "open-source AutoResearch" engine. We do NOT edit
their content in place — that keeps them updatable from upstream.

Our augmentation layer (model tiering, GLM caveat, `.worktrees/` convention,
decision-log, materiality/termination fusion, held-out discipline, context-budget
handling, no-decorative-unicode, safety gates, closeout) lives separately in the
qGoal skill at `qGoal/references/engine.md` and is reached via `/qGoal` (which
drives this engine only when a task warrants multiple variants). That fusion
layer is ours; the engine underneath is Arbor. (Historical note: this used to be
reached via `/qPlan auto`, now retired — execution moved out of the planner into
`/qGoal`.)

To update the engine: re-clone RUC-NLPIR/Arbor and re-copy its `skills/arbor-*`
dirs over these, then re-read `qGoal/references/engine.md` to confirm the
house-rules still map onto the upstream phase names.
