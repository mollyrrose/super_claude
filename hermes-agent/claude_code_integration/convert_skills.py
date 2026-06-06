#!/usr/bin/env python3
"""Convert Hermes skills to Claude Code SKILL.md format.

Walks <repo>/skills/<category>/<name>/SKILL.md and writes a minimal-frontmatter
copy to ~/.claude/skills/hermes-<name>/SKILL.md (or a custom dest).

The body is copied verbatim — Hermes-specific tool references (e.g.
`tools.file_operations.read`) are left intact. They translate to common
Claude Code primitives well enough that Claude can usually pick them up;
where they don't, a small head-note at the top of each converted skill
flags the origin so the user knows to inspect on first use.

Usage:
    python -m claude_code_integration.convert_skills [--dry-run]
        [--dest DIR] [--source DIR] [--exclude category1,category2]
        [--overwrite]

Exit codes:
    0  success
    1  source dir missing / malformed
    2  destination not writable
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

# Categories skipped by default — too Hermes-specific or context-bound to
# carry over usefully into a Claude Code session.
#
# `workflow` lives in the fork itself and contains qrem/qupd/rev, which
# duplicate the user's existing ECC-provided qRem/qUpd/rev. Exclude it
# from the converter so the duplicates are not recreated on install
# refresh. The fork's Hermes runtime still uses skills/workflow/ — only
# the Claude Code re-export is suppressed.
DEFAULT_EXCLUDE = {"dogfood", "gifs", "yuanbao", "index-cache", "workflow"}

# Hermes frontmatter keys we preserve. Anything else gets dropped because
# Claude Code's skill loader doesn't understand it.
PRESERVE_KEYS = {"name", "description"}

# Marker we add so the user (and curator) can tell which skills came in
# via this converter.
SOURCE_TAG = "hermes-agent-converted"

CONVERTED_NOTE = (
    "> _Converted from Hermes Agent. Some tool references in the body may "
    "name Hermes-specific modules (e.g. `tools.file_operations`); the "
    "Claude Code equivalents are typically `Read`, `Edit`, `Write`, `Bash`, "
    "`Glob`, `Grep`. Treat them as guidance, not literal API calls._\n\n"
)


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter_dict, body) from a SKILL.md text.

    Accepts only flat YAML — Hermes does have nested keys (metadata.hermes.tags)
    but we drop everything except 'name' and 'description' anyway, so a
    shallow line-by-line scan is sufficient.
    """
    if not text.startswith("---"):
        return {}, text

    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    header = text[3:end].strip("\n")
    body = text[end + 4 :].lstrip("\n")

    fm: dict[str, str] = {}
    in_nested = False
    for raw in header.splitlines():
        if not raw.strip():
            continue
        # crude nested-block skip: a line that doesn't start with whitespace
        # AND has a key without a value triggers a "skip until dedent" mode.
        if not raw.startswith((" ", "\t")):
            in_nested = False
            if ":" in raw:
                key, _, value = raw.partition(":")
                key = key.strip()
                value = value.strip()
                if not value:
                    in_nested = True
                    continue
                # strip surrounding quotes
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                fm[key] = value
        # nested lines are silently skipped
    return fm, body


def _slugify(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-").lower()
    return cleaned or "unnamed"


def convert_one(
    src: Path,
    dest_root: Path,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> Optional[Path]:
    """Convert one Hermes SKILL.md. Returns dest path or None if skipped."""
    text = src.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)

    name = fm.get("name") or src.parent.name
    name = _slugify(name)
    description = fm.get("description") or f"Hermes skill: {name}"

    dest_dir = dest_root / f"hermes-{name}"
    dest_path = dest_dir / "SKILL.md"

    if dest_path.exists() and not overwrite:
        return None

    output = (
        "---\n"
        f"name: hermes-{name}\n"
        f"description: {_yaml_quote(description)}\n"
        f"source: {SOURCE_TAG}\n"
        f"upstream_path: {src.relative_to(src.parents[2]).as_posix()}\n"
        "---\n\n"
        + CONVERTED_NOTE
        + body
    )

    if dry_run:
        return dest_path

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(output, encoding="utf-8")
    # Carry over any sibling files (scripts, examples) the skill might rely on.
    for extra in src.parent.iterdir():
        if extra.name == "SKILL.md":
            continue
        target = dest_dir / extra.name
        if target.exists() and not overwrite:
            continue
        if extra.is_dir():
            shutil.copytree(extra, target, dirs_exist_ok=overwrite)
        else:
            shutil.copy2(extra, target)
    return dest_path


def _yaml_quote(value: str) -> str:
    """Quote a description for safe YAML inlining."""
    needs_quote = any(c in value for c in ":#&*!|>'%@`")
    if not needs_quote and "\n" not in value and not value.startswith(("[", "{")):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "skills",
        help="Hermes skills root (default: <repo>/skills)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path.home() / ".claude" / "skills",
        help="Destination directory (default: ~/.claude/skills)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default=",".join(sorted(DEFAULT_EXCLUDE)),
        help="Comma-separated category names to skip",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing hermes-* skills instead of skipping them",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing anything",
    )
    args = parser.parse_args()

    if not args.source.is_dir():
        print(f"ERROR: source not found: {args.source}", file=sys.stderr)
        return 1

    excluded = {s.strip() for s in args.exclude.split(",") if s.strip()}

    try:
        args.dest.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"ERROR: destination not writable: {args.dest} — {e}", file=sys.stderr)
        return 2

    converted = 0
    skipped_existing = 0
    skipped_excluded = 0

    for skill_md in sorted(args.source.glob("*/*/SKILL.md")):
        category = skill_md.parents[1].name
        if category in excluded:
            skipped_excluded += 1
            continue
        result = convert_one(
            skill_md,
            args.dest,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
        if result is None:
            skipped_existing += 1
            continue
        converted += 1
        if args.dry_run:
            print(f"would write: {result}")
        else:
            print(f"wrote: {result}")

    summary = (
        f"\nDone — converted={converted}  "
        f"skipped_existing={skipped_existing}  "
        f"skipped_excluded={skipped_excluded}"
    )
    if args.dry_run:
        summary += "  (dry-run)"
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
