"""Tests for the smart-router eval-log writer in smart_router_prompt_hook.

Run with: python -m unittest test_smart_router_eval_log
from the claude_code_integration directory.

Privacy contract (load-bearing):
- The prompt body never appears in the output JSONL row.
- A logger exception never changes the hook's exit code or stdout output.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class _IsolatedLogPath:
    """Patches CLAUDE_CONFIG_DIR + reloads the hook so EVAL_LOG_PATH resolves to a tmpdir."""

    def __init__(self, tmpdir: Path):
        self.tmpdir = tmpdir
        self._old_env = None

    def __enter__(self):
        self._old_env = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.tmpdir)
        # Re-import the hook so module-level EVAL_LOG_PATH picks up the env var.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        for mod_name in ("smart_router_prompt_hook",):
            sys.modules.pop(mod_name, None)
        import smart_router_prompt_hook  # noqa: F401

        return smart_router_prompt_hook

    def __exit__(self, *_):
        if self._old_env is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = self._old_env


class TestEvalLogPrivacy(unittest.TestCase):
    def _run_hook_with_payload(self, payload: dict, tmpdir: Path) -> tuple[int, str]:
        """Invoke smart_router_prompt_hook.main() with a JSON stdin payload."""
        raw = json.dumps(payload)
        with _IsolatedLogPath(tmpdir) as hook:
            with mock.patch.object(sys, "stdin", io.StringIO(raw)):
                stdout_buf = io.StringIO()
                with mock.patch.object(sys, "stdout", stdout_buf):
                    rc = hook.main()
                return rc, stdout_buf.getvalue()

    def test_prompt_body_never_appears_in_log(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            distinctive = "DOLPHIN-MAGIC-FLAMINGO-12345"
            payload = {
                "prompt": f"the {distinctive} crashed at startup",
                "session_id": "test-sid",
                "cwd": "D:\\projects\\super_claude",
            }
            self._run_hook_with_payload(payload, tmpdir)

            log_file = tmpdir / ".smart_router_eval.jsonl"
            self.assertTrue(log_file.exists(), "logger must write the row")
            text = log_file.read_text(encoding="utf-8")
            self.assertNotIn(
                distinctive, text, "prompt body must NEVER appear in the log"
            )

    def test_hash_format_is_16_hex(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            payload = {
                "prompt": "Traceback ValueError in foo.py",
                "session_id": "test-sid",
                "cwd": "D:\\projects\\super_claude",
            }
            self._run_hook_with_payload(payload, tmpdir)

            row = json.loads((tmpdir / ".smart_router_eval.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(len(row["prompt_hash"]), 16)
            expected = hashlib.sha256(payload["prompt"].encode()).hexdigest()[:16]
            self.assertEqual(row["prompt_hash"], expected)

    def test_logger_exception_does_not_break_hook(self):
        """A forced logger crash must not change exit code or stdout."""
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            payload = {
                "prompt": "Traceback ValueError in foo.py",
                "session_id": "test-sid",
                "cwd": "D:\\projects\\super_claude",
            }
            # First confirm baseline output without crashing logger.
            rc_ok, stdout_ok = self._run_hook_with_payload(payload, tmpdir)
            # Now force the logger to raise.
            with _IsolatedLogPath(tmpdir) as hook:
                with mock.patch.object(
                    hook, "_log_eval_row", side_effect=RuntimeError("boom")
                ):
                    raw = json.dumps(payload)
                    with mock.patch.object(sys, "stdin", io.StringIO(raw)):
                        stdout_buf = io.StringIO()
                        with mock.patch.object(sys, "stdout", stdout_buf):
                            rc_crash = hook.main()
                            stdout_crash = stdout_buf.getvalue()

            self.assertEqual(rc_crash, rc_ok)
            self.assertEqual(stdout_crash, stdout_ok)

    def test_suggested_skill_captured_when_present(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            # Use a prompt the smart router actually classifies as a bug → /hunt.
            payload = {
                "prompt": "Traceback (most recent call last): ValueError in foo.py",
                "session_id": "test-sid",
                "cwd": "D:\\projects\\super_claude",
            }
            self._run_hook_with_payload(payload, tmpdir)
            row = json.loads((tmpdir / ".smart_router_eval.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(row["suggested_skill_or_null"], "/hunt")

    def test_no_suggestion_logged_as_null(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            payload = {
                "prompt": "hi there how are you doing today",  # neutral, no rule matches
                "session_id": "test-sid",
                "cwd": "D:\\projects\\super_claude",
            }
            self._run_hook_with_payload(payload, tmpdir)
            row = json.loads((tmpdir / ".smart_router_eval.jsonl").read_text(encoding="utf-8"))
            self.assertIsNone(row["suggested_skill_or_null"])

    def test_project_slug_matches_claude_code_pattern(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            payload = {
                "prompt": "Traceback ValueError in foo.py",
                "session_id": "test-sid",
                "cwd": "D:\\projects\\super_claude",
            }
            self._run_hook_with_payload(payload, tmpdir)
            row = json.loads((tmpdir / ".smart_router_eval.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(row["project"], "D--projects-super-claude")


if __name__ == "__main__":
    unittest.main()
