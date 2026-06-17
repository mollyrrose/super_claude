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
qPlan skill at `qPlan/references/auto-mode.md` and is reached via `/qPlan auto`.
That fusion layer is ours; the engine underneath is Arbor.

To update the engine: re-clone RUC-NLPIR/Arbor and re-copy its `skills/arbor-*`
dirs over these, then re-read `qPlan/references/auto-mode.md` to confirm the
house-rules still map onto the upstream phase names.
