#!/usr/bin/env python3
"""banner_stop_hook.py — Stop hook that enforces the USER INPUT REQUIRED banner.

The global ~/.claude/CLAUDE.md rule: whenever a reply ends with a question, a
choice, or an approval gate that awaits the user, the LAST line MUST be the
`USER INPUT REQUIRED` ASCII banner. The model sometimes forgets. This Stop hook
catches that: when the final assistant message *looks like it is awaiting user
input* but does NOT contain the banner, it returns a Stop "block" decision so
Claude Code continues the turn and the model adds the banner (plus the
plain-language summary the same rule requires).

Design constraints (all load-bearing):
- CONSERVATIVE trigger. A false positive forces a spurious continue, which is
  annoying, so the heuristic only fires on a strong "awaiting input" signal
  (last non-empty line ends with '?', or an explicit approval phrase near the
  end) AND the banner being absent.
- LOOP GUARD. State in ~/.claude/.banner_hook_state.json caps blocks per session
  (default 2). After the cap, the hook stops blocking and only warns on stderr —
  so a model that keeps omitting the banner can never trap the turn in a loop.
- SILENT NO-OP on missing/malformed stdin or any internal error (same invariant
  as every other hook here): a broken hook must never wedge the session. Always
  exit 0.
- KILL SWITCH: set BANNER_HOOK_DISABLE=1 to make it a pass-through no-op, or
  remove its command from settings.json Stop (a single curator_stop_hook entry
  is the original state).

Communication: a block is emitted as stdout JSON {"decision":"block","reason":...}
which Claude Code's Stop hook contract reads to keep the turn going.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

BANNER_TEXT = "USER INPUT REQUIRED"
MAX_BLOCKS_PER_SESSION = 2
STATE_FILENAME = ".banner_hook_state.json"

# Imperative / interrogative approval phrases that genuinely signal an awaiting
# prompt and are rare in ordinary statements. Matched within the FINAL line only.
_APPROVAL_RE = re.compile(
    r"\b("
    r"yes\s*/\s*no|y\s*/\s*n|which option|shall i|should i (?:proceed|continue)|"
    r"do you want|let me know|please confirm|awaiting your|waiting on you|"
    r"válassz|döntsd el"
    r")\b",
    re.IGNORECASE,
)

# Ambiguous Hungarian verbs that appear constantly in conditional / subordinate
# clauses ("Ha szeretnéd, ...", "...mehet a deploy.", "jóváhagyom a tervet").
# These are NOT prompts in those forms, so count them as awaiting-input ONLY in
# explicit question form — directly followed (within a few words) by a question
# mark on the same line. This is what kills the false positive that blocked a
# plain "...lezárhatod." status message.
_HU_QUESTION_RE = re.compile(
    r"\b(szeretnéd|akarod|mehet|melyik|jóváhagy\w*)\b[^?\n]{0,40}\?",
    re.IGNORECASE,
)


def _state_path() -> Path:
    claude_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))
    return claude_dir / STATE_FILENAME


def _read_state() -> dict:
    try:
        return json.loads(_state_path().read_text(encoding="utf8")) or {}
    except Exception:
        return {}


def _write_state(data: dict) -> None:
    try:
        _state_path().write_text(json.dumps(data), encoding="utf8")
    except Exception:
        pass


def extract_last_assistant_text(transcript_path: Path) -> str:
    """Return the concatenated text of the last assistant message that carried
    a text block. Returns '' if none / unreadable."""
    try:
        lines = transcript_path.read_text(encoding="utf8", errors="replace").splitlines()
    except Exception:
        return ""
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") != "assistant":
            continue
        content = obj.get("message", {}).get("content", [])
        texts = [c.get("text", "") for c in content
                 if isinstance(c, dict) and c.get("type") == "text"]
        joined = "".join(texts).strip()
        if joined:
            return joined
        # An assistant message with only tool_use/thinking — keep scanning back
        # is wrong (that would skip past the real final text); but the FINAL
        # user-facing turn always ends on a text block, so the first text-bearing
        # assistant message from the end is the reply. If this one had no text,
        # it's a trailing tool turn; continue to find the text reply.
    return ""


def has_banner(text: str) -> bool:
    return BANNER_TEXT in text


def looks_like_awaiting_input(text: str) -> bool:
    """Conservative: True only when the message's FINAL line is actually posed as
    a prompt — a trailing question mark, an imperative/interrogative approval
    phrase, or a Hungarian approval verb in explicit question form.

    Restricting to the final line (not the whole 400-char tail) is deliberate: a
    conditional clause such as "Ha szeretnéd, ... — de most lezárhatod." contains
    an approval verb mid-sentence but is NOT awaiting input, and the old tail
    scan blocked exactly that. A real awaiting-input prompt closes ON the ask."""
    if not text:
        return False
    stripped = text.rstrip()
    non_empty = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    if not non_empty:
        return False
    last = non_empty[-1]
    # Ignore obvious code/markup, and overly long paragraphs (a real
    # awaiting-input prompt is a short closing line, not a wall of text).
    if last.startswith(("#", "```", "|")) or len(last) > 200:
        return False
    # Strong signal: the final line is itself a question.
    if last.endswith("?"):
        return True
    # Imperative / interrogative approval phrase in the final line.
    if _APPROVAL_RE.search(last):
        return True
    # Ambiguous Hungarian verbs only count in explicit question form.
    if _HU_QUESTION_RE.search(last):
        return True
    return False


def decide(text: str, session_id: str, state: dict):
    """Return (action, reason, new_state). action in {allow, block, warn}."""
    new_state = dict(state)
    sid = session_id or "_nosession"
    sess = dict(new_state.get(sid, {"blocks": 0}))

    awaiting = looks_like_awaiting_input(text)
    banner = has_banner(text)

    if not awaiting or banner:
        # Clean turn — reset the per-session block counter.
        sess["blocks"] = 0
        new_state[sid] = sess
        return "allow", "", new_state

    # Awaiting input but no banner.
    if sess.get("blocks", 0) >= MAX_BLOCKS_PER_SESSION:
        # Loop guard tripped — stop blocking, warn only.
        new_state[sid] = sess
        return "warn", "banner missing but block cap reached", new_state

    sess["blocks"] = sess.get("blocks", 0) + 1
    new_state[sid] = sess
    reason = (
        "Your reply ends with a question/approval that awaits the user, but it is "
        "missing the required `USER INPUT REQUIRED` banner as its last line AND the "
        "plain-language (17-year-old-logic) restatement of the question. Per "
        "~/.claude/CLAUDE.md ('User input visibility' + 'Plain-language questions'), "
        "append both now: first the simplified-logic summary of what you are asking, "
        "then the banner exactly as:\n"
        "*********************************\n"
        "*    USER INPUT REQUIRED        *\n"
        "*********************************"
    )
    return "block", reason, new_state


def main() -> int:
    if os.environ.get("BANNER_HOOK_DISABLE") == "1":
        return 0
    try:
        payload_raw = sys.stdin.read()
    except Exception:
        return 0
    if not payload_raw.strip():
        return 0
    try:
        payload = json.loads(payload_raw)
    except Exception:
        return 0

    transcript_path_str = payload.get("transcript_path")
    session_id = payload.get("session_id") or ""
    if not transcript_path_str:
        return 0

    try:
        text = extract_last_assistant_text(Path(transcript_path_str))
        state = _read_state()
        action, reason, new_state = decide(text, session_id, state)
        _write_state(new_state)
        if action == "block":
            print(json.dumps({"decision": "block", "reason": reason}))
        elif action == "warn":
            print("[banner-hook] reply looks like it awaits input but has no "
                  "USER INPUT REQUIRED banner (block cap reached; not forcing).",
                  file=sys.stderr)
    except Exception:
        # Never wedge the session on an internal error.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
