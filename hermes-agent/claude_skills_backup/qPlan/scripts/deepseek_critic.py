#!/usr/bin/env python3
"""
qPlan cross-model critic — DeepSeek provider.

Mirror of openai_critic.py for DeepSeek's chat-completions endpoint.

Reads JSON from stdin:
  { "task": "<original task>",
    "plan": "<current plan.md content>",
    "ledger": [ { "text": "...", "status": "...", "tier": "..." }, ... ],
    "model": "<optional model override>" }

Writes JSON to stdout:
  { "verdict": "major issue|minor issue|no material issue",
    "suggestions": [ { "text": "...", "tier_hint": "..." } ],
    "provider": "deepseek",
    "model": "<model used>",
    "chunks_submitted": <int> }

If the caller does NOT pass a `model` key, the script auto-discovers the
best chat model the DEEPSEEK_API_KEY can reach by listing /v1/models and
matching against MODEL_PRIORITY (best-first). The pick is cached in
~/.claude/.qplan_deepseek_model_cache.json for CACHE_TTL_HOURS to avoid
hitting /v1/models every critic round. Force a refresh with the env var
QPLAN_DEEPSEEK_MODEL_REFRESH=1 or by deleting the cache file.

DeepSeek API notes (verified 2026-06-12):
- Endpoint: https://api.deepseek.com/v1/chat/completions (OpenAI-compatible).
- Unlike OpenAI, DeepSeek exposes CONCURRENCY caps rather than strict
  TPM/RPM. As of 2026-06: deepseek-v4-pro 500 concurrent, deepseek-v4-flash
  2500 concurrent. Single-call critic usage rarely hits this — but if a
  call returns HTTP 429 (overload, concurrency excess, or future per-tier
  TPM enforcement), we still chunk the plan defensively. Same pattern as
  the OpenAI critic; see feedback_model_selection_highest.md.
- DeepSeek accepts standard `temperature` on all current models — no
  GPT-5-style 400 trap.

Fails loud (non-zero exit + stderr) on missing DEEPSEEK_API_KEY or chat
errors. Does NOT silently fall back to Claude — provider distinguishability
is the whole point.

Stdlib only.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CRITIC_PROMPT = """You are the DeepSeek critic in a qPlan author<->critic loop.

Read the plan and the ledger of prior suggestions. Produce a JSON verdict
EXACTLY in this shape:

{
  "verdict": "major issue" | "minor issue" | "no material issue",
  "suggestions": [
    { "text": "<one concrete actionable point>",
      "tier_hint": "structural" | "behavioral" | "editorial" }
  ]
}

CRITICAL: `no material issue` with an empty suggestions list is a VALID and
correct outcome. Do not invent a critique if the plan is sound. Convergence
is the point.

Do not repeat points already in the ledger — they will be detected as
semantic duplicates and the round will be wasted. If you find yourself
rephrasing a prior point, omit it.

