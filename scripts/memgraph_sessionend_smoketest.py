#!/usr/bin/env python3
"""Smoketest for memgraph_sessionend.py. Run: python memgraph_sessionend_smoketest.py"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "memgraph_sessionend.py"


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
    with tempfile.TemporaryDirectory() as td:
        queue = Path(td) / "q.json"
        transcript = Path(td) / "t.jsonl"
        transcript.write_text("x" * 25_000, encoding="utf-8")
        # MEMGRAPH_PROJECT_ROOT=td so sessions with cwd under td pass the scope filter.
        env = {"MEMGRAPH_QUEUE": str(queue), "MEMGRAPH_PROJECT_ROOT": td}

        # 1. malformed stdin -> exit 0, no queue file
        r = run("not json", env)
        ok = r.returncode == 0 and not queue.exists()
        print(("pass" if ok else "FAIL") + " malformed stdin is a silent no-op")
        fails += 0 if ok else 1

        # 2. valid payload with cwd under project root -> queued once, cwd preserved
        payload = json.dumps(
            {"session_id": "s1", "transcript_path": str(transcript), "cwd": td}
        )
        r = run(payload, env)
        entries = json.loads(queue.read_text(encoding="utf-8")) if queue.exists() else []
        ok = (
            r.returncode == 0
            and len(entries) == 1
            and entries[0]["session_id"] == "s1"
            and entries[0]["cwd"] == td
        )
        print(("pass" if ok else "FAIL") + " valid session is queued with cwd preserved")
        fails += 0 if ok else 1

        # 3. same session again -> deduped
        r = run(payload, env)
        ok = r.returncode == 0
        entries = json.loads(queue.read_text(encoding="utf-8"))
        ok = ok and len(entries) == 1
        print(("pass" if ok else "FAIL") + " duplicate session_id deduped")
        fails += 0 if ok else 1

        # 4. tiny transcript -> skipped
        tiny = Path(td) / "tiny.jsonl"
        tiny.write_text("small", encoding="utf-8")
        r = run(json.dumps({"session_id": "s2", "transcript_path": str(tiny), "cwd": td}), env)
        entries = json.loads(queue.read_text(encoding="utf-8"))
        ok = r.returncode == 0 and len(entries) == 1
        print(("pass" if ok else "FAIL") + " trivial transcript skipped")
        fails += 0 if ok else 1

        # 5. cross-project cwd -> filtered out (not queued)
        other_cwd = str(Path(td).parent)  # parent is NOT under td (the project root)
        r = run(
            json.dumps({"session_id": "s-other", "transcript_path": str(transcript), "cwd": other_cwd}),
            env,
        )
        entries = json.loads(queue.read_text(encoding="utf-8"))
        ok = r.returncode == 0 and len(entries) == 1  # still only s1
        print(("pass" if ok else "FAIL") + " cross-project session filtered out")
        fails += 0 if ok else 1

        # 6. missing cwd -> filtered out (no cwd = not this project)
        r = run(
            json.dumps({"session_id": "s-nocwd", "transcript_path": str(transcript)}),
            env,
        )
        entries = json.loads(queue.read_text(encoding="utf-8"))
        ok = r.returncode == 0 and len(entries) == 1
        print(("pass" if ok else "FAIL") + " missing cwd filtered out")
        fails += 0 if ok else 1

        # 7. kill switch: exit 0, queue unchanged
        r = run(
            json.dumps({"session_id": "s3", "transcript_path": str(transcript), "cwd": td}),
            {**env, "MEMGRAPH_DISABLE": "1"},
        )
        entries = json.loads(queue.read_text(encoding="utf-8"))
        ok = r.returncode == 0 and len(entries) == 1
        print(("pass" if ok else "FAIL") + " MEMGRAPH_DISABLE=1 is a no-op")
        fails += 0 if ok else 1

    print("result: " + ("ALL PASS" if fails == 0 else f"{fails} FAILURES"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
