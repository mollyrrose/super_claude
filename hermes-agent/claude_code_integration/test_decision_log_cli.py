"""Tests for decision_log_cli — the decision-log data stream writer.

Run with: python -m unittest test_decision_log_cli
from the claude_code_integration directory.

Contract:
- Valid payload: one JSONL row with the normalized schema; ts auto-generated.
- Missing/empty title or decision: exit 1, no row written.
- Invalid outcome: exit 1, no row written.
- Optional fields default cleanly; CLAUDE_CONFIG_DIR controls the path.
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
    sys.modules.pop("decision_log_cli", None)
    import decision_log_cli  # noqa: WPS433

    raw = json.dumps(payload) if isinstance(payload, (dict, list)) else payload
    try:
        with mock.patch.object(sys, "stdin", io.StringIO(raw)):
            stdout_buf = io.StringIO()
            stderr_buf = io.StringIO()
            with mock.patch.object(sys, "stdout", stdout_buf), mock.patch.object(
                sys, "stderr", stderr_buf
            ):
                rc = decision_log_cli.main()
            return rc, stdout_buf.getvalue(), stderr_buf.getvalue()
    finally:
        if old_env is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = old_env


def _rows(tmpdir):
    p = Path(tmpdir) / ".decision_log.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


class TestDecisionLogCli(unittest.TestCase):
    def test_valid_payload_writes_one_row(self):
        with tempfile.TemporaryDirectory() as td:
            payload = {
                "title": "use unit-by-unit recite",
                "decision": "run each mantra unit to full count sequentially",
                "why": "user wants each mantra completed before the next",
                "rejected_alternatives": "round-robin whole block (interleaves units)",
                "revisit_if": "engine gains native sequential mode",
                "project": "mantra_factory",
                "outcome": "open",
                "session_id": "sid-xyz",
            }
            rc, stdout, _ = _run_main(payload, td)
            self.assertEqual(rc, 0)
            rows = _rows(td)
            self.assertEqual(len(rows), 1)
            r = rows[0]
            self.assertEqual(r["title"], "use unit-by-unit recite")
            self.assertEqual(r["project"], "mantra_factory")
            self.assertEqual(r["outcome"], "open")
            self.assertEqual(r["session_id"], "sid-xyz")
            self.assertTrue(r["ts"])  # auto/explicit ts present
            self.assertIn("logged", stdout)

    def test_appends_not_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            base = {"title": "t", "decision": "d"}
            _run_main({**base, "title": "first"}, td)
            _run_main({**base, "title": "second"}, td)
            rows = _rows(td)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["title"], "first")
            self.assertEqual(rows[1]["title"], "second")

    def test_missing_title_exit_1_no_row(self):
        with tempfile.TemporaryDirectory() as td:
            rc, _, stderr = _run_main({"decision": "d"}, td)
            self.assertEqual(rc, 1)
            self.assertEqual(_rows(td), [])
            self.assertIn("title", stderr)

    def test_empty_decision_exit_1_no_row(self):
        with tempfile.TemporaryDirectory() as td:
            rc, _, _ = _run_main({"title": "t", "decision": "   "}, td)
            self.assertEqual(rc, 1)
            self.assertEqual(_rows(td), [])

    def test_bad_outcome_exit_1(self):
        with tempfile.TemporaryDirectory() as td:
            rc, _, _ = _run_main({"title": "t", "decision": "d", "outcome": "maybe"}, td)
            self.assertEqual(rc, 1)
            self.assertEqual(_rows(td), [])

    def test_optional_fields_default(self):
        with tempfile.TemporaryDirectory() as td:
            rc, _, _ = _run_main({"title": "t", "decision": "d"}, td)
            self.assertEqual(rc, 0)
            r = _rows(td)[0]
            self.assertEqual(r["why"], "")
            self.assertEqual(r["rejected_alternatives"], "")
            self.assertEqual(r["revisit_if"], "")
            self.assertEqual(r["outcome"], "open")
            self.assertIsNone(r["session_id"])

    def test_not_object_exit_1(self):
        with tempfile.TemporaryDirectory() as td:
            rc, _, _ = _run_main([1, 2, 3], td)
            self.assertEqual(rc, 1)
            self.assertEqual(_rows(td), [])


if __name__ == "__main__":
    unittest.main()
