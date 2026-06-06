"""Skill usage tracking + deterministic lifecycle management.

Days are counted in **active days** — UTC dates on which a Claude Code
session actually ended (i.e. the Stop hook fired at least once). A
calendar week with zero activity counts as zero days against any
threshold. This means a 3-month break from programming does NOT
archive your library; the clock simply stops.

Two halves:

1. **Usage tracking.** ``record_skill_uses(names)`` is called from the
   Stop hook after parsing the just-finished session's transcript for
   ``Skill`` tool invocations. ``record_active_day()`` is called every
   Stop hook regardless of whether any skill was used, so the global
   active-day calendar stays current. State lives in
   ``~/.claude/.hermes_skill_state.json``.

2. **Lifecycle pass.** ``run_lifecycle_pass()`` is invoked from the
   prompt hook when ``should_run_maintenance()`` is true (defaults to
   once per 7 active days). Fully deterministic — no LLM:

   - Pinned skills (`pinned: true` in SKILL.md frontmatter) are never
     touched.
   - Curator infrastructure skills (hermes-curate, hermes-learn,
     hermes-maintain) are never touched.
   - A skill not used for HERMES_SKILL_STALE_AFTER_DAYS active days
     (default 30) gets a ``stale_since`` stamp in state.
   - A skill not used for HERMES_SKILL_ARCHIVE_AFTER_DAYS active days
     (default 90) is **moved** (not deleted) to
     ~/.claude/skills-archive/<name>/. Fully recoverable.

When a skill has zero usage history, the lifecycle treats its own
mtime on disk as the "added at" date and counts active days since
then. Newly converted skills therefore get the full grace period.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_claude.lifecycle")

STATE_FILE = Path.home() / ".claude" / ".hermes_skill_state.json"
SKILLS_DIR = Path.home() / ".claude" / "skills"
ARCHIVE_DIR = Path.home() / ".claude" / "skills-archive"

DEFAULT_STALE_AFTER_DAYS = 30
DEFAULT_ARCHIVE_AFTER_DAYS = 90
DEFAULT_MAINTENANCE_INTERVAL_DAYS = 7

# Curator's own skill scaffolding. Never archived regardless of usage.
PROTECTED_NAMES = frozenset({"hermes-curate", "hermes-learn", "hermes-maintain"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_state(state: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _days_since(iso: Optional[str]) -> Optional[float]:
    """Calendar days since the given ISO timestamp (legacy helper)."""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0


def _today_iso_date() -> str:
    """Today as a UTC date string, e.g. '2026-06-02'."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _iso_to_date(iso: Optional[str]) -> Optional[str]:
    """Extract the UTC date portion from an ISO timestamp string."""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.strftime("%Y-%m-%d")


def _active_days_since(iso: Optional[str], state: Dict[str, Any]) -> Optional[int]:
    """Count active days *after* the given timestamp's UTC date.

    An active day is a UTC date in ``state['active_days']``. The count
    is **exclusive of** the day on which the event occurred — the day
    of last use does not itself age the skill.

    Returns None when ``iso`` is unparseable.
    """
    target_date = _iso_to_date(iso)
    if target_date is None:
        return None
    active = state.get("active_days") or []
    # active_days is stored sorted; count entries strictly greater than
    # target_date.
    count = 0
    for d in active:
        if isinstance(d, str) and d > target_date:
            count += 1
    return count


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


# ──────────────────────────────────────────────────────────────────────
# Usage tracking
# ──────────────────────────────────────────────────────────────────────

def parse_skill_uses_from_transcript(transcript_path: Path) -> List[str]:
    """Scan a Claude Code JSONL transcript for Skill tool invocations.

    Returns the list of skill names invoked (duplicates included so the
    counter increments correctly).
    """
    used: List[str] = []
    if not transcript_path.exists():
        return used
    try:
        text = transcript_path.read_text(encoding="utf-8")
    except OSError:
        return used

    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Newer transcripts wrap the model message in a "message" field.
        msg = obj.get("message", obj)
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use":
                continue
            if block.get("name") != "Skill":
                continue
            inp = block.get("input")
            if not isinstance(inp, dict):
                continue
            name = inp.get("skill") or inp.get("skill_name")
            if isinstance(name, str) and name.strip():
                used.append(name.strip())
    return used


def record_skill_uses(names: List[str]) -> Dict[str, Any]:
    """Increment usage counters. Re-activates a stale skill on hit."""
    if not names:
        return {"updated": 0}
    state = _read_state()
    skills = state.setdefault("skills", {})
    now = _now_iso()
    updated = 0
    for raw_name in names:
        name = raw_name.strip()
        if not name:
            continue
        entry = skills.setdefault(name, {"total_uses": 0, "first_seen": now})
        entry["last_used"] = now
        entry["total_uses"] = int(entry.get("total_uses", 0)) + 1
        # A use re-activates a previously-stale skill.
        if "stale_since" in entry:
            entry.pop("stale_since", None)
        updated += 1
    _write_state(state)
    return {"updated": updated, "tracked_total": len(skills)}


# Cap the active-day calendar so the state file stays small. ~5 years
# of daily activity = 1825 entries. Above this we trim the oldest 25%.
ACTIVE_DAYS_CAP = 2000


