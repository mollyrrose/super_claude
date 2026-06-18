#!/usr/bin/env python3
"""Smoke test for hook_dispatch.py.

Part A (hermetic): synthetic hook files in a temp dir + a monkeypatched
REGISTRY exercise the dispatcher's merge / block / failure-isolation logic with
no dependency on the real hooks and no side effects.

Part B (end-to-end): run the dispatcher as a subprocess against the REAL
registry with benign payloads, asserting it never blocks and emits valid JSON
(or nothing). QREV_AUTO_LEVEL=0 keeps the qrev hooks silent so no state file is
touched.

Cases:
 A1 UserPromptSubmit merges two hooks' additionalContext into ONE JSON object.
 A2 plain-text stdout from a hook is carried through as context.
 A3 a hook that raises is isolated -> other hook still merged, exit 0.
 A4 all hooks silent -> no stdout, exit 0.
 A5 PostToolUse: a hook exiting 2 -> dispatcher exit 2 with its stderr surfaced.
 A6 PostToolUse: all hooks exit 0 -> dispatcher exit 0, no stderr.
 B1 real registry, near-full context payload -> valid JSON, exit 0.
 B2 real registry, malformed stdin -> exit 0, stdout empty or valid JSON.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DISPATCH = os.path.join(HERE, "hook_dispatch.py")


def _load_dispatch_module():
    spec = importlib.util.spec_from_file_location("hook_dispatch_under_test", DISPATCH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_hook(tmp: str, name: str, body: str) -> str:
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


# --- synthetic hook bodies (each a standalone module with a main()) ---
_UPS_JSON = '''
import json, sys
def main():
    out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                  "additionalContext": %r}}
    sys.stdout.write(json.dumps(out))
    return 0
'''

_UPS_PLAIN = '''
import sys
def main():
    sys.stdout.write(%r)
    return 0
'''

_RAISES = '''
def main():
    raise RuntimeError("boom")
'''

_SILENT = '''
def main():
    return 0
'''

_POST_BLOCK = '''
import sys
def main():
    sys.stderr.write(%r)
    return 2
'''

_POST_OK = '''
def main():
    return 0
'''


def _capture_dispatch(mod, event: str, hooks, payload_raw: str):
    """Drive the dispatcher's per-event function directly, capturing stdout/stderr/code."""
    real_out, real_err = sys.stdout, sys.stderr
    out_buf, err_buf = io.StringIO(), io.StringIO()
    try:
        sys.stdout, sys.stderr = out_buf, err_buf
        if event == "UserPromptSubmit":
            code = mod._dispatch_user_prompt_submit(hooks, payload_raw)
        else:
            code = mod._dispatch_post_tool_use(hooks, payload_raw)
    finally:
        sys.stdout, sys.stderr = real_out, real_err
    return code, out_buf.getvalue(), err_buf.getvalue()


