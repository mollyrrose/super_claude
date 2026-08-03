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
 - CC_GLM_CONTEXT_LIMIT  window for GLM (z.ai) models -- ids containing "glm"
                      (default 200_000; raise if a GLM model ships a larger
                      window). Keeps the budget correct when running on z.ai.
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
# qClose nudge tier: when remaining drops this low, surface the USER-INPUT
# banner recommending a manual /qClose BEFORE the (lossy) auto-compact fires.
# The statusline's context bar reads ~100% "full" at ~16.5% real remaining
# (its AUTO_COMPACT_BUFFER_PCT), which is where Claude Code auto-compacts.
# Bar ~99% therefore corresponds to ~17-18% real remaining, so 18 fires the
# nudge a hair earlier than the auto-compact point -- giving the user a chance
# to choose the precise /qClose handoff instead of the lossy summary.
QCLOSE_REMAIN_PCT = int(os.environ.get("CC_BUDGET_QCLOSE_PCT", "18"))
# qUpd pre-compaction flush tier: fires EARLIER than the qClose tier (more
# headroom above the auto-compact floor) so there is still context-room to run
# /qUpd's doc refreshes -- writing the durable tracking docs
# (INDEX/TODO/SYSTEM_STATUS/drawio) to disk BEFORE the lossy auto-compaction, so
# the post-compact session has ground truth to re-derive from. Default 35%
# remaining (sits above SOFT 25% and QCLOSE 18%). It is fire-once per session so
# it does not nag every prompt; it re-fires only if context climbs another
# QUPD_REDO_DELTA points after a prior flush (to refresh the docs again closer to
# the compaction boundary). Disable with CC_BUDGET_QUPD_DISABLE=1.
QUPD_REMAIN_PCT = int(os.environ.get("CC_BUDGET_QUPD_PCT", "35"))
QUPD_REDO_DELTA = int(os.environ.get("CC_BUDGET_QUPD_REDO_DELTA", "15"))
QUPD_DISABLE = os.environ.get("CC_BUDGET_QUPD_DISABLE", "").strip() not in ("", "0", "false", "False")
# Master kill switch: CC_BUDGET_GATE_DISABLE=1 silences EVERY tier (soft,
# qClose handoff nudge, and qUpd flush) -- the whole gate becomes a no-op that
# never injects additionalContext. Use when the periodic "context almost full,
# run /qClose before the lossy auto-compact" warnings are unwanted. Re-enable by
# removing the env var. (Auto-compact still runs; you just lose the precise
# /qClose handoff nudge before it -- and auto-compact IS lossy, it summarises.)
GATE_DISABLE = os.environ.get("CC_BUDGET_GATE_DISABLE", "").strip() not in ("", "0", "false", "False")
QUPD_STATE_PATH = os.environ.get("CC_BUDGET_QUPD_STATE", "").strip() or os.path.expanduser(
    "~/.claude/.context_qupd_flush_state.json"
)
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
# ROT WARNING: when a new top-tier model generation lands (Opus 6, Fable 6...),
# ADD IT HERE, or the gate silently falls back to 200K and starts telling the
# model "context nearly full" at ~18% real usage of the 1M window (this exact
# bug shipped once: the list said only "opus-4" while the setup ran Opus 5 /
# Fable 5 [1m], fixed 2026-08-03).
_ONE_MILLION_FAMILIES = ("opus-4", "opus-5", "fable")

# GLM (z.ai) model-id substrings. When the active provider is z.ai the served
# model id is "glm-..." (e.g. glm-4.6, GLM-5.2), NOT an Anthropic id, so this
# branch keeps the budget correct under GLM and stops a GLM id from ever being
# mistaken for a 1M Opus window. GLM-4.x is a 200K window; override with
# CC_GLM_CONTEXT_LIMIT if a GLM model ships a larger one (e.g. GLM-5.2).
_GLM_FAMILIES = ("glm",)
GLM_CONTEXT_LIMIT = int(os.environ.get("CC_GLM_CONTEXT_LIMIT", "200000"))


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
    # GLM (z.ai) check first: a glm-* id takes its own window and must never be
    # caught by the 1M-Opus heuristic below.
    if model_id and any(family in model_id for family in _GLM_FAMILIES):
        return GLM_CONTEXT_LIMIT
    if model_id and (
        any(marker in model_id for marker in _ONE_MILLION_MARKERS)
        or any(family in model_id for family in _ONE_MILLION_FAMILIES)
    ):
        return 1_000_000
    return TOKEN_LIMIT_FALLBACK


