#!/usr/bin/env python3
"""Read and filter Cursor rules (.cursor/rules/**/*.mdc) for code review context.

Cursor switched from a single flat `.cursorrules` file to per-rule `.mdc` files
under `.cursor/rules/` (Cursor 0.45+). Each .mdc file has YAML frontmatter:
  alwaysApply: true  -> include in every review session
  globs: "src/**"    -> include only when a scope file matches the glob pattern
  description: "..."  -> agent-decides attachment (skipped here; not deterministic)

This script collects all applicable rules and prints a combined text block
suitable for injecting into a review agent's PROJECT CONVENTIONS prompt section.

Usage:
    python read_cursor_rules.py [--repo-root <dir>] [--scope-file <path>]
    python read_cursor_rules.py --repo-root . --scope-file .scratch/qrev-scope.txt

Output:
    A text block on stdout listing the source file and content of each applicable
    rule. Empty output (exit 0) when no rules are found or the directory is absent.

Exit codes:
    0 -- always (non-blocking; missing .cursor/rules/ is fine)
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import sys
from pathlib import Path


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body) from MDC text. Never raises."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw_fm = text[3:end].strip()
    body = text[end + 4:].strip()
    fm: dict = {}
    for line in raw_fm.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            key = k.strip()
            val = v.strip().strip('"').strip("'")
            if val.lower() == "true":
                fm[key] = True
            elif val.lower() == "false":
                fm[key] = False
            else:
                fm[key] = val
    return fm, body


def _matches_any_scope(globs_val: str, scope_files: list[str]) -> bool:
    """Return True if any scope file matches at least one glob pattern."""
    patterns = [g.strip() for g in globs_val.replace(",", " ").split() if g.strip()]
    for sf in scope_files:
        sf_name = sf.replace("\\", "/")
        for pat in patterns:
            if fnmatch.fnmatch(sf_name, pat) or fnmatch.fnmatch(Path(sf).name, pat):
                return True
    return False


def read_rules(repo_root: Path, scope_files: list[str]) -> str:
    """Return a combined block of all applicable cursor rules, or empty string."""
    rules_dir = repo_root / ".cursor" / "rules"
    if not rules_dir.is_dir():
        return ""

    blocks: list[str] = []
    for mdc in sorted(rules_dir.rglob("*.mdc")):
        try:
            text = mdc.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        fm, body = _parse_frontmatter(text)
        if not body.strip():
            continue

        always = fm.get("alwaysApply", False) is True
        globs_val = fm.get("globs", "")

        if always:
            include = True
        elif globs_val and scope_files:
            include = _matches_any_scope(str(globs_val), scope_files)
        else:
            include = False

        if include:
            rel = mdc.relative_to(repo_root)
            blocks.append(f"# Rule: {rel}\n{body.strip()}")

    if not blocks:
        return ""

    return "\n\n".join(blocks)


def _load_scope_file(path: Path) -> list[str]:
    try:
        return [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except OSError:
        return []


def main() -> None:
    ap = argparse.ArgumentParser(description="Read applicable Cursor MDC rules")
    ap.add_argument("--repo-root", default=".", help="Repo root directory")
    ap.add_argument("--scope-file", default=None,
                    help="File listing paths in review scope (one per line)")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    scope_files: list[str] = []
    if args.scope_file:
        scope_files = _load_scope_file(Path(args.scope_file))

    output = read_rules(repo_root, scope_files)
    if output:
        sys.stdout.write(output)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
