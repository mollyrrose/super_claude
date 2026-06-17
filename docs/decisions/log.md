# Decision log — super_claude

Newest entry on top. One short ADR-style entry per non-trivial / hard-to-reverse
decision. See `~/.claude/CLAUDE.md` "Decision log" for the format.

### 2026-06-17 - skillspector pre-download gate + ponytail/improve/drawio skills
Decision: Install NVIDIA skillspector as an always-on pre-download security gate
(scan any GitHub repo/skill before cloning/installing; block on high risk) via a
`skillspector-gate` skill + a global CLAUDE.md rule. Install three reviewed skills
despite CRITICAL scores: ponytail (minimal-code lens) into qMin/qRev/qPlan,
shadcn/improve (audit -> plan-for-cheaper-model) into qRev/qPlan, Agents365-ai
drawio-skill into qUpd (every project keeps exclude/SYSTEM_STRATEGIES/
SYSTEM_STATUS.md + system_map.drawio, kept in sync).
Why: The gate is cheap insurance (research cited: 26% of skills have vulns, 5%
malicious). skillspector flagged all four candidates (incl. already-installed
Arbor) DO_NOT_INSTALL, but line-by-line review showed the scores are inflated by
auxiliary code, inherent agent behavior, and literal false positives (XML
comments, an anti-injection rule, the phrase "flood context"); no real malice in
any runtime path. ponytail/improve directly reinforce existing principles
(minimal scope, tiered execution).
Rejected alternatives: (a) trust scores blindly and skip all four — rejected:
they are false-positive-heavy and the skills are genuinely useful. (b) a hook
instead of a skill for the gate — rejected: a hook can't cleanly intercept "about
to git clone"; a CLAUDE.md rule + skill is the right altitude. (c) vendor whole
repos — rejected: only skill dirs vendored (benchmarks/tests/src excluded), which
also removes most of the scanner noise.
Revisit if: skillspector ships an allowlist/baseline so agent-skill false
positives drop; OR any of these skills later shows real malice on a deeper LLM
scan; OR the override pattern is abused (treat CRITICAL as auto-ignore).
Override-logged in ~/.claude/.skillspector_log.jsonl.

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
