#!/usr/bin/env python3
"""
qPlan cross-model critic — direct Claude (Anthropic) provider.

WHY THIS EXISTS: in the panel, the `claude` lens means "the current session's
model". When Claude Code is launched on GLM (z.ai) via claude-glm.ps1, that
"current session" is actually a GLM model — so the panel would have NO genuine
Claude voice. This provider restores a TRUE highest-Claude-model voice that is
INDEPENDENT of the active session provider, exactly like openai_critic.py /
deepseek_critic.py are independent. That lets qPlan (and qGoal, which calls
qPlan) cross-check its decisions against Claude even while it runs on GLM.

Two backends, auto-selected:
  - "api": if ANTHROPIC_API_KEY is set -> call the Anthropic Messages API
    directly (pay-per-token), auto-pick the highest Claude model.
  - "cli": else, shell out to `claude -p` (Claude Code headless/print mode) with
    the GLM environment STRIPPED, so the subprocess talks to Anthropic using the
    logged-in Claude SUBSCRIPTION (the OAuth lives in Claude Code's credential
    store, not in env; clearing the GLM base-URL/token overrides restores the
    default Anthropic endpoint + subscription). This is the "use my Claude
    subscription while running on GLM" path. Force with CLAUDE_CRITIC_BACKEND=cli.

Reads JSON from stdin:  { "task","plan","ledger","model"? }
Writes JSON to stdout:  { "verdict","suggestions","provider":"claude-direct","model" }

Opt-in / graceful: if neither backend is available (no ANTHROPIC_API_KEY and no
`claude` CLI), exits non-zero with a clear message and the panel mutes the lens.
Stdlib only.
"""

import json
import os
import re
import shutil
import subprocess
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

`no material issue` with an empty suggestions list is VALID — do not invent a
critique if the plan is sound. Do not repeat points already in the ledger.

