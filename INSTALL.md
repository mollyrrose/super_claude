# INSTALL — rebuild the Claude Code setup from this repo

This repo is the source of truth for the personal `~/.claude` configuration, so a
fresh machine can be rebuilt from git. The live config is mirrored into the repo
in a **sanitized** form (API keys redacted, user name tokenized) and restored back
out with secrets filled from the environment.

## Files

- `home_dotclaude/settings.json` — sanitized mirror of `~/.claude/settings.json`.
  Secrets appear as `[REDACTED:<NAME>]`; the profile user name as `[USER]`.
- `home_dotclaude/CLAUDE.md` — verbatim copy of the global `~/.claude/CLAUDE.md`.
- `scripts/sync_claude_config.ps1` — LIVE -> repo. Run after editing the live
  config so the repo stays current (redacts secrets, tokenizes the user name,
  aborts if a real key would leak).
- `scripts/restore_claude_config.ps1` — repo -> LIVE. Rebuilds `~/.claude` on a
  machine: de-tokenizes paths, fills secrets from env vars, copies `scripts/*.py,
  *.js` and the skills backup, backs up any existing `settings.json` first.

### Full personal state (private, not in git)

The two scripts above only cover what's safe to commit. Personal state that
git never sees — memory, auto-learned `hermes-auto-*` skills, decision logs,
curator/qrev counters — lives in the gitignored `exclude/windows_reinstall_backup/`
and is handled by a second, parallel pair of scripts using the SAME
`[USER]`/`[PY]`/`[REPO]` tokenization scheme (so no absolute path or Windows
username is ever hardcoded in either):

- `scripts/backup_claude_state.ps1` — LIVE -> `exclude/windows_reinstall_backup/dotclaude/`.
  Tokenizes `settings.json`/`settings.local.json` the same way `sync_claude_config.ps1`
  does, but does NOT redact secrets (this destination is private, not committed).
- `scripts/restore_claude_state.ps1` — that backup -> LIVE, on any machine or
  any renamed Windows profile. De-tokenizes `[USER]`/`[PY]`/`[REPO]`
  automatically for whatever machine it runs on, and also installs the full
  skill bundle from `hermes-agent/claude_skills_backup/`.

See `exclude/windows_reinstall_backup/RESTORE_GUIDE.md` for the full restore
walkthrough (Python/Node install, plugin install, verification steps).

## Keep the repo current (existing machine)

After changing `~/.claude/settings.json` or `~/.claude/CLAUDE.md`:

```powershell
powershell -File <repo-root>\scripts\sync_claude_config.ps1
git -C <repo-root> diff home_dotclaude\   # review
git -C <repo-root> add home_dotclaude\ ; git commit -m "chore: sync claude config" ; git push
```

Got a personal machine handy (memory, auto-learned skills, decision logs)?
Refresh that snapshot too before anything risky:
```powershell
powershell -File <repo-root>\scripts\backup_claude_state.ps1
```

## Rebuild on a new machine

1. Install **Python 3.x** (any drive; on PATH, or set `$env:CLAUDE_PYTHON`) and **Node.js**.
   Also install **semgrep** (`python -m pip install --upgrade semgrep`) — required
   for `/qRev`'s and `/rev`'s Phase A deterministic gate; see "Required tool:
   semgrep" below. Without it, Phase A logs a coverage gap and skips straight to
   the agent fleet.
2. Clone this repo **anywhere** (no specific drive needed — no fixed drive letter
   is required). Restore fills `[REPO]` from the clone's own location and `[PY]`
   from the Python it finds, so the layout is portable.
3. If you have a personal `exclude/windows_reinstall_backup/` snapshot from this
   same setup (see below), restore everything — settings, memory, skills, hook
   scripts, state — in one step:
   ```powershell
   powershell -File <repo-root>\scripts\restore_claude_state.ps1
   ```
   This is the recommended path when rebuilding YOUR OWN machine; it already
   carries your real API keys. Skip to step 6.
4. Otherwise (a genuinely fresh clone, no personal backup), set the API keys so
   the config-only restore can fill them:
   ```powershell
   setx OPENAI_API_KEY   "<key>"
   setx DEEPSEEK_API_KEY "<key>"
   # open a NEW shell so setx values are in the environment
   ```
5. Restore from the git-tracked, sanitized mirror:
   ```powershell
   powershell -File <repo-root>\scripts\restore_claude_config.ps1
   ```
   Secrets not present in the environment are left as `[REDACTED:<NAME>]` with a
   warning (the script never invents a key) — set them and re-run, or edit
   `~/.claude/settings.json` by hand.
6. Install the marketplace plugins listed in `settings.json` `enabledPlugins`
   (`ecc@ecc`, `ruflo-core@ruflo`) via `/plugin` inside Claude Code.

