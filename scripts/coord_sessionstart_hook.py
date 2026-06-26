#!/usr/bin/env python3
"""SessionStart hook: the moment a Claude Code window opens on a repo, register
it on the shared coordination board and tell it the cross-window protocol -- so
it knows what to do WITHOUT the user pasting anything.

This is the "knows what to do at startup" piece. The standing behaviour itself
lives in CLAUDE.md (loaded every session); this hook (a) registers the window so
it is immediately visible to the others even before the first prompt, and (b)
injects a compact standing directive + the LIVE board, so on its very first turn
the window already handles its inbox and -- if other live windows are present --
starts its own self-paced relay loop, with no pasted command.

Contract: read JSON payload from stdin ({session_id, cwd, source, ...}); emit
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext":
"..."}}. Silent no-op on missing/malformed input; never blocks startup.

Kill switch: COORD_DISABLE=1 (whole feature off). COORD_AUTOLOOP=0 keeps the
per-turn mailbox handling but drops the "start a self-paced loop" suggestion.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load_coord():
    try:
        spec = importlib.util.spec_from_file_location("_coord_mod", str(_HERE / "coord.py"))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _directive(tick: dict) -> str:
    others = tick.get("others") or []
    reqs = tick.get("requests_for_me") or []
    answers = tick.get("answers_for_me") or []
    autoloop = os.environ.get("COORD_AUTOLOOP") != "0"

    lines = [
        "[coordination] You are registered on this repo's shared board "
        "(~/.claude/.coord). Full protocol: CLAUDE.md \"Cross-window coordination\". "
        "Standing behaviour, NO user action and NO pasted command needed:",
        "- Each turn, auto-handle your inbox: `python ~/.claude/scripts/coord.py inbox`. "
        "Answer requests addressed to you with `coord.py reply <id> --note \"...\"`; "
        "read answers to your own questions and `coord.py ack <id>`.",
        "- Claim a file before editing it (`coord.py claim <path>`); post cross-branch "
        "handoffs with `coord.py request --to <sid|branch> --note \"...\"`.",
        "- DECISION-GATE: never run an irreversible op (merge to main, push, rebase of "
        "live files, deleting data) autonomously -- propose the exact command back via "
        "`coord.py reply` and stop for the user with the USER-INPUT banner.",
        "- SAME PROJECT ONLY: the board is per-repo, so you only ever see/act on "
        "same-repo windows; never touch another project's files.",
    ]
    if others:
        summary = "; ".join(
            f"[{o.get('session')}] {o.get('branch') or '?'} (\"{o.get('note') or '-'}\")"
            for o in others
        )
        lines.append(f"- LIVE NOW: {len(others)} other window(s): {summary}.")
        if reqs:
            lines.append(f"- {len(reqs)} request(s) already addressed to you -- handle them this turn.")
        if answers:
            lines.append(f"- {len(answers)} answer(s) to your questions are waiting -- read + ack.")
        if autoloop:
            lines.append(
                "- Because other windows are live and handoffs may arrive while you sit "
                "idle, START a self-paced relay loop yourself now via the /loop skill "
                "(check `coord.py inbox`, reply, ack; honour the DECISION-GATE) so you "
                "coordinate without being prompted. Do NOT wait for the user to paste anything.")
    return "\n".join(lines)


def main() -> int:
    if os.environ.get("COORD_DISABLE") == "1":
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    session = payload.get("session_id") or os.environ.get("CLAUDE_SESSION_ID")
    cwd = payload.get("cwd") or None
    if not session:
        return 0

    coord = _load_coord()
    if coord is None:
        return 0
    try:
        tick = coord.hook_tick(session, cwd=cwd, note="session start")
    except Exception:
        return 0

    ctx = _directive(tick if isinstance(tick, dict) else {})
    if ctx:
        sys.stdout.write(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": ctx,
            }
        }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
