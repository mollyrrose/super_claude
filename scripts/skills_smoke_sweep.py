"""Skills smoke sweep -- ISC #2 of AI_OS_STRATEGY.md ("nothing broke").

For each skill named in scripts/smoke_skills.txt (one directory name per line,
25 significant skills), verify the installed skill is present and intact:
its SKILL.md exists under ~/.claude/skills/<name>/ and is non-trivially sized.

HONEST SCOPE LIMIT: skills are markdown instructions executed by the model, so
a deterministic script cannot "invoke" one. This sweep verifies PRESENCE and
INTEGRITY (the deterministic half of the ISC); the "invocation returns useful
output" half is only observable in a live session and is covered by the day-30
adoption tripwire (exclude/SYSTEM_STRATEGIES/day30_tripwire.md).

Read-only. Exit 0 only if every listed skill passes.
Kill switch: delete this file and smoke_skills.txt; nothing else references them
at runtime. Env override: BRAIN_SKILLS_DIR to point at a non-default skills dir.

Usage: python skills_smoke_sweep.py
"""

from __future__ import annotations

import os
import pathlib
import sys

# A real SKILL.md is prose; anything under this is a stub or a truncated write.
MIN_SKILL_BYTES = 200


def main() -> int:
    here = pathlib.Path(__file__).resolve().parent
    list_file = here / "smoke_skills.txt"
    if not list_file.is_file():
        print(f"[fail] skill list missing: {list_file}")
        return 1

    skills_dir = pathlib.Path(
        os.environ.get("BRAIN_SKILLS_DIR", str(pathlib.Path.home() / ".claude" / "skills"))
    )
    if not skills_dir.is_dir():
        print(f"[fail] skills dir missing: {skills_dir}")
        return 1

    names = [
        line.strip()
        for line in list_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    passed = 0
    for name in names:
        skill_md = skills_dir / name / "SKILL.md"
        if not skill_md.is_file():
            print(f"  [fail] {name}: SKILL.md not found")
            continue
        try:
            size = skill_md.stat().st_size
        except OSError as e:
            print(f"  [fail] {name}: unreadable ({e.__class__.__name__})")
            continue
        if size < MIN_SKILL_BYTES:
            print(f"  [fail] {name}: SKILL.md suspiciously small ({size} bytes)")
            continue
        passed += 1
        print(f"  [pass] {name}")

    total = len(names)
    print(f"\n{passed}/{total} skills present and intact")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
