#!/usr/bin/env python3
"""CLI: append one structured decision row to ~/.claude/.decision_log.jsonl.

Why this exists: the global CLAUDE.md "Decision log" convention tells Claude to
record non-trivial / hard-to-reverse decisions in a human-readable place
(per-project docs/decisions/log.md or the memory system) AND, for the future
learned-predictor data layer (the FabricPC PCN evaluation), to ALSO append a
machine-readable row to a central JSONL stream. This wrapper is the deterministic
writer for that stream, so every row has a consistent schema — the same role
mark_drained_cli.py plays for the curator and qrev_mark_done.py plays for the
qRev verdict stream.

It is pure logging: no ML, no model, no network, append-only, reversible (delete
the JSONL to reset). It sits alongside the two streams already collected
(.smart_router_eval.jsonl, .qrev_verdict_log.jsonl) as the third candidate input
for any future learned component.

Input  (stdin, JSON object):
    {
      "title": "<short decision title>",         # required, non-empty
      "decision": "<what was decided>",          # required, non-empty
      "why": "<reason>",                          # optional
      "rejected_alternatives": "<dropped + why>", # optional
      "revisit_if": "<condition that reopens it>", # optional -> future label source
      "project": "<repo/project name>",          # optional (defaults to $CLAUDE_PROJECT or cwd)
      "outcome": "open|held|reversed",           # optional, default "open"
      "session_id": "<sid>",                     # optional
      "ts": "<ISO8601>"                          # optional, generated if absent
    }
Output (stdout, JSON): {"logged": true, "path": "<jsonl>", "ts": "<iso>"}
Errors (stderr + exit 1): {"error": "...", "kind": "..."}
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _log_path() -> Path:
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    return base / ".decision_log.jsonl"


_VALID_OUTCOMES = ("open", "held", "reversed")


def append_decision_log(payload: dict) -> dict:
    """Validate `payload`, append one row, return the written row.

    Raises ValueError on a bad payload (missing/empty title or decision, or an
    invalid outcome). Importable so tests can call it directly.
    """
    title = payload.get("title")
    decision = payload.get("decision")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a non-empty string")
    if not isinstance(decision, str) or not decision.strip():
        raise ValueError("decision must be a non-empty string")

    outcome = payload.get("outcome", "open")
    if outcome not in _VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {_VALID_OUTCOMES}")

    ts = payload.get("ts")
    if not isinstance(ts, str) or not ts.strip():
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    project = payload.get("project")
    if not isinstance(project, str) or not project.strip():
        project = os.environ.get("CLAUDE_PROJECT") or Path.cwd().name

    row = {
        "ts": ts,
        "project": project,
        "title": title.strip(),
        "decision": decision.strip(),
        "why": (payload.get("why") or "").strip() if isinstance(payload.get("why"), str) else "",
        "rejected_alternatives": (
            payload.get("rejected_alternatives") or ""
        ).strip()
        if isinstance(payload.get("rejected_alternatives"), str)
        else "",
        "revisit_if": (payload.get("revisit_if") or "").strip()
        if isinstance(payload.get("revisit_if"), str)
        else "",
        "outcome": outcome,
        "session_id": payload.get("session_id")
        if isinstance(payload.get("session_id"), str)
        else None,
    }

    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def main() -> int:
    try:
        raw = sys.stdin.read()
    except Exception as exc:  # pragma: no cover - stdin failure
        print(json.dumps({"error": str(exc), "kind": "stdin_read"}), file=sys.stderr)
        return 1

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(
            json.dumps(
                {"error": f"invalid JSON: {exc}", "kind": "bad_json", "raw": raw[:200]}
            ),
            file=sys.stderr,
        )
        return 1

    if not isinstance(payload, dict):
        print(
            json.dumps({"error": "payload must be a JSON object", "kind": "bad_shape"}),
            file=sys.stderr,
        )
        return 1

    try:
        row = append_decision_log(payload)
    except ValueError as exc:
        print(json.dumps({"error": str(exc), "kind": "bad_shape"}), file=sys.stderr)
        return 1
    except OSError as exc:
        print(json.dumps({"error": str(exc), "kind": "write_failed"}), file=sys.stderr)
        return 1

    print(json.dumps({"logged": True, "path": str(_log_path()), "ts": row["ts"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