def _run_subprocess(event: str, stdin_text: str, extra_env=None):
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, DISPATCH, event],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def main() -> int:
    from pathlib import Path

    mod = _load_dispatch_module()
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        h_json_a = Path(_write_hook(tmp, "a.py", _UPS_JSON % "CTX-A"))
        h_json_b = Path(_write_hook(tmp, "b.py", _UPS_JSON % "CTX-B"))
        h_plain = Path(_write_hook(tmp, "p.py", _UPS_PLAIN % "PLAINTEXT-CTX"))
        h_raise = Path(_write_hook(tmp, "r.py", _RAISES))
        h_silent = Path(_write_hook(tmp, "s.py", _SILENT))
        h_block = Path(_write_hook(tmp, "blk.py", _POST_BLOCK % "BLOCKED-HERE"))
        h_ok = Path(_write_hook(tmp, "ok.py", _POST_OK))

        # A1: merge two JSON hooks into one object.
        code, out, _ = _capture_dispatch(
            mod, "UserPromptSubmit",
            [("a", h_json_a), ("b", h_json_b)], "{}",
        )
        try:
            obj = json.loads(out)
            ctx = obj["hookSpecificOutput"]["additionalContext"]
            if code != 0:
                failures.append(f"A1 exit {code}")
            elif "CTX-A" not in ctx or "CTX-B" not in ctx:
                failures.append(f"A1 missing a context: {ctx!r}")
            elif ctx != "CTX-A\n\nCTX-B":
                failures.append(f"A1 wrong merge/order: {ctx!r}")
        except Exception as e:
            failures.append(f"A1 not valid single JSON: {out!r} ({e})")

        # A2: plain-text stdout carried through.
        code, out, _ = _capture_dispatch(
            mod, "UserPromptSubmit", [("p", h_plain)], "{}",
        )
        try:
            ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
            if "PLAINTEXT-CTX" not in ctx:
                failures.append(f"A2 plain text dropped: {out!r}")
        except Exception as e:
            failures.append(f"A2 not valid JSON: {out!r} ({e})")

        # A3: a raising hook is isolated; the other still merges; exit 0.
        code, out, _ = _capture_dispatch(
            mod, "UserPromptSubmit",
            [("r", h_raise), ("a", h_json_a)], "{}",
        )
        if code != 0:
            failures.append(f"A3 exit {code}")
        else:
            try:
                ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
                if ctx != "CTX-A":
                    failures.append(f"A3 expected only CTX-A: {ctx!r}")
            except Exception as e:
                failures.append(f"A3 not valid JSON: {out!r} ({e})")

        # A4: all silent -> no output, exit 0.
        code, out, _ = _capture_dispatch(
            mod, "UserPromptSubmit",
            [("s", h_silent), ("r", h_raise)], "{}",
        )
        if code != 0:
            failures.append(f"A4 exit {code}")
        elif out.strip():
            failures.append(f"A4 should be silent: {out!r}")

        # A5: PostToolUse block propagates exit 2 + stderr.
        code, out, err = _capture_dispatch(
            mod, "PostToolUse",
            [("ok", h_ok), ("blk", h_block)], "{}",
        )
        if code != 2:
            failures.append(f"A5 expected exit 2, got {code}")
        elif "BLOCKED-HERE" not in err:
            failures.append(f"A5 stderr not surfaced: {err!r}")

        # A6: PostToolUse all-ok -> exit 0, no stderr.
        code, out, err = _capture_dispatch(
            mod, "PostToolUse",
            [("ok", h_ok), ("ok2", h_ok)], "{}",
        )
        if code != 0:
            failures.append(f"A6 expected exit 0, got {code}")
        elif err.strip():
            failures.append(f"A6 unexpected stderr: {err!r}")

    # B1: end-to-end with the REAL registry, near-full context -> valid JSON.
    fd, tpath = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        rec = {"type": "assistant", "message": {"model": "claude-opus-4-8",
               "usage": {"input_tokens": 880000, "output_tokens": 0,
                         "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}}
        fh.write(json.dumps(rec) + "\n")
    payload = json.dumps({"prompt": "do a small thing", "session_id": "smoke-dispatch",
                          "transcript_path": tpath, "model": "claude-opus-4-8"})
    rc, out, err = _run_subprocess("UserPromptSubmit", payload, {"QREV_AUTO_LEVEL": "0"})
    if rc != 0:
        failures.append(f"B1 exit {rc} (stderr: {err[:160]})")
    elif out:
        try:
            obj = json.loads(out)
            if "context-budget" not in obj["hookSpecificOutput"]["additionalContext"]:
                failures.append(f"B1 context-budget gate did not run through dispatcher: {out[:160]}")
        except Exception as e:
            failures.append(f"B1 invalid combined JSON: {out[:160]} ({e})")
    else:
        failures.append("B1 expected context-budget output, got nothing")
    try:
        os.unlink(tpath)
    except OSError:
        pass

    # B2: malformed stdin -> exit 0, output empty or valid JSON.
    rc, out, err = _run_subprocess("UserPromptSubmit", "{not json", {"QREV_AUTO_LEVEL": "0"})
    if rc != 0:
        failures.append(f"B2 exit {rc}")
    elif out:
        try:
            json.loads(out)
        except Exception:
            failures.append(f"B2 produced invalid JSON: {out[:160]}")

    if failures:
        print("FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print("PASS (8 cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