def record_active_day() -> Dict[str, Any]:
    """Mark today as an active day. Called once per Stop hook.

    Stored as a deduplicated, sorted list of ``YYYY-MM-DD`` strings in
    ``state['active_days']``. This is the calendar that
    ``_active_days_since`` queries — it is what makes the lifecycle
    pass count work-days instead of wall-clock days.
    """
    state = _read_state()
    days = state.setdefault("active_days", [])
    today = _today_iso_date()
    if today in days:
        return {"changed": False, "today": today, "total_active_days": len(days)}
    days.append(today)
    # Keep sorted and unique.
    days[:] = sorted(set(days))
    # Trim if we ever blow past the cap.
    if len(days) > ACTIVE_DAYS_CAP:
        excess = len(days) - int(ACTIVE_DAYS_CAP * 0.75)
        days[:excess] = []
    _write_state(state)
    return {"changed": True, "today": today, "total_active_days": len(days)}


# ──────────────────────────────────────────────────────────────────────
# Pinning detection
# ──────────────────────────────────────────────────────────────────────

_PINNED_PATTERN = re.compile(r"^pinned:\s*true\s*$", re.IGNORECASE | re.MULTILINE)


def is_pinned(skill_dir: Path) -> bool:
    """A skill is pinned when its SKILL.md frontmatter contains
    ``pinned: true`` (anywhere in the first 2KB)."""
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return False
    try:
        head = md.read_text(encoding="utf-8")[:2048]
    except OSError:
        return False
    return bool(_PINNED_PATTERN.search(head))


# ──────────────────────────────────────────────────────────────────────
# Lifecycle pass
# ──────────────────────────────────────────────────────────────────────

def should_run_maintenance() -> bool:
    """True when at least ``HERMES_SKILL_MAINTENANCE_INTERVAL_DAYS``
    *active* days have passed since the last maintenance run.

    Active days = UTC dates on which the Stop hook actually fired (see
    ``record_active_day``). A long break from programming therefore
    delays maintenance proportionally — the clock pauses when you do.
    """
    state = _read_state()
    last = state.get("last_maintenance_at")
    if not last:
        return True
    interval = _int_env(
        "HERMES_SKILL_MAINTENANCE_INTERVAL_DAYS",
        DEFAULT_MAINTENANCE_INTERVAL_DAYS,
    )
    active = _active_days_since(last, state)
    if active is None:
        return True
    return active >= interval


def run_lifecycle_pass() -> Dict[str, List[str]]:
    """Mark stale skills, archive long-unused ones.

    Returns ``{"marked_stale": [...], "archived": [...]}``.

    Thresholds are measured in **active days** (see
    ``_active_days_since``). A 90-active-day-unused skill might be 6
    calendar months old if you programmed every other week.

    Archive moves the skill folder to ~/.claude/skills-archive/<name>/.
    The skill is no longer discoverable by Claude Code but is fully
    recoverable: ``mv ~/.claude/skills-archive/<name> ~/.claude/skills/``.
    """
    state = _read_state()
    skills_state: Dict[str, Any] = state.setdefault("skills", {})

    stale_after = _int_env("HERMES_SKILL_STALE_AFTER_DAYS", DEFAULT_STALE_AFTER_DAYS)
    archive_after = _int_env("HERMES_SKILL_ARCHIVE_AFTER_DAYS", DEFAULT_ARCHIVE_AFTER_DAYS)

    marked_stale: List[str] = []
    archived: List[str] = []

    if SKILLS_DIR.is_dir():
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            if not skill_dir.is_dir():
                continue
            name = skill_dir.name
            if name in PROTECTED_NAMES:
                continue
            if is_pinned(skill_dir):
                # Pinned skills bypass everything; clear any prior stale stamp.
                entry = skills_state.get(name)
                if entry and "stale_since" in entry:
                    entry.pop("stale_since", None)
                continue

            entry = skills_state.get(name, {})
            last_used_iso = entry.get("last_used")
            if not last_used_iso:
                # Never tracked. Use folder mtime as proxy for "added at".
                try:
                    mtime = skill_dir.stat().st_mtime
                    last_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                    last_used_iso = last_dt.isoformat(timespec="seconds")
                except OSError:
                    continue

            active_days = _active_days_since(last_used_iso, state)
            if active_days is None:
                continue

            if active_days >= archive_after:
                target_root = ARCHIVE_DIR
                target_root.mkdir(parents=True, exist_ok=True)
                target = target_root / name
                if target.exists():
                    # Avoid clobbering a prior archive of the same name.
                    target = target_root / f"{name}-{int(time.time())}"
                try:
                    shutil.move(str(skill_dir), str(target))
                except OSError as exc:
                    logger.warning("could not archive %s: %s", name, exc)
                    continue
                entry["archived_at"] = _now_iso()
                entry["archived_path"] = str(target)
                skills_state[name] = entry
                archived.append(name)
            elif active_days >= stale_after and "stale_since" not in entry:
                entry["stale_since"] = _now_iso()
                skills_state[name] = entry
                marked_stale.append(name)

    state["last_maintenance_at"] = _now_iso()
    _write_state(state)
    return {"marked_stale": marked_stale, "archived": archived}


def maintenance_summary_text(result: Dict[str, List[str]]) -> Optional[str]:
    """One-line summary of a lifecycle pass; None when nothing happened.

    Suitable for tacking onto the curator reminder in the prompt hook.
    """
    archived = result.get("archived", [])
    stale = result.get("marked_stale", [])
    if not archived and not stale:
        return None
    parts: List[str] = []
    if archived:
        first = ", ".join(archived[:5])
        more = f" (+{len(archived) - 5} more)" if len(archived) > 5 else ""
        parts.append(f"archived {len(archived)}: {first}{more}")
    if stale:
        first = ", ".join(stale[:5])
        more = f" (+{len(stale) - 5} more)" if len(stale) > 5 else ""
        parts.append(f"marked stale {len(stale)}: {first}{more}")
    return "[hermes-curator] maintenance — " + " · ".join(parts)
