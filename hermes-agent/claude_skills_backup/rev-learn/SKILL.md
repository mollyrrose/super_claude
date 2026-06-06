---
name: rev-learn
description: Self-learning loop over /rev + Semgrep findings + CodeRabbit/Cursor Bugbot PR threads. Determines which past findings were ACCEPTED via follow-up commits, clusters by rule, promotes patterns seen ≥3 times into candidate Semgrep rules (disabled by default) or CODING_STANDARDS.md style notes. Risky promotions (blocking rules, non-negotiable edits, rule removals, self-modification) are stage-only in RULE_UPDATES.md — never auto-applied. Runs as user-typed /rev-learn (foreground) or spawned by the SessionEnd hook (headless, acceptEdits). Reads CLAUDE_REV_LEARN_REPOS env var when invoked headless; otherwise scans cwd.
---

# /rev-learn — Self-learning from review feedback

The learning half of the `/rev` system. `/rev` produces findings; `/rev-learn` turns accepted-fix patterns into rules. Conservative by design — promotes nothing on its own that could break a build or change a non-negotiable.

## Invocation context

Two modes — same skill body, same logic, slightly different gates:

| Mode | How invoked | Permission mode | Repo discovery |
|---|---|---|---|
| **Foreground** | User types `/rev-learn` (or `/rev-learn <repo>`) | Whatever the foreground session has | Argument OR `cwd` |
| **Headless** | `~/.claude/scripts/rev_learn_sessionend.py` spawns it on SessionEnd | `acceptEdits` (set by the spawn) | `CLAUDE_REV_LEARN_REPOS` env var (semicolon-separated) |

Detection at runtime: `if os.environ.get("CLAUDE_REV_LEARN_SUBSESSION") == "1"` → headless mode.

In both modes, the routing decision (auto-apply vs stage-only) is **identical** — `acceptEdits` does NOT relax the safety gates. The gates are inside this skill's logic, not the permission system.

## Configuration

`~/.claude/.rev_learn_config.json` (defaults shown):

```json
{
  "min_occurrences": 3,
  "max_auto_per_drain": 5,
  "overfit_threshold": 0.25,
  "low_trust_source_threshold": 0.30,
  "pr_bot_authors": ["coderabbitai", "cursor-bugbot"],
  "lock_stale_minutes": 30
}
```

State persists in `~/.claude/.rev_learn_state.json`:

```json
{"last_run": "<iso8601>",
 "sources": {"<source>": {"accepted": N, "total": N, "rate": float}}}
```

## Step-by-step procedure

### 1. Collect

For each repo in scope (foreground: `cwd`; headless: parse `CLAUDE_REV_LEARN_REPOS`):

a. Read `<repo>/.claude/review-log/findings.jsonl`. Each line is one finding with the shape produced by `/rev` Phase A and `semgrep_postedit_hook.py`:
```json
{"ts": "...", "source": "rev|semgrep|semgrep-postedit|rev-standards",
 "rule": "...", "file": "...", "line": N,
 "severity": "blocking|warning|nit", "message": "...",
 "status": "open|accepted|dismissed", "fix_commit": null}
```

b. If the repo has a GitHub remote and `gh` is authenticated, pull PR review threads:
```bash
gh pr list --state all --search "review-requested:@me" --json number
# for each PR:
gh api repos/<owner>/<repo>/pulls/<num>/comments --paginate \
  --jq '.[] | select(.user.login | test("coderabbitai|cursor-bugbot")) | {id, path, line, body, in_reply_to_id, original_commit_id, side}'
gh api repos/<owner>/<repo>/pulls/<num>/reviews --paginate \
  --jq '.[] | select(.user.login | test("coderabbitai|cursor-bugbot"))'
```
Append each external finding to `findings.jsonl` with `source: "coderabbitai"` or `"cursor-bugbot"` if not already present (dedupe by `<source>:<file>:<line>:<rule>`).

### 2. Determine disposition

For each finding with `status: open`:

- Check if any commit AFTER the finding's `ts` modified the offending `file:line`:
  - `git log --since="<ts>" --pretty=format:%H -- <file>` → list candidate commits
  - For each, `git diff <commit>^ <commit> -- <file>` → check if the offending line range changed
- **ACCEPTED** if a fix-commit changed the line AND the file no longer triggers the rule (re-run Semgrep on the post-commit file for `semgrep` source; LLM-check the change semantically for `rev`/`rev-standards` sources)
- **DISMISSED** if (a) PR review thread for this finding was resolved without a code change, OR (b) the finding has been re-emitted by Semgrep >= 5 times across runs and never fixed (signal of "user actively ignores this rule")
- **OPEN** otherwise — ignore for this round's learning

Update findings.jsonl in place: set `status` and `fix_commit`.

### 3. Cluster + threshold

