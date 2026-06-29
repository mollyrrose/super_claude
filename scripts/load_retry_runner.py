#!/usr/bin/env python3
"""load_retry_runner.py -- load-aware retry runner for hang-prone commands.

WHAT THIS IS FOR
----------------
Tool/shell calls on this machine sometimes hang or fail when the box is already
pegged (several Claude / PowerShell windows churning at once). This wrapper runs
ONE command defensively:

  1. GATE on system load before each attempt: read total CPU% and free RAM, and
     also survey the other heavy windows (claude / pwsh / powershell / node). If
     the machine is already over the threshold, WAIT (variable backoff) instead
     of piling on -- this is the feasible version of "start them one by one":
     the runner serialises its own launches behind available capacity.
  2. RUN with a hard timeout so a wedged command is killed (process tree), not
     left hanging forever.
  3. RETRY with a variable/jittered backoff until the command succeeds or the
     attempt / overall-deadline budget runs out.

THE HARD LIMIT (read this -- it is the same wall window_watchdog.py documents):
a separate process CANNOT resume a *frozen interactive Claude window*. Nothing
outside that window can type "continue" into its REPL. So this runner can:
  - retry and restart commands / processes IT launches,
  - MONITOR other claude/pwsh windows' load and gate its own work on it,
but it CANNOT un-stick another already-hung interactive Claude window. For that,
window_watchdog.py only DETECTS + ALERTS -- by design. Do not expect this script
to revive a dead window; it manages the command you hand it.

USAGE
-----
    python load_retry_runner.py [opts] -- <command...>
    python load_retry_runner.py --timeout 15 --max-attempts 6 -- git fetch
    python load_retry_runner.py --json -- git -C "D:/p" status --porcelain
    python load_retry_runner.py --probe          # print one load reading + exit

Everything after `--` is the command, run via the shell. Exit code is the
command's own exit code on success, or 1 if every attempt failed / the deadline
was hit before a green light.

KILL SWITCH
-----------
  - LOAD_RETRY_DISABLE=1  -> pass-through: run the command once, no gating, no
    retry (so a bad gate can never block you).
  - Or just call the command directly without this wrapper. It is a one-off
    helper, not a daemon or hook -- nothing persists when it exits.

Dependencies: none required. Uses psutil if importable for cheaper/finer
readings; otherwise falls back to PowerShell CIM queries (Windows) or /proc and
the load average (POSIX). Designed to degrade to "gate open" rather than block
when load cannot be read -- it must never become the thing that wedges you.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

# ----------------------------------------------------------------------------
# Load reading -- psutil if present, else OS fallbacks. Always returns a dict;
# on total failure returns an all-None reading so the gate fails OPEN.
# ----------------------------------------------------------------------------

HEAVY_NAMES = ("claude", "pwsh", "powershell", "node")


def _read_load_psutil():
    import psutil  # type: ignore
    vm = psutil.virtual_memory()
    return {
        "cpu_pct": float(psutil.cpu_percent(interval=0.3)),
        "mem_free_gb": vm.available / (1024 ** 3),
        "mem_total_gb": vm.total / (1024 ** 3),
        "source": "psutil",
    }


def _read_load_windows():
    """CPU% + free/total RAM via CIM. Short, hard-timeout PowerShell call."""
    ps = (
        "$c=(Get-CimInstance Win32_Processor | "
        "Measure-Object -Property LoadPercentage -Average).Average; "
        "$o=Get-CimInstance Win32_OperatingSystem; "
        "[pscustomobject]@{cpu=$c; freeKB=$o.FreePhysicalMemory; "
        "totalKB=$o.TotalVisibleMemorySize} | ConvertTo-Json -Compress"
    )
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, text=True, timeout=10,
    )
    data = json.loads(out.stdout.strip())
    free_gb = float(data["freeKB"]) / (1024 ** 2)
    total_gb = float(data["totalKB"]) / (1024 ** 2)
    cpu = data.get("cpu")
    return {
        "cpu_pct": float(cpu) if cpu is not None else None,
        "mem_free_gb": free_gb,
        "mem_total_gb": total_gb,
        "source": "cim",
    }


def _read_load_posix():
    cpu = None
    try:
        load1, _, _ = os.getloadavg()
        ncpu = os.cpu_count() or 1
        cpu = min(100.0, 100.0 * load1 / ncpu)
    except (OSError, AttributeError):
        pass
    free_gb = total_gb = None
    try:
        with open("/proc/meminfo", "r") as fh:
            mem = {}
            for line in fh:
                k, _, rest = line.partition(":")
                mem[k.strip()] = float(rest.strip().split()[0])  # kB
        total_gb = mem["MemTotal"] / (1024 ** 2)
        avail = mem.get("MemAvailable", mem.get("MemFree", 0.0))
        free_gb = avail / (1024 ** 2)
    except (OSError, KeyError, ValueError, IndexError):
        pass
    return {"cpu_pct": cpu, "mem_free_gb": free_gb, "mem_total_gb": total_gb,
            "source": "posix"}


def read_load():
    """Best-effort load reading. Never raises; failure -> all-None (gate opens)."""
    try:
        return _read_load_psutil()
    except Exception:
        pass
    try:
        if sys.platform.startswith("win"):
            return _read_load_windows()
        return _read_load_posix()
    except Exception:
        return {"cpu_pct": None, "mem_free_gb": None, "mem_total_gb": None,
                "source": "unavailable"}


def summarize_heavy(rows, top=8):
    """Compact view of the heavy-window survey: per-name counts + total MB, and
    the top-N processes by memory. Keeps --probe output small on a dev box where
    node.exe alone can be dozens of entries."""
    by_name = {}
    total_mb = 0.0
    for r in rows:
        name = r.get("name", "?")
        mb = r.get("mem_mb") or 0.0
        total_mb += mb
        slot = by_name.setdefault(name, {"count": 0, "mem_mb": 0.0})
        slot["count"] += 1
        slot["mem_mb"] += mb
    top_rows = sorted(rows, key=lambda r: (r.get("mem_mb") or 0.0), reverse=True)[:top]
    return {
        "count": len(rows),
        "total_mem_mb": round(total_mb, 1),
        "by_name": {k: {"count": v["count"], "mem_mb": round(v["mem_mb"], 1)}
                    for k, v in sorted(by_name.items())},
        "top": [{"pid": r.get("pid"), "name": r.get("name"),
                 "mem_mb": round(r.get("mem_mb") or 0.0, 1)} for r in top_rows],
    }


def list_heavy_windows():
    """Survey other heavy processes (claude/pwsh/powershell/node) for context.
    Returns a list of {pid,name,mem_mb}. Best-effort; [] on failure."""
    try:
        import psutil  # type: ignore
        rows = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            name = (p.info.get("name") or "").lower()
            if any(h in name for h in HEAVY_NAMES):
                mi = p.info.get("memory_info")
                rows.append({"pid": p.info["pid"], "name": name,
                             "mem_mb": (mi.rss / (1024 ** 2)) if mi else None})
        return rows
    except Exception:
        pass
    if sys.platform.startswith("win"):
        try:
            ps = (
                "Get-Process | Where-Object { $_.ProcessName -match "
                "'claude|pwsh|powershell|node' } | Select-Object Id,ProcessName,"
                "@{n='memMB';e={[math]::Round($_.WorkingSet64/1MB)}} | "
                "ConvertTo-Json -Compress"
            )
            out = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True, text=True, timeout=10,
            )
            raw = out.stdout.strip()
            if not raw:
                return []
            data = json.loads(raw)
            if isinstance(data, dict):
                data = [data]
            return [{"pid": d.get("Id"), "name": str(d.get("ProcessName", "")).lower(),
                     "mem_mb": d.get("memMB")} for d in data]
        except Exception:
            return []
    return []


# ----------------------------------------------------------------------------
# Pure decisions -- extracted so the smoketest can exercise them deterministically.
# ----------------------------------------------------------------------------

def gate_open(load, cpu_max, mem_min_gb):
    """Decide whether there is capacity to launch now.

    Returns (ok: bool, reason: str). Fails OPEN on unreadable metrics: a metric
    that is None is treated as 'cannot prove overloaded', so the gate does not
    become the thing that blocks you.
    """
    cpu = load.get("cpu_pct")
    free = load.get("mem_free_gb")
    if cpu is not None and cpu >= cpu_max:
        return False, "cpu %.0f%% >= %.0f%% cap" % (cpu, cpu_max)
    if free is not None and free < mem_min_gb:
        return False, "free RAM %.2fGB < %.2fGB floor" % (free, mem_min_gb)
    bits = []
    bits.append("cpu %.0f%%" % cpu if cpu is not None else "cpu n/a")
    bits.append("free %.2fGB" % free if free is not None else "ram n/a")
    return True, "ok (" + ", ".join(bits) + ")"


def next_backoff(attempt, base, cap, factor=2.0):
    """Variable, capped, deterministically-jittered backoff in seconds.

    attempt is 0-based. Grows base*factor**attempt up to cap, plus a small
    deterministic jitter (function of attempt -- no RNG, so it is reproducible
    in the smoketest and across resumes). Always within [0, cap*1.25].
    """
    raw = base * (factor ** max(0, attempt))
    raw = min(raw, cap)
    jitter = (((attempt * 37) % 100) / 100.0) * base * 0.25
    return round(raw + jitter, 3)


# ----------------------------------------------------------------------------
# Running a single attempt with a hard timeout and a real process-tree kill.
# ----------------------------------------------------------------------------

def _kill_tree(proc):
    try:
        if sys.platform.startswith("win"):
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=10)
        else:
            proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_once(command, timeout):
    """Run command (string, via shell) with a hard timeout. Returns a dict:
    {rc, timed_out, duration}. Kills the whole tree on timeout so nothing is
    left hanging. stdout/stderr stream to this process's stdout/stderr."""
    start = time.time()
    # nosemgrep: subprocess-shell-true -- `command` is the operator-provided shell command this runner exists to execute (shell semantics required); not untrusted external input
    proc = subprocess.Popen(command, shell=True)
    try:
        rc = proc.wait(timeout=timeout)
        return {"rc": rc, "timed_out": False, "duration": time.time() - start}
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            proc.wait(timeout=2)
        except Exception:
            pass
        return {"rc": None, "timed_out": True, "duration": time.time() - start}


