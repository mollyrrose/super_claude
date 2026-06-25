#!/usr/bin/env python3
"""
qPlan cross-model critic — GLM (z.ai / Zhipu) provider.

The RECIPROCAL of claude_critic.py. When the qPlan session runs on Claude
(Anthropic), the built-in `claude` lens IS Claude, so there is no GLM voice in
the panel. This provider adds a TRUE GLM voice that is INDEPENDENT of the active
session provider — exactly like openai_critic.py / deepseek_critic.py. It lets
qPlan (and qGoal, which calls qPlan) cross-check its decisions against GLM even
while running on Claude — the mirror image of the "real Claude voice while on
GLM" path that claude_critic.py provides.

Two tiers, selected purely by the `model` you pass (ONE script, TWO lenses):
  - paid  (`glm` lens):      flagship model, auto-discovered (glm-5.x > glm-4.6 ...)
  - free  (`glm-free` lens): a free model id (default glm-4-flash), same key

OpenAI-compatible chat-completions endpoint (z.ai international):
  base  : GLM_BASE_URL or https://api.z.ai/api/paas/v4
  key   : GLM_API_KEY or ZAI_API_KEY  (the GLM launcher already exports ZAI_API_KEY)
  model : stdin `model` override, else GLM_MODEL, else auto-discovery (paid)

Reads JSON from stdin:  { "task","plan","ledger","model"? }
Writes JSON to stdout:  { "verdict","suggestions","provider":"glm","model" }

Opt-in / graceful: if no key is available, exits non-zero with a clear message
and the panel mutes the lens (same policy as the other cross-model critics). Does
NOT silently fall back to another provider — provider distinguishability is the
point. Stdlib only.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BASE_URL = "https://api.z.ai/api/paas/v4"
CACHE_PATH = Path.home() / ".claude" / ".qplan_glm_model_cache.json"
CACHE_TTL_HOURS = 24.0

# Highest-first. IDs are best-effort against z.ai's lineup (2026-06) and are
# self-correcting: auto-discovery walks this list against /models, and either of
# GLM_MODEL / the per-call `model` field overrides it entirely. Update this list
# when z.ai ships a new flagship — that's the only thing that needs editing.
MODEL_PRIORITY = [
    re.compile(r"^glm-5(?:[.-].*)?$"),
    re.compile(r"^glm-4\.6$"),
    re.compile(r"^glm-4\.5(?:-.*)?$"),
    re.compile(r"^glm-4-plus$"),
    re.compile(r"^glm-4(?:-0\d+)?$"),
]
HARD_FALLBACK_MODEL = "glm-4.6"
FREE_DEFAULT_MODEL = "glm-4-flash"

CRITIC_PROMPT = """You are the GLM critic in a qPlan author<->critic loop.

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
correct outcome. Do not invent a critique if the plan is sound. Convergence is
the point. Do not repeat points already in the ledger.

