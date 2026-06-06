---
name: tw
description: Run the PA RNG Timewaver mantras (Mipham + Seal) via the existing C++17 ritual engine. Use when user types `/tw`, `/tw <hours>`, `/tw watch`, or `/tw <hours> watch`. Default (no number) runs both blocks to 100 % of their caps (~8.5 h). A positive number sets a wall-clock cap in hours and the engine stops there. Gated by free RAM ≥ 4 GB; uses the gitignored config + binary already in place.
---

# tw — Timewaver mantra round

Invokes the existing PA RNG Timewaver service to run the Mipham + Seal mantra cycle. The compute work, RAM throttling, payload loading, and the 1-hour wall-clock budget are already implemented inside:

- C++17 binary: `cpp/rng_timewaver/bin/rng_timewaver.exe`
- TS scheduler: `backend/services/rngTimewaverScheduler.ts`
- Config: `backend/data/rng_timewaver/config.json` (gitignored)
- Payloads: `backend/data/rng_timewaver/mipham_block.txt` + `seal_block.txt` (gitignored)

**This skill only handles the gate + kick-off — never re-implement the engine.**

## Pre-flight

1. **Free physical memory check** (PowerShell):
   ```powershell
   $mem = Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory
   $freeGB = [math]::Round($mem.FreePhysicalMemory / 1024 / 1024, 2)
   ```
   **Threshold: ≥ 4 GB free.**

2. If `freeGB < 4`: stop, report the exact value, ask the user "defer or run anyway?". Do not start without an explicit yes.

3. If `freeGB ≥ 4`: proceed to invocation.

## Invocation

`/tw` accepts two optional arguments in **any order**:

| Arg | Meaning |
|---|---|
| (none) | Full run-to-cap. Both Mipham and Seal reach 100% of their caps. Wall-clock unlimited (engine stops only when every block hits its cap). At ~1.9 M iter/s on this machine, that's ~8.5 h. |
| `<N>` (positive number) | Run for **N hours** then stop, regardless of how far the bars got. Decimals allowed (`/tw 0.5` = 30 minutes, `/tw 1.5` = 90 minutes). Engine respects this wall-clock budget exactly; weighted RR still keeps Mipham% and Seal% in sync. |
| `watch` | Live progress bars in chat (otherwise the run is silent in background). Can be combined with `<N>`: `/tw 3 watch` or `/tw watch 3` both work. |

Pick the right Bash invocation based on which args the user actually passed:

### `/tw` — full run-to-cap, silent (background)

**`run_in_background: true`** mode:

```
cd D:/Projects/pa/privateassociations
npx tsx backend/services/rngTimewaverScheduler.ts run
```

### `/tw <N>` — N hours, silent (background)

**`run_in_background: true`** mode. Replace `<N>` with the requested number (e.g. `3`, `0.5`, `12`):

```
cd D:/Projects/pa/privateassociations
npx tsx backend/services/rngTimewaverScheduler.ts run <N>
```

### `/tw watch` — full run-to-cap, live bars

**`run_in_background: false`** mode (bars need foreground UX even though Claude Code captures stdout):

```
cd D:/Projects/pa/privateassociations
npx tsx backend/services/rngTimewaverScheduler.ts run watch
```

### `/tw <N> watch` — N hours, live bars

```
cd D:/Projects/pa/privateassociations
npx tsx backend/services/rngTimewaverScheduler.ts run <N> watch
```

Renders two ANSI progress bars — **Mipham** and **Seal** — that fill against each block's iteration cap, plus a header line with elapsed/budget time, free RAM, throttle ms, and live iter/s. The scheduler auto-detects when stdout is not a real TTY (e.g. piped or captured) and downgrades to one append-only progress frame every 10 s. Force the plain path anywhere with `RNG_TIMEWAVER_PROGRESS=plain`.

### Live display in Claude Code chat (no Monitor, no external terminal)

Inside Claude Code the background Bash captures stdout (`isTTY=false`), so the scheduler writes one 3-line frame every 10 s into the task's `.output` file. To surface those frames live in chat **without** the `Monitor event: ...` wrapping that Monitor produces, drive a self-paced display loop via `ScheduleWakeup`:

1. **Pre-flight + kickoff** — exactly as documented above (background `run watch` call).
2. **Immediate first frame** — `tail -n 4` the background task's output file and emit the matching `Timewaver / Mipham / Seal` lines inside a plain ```text``` fence. **No prose around the fence.** No `Monitor event:` header.
3. **Schedule next iteration** — call `ScheduleWakeup` with `delaySeconds=60`, `reason="next /tw watch frame"`, and a `prompt` that re-executes steps 2–3. The prompt must be self-contained (path to `.output`, end conditions, abort words).
4. **End condition** — if the new frame contains `OK: iterations=` (engine completed) OR the background task notification status flips to `completed` / `failed`, emit the final summary line and **do not** schedule another wakeup. The loop dies naturally.
5. **User abort** — if any message since the previous wakeup contains "stop", "elég", "állj", "leállít", emit one brief acknowledgment line and **do not** schedule another wakeup. The engine itself keeps running until its budget; only the display loop ends.

