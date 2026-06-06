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

Fails loud (non-zero exit + stderr message) if OPENAI_API_KEY is missing or
the API call errors. Does NOT fall back to a stub or to claude — provider
distinguishability is the whole point of the comparison.

Stdlib only. No `openai` package install needed.
"""

import json
import os
import sys
import urllib.error
import urllib.request

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
        "temperature": 0.3,
    }
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
    model = req_in.get("model") or "gpt-4o"

    verdict = call_openai(api_key, model, task, plan, ledger)
    verdict["provider"] = "openai"
    verdict["model"] = model

    sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
