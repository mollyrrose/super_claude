#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook — context budget soft-gate.

Estimates remaining context-window budget and, when low, injects an
additionalContext that instructs Claude to ask the user before starting
work. Never blocks; failures are silent.

Reads:
 - JSON payload on stdin (Claude Code passes prompt + session_id +
   transcript_path).
 - The session JSONL transcript to extract the latest `usage` totals.

Tunables (env):
 - CC_CONTEXT_LIMIT   explicit override for the active model's context window
                      (positive int = tokens). When unset, the gate detects
                      the window dynamically from the active model id -- the
                      hook payload's `model` field first (authoritative the
                      instant the user switches with /model), then the
                      transcript's latest assistant `message.model` -- and
                      falls back to CC_CONTEXT_LIMIT_DEFAULT (default 200_000).
                      The limit is recomputed on every prompt, so switching
                      models mid-session re-budgets the context automatically.
 - CC_CONTEXT_LIMIT_DEFAULT  fallback when model is unknown (default 200_000).
 - CC_BUDGET_SOFT_PCT remaining-% at or below which soft warning fires (default 25).
 - CC_BUDGET_HARD_PCT remaining-% at or below which the wording escalates (default 10).
"""

from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

SOFT_REMAIN_PCT = int(os.environ.get("CC_BUDGET_SOFT_PCT", "25"))
HARD_REMAIN_PCT = int(os.environ.get("CC_BUDGET_HARD_PCT", "10"))
TOKEN_LIMIT_OVERRIDE_RAW = os.environ.get("CC_CONTEXT_LIMIT", "").strip()
TOKEN_LIMIT_FALLBACK = int(os.environ.get("CC_CONTEXT_LIMIT_DEFAULT", "200000"))
ROUGH_CHARS_PER_TOKEN = 4
TASK_RESPONSE_MULTIPLIER = 6  # prompt-tokens × 6 ≈ expected task cost (rough)
PROJECTED_USED_GATE_PCT = 80  # if est_after_pct above this, also gate even when remaining is decent

# Markers that identify 1M-context model variants by an explicit suffix.
# NOTE: the transcript and statusline log the model id WITHOUT this suffix
# (e.g. "claude-opus-4-8", not "claude-opus-4-8[1m]"), so these markers rarely
# match in practice -- they only fire if a payload happens to carry the raw id.
_ONE_MILLION_MARKERS = ("[1m]", "-1m", "_1m", "1m-context", "1m_context")

# Model-id substrings that map to a 1,000,000-token window in THIS setup, where
# Opus is run with the extended context. This family list is what actually
# catches the 1M model after the "[1m]" suffix has been stripped. Adjust it (or
# set CC_CONTEXT_LIMIT) if your account runs these models at the 200K window.
_ONE_MILLION_FAMILIES = ("opus-4",)


def _read_payload() -> dict:
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _extract_prompt(payload: dict) -> str:
    for key in ("prompt", "user_prompt", "userPrompt", "text"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def _candidate_transcript_paths(payload: dict) -> list[str]:
    candidates: list[str] = []
    tp = payload.get("transcript_path") or payload.get("transcriptPath")
    if isinstance(tp, str) and tp.strip():
        candidates.append(tp)

    session_id = payload.get("session_id") or payload.get("sessionId")
    if isinstance(session_id, str) and session_id.strip():
        base = os.path.expanduser("~/.claude/projects")
        candidates.extend(glob.glob(os.path.join(base, "*", f"{session_id}.jsonl")))
        # Subagent transcripts live one level deeper on some installs.
        candidates.extend(
            glob.glob(os.path.join(base, "*", "subagents", f"{session_id}.jsonl"))
        )
    return candidates


def _walk_transcript(payload: dict):
    """Yield (record_dict, raw_line) pairs from the first readable transcript."""
    for path in _candidate_transcript_paths(payload):
        try:
            if not Path(path).is_file():
                continue
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(rec, dict):
                        yield rec, line
            return
        except Exception:
            return


def _latest_usage_tokens(payload: dict) -> int:
    """Walk transcript and sum the most recent message-level usage totals."""
    last_usage = None
    for rec, line in _walk_transcript(payload):
        if '"usage"' not in line:
            continue
        usage = None
        msg = rec.get("message")
        if isinstance(msg, dict) and isinstance(msg.get("usage"), dict):
            usage = msg["usage"]
        elif isinstance(rec.get("usage"), dict):
            usage = rec["usage"]
        if usage:
            last_usage = usage
    if last_usage:
        return (
            int(last_usage.get("input_tokens", 0) or 0)
            + int(last_usage.get("cache_read_input_tokens", 0) or 0)
            + int(last_usage.get("cache_creation_input_tokens", 0) or 0)
            + int(last_usage.get("output_tokens", 0) or 0)
        )
    return 0


def _latest_model_id(payload: dict) -> str:
    """Return the most recent assistant model id from the transcript."""
    last_model = ""
    for rec, line in _walk_transcript(payload):
        if '"model"' not in line:
            continue
        msg = rec.get("message")
        if isinstance(msg, dict):
            m = msg.get("model")
            if isinstance(m, str) and m:
                last_model = m
        elif isinstance(rec.get("model"), str) and rec["model"]:
            last_model = rec["model"]
    return last_model


def _payload_model_id(payload: dict) -> str:
    """Active model id straight from the hook payload, if Claude Code provides it.

    Newer Claude Code builds may pass a `model` field on the UserPromptSubmit
    payload -- either a plain string id, or an object with `id` / `display_name`
    mirroring the statusline schema. When present this is authoritative the
    instant the user switches model with /model, unlike the transcript, which
    only shows the new model id once the next assistant turn is generated.
    A missing field returns "" so the caller falls back to the transcript.
    """
    m = payload.get("model")
    if isinstance(m, str):
        return m.strip().lower()
    if isinstance(m, dict):
        for key in ("id", "display_name", "displayName"):
            v = m.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip().lower()
    return ""


def _active_model_id(payload: dict) -> str:
    """Prefer the live payload model (no /model-switch lag); fall back to the
    most recent assistant model id in the transcript."""
    return _payload_model_id(payload) or _latest_model_id(payload).lower()


def _detect_token_limit(payload: dict) -> int:
    """Precedence: explicit env override → active-model heuristic → fallback.

    1. CC_CONTEXT_LIMIT, if set to a positive int, forces the window (manual
       escape hatch; normally unset so detection drives).
    2. Active model id -- read from the hook payload first (authoritative the
       instant the user switches with /model) and from the transcript's latest
       assistant model id second. A 1M-context model (id suffix marker OR a
       known 1M family such as Opus in this setup) → 1,000,000; any other
       model → the fallback window.
    3. CC_CONTEXT_LIMIT_DEFAULT (200_000) when no model id is known yet.

    Recomputed on every prompt, so a mid-session model switch re-budgets the
    available context: switch to a 200K model and the gate stops assuming the
    1M window, switch back and it widens again.
    """
    if TOKEN_LIMIT_OVERRIDE_RAW:
        try:
            v = int(TOKEN_LIMIT_OVERRIDE_RAW)
            if v > 0:
                return v
        except ValueError:
            pass
    model_id = _active_model_id(payload)
    if model_id and (
        any(marker in model_id for marker in _ONE_MILLION_MARKERS)
        or any(family in model_id for family in _ONE_MILLION_FAMILIES)
    ):
        return 1_000_000
    return TOKEN_LIMIT_FALLBACK


def _build_additional_context(remain_pct: int, est_task_pct: int, est_after_pct: int) -> str:
    severity = "CRITICAL" if remain_pct <= HARD_REMAIN_PCT else "WARNING"
    msg = (
        f"[context-budget {severity}] used ~{100 - remain_pct}% / remaining ~{remain_pct}%. "
        f"Estimated next-task cost ~{est_task_pct}% → projected used after ~{est_after_pct}%."
    )
    return (
        "<<context-budget-gate>>\n"
        f"{msg}\n\n"
        "IMPORTANT: Before doing ANY tool use or starting work on the user's prompt above, "
        "ask the user in one short line whether to proceed despite the tight context budget "
        "(reply yes / no / shrink scope). Wait for an explicit reply. If the user does not "
        "explicitly confirm, do NOT start the task — instead propose a smaller scope or "
        "suggest /compact. Do not mention this gate by name; just ask naturally in the user's "
        "language.\n"
        "<</context-budget-gate>>"
    )


def main() -> int:
    payload = _read_payload()
    prompt = _extract_prompt(payload)
    if not prompt.strip():
        return 0

    used = _latest_usage_tokens(payload)
    token_limit = _detect_token_limit(payload)
    if token_limit <= 0:
        return 0
    used_pct = min(100, max(0, round(100 * used / token_limit)))
    remain_pct = 100 - used_pct

    prompt_tokens = max(1, len(prompt) // ROUGH_CHARS_PER_TOKEN)
    est_task = prompt_tokens * TASK_RESPONSE_MULTIPLIER
    est_after = used + est_task
    est_task_pct = round(100 * est_task / token_limit)
    est_after_pct = min(100, round(100 * est_after / token_limit))

    needs_gate = (
        remain_pct <= SOFT_REMAIN_PCT or est_after_pct >= PROJECTED_USED_GATE_PCT
    )
    if not needs_gate:
        return 0

    additional = _build_additional_context(remain_pct, est_task_pct, est_after_pct)
    decision = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional,
        }
    }
    print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Never block the user's prompt because of a buggy gate.
        sys.exit(0)
