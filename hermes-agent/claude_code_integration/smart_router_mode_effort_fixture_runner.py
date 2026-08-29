#!/usr/bin/env python3
"""Gate check (ISC #8): assert every fixture prompt maps to its expected
{mode, effort, tier}. Exit 0 on 15/15, exit 1 on any mismatch. Importable:
run_fixture() -> (passed: bool, failures: list[str])."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from smart_router_rules import recommend_mode_effort

FIXTURE = Path(__file__).resolve().parent / "smart_router_mode_effort_fixture.json"


def run_fixture(path: Path = FIXTURE):
    rows = json.loads(path.read_text(encoding="utf-8"))
    failures = []
    for r in rows:
        me = recommend_mode_effort(r["prompt"])
        got = None if me is None else (me.mode, me.effort, me.tier)
        want = (r["mode"], r["effort"], r["tier"])
        if got != want:
            failures.append(f"{r['prompt']!r}: want {want}, got {got}")
    return (len(failures) == 0 and len(rows) == 15), failures


def main() -> int:
    # Counts derive from the ACTUAL row count -- never from the constant 15.
    # (A 14-row fixture with zero mismatches must NOT print a 15/15 pass line.)
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    ok, failures = run_fixture()
    passed = len(rows) - len(failures)
    if len(rows) != 15:
        print(f"GATE FAIL: fixture has {len(rows)} rows, expected 15")
    for f in failures:
        print("FAIL:", f)
    print(f"{passed}/{len(rows)} PASS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
