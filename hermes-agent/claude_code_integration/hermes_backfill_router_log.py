#!/usr/bin/env python3
"""Backfill the smart-router evaluation log from existing Claude Code session JSONLs.

Walks ~/.claude/projects/<project>/<session>.jsonl (skipping subagents/),
extracts every user-prompt event and the first subsequent Skill tool_use
within the same prompt window, and writes one privacy-safe row per prompt
to ~/.claude/.smart_router_eval_backfill.jsonl.

Privacy invariants (load-bearing — see plans/logical-questing-clarke.md):
- Never write the prompt body. Only sha256(prompt)[:16].
- Never write file paths, tool-call arguments, or any other prompt-derived
  content. Output columns are fixed.
- Read-only on ~/.claude/projects/. We open the JSONLs to read; we never
  modify, delete, or move them.

Idempotent: rows are keyed by (session_id, prompt_hash, ts). Re-running
appends only new rows.

Usage:
    python hermes_backfill_router_log.py [--dry-run] [--projects-dir PATH]
                                         [--out PATH] [--limit N]

Exit codes:
    0 success
    1 unrecoverable error (missing projects dir, output not writable)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Iterator

CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
DEFAULT_PROJECTS_DIR = CLAUDE_DIR / "projects"
DEFAULT_OUT = CLAUDE_DIR / ".smart_router_eval_backfill.jsonl"


def hash_prompt(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def extract_prompt_text(message_content) -> str:
    """Pull plain text out of a user message's content field.

    Content can be a string or a list of content blocks (multimodal).
    For multimodal we concatenate the text blocks; non-text blocks
    (image, tool_result, etc.) are ignored. Never returns the raw
    content to disk — caller hashes it.
    """
    if isinstance(message_content, str):
        return message_content
    if isinstance(message_content, list):
        parts = []
        for block in message_content:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text")
                if isinstance(t, str):
                    parts.append(t)
        return "\n".join(parts)
    return ""


def is_slash_command(prompt: str) -> bool:
    """Detect user-driven slash commands (router doesn't make the call here).

    Claude Code wraps slash invocations as <command-name>/foo</command-name>.
    We also catch plain-text /foo at the start of the prompt as a defensive
    fallback for older transcripts.
    """
    stripped = prompt.lstrip()
    if stripped.startswith("<command-name>"):
        return True
    if stripped.startswith("/") and len(stripped) > 1 and stripped[1].isalpha():
        # Heuristic: looks like a slash command (single-line, starts with /<letter>).
        first_line = stripped.split("\n", 1)[0]
        if len(first_line) < 200 and " " not in first_line[:30]:
            return True
    return False


def iter_session_files(projects_dir: Path) -> Iterator[Path]:
    """Yield main session JSONLs only — skip subagents/ trees."""
    if not projects_dir.is_dir():
        return
    for project in sorted(projects_dir.iterdir()):
        if not project.is_dir():
            continue
        for jsonl in sorted(project.glob("*.jsonl")):
            # Skip files that live under a subagents/ subtree.
            if "subagents" in jsonl.parts:
                continue
            yield jsonl


def project_slug(jsonl_path: Path, projects_dir: Path) -> str:
    try:
        rel = jsonl_path.relative_to(projects_dir)
        return rel.parts[0] if rel.parts else jsonl_path.parent.name
    except ValueError:
        return jsonl_path.parent.name


def find_first_skill_in_assistant_event(event: dict) -> str | None:
    msg = event.get("message")
    if not isinstance(msg, dict):
        return None
    content = msg.get("content")
    if not isinstance(content, list):
        return None
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "tool_use":
            continue
        if block.get("name") != "Skill":
            continue
        inp = block.get("input")
        if isinstance(inp, dict):
            skill = inp.get("skill")
            if isinstance(skill, str) and skill.strip():
                return skill.strip()
    return None


def process_session(
    jsonl_path: Path,
    project: str,
    seen_keys: set[tuple[str, str, str]],
) -> Iterator[dict]:
    """Yield one row per user-prompt event in this session."""
    try:
        lines = jsonl_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return

    # Pre-parse so we can do a forward scan from each user event.
    events = []
    for raw in lines:
        if not raw.strip():
            continue
        try:
            events.append(json.loads(raw))
        except json.JSONDecodeError:
            continue

    n = len(events)
    for i, ev in enumerate(events):
        if ev.get("type") != "user":
            continue
        if ev.get("isSidechain") is True:
            continue
        msg = ev.get("message")
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue

        prompt = extract_prompt_text(msg.get("content"))
        if not prompt.strip():
            continue
        if is_slash_command(prompt):
            continue

        ts = ev.get("timestamp") or ""
        sid = ev.get("sessionId") or ""
        if not ts or not sid:
            continue

        h = hash_prompt(prompt)
        key = (sid, h, ts)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        # Forward scan: find next user event boundary, then look for first
        # Skill tool_use inside the window.
        invoked = None
        for j in range(i + 1, n):
            nxt = events[j]
            if nxt.get("type") == "user" and nxt.get("isSidechain") is not True:
                nxt_msg = nxt.get("message")
                if isinstance(nxt_msg, dict) and nxt_msg.get("role") == "user":
                    nxt_text = extract_prompt_text(nxt_msg.get("content"))
                    if nxt_text.strip():
                        break  # window ends at next real user prompt
            if nxt.get("type") == "assistant":
                skill = find_first_skill_in_assistant_event(nxt)
                if skill is not None:
                    invoked = skill
                    break

        word_count = len(prompt.split())
        yield {
            "ts": ts,
            "session_id": sid,
            "project": project,
            "prompt_hash": h,
            "prompt_len_words": word_count,
            "suggested_skill_or_null": None,
            "invoked_skill_or_null": invoked,
        }


def load_seen_keys(out: Path) -> set[tuple[str, str, str]]:
    seen: set[tuple[str, str, str]] = set()
    if not out.exists():
        return seen
    try:
        for raw in out.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            sid = row.get("session_id")
            h = row.get("prompt_hash")
            ts = row.get("ts")
            if isinstance(sid, str) and isinstance(h, str) and isinstance(ts, str):
                seen.add((sid, h, ts))
    except OSError:
        pass
    return seen


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Backfill smart-router eval log from session JSONLs.")
    ap.add_argument("--dry-run", action="store_true", help="Count without writing.")
    ap.add_argument("--projects-dir", type=Path, default=DEFAULT_PROJECTS_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=0, help="Stop after N sessions (0 = no limit).")
    args = ap.parse_args(argv)

    projects_dir = args.projects_dir
    if not projects_dir.is_dir():
        sys.stderr.write(f"[backfill] projects dir not found: {projects_dir}\n")
        return 1

    seen = load_seen_keys(args.out)
    initial_seen = len(seen)

    sessions = 0
    user_events = 0
    new_rows = 0
    invoked_skill_rows = 0
    new_records: list[dict] = []

    for jsonl in iter_session_files(projects_dir):
        sessions += 1
        if args.limit and sessions > args.limit:
            break
        project = project_slug(jsonl, projects_dir)
        for row in process_session(jsonl, project, seen):
            user_events += 1
            new_rows += 1
            if row["invoked_skill_or_null"]:
                invoked_skill_rows += 1
            new_records.append(row)

    if args.dry_run:
        print(
            f"[backfill --dry-run] sessions={sessions} new_prompts={new_rows} "
            f"invoked_skill={invoked_skill_rows} already_seen={initial_seen} "
            f"out={args.out}"
        )
        return 0

    if new_records:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("a", encoding="utf-8") as f:
            for row in new_records:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        f"[backfill] sessions={sessions} appended={new_rows} "
        f"invoked_skill={invoked_skill_rows} total_after={initial_seen + new_rows} "
        f"out={args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
