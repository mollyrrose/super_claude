#!/usr/bin/env python3
"""Install the Hermes-flavoured curator + skill bundle into Claude Code.

Three steps, each independently skippable:

1. **Skill conversion** — convert_skills.py copies converted Hermes
   skills into ~/.claude/skills/hermes-*/.

2. **Curate skill** — copies claude_code_integration/curate_skill/SKILL.md
   to ~/.claude/skills/hermes-curate/SKILL.md. This is the slash command
   Claude itself runs to drain the curator queue.

3. **Hook registration** — adds two hooks to ~/.claude/settings.json:
   - ``Stop`` → curator_stop_hook.py  (enqueues finished session metadata)
   - ``UserPromptSubmit`` → curator_prompt_hook.py  (surfaces reminder)
   Both hooks do zero LLM work. Cost: $0. The actual analysis is done
   by Claude itself when the user runs ``/hermes-curate``.

Run with ``--dry-run`` to preview without writing anything.

Usage:
    python -m claude_code_integration.install_into_claude_code [--dry-run]
        [--skip-skills] [--skip-curate-skill] [--skip-hooks]
        [--overwrite-skills]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CCI_DIR = REPO_ROOT / "claude_code_integration"
CC_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
STOP_HOOK_SCRIPT = CCI_DIR / "curator_stop_hook.py"
PROMPT_HOOK_SCRIPT = CCI_DIR / "curator_prompt_hook.py"

# Skills bundled with the fork. Each entry: (source SKILL.md, install dest).
# Always overwritten on install — these ship with the fork and should
# refresh with bug fixes / policy tweaks without --overwrite-skills.
BUNDLED_SKILLS = [
    (
        CCI_DIR / "curate_skill" / "SKILL.md",
        Path.home() / ".claude" / "skills" / "hermes-curate" / "SKILL.md",
    ),
    (
        CCI_DIR / "learn_skill" / "SKILL.md",
        Path.home() / ".claude" / "skills" / "hermes-learn" / "SKILL.md",
    ),
]


def info(msg: str) -> None:
    print(f"  · {msg}")


def ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def warn(msg: str) -> None:
    print(f"  ! {msg}")


def err(msg: str) -> None:
    print(f"  ✗ {msg}", file=sys.stderr)


def run_converter(overwrite: bool, dry_run: bool) -> int:
    cmd = [sys.executable, str(CCI_DIR / "convert_skills.py")]
    if overwrite:
        cmd.append("--overwrite")
    if dry_run:
        cmd.append("--dry-run")
    info(f"running converter: {' '.join(cmd)}")
    return subprocess.run(cmd, check=False).returncode


def install_bundled_skills(dry_run: bool, overwrite: bool) -> bool:
    """Copy every fork-bundled SKILL.md into ~/.claude/skills/.

    Always overwritten — these skills ship with the fork and should
    refresh on every install run so bug fixes / policy tweaks reach the
    user without an extra flag. The converted hermes-* bundle still
    honours --overwrite-skills via convert_skills.py.
    """
    all_ok = True
    for src, dest in BUNDLED_SKILLS:
        if not src.exists():
            err(f"bundled skill source missing: {src}")
            all_ok = False
            continue
        if dry_run:
            info(f"would copy (always overwrite): {src} -> {dest}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        ok(f"installed/refreshed -> {dest}")
    _ = overwrite  # accepted for signature consistency; these always refresh
    return all_ok


def load_settings() -> dict:
    if not CC_SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(CC_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        warn(f"could not parse {CC_SETTINGS_PATH}: {e} — will rewrite")
        return {}


def save_settings(settings: dict, dry_run: bool) -> None:
    if dry_run:
        info(f"would write: {CC_SETTINGS_PATH}")
        return
    if CC_SETTINGS_PATH.exists():
        backup = CC_SETTINGS_PATH.with_suffix(".json.bak")
        shutil.copy2(CC_SETTINGS_PATH, backup)
        info(f"backed up old settings to {backup.name}")
    CC_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CC_SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _register_one_hook(
    settings: dict,
    event_name: str,
    script: Path,
    timeout: int,
) -> None:
    """Idempotently add one hook entry to settings['hooks'][event_name]."""
    if not script.exists():
        err(f"hook script not found: {script}")
        return

    hook_cmd = f'"{sys.executable}" "{script}"'
    hooks = settings.setdefault("hooks", {})
    entries = hooks.setdefault(event_name, [])

    if not isinstance(entries, list):
        warn(f"unexpected {event_name} entry type: {type(entries).__name__} — skipping")
        return

    for entry in entries:
        if isinstance(entry, dict):
            inner = entry.get("hooks", [])
            if any(
                isinstance(h, dict) and script.name in (h.get("command") or "")
                for h in inner
            ):
                info(f"{event_name} hook for {script.name} already present")
                return
        elif isinstance(entry, str) and script.name in entry:
            info(f"{event_name} hook for {script.name} already present (string form)")
            return

    entries.append({
        "matcher": "",
        "hooks": [{
            "type": "command",
            "command": hook_cmd,
            "timeout": timeout,
        }],
    })
    ok(f"registered {event_name} hook -> {script.name}")


def register_hooks(dry_run: bool) -> bool:
    if not STOP_HOOK_SCRIPT.exists() or not PROMPT_HOOK_SCRIPT.exists():
        err("one or both hook scripts missing — aborting hook registration")
        return False
    settings = load_settings()
    _register_one_hook(settings, "Stop", STOP_HOOK_SCRIPT, timeout=30)
    _register_one_hook(settings, "UserPromptSubmit", PROMPT_HOOK_SCRIPT, timeout=10)
    save_settings(settings, dry_run=dry_run)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-skills", action="store_true")
    parser.add_argument("--skip-curate-skill", action="store_true")
    parser.add_argument("--skip-hooks", action="store_true")
    parser.add_argument("--overwrite-skills", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print()
    print("Hermes → Claude Code integration installer")
    print("==========================================")
    print()

    converter_rc = 0
    if not args.skip_skills:
        print("[1] Converting Hermes skills → ~/.claude/skills/hermes-*/")
        converter_rc = run_converter(
            overwrite=args.overwrite_skills, dry_run=args.dry_run
        )
        if converter_rc != 0:
            err(f"converter exited with code {converter_rc}")
    else:
        info("[1] skipped (--skip-skills)")

    print()
    curate_ok = True
    if not args.skip_curate_skill:
        print("[2] Installing fork-bundled skills (hermes-curate, hermes-learn)")
        curate_ok = install_bundled_skills(
            dry_run=args.dry_run, overwrite=args.overwrite_skills
        )
    else:
        info("[2] skipped (--skip-curate-skill)")

    print()
    hooks_ok = True
    if not args.skip_hooks:
        print("[3] Registering Stop + UserPromptSubmit hooks in ~/.claude/settings.json")
        hooks_ok = register_hooks(dry_run=args.dry_run)
    else:
        info("[3] skipped (--skip-hooks)")

    print()
    if converter_rc == 0 and curate_ok and hooks_ok:
        ok("Install finished.")
        print()
        print("Next steps:")
        print("  - Restart any open Claude Code sessions so the hooks are loaded.")
        print("  - On the next 3+ sessions (or 7+ days), Claude Code will show:")
        print("        [hermes-curator] N session(s) pending curate ...")
        print("    above your prompt. You (or Claude) can then type:")
        print("        /hermes-curate")
        print("    to drain the queue and write skill candidates to:")
        print("        ~/.claude/skills-pending/")
        print("  - No external API key or provider setup is needed —")
        print("    the analysis runs inside your normal Claude session.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
