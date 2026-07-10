# Decision log — super_claude

Newest entry on top. One short ADR-style entry per non-trivial / hard-to-reverse
decision. See `~/.claude/CLAUDE.md` "Decision log" for the format.

### 2026-07-10 - Adopt Crush as a secondary multi-model/LSP tool; Claude Code stays primary
Decision: Install Crush (charmbracelet/crush, via `npm i -g @charmland/crush`) as a
SECONDARY coding tool wired to the local llama.cpp ("Ornith") server by default,
with GLM/Anthropic-API providers dormant. Claude Code remains primary. Also prepped
Claude Code for free-tier Base44 code handoff (base44 CLI + official base44 skills +
documented docs-MCP/login steps).
Why: Crush's real value is multi-model + LSP-as-agent-tools + native Windows, useful
for running tasks on a free local model or GLM. But the pasted "Crush beats Claude"
comparison was mostly fabricated, Crush removed Anthropic OAuth (cannot use the
Claude subscription), and none of the super_claude harness (hooks/coord/q*/statusline)
carries over - so it supplements Claude Code, it cannot replace it.
Rejected alternatives: (a) migrate to Crush as primary - rejected: abandons the whole
hook/skill/coord ecosystem and forces per-token API or local-only. (b) analysis-only,
no install - rejected: user chose a full hands-on trial. (c) paid Base44 Builder
workflow - rejected: user chose the free path.
Revisit if: Crush restores Anthropic subscription auth, OR a GLM key arrives (then
Crush-on-GLM becomes a first-class cheap tier), OR Base44 free-tier limits block the
intended app work (then reconsider Builder).

### 2026-06-17 - Retire /qPlan auto; split brain (qPlan) from hands (qGoal)
Decision: Remove the `/qPlan auto` execution mode and move ALL execution +
optimization into a new standalone `/qGoal` skill. qPlan becomes strictly
plan-only again (the "brain", incl. the OpenAI cross-model panel); qGoal is the
only q-command that touches code (the "hands"). qGoal: plans via qPlan, runs a
single path OR multiple variants as the task warrants (qPlan decides the variant
count at planning time — optimization/competing-approach -> multi; deterministic
build like a webpage -> single), consults qPlan at every decision point (with the
OpenAI lens while `OPENAI_API_KEY` budget lasts, degrading to qPlan-without-OpenAI
otherwise, never aborting), then runs `/qRev` and fixes per its P0/P1 findings
before closeout. The Arbor fusion layer `qPlan/references/auto-mode.md` was deleted
and its content relocated/adapted to `qGoal/references/engine.md`.
Why: A planner executing code was a logical wart — qPlan's own MUST NOT-execute
rule contradicted its `auto` mode. Separating concerns (plan vs do) makes both
cleaner, lets qGoal reuse qPlan's judgment (and OpenAI) at forks, and removes the
"needs a metric" limitation: qGoal also handles metric-less tasks with a runnable
check or a qualitative qPlan/OpenAI verdict.
Rejected alternatives: (a) add a metric-less mode to `/qPlan auto` and keep
execution in qPlan — rejected: keeps the planner-executes wart. (b) make qGoal a
`/qPlan do` sub-mode — rejected: "qPlan" names planning; overloading it further
muddies it. (c) keep `/qPlan auto` alongside qGoal — rejected: two execution
entrypoints, redundant; user chose full removal with a redirect.
Revisit if: a third autonomous mode appears (then factor the shared house rules
out of `qGoal/references/engine.md` into a common reference); OR the qGoal->qPlan
decision-call cost proves too high in practice (then narrow what counts as a
"decision point" / reduce the panel weight for in-loop calls).
Supersedes the "Adopt Arbor as the engine behind /qPlan auto" entry below (the
engine stays; only its entrypoint moved from /qPlan auto to /qGoal).

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
