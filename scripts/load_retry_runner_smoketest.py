#!/usr/bin/env python3
"""Smoketest for load_retry_runner.py -- pure decisions + real subprocess paths.

Fast, dependency-free. Run: python load_retry_runner_smoketest.py
Exit 0 = all pass, 1 = a check failed (prints which).
"""

from __future__ import annotations

import sys
import time

import load_retry_runner as lr

FAILS = []


def check(name, cond):
    if cond:
        print("[ok] " + name)
    else:
        print("[fail] " + name)
        FAILS.append(name)


def test_gate_open():
    # Over CPU cap -> closed.
    ok, _ = lr.gate_open({"cpu_pct": 95.0, "mem_free_gb": 8.0}, 92.0, 2.0)
    check("gate closes over cpu cap", ok is False)
    # Under RAM floor -> closed.
    ok, _ = lr.gate_open({"cpu_pct": 10.0, "mem_free_gb": 1.0}, 92.0, 2.0)
    check("gate closes under ram floor", ok is False)
    # Healthy -> open.
    ok, _ = lr.gate_open({"cpu_pct": 10.0, "mem_free_gb": 8.0}, 92.0, 2.0)
    check("gate opens when healthy", ok is True)
    # Unreadable metrics fail OPEN (never become the blocker).
    ok, _ = lr.gate_open({"cpu_pct": None, "mem_free_gb": None}, 92.0, 2.0)
    check("gate fails open on unreadable load", ok is True)


def test_next_backoff():
    b0 = lr.next_backoff(0, 2.0, 30.0)
    b1 = lr.next_backoff(1, 2.0, 30.0)
    b2 = lr.next_backoff(2, 2.0, 30.0)
    check("backoff grows with attempt", b0 < b1 < b2)
    big = lr.next_backoff(20, 2.0, 30.0)
    check("backoff respects cap (+jitter)", big <= 30.0 * 1.25)
    check("backoff deterministic", lr.next_backoff(3, 2.0, 30.0) == lr.next_backoff(3, 2.0, 30.0))


def test_run_once_success():
    res = lr.run_once(sys.executable + ' -c "import sys; sys.exit(0)"', timeout=15)
    check("run_once success rc=0", res["rc"] == 0 and res["timed_out"] is False)


def test_run_once_timeout():
    # Sleep longer than the timeout -> killed, timed_out True. Wall time is not
    # asserted tightly: on a loaded machine process spawn + tree-kill add seconds
    # (exactly the condition this tool exists for). We assert correctness, not speed.
    res = lr.run_once(sys.executable + ' -c "import time; time.sleep(30)"', timeout=1.0)
    check("run_once times out + kills", res["timed_out"] is True and res["rc"] is None)
    check("run_once returned before the full sleep", res["duration"] < 25)


def test_retry_success_first():
    cfg = dict(timeout=15, max_attempts=3, base_interval=0.1, max_interval=0.2,
               max_wait=30, cpu_max=92, mem_min_gb=2, no_gate=True)
    rc = lr.run_with_retry(sys.executable + ' -c "import sys; sys.exit(0)"', cfg, quiet=True)
    check("retry returns 0 on first success", rc == 0)


def test_retry_exhausts_on_failure():
    cfg = dict(timeout=15, max_attempts=2, base_interval=0.05, max_interval=0.1,
               max_wait=30, cpu_max=92, mem_min_gb=2, no_gate=True)
    start = time.time()
    rc = lr.run_with_retry(sys.executable + ' -c "import sys; sys.exit(3)"', cfg, quiet=True)
    elapsed = time.time() - start
    check("retry returns 1 when all attempts fail", rc == 1)
    # Backoff itself is tiny here (base 0.05). Any large wall time is process
    # spawn on a loaded box, not our delay -- so the bound is generous, just a
    # guard against an accidental oversized sleep in the loop.
    check("retry did not insert an oversized sleep", elapsed < 60)


def test_read_load_shape():
    load = lr.read_load()
    keys = {"cpu_pct", "mem_free_gb", "mem_total_gb", "source"}
    check("read_load returns expected keys", keys.issubset(load.keys()))


def test_strip_dashdash():
    check("strips leading --", lr._strip_leading_dashdash(["--", "git", "fetch"]) == ["git", "fetch"])
    check("no -- left alone", lr._strip_leading_dashdash(["git", "fetch"]) == ["git", "fetch"])


def main():
    test_gate_open()
    test_next_backoff()
    test_run_once_success()
    test_run_once_timeout()
    test_retry_success_first()
    test_retry_exhausts_on_failure()
    test_read_load_shape()
    test_strip_dashdash()
    if FAILS:
        print("\nFAILED: " + ", ".join(FAILS))
        return 1
    print("\nall smoketests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
