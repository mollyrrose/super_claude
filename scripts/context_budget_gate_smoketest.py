#!/usr/bin/env python3
"""Smoke test for context_budget_gate.py.

Runs the hook as a subprocess with crafted stdin payloads and asserts the
right tier fires. No network, no real transcript -- the payload carries an
inline `usage` via a temp transcript file written per case.

Cases:
 1a. near-full (remaining <= QCLOSE_REMAIN_PCT) -> NON-BLOCKING one-line
     /qClose notice (no USER INPUT REQUIRED banner -- the old stop-and-banner
     wording deadlocked against loop/until Stop hooks).
 1b. same session, same usage -> qClose dedupe holds, silent.
 1c. same session, +12% more used -> qClose re-fires past QCLOSE_REDO_DELTA.
 2a. soft (remaining ~22%, flush disabled) -> generic soft warning, NOT qClose.
 2b. same session repeated -> soft dedupe holds, silent.
 3. healthy (remaining ~80%) -> no additionalContext at all.
 4. malformed stdin -> exit 0, no crash, no output.
 5a. GLM model id -> 200K window detected (NOT the 1M default), so the same
     token count that is "healthy" under 1M fires the near-full notice under GLM.
 5b. control -- identical token count under Opus 1M stays silent.
 6a. pre-compact flush band (remaining ~30%, fresh session) -> /qUpd flush tier.
 6b. same session repeated -> fire-once guard holds, silent.
 6c. flush disabled via CC_BUDGET_QUPD_DISABLE=1 -> silent at the same band.
 7a. claude-sonnet-5 at 300K live tokens -> silent (sonnet-5 is a 1M family;
     the 2026-08-05 regression budgeted it 200K and fired NEAR-FULL at ~30%).
 7b. UNKNOWN model id at 300K live tokens -> silent (self-correction: observed
     usage above the guessed 200K window proves the window is 1M).

The tier state is isolated to a temp file (CC_BUDGET_QUPD_STATE) and the
statusline bridge to a nonexistent temp path (CC_BUDGET_BRIDGE_PATH) so the run
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

    # Isolate tier state to a temp file and the statusline bridge to a missing
    # path so the run never touches real ~/.claude state and stays deterministic.
    fd, state_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(state_path)  # start with no state (fresh); the hook recreates it
    bridge_missing = state_path + ".no-bridge.json"
    base = {"CC_BUDGET_QUPD_STATE": state_path, "CC_BUDGET_BRIDGE_PATH": bridge_missing}
    flush_off = dict(base, CC_BUDGET_QUPD_DISABLE="1")
    flush_on = dict(base)

    # Case 1a: remaining ~12% -> non-blocking near-full /qClose notice.
    rc, out = _run(_payload(int(LIMIT * 0.88), session_id="qclose-fresh"), env=flush_on)
    if rc != 0:
        failures.append(f"case1a exit {rc}")
    elif "NEAR-FULL" not in out or "/qClose" not in out or "CONTINUE" not in out:
        failures.append(f"case1a missing non-blocking qClose notice: {out[:160]}")
    elif "*    USER INPUT REQUIRED" in out:
        failures.append(f"case1a must not force the banner block: {out[:160]}")
    elif "Do NOT start" in out:
        failures.append(f"case1a must not order a stop: {out[:160]}")

    # Case 1b: same session, same usage -> dedupe holds, silent.
    rc, out = _run(_payload(int(LIMIT * 0.88), session_id="qclose-fresh"), env=flush_on)
    if rc != 0:
        failures.append(f"case1b exit {rc}")
    elif out:
        failures.append(f"case1b should be silent (qclose dedupe): {out[:160]}")

    # Case 1c: same session, +12% used (past QCLOSE_REDO_DELTA=10) -> re-fires.
    rc, out = _run(_payload(LIMIT, session_id="qclose-fresh"), env=flush_on)
    if rc != 0:
        failures.append(f"case1c exit {rc}")
    elif "NEAR-FULL" not in out:
        failures.append(f"case1c should re-fire past redo delta: {out[:160]}")

    # Case 2a: remaining ~22%, flush disabled -> soft warning, not qClose notice.
    rc, out = _run(_payload(int(LIMIT * 0.78), session_id="soft-fresh"), env=flush_off)
    if rc != 0:
        failures.append(f"case2a exit {rc}")
    elif "NEAR-FULL" in out:
        failures.append(f"case2a wrongly fired qClose notice: {out[:160]}")
    elif "context-budget" not in out:
        failures.append(f"case2a missing soft warning: {out[:160]}")
    elif "PRE-COMPACT FLUSH" in out:
        failures.append(f"case2a flush fired despite disable: {out[:160]}")

    # Case 2b: same session, same usage -> soft dedupe holds, silent.
    rc, out = _run(_payload(int(LIMIT * 0.78), session_id="soft-fresh"), env=flush_off)
    if rc != 0:
        failures.append(f"case2b exit {rc}")
    elif out:
        failures.append(f"case2b should be silent (soft dedupe): {out[:160]}")

    # Case 3: remaining ~80% -> no gate at all.
    rc, out = _run(_payload(int(LIMIT * 0.20), session_id="healthy"), env=flush_on)
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

    # Case 5a: GLM id at 88% of the 200K window -> near-full notice (proves the
    # GLM window is detected). The SAME token count under the 1M Opus default
    # would be ~82% remaining and stay silent.
    glm_used = int(GLM_LIMIT * 0.88)
    rc, out = _run(_payload(glm_used, "glm-4.6", session_id="glm-full"), env=flush_on)
    if rc != 0:
        failures.append(f"case5a exit {rc}")
    elif "NEAR-FULL" not in out:
        failures.append(f"case5a GLM window not detected (no near-full notice): {out[:160]}")
    # Case 5b: control -- the identical token count under Opus 1M stays silent.
    rc, out = _run(_payload(glm_used, "claude-opus-4-8", session_id="glm-ctrl"), env=flush_on)
    if rc != 0:
        failures.append(f"case5b exit {rc}")
    elif out:
        failures.append(f"case5b should be silent under 1M: {out[:160]}")

    # Case 6a: remaining ~30% (used 70%), fresh session -> pre-compact qUpd
    # flush tier fires (not the qClose notice). Uses a fresh session_id so the
    # fire-once guard sees no prior flush.
    rc, out = _run(_payload(int(LIMIT * 0.70), session_id="flush-fresh"), env=flush_on)
    if rc != 0:
        failures.append(f"case6a exit {rc}")
    elif "PRE-COMPACT FLUSH" not in out or "/qUpd" not in out:
        failures.append(f"case6a missing qUpd flush tier: {out[:200]}")
    elif "NEAR-FULL" in out:
        failures.append(f"case6a wrongly fired qClose notice: {out[:160]}")

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

    # Case 7a: claude-sonnet-5 with 300K live tokens -> 1M family, ~30% used,
    # silent (the 2026-08-05 regression fired NEAR-FULL here).
    rc, out = _run(_payload(300_000, "claude-sonnet-5", session_id="sonnet5"), env=flush_on)
    if rc != 0:
        failures.append(f"case7a exit {rc}")
    elif out:
        failures.append(f"case7a sonnet-5 must budget 1M (got output): {out[:160]}")

    # Case 7b: UNKNOWN model id with 300K live tokens (> 200K fallback window)
    # -> self-correction snaps the window to 1M, ~30% used, silent.
    rc, out = _run(_payload(300_000, "claude-zeta-9", session_id="zeta9"), env=flush_on)
    if rc != 0:
        failures.append(f"case7b exit {rc}")
    elif out:
        failures.append(f"case7b self-correction failed (got output): {out[:160]}")

    for p in (state_path, bridge_missing):
        try:
            os.remove(p)
        except OSError:
            pass

    if failures:
        print("FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print("PASS (14 cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
