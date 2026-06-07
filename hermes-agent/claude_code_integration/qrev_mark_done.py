#!/usr/bin/env python3
"""CLI reset for qrev_edit_counter state. Claude calls this after running an auto-qMin / auto-qRev.

Stdin JSON: {"session_id": "<sid>", "kind": "qmin" | "qrev"}
Stdout JSON: {"reset": "<kind>", "session_id": "<sid>", "ts": "<iso>"}
Exit non-zero on bad input or write failure.

Mirrors the mark_drained_cli.py contract used by the hermes-curator system.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))) / ".qrev_auto_state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_state() -> dict:
    try:
        if STATE_FILE.exists():
            d = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}


def save_state(data: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=0), encoding="utf-8")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        sys.stderr.write(f"qrev_mark_done: bad stdin json: {exc}\n")
        return 2

    sid = payload.get("session_id") or ""
    kind = payload.get("kind") or ""
    if not sid or kind not in ("qmin", "qrev"):
        sys.stderr.write('qrev_mark_done: need {"session_id": "...", "kind": "qmin"|"qrev"}\n')
        return 2

    nowi = now_iso()
    data = load_state()
    entry = data.get(sid)
    if entry is None:
        entry = {
            "edits_since_qmin": 0,
            "loc_since_qmin": 0,
            "edits_since_qrev": 0,
            "loc_since_qrev": 0,
            "pending_qmin": False,
            "pending_qrev": False,
            "last_qmin_at": None,
            "last_qrev_at": None,
            "first_seen_at": nowi,
            "last_event_at": nowi,
        }

    if kind == "qmin":
        entry["edits_since_qmin"] = 0
        entry["loc_since_qmin"]   = 0
        entry["pending_qmin"]     = False
        entry["last_qmin_at"]     = nowi
    else:  # qrev resets both
        entry["edits_since_qmin"] = 0
        entry["loc_since_qmin"]   = 0
        entry["edits_since_qrev"] = 0
        entry["loc_since_qrev"]   = 0
        entry["pending_qmin"]     = False
        entry["pending_qrev"]     = False
        entry["last_qrev_at"]     = nowi
        entry["last_qmin_at"]     = nowi  # qRev includes qMin

    entry["last_event_at"] = nowi
    data[sid] = entry
    save_state(data)

    sys.stdout.write(json.dumps({"reset": kind, "session_id": sid, "ts": nowi}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        sys.stderr.write(f"qrev_mark_done: {exc}\n")
        sys.exit(1)