Output ONLY the JSON object. Do not use any tools. No prose before or after."""

ANTHROPIC_VERSION = "2023-06-01"

# Highest-first. Un-dated stable alias preferred within a family.
MODEL_PRIORITY = [
    re.compile(r"^claude-opus-4(?:[.-].*)?$"),
    re.compile(r"^claude-sonnet-4(?:[.-].*)?$"),
    re.compile(r"^claude-3-7-sonnet(?:.*)?$"),
    re.compile(r"^claude-3-5-sonnet(?:.*)?$"),
    re.compile(r"^claude-3-opus(?:.*)?$"),
    re.compile(r"^claude-3-5-haiku(?:.*)?$"),
]
HARD_FALLBACK_API_MODEL = "claude-sonnet-4-5"
# GLM launcher env overrides to strip so `claude -p` reaches Anthropic + the
# subscription instead of z.ai.
_GLM_ENV_KEYS = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_SMALL_FAST_MODEL",
    "ANTHROPIC_MODEL",
    "ZAI_API_KEY",
)


# --- pure helpers (unit-testable, no network/subprocess) ------------------

def build_prompt(task: str, plan: str, ledger: list) -> str:
    payload = json.dumps({"task": task, "plan": plan, "ledger": ledger}, ensure_ascii=False)
    return f"{CRITIC_PROMPT}\n\nINPUT:\n{payload}\n\nOutput ONLY the JSON object."


def sanitized_env(env: dict) -> dict:
    """Return a copy of env with the GLM/z.ai overrides removed so a child
    `claude -p` uses the default Anthropic endpoint + the subscription."""
    out = dict(env)
    for k in _GLM_ENV_KEYS:
        out.pop(k, None)
    return out


def extract_json(text: str) -> dict:
    """Tolerantly extract the first balanced top-level JSON object from text
    (models sometimes wrap JSON in prose or fences despite instructions)."""
    if not text:
        raise ValueError("empty text")
    # Fast path.
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
                        candidate = text[start:i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break
        start = text.find("{", start + 1)
    raise ValueError("no valid JSON object found in text")


def pick_backend() -> str:
    forced = os.environ.get("CLAUDE_CRITIC_BACKEND")
    if forced in ("api", "cli"):
        return forced
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "api"
    if shutil.which("claude"):
        return "cli"
    return "none"


# --- API backend ----------------------------------------------------------

def _api_list_models(api_key: str) -> list:
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/models",
        headers={"x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return [m.get("id", "") for m in body.get("data", [])]


def _api_pick_model(api_key: str) -> str:
    try:
        available = _api_list_models(api_key)
    except Exception:
        return HARD_FALLBACK_API_MODEL
    for pat in MODEL_PRIORITY:
        matches = [m for m in available if pat.match(m)]
        if matches:
            stable = [m for m in matches if not re.search(r"-\d{8}$", m)]
            return (stable or sorted(matches, reverse=True))[0]
    return available[0] if available else HARD_FALLBACK_API_MODEL


def call_api(api_key: str, model: str, prompt: str) -> dict:
    payload = {
        "model": model,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"claude_critic[api]: HTTP {e.code} — {e.read().decode('utf-8','replace')}\n")
        sys.exit(2)
    except urllib.error.URLError as e:
        sys.stderr.write(f"claude_critic[api]: network error — {e}\n")
        sys.exit(2)
    try:
        text = "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
        return extract_json(text)
    except (ValueError, KeyError, TypeError) as e:
        sys.stderr.write(f"claude_critic[api]: bad response ({e}). Raw: {json.dumps(body)[:800]}\n")
        sys.exit(2)


# --- CLI (subscription) backend -------------------------------------------

def call_cli(model_alias: str, prompt: str) -> dict:
    claude_bin = shutil.which("claude")
    if not claude_bin:
        sys.stderr.write("claude_critic[cli]: `claude` CLI not found on PATH.\n")
        sys.exit(2)
    args = [claude_bin, "-p", "--output-format", "json", "--model", model_alias]
    env = sanitized_env(os.environ)
    try:
        proc = subprocess.run(
            args, input=prompt, capture_output=True, text=True,
            env=env, timeout=240,
        )
    except subprocess.TimeoutExpired:
        sys.stderr.write("claude_critic[cli]: `claude -p` timed out.\n")
        sys.exit(2)
    if proc.returncode != 0:
        sys.stderr.write(f"claude_critic[cli]: `claude -p` exit {proc.returncode}: {proc.stderr[:800]}\n")
        sys.exit(2)
    # --output-format json wraps the answer; the critic JSON is inside `result`.
    raw = proc.stdout.strip()
    try:
        envelope = json.loads(raw)
        inner = envelope.get("result", raw) if isinstance(envelope, dict) else raw
    except json.JSONDecodeError:
        inner = raw
    try:
        return extract_json(inner if isinstance(inner, str) else json.dumps(inner))
    except ValueError as e:
        sys.stderr.write(f"claude_critic[cli]: could not parse verdict JSON ({e}). Raw: {raw[:800]}\n")
        sys.exit(2)


def main() -> None:
    backend = pick_backend()
    if backend == "none":
        sys.stderr.write(
            "claude_critic: no backend available — set ANTHROPIC_API_KEY (api "
            "backend) or ensure the `claude` CLI is installed (cli/subscription "
            "backend). The claude-direct lens is opt-in; the panel mutes it when "
            "unavailable.\n")
        sys.exit(2)

    try:
        req_in = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        sys.stderr.write(f"claude_critic: bad JSON on stdin — {e}\n")
        sys.exit(2)

    prompt = build_prompt(req_in.get("task", ""), req_in.get("plan", ""), req_in.get("ledger", []))
    override = req_in.get("model")

    if backend == "api":
        api_key = os.environ["ANTHROPIC_API_KEY"]
        model = override or _api_pick_model(api_key)
        verdict = call_api(api_key, model, prompt)
        model_used = model
    else:  # cli / subscription
        model_alias = override or "opus"
        verdict = call_cli(model_alias, prompt)
        model_used = f"subscription:{model_alias}"

    verdict["provider"] = "claude-direct"
    verdict["model"] = model_used
    verdict["backend"] = backend
    sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
