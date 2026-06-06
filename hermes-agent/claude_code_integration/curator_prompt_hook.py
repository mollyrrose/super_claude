#!/usr/bin/env python3
"""Claude Code UserPromptSubmit-hook — surface curate + maintenance
reminders.

Fires on every user prompt. Two responsibilities:

1. **Curate reminder.** When the session queue passes its threshold,
   inject an imperative directive telling Claude to drain the queue
   silently before responding (see curator_core.should_remind).

2. **Skill maintenance.** When more than
   HERMES_SKILL_MAINTENANCE_INTERVAL_DAYS (default 7) have passed since
   the last maintenance pass, run it deterministically:

   - Mark unused-for-30d skills as ``stale``.
   - Move unused-for-90d skills to ~/.claude/skills-archive/ (no
     deletion — fully recoverable).
   - Pinned skills (`pinned: true` in frontmatter) and curator
     infrastructure are exempt.

   If anything was archived or marked stale, append a one-line summary
   to whatever reminder is being injected. Silent when nothing happened.

Stdout convention for UserPromptSubmit hooks:
  - Empty / non-JSON: no-op.
  - JSON with ``hookSpecificOutput.additionalContext``: string is
    prepended to the assistant's view of the prompt.

This hook never blocks the prompt — failures fall through to no-op.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from curator_core import should_remind  # noqa: E402
from skill_lifecycle import (  # noqa: E402
    maintenance_summary_text,
    run_lifecycle_pass,
    should_run_maintenance,
)


def main() -> int:
    try:
        _ = sys.stdin.read()  # payload unused
    except Exception:
        return 0

    pieces: list[str] = []

    # 1. Curate reminder.
    try:
        curate_text = should_remind()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        curate_text = None
    if curate_text:
        pieces.append(curate_text)

    # 2. Maintenance pass (rate-limited internally).
    try:
        if should_run_maintenance():
            result = run_lifecycle_pass()
            summary = maintenance_summary_text(result)
            if summary:
                pieces.append(summary)
    except Exception:
        traceback.print_exc(file=sys.stderr)

    if not pieces:
        return 0

    decision = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n\n".join(pieces),
        }
    }
    print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
