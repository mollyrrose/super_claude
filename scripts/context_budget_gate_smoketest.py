#!/usr/bin/env python3
"""Smoke test for context_budget_gate.py.

Runs the hook as a subprocess with crafted stdin payloads and asserts the
right tier fires. No network, no real transcript -- the payload carries an
inline `usage` via a temp transcript file written per case.

Cases:
 1. near-full (remaining <= QCLOSE_REMAIN_PCT) -> qClose banner tier.
 2. soft (remaining ~22%, flush disabled) -> generic soft warning, NOT qClose.
 3. healthy (remaining ~80%) -> no additionalContext at all.
 4. malformed stdin -> exit 0, no crash, no output.
 5. GLM model id -> 200K window detected (NOT the 1M Opus default), so the same
    token count that is "healthy" under 1M fires the qClose banner under GLM.
 6a. pre-compact flush band (remaining ~30%, fresh session) -> /qUpd flush tier.
 6b. same session repeated -> fire-once guard holds, silent.
 6c. flush disabled via CC_BUDGET_QUPD_DISABLE=1 -> silent at the same band.

The flush state is isolated to a temp file (CC_BUDGET_QUPD_STATE) so the run
never touches real ~/.claude state and stays deterministic across re-runs.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "context_budget_gate.py")
LIMIT = 1_000_000  # Opus 1M window (opus-4 family -> 1M in this setup)


GLM_LIMIT = 200_000  # GLM (z.ai) window in this setup


def _write_transcript(used_tokens: int, model_id: str = "claude-opus-4-8") -> str:
    """Write a one-line transcript whose latest usage sums to used_tokens."""
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    rec = {
        "type": "assistant",
        "message": {
            "model": model_id,
            "usage": {
                "input_tokens": used_tokens,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "output_tokens": 0,
            },
        },
    }
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return path


def _run(stdin_text: str, env: dict | None = None) -> tuple[int, str]:
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    proc = subprocess.run(
        [sys.executable, GATE],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=run_env,
    )
    return proc.returncode, proc.stdout.strip()


def _payload(
    used_tokens: int, model_id: str = "claude-opus-4-8", session_id: str = "smoke"
) -> str:
    tp = _write_transcript(used_tokens, model_id)
    return json.dumps(
        {
            "prompt": "do a small thing",
            "session_id": session_id,
            "transcript_path": tp,
            "model": model_id,
        }
    )


def main() -> int:
    failures = []

    # Isolate the qUpd-flush state to a temp file so the run never touches real
    # ~/.claude state and stays deterministic across re-runs.
    fd, state_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(state_path)  # start with no state (fresh); the hook recreates it
    flush_off = {"CC_BUDGET_QUPD_STATE": state_path, "CC_BUDGET_QUPD_DISABLE": "1"}
    flush_on = {"CC_BUDGET_QUPD_STATE": state_path}

    # Case 1: remaining ~12% -> qClose banner (qClose tier precedes flush).
    rc, out = _run(_payload(int(LIMIT * 0.88)), env=flush_on)
    if rc != 0:
        failures.append(f"case1 exit {rc}")
    elif "USER INPUT REQUIRED" not in out or "/qClose" not in out:
        failures.append(f"case1 missing qClose banner: {out[:160]}")

    # Case 2: remaining ~22%, flush disabled -> soft warning, not qClose banner.
    rc, out = _run(_payload(int(LIMIT * 0.78)), env=flush_off)
    if rc != 0:
        failures.append(f"case2 exit {rc}")
    elif "USER INPUT REQUIRED" in out:
        failures.append(f"case2 wrongly fired qClose banner: {out[:160]}")
    elif "context-budget" not in out:
        failures.append(f"case2 missing soft warning: {out[:160]}")
    elif "PRE-COMPACT FLUSH" in out:
        failures.append(f"case2 flush fired despite disable: {out[:160]}")

    # Case 3: remaining ~80% -> no gate at all.
    rc, out = _run(_payload(int(LIMIT * 0.20)), env=flush_on)
    if rc != 0:
        failures.append(f"case3 exit {rc}")
    elif out:
        failures.append(f"case3 should be silent: {out[:160]}")

    # Case 4: malformed stdin -> exit 0, silent.
    rc, out = _run("{not json", env=flush_on)
    if rc != 0:
        failures.append(f"case4 exit {rc}")
    elif out:
        failures.append(f"case4 should be silent: {out[:160]}")

    # Case 5a: GLM id at 88% of the 200K window -> qClose banner (proves the
    # GLM window is detected). The SAME token count under the 1M Opus default
    # would be ~82% remaining and stay silent.
    glm_used = int(GLM_LIMIT * 0.88)
    rc, out = _run(_payload(glm_used, "glm-4.6"), env=flush_on)
    if rc != 0:
        failures.append(f"case5a exit {rc}")
    elif "USER INPUT REQUIRED" not in out:
        failures.append(f"case5a GLM window not detected (no qClose banner): {out[:160]}")
    # Case 5b: control -- the identical token count under Opus 1M stays silent.
    rc, out = _run(_payload(glm_used, "claude-opus-4-8"), env=flush_on)
    if rc != 0:
        failures.append(f"case5b exit {rc}")
    elif out:
        failures.append(f"case5b should be silent under 1M: {out[:160]}")

    # Case 6a: remaining ~30% (used 70%), fresh session -> pre-compact qUpd
    # flush tier fires (not the qClose banner). Uses a fresh session_id so the
    # fire-once guard sees no prior flush.
    rc, out = _run(_payload(int(LIMIT * 0.70), session_id="flush-fresh"), env=flush_on)
    if rc != 0:
        failures.append(f"case6a exit {rc}")
    elif "PRE-COMPACT FLUSH" not in out or "/qUpd" not in out:
        failures.append(f"case6a missing qUpd flush tier: {out[:200]}")
    elif "USER INPUT REQUIRED" in out:
        failures.append(f"case6a wrongly fired qClose banner: {out[:160]}")

    # Case 6b: same session, same usage -> fire-once guard holds. At ~30%
    # remaining nothing else fires (above SOFT 25%), so output is silent.
    rc, out = _run(_payload(int(LIMIT * 0.70), session_id="flush-fresh"), env=flush_on)
    if rc != 0:
        failures.append(f"case6b exit {rc}")
    elif "PRE-COMPACT FLUSH" in out:
        failures.append(f"case6b flush re-fired (fire-once guard broken): {out[:160]}")
    elif out:
        failures.append(f"case6b should be silent after flush: {out[:160]}")

    # Case 6c: kill switch -- flush disabled at the same band -> silent.
    rc, out = _run(_payload(int(LIMIT * 0.70), session_id="flush-off"), env=flush_off)
    if rc != 0:
        failures.append(f"case6c exit {rc}")
    elif out:
        failures.append(f"case6c should be silent with flush disabled: {out[:160]}")

    try:
        os.remove(state_path)
    except OSError:
        pass

    if failures:
        print("FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print("PASS (9 cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
