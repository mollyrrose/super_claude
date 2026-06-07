#!/usr/bin/env python3
"""PostToolUse hook: count Write/Edit events per session, set pending flags when thresholds tripped.

Companion to qrev_auto_inject.py (UserPromptSubmit) and qrev_mark_done.py (CLI reset).

State lives in ~/.claude/.qrev_auto_state.json:
{
  "<session_id>": {
    "edits_since_qmin":  int,
    "loc_since_qmin":    int,
    "edits_since_qrev":  int,
    "loc_since_qrev":    int,
    "pending_qmin":      bool,
    "pending_qrev":      bool,
    "last_qmin_at":      iso8601 or null,
    "last_qrev_at":      iso8601 or null,
    "first_seen_at":     iso8601,
    "last_event_at":     iso8601
  }
}

Silent no-op if tool isn't Write/Edit or there's no session_id. Always exits 0.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))) / ".qrev_auto_state.json"
STALE_DAYS = 30

DEFAULTS = {
    "QREV_AUTO_LEVEL":      "3",     # 0=off, 1=static-only, 2=+qMin, 3=+qRev
    "QREV_AUTO_QMIN_EDITS": "50",
    "QREV_AUTO_QMIN_LOC":   "5000",
    "QREV_AUTO_QREV_EDITS": "250",
    "QREV_AUTO_QREV_LOC":   "25000",
}


def env_int(name: str) -> int:
    raw = os.environ.get(name, DEFAULTS[name])
    try:
        return int(raw)
    except ValueError:
        return int(DEFAULTS[name])


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_state() -> dict:
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_state(data: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(data, indent=0), encoding="utf-8")
    except Exception:
        pass


def estimate_loc(tool_name: str, tool_input: dict) -> int:
    """Best-effort line count for the change."""
    if tool_name == "Write":
        content = tool_input.get("content", "") or ""
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "") or ""
    else:
        return 0
    if not content:
        return 0
    return content.count("\n") + (0 if content.endswith("\n") else 1)


def prune_stale(data: dict) -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - STALE_DAYS * 86400
    dead = []
    for sid, entry in data.items():
        ts = entry.get("last_event_at") or entry.get("first_seen_at") or ""
        try:
            t = datetime.fromisoformat(ts).timestamp()
        except Exception:
            t = 0
        if t and t < cutoff:
            dead.append(sid)
    for sid in dead:
        data.pop(sid, None)


def main() -> int:
    level = env_int("QREV_AUTO_LEVEL")
    if level <= 1:
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Write", "Edit"):
        return 0

    session_id = payload.get("session_id") or ""
    if not session_id:
        return 0

    tool_input = payload.get("tool_input") or {}
    loc = estimate_loc(tool_name, tool_input)
    nowi = now_iso()

    data = load_state()
    entry = data.get(session_id)
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

    entry["edits_since_qmin"] = entry.get("edits_since_qmin", 0) + 1
    entry["loc_since_qmin"]   = entry.get("loc_since_qmin", 0) + loc
    entry["edits_since_qrev"] = entry.get("edits_since_qrev", 0) + 1
    entry["loc_since_qrev"]   = entry.get("loc_since_qrev", 0) + loc
    entry["last_event_at"]    = nowi

    qrev_edits = env_int("QREV_AUTO_QREV_EDITS")
    qrev_loc   = env_int("QREV_AUTO_QREV_LOC")
    qmin_edits = env_int("QREV_AUTO_QMIN_EDITS")
    qmin_loc   = env_int("QREV_AUTO_QMIN_LOC")

    if level >= 3 and (entry["edits_since_qrev"] >= qrev_edits or entry["loc_since_qrev"] >= qrev_loc):
        entry["pending_qrev"] = True
        entry["pending_qmin"] = False
    elif level >= 2 and (entry["edits_since_qmin"] >= qmin_edits or entry["loc_since_qmin"] >= qmin_loc):
        entry["pending_qmin"] = True

    data[session_id] = entry
    prune_stale(data)
    save_state(data)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
