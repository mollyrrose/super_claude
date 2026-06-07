#!/usr/bin/env python3
"""UserPromptSubmit hook: if a qMin/qRev is pending for this session, instruct Claude
to silently run it before answering the user prompt.

Mirrors the curator_prompt_hook.py pattern: stdout contains a JSON object with
`hookSpecificOutput.additionalContext` so Claude Code injects it into the model's view
for the upcoming turn. The actual review runs in Claude's own session (Pro/Max subscription).

Silent no-op if QREV_AUTO_LEVEL<2 or no pending flag. Always exits 0.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

STATE_FILE = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))) / ".qrev_auto_state.json"
MARK_DONE = str(Path(__file__).parent / "qrev_mark_done.py")


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def load_state() -> dict:
    try:
        if STATE_FILE.exists():
            d = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}


def emit(context: str) -> None:
    out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                  "additionalContext": context}}
    sys.stdout.write(json.dumps(out))


def main() -> int:
    level = env_int("QREV_AUTO_LEVEL", 3)
    if level < 2:
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    sid = payload.get("session_id") or ""
    if not sid:
        return 0

    state = load_state()
    entry = state.get(sid)
    if not entry:
        return 0

    pending_qrev = bool(entry.get("pending_qrev")) and level >= 3
    pending_qmin = bool(entry.get("pending_qmin"))
    if not (pending_qrev or pending_qmin):
        return 0

    kind = "qrev" if pending_qrev else "qmin"
    skill = "/qRev" if pending_qrev else "/qMin"
    edits = entry.get(f"edits_since_{kind}", 0)
    loc   = entry.get(f"loc_since_{kind}", 0)

    if pending_qrev:
        scope_note = ("Full 3-pass exhaustive review (qMin → Phase A → exhaustive agent fleet). "
                      "Wall-clock 15–30 min — fine, subscription covers it.")
    else:
        scope_note = ("5-axis qMin lens only (minimal scope / correctness / security / maintainability / quality). "
                      "Single LLM pass, ~15–60s.")

    context = (
        f"[qrev-auto] {edits} Write/Edit events ({loc} LOC) accumulated since the last review on "
        f"this session - threshold tripped. BEFORE responding to the user's prompt below, execute "
        f"{skill} on the uncommitted diff (staged + unstaged). {scope_note} The skill's SKILL.md "
        f"now includes a standing auto-fix policy: after the verdict/report, apply the fixes "
        f"inline (no confirmation step) and log each as a one-liner. Output order MUST be: "
        f"(1) a status header line `- auto-{kind}: <verdict>, <N> findings`, "
        f"(2) the full skill output (report + auto-fix `- fix ...` / `- skip ...` lines), "
        f"(3) call the reset CLI by piping "
        f"{{\"session_id\": \"{sid}\", \"kind\": \"{kind}\"}} as JSON on stdin to: "
        f"\"{sys.executable}\" \"{MARK_DONE}\", "
        f"(4) then answer the user's actual prompt below. "
        f"If the working tree has no changes (clean), skip the review, just call the reset CLI "
        f"with kind={kind}, no status header in that case. "
        f"Never block on this - the user's request always takes priority over a review failure."
    )
    emit(context)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
