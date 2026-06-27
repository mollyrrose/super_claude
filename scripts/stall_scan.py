#!/usr/bin/env python3
"""stall_scan.py -- find swallowed tool calls in a Claude Code session transcript.

The harness can fail to deliver a tool result to the model with
"[Tool result missing due to internal error]". That is a RESULT-DELIVERY failure
at the harness layer: no hook (PreToolUse / PostToolUse / Stop) can intercept it,
and nothing outside the window can resume the REPL or inject a marker at the
moment it happens (the same hard wall window_watchdog.py / load_retry_runner.py
document). So a stall cannot be PREVENTED or auto-marked in real time -- but it
CAN be DETECTED after the fact: a swallowed call appears in the transcript as a
`tool_use` block with no matching `tool_result`.

This is a one-shot, READ-ONLY diagnostic (lowest-autonomy rule -- not a daemon,
not a hook). Run it when something feels stuck to see exactly which tool calls
got swallowed, so you know what to re-verify / re-apply:

    python stall_scan.py                       # newest transcript for THIS project
    python stall_scan.py --transcript PATH     # a specific .jsonl
    python stall_scan.py --json                # machine-readable
    python stall_scan.py --all                 # do not treat the last one as in-flight

The MOST RECENT unmatched tool_use is usually just IN-FLIGHT (the current turn's
call whose result has not been written yet), not a real stall -- it is flagged
as such and excluded from the stall count unless --all is given.

Exit code: always 0 (a diagnostic must never wedge anything). With --json the
payload carries the structured result regardless.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


def project_session_dir(cwd: str) -> Path:
    """Mirror Claude Code's transcript-dir mapping: every non-alphanumeric char
    in the project cwd is flattened to '-' (per char, runs are NOT collapsed),
    under ~/.claude/projects/.
    e.g. D:\\projects\\super_claude -> D--projects-super-claude."""
    claude_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))
    mangled = re.sub(r"[^A-Za-z0-9]", "-", cwd)
    return claude_dir / "projects" / mangled


def newest_transcript(cwd: str) -> Path | None:
    d = project_session_dir(cwd)
    if not d.is_dir():
        return None
    jsonls = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return jsonls[0] if jsonls else None


def _input_summary(name: str, inp: dict) -> str:
    """Short, human-readable identifier for what the call was doing."""
    if not isinstance(inp, dict):
        return ""
    for key in ("file_path", "path", "command", "pattern", "prompt", "skill"):
        val = inp.get(key)
        if isinstance(val, str) and val.strip():
            s = " ".join(val.split())
            return s[:120]
    return ""


def scan(transcript_path: Path) -> dict:
    """Return {ok, unmatched:[{id,name,summary,line}], total_use, total_result}.
    unmatched is in transcript order (oldest first)."""
    try:
        lines = transcript_path.read_text(encoding="utf8", errors="replace").splitlines()
    except Exception as exc:
        return {"ok": False, "error": str(exc), "unmatched": [],
                "total_use": 0, "total_result": 0}

    uses: dict[str, dict] = {}      # id -> {name, summary, line}
    order: list[str] = []
    results: set[str] = set()

    for lineno, raw in enumerate(lines, 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        content = obj.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for blk in content:
            if not isinstance(blk, dict):
                continue
            t = blk.get("type")
            if t == "tool_use":
                tid = blk.get("id")
                if tid and tid not in uses:
                    uses[tid] = {
                        "name": blk.get("name", "?"),
                        "summary": _input_summary(blk.get("name", ""), blk.get("input", {})),
                        "line": lineno,
                    }
                    order.append(tid)
            elif t == "tool_result":
                rid = blk.get("tool_use_id")
                if rid:
                    results.add(rid)

    unmatched = [{"id": tid, **uses[tid]} for tid in order if tid not in results]
    return {"ok": True, "unmatched": unmatched,
            "total_use": len(uses), "total_result": len(results)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Find swallowed (resultless) tool calls in a transcript.")
    ap.add_argument("--transcript", help="path to a session .jsonl (default: newest for this project)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--all", action="store_true",
                    help="count the most-recent unmatched call too (default: treat it as in-flight)")
    args = ap.parse_args(argv)

    if args.transcript:
        tpath = Path(args.transcript)
    else:
        tpath = newest_transcript(os.getcwd())
        if tpath is None:
            msg = "no transcript found for this project dir"
            print(json.dumps({"ok": False, "error": msg}) if args.json else f"[stall-scan] {msg}")
            return 0

    res = scan(tpath)
    unmatched = res.get("unmatched", [])

    # The newest unmatched call is most likely just in-flight (its result is not
    # on disk yet), not a genuine stall -- separate it unless --all.
    in_flight = None
    stalls = list(unmatched)
    if unmatched and not args.all:
        in_flight = unmatched[-1]
        stalls = unmatched[:-1]

    if args.json:
        print(json.dumps({
            "ok": res.get("ok", False),
            "transcript": str(tpath),
            "total_use": res.get("total_use", 0),
            "total_result": res.get("total_result", 0),
            "stalls": stalls,
            "in_flight": in_flight,
            "error": res.get("error"),
        }))
        return 0

    if not res.get("ok"):
        print(f"[stall-scan] could not read transcript: {res.get('error')}")
        return 0

    print(f"[stall-scan] {tpath.name}: {res['total_use']} tool calls, "
          f"{res['total_result']} results")
    if not stalls:
        print("[stall-scan] no stalled (resultless) tool calls.")
    else:
        print(f"[stall-scan] {len(stalls)} STALLED call(s) -- verify/re-apply these:")
        for s in stalls:
            summ = f"  {s['summary']}" if s["summary"] else ""
            print(f"  - line {s['line']}: {s['name']}{summ}")
    if in_flight:
        summ = f"  {in_flight['summary']}" if in_flight["summary"] else ""
        print(f"[stall-scan] (most recent call may be in-flight, not a stall: "
              f"{in_flight['name']}{summ})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