Output ONLY the JSON object. No prose before or after."""


class _BudgetExhausted(Exception):
    """Raised when z.ai rejects the call for billing/quota reasons (HTTP 402,
    429, or a balance/quota error code like 1113 in the body). Signals main()
    to retry on the FREE model instead of muting, so a dead paid balance does
    not stop the round."""


# --- pure helpers (unit-testable, no network) -----------------------------

def api_key() -> str:
    return os.environ.get("GLM_API_KEY") or os.environ.get("ZAI_API_KEY") or ""


def base_url() -> str:
    return (os.environ.get("GLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def build_messages(task: str, plan: str, ledger: list) -> list:
    return [
        {"role": "system", "content": CRITIC_PROMPT},
        {"role": "user", "content": json.dumps(
            {"task": task, "plan": plan, "ledger": ledger}, ensure_ascii=False)},
    ]


def extract_json(text: str) -> dict:
    """Tolerantly extract the first balanced top-level JSON object from text
    (models sometimes wrap JSON in prose or fences despite instructions)."""
    if not text:
        raise ValueError("empty text")
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except json.JSONDecodeError:
                            break
        start = text.find("{", start + 1)
    raise ValueError("no valid JSON object found in text")


def _pick_best(available: list) -> str:
    for pattern in MODEL_PRIORITY:
        matches = [m for m in available if pattern.match(m)]
        if not matches:
            continue
        stable = [m for m in matches if not re.search(r"-\d{4}-\d{2}-\d{2}$", m)]
        return (stable or sorted(matches, reverse=True))[0]
    return ""


# --- model auto-discovery (paid tier only) --------------------------------

def _list_models(key: str) -> list:
    req = urllib.request.Request(
        f"{base_url()}/models",
        headers={"Authorization": f"Bearer {key}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return [m.get("id", "") for m in body.get("data", [])]


def _read_cache(allow_stale: bool = False):
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
        age_h = (datetime.now(timezone.utc)
                 - datetime.fromisoformat(fetched_at)).total_seconds() / 3600.0
    except ValueError:
        return None
    return model if age_h < CACHE_TTL_HOURS else None


def _write_cache(model: str, count: int) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(
            {"model": model,
             "fetched_at": datetime.now(timezone.utc).isoformat(),
             "available_models_count": count}, indent=2), encoding="utf-8")
    except OSError as e:
        sys.stderr.write(f"glm_critic: cache write failed (non-fatal): {e}\n")


def discover_model(key: str) -> str:
    if not os.environ.get("QPLAN_GLM_MODEL_REFRESH"):
        fresh = _read_cache(allow_stale=False)
        if fresh:
            return fresh
    try:
        available = _list_models(key)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            sys.stderr.write(
                f"glm_critic: /models returned HTTP {e.code} — bad or revoked "
                f"GLM_API_KEY/ZAI_API_KEY. Fix the key and retry.\n")
            sys.exit(2)
        return _read_cache(allow_stale=True) or HARD_FALLBACK_MODEL
    except urllib.error.URLError:
        return _read_cache(allow_stale=True) or HARD_FALLBACK_MODEL
    best = _pick_best(available) or HARD_FALLBACK_MODEL
    _write_cache(best, len(available))
    return best


# --- chat call ------------------------------------------------------------

def call_glm(key: str, model: str, task: str, plan: str, ledger: list) -> dict:
    payload = {
        "model": model,
        "messages": build_messages(task, plan, ledger),
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        f"{base_url()}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", "replace")
        low = body_text.lower()
        # Budget/quota exhaustion -> signal main() to retry on the free model.
        # z.ai uses 402/429 and balance error codes (e.g. 1113); match keywords
        # in EN and ZH so a depleted paid balance falls back instead of stopping.
        if (
            e.code in (402, 429)
            or "1113" in body_text
            or any(k in low for k in ("insufficient", "balance", "quota", "arrears"))
            # z.ai may also word the balance/arrears error in Chinese, but the
            # numeric code 1113 and HTTP 402/429 above already catch those
            # responses, so no non-ASCII literals are needed here (keeps the
            # source ASCII-clean per the repo's no-non-ASCII-in-code rule).
        ):
            raise _BudgetExhausted(body_text)
        sys.stderr.write(f"glm_critic: HTTP {e.code} — {body_text}\n")
        sys.exit(2)
    except urllib.error.URLError as e:
        sys.stderr.write(f"glm_critic: network error — {e}\n")
        sys.exit(2)
    try:
        content = body["choices"][0]["message"]["content"]
        return extract_json(content)
    except (KeyError, IndexError, TypeError, ValueError) as e:
        sys.stderr.write(
            f"glm_critic: bad response ({type(e).__name__}: {e}). "
            f"Raw: {json.dumps(body)[:1000]}\n")
        sys.exit(2)


def main() -> None:
    key = api_key()
    if not key:
        sys.stderr.write(
            "glm_critic: no GLM_API_KEY or ZAI_API_KEY set. The glm lens is "
            "opt-in; the panel mutes it when unavailable. qPlan does NOT silently "
            "fall back to another provider — provider distinguishability is the "
            "point. Set the key or drop glm/glm-free from panel_lenses.\n")
        sys.exit(2)

    try:
        req_in = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        sys.stderr.write(f"glm_critic: bad JSON on stdin — {e}\n")
        sys.exit(2)

    task = req_in.get("task", "")
    plan = req_in.get("plan", "")
    ledger = req_in.get("ledger", [])
    model = req_in.get("model") or os.environ.get("GLM_MODEL") or discover_model(key)
    free_model = os.environ.get("GLM_FREE_MODEL") or FREE_DEFAULT_MODEL

    try:
        verdict = call_glm(key, model, task, plan, ledger)
    except _BudgetExhausted:
        # Paid balance/quota is dead. Per the user's policy, do NOT stop the
        # round — retry on the FREE model (glm-4-flash), which is a separate
        # quota bucket on the same key. Disable with QPLAN_GLM_NO_FREE_FALLBACK=1.
        if os.environ.get("QPLAN_GLM_NO_FREE_FALLBACK") == "1" or model == free_model:
            sys.stderr.write(
                "glm_critic: budget exhausted; free fallback disabled or already "
                "on the free model. Lens muted.\n"
            )
            sys.exit(2)
        sys.stderr.write(
            f"glm_critic: paid budget/quota exhausted — falling back to the free "
            f"model {free_model}.\n"
        )
        try:
            verdict = call_glm(key, free_model, task, plan, ledger)
        except _BudgetExhausted:
            sys.stderr.write(
                "glm_critic: free model also rejected (budget/limit). Lens muted.\n"
            )
            sys.exit(2)
        model = free_model

    verdict["provider"] = "glm"
    verdict["model"] = model
    sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
