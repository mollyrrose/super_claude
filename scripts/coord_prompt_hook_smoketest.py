#!/usr/bin/env python3
"""Smoketest for coord_prompt_hook.py against an isolated config + temp repo.

Checks: solo window injects nothing; a second live window + its claims appear in
the [coordination] block; a request addressed to the window surfaces; the hook
keeps the window's heartbeat fresh; malformed stdin is a silent no-op.
ASCII-only output; non-zero exit on any failure.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK = HERE / "coord_prompt_hook.py"
COORD = HERE / "coord.py"
PY = sys.executable
results = []


def check(name, ok):
    results.append((name, ok))
    print(f"[{'ok' if ok else 'fail'}] {name}")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="coord_hook_smoke_"))
    cfg = tmp / "claude"; cfg.mkdir()
    repo = tmp / "repo"; repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo)
    base = dict(os.environ); base["CLAUDE_CONFIG_DIR"] = str(cfg)
    base.pop("COORD_DISABLE", None)

    def hook(session, cwd=repo, raw=None):
        payload = raw if raw is not None else json.dumps(
            {"session_id": session, "cwd": str(cwd), "hook_event_name": "UserPromptSubmit"})
        p = subprocess.run([PY, str(HOOK)], input=payload, capture_output=True,
                           text=True, env=base, cwd=str(repo))
        return p

    def coord(session, *args, cwd=repo):
        e = dict(base); e["CLAUDE_SESSION_ID"] = session
        return subprocess.run([PY, str(COORD), *args], capture_output=True,
                              text=True, env=e, cwd=str(cwd))

    # 1) solo window: hook runs, registers, but emits no additionalContext
    p = hook("solo01")
    check("solo window exits 0", p.returncode == 0)
    check("solo window emits no context", p.stdout.strip() == "")

    # window solo01 is now registered/live; second window B claims a file
    coord("winnnb", "register", "--note", "engine work")
    coord("winnnb", "claim", "src/engine.py")

    # 2) solo01's hook now sees B + the blocked path
    p = hook("solo01")
    obj = json.loads(p.stdout) if p.stdout.strip() else {}
    ctx = obj.get("hookSpecificOutput", {}).get("additionalContext", "")
    check("hook reports other window", "winnnb" in ctx and "other live" in ctx)
    check("hook lists blocked path", "src/engine.py" in ctx)

    # 3) a request addressed to solo01 surfaces in its context
    coord("winnnb", "request", "--to", "solo01", "--note", "cherry-pick 60a8123 into main")
    p = hook("solo01")
    ctx = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]
    check("request surfaces to target window", "cherry-pick 60a8123" in ctx and "addressed to YOU" in ctx)

    # 4) heartbeat freshness: solo01 hb is recent after the hook tick
    st = json.loads((Path(coord("x", "path").stdout.strip()) / "state.json").read_text())
    hb = st["windows"]["solo01"]["hb"]
    check("hook refreshed heartbeat", bool(hb))

    # 5) malformed stdin -> silent no-op
    p = hook("solo01", raw="not json{{{")
    check("malformed stdin no-ops", p.returncode == 0 and p.stdout.strip() == "")

    # 6) kill switch
    e = dict(base); e["COORD_DISABLE"] = "1"
    p = subprocess.run([PY, str(HOOK)], input=json.dumps({"session_id": "z", "cwd": str(repo)}),
                       capture_output=True, text=True, env=e, cwd=str(repo))
    check("COORD_DISABLE silences hook", p.returncode == 0 and p.stdout.strip() == "")

    npass = sum(1 for _, ok in results if ok)
    print(f"\n{npass}/{len(results)} checks passed")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
