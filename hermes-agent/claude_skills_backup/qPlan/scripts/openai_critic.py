#!/usr/bin/env python3
"""
qPlan cross-model critic — OpenAI provider.

Reads JSON from stdin:
  { "task": "<original task>",
    "plan": "<current plan.md content>",
    "ledger": [ { "text": "...", "status": "...", "tier": "..." }, ... ],
    "model": "<optional model override>" }

Writes JSON to stdout:
  { "verdict": "major issue|minor issue|no material issue",
    "suggestions": [ { "text": "...", "tier_hint": "..." } ],
    "provider": "openai",
    "model": "<model used>" }

If the caller does NOT pass a `model` key, the script auto-discovers the
best chat model the OPENAI_API_KEY can reach by listing /v1/models and
matching against the MODEL_PRIORITY table (best-first). The pick is cached
in ~/.claude/.qplan_openai_model_cache.json for CACHE_TTL_HOURS to avoid
hitting /v1/models on every critic round. Force a refresh with the env var
QPLAN_OPENAI_MODEL_REFRESH=1 or by deleting the cache file.

Fails loud (non-zero exit + stderr message) if OPENAI_API_KEY is missing or
the chat completion call errors. Does NOT fall back to a stub or to claude
— provider distinguishability is the whole point of the comparison. The
/v1/models lookup is the only soft-fail path: if it errors, the script
falls back to a stale cache and then to HARD_FALLBACK_MODEL, because losing
auto-discovery should not kill an in-flight planning round.

Stdlib only. No `openai` package install needed.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CRITIC_PROMPT = """You are the critic in a qPlan author↔critic loop.

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

CACHE_PATH = Path.home() / ".claude" / ".qplan_openai_model_cache.json"
CACHE_TTL_HOURS = 24.0

# Best-first priority. Each entry matches a model family root; within a
# matched family we prefer the un-dated stable alias (e.g. `gpt-5` over
# `gpt-5-2025-07-15`) because OpenAI routes the alias to the latest
# snapshot of that family. Order reflects critic-quality vs cost: newest
# general-purpose first, then strong reasoning, then smaller / older
# models as graceful degradation. Add new families at the top as OpenAI
# releases them — this list is the only thing that needs updating.
MODEL_PRIORITY = [
    re.compile(r"^gpt-5\.5(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-5\.1(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-5(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^o3-pro(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^o3(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-5-mini(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-4\.1(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^o1(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^o3-mini(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-4\.1-mini(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-4o(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-4o-mini(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^o1-mini(?:-\d{4}-\d{2}-\d{2})?$"),
]

# Last-resort literal if /v1/models is unreachable AND no cache exists.
HARD_FALLBACK_MODEL = "gpt-4o"


def _list_models(api_key: str) -> list[str]:
    req = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return [m["id"] for m in body.get("data", [])]


def _pick_best(available: list[str]) -> str | None:
    for pattern in MODEL_PRIORITY:
        matches = [m for m in available if pattern.match(m)]
        if not matches:
            continue
        # Prefer the un-dated stable alias — OpenAI keeps it pointed at the
        # latest snapshot of the family.
        stable = [m for m in matches if not re.search(r"-\d{4}-\d{2}-\d{2}$", m)]
        if stable:
            return stable[0]
        # Else take the lexicographically latest dated snapshot
        # (YYYY-MM-DD sorts chronologically).
        return sorted(matches)[-1]
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
        pass  # cache write failure is non-fatal


def discover_model(api_key: str) -> str:
    """Pick the best chat model accessible to OPENAI_API_KEY.

    Cached for CACHE_TTL_HOURS. Force refresh with
    QPLAN_OPENAI_MODEL_REFRESH=1 or by deleting CACHE_PATH.
    """
    if not os.environ.get("QPLAN_OPENAI_MODEL_REFRESH"):
        fresh = _read_cache(allow_stale=False)
        if fresh:
            return fresh

    try:
        available = _list_models(api_key)
    except (urllib.error.HTTPError, urllib.error.URLError):
        # /v1/models is down or auth-blocked — accept a stale cache entry
        # rather than kill an in-flight planning round. Last resort: the
        # hardcoded fallback.
        stale = _read_cache(allow_stale=True)
        return stale or HARD_FALLBACK_MODEL

    best = _pick_best(available) or HARD_FALLBACK_MODEL
    _write_cache(best, len(available))
    return best


# --- Chat call ------------------------------------------------------------


def call_openai(api_key: str, model: str, task: str, plan: str, ledger: list) -> dict:
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
    }
    # 2026-06-10: GPT-5+ models (gpt-5, gpt-5.1...gpt-5.5) reject any non-
    # default temperature with HTTP 400. Only send temperature for legacy
    # models that accept it.
    if not model.startswith("gpt-5"):
        payload["temperature"] = 0.3
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
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
        sys.stderr.write(
            f"openai_critic: HTTP {e.code} — "
            f"{e.read().decode('utf-8', 'replace')}\n"
        )
        sys.exit(2)
    except urllib.error.URLError as e:
        sys.stderr.write(f"openai_critic: network error — {e}\n")
        sys.exit(2)

    content = body["choices"][0]["message"]["content"]
    return json.loads(content)


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.stderr.write(
            "openai_critic: OPENAI_API_KEY not set. qPlan does NOT silently "
            "fall back to claude — provider distinguishability is the point. "
            "Set the env var or switch critic_provider back to claude.\n"
        )
        sys.exit(2)

    try:
        req_in = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        sys.stderr.write(f"openai_critic: bad JSON on stdin — {e}\n")
        sys.exit(2)

    task = req_in.get("task", "")
    plan = req_in.get("plan", "")
    ledger = req_in.get("ledger", [])
    # Explicit override locks the model; otherwise auto-discover.
    model = req_in.get("model") or discover_model(api_key)

    verdict = call_openai(api_key, model, task, plan, ledger)
    verdict["provider"] = "openai"
    verdict["model"] = model

    sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
