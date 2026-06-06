# Claude Skills Backup

Snapshot of `~/.claude/skills/` from the operator's machine — a single
copy of every user-installed skill so a fresh Claude Code install can
be restored in one command instead of re-installing each skill
manually.

This is a **personal backup**, not a redistribution. The fork repo is
private. Each skill's `SKILL.md` retains its original
`source:`/`description:` frontmatter so attribution survives the copy.

## What is in here

Every directory under `claude_skills_backup/<name>/` is one skill,
with its `SKILL.md` at the root of that directory plus any support
files the skill ships (scripts, templates, examples). Most skills are
single-file `SKILL.md`-only; a few (e.g. `translate-book`,
`shift-training-year`) carry test baselines and helper scripts.

The snapshot includes:

- Your own custom skills (e.g. `qRem`, `qUpd`, `rev` after the
  Hermes-merge edits).
- Fork-bundled skills (`hermes-curate`, `hermes-learn`).
- 80+ `hermes-*` skills converted from upstream Hermes Agent via
  `claude_code_integration/convert_skills.py`.
- Whatever other skills you had installed at the time of snapshot
  (community/marketplace, ECC, etc.).

What is NOT in here:

- ECC plugin skills (those live under `~/.claude/plugins/`, not
  `~/.claude/skills/`, and update via the plugin marketplace —
  re-install via plugins after a fresh setup).
- `~/.claude/CLAUDE.md`, `~/.claude/settings.json`, hook scripts —
  those are in the fork separately (`claude_code_integration/`).

## Restore on a fresh machine

After cloning the fork and running `pip install -e ".[anthropic]"`:

### Option A — restore everything (PowerShell, Windows)

```powershell
$src = "D:\projects\hermes_claude\hermes-agent\claude_skills_backup"
$dst = "$env:USERPROFILE\.claude\skills"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item -Path "$src\*" -Destination $dst -Recurse -Force
```

### Option B — restore only the skills you want

```powershell
$skills = "qRem","qUpd","rev","hermes-curate","hermes-learn"
$src = "D:\projects\hermes_claude\hermes-agent\claude_skills_backup"
$dst = "$env:USERPROFILE\.claude\skills"
foreach ($s in $skills) {
    Copy-Item -Path "$src\$s" -Destination "$dst\$s" -Recurse -Force
}
```

### Option C — POSIX (macOS / Linux / git-bash)

```bash
cp -r path/to/fork/claude_skills_backup/* ~/.claude/skills/
```

Then restart Claude Code so the new skills are loaded.

## Refresh the backup later

When you want to update the snapshot to reflect your current state
(e.g. after installing new skills or editing existing ones):

```powershell
$src = "$env:USERPROFILE\.claude\skills"
$dst = "D:\projects\hermes_claude\hermes-agent\claude_skills_backup"
Remove-Item -Recurse -Force $dst
Copy-Item -Path $src -Destination $dst -Recurse
git -C "D:\projects\hermes_claude\hermes-agent" add claude_skills_backup
git -C "D:\projects\hermes_claude\hermes-agent" commit -m "Refresh claude_skills_backup snapshot"
git -C "D:\projects\hermes_claude\hermes-agent" push origin main
```

Or use the included script (see `restore.ps1` / `refresh.ps1` in this
directory).

## Conflict notes — what to watch for

- **Same skill exists from a different source.** If a fresh install
  comes with a built-in skill that you also have a customised version
  of in this backup, restoring will overwrite the built-in. Usually
  what you want — but verify before committing on a critical machine.
- **`hermes-auto-*` skills** are curator-generated. They're personal
  to the source machine; on a fresh restore they may not match the
  new machine's project context. Treat them as "starter material" —
  delete the ones that don't fit.
- **`pinned: true` skills** restore as pinned. The lifecycle pass
  will never auto-archive them on the new machine either.

## When this snapshot was taken

See git log for the commit that created this directory. The frontmatter
of each `SKILL.md` is what was active at snapshot time; nothing in the
backup has been modified.
