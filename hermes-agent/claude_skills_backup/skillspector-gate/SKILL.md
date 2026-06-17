---
name: skillspector-gate
description: "Security gate that scans external code with NVIDIA skillspector BEFORE it is cloned, installed, or trusted. Use automatically whenever about to download a GitHub repo, install a Claude Code skill/plugin, or pull any third-party agent code. Blocks high-risk code (prompt injection, data exfiltration, supply-chain, malicious patterns) and asks the user before proceeding. Invoked via /skillspector-gate <url-or-path> or auto-followed per the global CLAUDE.md scan-before-download rule."
---

# skillspector-gate — scan before you download

Run this BEFORE cloning, installing, or otherwise trusting any external code from
GitHub (or a URL / zip / directory). It wraps NVIDIA's `skillspector` static
scanner (64 patterns / 16 categories: prompt injection, data exfiltration,
privilege escalation, supply-chain, malicious code). It is the enforcement of the
global rule "Scan GitHub code before downloading it".

## When to run (automatic)

Trigger this gate, without being asked, whenever you are about to:
- `git clone` an external repo, or download a zip/tarball of one;
- install a Claude Code skill or plugin (`/plugin install`, copying into
  `~/.claude/skills/`, `npx skills add ...`, etc.);
- run an installer/setup from a freshly fetched third-party repo.

You may skip it for first-party / already-vetted code: this repo (`super_claude`),
NVIDIA's `skillspector` itself (the bootstrap-trust root), and anything already
recorded as scanned in `~/.claude/.skillspector_log.jsonl`.

## How to run

```powershell
$ss = "C:\Users\Seal Josephson\.claude\tools\skillspector\.venv\Scripts\skillspector.exe"
# URL form (preferred — scans WITHOUT adding it to your tree):
& $ss scan "<git-url>" --no-llm --format json -o "<repo-root>\.scratch\scans\<name>.json"
# local form (already-downloaded code, e.g. retro-scan):
& $ss scan "<local-dir>" --no-llm --format json -o "<...>\<name>.json"
```

- `--no-llm` is static-only: fast, offline, no API key. Use it by default.
- For a deeper pass on a borderline result, drop `--no-llm` (needs an LLM provider
  key: `NVIDIA_INFERENCE_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`).
- Read the JSON: the overall risk score (0-100) and the per-finding severity +
  category. A human-readable version is the default `--format terminal`.

## Verdict policy (our thresholds)

Interpret the overall risk score:

- **0-39 (LOW)** -> proceed. Note the score in one line; install normally.
- **40-69 (MEDIUM)** -> proceed with caution. Surface the top findings (category +
  file) to the user in one short block before installing; prefer installing only
  the needed subset.
- **70-100 (HIGH)** -> BLOCK. Do NOT clone/install. Show the findings and ask the
  user explicitly whether to override.
- **Any finding flagged likely-malicious / data-exfiltration / remote-code-exec**
  -> BLOCK regardless of the numeric score, and ask before doing anything.

When you block, end the turn with the global USER-INPUT banner so the user notices
they must decide.

## Log every scan

Append one line per scan to `~/.claude/.skillspector_log.jsonl` so the same repo
isn't re-scanned needlessly and there is an audit trail:

```json
{"ts":"<ISO8601>","target":"<url-or-path>","risk_score":<n>,"verdict":"low|medium|high|blocked","installed":<true|false>,"report":"<path to json>"}
```

## Kill switch / disable

This gate is a documentation+skill behavior, not a hook — to disable, stop
following the global "Scan GitHub code before downloading it" rule (remove that
section), or simply note "skip the scan gate for this one" when you have already
vetted a source. The scanner itself lives at `~/.claude/tools/skillspector` and
can be removed with no effect on anything else.

## Notes

- skillspector is bootstrap-trusted (it is the scanner; we cannot scan it with
  itself before first install). It is NVIDIA-published, Apache-2.0.
- The scanner is stdlib-plus-langchain Python in a dedicated venv; it does not
  touch the project being scanned (URL form scans an internal temp clone).
