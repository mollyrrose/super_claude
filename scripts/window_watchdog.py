#!/usr/bin/env python3
"""window_watchdog.py — idle/stuck-window monitor for a Claude Code session.

THE HARD LIMIT (read this first): a separate process CANNOT inject "continue"
into a running interactive Claude Code window. The window is the interactive
REPL; nothing outside it can type into it or resume its loop. So this watchdog
does NOT auto-unstick anything. What it CAN do — and all it does — is WATCH the
session's transcript for activity and ALERT YOU (sound + console line, optional
Windows toast) when the window has gone silent for too long, so you notice a
stuck / hung / waiting window in seconds instead of discovering it minutes later.

How it detects "stuck": Claude Code appends to the session transcript JSONL on
every tool call and message. While Claude is actively working the file's mtime
keeps advancing; when it hangs (a wedged tool call, a silent error loop) or sits
waiting for you, the mtime stops. So: newest .jsonl mtime older than the idle
threshold => alert. (It cannot distinguish "hung" from "waiting for you" — both
mean "go look at this window", which is exactly what you want to be told.)

Usage (run in a SPARE terminal, not the Claude window):
    python window_watchdog.py                       # watch this project's newest session
    python window_watchdog.py --project-dir <dir>   # watch a specific project's transcripts
    python window_watchdog.py --transcript <file>   # watch one exact transcript
    python window_watchdog.py --idle 180 --poll 20  # alert after 180s idle, poll every 20s

Kill switch: Ctrl-C, or just never start it. It changes nothing about the
watched window — purely an out-of-band observer.

Lowest-autonomy by design: a one-off script you start when you want it, not a
daemon, not a hook. No external dependencies (winsound is stdlib on Windows; a
terminal bell is the cross-platform fallback).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def default_project_dir() -> Path:
    """Map the current working directory to its Claude transcript dir.

    Claude Code stores transcripts under ~/.claude/projects/<slug>, where the
    slug is the absolute cwd with drive-colon and path separators flattened to
    '-' (e.g. D:\\projects\\super_claude -> D--projects-super-claude).
    """
    claude_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))
    cwd = Path.cwd()
    slug = str(cwd).replace(":", "-").replace("\\", "-").replace("/", "-")
    return claude_dir / "projects" / slug


def pick_active_transcript(project_dir: Path):
    """Return the most-recently-modified .jsonl in project_dir, or None."""
    try:
        files = [p for p in project_dir.glob("*.jsonl") if p.is_file()]
    except OSError:
        return None
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def should_alert(now: float, mtime: float, idle_seconds: float, already_alerted: bool) -> bool:
    """Pure decision: alert when idle past threshold and not already alerted
    for this same stall. Re-arms only after activity resumes (handled by the
    caller resetting already_alerted when mtime advances)."""
    if already_alerted:
        return False
    return (now - mtime) >= idle_seconds


def notify(message: str) -> None:
    """Best-effort attention signal: sound + a loud console line, plus a
    Windows toast when available. Never raises."""
    line = f"\n[window-watchdog] {message}"
    try:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except Exception:
        pass
    # Audible cue.
    try:
        if sys.platform.startswith("win"):
            import winsound  # stdlib on Windows
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        else:
            sys.stdout.write("\a")
            sys.stdout.flush()
    except Exception:
        pass
    # Optional Windows toast (no extra deps; ignored if it fails).
    if sys.platform.startswith("win"):
        try:
            import subprocess
            ps = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null; "
                "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                "[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                f"$t.GetElementsByTagName('text').Item(0).AppendChild($t.CreateTextNode('Claude window idle')) > $null; "
                f"$t.GetElementsByTagName('text').Item(1).AppendChild($t.CreateTextNode('{message[:80]}')) > $null; "
                "$n=[Windows.UI.Notifications.ToastNotification]::new($t); "
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Claude Code').Show($n);"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True, timeout=8,
            )
        except Exception:
            pass


def watch(transcript: Path, idle_seconds: float, poll_seconds: float) -> int:
    print(
        f"[window-watchdog] watching {transcript.name} "
        f"(idle>{int(idle_seconds)}s, poll {int(poll_seconds)}s). Ctrl-C to stop."
    )
    alerted = False
    last_mtime = None
    while True:
        try:
            mtime = transcript.stat().st_mtime
        except OSError:
            # Transcript vanished (session ended / rotated) — try to repoint.
            time.sleep(poll_seconds)
            newer = pick_active_transcript(transcript.parent)
            if newer is not None:
                transcript = newer
                alerted = False
                last_mtime = None
            continue

        now = time.time()
        if last_mtime is not None and mtime > last_mtime:
            # Activity resumed → re-arm.
            alerted = False
        last_mtime = mtime

        if should_alert(now, mtime, idle_seconds, alerted):
            idle_for = int(now - mtime)
            notify(f"no activity for {idle_for}s in {transcript.name} -- check the window.")
            alerted = True

        time.sleep(poll_seconds)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Alert when a Claude Code window goes idle/stuck.")
    p.add_argument("--project-dir", type=str, default=None,
                   help="Transcript dir to watch (default: derived from cwd).")
    p.add_argument("--transcript", type=str, default=None,
                   help="Exact transcript .jsonl to watch (overrides --project-dir).")
    p.add_argument("--idle", type=float, default=300.0,
                   help="Seconds of silence before alerting (default 300).")
    p.add_argument("--poll", type=float, default=30.0,
                   help="Polling interval in seconds (default 30).")
    return p


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.transcript:
        transcript = Path(args.transcript)
        if not transcript.exists():
            print(f"[window-watchdog] transcript not found: {transcript}", file=sys.stderr)
            return 1
    else:
        project_dir = Path(args.project_dir) if args.project_dir else default_project_dir()
        if not project_dir.exists():
            print(f"[window-watchdog] project dir not found: {project_dir}", file=sys.stderr)
            return 1
        transcript = pick_active_transcript(project_dir)
        if transcript is None:
            print(f"[window-watchdog] no .jsonl transcript in {project_dir}", file=sys.stderr)
            return 1
    try:
        return watch(transcript, args.idle, args.poll)
    except KeyboardInterrupt:
        print("\n[window-watchdog] stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
