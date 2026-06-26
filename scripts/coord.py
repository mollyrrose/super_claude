#!/usr/bin/env python3
"""coord.py -- shared cross-window coordination ledger for concurrent Claude windows.

Problem: several Claude Code windows can run on the same repo at once (different
worktrees / branches / sessions). They must not commit or merge the same files,
and must be able to see "who is doing what" so work doesn't collide. A running
Claude window cannot be pushed messages from outside (see window_watchdog.py /
load_retry_runner.py for that hard limit), so coordination is PULL-based: every
window reads + writes a SHARED journal at its own turn boundaries.

This CLI is the safe, deterministic writer for that journal. The model never
edits the journal directly (two windows Edit-ing one markdown file clobber each
other); instead each window calls this CLI, which mutates a JSON state file
under a cross-process file LOCK and then renders a human-readable work.md view.

Where the journal lives: a single shared, UNTRACKED location that every worktree
of the same repo resolves to identically, via `git rev-parse --git-common-dir`
(the common .git dir shared across all worktrees). Hash that -> a stable repo
key -> ~/.claude/.coord/<key>/{state.json, work.md, .lock}. Nothing is written
into the repo, so there are no merge conflicts and no tracked churn.

state.json shape:
{
  "repo":       "<abs path of main worktree>",
  "updated_at": iso8601,
  "windows": {
    "<session6>": {
      "session": "<session6>", "pid": int, "host": str,
      "start": iso8601|null,            # process start time (PID-reuse defense; best-effort)
      "branch": str|null, "worktree": str|null,
      "first_seen": iso8601, "hb": iso8601,   # hb = last heartbeat
      "note": str,                       # what this window is doing right now
      "claims": ["<repo-relative path>", ...]   # files/tasks this window owns
    }, ...
  }
}

Subcommands (every mutating one takes --session; falls back to $CLAUDE_SESSION_ID):
  register  --session S [--note T] [--branch B] [--worktree W]   upsert this window
  beat      --session S [--note T]                               refresh heartbeat (+note)
  claim     --session S PATH [PATH ...]                          claim files if free
  release   --session S [PATH ...]                               drop some/all claims
  done      --session S                                          remove this window
  status                                                         render + print work.md
  context   --session S                                          compact machine block (for a hook)
  gc                                                             drop dead windows
  path                                                           print journal dir

Liveness: a window is LIVE if its heartbeat is within --stale seconds
(default 1800). A hook refreshes hb every turn, so a live window never goes
stale; a crashed/closed window ages out and its claims free up. On the same
host a best-effort PID check (psutil if present) can mark a window dead early.
Cross-host windows are judged by heartbeat only and never force-killed.

claim is first-come-first-served and atomic (whole op under the lock): if a
LIVE other window already holds a path, the claim is refused for that path and
reported as a conflict (exit 3), so the caller picks different work.

Exit codes: 0 ok; 2 bad usage; 3 claim conflict. Never throws on a corrupt
state file -- it is rebuilt. Kill switch: COORD_DISABLE=1 makes every command a
no-op success; or delete ~/.claude/.coord/<key>/ to reset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
COORD_ROOT = CLAUDE_DIR / ".coord"
DEFAULT_STALE = int(os.environ.get("COORD_STALE_SECONDS", "1800"))  # 30 min
LOCK_TIMEOUT = 10.0   # seconds to wait for the cross-process lock
LOCK_STALE = 60.0     # break a lock dir older than this (a crashed holder)
EVENTS_KEEP = 25      # recent activity lines retained in work.md


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _age_seconds(iso: str | None) -> float:
    dt = _parse_iso(iso)
    if dt is None:
        return float("inf")
    return (datetime.now(timezone.utc) - dt).total_seconds()


# --------------------------------------------------------------------------- repo key

def _git(args: list[str], cwd: str | None = None) -> str | None:
    cmd = ["git"] + (["-C", cwd] if cwd else []) + list(args)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def repo_identity(cwd: str | None = None) -> tuple[str, str | None, str | None]:
    """Return (key, main_worktree_abs, branch). key is stable across all worktrees
    of one repo. Falls back to cwd when not in a git repo. cwd lets a caller
    (e.g. the prompt hook) resolve a repo other than the process cwd WITHOUT an
    in-process chdir (which would corrupt sibling hooks in the dispatcher)."""
    common = _git(["rev-parse", "--git-common-dir"], cwd=cwd)
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if common:
        # git -C resolves relative to cwd, so make absolute against it
        cp = Path(common)
        if not cp.is_absolute() and cwd:
            cp = Path(cwd) / cp
        common_abs = str(cp.resolve())
        # main worktree root is the parent of the common .git dir
        main_root = str(Path(common_abs).parent) if Path(common_abs).name == ".git" else common_abs
        seed = common_abs
    else:
        main_root = str(Path(cwd).resolve()) if cwd else str(Path.cwd().resolve())
        seed = main_root
    key = hashlib.sha1(seed.lower().encode("utf-8")).hexdigest()[:12]
    return key, main_root, branch


def journal_dir(cwd: str | None = None) -> Path:
    key, _, _ = repo_identity(cwd)
    return COORD_ROOT / key


# --------------------------------------------------------------------------- locking

def _acquire_lock(lock: Path) -> bool:
    """Atomic cross-process lock via mkdir (works identically on Windows/POSIX)."""
    deadline = time.time() + LOCK_TIMEOUT
    while True:
        try:
            lock.mkdir(parents=False, exist_ok=False)
            return True
        except FileExistsError:
            # break a stale lock left by a crashed holder
            try:
                if (time.time() - lock.stat().st_mtime) > LOCK_STALE:
                    try:
                        lock.rmdir()
                    except OSError:
                        pass
                    continue
            except OSError:
                pass
            if time.time() >= deadline:
                return False
            time.sleep(0.05)
        except OSError:
            return False


def _release_lock(lock: Path) -> None:
    try:
        lock.rmdir()
    except OSError:
        pass


# --------------------------------------------------------------------------- state io

def _load_state(d: Path) -> dict:
    f = d / "state.json"
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("windows"), dict):
            return data
    except (OSError, ValueError):
        pass
    _, main_root, _ = repo_identity()
    return {"repo": main_root, "updated_at": now_iso(), "windows": {},
            "events": [], "requests": []}


def _save_state(d: Path, state: dict) -> None:
    state["updated_at"] = now_iso()
    f = d / "state.json"
    tmp = d / "state.json.tmp"
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=True), encoding="utf-8")
    os.replace(tmp, f)


def _pid_alive(pid: int | None, host: str) -> bool | None:
    """True/False if determinable on this host, else None (unknown -> use heartbeat)."""
    if not pid or host != socket.gethostname():
        return None
    try:
        import psutil  # type: ignore
        return psutil.pid_exists(int(pid))
    except Exception:
        return None


def _is_live(win: dict, stale: int) -> bool:
    alive = _pid_alive(win.get("pid"), win.get("host", ""))
    if alive is False:
        return False
    return _age_seconds(win.get("hb")) <= stale


def _gc(state: dict, stale: int) -> list[str]:
    dropped = []
    for sid, win in list(state["windows"].items()):
        if not _is_live(win, stale):
            dropped.append(sid)
            del state["windows"][sid]
    return dropped


def _add_event(state: dict, line: str) -> None:
    events = state.setdefault("events", [])
    events.append({"t": now_iso(), "line": line})
    if len(events) > EVENTS_KEEP:
        del events[: len(events) - EVENTS_KEEP]


# --------------------------------------------------------------------------- render

def _render_work_md(state: dict, stale: int) -> str:
    lines = []
    lines.append("# work.md -- live cross-window coordination board")
    lines.append("")
    lines.append("Auto-generated by coord.py. Do NOT hand-edit (it is overwritten).")
    lines.append("All Claude windows on this repo register here; each owns the files")
    lines.append("it has claimed -- do not commit/merge another live window's claims.")
    lines.append("")
    lines.append(f"- repo: {state.get('repo')}")
    lines.append(f"- updated: {state.get('updated_at')}")
    wins = state.get("windows", {})
    live = {s: w for s, w in wins.items() if _is_live(w, stale)}
    lines.append(f"- live windows: {len(live)}")
    lines.append("")
    lines.append("## Active windows")
    if not live:
        lines.append("")
        lines.append("(none registered)")
    for sid, w in sorted(live.items()):
        age = int(_age_seconds(w.get("hb")))
        lines.append("")
        lines.append(f"### [{sid}] {w.get('branch') or '?'} (pid {w.get('pid')}, {w.get('host')})")
        lines.append(f"- worktree: {w.get('worktree') or '?'}")
        lines.append(f"- heartbeat: {w.get('hb')} ({age}s ago)")
        lines.append(f"- doing: {w.get('note') or '-'}")
        claims = w.get("claims") or []
        lines.append(f"- holds ({len(claims)}): {', '.join(claims) if claims else '-'}")
    lines.append("")
    lines.append("## Pending requests / handoffs")
    reqs = [r for r in state.get("requests", []) if r.get("status") in ("open", "answered")]
    if not reqs:
        lines.append("")
        lines.append("(none)")
    for r in reqs:
        lines.append("")
        lines.append(f"### [{r.get('id')}] {r.get('frm')} -> {r.get('to')}  ({r.get('status')})")
        lines.append(f"- posted: {r.get('t')}")
        lines.append(f"- ask: {r.get('note')}")
        if r.get("answer"):
            lines.append(f"- answer ({r.get('answered_by')}): {r.get('answer')}")
    lines.append("")
    lines.append("## Recent activity")
    events = state.get("events", [])
    if not events:
        lines.append("")
        lines.append("(none)")
    for ev in events[-EVENTS_KEEP:]:
        lines.append(f"- {ev.get('t')}  {ev.get('line')}")
    lines.append("")
    return "\n".join(lines)


def _write_work_md(d: Path, state: dict, stale: int) -> None:
    (d / "work.md").write_text(_render_work_md(state, stale), encoding="utf-8")


# --------------------------------------------------------------------------- helpers

def _session(args) -> str | None:
    return getattr(args, "session", None) or os.environ.get("CLAUDE_SESSION_ID") or None


def _proc_start(pid: int) -> str | None:
    try:
        import psutil  # type: ignore
        return datetime.fromtimestamp(
            psutil.Process(pid).create_time(), tz=timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _norm_claims(state: dict, sid: str, paths: list[str]) -> list[str]:
    return [p.replace("\\", "/").strip() for p in paths if p.strip()]


def _holder_of(state: dict, path: str, stale: int, exclude: str) -> str | None:
    for s, w in state["windows"].items():
        if s == exclude:
            continue
        if not _is_live(w, stale):
            continue
        if path in (w.get("claims") or []):
            return s
    return None


def _requests_for(state: dict, sid: str, branch: str | None) -> list[dict]:
    """Open requests addressed to this window (by session6, by branch, or '*')."""
    out = []
    for r in state.get("requests", []):
        if r.get("status") != "open":
            continue
        to = r.get("to")
        if to in (sid, "*") or (branch and to == branch):
            out.append(r)
    return out


def _answers_for(state: dict, sid: str) -> list[dict]:
    """Requests THIS window posted that have now been answered (awaiting ack)."""
    return [r for r in state.get("requests", [])
            if r.get("frm") == sid and r.get("status") == "answered"]


def hook_tick(session: str | None, cwd: str | None = None,
              note: str | None = None, stale: int = DEFAULT_STALE) -> dict:
    """One-call entry point for the UserPromptSubmit hook: refresh THIS window's
    heartbeat (auto-registering on first sight), GC dead windows, re-render
    work.md, and return the coordination context (other live windows, the paths
    they hold, and any open requests addressed here). Returns {} on any problem
    so the hook can no-op silently. cwd resolves the repo without chdir."""
    if not session:
        return {}
    sid = session[:6]
    d = journal_dir(cwd)
    _, main_root, branch = repo_identity(cwd)

    def op():
        state = _load_state(d)
        state["repo"] = main_root
        win = state["windows"].get(sid)
        if win is None:
            win = {
                "session": sid, "pid": os.getppid(), "host": socket.gethostname(),
                "start": _proc_start(os.getppid()), "branch": branch,
                "worktree": cwd or str(Path.cwd().resolve()),
                "first_seen": now_iso(), "hb": now_iso(),
                "note": note or "", "claims": [],
            }
            _add_event(state, f"[{sid}] joined on {branch}")
        else:
            win["hb"] = now_iso()
            win["branch"] = branch or win.get("branch")
            if note is not None:
                win["note"] = note
        state["windows"][sid] = win
        _gc(state, stale)
        _save_state(d, state)
        _write_work_md(d, state, stale)
        others = []
        for s, w in sorted(state["windows"].items()):
            if s == sid or not _is_live(w, stale):
                continue
            others.append({"session": s, "branch": w.get("branch"),
                           "note": w.get("note"), "claims": w.get("claims", [])})
        blocked = sorted({c for o in others for c in o["claims"]})
        return {"self": sid, "branch": branch, "others": others,
                "blocked_paths": blocked,
                "requests_for_me": _requests_for(state, sid, branch),
                "answers_for_me": _answers_for(state, sid)}

    r = _with_lock(d, op)
    return r if isinstance(r, dict) else {}


# --------------------------------------------------------------------------- commands

def _with_lock(d: Path, fn):
    d.mkdir(parents=True, exist_ok=True)
    lock = d / ".lock"
    if not _acquire_lock(lock):
        sys.stderr.write("coord: could not acquire lock\n")
        return 2
    try:
        return fn()
    finally:
        _release_lock(lock)


def cmd_register(args) -> int:
    sid = _session(args)
    if not sid:
        sys.stderr.write("coord register: no --session and no $CLAUDE_SESSION_ID\n")
        return 2
    sid = sid[:6]
    d = journal_dir()
    _, main_root, branch = repo_identity()

    def op():
        state = _load_state(d)
        win = state["windows"].get(sid, {})
        pid = int(args.pid) if args.pid else os.getppid()
        win.update({
            "session": sid,
            "pid": pid,
            "host": socket.gethostname(),
            "start": win.get("start") or _proc_start(pid),
            "branch": args.branch or branch,
            "worktree": args.worktree or str(Path.cwd().resolve()),
            "first_seen": win.get("first_seen") or now_iso(),
            "hb": now_iso(),
            "note": args.note if args.note is not None else win.get("note", ""),
            "claims": win.get("claims", []),
        })
        state["windows"][sid] = win
        _gc(state, args.stale)
        _add_event(state, f"[{sid}] registered on {win['branch']}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        return 0

    return _with_lock(d, op)


def cmd_beat(args) -> int:
    sid = _session(args)
    if not sid:
        sys.stderr.write("coord beat: no session\n")
        return 2
    sid = sid[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        win = state["windows"].get(sid)
        if win is None:
            return cmd_register(args)  # auto-register on first beat
        win["hb"] = now_iso()
        if args.note is not None:
            if args.note != win.get("note"):
                _add_event(state, f"[{sid}] {args.note}")
            win["note"] = args.note
        _gc(state, args.stale)
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        return 0

    return _with_lock(d, op)


def cmd_claim(args) -> int:
    sid = _session(args)
    if not sid:
        sys.stderr.write("coord claim: no session\n")
        return 2
    sid = sid[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        _gc(state, args.stale)
        win = state["windows"].setdefault(sid, {
            "session": sid, "pid": os.getppid(), "host": socket.gethostname(),
            "start": None, "branch": None, "worktree": str(Path.cwd().resolve()),
            "first_seen": now_iso(), "hb": now_iso(), "note": "", "claims": [],
        })
        win["hb"] = now_iso()
        wanted = _norm_claims(state, sid, args.paths)
        conflicts = {}
        granted = []
        for p in wanted:
            holder = _holder_of(state, p, args.stale, exclude=sid)
            if holder:
                conflicts[p] = holder
            elif p not in win["claims"]:
                win["claims"].append(p)
                granted.append(p)
            else:
                granted.append(p)  # already ours (idempotent)
        if granted:
            _add_event(state, f"[{sid}] claimed {', '.join(granted)}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        result = {"granted": granted, "conflicts": conflicts}
        sys.stdout.write(json.dumps(result) + "\n")
        return 3 if conflicts else 0

    return _with_lock(d, op)


def cmd_release(args) -> int:
    sid = _session(args)
    if not sid:
        sys.stderr.write("coord release: no session\n")
        return 2
    sid = sid[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        win = state["windows"].get(sid)
        if win is None:
            return 0
        targets = _norm_claims(state, sid, args.paths) if args.paths else list(win.get("claims", []))
        win["claims"] = [c for c in win.get("claims", []) if c not in targets]
        win["hb"] = now_iso()
        if targets:
            _add_event(state, f"[{sid}] released {', '.join(targets)}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        return 0

    return _with_lock(d, op)


def cmd_done(args) -> int:
    sid = _session(args)
    if not sid:
        sys.stderr.write("coord done: no session\n")
        return 2
    sid = sid[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        if sid in state["windows"]:
            del state["windows"][sid]
            _add_event(state, f"[{sid}] left")
        _gc(state, args.stale)
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        return 0

    return _with_lock(d, op)


def cmd_gc(args) -> int:
    d = journal_dir()

    def op():
        state = _load_state(d)
        dropped = _gc(state, args.stale)
        if dropped:
            _add_event(state, f"gc dropped {', '.join(dropped)}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps({"dropped": dropped}) + "\n")
        return 0

    return _with_lock(d, op)


def cmd_request(args) -> int:
    """Post a handoff/request to another window (by session6, branch, or '*').
    Use for cross-window asks coord can't do for you -- e.g. 'engine-owner:
    cherry-pick commit 60a8123 (Q1.6 safety fix) into main'. The target window
    sees it in its next-turn context and acts or declines."""
    sid = _session(args)
    if not sid:
        sys.stderr.write("coord request: no session\n")
        return 2
    sid = sid[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        reqs = state.setdefault("requests", [])
        rid = "r" + hashlib.sha1(f"{now_iso()}{sid}{args.note}".encode()).hexdigest()[:6]
        reqs.append({"id": rid, "t": now_iso(), "frm": sid, "to": args.to,
                     "note": args.note, "status": "open"})
        _add_event(state, f"[{sid}] -> {args.to}: {args.note}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps({"id": rid}) + "\n")
        return 0

    return _with_lock(d, op)


def cmd_reply(args) -> int:
    """Answer a request addressed to you. The answer travels BACK to the asker
    (it shows in their `answers_for_me` next turn). Use for the auto-relay
    round-trip: engine asks 'who rebases?' -> you reply -> engine reads it.
    DECISION-GATE: if the ask needs an irreversible op (merge to main, push,
    rebase of live files), do NOT execute it autonomously -- reply with the
    PROPOSED command and 'needs user approval', and surface it to the user."""
    sid = (_session(args) or "")[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        found = False
        for r in state.get("requests", []):
            if r.get("id") == args.id and r.get("status") in ("open", "answered"):
                r["status"] = "answered"
                r["answer"] = args.note
                r["answered_by"] = sid
                r["answered_at"] = now_iso()
                found = True
                _add_event(state, f"[{sid}] answered {args.id}: {args.note}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps({"answered": found}) + "\n")
        return 0

    return _with_lock(d, op)


def cmd_ack(args) -> int:
    """Close out an answered request you posted (you've read the answer)."""
    sid = (_session(args) or "")[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        for r in state.get("requests", []):
            if r.get("id") == args.id:
                r["status"] = "closed"
                r["acked_by"] = sid
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps({"acked": args.id}) + "\n")
        return 0

    return _with_lock(d, op)


def cmd_resolve(args) -> int:
    """Close a request by id (the actor or poster marks it handled/declined)."""
    sid = (_session(args) or "")[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        found = False
        for r in state.get("requests", []):
            if r.get("id") == args.id and r.get("status") == "open":
                r["status"] = args.status
                r["resolved_by"] = sid
                r["resolved_at"] = now_iso()
                found = True
                _add_event(state, f"[{sid}] {args.status} {args.id}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps({"resolved": found}) + "\n")
        return 0

    return _with_lock(d, op)


def cmd_status(args) -> int:
    d = journal_dir()
    state = _load_state(d)
    sys.stdout.write(_render_work_md(state, args.stale))
    return 0


def cmd_context(args) -> int:
    """Compact machine-readable block for a UserPromptSubmit hook to inject."""
    sid = (_session(args) or "")[:6]
    d = journal_dir()
    state = _load_state(d)
    wins = state.get("windows", {})
    others = []
    for s, w in sorted(wins.items()):
        if s == sid or not _is_live(w, args.stale):
            continue
        others.append({
            "session": s, "branch": w.get("branch"), "note": w.get("note"),
            "claims": w.get("claims", []),
        })
    blocked = sorted({c for o in others for c in o["claims"]})
    _, _, branch = repo_identity()
    out = {"self": sid, "others": others, "blocked_paths": blocked,
           "requests_for_me": _requests_for(state, sid, branch),
           "answers_for_me": _answers_for(state, sid)}
    sys.stdout.write(json.dumps(out) + "\n")
    return 0


def cmd_inbox(args) -> int:
    """Compact actionable view for the auto-relay loop: requests addressed to
    me + answers to my own questions. Same-project only (the board is per-repo)."""
    sid = (_session(args) or "")[:6]
    d = journal_dir()
    state = _load_state(d)
    _, _, branch = repo_identity()
    out = {"self": sid,
           "requests_for_me": _requests_for(state, sid, branch),
           "answers_for_me": _answers_for(state, sid)}
    sys.stdout.write(json.dumps(out) + "\n")
    return 0


def cmd_path(args) -> int:
    sys.stdout.write(str(journal_dir()) + "\n")
    return 0


# --------------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="coord", description="cross-window coordination ledger")
    p.add_argument("--stale", type=int, default=DEFAULT_STALE,
                   help="seconds before a silent window is considered dead")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_session(sp):
        sp.add_argument("--session", default=None)

    sp = sub.add_parser("register"); add_session(sp)
    sp.add_argument("--note", default=None); sp.add_argument("--branch", default=None)
    sp.add_argument("--worktree", default=None); sp.add_argument("--pid", default=None)
    sp.set_defaults(func=cmd_register)

    sp = sub.add_parser("beat"); add_session(sp)
    sp.add_argument("--note", default=None); sp.add_argument("--branch", default=None)
    sp.add_argument("--worktree", default=None); sp.add_argument("--pid", default=None)
    sp.set_defaults(func=cmd_beat)

    sp = sub.add_parser("claim"); add_session(sp)
    sp.add_argument("paths", nargs="+"); sp.set_defaults(func=cmd_claim)

    sp = sub.add_parser("release"); add_session(sp)
    sp.add_argument("paths", nargs="*"); sp.set_defaults(func=cmd_release)

    sp = sub.add_parser("request"); add_session(sp)
    sp.add_argument("--to", required=True, help="target session6, branch name, or '*'")
    sp.add_argument("--note", required=True, help="what you are asking for")
    sp.set_defaults(func=cmd_request)

    sp = sub.add_parser("resolve"); add_session(sp)
    sp.add_argument("id"); sp.add_argument("--status", default="done",
                                           choices=["done", "declined"])
    sp.set_defaults(func=cmd_resolve)

    sp = sub.add_parser("reply"); add_session(sp)
    sp.add_argument("id"); sp.add_argument("--note", required=True)
    sp.set_defaults(func=cmd_reply)

    sp = sub.add_parser("ack"); add_session(sp)
    sp.add_argument("id"); sp.set_defaults(func=cmd_ack)

    sp = sub.add_parser("inbox"); add_session(sp); sp.set_defaults(func=cmd_inbox)

    sp = sub.add_parser("done"); add_session(sp); sp.set_defaults(func=cmd_done)
    sp = sub.add_parser("gc"); sp.set_defaults(func=cmd_gc)
    sp = sub.add_parser("status"); sp.set_defaults(func=cmd_status)
    sp = sub.add_parser("context"); add_session(sp); sp.set_defaults(func=cmd_context)
    sp = sub.add_parser("path"); sp.set_defaults(func=cmd_path)
    return p


def main(argv: list[str] | None = None) -> int:
    if os.environ.get("COORD_DISABLE") == "1":
        return 0  # kill switch: no-op success
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:  # never hard-crash a caller
        sys.stderr.write(f"coord: {e}\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
