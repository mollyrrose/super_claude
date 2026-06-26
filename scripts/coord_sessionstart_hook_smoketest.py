#!/usr/bin/env python3
"""Smoketest for coord_sessionstart_hook.py against an isolated config + temp repo.

Checks: a starting window registers + gets the standing directive; when another
live window is present the directive includes the live board + the self-loop
nudge; COORD_AUTOLOOP=0 drops the loop nudge but keeps the protocol; malformed
stdin no-ops; COORD_DISABLE silences it. ASCII output; non-zero on any failure.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK = HERE / "coord_sessionstart_hook.py"
COORD = HERE / "coord.py"
PY = sys.executable
results = []


def check(name, ok):
    results.append((name, ok))
    print(f"[{'ok' if ok else 'fail'}] {name}")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="coord_ss_smoke_"))
    cfg = tmp / "claude"; cfg.mkdir()
    repo = tmp / "repo"; repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo)
    base = dict(os.environ); base["CLAUDE_CONFIG_DIR"] = str(cfg)
    base.pop("COORD_DISABLE", None); base.pop("COORD_AUTOLOOP", None)

    def hook(session, cwd=repo, raw=None, extra_env=None):
        payload = raw if raw is not None else json.dumps(
            {"session_id": session, "cwd": str(cwd), "source": "startup",
             "hook_event_name": "SessionStart"})
        env = dict(base)
        if extra_env:
            env.update(extra_env)
        return subprocess.run([PY, str(HOOK)], input=payload, capture_output=True,
                              text=True, env=env, cwd=str(repo))

    def coord(session, *args):
        e = dict(base); e["CLAUDE_SESSION_ID"] = session
        return subprocess.run([PY, str(COORD), *args], capture_output=True,
                              text=True, env=e, cwd=str(repo))

    # 1) a starting window registers + gets the standing directive (even solo)
    p = hook("start1")
    obj = json.loads(p.stdout) if p.stdout.strip() else {}
    ctx = obj.get("hookSpecificOutput", {}).get("additionalContext", "")
    check("solo start exits 0", p.returncode == 0)
    check("directive injected at startup", "[coordination]" in ctx and "DECISION-GATE" in ctx)
    check("solo start has no live-board / no loop nudge", "LIVE NOW" not in ctx)
    # registered on the board?
    st = json.loads((Path(coord("x", "path").stdout.strip()) / "state.json").read_text())
    check("window registered at startup", "start1" in st["windows"])

    # 2) with another live window + a pending request -> board + loop nudge appear
    coord("otherw", "register", "--note", "engine")
    coord("otherw", "request", "--to", "start2", "--note", "merge X into main")
    p = hook("start2")
    ctx = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]
    check("live board shown when others present", "LIVE NOW" in ctx and "otherw" in ctx)
    check("pending request flagged", "addressed to you" in ctx)
    check("self-loop nudge present", "/loop" in ctx)

    # 3) COORD_AUTOLOOP=0 drops the loop nudge but keeps protocol
    p = hook("start3", extra_env={"COORD_AUTOLOOP": "0"})
    ctx = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]
    check("AUTOLOOP=0 keeps protocol", "DECISION-GATE" in ctx)
    check("AUTOLOOP=0 drops loop nudge", "/loop" not in ctx)

    # 4) malformed stdin -> silent no-op
    p = hook("start1", raw="not json{{{")
    check("malformed stdin no-ops", p.returncode == 0 and p.stdout.strip() == "")

    # 5) kill switch
    p = hook("start9", extra_env={"COORD_DISABLE": "1"})
    check("COORD_DISABLE silences hook", p.returncode == 0 and p.stdout.strip() == "")

    npass = sum(1 for _, ok in results if ok)
    print(f"\n{npass}/{len(results)} checks passed")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