# ----------------------------------------------------------------------------
# Orchestration: gate-wait then attempt, retry with backoff until budget spent.
# ----------------------------------------------------------------------------

def _emit(msg, quiet):
    if not quiet:
        sys.stderr.write("[load-retry] " + msg + "\n")
        sys.stderr.flush()


def wait_for_green(cfg, deadline, quiet):
    """Poll load until the gate opens or the overall deadline passes.
    Returns True if green, False if the deadline was hit first."""
    if cfg["no_gate"]:
        return True
    poll = 0
    while True:
        load = read_load()
        ok, reason = gate_open(load, cfg["cpu_max"], cfg["mem_min_gb"])
        if ok:
            _emit("green light: " + reason, quiet)
            return True
        if time.time() >= deadline:
            _emit("deadline hit while waiting for capacity (" + reason + ")", quiet)
            return False
        wait = next_backoff(poll, cfg["base_interval"], cfg["max_interval"])
        wait = min(wait, max(0.0, deadline - time.time()))
        heavy = list_heavy_windows()
        _emit("holding: %s; %d heavy window(s); waiting %.1fs"
              % (reason, len(heavy), wait), quiet)
        if wait <= 0:
            return False
        time.sleep(wait)
        poll += 1


def run_with_retry(command, cfg, quiet=False):
    """Full loop. Returns the final rc (command's own rc on success, else 1)."""
    start = time.time()
    deadline = start + cfg["max_wait"]
    last = {"rc": 1}
    for attempt in range(cfg["max_attempts"]):
        if not wait_for_green(cfg, deadline, quiet):
            _emit("giving up: no capacity within budget", quiet)
            return 1
        _emit("attempt %d/%d: %s" % (attempt + 1, cfg["max_attempts"], command), quiet)
        last = run_once(command, cfg["timeout"])
        if last["timed_out"]:
            _emit("attempt %d timed out after %.0fs (killed)"
                  % (attempt + 1, cfg["timeout"]), quiet)
        elif last["rc"] == 0:
            _emit("success on attempt %d (%.1fs)" % (attempt + 1, last["duration"]), quiet)
            return 0
        else:
            _emit("attempt %d exited rc=%s" % (attempt + 1, last["rc"]), quiet)
        if attempt + 1 >= cfg["max_attempts"] or time.time() >= deadline:
            break
        back = next_backoff(attempt, cfg["base_interval"], cfg["max_interval"])
        back = min(back, max(0.0, deadline - time.time()))
        if back <= 0:
            break
        _emit("backing off %.1fs before retry" % back, quiet)
        time.sleep(back)
    _emit("exhausted: %d attempt(s), last rc=%s timed_out=%s"
          % (cfg["max_attempts"], last.get("rc"), last.get("timed_out")), quiet)
    return 1


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def build_arg_parser():
    p = argparse.ArgumentParser(
        description="Load-aware retry runner for hang-prone commands.",
        epilog="Everything after -- is the command. KILL SWITCH: LOAD_RETRY_DISABLE=1.")
    p.add_argument("--timeout", type=float, default=120.0,
                   help="Hard per-attempt timeout, seconds (default 120).")
    p.add_argument("--max-attempts", type=int, default=5,
                   help="Maximum attempts (default 5).")
    p.add_argument("--base-interval", type=float, default=2.0,
                   help="Base backoff seconds (default 2).")
    p.add_argument("--max-interval", type=float, default=30.0,
                   help="Backoff cap seconds (default 30).")
    p.add_argument("--max-wait", type=float, default=600.0,
                   help="Overall deadline across all attempts+waits, seconds (default 600).")
    p.add_argument("--cpu-max", type=float, default=92.0,
                   help="Hold launches when total CPU%% >= this (default 92).")
    p.add_argument("--mem-min-gb", type=float, default=2.0,
                   help="Hold launches when free RAM < this many GB (default 2).")
    p.add_argument("--no-gate", action="store_true",
                   help="Skip load gating; retry only.")
    p.add_argument("--quiet", action="store_true", help="Suppress progress lines.")
    p.add_argument("--json", action="store_true",
                   help="Print one JSON status line at the end (machine-readable).")
    p.add_argument("--probe", action="store_true",
                   help="Print one load reading + heavy-window survey, then exit 0.")
    p.add_argument("command", nargs=argparse.REMAINDER,
                   help="Command after -- (e.g. -- git fetch).")
    return p