Group ACCEPTED findings by `rule`. For each rule with `count >= min_occurrences` (default 3):

- Read 5 most recent ACCEPTED instances. Inspect each `(file, line, fix_commit)` for the **shape** of the fix (rename? early return? input validation added? assertion added? guard clause? type change?).
- If the shape is consistent across instances → "promotion candidate".
- If shapes diverge → not promotable; log as "heterogeneous accepts, no rule" in this round's RULE_UPDATES.md.

Per-source acceptance rate update:
```
sources[source].total = count of findings from this source ever
sources[source].accepted = count where status == "accepted"
sources[source].rate = accepted / total
```
Findings from a source with `rate < low_trust_source_threshold` (default 0.30) are **excluded from clustering** (low-trust = noisy).

### 4. Routing decision (the load-bearing table)

| Promotion class | Foreground | Headless (acceptEdits) | Where it goes |
|---|---|---|---|
| Style note (qualitative pattern) | Auto-apply | Auto-apply | `<repo>/CODING_STANDARDS.md` **"Style notes"** appendix |
| Non-blocking custom rule (deterministic + low-confidence) | Auto-apply as **`enabled: false`** | Auto-apply as **`enabled: false`** | `<repo>/.semgrep/custom/<rule>.yaml` + `<rule>.test.<ext>` |
| **Blocking** custom rule (deterministic + high-confidence) | Stage-only | Stage-only | `<repo>/.claude/RULE_UPDATES.md` (sample YAML + tests inline) |
| Edit to "Non-negotiable rules" section of CODING_STANDARDS.md | Stage-only | Stage-only | `<repo>/.claude/RULE_UPDATES.md` |
| Rule removal / weakening | Stage-only | Stage-only | `<repo>/.claude/RULE_UPDATES.md` (existing rule quoted in full) |
| Edit to `~/.claude/skills/rev/SKILL.md` | Stage-only | Stage-only | `<repo>/.claude/RULE_UPDATES.md` |
| Edit to `~/.claude/skills/rev-learn/SKILL.md` (self-mod) | Stage-only with `[SELF-MODIFICATION]` header | Stage-only with `[SELF-MODIFICATION]` header | `<repo>/.claude/RULE_UPDATES.md` |
| Auto-memory addition ("how I learn" only) | Auto-apply | Auto-apply | `~/.claude/MEMORY.md` (feedback type, only process insights — NEVER code rules) |

### 5. Auto-apply caps + dedupe

- Hard cap: `max_auto_per_drain` (default 5) auto-applies per run total across all classes. Excess promotions become stage-only.
- Dedupe before applying:
  - For custom rule: load `<repo>/.semgrep/*.yaml` and `<repo>/.semgrep/custom/*.yaml`, reject if any rule has same `id` OR same `pattern` OR `message` cosine-similarity > 0.85 against an existing one.
  - For style note: load `<repo>/CODING_STANDARDS.md`, reject if appended line is substring-equal or fuzzy-equal (cosine > 0.85) to any existing line.
  - For auto-memory: load `~/.claude/MEMORY.md` index and the candidate's target memory file, reject if duplicate.

### 6. Overfit guard

After applying any new candidate rule (auto or stage), record `metadata.overfit_marker: pending` in the rule's YAML. On the NEXT `/rev` Phase A run in the same repo:

- Phase A reports per-rule fire-count and fire-files. The learner reads that report on its next run.
- If the new rule fired on >`overfit_threshold` (default 25%) of files OUTSIDE the original evidence cluster's directory:
  - Set `metadata.overfit_marker: possible-overfit`
  - Set `metadata.enabled: false`
  - Append to RULE_UPDATES.md: `[OVERFIT] <rule-id> fired on N/M unrelated files; disabled pending review`

### 7. Mark drained + report

Append to `<repo>/.claude/RULE_UPDATES.md`:

```markdown
## /rev-learn run — <iso8601> (<foreground|headless>)

- Findings scanned: N (rev: a, semgrep: b, semgrep-postedit: c, coderabbitai: d, cursor-bugbot: e)
- Dispositioned: ACCEPTED x, DISMISSED y, OPEN z
- Promoted clusters: k (above threshold of <min_occurrences>)
- Auto-applied: s style notes, t disabled candidate rules, u memory entries
- Staged for approval: v (see entries below)
- Source acceptance: rev a.aa / semgrep b.bb / coderabbitai c.cc / cursor-bugbot d.dd
- Overfit-flagged (disabled): w rules

### Staged proposals (require user review)
[per-promotion blocks]
```

Append a one-line summary to `<repo>/.claude/review-log/learn.log`:
```
[<iso8601>] drained N session(s), s/t/u auto, v staged, source rates ...
```

Update `~/.claude/.rev_learn_state.json` with new acceptance rates and `last_run` timestamp.

## Output contract (foreground only)