## Notes

- `sync` redacts any `env` key whose name matches `*_API_KEY` / `*_KEY` / `*TOKEN`
  / `*SECRET` / `*PASSWORD`, so new secret env vars are sanitized automatically.
- The repo root and Python path are stored as `[REPO]` / `[PY]` tokens in the
  mirror and filled at restore time from the clone's location and a discovered
  Python (`$env:CLAUDE_PYTHON` overrides) — so no specific drive or install path
  is baked in. `~/.claude/...` paths use `[USER]` (the Windows profile is always
  under `C:\Users\<user>`).
- The GLM (z.ai) launcher and other one-off install commands live in the global
  `~/.claude/CLAUDE.md`; run them manually when needed.

## Required tool: semgrep (`/qRev` & `/rev` Phase A)

`/qRev` and `/rev` run a deterministic gate (Phase A) before the agent fleet:
semgrep + `CODING_STANDARDS.md` non-negotiable rules, via
`scripts/lib/run_semgrep_loop.py`. If semgrep is missing on a machine, Phase A
logs `Phase A: semgrep nincs telepitve -> kihagyva (coverage gap)` and the run
falls straight to Phase B — findings that semgrep would have caught are
silently skipped.

Install (any Python on the machine; pick the same one Claude Code's hooks use):
```powershell
python -m pip install --upgrade semgrep
```

On Windows, `pip install --user`-style installs put `semgrep.exe` under
`%APPDATA%\Python\Python3XX\Scripts`, which is usually **not** on `PATH`.
`run_semgrep_loop.py` already handles this: `_extend_path_for_semgrep()` globs
the standard per-user install roots (`%APPDATA%\Python`,
`%LOCALAPPDATA%\Programs\Python`) for `semgrep.exe` and prepends the matching
`Scripts` dir to its own process `PATH` before invoking semgrep — so no PATH
edit is required for `/qRev`/`/rev` themselves to find it. To run bare
`semgrep` from an interactive shell too (optional, for manual debugging),
add that `Scripts` directory to your user `PATH` and open a new shell/window
(env changes don't propagate to already-running processes, including an
already-open Claude Code window).

Per the standing "keep semgrep on the latest release" policy, upgrade with the
same command above whenever `/qRev` or `/rev` reports semgrep is behind — no
need to ask first.

## External skills (bundled in repo, sources below)

The following external skill packs are vendored into `hermes-agent/claude_skills_backup/`
and installed by `restore_claude_config.ps1` alongside the other skills. No separate
clone is needed -- the SKILL.md files are already in the repo.

| Skill folder | Source repo | License |
|---|---|---|
| `no-ai-slop` | https://github.com/petergyang/no-ai-slop | MIT |
| `i-have-adhd` | https://github.com/ayghri/i-have-adhd | MIT |
| `code-structure` | https://github.com/michaelshimeles/skills/tree/main/code-structure | MIT |
| `improve-codebase-architecture` | https://github.com/mattpocock/skills/tree/main/skills/engineering/improve-codebase-architecture | MIT |
| `mp-code-review` | https://github.com/mattpocock/skills/tree/main/skills/engineering/code-review | MIT |
| `mp-diagnosing-bugs` | https://github.com/mattpocock/skills/tree/main/skills/engineering/diagnosing-bugs | MIT |
| `opensrc` | https://github.com/vercel-labs/opensrc | MIT |

To pull the latest version of any of these from upstream:
```powershell
# Example: update mp-diagnosing-bugs
$b64 = (gh api repos/mattpocock/skills/contents/skills/engineering/diagnosing-bugs/SKILL.md --jq '.content')
[System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64 -replace '\n','')) |
  Set-Content -Encoding UTF8 "hermes-agent\claude_skills_backup\mp-diagnosing-bugs\SKILL.md"
Copy-Item "hermes-agent\claude_skills_backup\mp-diagnosing-bugs\SKILL.md" `
  "$env:USERPROFILE\.claude\skills\mp-diagnosing-bugs\SKILL.md"
```

### opensrc CLI (optional, needed for the opensrc skill)

The `opensrc` skill requires the `opensrc` CLI from vercel-labs:
```powershell
npm install -g opensrc
# or without installing: npx opensrc path zod
```

### composio (optional, AI tool integration)

Composio (https://github.com/ComposioHQ/composio) provides 250+ pre-built tool integrations
for AI agents (GitHub, Slack, Gmail, etc.). Install when you need Claude agents to call
external APIs without writing custom tool wrappers:
```powershell
pip install composio-claude          # Python SDK
npm install @composio-dev/composio-core   # TypeScript SDK
```
See https://docs.composio.dev for available tools.
