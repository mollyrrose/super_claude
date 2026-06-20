#!/usr/bin/env python3
"""Smoketest for window_watchdog.py — exercises the pure helpers without
starting the blocking poll loop. Run: python scripts/window_watchdog_smoketest.py
Prints per-check lines + 'ALL PASS'; non-zero exit on first failure."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import window_watchdog as ww  # noqa: E402

n = 0


def check(cond, label):
    global n
    n += 1
    if not cond:
        print(f"[fail] {label}")
        sys.exit(1)
    print(f"[ok] {label}")


# 1. should_alert: idle past threshold, not yet alerted -> True
check(ww.should_alert(now=1000.0, mtime=600.0, idle_seconds=300, already_alerted=False),
      "alerts when idle beyond threshold")

# 2. should_alert: within threshold -> False
check(not ww.should_alert(now=1000.0, mtime=800.0, idle_seconds=300, already_alerted=False),
      "no alert within threshold")

# 3. should_alert: already alerted -> False (no repeat for same stall)
check(not ww.should_alert(now=1000.0, mtime=600.0, idle_seconds=300, already_alerted=True),
      "no repeat alert for same stall")

# 4. exactly at threshold -> True (>=)
check(ww.should_alert(now=1000.0, mtime=700.0, idle_seconds=300, already_alerted=False),
      "alerts exactly at threshold")

# 5. pick_active_transcript: picks newest by mtime
with tempfile.TemporaryDirectory() as d:
    dd = Path(d)
    old = dd / "old.jsonl"
    new = dd / "new.jsonl"
    old.write_text("{}\n", encoding="utf8")
    time.sleep(0.02)
    new.write_text("{}\n", encoding="utf8")
    # force ordering deterministically
    import os
    os.utime(old, (1000, 1000))
    os.utime(new, (2000, 2000))
    picked = ww.pick_active_transcript(dd)
    check(picked is not None and picked.name == "new.jsonl", "picks newest transcript")

# 6. pick_active_transcript: empty dir -> None
with tempfile.TemporaryDirectory() as d:
    check(ww.pick_active_transcript(Path(d)) is None, "empty dir yields None")

# 7. default_project_dir flattens path separators and colon
pd = ww.default_project_dir()
check(":" not in pd.name and "projects" in str(pd.parent), "project slug flattens drive/sep")

# 8. notify never raises
try:
    ww.notify("smoketest -- please ignore")
    raised = False
except Exception:
    raised = True
check(not raised, "notify never raises")

# 9. arg parser defaults
args = ww.build_arg_parser().parse_args([])
check(args.idle == 300.0 and args.poll == 30.0, "arg defaults idle=300 poll=30")

print(f"\nALL PASS ({n} checks)")
