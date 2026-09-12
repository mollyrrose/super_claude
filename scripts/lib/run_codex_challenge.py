#!/usr/bin/env python3
"""Adversarial code reviewer for qRev and pentest skills.

Priority: local LLM (no key) -> hosted API (opt-in) -> Codex CLI -> skip.

Local LLM: auto-detects llama.cpp (8080), Ollama (11434), LM Studio (1234).
Override with QREV_LOCAL_LLM_URL. No API key required for local mode.

Hosted API: OPT-IN, off by default, because it spends the user's API money.
Set QREV_CHALLENGE_API=deepseek|openai to enable; the key comes from
DEEPSEEK_API_KEY / OPENAI_API_KEY (or CODEX_API_KEY). It speaks the same
OpenAI-compatible chat-completions protocol as the local backend, so no
extra binary is needed. The model is the highest-capability one the key can
reach (discovered via /v1/models, cached 24h); override with
QREV_CHALLENGE_MODEL.

Codex CLI: fallback when neither of the above produced a review; requires
OPENAI_API_KEY or CODEX_API_KEY or ~/.codex/auth.json plus the `codex`
binary on PATH.

Usage:
    python run_codex_challenge.py --scope <file> --base <branch> [--focus <topic>] [--timeout <sec>] --json
    python run_codex_challenge.py --probe            # which backends are available
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


# --- local LLM detection (no API key) ---

_LOCAL_LLM_CANDIDATES = [
    ("http://127.0.0.1:8080/v1", "llama.cpp"),
    ("http://127.0.0.1:11434/v1", "Ollama"),
    ("http://127.0.0.1:1234/v1", "LM Studio"),
]


def check_local_llm() -> tuple[bool, str, str]:
    """Auto-detect a running local LLM server. Returns (ok, base_url, name)."""
    custom = os.environ.get("QREV_LOCAL_LLM_URL", "")
    candidates = ([(custom, "custom (QREV_LOCAL_LLM_URL)")] if custom else []) + _LOCAL_LLM_CANDIDATES

    for url, name in candidates:
        try:
            req = urllib.request.Request(
                f"{url}/models",
                headers={"Authorization": "Bearer none"},
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True, url, name
        except Exception:
            continue
    return False, "", "no local LLM server found (tried ports 8080/11434/1234; set QREV_LOCAL_LLM_URL to override)"


def call_local_llm(base_url: str, prompt: str, timeout_sec: int = 300) -> dict[str, Any]:
    """POST to an OpenAI-compatible local LLM. No API key required."""
    payload = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.7,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer none"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            return {"success": True, "text": text, "tokens_used": tokens}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"LOCAL_LLM_ERROR: {e}"}
    except (KeyError, json.JSONDecodeError, IndexError) as e:
        return {"success": False, "error": f"LOCAL_LLM_PARSE_ERROR: {e}"}


def parse_local_llm_findings(text: str) -> dict[str, Any]:
    """Extract [P1]/[P2] findings from plain-text LLM response."""
    p1_findings: list[str] = []
    p2_findings: list[str] = []
    other_findings: list[str] = []

    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if "[P1]" in para:
            p1_findings.append(para)
        elif "[P2]" in para:
            p2_findings.append(para)
        elif re.match(r"^[\d\-\*]", para) or any(
            kw in para.lower()
            for kw in ["vulnerability", "injection", "race condition", "leak", "overflow", "bypass", "exposure"]
        ):
            other_findings.append(para)

    return {
        "p1_findings": p1_findings,
        "p2_findings": p2_findings + other_findings,
        "all_findings": p1_findings + p2_findings + other_findings,
    }


# --- hosted API backend (opt-in, OpenAI-compatible: DeepSeek / OpenAI) ---

# Opt-in ONLY. Default off so a /qRev never spends the user's API money
# without them asking for it. The local-LLM backend above stays the free
# default; this is the "no binary, no local model, but I do have a key" path.
_API_PROVIDERS: dict[str, dict[str, Any]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "key_envs": ("DEEPSEEK_API_KEY",),
        # Best-first; mirrors qPlan's deepseek_critic.py MODEL_PRIORITY.
        "priority": [
            r"^deepseek-v4-pro$",
            r"^deepseek-v4-flash$",
            r"^deepseek-v3-pro$",
            r"^deepseek-v3-flash$",
            r"^deepseek-reasoner$",
            r"^deepseek-chat$",
            r"^deepseek-coder$",
        ],
        "fallback": "deepseek-chat",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "key_envs": ("CODEX_API_KEY", "OPENAI_API_KEY"),
        # Best-first; mirrors qPlan's openai_critic.py MODEL_PRIORITY.
        "priority": [
            r"^gpt-5\.5(?:-\d{4}-\d{2}-\d{2})?$",
            r"^gpt-5\.1(?:-\d{4}-\d{2}-\d{2})?$",
            r"^gpt-5(?:-\d{4}-\d{2}-\d{2})?$",
            r"^o3-pro(?:-\d{4}-\d{2}-\d{2})?$",
            r"^o3(?:-\d{4}-\d{2}-\d{2})?$",
            r"^gpt-4\.1(?:-\d{4}-\d{2}-\d{2})?$",
            r"^gpt-4o(?:-\d{4}-\d{2}-\d{2})?$",
        ],
        "fallback": "gpt-4o",
    },
}

_API_MODEL_CACHE = Path.home() / ".claude" / ".qrev_challenge_model_cache.json"
_API_CACHE_TTL_HOURS = 24.0
_API_OFF_VALUES = ("", "0", "off", "no", "none", "false")


def _api_key_for(provider: str) -> str:
    """First non-empty key env for the provider ('' when none is set)."""
    for env in _API_PROVIDERS.get(provider, {}).get("key_envs", ()):
        val = os.environ.get(env)
        if val:
            return val
    return ""


def check_api_backend() -> tuple[bool, str, str]:
    """Resolve the opt-in hosted API backend. Returns (ok, provider, reason)."""
    raw = (os.environ.get("QREV_CHALLENGE_API") or "").strip().lower()
    if raw in _API_OFF_VALUES:
        return False, "", "hosted API off (set QREV_CHALLENGE_API=deepseek|openai)"
    if raw not in _API_PROVIDERS:
        known = ", ".join(sorted(_API_PROVIDERS))
        return False, "", f"unknown QREV_CHALLENGE_API={raw!r} (expected one of: {known})"
    if not _api_key_for(raw):
        envs = " or ".join(_API_PROVIDERS[raw]["key_envs"])
        return False, raw, f"{raw}: no API key ({envs} unset)"
    return True, raw, f"{raw} API"


def _api_list_models(provider: str, api_key: str) -> list[str]:
    req = urllib.request.Request(
        f"{_API_PROVIDERS[provider]['base_url']}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return [m["id"] for m in body.get("data", []) if isinstance(m, dict) and m.get("id")]


def _api_pick_best(provider: str, available: list[str]) -> str | None:
    """Highest-priority model present in `available` (best-first list)."""
    for pattern in _API_PROVIDERS[provider]["priority"]:
        matches = [m for m in available if re.match(pattern, m)]
        if not matches:
            continue
        # Prefer the un-dated stable alias -- providers keep it pointed at
        # the latest snapshot of that family.
        stable = [m for m in matches if not re.search(r"-\d{4}-\d{2}-\d{2}$", m)]
        if stable:
            return stable[0]
        return sorted(matches)[-1]
    return None


def _api_read_cache(provider: str, allow_stale: bool = False) -> str | None:
    try:
        cache = json.loads(_API_MODEL_CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    entry = cache.get(provider) if isinstance(cache, dict) else None
    if not isinstance(entry, dict):
        return None
    model = entry.get("model")
    if not model:
        return None
    if allow_stale:
        return model
    try:
        age_hours = (time.time() - float(entry.get("fetched_at", 0))) / 3600.0
    except (TypeError, ValueError):
        return None
    return model if age_hours < _API_CACHE_TTL_HOURS else None


def _api_write_cache(provider: str, model: str) -> None:
    try:
        cache = json.loads(_API_MODEL_CACHE.read_text(encoding="utf-8"))
        if not isinstance(cache, dict):
            cache = {}
    except (OSError, json.JSONDecodeError):
        cache = {}
    cache[provider] = {"model": model, "fetched_at": time.time()}
    try:
        _API_MODEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _API_MODEL_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except OSError:
        pass  # the cache is an optimisation -- never fatal


def discover_api_model(provider: str, api_key: str) -> str:
    """Highest-capability model the key can reach. 24h cached, never fatal."""
    override = (os.environ.get("QREV_CHALLENGE_MODEL") or "").strip()
    if override:
        return override
    refresh = (os.environ.get("QREV_CHALLENGE_MODEL_REFRESH") or "").strip().lower()
    if refresh not in ("1", "true", "yes"):
        fresh = _api_read_cache(provider)
        if fresh:
            return fresh
    try:
        available = _api_list_models(provider, api_key)
    except Exception:
        # /v1/models unreachable (network, bad key, provider down) -- a stale
        # pick still beats failing the whole challenge.
        return _api_read_cache(provider, allow_stale=True) or _API_PROVIDERS[provider]["fallback"]
    best = _api_pick_best(provider, available) or _API_PROVIDERS[provider]["fallback"]
    _api_write_cache(provider, best)
    return best


def call_api_llm(provider: str, prompt: str, timeout_sec: int = 300) -> dict[str, Any]:
    """POST to a hosted OpenAI-compatible chat API (DeepSeek / OpenAI)."""
    api_key = _api_key_for(provider)
    if not api_key:
        return {"success": False, "error": f"API_KEY_MISSING: {provider}"}
    model = discover_api_model(provider, api_key)

    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    # gpt-5.x and the o-series reject a custom temperature and the legacy
    # max_tokens field with HTTP 400 -- send neither for those families.
    if not re.match(r"^(gpt-5|o\d)", model):
        payload["temperature"] = 0.3
        payload["max_tokens"] = 4096

    req = urllib.request.Request(
        f"{_API_PROVIDERS[provider]['base_url']}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return {"success": True, "text": text, "tokens_used": tokens, "model": model}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        return {"success": False, "error": f"API_HTTP_{e.code}: {body}", "model": model}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"API_ERROR: {e}", "model": model}
    except (KeyError, json.JSONDecodeError, IndexError) as e:
        return {"success": False, "error": f"API_PARSE_ERROR: {e}", "model": model}


# --- Codex CLI backend (fallback, requires API key) ---

def check_codex_binary() -> tuple[bool, str]:
    """Check if codex binary is available."""
    codex_bin = os.environ.get("CODEX_BIN") or "codex"
    if not shutil.which(codex_bin):
        return False, "codex binary not found in PATH"
    use_shell = sys.platform == "win32"
    try:
        result = subprocess.run(
            [codex_bin, "--version"], capture_output=True, text=True, timeout=5, shell=use_shell
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, f"codex --version failed: {result.stderr}"
    except FileNotFoundError:
        return False, "codex binary not found in PATH"
    except subprocess.TimeoutExpired:
        return False, "codex --version timed out"


def check_codex_auth() -> tuple[bool, str]:
    """Check if Codex CLI has valid authentication."""
    if os.environ.get("CODEX_API_KEY"):
        return True, "CODEX_API_KEY set"
    if os.environ.get("OPENAI_API_KEY"):
        return True, "OPENAI_API_KEY set"
    codex_home = os.environ.get("CODEX_HOME", os.path.expanduser("~/.codex"))
    auth_file = Path(codex_home) / "auth.json"
    if auth_file.exists():
        return True, f"auth.json found at {auth_file}"
    return False, "No Codex auth: CODEX_API_KEY, OPENAI_API_KEY, or ~/.codex/auth.json required"


# --- shared prompt builder ---

def build_adversarial_prompt(
    scope_files: list[str],
    base_branch: str,
    focus: str | None = None,
    include_format_hint: bool = True,
) -> str:
    """Build the adversarial review prompt."""
    repo_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True
    ).stdout.strip()

    diff_cmd = ["git", "diff", f"origin/{base_branch}...HEAD"]
    try:
        diff_result = subprocess.run(diff_cmd, capture_output=True, text=True, cwd=repo_root, timeout=30)
        if diff_result.returncode != 0:
            diff_cmd = ["git", "diff", f"{base_branch}...HEAD"]
            diff_result = subprocess.run(diff_cmd, capture_output=True, text=True, cwd=repo_root, timeout=30)
    except subprocess.TimeoutExpired:
        diff_result = subprocess.CompletedProcess(diff_cmd, -1, "", "git diff timed out")

    diff_text = diff_result.stdout if diff_result.returncode == 0 else f"(diff unavailable: {diff_result.stderr})"

    boundary = (
        "IMPORTANT: Do NOT read or execute any files under ~/.claude/, ~/.agents/, "
        ".claude/skills/, or agents/. Stay focused on repository code only."
    )

    format_hint = (
        "\n\nFormat: mark critical findings with [P1] and advisory findings with [P2] "
        "at the start of each paragraph. Example:\n"
        "[P1] SQL injection at api/users.py:42 -- unsanitized input in raw query.\n"
        "[P2] Missing rate limiting on /login -- brute force vector."
    ) if include_format_hint else ""

    if focus:
        body = (
            f"Review the changes against the base branch. Focus specifically on {focus.upper()}. "
            "Find every way an attacker could exploit this code. Think about injection, "
            "auth bypasses, privilege escalation, data exposure, timing attacks. Be adversarial."
        )
    else:
        body = (
            "Review the changes against the base branch. Find ways this code will fail in "
            "production. Think like an attacker and chaos engineer: edge cases, race conditions, "
            "security holes, resource leaks, silent data corruption. Be adversarial. No compliments."
        )

    return f"{boundary}\n\n{body}{format_hint}\n\nTHE DIFF:\n{diff_text}"


# --- JSONL parser for Codex CLI output ---

def parse_codex_jsonl(output: str) -> dict[str, Any]:
    """Parse Codex CLI JSONL output for reasoning traces, findings, token usage."""
    findings: list[str] = []
    reasoning_traces: list[str] = []
    tokens_used = 0
    turn_completed = 0

    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            t = obj.get("type", "")
            if t == "item.completed" and "item" in obj:
                item = obj["item"]
                itype = item.get("type", "")
                text = item.get("text", "")
                if itype == "reasoning" and text:
                    reasoning_traces.append(text)
                elif itype == "agent_message" and text:
                    findings.append(text)
            elif t == "turn.completed":
                turn_completed += 1
                usage = obj.get("usage", {})
                tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                if tokens:
                    tokens_used = tokens
        except json.JSONDecodeError:
            continue

    return {
        "findings": findings,
        "reasoning_traces": reasoning_traces,
        "tokens_used": tokens_used,
        "turns_completed": turn_completed,
    }


# --- main runner ---

def run_codex_challenge(
    scope_files: list[str],
    base_branch: str,
    focus: str | None = None,
    timeout_sec: int = 600,
    reasoning_effort: str = "high",
) -> dict[str, Any]:
    """Run the adversarial code reviewer.

    Priority: local LLM (no API key) -> hosted API (opt-in) -> Codex CLI -> skip.
    """
    prompt = build_adversarial_prompt(scope_files, base_branch, focus, include_format_hint=True)

    # 1. Try local LLM first -- no API key required
    llm_ok, llm_url, llm_name = check_local_llm()
    if llm_ok:
        start_time = time.time()
        llm_result = call_local_llm(llm_url, prompt, timeout_sec=timeout_sec)
        elapsed = time.time() - start_time

        if llm_result["success"]:
            parsed = parse_local_llm_findings(llm_result["text"])
            return {
                "success": True,
                "backend": f"local_llm:{llm_name}",
                "exit_code": 0,
                "elapsed_sec": elapsed,
                "tokens_used": llm_result.get("tokens_used", 0),
                "turns_completed": 1,
                "reasoning_traces": [],
                "p1_findings": parsed["p1_findings"],
                "p2_findings": parsed["p2_findings"],
                "all_findings": parsed["all_findings"],
                "gate": "FAIL" if parsed["p1_findings"] else "PASS",
            }
        # local LLM errored -- fall through to the hosted API / Codex CLI

    # 2. Hosted API backend -- opt-in via QREV_CHALLENGE_API=deepseek|openai.
    #    Needs no binary: same chat-completions protocol as the local backend.
    api_ok, api_provider, api_msg = check_api_backend()
    if api_ok:
        start_time = time.time()
        api_result = call_api_llm(api_provider, prompt, timeout_sec=timeout_sec)
        elapsed = time.time() - start_time

        if api_result["success"]:
            parsed = parse_local_llm_findings(api_result["text"])
            return {
                "success": True,
                "backend": f"api:{api_provider}:{api_result.get('model', 'unknown')}",
                "exit_code": 0,
                "elapsed_sec": elapsed,
                "tokens_used": api_result.get("tokens_used", 0),
                "turns_completed": 1,
                "reasoning_traces": [],
                "p1_findings": parsed["p1_findings"],
                "p2_findings": parsed["p2_findings"],
                "all_findings": parsed["all_findings"],
                "gate": "FAIL" if parsed["p1_findings"] else "PASS",
            }
        api_msg = f"{api_provider} API failed: {api_result.get('error', 'unknown')}"
        # API errored -- fall through to Codex CLI

    # 3. Codex CLI fallback (requires the binary AND auth)
    bin_ok, bin_msg = check_codex_binary()
    if not bin_ok:
        return {
            "success": False,
            "error": f"LOCAL_LLM_UNAVAILABLE + API_UNAVAILABLE ({api_msg}) + CODEX_CLI_MISSING: {bin_msg}",
            "exit_code": -1,
            "skip_reason": "no local LLM, no hosted API, no codex binary",
        }

    auth_ok, auth_msg = check_codex_auth()
    if not auth_ok:
        return {
            "success": False,
            "error": f"LOCAL_LLM_UNAVAILABLE + API_UNAVAILABLE ({api_msg}) + CODEX_AUTH_FAILED: {auth_msg}",
            "exit_code": -1,
            "skip_reason": "no local LLM, no hosted API, no codex auth",
        }

    repo_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True
    ).stdout.strip()

    codex_bin = os.environ.get("CODEX_BIN") or "codex"
    cmd = [
        codex_bin, "exec", prompt,
        "-C", repo_root,
        "-s", "read-only",
        "-c", f'model_reasoning_effort="{reasoning_effort}"',
        "--enable", "web_search_cached",
        "--json",
    ]

    stderr_path = None
    use_shell = sys.platform == "win32"
    try:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as tmp_stderr:
            stderr_path = tmp_stderr.name

        start_time = time.time()
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=open(stderr_path, "w"),
            text=True,
            cwd=repo_root,
            shell=use_shell,
        )

        stdout_lines: list[str] = []
        parsed: dict[str, Any] = {
            "findings": [], "reasoning_traces": [], "tokens_used": 0, "turns_completed": 0
        }

        if process.stdout:
            for line in process.stdout:
                stdout_lines.append(line)
                try:
                    obj = json.loads(line.strip())
                    t = obj.get("type", "")
                    if t == "item.completed" and "item" in obj:
                        item = obj["item"]
                        itype = item.get("type", "")
                        text = item.get("text", "")
                        if itype == "reasoning" and text:
                            parsed["reasoning_traces"].append(text)
                        elif itype == "agent_message" and text:
                            parsed["findings"].append(text)
                    elif t == "turn.completed":
                        parsed["turns_completed"] += 1
                        usage = obj.get("usage", {})
                        tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                        if tokens:
                            parsed["tokens_used"] = tokens
                except json.JSONDecodeError:
                    continue

        try:
            exit_code = process.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            elapsed = time.time() - start_time
            stderr_text = ""
            if stderr_path and os.path.exists(stderr_path):
                with open(stderr_path) as f:
                    stderr_text = f.read()
            return {
                "success": False,
                "backend": "codex_cli",
                "error": f"CODEX_TIMEOUT: stalled past {elapsed:.0f}s (timeout {timeout_sec}s)",
                "exit_code": 124,
                "stderr": stderr_text[:2000],
                "partial_findings": parsed["findings"],
                "skip_reason": "timeout",
            }

        elapsed = time.time() - start_time
        stderr_text = ""
        if stderr_path and os.path.exists(stderr_path):
            with open(stderr_path) as f:
                stderr_text = f.read()

        if exit_code != 0 and any(kw in stderr_text.lower() for kw in ["auth", "login", "unauthorized", "401"]):
            return {
                "success": False,
                "backend": "codex_cli",
                "error": f"CODEX_AUTH_ERROR: {stderr_text[:500]}",
                "exit_code": exit_code,
                "stderr": stderr_text[:2000],
                "skip_reason": "auth error",
            }

        full_output = "".join(stdout_lines)
        parsed_full = parse_codex_jsonl(full_output)

        p1_findings = [f for f in parsed_full["findings"] if "[P1]" in f]
        p2_findings = [f for f in parsed_full["findings"] if "[P1]" not in f]

        return {
            "success": exit_code == 0,
            "backend": "codex_cli",
            "exit_code": exit_code,
            "elapsed_sec": elapsed,
            "tokens_used": parsed_full["tokens_used"],
            "turns_completed": parsed_full["turns_completed"],
            "reasoning_traces": parsed_full["reasoning_traces"],
            "p1_findings": p1_findings,
            "p2_findings": p2_findings,
            "all_findings": parsed_full["findings"],
            "stderr": stderr_text[:2000] if stderr_text else "",
            "gate": "FAIL" if p1_findings else "PASS",
        }

    except Exception as e:
        return {
            "success": False,
            "backend": "codex_cli",
            "error": f"CODEX_EXCEPTION: {type(e).__name__}: {e}",
            "exit_code": -1,
            "skip_reason": "exception",
        }
    finally:
        if stderr_path and os.path.exists(stderr_path):
            try:
                os.unlink(stderr_path)
            except OSError:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Adversarial code reviewer for qRev/pentest")
    parser.add_argument("--scope", nargs="+", help="Files to review (required unless --probe)")
    parser.add_argument("--base", default="main", help="Base branch to diff against")
    parser.add_argument("--focus", help="Focus area (security, performance, etc.)")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds")
    parser.add_argument("--reasoning-effort", default="high", choices=["low", "medium", "high", "xhigh"])
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--local-url", help="Override local LLM URL (sets QREV_LOCAL_LLM_URL)")
    parser.add_argument(
        "--api",
        choices=sorted(_API_PROVIDERS),
        help="Enable the hosted API backend for this run (sets QREV_CHALLENGE_API)",
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Report which backends are available and exit (no review, no API call)",
    )

    args = parser.parse_args()

    if args.local_url:
        os.environ["QREV_LOCAL_LLM_URL"] = args.local_url
    if args.api:
        os.environ["QREV_CHALLENGE_API"] = args.api

    if args.probe:
        llm_ok, llm_url, llm_name = check_local_llm()
        api_ok, api_provider, api_msg = check_api_backend()
        bin_ok, bin_msg = check_codex_binary()
        auth_ok, auth_msg = check_codex_auth()
        probe = {
            "local_llm": {"available": llm_ok, "url": llm_url, "name": llm_name},
            "hosted_api": {"available": api_ok, "provider": api_provider, "detail": api_msg},
            "codex_cli": {
                "binary": {"available": bin_ok, "detail": bin_msg},
                "auth": {"available": auth_ok, "detail": auth_msg},
            },
            "usable": llm_ok or api_ok or (bin_ok and auth_ok),
        }
        if args.json:
            json.dump(probe, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            print(f"local LLM : {'OK' if llm_ok else 'no'} -- {llm_url or llm_name}")
            print(f"hosted API: {'OK' if api_ok else 'no'} -- {api_msg}")
            print(f"codex bin : {'OK' if bin_ok else 'no'} -- {bin_msg}")
            print(f"codex auth: {'OK' if auth_ok else 'no'} -- {auth_msg}")
            print(f"=> adversarial review would {'RUN' if probe['usable'] else 'SKIP'}")
        sys.exit(0 if probe["usable"] else 1)

    if not args.scope:
        parser.error("--scope is required unless --probe is given")

    result = run_codex_challenge(
        scope_files=args.scope,
        base_branch=args.base,
        focus=args.focus,
        timeout_sec=args.timeout,
        reasoning_effort=args.reasoning_effort,
    )

    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        backend = result.get("backend", "unknown")
        if result["success"]:
            print(f"Adversarial review [{backend}]: {result['gate']}")
            print(f"  Tokens: {result['tokens_used']} | Time: {result['elapsed_sec']:.1f}s")
            if result["p1_findings"]:
                print(f"  [P1] Critical: {len(result['p1_findings'])}")
                for f in result["p1_findings"][:3]:
                    print(f"    - {f[:120]}")
            if result["p2_findings"]:
                print(f"  [P2] Advisory: {len(result['p2_findings'])}")
                for f in result["p2_findings"][:3]:
                    print(f"    - {f[:120]}")
        else:
            print(f"Adversarial review: SKIPPED ({result.get('skip_reason', 'unknown')})")
            print(f"  Error: {result.get('error', 'unknown')}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
