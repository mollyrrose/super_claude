#!/usr/bin/env python3
"""PreCompact hook: snapshot the live transcript JSONL before /compact
rewrites it, then enqueue the snapshot under a `-precompact-<ts>` suffixed
session_id so the curator picks it up on the next drain.

Fail-soft: never blocks the compact path. Bookkeeps a daily marker into
`~/.claude/.coding-days.json` and prunes snapshots older than 90
*coding* days (bicycle principle — calendar days don't count when no
session ran).
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def main() -> int:
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0

    sid = str(payload.get("session_id") or "").strip()
    tpath = str(payload.get("transcript_path") or "").strip()
    if not sid or not tpath:
        return 0
    src = Path(tpath)
    if not src.is_file():
        return 0

    try:
        from coding_days import SNAPSHOT_DIR, prune_snapshots
    except Exception:
        return 0

    ts = int(time.time())
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = SNAPSHOT_DIR / f"{sid}-{ts}.jsonl"
    try:
        shutil.copyfile(src, snapshot)
    except OSError:
        return 0

    try:
        from curator_core import enqueue_session
        enqueue_session(
            session_id=f"{sid}-precompact-{ts}",
            transcript_path=snapshot,
        )
    except Exception:
        pass  # snapshot persists; queue can re-pick on next drain

    # Bicycle calendar already maintained by the Stop hook's
    # skill_lifecycle.record_active_day. Mark today too so a session that
    # only compacts (no Stop hook firing) still ages its snapshots.
    try:
        from skill_lifecycle import record_active_day
        record_active_day()
    except Exception:
        pass

    try:
        prune_snapshots(max_coding_days=90)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