def _strip_leading_dashdash(rest):
    return rest[1:] if rest and rest[0] == "--" else rest


def main(argv=None):
    args = build_arg_parser().parse_args(argv)

    if args.probe:
        load = read_load()
        heavy = summarize_heavy(list_heavy_windows())
        ok, reason = gate_open(load, args.cpu_max, args.mem_min_gb)
        print(json.dumps({"load": load, "gate_open": ok, "reason": reason,
                          "heavy_windows": heavy}, indent=2))
        return 0

    parts = _strip_leading_dashdash(args.command)
    if not parts:
        sys.stderr.write("[load-retry] no command given (use: ... -- <command>)\n")
        return 2
    command = " ".join(parts)

    # Kill switch: pass-through single run, no gate, no retry.
    if os.environ.get("LOAD_RETRY_DISABLE") == "1":
        res = run_once(command, args.timeout)
        return 0 if res["rc"] == 0 else 1

    cfg = {
        "timeout": args.timeout, "max_attempts": max(1, args.max_attempts),
        "base_interval": args.base_interval, "max_interval": args.max_interval,
        "max_wait": args.max_wait, "cpu_max": args.cpu_max,
        "mem_min_gb": args.mem_min_gb, "no_gate": args.no_gate,
    }
    rc = run_with_retry(command, cfg, quiet=args.quiet)
    if args.json:
        print(json.dumps({"command": command, "final_rc": rc, "config": cfg}))
    return rc


if __name__ == "__main__":
    sys.exit(main())
