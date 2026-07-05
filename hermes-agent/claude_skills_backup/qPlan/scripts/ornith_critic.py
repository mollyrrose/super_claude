#!/usr/bin/env python3
"""
qPlan cross-model critic -- Ornith local AI provider.

Connects to a llama-server instance running Ornith 35B at
http://127.0.0.1:8080 (OpenAI-compatible endpoint). No API key required.

Launch the server with start-ornith.ps1 (C:\\llama\\start-ornith.ps1).

Reads JSON from stdin:
  { "task": "...", "plan": "...", "ledger": [...], "model": "<optional>" }

Writes JSON to stdout:
  { "verdict": "...", "suggestions": [...], "provider": "ornith", "model": "...", "chunks_submitted": N }

MUTES (exit 2) if the server is unreachable -- expected when not running.
Kill switch: QPLAN_ORNITH_DISABLE=1
Override endpoint: ORNITH_BASE_URL (default http://127.0.0.1:8080)
Override model name: ORNITH_MODEL (default ornith)

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
try:
    from plan_chunker import MAX_CHUNK_DEPTH, merge_verdicts, split_plan
    _HAS_CHUNKER = True
except ImportError:
    _HAS_CHUNKER = False

DEFAULT_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_MODEL = "ornith"

CRITIC_PROMPT = """You are the Ornith critic in a qPlan author<->critic loop.
You are a local 35B model (Ornith-1.0-APEX) running on the user's own hardware --
independent, unconstrained reasoning from a different model family than the cloud
providers in the panel.

Read the plan and ledger. Produce a JSON verdict EXACTLY in this shape:

{
  "verdict": "major issue" | "minor issue" | "no material issue",
  "suggestions": [
    { "text": "<one concrete actionable point>",
      "tier_hint": "structural" | "behavioral" | "editorial" }
  ]
}

`no material issue` with an empty suggestions list is a VALID outcome.
Do not repeat ledger entries. Output ONLY the JSON. No prose before or after."""

MAX_TOTAL_CHUNKS = 4
_total_chunks_submitted = 0


def call_ornith(base_url: str, model: str, task: str, plan: str, ledger: list, depth: int = 0) -> dict:
    global _total_chunks_submitted
    _total_chunks_submitted += 1
    endpoint = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": CRITIC_PROMPT},
            {"role": "user", "content": json.dumps({"task": task, "plan": plan, "ledger": ledger}, ensure_ascii=False)},
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
        sys.stderr.write(
            f"ornith_critic: server unreachable at {base_url} ({e}). "
            "Start llama-server (start-ornith.ps1) or this lens is muted.\n"
        )
        sys.exit(2)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", "replace")
        if e.code == 429 and _HAS_CHUNKER and depth < MAX_CHUNK_DEPTH and _total_chunks_submitted < MAX_TOTAL_CHUNKS:
            parts = split_plan(plan)
            if len(parts) < 2:
                sys.stderr.write("ornith_critic: 429 but plan atomic, cannot split.\n")
                sys.exit(2)
            time.sleep(2 ** depth)
            sub = [call_ornith(base_url, model, task, p, ledger, depth + 1) for p in parts]
            merged = merge_verdicts(sub)
            merged["_chunks_submitted"] = sum(v.get("_chunks_submitted", 1) for v in sub)
            return merged
        sys.stderr.write(f"ornith_critic: HTTP {e.code} -- {body_text[:400]}\n")
        sys.exit(2)

    try:
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, TypeError) as e:
        sys.stderr.write(f"ornith_critic: unexpected response shape: {e}\n")
        sys.exit(2)
    except json.JSONDecodeError as e:
        # Try to extract JSON if the model added surrounding prose.
        if isinstance(content, str):
            s, end = content.find("{"), content.rfind("}") + 1
            if s >= 0 and end > s:
                try:
                    return json.loads(content[s:end])
                except json.JSONDecodeError:
                    pass
        sys.stderr.write(f"ornith_critic: not valid JSON: {e}. Content: {str(content)[:400]}\n")
        sys.exit(2)


def main() -> None:
    if os.environ.get("QPLAN_ORNITH_DISABLE"):
        sys.stderr.write("ornith_critic: disabled via QPLAN_ORNITH_DISABLE.\n")
        sys.exit(2)

    base_url = os.environ.get("ORNITH_BASE_URL", DEFAULT_BASE_URL)
    model_env = os.environ.get("ORNITH_MODEL", DEFAULT_MODEL)

    try:
        req_in = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        sys.stderr.write(f"ornith_critic: bad JSON on stdin -- {e}\n")
        sys.exit(2)

    task = req_in.get("task", "")
    plan = req_in.get("plan", "")
    ledger = req_in.get("ledger", [])
    model = req_in.get("model") or model_env

    verdict = call_ornith(base_url, model, task, plan, ledger)
    verdict["provider"] = "ornith"
    verdict["model"] = model
    verdict["chunks_submitted"] = verdict.pop("_chunks_submitted", 1)
    sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