def _load_flush_state() -> dict:
    """Per-session record of the last qUpd-flush point. Fail-soft to {}."""
    try:
        with open(QUPD_STATE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _qupd_flush_due(session_id: str, used_pct: int) -> bool:
    """True if this session has never flushed, or has consumed at least
    QUPD_REDO_DELTA more percent of the window since its last flush."""
    state = _load_flush_state()
    entry = state.get(session_id)
    if not isinstance(entry, dict):
        return True
    last = entry.get("used_pct")
    if not isinstance(last, (int, float)):
        return True
    return (used_pct - last) >= QUPD_REDO_DELTA


def _record_flush(session_id: str, used_pct: int) -> None:
    """Mark this session flushed at used_pct. Fail-soft; bounds file size."""
    if not session_id:
        return
    try:
        data = _load_flush_state()
        data[session_id] = {"used_pct": used_pct}
        if len(data) > 200:  # keep the most-recently-inserted ~200 sessions
            for k in list(data.keys())[:-200]:
                data.pop(k, None)
        with open(QUPD_STATE_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except Exception:
        pass


def _build_qupd_flush_context(remain_pct: int) -> str:
    """Pre-compaction flush tier: run /qUpd's doc refreshes NOW, with headroom,
    so the durable tracking docs survive the imminent lossy auto-compaction.

    Unlike the qClose tier this does NOT stop or banner -- it instructs Claude to
    flush the docs proactively, report one line, and continue with the user's
    actual prompt. A pre-compaction flush only WRITES the files to disk: it must
    NOT commit and must NOT push (the files persist on disk through compaction;
    committing is a separate later step).
    """
    return (
        "<<context-budget-gate>>\n"
        f"[context-budget PRE-COMPACT FLUSH] remaining ~{remain_pct}% -- a lossy "
        "auto-compaction is approaching while there is still headroom.\n\n"
        "IMPORTANT: Before working on the user's prompt above, run the /qUpd doc "
        "refreshes NOW (invoke the qUpd skill): update INDEX.md, "
        "exclude/SYSTEM_STRATEGIES/TODO.md, SYSTEM_STATUS.md, and regenerate "
        "system_map.drawio only if the architecture actually changed. Writing "
        "these durable docs to disk before the compaction gives the post-compact "
        "session ground truth to re-derive from instead of the lossy summary. "
        "Do NOT run qUpd's commit or push step -- a pre-compaction flush must "
        "ONLY write the updated files to disk, never commit and never push. qUpd "
        "self-skips if nothing meaningful changed. After the flush, note it in "
        "ONE short line in the user's language (do NOT mention this gate by "
        "name), then continue with the user's actual prompt normally. Do not stop "
        "or ask for confirmation; just flush, report one line, and proceed.\n"
        "<</context-budget-gate>>"
    )


def _build_qclose_context(remain_pct: int) -> str:
    """Strongest tier: context is nearly full and auto-compact is imminent.

    Instructs Claude to STOP, recommend a manual /qClose (precise handoff),
    and end the turn with the exact USER-INPUT banner so the idle terminal is
    noticed. Fires just before the auto-compact point so the user can pick the
    precise handoff over the lossy summary.
    """
    return (
        "<<context-budget-gate>>\n"
        f"[context-budget NEAR-FULL] remaining ~{remain_pct}% -- auto-compact is imminent.\n\n"
        "IMPORTANT: Do NOT start the user's prompt above or any new work. The context window "
        "is almost full; auto-compact will soon replace this session with a LOSSY summary. "
        "Instead, in the user's language, briefly tell them the context is nearly full and "
        "recommend running /qClose now to capture a precise, resumable handoff before that "
        "happens (auto-compact remains the fallback if they do nothing). Do not mention this "
        "gate by name. End your reply with EXACTLY these three lines and nothing after them:\n"
        "*********************************\n"
        "*    USER INPUT REQUIRED        *\n"
        "*********************************\n"
        "<</context-budget-gate>>"
    )


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
    if GATE_DISABLE:
        return 0
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

    # Strongest tier first: near-full -> recommend a manual /qClose handoff
    # before the (lossy) auto-compact kicks in. Takes precedence over the
    # soft/projected warning below.
    if used > 0 and remain_pct <= QCLOSE_REMAIN_PCT:
        decision = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": _build_qclose_context(remain_pct),
            }
        }
        print(json.dumps(decision))
        return 0

    # Next tier: pre-compaction qUpd flush. Fires earlier than qClose (more
    # headroom) so /qUpd can write the durable docs before the lossy compaction.
    # Fire-once per session (re-fires only after QUPD_REDO_DELTA more % consumed)
    # and requires a session_id to dedupe -- without one we cannot avoid nagging,
    # so we skip rather than loop.
    session_id = payload.get("session_id") or payload.get("sessionId")
    session_id = session_id.strip() if isinstance(session_id, str) else ""
    if (
        not QUPD_DISABLE
        and used > 0
        and session_id
        and remain_pct <= QUPD_REMAIN_PCT
        and _qupd_flush_due(session_id, used_pct)
    ):
        _record_flush(session_id, used_pct)
        decision = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": _build_qupd_flush_context(remain_pct),
            }
        }
        print(json.dumps(decision))
        return 0

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