After the run, print to the user:

```
/rev-learn — <repo>, <N> findings, <M> promotions

  Auto-applied (low-risk):
    - [style] <CODING_STANDARDS.md appendix line>
    - [candidate-rule] <rule-id> (disabled; review .semgrep/custom/<id>.yaml)
    ...
  Staged for approval (see <repo>/.claude/RULE_UPDATES.md):
    - [blocking-rule] <rule-id> from <N> accepted instances
    - [non-negotiable-edit] <proposed text>
    ...
  Overfit-disabled: <count>
  Source acceptance: rev <r>, semgrep <s>, coderabbitai <cr>, cursor-bugbot <cb>

  Next: review staged proposals in RULE_UPDATES.md before next /rev.
```

In headless mode, no console output — everything goes to `learn.log` and `RULE_UPDATES.md`.

## What NOT to do

- **Don't** auto-apply edits to `.semgrep.yml` (the main rule file). All learner additions go into `.semgrep/custom/<id>.yaml`, never into the root file. Keeps the root file user-owned.
- **Don't** auto-apply edits to `CLAUDE.md` (per-repo). If a process insight belongs in CLAUDE.md, stage it in RULE_UPDATES.md.
- **Don't** auto-modify `~/.claude/CLAUDE.md` (global) under any circumstance — the global CLAUDE.md belongs to the user alone.
- **Don't** edit `findings.jsonl` entries' raw payload (file, line, message, ts). Only the `status` and `fix_commit` fields are mutable.
- **Don't** delete custom rules. Disable via `enabled: false` and move on; manual deletion is a user-driven step.
- **Don't** scan repos other than those passed in `CLAUDE_REV_LEARN_REPOS` or the current cwd. No cross-repo crawl.
- **Don't** invoke `/rev` from inside `/rev-learn`. They're separate operations. Reading findings.jsonl is allowed; triggering a new scan is not.
- **Don't** retry on partial failure. If GH API is down, skip external sources, log "external sources unavailable this round", and continue with local findings only.
- **Don't** apply ANY promotion that originated from a source whose acceptance rate is below `low_trust_source_threshold`. The whole cluster is excluded silently and logged in RULE_UPDATES.md as "low-trust source <name>, N clusters excluded".

## Self-modification — special rules

If the learner concludes its own SKILL.md needs an edit (e.g. heuristic refinement, new disposition rule, threshold tweak):

1. **Never auto-apply.** Even in foreground.
2. Stage in RULE_UPDATES.md with a `## [SELF-MODIFICATION] Proposed change to ~/.claude/skills/rev-learn/SKILL.md` header.
3. Include the proposed unified diff in a fenced block.
4. Include the evidence (which findings, which sessions, which clusters drove the proposal).
5. End the entry with: `Apply only after manual review. Self-modification under acceptEdits is the highest-risk path — your foreground approval is the safety boundary.`

## Failure modes / recovery

| Symptom | Cause | Recovery |
|---|---|---|
| `findings.jsonl` missing or empty | Repo never ran /rev or had findings | Exit 0 silently. Log "no findings to learn from" in `learn.log`. |
| `gh` not authenticated | External-source pull fails | Skip external sources for this round. Log it. Continue. |
| `gh` returns rate-limit | API quota exhausted | Skip external. Log. Schedule retry on next run. |
| Promotion would exceed cap | More than `max_auto_per_drain` candidates | Auto-apply first N, stage the rest. Note both in RULE_UPDATES.md. |
| Custom rule writes succeed but Semgrep can't parse | Generated YAML invalid | Move the .yaml to `.semgrep/custom/_quarantine/`, log error to RULE_UPDATES.md, do NOT count toward cap (re-promote next round only if user fixes). |
| Lock file ~/.claude/.rev_learn_lock exists and headless was just spawned | Concurrent run | Exit 0 immediately (handled by `rev_learn_sessionend.py` before we ever get here). |
| `min_occurrences` set too low | Spammy promotions | Caps + dedupe + overfit guard catch most of it. If user complains, raise `min_occurrences` in `.rev_learn_config.json`. |
| Multiple repos in `CLAUDE_REV_LEARN_REPOS` | Headless was passed > 1 | Process each independently; concatenate per-repo summaries into a single `learn.log` write at end. |

## Related

- `/rev` Phase A produces the findings this skill consumes.
- `/rev` Phase B (multi-agent fleet) writes its findings to the same `findings.jsonl` with `source: "rev"`.
- `~/.claude/scripts/rev_learn_sessionend.py` is the SessionEnd wrapper that headless-invokes this skill.
- `<repo>/.claude/RULE_UPDATES.md` is the staging file — read it before each `/rev` to know what's pending your approval.
- `<repo>/.semgrep/custom/` is where promoted candidate rules live; flip `metadata.enabled: true` to activate.
