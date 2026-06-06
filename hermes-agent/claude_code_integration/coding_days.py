"""Snapshot pruner that ages files by *coding days* (bicycle principle).

A coding day = a UTC date on which a Claude session was active. The
authoritative calendar lives in `~/.claude/.hermes_skill_state.json`
under `state['active_days']`, maintained by
`skill_lifecycle.record_active_day()`. This module only consumes that
calendar — it does not write to it.

Used by the PreCompact hook to delete pre-compact snapshot transcripts
that have aged past N coding days.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

SNAPSHOT_DIR = Path.home() / ".claude" / ".pre-compact-snapshots"
_SKILL_STATE_FILE = Path.home() / ".claude" / ".hermes_skill_state.json"


def _load_active_days() -> List[str]:
    try:
        data = json.loads(_SKILL_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    days = data.get("active_days", []) if isinstance(data, dict) else []
    return [d for d in days if isinstance(d, str)]


def coding_days_since(iso_date: str) -> int:
    """Count distinct coding days STRICTLY AFTER iso_date (YYYY-MM-DD).

    Mirrors `skill_lifecycle._active_days_since` semantics — uses the
    same source-of-truth calendar.
    """
    return sum(1 for d in _load_active_days() if d > iso_date)


def prune_snapshots(max_coding_days: int = 90) -> dict:
    """Delete snapshots older than N coding-days and matching queue entries.

    Snapshot filename pattern: `<sid>-<unix_ts>.jsonl`.
    Queue session_id pattern:  `<sid>-precompact-<unix_ts>`.
    """
    if not SNAPSHOT_DIR.exists():
        return {"checked": 0, "deleted": 0}

    deleted_stems: List[str] = []
    checked = 0
    for f in SNAPSHOT_DIR.glob("*.jsonl"):
        checked += 1
        try:
            ts = int(f.stem.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            continue
        snap_date = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        if coding_days_since(snap_date) > max_coding_days:
            try:
                f.unlink()
                deleted_stems.append(f.stem)
            except OSError:
                continue

    if deleted_stems:
        try:
            from curator_core import load_queue, save_queue  # local import to avoid cycle
            deleted_stem_set = set(deleted_stems)
            keep = [
                e for e in load_queue()
                if e.session_id.replace("-precompact-", "-", 1) not in deleted_stem_set
            ]
            save_queue(keep)
        except Exception:
            pass  # snapshot files already gone; queue cleanup best-effort

    return {"checked": checked, "deleted": len(deleted_stems)}
