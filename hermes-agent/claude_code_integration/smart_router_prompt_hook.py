#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook — smart-router skill suggestion.

Reads the JSON payload Claude Code passes on stdin, classifies the user's
prompt via smart_router_rules.classify_prompt, and (if confident) emits a
hookSpecificOutput.additionalContext JSON to surface the suggested skill.

Designed to run side-by-side with curator_prompt_hook.py — Claude Code
concatenates the additionalContext from every registered UserPromptSubmit
hook.

Failures are silent: any exception → exit 0 with no output. A broken router
must never block the user's prompt.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from smart_router_rules import classify_prompt, format_suggestion  # noqa: E402

MAX_INJECTED_CHARS = 400

EVAL_LOG_PATH = (
    Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    / ".smart_router_eval.jsonl"
)


def _slugify_project(cwd: str) -> str:
    """Turn a working directory into the slug Claude Code uses for ~/.claude/projects/<slug>/.

    Matches the observed naming pattern: ``:``, ``\\``, ``/``, ``_``, and
    spaces all become ``-``. Case is preserved.
    """
    if not cwd:
        return ""
    out = cwd
    for ch in (":", "\\", "/", "_", " "):
        out = out.replace(ch, "-")
    return out


def _log_eval_row(prompt_text: str, suggestion, payload: dict) -> None:
    """Append one hashed eval row to ~/.claude/.smart_router_eval.jsonl.

    Privacy: stores sha256(prompt)[:16] and a word count; never the body.
    Caller MUST wrap this in try/except — a logger failure must never
    block the user's prompt (the hook's load-bearing invariant).
    """
    sid = payload.get("session_id") or ""
    cwd = payload.get("cwd") or ""
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_id": sid,
        "project": _slugify_project(cwd),
        "prompt_hash": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:16],
        "prompt_len_words": len(prompt_text.split()),
        "suggested_skill_or_null": suggestion.skill if suggestion is not None else None,
        "invoked_skill_or_null": None,
    }
    EVAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVAL_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _extract_prompt(raw: str) -> str:
    """Pull the user prompt out of the stdin payload.

    Claude Code passes a JSON object with the prompt field. Be defensive:
    accept multiple shapes, fall back to raw stdin when JSON parsing fails.
    """
    if not raw:
        return ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw  # treat raw stdin as prompt text
    if not isinstance(payload, dict):
        return ""
    for key in ("prompt", "user_prompt", "userPrompt", "text"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def main() -> int:
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0

    prompt_text = _extract_prompt(raw)
    if not prompt_text.strip():
        return 0

    try:
        payload_obj = json.loads(raw) if raw else {}
        if not isinstance(payload_obj, dict):
            payload_obj = {}
    except json.JSONDecodeError:
        payload_obj = {}

    try:
        suggestion = classify_prompt(prompt_text)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 0

    try:
        _log_eval_row(prompt_text, suggestion, payload_obj)
    except Exception:
        pass  # logger must never block the prompt

    if suggestion is None:
        return 0

    text = format_suggestion(suggestion)
    if len(text) > MAX_INJECTED_CHARS:
        text = text[: MAX_INJECTED_CHARS - 3] + "..."

    decision = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": text,
        }
    }
    print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
