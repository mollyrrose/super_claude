#!/usr/bin/env python3
"""
qPlan cross-model critic — Ornith local AI provider.

Connects to a llama-server instance running the Ornith 35B model at
http://127.0.0.1:8080 (OpenAI-compatible endpoint). No API key required —
local inference only.

Launch the server with:
  cd C:\\llama && .\\llama-server.exe -m C:\\llama\\Ornith-1.0-35B-MTP-APEX-I-Compact.gguf
    -ngl 99 --n-cpu-moe 24 --no-mmap --spec-type draft-mtp --spec-draft-n-max 4
    --flash-attn on -c 32768 --temp 0.2 --top-p 0.95 --repeat-penalty 1.1
    --repeat-last-n 256 --dry-multiplier 0.8 --dry-base 1.75
    --dry-allowed-length 2 --jinja

Reads JSON from stdin:
  { "task": "<original task>",
    "plan": "<current plan.md content>",
    "ledger": [ { "text": "...", "status": "...", "tier": "..." }, ... ],
    "model": "<optional model override, defaults to 'ornith'>" }

Writes JSON to stdout:
  { "verdict": "major issue|minor issue|no material issue",
    "suggestions": [ { "text": "...", "tier_hint": "..." } ],
    "provider": "ornith",
    "model": "<model used>",
    "chunks_submitted": <int> }

MUTES (exit 2) if the local server is not reachable — this is the expected
behaviour when the server is not running. The qPlan round continues with the
remaining providers.

Kill switch: QPLAN_ORNITH_DISABLE=1 (exits 2 immediately, same as mute).
Override endpoint: ORNITH_BASE_URL (default http://127.0.0.1:8080).
Override model name: ORNITH_MODEL (default ornith).

Stdlib only.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Shared chunking helpers — same as the other critic scripts.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from plan_chunker import MAX_CHUNK_DEPTH, merge_verdicts, split_plan
    _HAS_CHUNKER = True
except ImportError:
    _HAS_CHUNKER = False

DEFAULT_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_MODEL = "ornith"

CRITIC_PROMPT = """You are the Ornith critic in a qPlan author<->critic loop.
You are a local 35B parameter model (Ornith) running on the user's own hardware.
Your unique value is independent, unconstrained reasoning from a different model
family than the cloud providers in the panel.

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

MAX_TOTAL_CHUNKS = 4
_total_chunks_submitted = 0


def call_ornith(
    base_url: str,
    model: str,
    task: str,
    plan: str,
    ledger: list,
    depth: int = 0,
) -> dict:
    global _total_chunks_submitted
    _total_chunks_submitted += 1
    endpoint = base_url.rstrip("/") + "/v1/chat/completions"
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
        "temperature": 0.2,
        "top_p": 0.95,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        # Server not running or unreachable — mute, don't crash the round.
        sys.stderr.write(
            f"ornith_critic: server unreachable at {base_url} ({e}). "
            "Start llama-server with the Ornith model, or this lens is muted. "
            "The qPlan round continues with remaining providers.\n"
        )
        sys.exit(2)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", "replace")
        if (
            e.code == 429
            and _HAS_CHUNKER
            and depth < MAX_CHUNK_DEPTH
            and _total_chunks_submitted < MAX_TOTAL_CHUNKS
        ):
            parts = split_plan(plan)
            if len(parts) < 2:
                sys.stderr.write(
                    f"ornith_critic: HTTP 429 but plan is atomic at depth "
                    f"{depth} — cannot split further.\n"
                )
                sys.exit(2)
            sleep_s = 2 ** depth
            sys.stderr.write(
                f"ornith_critic: 429 at depth {depth}, splitting into "
                f"{len(parts)} parts after {sleep_s}s.\n"
            )
            time.sleep(sleep_s)
            sub_verdicts = [
                call_ornith(base_url, model, task, p, ledger, depth + 1)
                for p in parts
            ]
            merged = merge_verdicts(sub_verdicts)
            merged["_chunks_submitted"] = sum(
                v.get("_chunks_submitted", 1) for v in sub_verdicts
            )
            return merged
        # Any other HTTP error from a local server is unusual; mute.
        sys.stderr.write(
            f"ornith_critic: HTTP {e.code} from local server — {body_text[:500]}\n"
        )
        sys.exit(2)

    try:
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, TypeError) as e:
        sys.stderr.write(
            f"ornith_critic: unexpected response shape ({type(e).__name__}: "
            f"{e}). Raw body: {json.dumps(body)[:1000]}\n"
        )
        sys.exit(2)
    except json.JSONDecodeError as e:
        # Try to extract JSON from a response that has surrounding prose.
        if isinstance(content, str):
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start:end])
                except json.JSONDecodeError:
                    pass
        sys.stderr.write(
            f"ornith_critic: response was not valid JSON: {e}. "
            f"Raw content: {str(content)[:500]}\n"
        )
        sys.exit(2)


def main() -> None:
    if os.environ.get("QPLAN_ORNITH_DISABLE"):
        sys.stderr.write("ornith_critic: disabled via QPLAN_ORNITH_DISABLE.\n")
        sys.exit(2)

    base_url = os.environ.get("ORNITH_BASE_URL", DEFAULT_BASE_URL)
    model = os.environ.get("ORNITH_MODEL", DEFAULT_MODEL)

    try:
        req_in = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        sys.stderr.write(f"ornith_critic: bad JSON on stdin — {e}\n")
        sys.exit(2)

    task = req_in.get("task", "")
    plan = req_in.get("plan", "")
    ledger = req_in.get("ledger", [])
    model = req_in.get("model") or model

    verdict = call_ornith(base_url, model, task, plan, ledger)
    verdict["provider"] = "ornith"
    verdict["model"] = model
    verdict["chunks_submitted"] = verdict.pop("_chunks_submitted", 1)

    sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