Output ONLY the JSON. No prose before or after."""


# --- Model auto-discovery -------------------------------------------------

CACHE_PATH = Path.home() / ".claude" / ".qplan_deepseek_model_cache.json"
CACHE_TTL_HOURS = 24.0

# Best-first priority. Order reflects reasoning quality vs cost: pro
# reasoning first, then flash, then earlier families as graceful
# degradation. Update this list when DeepSeek releases new model families
# — that's the only thing that needs editing.
MODEL_PRIORITY = [
    re.compile(r"^deepseek-v4-pro$"),
    re.compile(r"^deepseek-v4-flash$"),
    re.compile(r"^deepseek-v3-pro$"),
    re.compile(r"^deepseek-v3-flash$"),
    re.compile(r"^deepseek-reasoner$"),
    re.compile(r"^deepseek-chat$"),
    re.compile(r"^deepseek-coder$"),
]

# Last-resort if /v1/models is unreachable AND no cache exists.
HARD_FALLBACK_MODEL = "deepseek-chat"


def _list_models(api_key: str) -> list[str]:
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return [m["id"] for m in body.get("data", [])]


def _pick_best(available: list[str]) -> str | None:
    for pattern in MODEL_PRIORITY:
        matches = [m for m in available if pattern.match(m)]
        if matches:
            return matches[0]
    return None


def _read_cache(allow_stale: bool = False) -> str | None:
    try:
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    model = cache.get("model")
    fetched_at = cache.get("fetched_at", "")
    if not (model and fetched_at):
        return None
    if allow_stale:
        return model
    try:
        age_h = (
            datetime.now(timezone.utc) - datetime.fromisoformat(fetched_at)
        ).total_seconds() / 3600.0
    except ValueError:
        return None
    return model if age_h < CACHE_TTL_HOURS else None


def _write_cache(model: str, available_count: int) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps(
                {
                    "model": model,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "available_models_count": available_count,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        pass


def discover_model(api_key: str) -> str:
    if not os.environ.get("QPLAN_DEEPSEEK_MODEL_REFRESH"):
        fresh = _read_cache(allow_stale=False)
        if fresh:
            return fresh

    try:
        available = _list_models(api_key)
    except (urllib.error.HTTPError, urllib.error.URLError):
        stale = _read_cache(allow_stale=True)
        return stale or HARD_FALLBACK_MODEL

    best = _pick_best(available) or HARD_FALLBACK_MODEL
    _write_cache(best, len(available))
    return best


# --- Chunking on HTTP 429 -------------------------------------------------
#
# Defensive: DeepSeek caps concurrency, not TPM, but a single call can
# still 429 on server overload or unannounced per-tier TPM. Pattern is
# identical to the OpenAI critic — split plan on Markdown headers,
# recurse, merge verdicts.

MAX_CHUNK_DEPTH = 4
VERDICT_SEVERITY = {"major issue": 0, "minor issue": 1, "no material issue": 2}


def _split_plan(plan: str) -> list[str]:
    """Same as openai_critic._split_plan — kept inline to avoid a shared
    helper module on the path."""
    lines = plan.splitlines(keepends=True)
    for prefix in ("## ", "### "):
        starts = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
        if len(starts) >= 2:
            mid_idx = starts[len(starts) // 2]
            return ["".join(lines[:mid_idx]), "".join(lines[mid_idx:])]
    if len(lines) >= 4:
        mid = len(lines) // 2
        for offset in range(0, mid):
            for sign in (-1, 1):
                idx = mid + sign * offset
                if 0 < idx < len(lines) and lines[idx].strip() == "":
                    return ["".join(lines[:idx]), "".join(lines[idx:])]
    if len(lines) <= 1:
        return [plan]
    mid = len(lines) // 2
    return ["".join(lines[:mid]), "".join(lines[mid:])]


def _merge_verdicts(sub_verdicts: list[dict]) -> dict:
    seen_texts: set = set()
    suggestions: list = []
    worst = 2
    for v in sub_verdicts:
        sub = VERDICT_SEVERITY.get(v.get("verdict", "no material issue"), 2)
        if sub < worst:
            worst = sub
        for s in v.get("suggestions", []) or []:
            text = s.get("text", "").strip()
            if not text or text in seen_texts:
                continue
            seen_texts.add(text)
            suggestions.append(s)
    verdict_str = next(k for k, v in VERDICT_SEVERITY.items() if v == worst)
    return {"verdict": verdict_str, "suggestions": suggestions}


# --- Chat call ------------------------------------------------------------


def call_deepseek(
    api_key: str,
    model: str,
    task: str,
    plan: str,
    ledger: list,
    depth: int = 0,
) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": CRITIC_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"task": task, "plan": plan, "ledger": ledger},
                    ensure_ascii=False,
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", "replace")
        if e.code == 429 and depth < MAX_CHUNK_DEPTH:
            parts = _split_plan(plan)
            if len(parts) < 2:
                sys.stderr.write(
                    f"deepseek_critic: HTTP 429 but plan is atomic at depth "
                    f"{depth} — cannot split further. Response: {body_text}\n"
                )
                sys.exit(2)
            sys.stderr.write(
                f"deepseek_critic: 429 at depth {depth}, splitting plan "
                f"into {len(parts)} parts and retrying.\n"
            )
            sub_verdicts = [
                call_deepseek(api_key, model, task, p, ledger, depth + 1)
                for p in parts
            ]
            merged = _merge_verdicts(sub_verdicts)
            merged["_chunks_submitted"] = sum(
                v.get("_chunks_submitted", 1) for v in sub_verdicts
            )
            return merged
        sys.stderr.write(f"deepseek_critic: HTTP {e.code} — {body_text}\n")
        sys.exit(2)
    except urllib.error.URLError as e:
        sys.stderr.write(f"deepseek_critic: network error — {e}\n")
        sys.exit(2)

    content = body["choices"][0]["message"]["content"]
    return json.loads(content)


def main() -> None:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        sys.stderr.write(
            "deepseek_critic: DEEPSEEK_API_KEY not set. qPlan does NOT silently "
            "fall back to claude — provider distinguishability is the point. "
            "Set the env var or drop deepseek from the providers list.\n"
        )
        sys.exit(2)

    try:
        req_in = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        sys.stderr.write(f"deepseek_critic: bad JSON on stdin — {e}\n")
        sys.exit(2)

    task = req_in.get("task", "")
    plan = req_in.get("plan", "")
    ledger = req_in.get("ledger", [])
    model = req_in.get("model") or discover_model(api_key)

    verdict = call_deepseek(api_key, model, task, plan, ledger)
    verdict["provider"] = "deepseek"
    verdict["model"] = model
    verdict["chunks_submitted"] = verdict.pop("_chunks_submitted", 1)

    sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
