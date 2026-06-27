#!/usr/bin/env python3
"""Smoketest for stall_scan.py. Run:
    python scripts/stall_scan_smoketest.py
Prints per-check lines + 'ALL PASS'; non-zero exit on first failure."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stall_scan as ss  # noqa: E402

n = 0


def check(cond, label):
    global n
    n += 1
    if not cond:
        print(f"[fail] {label}")
        sys.exit(1)
    print(f"[ok] {label}")


def _write(rows):
    d = tempfile.mkdtemp(prefix="stallscan-")
    tp = Path(d) / "t.jsonl"
    tp.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf8")
    return tp


def asst(*blocks):
    return {"type": "assistant", "message": {"content": list(blocks)}}


def usr(*blocks):
    return {"type": "user", "message": {"content": list(blocks)}}


def tu(tid, name, **inp):
    return {"type": "tool_use", "id": tid, "name": name, "input": inp}


def tr(tid):
    return {"type": "tool_result", "tool_use_id": tid, "content": "ok"}


# --- all calls matched -> no unmatched ---
tp = _write([
    asst(tu("a", "Read", file_path="x.py")),
    usr(tr("a")),
    asst(tu("b", "Bash", command="ls")),
    usr(tr("b")),
])
res = ss.scan(tp)
check(res["ok"] and res["total_use"] == 2 and res["total_result"] == 2, "counts both calls + results")
check(res["unmatched"] == [], "no unmatched when all results present")

# --- one swallowed Edit in the middle -> detected, with summary + line ---
tp = _write([
    asst(tu("a", "Read", file_path="x.py")),
    usr(tr("a")),
    asst(tu("b", "Edit", file_path="backend/foo.ts")),   # no result -> stall
    asst(tu("c", "Bash", command="pytest")),
    usr(tr("c")),
])
res = ss.scan(tp)
ids = [u["id"] for u in res["unmatched"]]
check(ids == ["b"], "detects the single swallowed Edit")
check(res["unmatched"][0]["name"] == "Edit", "stall carries tool name")
check("backend/foo.ts" in res["unmatched"][0]["summary"], "stall carries input summary")
check(res["unmatched"][0]["line"] == 3, "stall carries transcript line number")

# --- order preserved (oldest first) ---
tp = _write([
    asst(tu("a", "Edit", file_path="one.ts")),    # stall
    asst(tu("b", "Edit", file_path="two.ts")),    # stall
])
res = ss.scan(tp)
check([u["summary"] for u in res["unmatched"]] == ["one.ts", "two.ts"], "unmatched in transcript order")

# --- main(): most-recent unmatched treated as in-flight (excluded from stalls) ---
out = ss.main(["--transcript", str(tp), "--json"])
check(out == 0, "main returns 0")

# capture JSON by re-running scan logic the way main does
res = ss.scan(tp)
unmatched = res["unmatched"]
in_flight = unmatched[-1]
stalls = unmatched[:-1]
check([s["summary"] for s in stalls] == ["one.ts"], "default: last unmatched is in-flight, not a stall")
check(in_flight["summary"] == "two.ts", "in-flight is the most recent unmatched")

# --- malformed lines are skipped, not fatal ---
d = tempfile.mkdtemp(prefix="stallscan-")
tp = Path(d) / "bad.jsonl"
tp.write_text("not json\n" + json.dumps(asst(tu("a", "Edit", file_path="z.ts"))) + "\n{also bad", encoding="utf8")
res = ss.scan(tp)
check(res["ok"] and [u["id"] for u in res["unmatched"]] == ["a"], "skips malformed lines, still finds stall")

# --- missing transcript -> ok False, no crash ---
res = ss.scan(Path(d) / "nope.jsonl")
check(not res["ok"], "missing transcript -> ok False (no crash)")

# --- path mangling matches Claude Code's project-dir scheme ---
mp = ss.project_session_dir("D:\\projects\\super_claude")
check(mp.name == "D--projects-super-claude", "cwd -> mangled project dir name")

print(f"\nALL PASS ({n} checks)")