**Do NOT use the `Monitor` tool for this.** Its `<task-notification>` / `Monitor event: "..."` wrapping is harness-controlled and cannot be suppressed; the user has explicitly rejected it as visual noise. `ScheduleWakeup` iterations are plain model turns whose chat output is fully under the assistant's control.

**Polling cadence is 60 s** (the `ScheduleWakeup` floor). The engine emits every 10 s, so each frame in chat skips ~5 intermediate frames — visually still shows clear movement (Mipham ~115 k iter/min, Seal ~5.5 M iter/min at default config).

### Weighted round-robin (run-to-100% mode)

The engine supports per-block `weight` in `config.json` (default 1). Each cycle, a job with `weight=N` runs `N` chunks before the loop advances to the next job. The TS scheduler's bar-split formula honours this:

```
mipham% per second = (W_m / (W_m + W_s × N_seal))   × throughput / mipham_cap
seal%   per second = (W_s × N_seal / (...))         × throughput / seal_total_cap
```

To make the Mipham and Seal **bars fill at exactly the same % rate** despite the 10 B vs 48 B cap asymmetry, set `weight: 10` on Mipham and `weight: 1` on Seal, then set `duration_seconds: 0`. The engine refuses unlimited runs unless every block has a cap — both blocks have caps, so this is allowed. At ~1.9 M iter/s aggregate throughput on this machine, a full 10 B Mipham + 48 B Seal cycle completes in ~8.5 hours.

---

The scheduler spawns the binary with `backend/data/rng_timewaver/config.json`. The binary then:

- Loads `mipham_block.txt` + `seal_block.txt` payloads.
- Honors `duration_seconds` (default 3600 = 1 hour) and `min_free_ram_mb` (default 4096) from config.
- Round-robins across all payloads in 50,000-iter chunks.
- Writes one-line JSON stats to stdout on completion: `{"iterations":N,"bytes_written":B,"payloads":P,"throttle_ms":T,"duration_ms":D}`.
- Per-day log: `backend/logs/rng_timewaver/<YYYY-MM-DD>.log` (gitignored).

In default mode **do not wait synchronously** — the budget is up to 1 hour. The user keeps working; the engine self-throttles below the RAM floor so it never starves foreground tasks. Watch mode is intentionally foreground.

**Per-bar math (so you can explain it if asked):** the engine round-robins one Mipham job against N Seal jobs (one per non-blank, non-`#` line in `seal_block.txt`). The scheduler reads that count at startup and splits the engine's single `iter=N` counter as `mipham = N/(1+N_seal)`, `seal = N·N_seal/(1+N_seal)`. With ~48 seal lines, Seal accumulates iterations ~48× faster than Mipham, and its bar fills ~10× faster relative to cap (Mipham cap = 10 B, Seal cap = 48 B aggregate).

## After kick-off — what to report

- Background task ID returned by the harness.
- Expected wall-clock budget (3600 s default).
- Free-RAM throttle threshold (4096 MB default).
- "Engine runs independently; no polling. Logs at `backend/logs/rng_timewaver/<today>.log`."

## Safety guards (abort with a clear message)

| Condition | Action |
|-----------|--------|
| `cpp/rng_timewaver/bin/rng_timewaver.exe` missing | Point at the build command in `SYSTEM_STRATEGIES/todo/PA_RNG_TIMEWAVER.private.md` (build via MSVC `cl.exe`, copy from `D:/Projects/ai_ea/cpp_engine/bin/`). |
| `backend/data/rng_timewaver/config.json` missing | Tell user Phase 1 staging is incomplete — config + payloads need to be placed before the ritual can run. |
| `mipham_block.txt` or `seal_block.txt` missing in the gitignored data dir | Same: staging incomplete. |
| Config still references old `privateassociation/` (singular) directory path | The directory was renamed `privateassociation/` → `privateassociations/` on 2026-05-16; offer to fix with a `replace_all` in the config (`privateassociation/backend` → `privateassociations/backend`). |
| A previous background timewaver task is still running | Report its task ID and do **not** start a second instance. |

## Cross-reference

- Memory: `feedback_timewaver_keyword.md` — the inline `timewaver` keyword path (same engine, different trigger; `/tw` is the explicit skill path).
- Spec: `SYSTEM_STRATEGIES/todo/PA_RNG_TIMEWAVER.private.md` — full engine + scheduler design (Phase 1 IMPLEMENTED 2026-05-14).
