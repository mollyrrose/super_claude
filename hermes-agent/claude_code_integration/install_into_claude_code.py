#!/usr/bin/env python3
"""Install the Hermes-flavoured curator + skill bundle into Claude Code.

Four steps, each independently skippable:

1. **Skill conversion** -- convert_skills.py copies converted Hermes
   skills into ~/.claude/skills/hermes-*/.

2. **Curate skill** -- copies claude_code_integration/curate_skill/SKILL.md
   to ~/.claude/skills/hermes-curate/SKILL.md. This is the slash command
   Claude itself runs to drain the curator queue.

3. **Hook registration** -- adds two hooks to ~/.claude/settings.json:
   - ``Stop`` -> curator_stop_hook.py  (enqueues finished session metadata)
   - ``UserPromptSubmit`` -> curator_prompt_hook.py  (surfaces reminder)
   Both hooks do zero LLM work. Cost: $0. The actual analysis is done
   by Claude itself when the user runs ``/hermes-curate``.

4. **Optional API keys** -- interactive prompt for OPENAI_API_KEY and
   DEEPSEEK_API_KEY, stored in ~/.claude/settings.json's ``env`` block
   (Claude-Code-scoped; never leaks to other Windows applications). Used
   by ``/qRev``'s opt-in multi-provider critic. Press Enter to skip a
   single key, or pass ``--skip-api-keys`` to skip the whole step.
   If a key is already set in process env, Windows User env, or already
   in settings.json, the installer detects it and does NOT prompt again.
   Also auto-configures ``QREV_CRITIC_PROVIDERS`` to match the keys
   actually present, so /qRev knows which providers to consult.

Run with ``--dry-run`` to preview without writing anything.

Usage:
    python -m claude_code_integration.install_into_claude_code [--dry-run]
        [--skip-skills] [--skip-curate-skill] [--skip-hooks]
        [--skip-api-keys] [--overwrite-skills]
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
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
# Always overwritten on install -- these ship with the fork and should
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
    print(f"  - {msg}")


def ok(msg: str) -> None:
    print(f"  [ok] {msg}")


def warn(msg: str) -> None:
    print(f"  ! {msg}")


def err(msg: str) -> None:
    print(f"  [fail] {msg}", file=sys.stderr)


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

    Always overwritten -- these skills ship with the fork and should
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
        warn(f"could not parse {CC_SETTINGS_PATH}: {e} -- will rewrite")
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
        warn(f"unexpected {event_name} entry type: {type(entries).__name__} -- skipping")
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


def _check_existing_key(env_var: str, settings: dict) -> tuple[str, str]:
    """Return (current_value, source) for env_var across all check locations.

    Sources: 'settings.json', 'process', 'user-env', or 'unset'. Used to
    decide whether the API-key prompt should ask the user again -- never
    silently overwrite a key the user has already configured elsewhere.
    """
    settings_env = settings.get("env", {})
    if isinstance(settings_env, dict) and settings_env.get(env_var):
        return settings_env[env_var], "settings.json"
    if os.environ.get(env_var):
        return os.environ[env_var], "process"
    if sys.platform == "win32":
        try:
            val = subprocess.check_output(
                [
                    "powershell", "-NoProfile", "-Command",
                    f'[Environment]::GetEnvironmentVariable("{env_var}", "User")',
                ],
                text=True,
                timeout=10,
                stderr=subprocess.DEVNULL,
            ).strip()
            if val and val.lower() != "null":
                return val, "user-env"
        except (subprocess.SubprocessError, OSError):
            pass
    return "", "unset"


def _mask_key(val: str) -> str:
    if not val:
        return "(empty)"
    if len(val) <= 12:
        return val[:3] + "..." + val[-3:]
    return val[:7] + "..." + val[-4:]


def prompt_for_api_keys(dry_run: bool) -> bool:
    """Step 4 -- interactive prompt for OpenAI + DeepSeek keys.

    Stored in ~/.claude/settings.json's `env` block, which Claude Code
    injects into every subprocess it spawns (hooks + skill scripts both
    see it). Scope = Claude Code only; nothing leaks to other Windows
    apps the way a system-wide User env var would.

    Also configures QREV_CRITIC_PROVIDERS to match whichever keys are
    present (claude is always included; openai / deepseek added when
    their key is reachable from any source).

    Press Enter to skip a key. You can re-run this installer later to
    add a missing key without touching the rest of the setup.
    """
    print()
    print("[4] Multi-provider /qRev critic API keys (optional)")
    print()
    print("These power the cross-model consensus layer of /qRev. With them,")
    print("/qRev asks Claude + OpenAI + DeepSeek and elevates findings the")
    print("two providers agree on. Without them, /qRev runs Claude-only --")
    print("which is the default and works fine. Press Enter on any prompt")
    print("to skip that key.")
    print()

    if dry_run:
        info("would prompt interactively for OPENAI_API_KEY + DEEPSEEK_API_KEY")
        info("would set QREV_CRITIC_PROVIDERS based on which keys are present")
        info("would write to ~/.claude/settings.json 'env' block")
        return True

    settings = load_settings()
    env_block = settings.get("env")
    if not isinstance(env_block, dict):
        if env_block is not None:
            warn(
                f"settings.json 'env' is {type(env_block).__name__}, expected dict"
                " -- replacing with an empty dict"
            )
        env_block = {}
        settings["env"] = env_block

    keys_to_check = [
        ("OPENAI_API_KEY",   "OpenAI",   "openai"),
        ("DEEPSEEK_API_KEY", "DeepSeek", "deepseek"),
    ]

    changed = False
    have_providers: list[str] = []

    for env_var, label, provider_name in keys_to_check:
        current, source = _check_existing_key(env_var, settings)
        if current:
            print(f"  [{label}] already configured (source: {source}): {_mask_key(current)}")
            if source == "settings.json":
                have_providers.append(provider_name)
                continue
            try:
                choice = input(
                    f"    Copy into settings.json's env block too? (y/N): "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = ""
                print()
            if choice == "y":
                env_block[env_var] = current
                changed = True
                ok(f"{label} key copied to settings.json env block")
            else:
                info(f"{label} left where it is ({source})")
            have_providers.append(provider_name)
            continue

        try:
            new_val = getpass.getpass(
                f"    Enter {label} API key (input hidden; Enter to skip): "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            new_val = ""

        if new_val:
            env_block[env_var] = new_val
            have_providers.append(provider_name)
            changed = True
            ok(f"{label} key stored in settings.json env block")
        else:
            info(f"{label} skipped")

    desired_providers = "claude"
    if have_providers:
        desired_providers = "claude," + ",".join(have_providers)

    current_qrev = env_block.get("QREV_CRITIC_PROVIDERS", "")
    if desired_providers != "claude" and current_qrev != desired_providers:
        print()
        print(f"  QREV_CRITIC_PROVIDERS would be set to: {desired_providers}")
        if current_qrev:
            print(f"    (current value: {current_qrev})")
        else:
            print(f"    (currently unset -- default is claude-only)")
        try:
            choice = input("    Apply? (Y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = ""
            print()
        if choice != "n":
            env_block["QREV_CRITIC_PROVIDERS"] = desired_providers
            changed = True
            ok(f"QREV_CRITIC_PROVIDERS = {desired_providers}")
        else:
            info("QREV_CRITIC_PROVIDERS left unchanged")

    if changed:
        save_settings(settings, dry_run=False)
        ok(f"settings written to {CC_SETTINGS_PATH}")
        info("Restart Claude Code (open a fresh window) so the new env takes effect.")
    else:
        info("no changes to API key settings")

    return True


def register_hooks(dry_run: bool) -> bool:
    if not STOP_HOOK_SCRIPT.exists() or not PROMPT_HOOK_SCRIPT.exists():
        err("one or both hook scripts missing -- aborting hook registration")
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
    parser.add_argument(
        "--skip-api-keys",
        action="store_true",
        help=(
            "Skip step 4: don't prompt for OpenAI / DeepSeek API keys."
            " You can re-run the installer later to add them, or set them"
            " manually in ~/.claude/settings.json's 'env' block."
        ),
    )
    parser.add_argument("--overwrite-skills", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print()
    print("Hermes -> Claude Code integration installer")
    print("==========================================")
    print()

    converter_rc = 0
    if not args.skip_skills:
        print("[1] Converting Hermes skills -> ~/.claude/skills/hermes-*/")
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
    api_keys_ok = True
    if not args.skip_api_keys:
        try:
            api_keys_ok = prompt_for_api_keys(dry_run=args.dry_run)
        except Exception as e:
            warn(f"step 4 errored: {e} -- continuing without API keys")
            api_keys_ok = True  # non-fatal
    else:
        info("[4] skipped (--skip-api-keys) -- /qRev will run claude-only")
        info("    To add keys later, re-run this installer, or edit:")
        info(f"    {CC_SETTINGS_PATH} ('env' block)")

    print()
    if converter_rc == 0 and curate_ok and hooks_ok and api_keys_ok:
        ok("Install finished.")
        print()
        print("Next steps:")
        print("  - Restart any open Claude Code sessions so the hooks AND the")
        print("    new env block (if any) are loaded.")
        print("  - On the next 3+ sessions (or 7+ days), Claude Code will show:")
        print("        [hermes-curator] N session(s) pending curate ...")
        print("    above your prompt. You (or Claude) can then type:")
        print("        /hermes-curate")
        print("    to drain the queue and write skill candidates to:")
        print("        ~/.claude/skills-pending/")
        print("  - The curator analysis itself uses no external API -- it runs")
        print("    inside your normal Claude session.")
        print("  - The optional API keys in step 4 are ONLY used by /qRev's")
        print("    multi-provider critic. Without them, /qRev runs claude-only.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
