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

## Keep the repo current (existing machine)

After changing `~/.claude/settings.json` or `~/.claude/CLAUDE.md`:

```powershell
pwsh D:\projects\super_claude\scripts\sync_claude_config.ps1
git -C D:\projects\super_claude diff home_dotclaude\   # review
git -C D:\projects\super_claude add home_dotclaude\ ; git commit -m "chore: sync claude config" ; git push
```

## Rebuild on a new machine

1. Install **Python 3.13** at `C:\Python313` and **Node.js** (hooks + statusline need them).
2. Clone this repo to `D:\Projects\super_claude` (paths in `settings.json` are absolute).
3. Set the API keys so restore can fill them:
   ```powershell
   setx OPENAI_API_KEY   "<key>"
   setx DEEPSEEK_API_KEY "<key>"
   # open a NEW shell so setx values are in the environment
   ```
4. Restore:
   ```powershell
   pwsh D:\projects\super_claude\scripts\restore_claude_config.ps1
   ```
   Secrets not present in the environment are left as `[REDACTED:<NAME>]` with a
   warning (the script never invents a key) — set them and re-run, or edit
   `~/.claude/settings.json` by hand.
5. Install the marketplace plugins listed in `settings.json` `enabledPlugins`
   (`ecc@ecc`, `ruflo-core@ruflo`) via `/plugin` inside Claude Code.

## Notes

- `sync` redacts any `env` key whose name matches `*_API_KEY` / `*_KEY` / `*TOKEN`
  / `*SECRET` / `*PASSWORD`, so new secret env vars are sanitized automatically.
- Hooks reference the repo at `D:\Projects\super_claude` and Python at
  `C:\Python313`; on a different layout, edit `~/.claude/settings.json` after restore.
- The GLM (z.ai) launcher and other one-off install commands live in the global
  `~/.claude/CLAUDE.md`; run them manually when needed.
