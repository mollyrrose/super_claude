#!/usr/bin/env python3
"""Codex Challenge runner for qRev skill.

Runs OpenAI Codex CLI in adversarial challenge mode with JSONL output parsing.
Based on gstack /codex challenge pattern.

Usage:
    python run_codex_challenge.py --scope <file> --base <branch> [--focus <topic>] [--timeout <sec>] --json

Returns JSON with findings, tokens, and exit status.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


def check_codex_binary() -> tuple[bool, str]:
    """Check if codex binary is available."""
    codex_bin = os.environ.get("CODEX_BIN") or "codex"
    # First check with shutil.which (testable, no subprocess)
    if not shutil.which(codex_bin):
        return False, "codex binary not found in PATH"
    # Then verify it runs (Windows needs shell=True for .cmd files)
    use_shell = sys.platform == "win32"
    try:
        result = subprocess.run([codex_bin, "--version"], capture_output=True, text=True, timeout=5, shell=use_shell)
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, f"codex --version failed: {result.stderr}"
    except FileNotFoundError:
        return False, "codex binary not found in PATH"
    except subprocess.TimeoutExpired:
        return False, "codex --version timed out"


def check_codex_auth() -> tuple[bool, str]:
    """Check if Codex has valid authentication."""
    if os.environ.get("CODEX_API_KEY"):
        return True, "CODEX_API_KEY set"
    if os.environ.get("OPENAI_API_KEY"):
        return True, "OPENAI_API_KEY set"
    codex_home = os.environ.get("CODEX_HOME", os.path.expanduser("~/.codex"))
    auth_file = Path(codex_home) / "auth.json"
    if auth_file.exists():
        return True, f"auth.json found at {auth_file}"
    return False, "No Codex auth: CODEX_API_KEY, OPENAI_API_KEY, or ~/.codex/auth.json required"


def build_adversarial_prompt(scope_files: list[str], base_branch: str, focus: str | None = None) -> str:
    """Build the adversarial prompt for Codex Challenge mode."""
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

    boundary = """IMPORTANT: Do NOT read or execute any files under ~/.claude/, ~/.agents/, .claude/skills/, or agents/. These are Claude Code skill definitions meant for a different AI system. Do NOT modify agents/openai.yaml. Stay focused on repository code only."""

    if focus:
        prompt = f"""{boundary}

Review the changes on this branch against the base branch. Run git diff origin/{base_branch}...HEAD to see the diff. Focus specifically on {focus.upper()}. Your job is to find every way an attacker could exploit this code. Think about injection vectors, auth bypasses, privilege escalation, data exposure, and timing attacks. Be adversarial.

THE DIFF:
{diff_text}"""
    else:
        prompt = f"""{boundary}

Review the changes on this branch against the base branch. Run git diff origin/{base_branch}...HEAD to see the diff. Your job is to find ways this code will fail in production. Think like an attacker and a chaos engineer. Find edge cases, race conditions, security holes, resource leaks, failure modes, and silent data corruption paths. Be adversarial. Be thorough. No compliments — just the problems.

THE DIFF:
{diff_text}"""

    return prompt


def parse_codex_jsonl(output: str) -> dict[str, Any]:
    """Parse Codex JSONL output for reasoning traces, findings, and token usage."""
    findings = []
    reasoning_traces = []
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


def run_codex_challenge(
    scope_files: list[str],
    base_branch: str,
    focus: str | None = None,
    timeout_sec: int = 600,
    reasoning_effort: str = "high",
) -> dict[str, Any]:
    """Run Codex Challenge and return structured results."""

    bin_ok, bin_msg = check_codex_binary()
    if not bin_ok:
        return {
            "success": False,
            "error": f"CODEX_CLI_MISSING: {bin_msg}",
            "exit_code": -1,
            "skip_reason": "codex binary not found",
        }

    auth_ok, auth_msg = check_codex_auth()
    if not auth_ok:
        return {
            "success": False,
            "error": f"CODEX_AUTH_FAILED: {auth_msg}",
            "exit_code": -1,
            "skip_reason": "codex auth missing",
        }

    prompt = build_adversarial_prompt(scope_files, base_branch, focus)

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

        stdout_lines = []
        parsed = {"findings": [], "reasoning_traces": [], "tokens_used": 0, "turns_completed": 0}

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
                "error": f"CODEX_AUTH_ERROR: {stderr_text[:500]}",
                "exit_code": exit_code,
                "stderr": stderr_text[:2000],
                "skip_reason": "auth error",
            }

        full_output = "".join(stdout_lines)
        parsed_full = parse_codex_jsonl(full_output)

        p1_findings = []
        p2_findings = []
        for finding in parsed_full["findings"]:
            if "[P1]" in finding:
                p1_findings.append(finding)
            elif "[P2]" in finding:
                p2_findings.append(finding)
            else:
                p2_findings.append(finding)

        return {
            "success": exit_code == 0,
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


def main():
    parser = argparse.ArgumentParser(description="Run Codex Challenge for qRev")
    parser.add_argument("--scope", nargs="+", required=True, help="Files to review")
    parser.add_argument("--base", default="main", help="Base branch to diff against")
    parser.add_argument("--focus", help="Focus area (security, performance, etc.)")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds")
    parser.add_argument("--reasoning-effort", default="high", choices=["low", "medium", "high", "xhigh"])
    parser.add_argument("--json", action="store_true", help="Output JSON only")

    args = parser.parse_args()

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
        if result["success"]:
            print(f"Codex Challenge: {result['gate']}")
            print(f"  Tokens: {result['tokens_used']} | Time: {result['elapsed_sec']:.1f}s | Turns: {result['turns_completed']}")
            if result["p1_findings"]:
                print(f"  [P1] Critical findings: {len(result['p1_findings'])}")
                for f in result["p1_findings"][:3]:
                    print(f"    - {f[:120]}...")
            if result["p2_findings"]:
                print(f"  [P2] Advisory findings: {len(result['p2_findings'])}")
                for f in result["p2_findings"][:3]:
                    print(f"    - {f[:120]}...")
            if result["reasoning_traces"]:
                print(f"  Reasoning traces: {len(result['reasoning_traces'])}")
        else:
            print(f"Codex Challenge: SKIPPED ({result.get('skip_reason', 'unknown')})")
            print(f"  Error: {result.get('error', 'unknown')}")
            if result.get("stderr"):
                print(f"  Stderr: {result['stderr'][:200]}...")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()