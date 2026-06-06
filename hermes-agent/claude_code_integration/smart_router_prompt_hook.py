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

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from smart_router_rules import classify_prompt, format_suggestion  # noqa: E402

MAX_INJECTED_CHARS = 400


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
        suggestion = classify_prompt(prompt_text)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 0

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
