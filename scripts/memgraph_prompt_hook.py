#!/usr/bin/env python3
"""memgraph_prompt_hook.py -- UserPromptSubmit hook: trigger memory-graph ingestion.

Level-5 ("always-on") memory layer, part 2 of 2. Reads the queue written by
memgraph_sessionend.py; when the drain threshold is reached (>= 2 pending
sessions, or the oldest pending entry is >= 48 h old), injects a small
additionalContext block instructing Claude to silently run the
memgraph-ingest skill (which extracts evergreen facts into the memory dir
and refreshes the graph) before answering the user's prompt.

Runs inside hook_dispatch.py's UserPromptSubmit chain -- same contract as
curator_prompt_hook.py: emit ONE JSON object with
hookSpecificOutput.additionalContext, or nothing; exit 0 always; silent
no-op on any internal error. Injection is once per session (guarded via
~/.claude/.memgraph_state.json) so a long session is not renagged.

Kill switch: MEMGRAPH_DISABLE=1, or remove ("memgraph_prompt_hook", ...)
from REGISTRY in hook_dispatch.py.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_BASE = Path(os.environ.get("CLAUDE_CONFIG_DIR", "") or (Path.home() / ".claude"))
QUEUE_PATH = Path(os.environ.get("MEMGRAPH_QUEUE", "") or _BASE / ".memgraph_queue.json")
STATE_PATH = Path(os.environ.get("MEMGRAPH_STATE", "") or _BASE / ".memgraph_state.json")

DRAIN_MIN_SESSIONS = int(os.environ.get("MEMGRAPH_MIN_SESSIONS", "2"))
DRAIN_MAX_AGE_HOURS = float(os.environ.get("MEMGRAPH_MAX_AGE_HOURS", "48"))


def _emit(context: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            }
        )
    )


def _parse_ts(ts_str: str) -> "datetime | None":
    """Parse an ISO timestamp, coercing naive timestamps to UTC."""
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            # Naive timestamp (written by an older version) -- assume UTC to
            # avoid TypeError when subtracting from a timezone-aware now.
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def main() -> int:
    if os.environ.get("MEMGRAPH_DISABLE") == "1":
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        session_id = str(payload.get("session_id") or "").strip()

        # Fast path: read state FIRST -- it is a small fixed-size file, and the
        # common case (already injected this session) exits after one read instead
        # of two (the queue file grows over time as sessions accumulate).
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if not isinstance(state, dict):
                state = {}
        except Exception:
            state = {}
        if session_id and state.get("last_inject_session") == session_id:
            return 0  # already nudged this session

        # State guard passed -- now read the (larger) queue.
        try:
            queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return 0
        if not isinstance(queue, list) or not queue:
            return 0

        now = datetime.now(timezone.utc)
        oldest_age_h = 0.0
        valid_count = 0
        for entry in queue:
            if not isinstance(entry, dict):
                continue
            valid_count += 1
            dt = _parse_ts(str(entry.get("ts", "")))
            if dt is not None:
                age = (now - dt).total_seconds() / 3600.0
                oldest_age_h = max(oldest_age_h, age)
        if valid_count < DRAIN_MIN_SESSIONS and oldest_age_h < DRAIN_MAX_AGE_HOURS:
            return 0

        # Threshold met. Persist the guard BEFORE emitting so that a write
        # failure causes a silent skip (retry next session) rather than emitting
        # without persisting -- which would re-inject on EVERY subsequent prompt
        # for the rest of the session.
        state["last_inject_session"] = session_id
        state["last_inject_ts"] = now.isoformat(timespec="seconds")
        try:
            STATE_PATH.write_text(
                json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            return 0  # failed to persist guard -- skip nudge, retry next session
        _emit(
            "[memgraph] "
            f"{valid_count} session(s) queued for memory ingestion. Before answering "
            "the user's prompt, silently invoke the memgraph-ingest skill (Skill tool, "
            'skill: "memgraph-ingest") to extract evergreen facts into the memory dir '
            "and refresh the memory graph. Never block or surface errors from it; if "
            "it fails, continue with the user's prompt."
        )
    except BaseException:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
