# Decision log — super_claude

Newest entry on top. One short ADR-style entry per non-trivial / hard-to-reverse
decision. See `~/.claude/CLAUDE.md` "Decision log" for the format.

### 2026-06-17 - Adopt Arbor as the engine behind /qPlan auto
Decision: Vendor the full RUC-NLPIR/Arbor skill suite (11 `arbor-*` skills,
Apache-2.0) verbatim as the autonomous-optimization engine, and reach it through
a new `/qPlan auto` mode whose fusion layer (`qPlan/references/auto-mode.md`)
applies our conventions: model tiering + GLM caveat, `.worktrees/` convention,
B_dev/B_test held-out discipline, decision-log on merges/prunes, qPlan-style
progress-based termination, context-budget/resume handling, no-decorative-unicode,
and safety gates.
Why: Arbor's measured wins are mostly the iterative loop (Idea Tree, held-out
split, worktree-isolated experiments), not the base model — and that loop is
genuinely useful for metric-driven optimization we can't get from interactive
qPlan. Keeping the engine unmodified makes it updatable from upstream; putting
our knowledge in a separate fusion layer makes the combination smarter without
forking their content.
Rejected alternatives: (a) penso/arbor desktop app — rejected: it runs its own
agent loop instead of the Claude Code CLI, so our hooks/skills/statusline/curator
would not apply (replaces, not complements). (b) Cherry-pick 1-2 arbor skills —
rejected: the suite is a coupled pipeline (entrypoint -> orchestrator -> phases),
not standalone utilities. (c) Re-implement the loop ourselves inside qPlan —
rejected: more work, loses upstream updates.
Revisit if: Arbor's self-reported benchmark (arxiv 2606.11926) turns out to use
an unfair iteration/compute budget vs the Claude Code baseline; OR the 11 extra
skills cause real index/routing clutter; OR penso/arbor gains a "Claude Code CLI
as backend" mode (then reconsider it as the front-end).
