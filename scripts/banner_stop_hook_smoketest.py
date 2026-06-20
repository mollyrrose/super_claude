#!/usr/bin/env python3
"""Smoketest for banner_stop_hook.py. Run:
    python scripts/banner_stop_hook_smoketest.py
Prints per-check lines + 'ALL PASS'; non-zero exit on first failure."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Isolate state file in a temp config dir.
_tmp = tempfile.mkdtemp(prefix="bannerhook-")
os.environ["CLAUDE_CONFIG_DIR"] = _tmp

import banner_stop_hook as bh  # noqa: E402

n = 0


def check(cond, label):
    global n
    n += 1
    if not cond:
        print(f"[fail] {label}")
        sys.exit(1)
    print(f"[ok] {label}")


BANNER = (
    "*********************************\n"
    "*    USER INPUT REQUIRED        *\n"
    "*********************************"
)

# --- has_banner ---
check(bh.has_banner("blah\n" + BANNER), "has_banner detects banner")
check(not bh.has_banner("no banner here"), "has_banner false when absent")

# --- looks_like_awaiting_input ---
check(bh.looks_like_awaiting_input("Which option do you want?"),
      "question mark on last line -> awaiting")
check(bh.looks_like_awaiting_input("Some text.\nShall I proceed with the deploy?"),
      "trailing question -> awaiting")
check(bh.looks_like_awaiting_input("Choose A or B. Yes/No?"),
      "approval phrase -> awaiting")
check(not bh.looks_like_awaiting_input("Done. Pushed to main."),
      "plain statement -> not awaiting")
check(not bh.looks_like_awaiting_input(
        "Here is how the regex matches lazily.\nThat is the explanation."),
      "explanatory, no trailing ? -> not awaiting")

# --- Hungarian conditional false positives (the bug this fix targets) ---
check(not bh.looks_like_awaiting_input(
        "Ha szeretnéd, később megcsináljuk — de most semmi nem ragad bent, lezárhatod."),
      "HU conditional 'Ha szeretnéd ... lezárhatod.' -> NOT awaiting")
check(not bh.looks_like_awaiting_input("Ha minden ok, mehet a deploy."),
      "HU conditional '...mehet a deploy.' -> NOT awaiting")
check(not bh.looks_like_awaiting_input("Jóváhagyom a tervet és bezárom."),
      "HU statement 'Jóváhagyom ...' -> NOT awaiting")
# --- but the same verbs in explicit question form DO await ---
check(bh.looks_like_awaiting_input("Tehát: kérsz még valamit, vagy csak bezárod?"),
      "HU trailing question -> awaiting")
check(bh.looks_like_awaiting_input("Kész minden. Mehet? Mondd meg."),
      "HU 'Mehet?' mid-line question form -> awaiting")
check(bh.looks_like_awaiting_input("Melyik opciót válasszam?"),
      "HU 'Melyik ...?' -> awaiting")

# --- decide: awaiting + no banner -> block (first time) ---
state = {}
action, reason, state = bh.decide("Which way should we go?", "sessA", state)
check(action == "block" and "USER INPUT REQUIRED" in reason, "blocks when awaiting w/o banner")
check(state["sessA"]["blocks"] == 1, "block counter increments")

# --- decide: awaiting WITH banner -> allow + reset ---
action, reason, state = bh.decide("Which way?\n" + BANNER, "sessA", state)
check(action == "allow", "allows when banner present")
check(state["sessA"]["blocks"] == 0, "counter resets on clean turn")

# --- decide: plain statement -> allow ---
action, reason, state = bh.decide("All done.", "sessB", state)
check(action == "allow", "allows plain statement")

# --- loop guard: cap blocks then warn ---
state = {}
a1, _, state = bh.decide("Pick one?", "sessC", state)
a2, _, state = bh.decide("Pick one?", "sessC", state)
a3, _, state = bh.decide("Pick one?", "sessC", state)
check(a1 == "block" and a2 == "block" and a3 == "warn", "block cap -> warn after 2")

# --- extract_last_assistant_text from a transcript ---
with tempfile.TemporaryDirectory() as d:
    tp = Path(d) / "t.jsonl"
    rows = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "hi"}]}},
        {"type": "assistant", "message": {"content": [{"type": "thinking", "thinking": "x"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Final answer: which option?"}]}},
    ]
    tp.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf8")
    txt = bh.extract_last_assistant_text(tp)
    check("which option?" in txt, "extracts last assistant text block")

# --- extract returns '' on unreadable ---
check(bh.extract_last_assistant_text(Path(_tmp) / "nope.jsonl") == "", "missing transcript -> empty")

# --- disable kill switch makes main a no-op (returns 0) ---
os.environ["BANNER_HOOK_DISABLE"] = "1"
check(bh.main() == 0, "disable kill switch -> no-op exit 0")
del os.environ["BANNER_HOOK_DISABLE"]

print(f"\nALL PASS ({n} checks)")
