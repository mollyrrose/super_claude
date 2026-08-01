#!/usr/bin/env python3
"""Smoketest for memgraph_prompt_hook.py. Run: python memgraph_prompt_hook_smoketest.py"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "memgraph_prompt_hook.py"


def run(payload: str, env_extra: dict) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def main() -> int:
    fails = 0
    now = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory() as td:
        queue = Path(td) / "q.json"
        state = Path(td) / "s.json"
        env = {"MEMGRAPH_QUEUE": str(queue), "MEMGRAPH_STATE": str(state)}
        payload_a = json.dumps({"session_id": "sess-A", "prompt": "hi"})

        # 1. no queue file -> no output, exit 0
        r = run(payload_a, env)
        ok = r.returncode == 0 and not r.stdout.strip()
        print(("pass" if ok else "FAIL") + " missing queue is silent")
        fails += 0 if ok else 1

        # 2. one fresh entry -> below threshold, silent
        queue.write_text(
            json.dumps([{"session_id": "s1", "ts": now.isoformat(timespec="seconds")}]),
            encoding="utf-8",
        )
        r = run(payload_a, env)
        ok = r.returncode == 0 and not r.stdout.strip()
        print(("pass" if ok else "FAIL") + " below threshold is silent")
        fails += 0 if ok else 1

        # 3. two entries -> inject; verify state file is written with correct session id
        queue.write_text(
            json.dumps(
                [
                    {"session_id": "s1", "ts": now.isoformat(timespec="seconds")},
                    {"session_id": "s2", "ts": now.isoformat(timespec="seconds")},
                ]
            ),
            encoding="utf-8",
        )
        r = run(payload_a, env)
        out = json.loads(r.stdout) if r.stdout.strip() else {}
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        state_data = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {}
        ok = (
            r.returncode == 0
            and "memgraph-ingest" in ctx
            and state_data.get("last_inject_session") == "sess-A"
        )
        print(("pass" if ok else "FAIL") + " threshold reached injects nudge and writes state")
        fails += 0 if ok else 1

        # 4. same session again -> once-per-session guard, silent
        r = run(payload_a, env)
        ok = r.returncode == 0 and not r.stdout.strip()
        print(("pass" if ok else "FAIL") + " once-per-session guard holds")
        fails += 0 if ok else 1

        # 5. old single entry (>48h) in a NEW session -> inject
        queue.write_text(
            json.dumps(
                [
                    {
                        "session_id": "s1",
                        "ts": (now - timedelta(hours=72)).isoformat(timespec="seconds"),
                    }
                ]
            ),
            encoding="utf-8",
        )
        r = run(json.dumps({"session_id": "sess-B"}), env)
        out = json.loads(r.stdout) if r.stdout.strip() else {}
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        ok = r.returncode == 0 and "memgraph-ingest" in ctx
        print(("pass" if ok else "FAIL") + " stale entry triggers on age")
        fails += 0 if ok else 1

        # 6. kill switch -- use "sess-C", a FRESH session id not seen before, so
        #    the once-per-session guard cannot fire and mask the kill switch test.
        queue.write_text(
            json.dumps(
                [
                    {"session_id": "s1", "ts": now.isoformat(timespec="seconds")},
                    {"session_id": "s2", "ts": now.isoformat(timespec="seconds")},
                ]
            ),
            encoding="utf-8",
        )
        r = run(
            json.dumps({"session_id": "sess-C", "prompt": "hi"}),
            {**env, "MEMGRAPH_DISABLE": "1"},
        )
        ok = r.returncode == 0 and not r.stdout.strip()
        print(("pass" if ok else "FAIL") + " MEMGRAPH_DISABLE=1 is a no-op")
        fails += 0 if ok else 1

        # 7. naive timestamp (no timezone suffix) -> must not crash; must handle
        #    coercion to UTC in _parse_ts without TypeError.
        queue.write_text(
            json.dumps(
                [
                    {"session_id": "s1", "ts": "2026-01-01T00:00:00"},  # naive, no +00:00
                    {"session_id": "s2", "ts": "2026-01-01T00:00:00"},
                ]
            ),
            encoding="utf-8",
        )
        r = run(json.dumps({"session_id": "sess-D"}), env)
        ok = r.returncode == 0  # must not crash regardless of injection outcome
        print(("pass" if ok else "FAIL") + " naive timestamp handled without crash")
        fails += 0 if ok else 1

    print("result: " + ("ALL PASS" if fails == 0 else f"{fails} FAILURES"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
