#!/usr/bin/env python3
"""Claude Code Stop-hook — enqueue session metadata and update skill
usage counters.

Two responsibilities, both deterministic and fast:

1. Append a record to ~/.claude/.hermes_curator_queue.json so the
   curator can later analyse the transcript for reusable patterns.
2. Parse the transcript for Skill tool invocations and bump per-skill
   usage counters in ~/.claude/.hermes_skill_state.json.

Neither step calls an LLM. Cost: zero. Time: milliseconds. Stderr
carries diagnostics that Claude Code surfaces in its log.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from curator_core import enqueue_session  # noqa: E402
from skill_lifecycle import (  # noqa: E402
    parse_skill_uses_from_transcript,
    record_active_day,
    record_skill_uses,
)


def main() -> int:
    try:
        payload_raw = sys.stdin.read()
    except Exception:
        return 0
    if not payload_raw.strip():
        return 0
    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError as e:
        print(f"[hermes-curator/stop] bad JSON: {e}", file=sys.stderr)
        return 0

    transcript_path_str = payload.get("transcript_path")
    session_id = payload.get("session_id")
    if not transcript_path_str:
        return 0
    transcript_path = Path(transcript_path_str)

    # 1. Enqueue session for later curate analysis.
    try:
        enqueue_result = enqueue_session(session_id, transcript_path)
    except Exception:
        print("[hermes-curator/stop] enqueue error:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        enqueue_result = {"status": "error"}

    status = enqueue_result.get("status", "?")
    if status == "enqueued":
        print(
            f"[hermes-curator/stop] enqueued — queue_size={enqueue_result['queue_size']}"
            f" user_turns={enqueue_result['user_turns']}",
            file=sys.stderr,
        )
    elif status == "skipped":
        print(
            f"[hermes-curator/stop] enqueue skipped — {enqueue_result.get('reason')}",
            file=sys.stderr,
        )

    # 2. Record skill-usage signals from the transcript. Safe to run even
    #    when the enqueue path skipped (a session may still have used a
    #    skill or two even if it was below the curate-enqueue threshold).
    try:
        used = parse_skill_uses_from_transcript(transcript_path)
        if used:
            usage_result = record_skill_uses(used)
            distinct = sorted(set(used))
            head = ", ".join(distinct[:4])
            more = f" (+{len(distinct) - 4} more)" if len(distinct) > 4 else ""
            print(
                f"[hermes-curator/stop] tracked {len(used)} skill use(s) "
                f"across {len(distinct)} skill(s): {head}{more} "
                f"(state now tracks {usage_result['tracked_total']} skill(s))",
                file=sys.stderr,
            )
    except Exception:
        print("[hermes-curator/stop] usage tracking error:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    # 3. Mark today as an active day. Always fires — even if nothing
    #    else above did. This is the calendar the lifecycle uses to
    #    measure "30 days" / "90 days" as 30/90 *active* days rather
    #    than calendar days, so a long break does not age skills.
    try:
        active_result = record_active_day()
        if active_result.get("changed"):
            print(
                f"[hermes-curator/stop] active day marked: "
                f"{active_result['today']} (total {active_result['total_active_days']})",
                file=sys.stderr,
            )
    except Exception:
        print("[hermes-curator/stop] active-day record error:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
