#!/usr/bin/env python3
"""
qPlan cross-model critic — SubQ (subq.ai) provider.

SubQ exposes an OpenAI-COMPATIBLE Chat Completions API at
https://api.subq.ai/v1 with a very large context window (subq-preview =
~1M tokens; the 12M tier is gated to research/enterprise). That makes it the
natural home for the qPlan FULL-CONTEXT lens: feed it the whole plan plus far
more surrounding context (whole files, large reference docs, prior rounds) than
a 200K-window model can hold, "using the huge budget cleverly". Because the API
is OpenAI-shaped, this script is a focused clone of openai_critic.py pointed at
SubQ's base URL + key + model.

Reads JSON from stdin:
  { "task": "...", "plan": "...", "ledger": [...], "model": "<optional>" }
Writes JSON to stdout:
  { "verdict": "...", "suggestions": [...], "provider": "subq", "model": "..." }

Opt-in: requires SUBQ_API_KEY. Without it the script exits non-zero with a clear
message and the qPlan panel silently mutes the `subq` lens (same convention as
the openai / deepseek lenses). Config:
  - SUBQ_API_KEY   (required)   API key from console.subq.ai
  - SUBQ_BASE_URL  (optional)   default https://api.subq.ai/v1
  - SUBQ_MODEL     (optional)   default subq-preview; or pass "model" on stdin

Stdlib only.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plan_chunker import (  # noqa: E402
    MAX_CHUNK_DEPTH,
    merge_verdicts,
    split_plan,
)

# Reuse the exact critic prompt contract from the OpenAI provider so verdicts
# are directly comparable across providers.
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

You have a very large context window — USE it: reason over the whole plan and
all provided context at once rather than skimming. But do not repeat points
already in the ledger; semantic duplicates waste the round.

Output ONLY the JSON. No prose before or after."""

DEFAULT_BASE_URL = "https://api.subq.ai/v1"
DEFAULT_MODEL = "subq-preview"
HARD_FALLBACK_MODEL = "subq-preview"

MAX_TOTAL_CHUNKS = 8
_total_chunks_submitted = 0


def base_url() -> str:
    return (os.environ.get("SUBQ_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def discover_model(api_key: str) -> str:
    """SubQ is OpenAI-compatible, so /v1/models *may* list models. Try it; on
    any error fall back to the documented default. We do not cache — the model
    set is tiny and the default is almost always right."""
    try:
        req = urllib.request.Request(
            f"{base_url()}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        ids = [m.get("id", "") for m in body.get("data", [])]
        # Prefer a larger-context variant if one is exposed, else the preview.
        for pref in ("subq-preview-12m", "subq-12m", "subq-preview", "subq"):
            for mid in ids:
                if mid == pref:
                    return mid
        # Else first listed model, else default.
        return ids[0] if ids else DEFAULT_MODEL
    except Exception:
        return DEFAULT_MODEL


def call_subq(api_key, model, task, plan, ledger, depth=0) -> dict:
    global _total_chunks_submitted
    _total_chunks_submitted += 1
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": CRITIC_PROMPT},
            {"role": "user", "content": json.dumps(
                {"task": task, "plan": plan, "ledger": ledger}, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        f"{base_url()}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", "replace")
        # SubQ's huge context makes 429 unlikely, but keep the same chunk-on-
        # throttle safety the other providers have.
        if (e.code == 429 and depth < MAX_CHUNK_DEPTH
                and _total_chunks_submitted < MAX_TOTAL_CHUNKS):
            parts = split_plan(plan)
            if len(parts) < 2:
                sys.stderr.write(
                    f"subq_critic: HTTP 429 but plan is atomic at depth {depth}. "
                    f"Response: {body_text}\n")
                sys.exit(2)
            time.sleep(2 ** depth)
            sub = [call_subq(api_key, model, task, p, ledger, depth + 1) for p in parts]
            merged = merge_verdicts(sub)
            merged["_chunks_submitted"] = sum(v.get("_chunks_submitted", 1) for v in sub)
            return merged
        if e.code in (401, 403):
            sys.stderr.write(
                f"subq_critic: HTTP {e.code} — bad or revoked SUBQ_API_KEY.\n")
            sys.exit(2)
        sys.stderr.write(f"subq_critic: HTTP {e.code} — {body_text}\n")
        sys.exit(2)
    except urllib.error.URLError as e:
        sys.stderr.write(f"subq_critic: network error — {e}\n")
        sys.exit(2)

    try:
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, TypeError) as e:
        sys.stderr.write(
            f"subq_critic: unexpected response shape ({type(e).__name__}: {e}). "
            f"Raw body: {json.dumps(body)[:1000]}\n")
        sys.exit(2)
    except json.JSONDecodeError as e:
        sys.stderr.write(
            f"subq_critic: response content was not valid JSON: {e}.\n")
        sys.exit(2)


def main() -> None:
    api_key = os.environ.get("SUBQ_API_KEY")
    if not api_key:
        sys.stderr.write(
            "subq_critic: SUBQ_API_KEY not set. The subq lens is opt-in; set the "
            "key (from console.subq.ai) to enable it, or drop the subq lens.\n")
        sys.exit(2)

    try:
        req_in = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        sys.stderr.write(f"subq_critic: bad JSON on stdin — {e}\n")
        sys.exit(2)

    task = req_in.get("task", "")
    plan = req_in.get("plan", "")
    ledger = req_in.get("ledger", [])
    model = req_in.get("model") or os.environ.get("SUBQ_MODEL") or discover_model(api_key)

    verdict = call_subq(api_key, model, task, plan, ledger)
    verdict["provider"] = "subq"
    verdict["model"] = model
    verdict["chunks_submitted"] = verdict.pop("_chunks_submitted", 1)

    sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
