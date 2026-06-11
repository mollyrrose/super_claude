"""Tests for the verdict-log writer added to qrev_mark_done.

Run with: python -m unittest test_qrev_mark_done_verdict_log
from the claude_code_integration directory.

Contract:
- Without verdict_summary: no JSONL row, state reset still happens.
- With verdict_summary: one JSONL row, state reset still happens.
- Bad input (missing session_id / kind): existing exit-2 behavior preserved.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def _run_main(payload, tmpdir):
    old_env = os.environ.get("CLAUDE_CONFIG_DIR")
    os.environ["CLAUDE_CONFIG_DIR"] = str(tmpdir)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    for mod_name in ("qrev_mark_done",):
        sys.modules.pop(mod_name, None)
    import qrev_mark_done  # noqa: WPS433

    raw = json.dumps(payload) if isinstance(payload, dict) else payload
    try:
        with mock.patch.object(sys, "stdin", io.StringIO(raw)):
            stdout_buf = io.StringIO()
            stderr_buf = io.StringIO()
            with mock.patch.object(sys, "stdout", stdout_buf), mock.patch.object(
                sys, "stderr", stderr_buf
            ):
                rc = qrev_mark_done.main()
            return rc, stdout_buf.getvalue(), stderr_buf.getvalue()
    finally:
        if old_env is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = old_env


class TestQrevVerdictLog(unittest.TestCase):
    def test_no_verdict_summary_no_log_row(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            rc, stdout, _ = _run_main({"session_id": "sid-1", "kind": "qmin"}, tmpdir)
            self.assertEqual(rc, 0)
            # State file written, verdict log NOT written.
            self.assertTrue((tmpdir / ".qrev_auto_state.json").exists())
            self.assertFalse((tmpdir / ".qrev_verdict_log.jsonl").exists())
            self.assertIn("reset", stdout)

    def test_with_verdict_summary_log_row_appears(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            verdict = {"fix_count": 3, "skip_count": 1, "p0": 0, "p1": 1, "p2": 2, "p3": 1}
            rc, stdout, _ = _run_main(
                {"session_id": "sid-2", "kind": "qrev", "verdict_summary": verdict},
                tmpdir,
            )
            self.assertEqual(rc, 0)
            self.assertTrue((tmpdir / ".qrev_auto_state.json").exists())
            log_path = tmpdir / ".qrev_verdict_log.jsonl"
            self.assertTrue(log_path.exists())
            rows = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["session_id"], "sid-2")
            self.assertEqual(rows[0]["kind"], "qrev")
            self.assertEqual(rows[0]["verdict_summary"], verdict)

    def test_bad_input_exit_2_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            rc, _, _ = _run_main({"session_id": "", "kind": "qmin"}, tmpdir)
            self.assertEqual(rc, 2)
            self.assertFalse((tmpdir / ".qrev_verdict_log.jsonl").exists())

    def test_bad_kind_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            rc, _, _ = _run_main({"session_id": "sid-3", "kind": "bogus"}, tmpdir)
            self.assertEqual(rc, 2)
            self.assertFalse((tmpdir / ".qrev_verdict_log.jsonl").exists())

    def test_verdict_summary_not_dict_no_log(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            rc, _, _ = _run_main(
                {"session_id": "sid-4", "kind": "qmin", "verdict_summary": "nope"},
                tmpdir,
            )
            self.assertEqual(rc, 0)
            self.assertFalse((tmpdir / ".qrev_verdict_log.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
