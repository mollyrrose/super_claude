#!/usr/bin/env python3
"""Adversarial code reviewer for qRev and pentest skills.

Priority: local LLM (no key) -> Codex CLI -> skip.

Local LLM: auto-detects llama.cpp (8080), Ollama (11434), LM Studio (1234).
Override with QREV_LOCAL_LLM_URL. No API key required for local mode.

Codex CLI: fallback when no local LLM found; requires OPENAI_API_KEY or
CODEX_API_KEY or ~/.codex/auth.json.

Usage:
    python run_codex_challenge.py --scope <file> --base <branch> [--focus <topic>] [--timeout <sec>] --json
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

    Priority: local LLM (no API key) -> Codex CLI -> skip.
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
        # local LLM errored -- fall through to Codex CLI

    # 2. Codex CLI fallback (requires API key)
    bin_ok, bin_msg = check_codex_binary()
    if not bin_ok:
        return {
            "success": False,
            "error": f"LOCAL_LLM_UNAVAILABLE + CODEX_CLI_MISSING: {bin_msg}",
            "exit_code": -1,
            "skip_reason": "no local LLM and no codex binary",
        }

    auth_ok, auth_msg = check_codex_auth()
    if not auth_ok:
        return {
            "success": False,
            "error": f"LOCAL_LLM_UNAVAILABLE + CODEX_AUTH_FAILED: {auth_msg}",
            "exit_code": -1,
            "skip_reason": "no local LLM and no codex auth",
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
    parser.add_argument("--scope", nargs="+", required=True, help="Files to review")
    parser.add_argument("--base", default="main", help="Base branch to diff against")
    parser.add_argument("--focus", help="Focus area (security, performance, etc.)")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds")
    parser.add_argument("--reasoning-effort", default="high", choices=["low", "medium", "high", "xhigh"])
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--local-url", help="Override local LLM URL (sets QREV_LOCAL_LLM_URL)")

    args = parser.parse_args()

    if args.local_url:
        os.environ["QREV_LOCAL_LLM_URL"] = args.local_url

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
