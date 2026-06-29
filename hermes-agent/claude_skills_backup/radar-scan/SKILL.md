---
name: radar-scan
description: Weekly multi-modal sweep that learns what is new/better in AI into the AI Radar OKF bundle. Searches the web, YouTube (keyword search + transcript), and arXiv across the 5 topics, ALWAYS inspects the real GitHub repo (skillspector-gated) of interesting findings, distills/merges OKF entries, then runs a lint pass (contradictions, stale, orphans, missing links). Invoked via /radar-scan [topic] (case-insensitive).
---

# radar-scan — weekly auto intake + lint for the AI Radar

The AUTO half of the hybrid intake (manual half = `/radar-add`). Runnable by hand
any time, and scheduled weekly (phase 4). Bundle source of truth:
`D:\projects\super_claude\okf\ai-radar\`; live mirror `~/.claude/okf/ai-radar/`.

## Scope

Default: sweep all 5 topics. `/radar-scan <topic>` limits to one of:
`harness | models | knowledge | agent-tooling | devsec-tools`.

## Topics and search seeds

| Topic | Web / YouTube / arXiv seeds |
|-------|------------------------------|
| harness | "Claude Code" new hooks skills MCP, agent harness update, Claude Code release |
| models | new Claude / OpenAI / GPT / Gemini / GLM model release, pricing, context limit |
| knowledge | OKF open knowledge format, RAG vs wiki, knowledge graph for agents, agent memory |
| agent-tooling | autonomous agent framework, multi-agent orchestration, prompting technique |
| devsec-tools | semgrep / linter release, supply-chain scanner, AI code security tool |

(Tune these seeds over time; they are the keyword net.)

## Steps

1. **Multi-modal search per topic** (each angle is blind to the others):
   - **Web:** WebSearch / `deep-research` on the topic seeds, last ~7-14 days.
   - **YouTube (keyword search + transcript):** find recent relevant videos by
     keyword, then read the transcript and distill:
     ```bash
     # search: top N recent videos for a phrase (no download)
     yt-dlp "ytsearch8:<topic seed phrase>" --flat-playlist \
       --print "%(title)s | %(id)s | %(upload_date)s | %(channel)s"
     # transcript for a chosen video id (prefer the hermes helper):
     python "$HOME/.claude/skills/hermes-youtube-content/scripts/fetch_transcript.py" "https://youtube.com/watch?v=<id>"
     # fallback if that fails: yt-dlp auto-subs
     yt-dlp --write-auto-sub --sub-lang en --skip-download --sub-format vtt -o "%(id)s" "https://youtube.com/watch?v=<id>"
     ```
     Pick only videos whose title/channel actually match the topic; ignore the rest.
   - **arXiv:** for `knowledge` / `agent-tooling`, use the `hermes-arxiv` skill.
   - `hermes-blogwatcher` / `news-aggregator-skill` may feed the web angle too.

2. **For each promising finding with a code repo: inspect the real GitHub repo**
   (same grounding rule as `/radar-add`, do NOT skip):
   - Run `skillspector-gate` on the repo URL (scan-before-trust). Verdict policy:
     0-39 proceed; 40-69 caution + surface findings; 70-100 or any malicious /
     exfil / RCE finding -> mark `status: unverified`, BLOCK, banner, no recommend.
   - Read repo signals: README, last commit / latest release (alive?), issues +
     stars trajectory, license, language, does the code back the claim.
   - Base `description` / `status` / `supersedes` / recommendation on the REPO, not
     the announcement. Contradiction with the hype IS the signal — record it.

3. **Distill + merge into OKF entries** (`okf/ai-radar/<topic>/<slug>.md`):
   frontmatter `type` (required), `title`, `description`, `tags`, `timestamp`
   (today), `resource` (repo URL if any, else source), `status`
   (current|superseded|unverified), `supersedes`. Body: `# Summary`, `# Repo /
   source check`, `# Why this is in the radar`. MERGE into an existing entry on the
   same thing (refresh timestamp, add detail) instead of duplicating; when a new
   finding beats an old one, set the old entry `status: superseded` and point the
   new `supersedes` at it.

4. **Lint pass (the compounding-wiki maintenance step)** — scan the WHOLE bundle:
   - **Contradictions:** two entries asserting incompatible claims -> flag both.
   - **Stale:** `timestamp` older than the topic's freshness window (models/harness
     move fast: ~30 days; knowledge/patterns: ~120 days) and `status: current` ->
     flag "re-verify".
   - **Orphans:** entry with no inbound cross-link and not listed in any index ->
     flag.
   - **Missing links:** entry that mentions a concept that has its own entry but
     does not link it -> add the cross-link.
   Safe fixes (add missing index line, add obvious cross-link, set a clearly-stale
   `current` to needs-reverify) may be applied; anything judgmental is reported,
   not auto-changed.

5. **Update indexes + log.** Refresh topic `index.md` + root `index.md`; prepend a
   `log.md` line summarizing the sweep (topics covered, entries added/updated,
   lint findings).

6. **Sync to live mirror:** copy changed files to `~/.claude/okf/ai-radar/`.

7. **Report** a compact summary: per topic — new/updated entries, any blocked
   (unverified) repos, and the lint punch-list (contradictions / stale / orphans).
   Honor no-nagging: this is a sweep report, not an interruption.

## Notes

- No commit / push from this skill — disk only; committing is a separate gated step.
- Kill switch: `AI_RADAR_DISABLE=1` (silences the downstream gate "speak up");
  deleting `okf/` removes the capability. The weekly schedule (phase 4) is a cron
  routine that can be deleted independently.
- Cap coverage honestly: if a topic's search returns more than you can inspect,
  `log.md` what was deferred — never silently truncate.
