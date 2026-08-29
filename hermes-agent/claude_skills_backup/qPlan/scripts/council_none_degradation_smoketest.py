#!/usr/bin/env python3
"""None-degradation falsifier for qPlan's cross-model critic scripts (ISC #7
hard prerequisite for council mode). Every critic script invoked with an
invalid/absent credential must MUTE: exit code 2, non-empty stderr, no Python
traceback, and no parseable {"verdict": ...} JSON on stdout. A script that
raises instead of muting would crash council's phase-1 fan-out instead of
just shrinking the active-voice roster.

Mute contract (P2, SETTLED): exit 2, NOT exit 0. This test asserts exit==2.
Do NOT change any critic script to exit 0 to make a case here pass -- that
would break cross_model_critics_smoketest.py's returncode==2 asserts and the
documented orchestrator contract (qPlan SKILL.md: "any failure just mutes the
lens (exit 2)").

Stdlib-only, offline -- every case either omits credentials or points a
provider's base-url override at a closed local port, so no real network call
ever completes. Run:
    python council_none_degradation_smoketest.py

Unlike cross_model_critics_smoketest.py (which fails fast on the first bad
check), this test does NOT stop at the first failure: it must be able to
report exactly which of the 6 critic scripts raise instead of mute in one run
(the mission's abort condition is "more than two scripts raise", which is
unobservable under fail-fast). It prints '[ok]'/'[fail]'/'[skip]' per case and
'ALL PASS (N checks)' only if nothing failed; otherwise it lists every failed
case and exits 1.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAYLOAD = '{"task":"t","plan":"p","ledger":[]}'
CASE_TIMEOUT = 30

n = 0
failures = []


def check(cond, label, detail=""):
    global n
    n += 1
    if cond:
        print(f"[ok] {label}")
    else:
        print(f"[fail] {label}" + (f" -- {detail}" if detail else ""))
        failures.append(label)


def _stdout_has_verdict(stdout: str) -> bool:
    """True if stdout parses as a JSON object containing a 'verdict' key --
    i.e. the script produced real critic output instead of muting."""
    s = stdout.strip()
    if not s:
        return False
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return False
    return isinstance(obj, dict) and "verdict" in obj


def _mute_ok(r: subprocess.CompletedProcess) -> bool:
    return (
        r.returncode == 2
        and len(r.stderr.strip()) > 0
        and "Traceback" not in r.stderr
        and "Traceback" not in r.stdout
        and not _stdout_has_verdict(r.stdout)
    )


def base_env(pop=()):
    env = dict(os.environ)
    for k in pop:
        env.pop(k, None)
    return env


def run_case(label, script, env, payload=PAYLOAD, timeout=CASE_TIMEOUT):
    """Run one critic script as a subprocess and assert the mute contract."""
    try:
        r = subprocess.run(
            [sys.executable, str(HERE / script)],
            input=payload, capture_output=True, text=True,
            env=env, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        check(False, label, f"{script} did not exit within {timeout}s (hang instead of mute)")
        return None
    detail = f"returncode={r.returncode} stderr={r.stderr[:300]!r} stdout={r.stdout[:200]!r}"
    check(_mute_ok(r), label, detail)
    return r


def run_case_offline(label, script, make_env, timeout=CASE_TIMEOUT):
    """Like run_case, but make_env(port) builds the env for a given closed
    local port. Some Windows configs don't fail-fast on a connect to port 9
    (observed risk, not universal), so retry once on port 1; if BOTH hang,
    skip the case (do not fail the run) and say why -- the kill-switch /
    no-key cases already prove the script's controlled mute path."""
    for port in (9, 1):
        env = make_env(port)
        try:
            r = subprocess.run(
                [sys.executable, str(HERE / script)],
                input=PAYLOAD, capture_output=True, text=True, env=env, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            continue
        detail = f"returncode={r.returncode} stderr={r.stderr[:300]!r} stdout={r.stdout[:200]!r}"
        check(_mute_ok(r), label, detail)
        return
    print(f"[skip] {label} -- port 9 and port 1 both hung past {timeout}s on this Windows config")


# --- case 1: openai_critic.py -- pop OPENAI_API_KEY, QPLAN_OPENAI_BACKEND (api default path) ---
run_case(
    "openai_critic mutes with no key",
    "openai_critic.py",
    base_env(["OPENAI_API_KEY", "QPLAN_OPENAI_BACKEND"]),
)

# --- case 2: deepseek_critic.py -- pop DEEPSEEK_API_KEY ---
run_case(
    "deepseek_critic mutes with no key",
    "deepseek_critic.py",
    base_env(["DEEPSEEK_API_KEY"]),
)

# --- case 3: subq_critic.py -- pop SUBQ_API_KEY, SUBQ_FREE_API_KEY, SUBQ_FREE_BASE_URL, SUBQ_TIER ---
run_case(
    "subq_critic mutes with no key",
    "subq_critic.py",
    base_env(["SUBQ_API_KEY", "SUBQ_FREE_API_KEY", "SUBQ_FREE_BASE_URL", "SUBQ_TIER"]),
)

# --- case 4: glm_critic.py -- pop GLM_API_KEY, ZAI_API_KEY ---
run_case(
    "glm_critic mutes with no key",
    "glm_critic.py",
    base_env(["GLM_API_KEY", "ZAI_API_KEY"]),
)

# --- case 5: claude_critic.py no-backend -- pop ANTHROPIC_API_KEY, CLAUDE_CRITIC_BACKEND,
# and set PATH to a fresh empty temp dir so shutil.which("claude") fails. Launched
# via sys.executable's absolute path, so the child still starts despite empty PATH. ---
with tempfile.TemporaryDirectory() as empty_path_dir:
    env5 = base_env(["ANTHROPIC_API_KEY", "CLAUDE_CRITIC_BACKEND"])
    env5["PATH"] = empty_path_dir
    run_case("claude_critic mutes with no backend available", "claude_critic.py", env5)

# --- case 6: claude_critic.py forced-api-no-key (P3 suspected raise) ---
env6 = base_env(["ANTHROPIC_API_KEY"])
env6["CLAUDE_CRITIC_BACKEND"] = "api"
run_case(
    "claude_critic mutes when backend forced to api with no key (P3)",
    "claude_critic.py",
    env6,
)

# --- case 7: ornith_critic.py kill switch ---
env7 = dict(os.environ)
env7["QPLAN_ORNITH_DISABLE"] = "1"
run_case("ornith_critic mutes via QPLAN_ORNITH_DISABLE", "ornith_critic.py", env7)


# --- case 8: ornith_critic.py unreachable (closed port) ---
def _env_ornith_unreachable(port):
    e = base_env(["QPLAN_ORNITH_DISABLE"])
    e["ORNITH_BASE_URL"] = f"http://127.0.0.1:{port}"
    return e


run_case_offline(
    "ornith_critic mutes when unreachable",
    "ornith_critic.py",
    _env_ornith_unreachable,
)

# --- case 9: invalid-key offline variants (URLError mute paths, no real network) ---
# openai/deepseek expose no base-url override -- their invalid-key path would hit
# the real endpoint, so live-fire is skipped here. Covered by code-read instead:
# both scripts exit 2 on HTTPError 401/403 (openai_critic.py ~line 220,
# deepseek_critic.py ~line 196) -- confirmed during recon.


def _env_glm_unreachable(port):
    e = dict(os.environ)
    e["GLM_API_KEY"] = "dummy"
    e["GLM_BASE_URL"] = f"http://127.0.0.1:{port}"
    return e


run_case_offline(
    "glm_critic mutes on unreachable base url (invalid-key offline variant)",
    "glm_critic.py",
    _env_glm_unreachable,
)


def _env_subq_unreachable(port):
    e = dict(os.environ)
    e["SUBQ_API_KEY"] = "dummy"
    e["SUBQ_BASE_URL"] = f"http://127.0.0.1:{port}"
    return e


run_case_offline(
    "subq_critic mutes on unreachable base url (invalid-key offline variant)",
    "subq_critic.py",
    _env_subq_unreachable,
)

if failures:
    print(f"\n{len(failures)} FAILED / {n} checks: " + ", ".join(failures))
    sys.exit(1)

print(f"\nALL PASS ({n} checks)")
