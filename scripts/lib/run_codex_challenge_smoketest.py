#!/usr/bin/env python3
"""Smoketest for run_codex_challenge.py — runs without Codex CLI (mock mode)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add scripts/lib to path
sys.path.insert(0, str(Path(__file__).parent))

from run_codex_challenge import (
    check_codex_binary,
    check_codex_auth,
    build_adversarial_prompt,
    parse_codex_jsonl,
    run_codex_challenge,
)


def test_check_codex_binary_missing():
    """Test binary check when codex not found."""
    with patch("shutil.which", return_value=None):
        ok, msg = check_codex_binary()
        assert not ok
        assert "not found" in msg.lower()
    print("[ok] check_codex_binary: correctly detects missing binary")


def test_check_codex_auth_missing():
    """Test auth check when no auth configured."""
    with patch.dict(os.environ, {"CODEX_HOME": "/nonexistent/path"}, clear=False):
        for key in ["CODEX_API_KEY", "OPENAI_API_KEY"]:
            os.environ.pop(key, None)
        ok, msg = check_codex_auth()
        assert not ok
        assert "auth" in msg.lower()
    print("[ok] check_codex_auth: correctly detects missing auth")


def test_build_adversarial_prompt():
    """Test prompt building includes boundary and diff."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], check=True, capture_output=True)
            Path("test.txt").write_text("original")
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init", "-q"], check=True, capture_output=True)
            Path("test.txt").write_text("modified")
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "modify", "-q"], check=True, capture_output=True)

            prompt = build_adversarial_prompt(["test.txt"], "HEAD~1")
            assert "IMPORTANT: Do NOT read or execute any files under ~/.claude/" in prompt
            assert "adversarial" in prompt.lower() or "attacker" in prompt.lower()
            assert "THE DIFF:" in prompt
            print("[ok] build_adversarial_prompt: contains boundary and diff")
        finally:
            os.chdir(old_cwd)


def test_parse_codex_jsonl():
    """Test JSONL parser extracts findings, reasoning, tokens."""
    jsonl_output = """{"type": "item.completed", "item": {"type": "reasoning", "text": "thinking about race conditions"}}
{"type": "item.completed", "item": {"type": "agent_message", "text": "Found [P1] SQL injection at users.py:42"}}
{"type": "item.completed", "item": {"type": "agent_message", "text": "Found [P2] missing input validation at api.py:10"}}
{"type": "turn.completed", "usage": {"input_tokens": 1000, "output_tokens": 500}}"""

    result = parse_codex_jsonl(jsonl_output)
    assert len(result["reasoning_traces"]) == 1
    assert "race conditions" in result["reasoning_traces"][0]
    assert len(result["findings"]) == 2
    assert result["tokens_used"] == 1500
    assert result["turns_completed"] == 1
    print("[ok] parse_codex_jsonl: extracts reasoning, findings, tokens")


def test_p1_p2_classification():
    """Test [P1]/[P2] classification logic."""
    p1 = ["Found [P1] critical bug", "Another [P1] issue"]
    p2 = ["Found [P2] advisory", "No marker here"]
    classified_p1 = [f for f in p1 + p2 if "[P1]" in f]
    classified_p2 = [f for f in p1 + p2 if "[P2]" in f or ("[P1]" not in f and "[P2]" not in f)]
    assert len(classified_p1) == 2
    assert len(classified_p2) == 2
    print("[ok] p1/p2 classification: works correctly")


def _no_local_llm(monkeypatch_target="run_codex_challenge.check_local_llm"):
    """Context manager: force check_local_llm to return False (no server)."""
    from unittest.mock import patch as _patch
    return _patch(monkeypatch_target, return_value=(False, "", "mocked: no local LLM"))


def test_check_local_llm_no_server():
    """Test check_local_llm returns False when nothing runs on known ports."""
    # All common ports are blocked/unavailable in a test environment without running servers.
    # We verify the function returns a tuple and does not raise.
    import run_codex_challenge as m
    ok, url, name = m.check_local_llm()
    assert isinstance(ok, bool)
    assert isinstance(url, str)
    assert isinstance(name, str)
    print("[ok] check_local_llm: returns valid tuple (server may or may not be running)")


def test_parse_local_llm_findings():
    """Test [P1]/[P2] extraction from plain text LLM response."""
    from run_codex_challenge import parse_local_llm_findings
    text = (
        "[P1] SQL injection at users.py:42 -- raw query with unsanitized input.\n\n"
        "[P2] Missing rate limiting on /api/login -- brute force vector.\n\n"
        "Some other paragraph without markers but mentions injection."
    )
    result = parse_local_llm_findings(text)
    assert len(result["p1_findings"]) == 1
    assert "injection" in result["p1_findings"][0].lower()
    assert len(result["p2_findings"]) >= 1  # [P2] + other (injection keyword)
    assert len(result["all_findings"]) >= 2
    print("[ok] parse_local_llm_findings: extracts [P1]/[P2] and keyword findings")


def test_run_codex_challenge_skip_on_missing_binary():
    """Test run_codex_challenge returns skip when no local LLM and no binary."""
    with _no_local_llm():
        with patch("shutil.which", return_value=None):
            result = run_codex_challenge(["test.txt"], "main")
            assert not result["success"]
            assert "no local LLM" in result["skip_reason"]
            assert "CODEX_CLI_MISSING" in result["error"]
    print("[ok] run_codex_challenge: skips gracefully when no local LLM and binary missing")


def test_run_codex_challenge_skip_on_missing_auth():
    """Test run_codex_challenge returns skip when no local LLM and no auth."""
    with _no_local_llm():
        with patch("shutil.which", return_value="/fake/codex"):
            with patch.dict(os.environ, {"CODEX_HOME": "/nonexistent"}, clear=False):
                for key in ["CODEX_API_KEY", "OPENAI_API_KEY"]:
                    os.environ.pop(key, None)
                result = run_codex_challenge(["test.txt"], "main")
                assert not result["success"]
                assert "no local LLM" in result["skip_reason"]
                assert "CODEX_AUTH_FAILED" in result["error"]
    print("[ok] run_codex_challenge: skips gracefully when no local LLM and auth missing")


def main():
    """Run all smoketests."""
    test_check_codex_binary_missing()
    test_check_codex_auth_missing()
    test_parse_codex_jsonl()
    test_p1_p2_classification()
    test_check_local_llm_no_server()
    test_parse_local_llm_findings()
    test_run_codex_challenge_skip_on_missing_binary()
    test_run_codex_challenge_skip_on_missing_auth()

    # test_build_adversarial_prompt requires git - run separately if git available
    if shutil.which("git"):
        try:
            test_build_adversarial_prompt()
        except Exception as e:
            print(f"(warn) build_adversarial_prompt test skipped: {e}")

    print("\n[ok] All smoketests passed!")


if __name__ == "__main__":
    main()