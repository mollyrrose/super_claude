#!/usr/bin/env python3
"""CLI wrapper around curator_core.mark_drained for Claude to invoke.

Why this exists: the curator UserPromptSubmit hook injects a directive
telling Claude to clear the queue after draining. Claude executes that
as a one-off `python -c "from claude_code_integration.curator_core ..."`,
which fails with ModuleNotFoundError because the hermes-agent root is
not on sys.path for ad-hoc python invocations. This wrapper sets sys.path
the same way curator_prompt_hook.py does and exposes mark_drained as a
stdin→stdout JSON contract.

Input  (stdin, JSON): {"session_ids": ["...", "..."], "candidates_written": 0}
Output (stdout, JSON): {"removed": N, "remaining": M, "last_drain_at": "..."}
Errors (stderr + exit 1): {"error": "...", "kind": "..."}
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from curator_core import mark_drained  # noqa: E402


def main() -> int:
    try:
        raw = sys.stdin.read()
    except Exception as exc:  # pragma: no cover — stdin failure
        print(json.dumps({"error": str(exc), "kind": "stdin_read"}), file=sys.stderr)
        return 1

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(
            json.dumps({"error": f"invalid JSON: {exc}", "kind": "bad_json", "raw": raw[:200]}),
            file=sys.stderr,
        )
        return 1

    if not isinstance(payload, dict):
        print(json.dumps({"error": "payload must be a JSON object", "kind": "bad_shape"}), file=sys.stderr)
        return 1

    session_ids = payload.get("session_ids")
    candidates_written = payload.get("candidates_written", 0)

    if not isinstance(session_ids, list) or not all(isinstance(s, str) for s in session_ids):
        print(
            json.dumps({"error": "session_ids must be a list of strings", "kind": "bad_shape"}),
            file=sys.stderr,
        )
        return 1
    if not isinstance(candidates_written, int):
        print(
            json.dumps({"error": "candidates_written must be an int", "kind": "bad_shape"}),
            file=sys.stderr,
        )
        return 1

    try:
        result = mark_drained(session_ids, candidates_written)
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({"error": str(exc), "kind": "mark_drained_raised"}), file=sys.stderr)
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
