#!/usr/bin/env python3
"""Smoke test for context_budget_gate.py.

Runs the hook as a subprocess with crafted stdin payloads and asserts the
right tier fires. No network, no real transcript -- the payload carries an
inline `usage` via a temp transcript file written per case.

Cases:
 1. near-full (remaining <= QCLOSE_REMAIN_PCT) -> qClose banner tier.
 2. soft (remaining ~22%) -> generic soft warning, NOT the qClose banner.
 3. healthy (remaining ~80%) -> no additionalContext at all.
 4. malformed stdin -> exit 0, no crash, no output.
 5. GLM model id -> 200K window detected (NOT the 1M Opus default), so the same
    token count that is "healthy" under 1M fires the qClose banner under GLM.
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


def _run(stdin_text: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, GATE],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.returncode, proc.stdout.strip()


def _payload(used_tokens: int, model_id: str = "claude-opus-4-8") -> str:
    tp = _write_transcript(used_tokens, model_id)
    return json.dumps(
        {
            "prompt": "do a small thing",
            "session_id": "smoke",
            "transcript_path": tp,
            "model": model_id,
        }
    )


def main() -> int:
    failures = []

    # Case 1: remaining ~12% -> qClose banner.
    rc, out = _run(_payload(int(LIMIT * 0.88)))
    if rc != 0:
        failures.append(f"case1 exit {rc}")
    elif "USER INPUT REQUIRED" not in out or "/qClose" not in out:
        failures.append(f"case1 missing qClose banner: {out[:160]}")

    # Case 2: remaining ~22% -> soft warning, not the qClose banner.
    rc, out = _run(_payload(int(LIMIT * 0.78)))
    if rc != 0:
        failures.append(f"case2 exit {rc}")
    elif "USER INPUT REQUIRED" in out:
        failures.append(f"case2 wrongly fired qClose banner: {out[:160]}")
    elif "context-budget" not in out:
        failures.append(f"case2 missing soft warning: {out[:160]}")

    # Case 3: remaining ~80% -> no gate at all.
    rc, out = _run(_payload(int(LIMIT * 0.20)))
    if rc != 0:
        failures.append(f"case3 exit {rc}")
    elif out:
        failures.append(f"case3 should be silent: {out[:160]}")

    # Case 4: malformed stdin -> exit 0, silent.
    rc, out = _run("{not json")
    if rc != 0:
        failures.append(f"case4 exit {rc}")
    elif out:
        failures.append(f"case4 should be silent: {out[:160]}")

    # Case 5a: GLM id at 88% of the 200K window -> qClose banner (proves the
    # GLM window is detected). The SAME token count under the 1M Opus default
    # would be ~82% remaining and stay silent.
    glm_used = int(GLM_LIMIT * 0.88)
    rc, out = _run(_payload(glm_used, "glm-4.6"))
    if rc != 0:
        failures.append(f"case5a exit {rc}")
    elif "USER INPUT REQUIRED" not in out:
        failures.append(f"case5a GLM window not detected (no qClose banner): {out[:160]}")
    # Case 5b: control -- the identical token count under Opus 1M stays silent.
    rc, out = _run(_payload(glm_used, "claude-opus-4-8"))
    if rc != 0:
        failures.append(f"case5b exit {rc}")
    elif out:
        failures.append(f"case5b should be silent under 1M: {out[:160]}")

    if failures:
        print("FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print("PASS (6 cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
