#!/usr/bin/env python3
"""Robust semgrep runner with retry-on-error loop.

Reusable helper for the /qRev and /rev skills' Phase A. Replaces ad-hoc
inline retry logic that has appeared (and broken) in multiple project
sessions. The contract is:

    python run_semgrep_loop.py [--config <yml>...] [--repo-root <dir>]
                               [--max-retries N] [--max-batch N]
                               [--scope-file <path>] [paths...]

Reads scope from --scope-file (one path per line) AND/OR positional args.
De-dupes, drops paths that don't exist in the working tree (handles the
git diff "AM vs D" case: files that exist on HEAD but are deleted in WT
make semgrep error out), runs semgrep in batches if scope is large, and
retries on errors by dropping the offending file (best-effort isolation
via parsing semgrep stderr).

Why this script exists:
- Semgrep returns non-zero exit codes on ANY error but still emits a
  valid JSON document to stdout. Naive `subprocess.run(check=True)`
  loses every finding the moment one file fails. We catch CalledProcessError
  AND parse stdout regardless.
- On a large scope (>100 files), `semgrep <args> path1 path2 ... pathN`
  can overflow argv on Windows. We batch in groups of <max_batch> files.
- When semgrep crashes on a SINGLE problem file, we isolate it (binary
  search if needed) so the rest of the scope still gets scanned. Max
  <max_retries> rounds before giving up.

Output: a single JSON document on stdout with the SAME schema semgrep
itself emits (results array + errors array), aggregated across batches
and retries. Findings are de-duped on (path, check_id, start.line).

Exit codes:
    0 — ran to completion (results may or may not contain findings)
    1 — usage error / scope-file unreadable
    2 — semgrep binary not found on PATH
    3 — all retries exhausted without a single successful batch
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

DEFAULT_BATCH_SIZE = 60   # conservative for Windows argv limits
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_SEC = 180


def _read_scope_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        sys.stderr.write(f"run_semgrep_loop: cannot read scope file {path}: {e}\n")
        sys.exit(1)
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def _normalize_paths(raw: Iterable[str], repo_root: Path) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for entry in raw:
        # Strip surrounding quotes if any (Windows path with spaces).
        clean = entry.strip().strip('"').strip("'")
        if not clean:
            continue
        # Normalise to absolute path so semgrep's relative-path
        # interpretation does not change with the cwd we spawn from.
        p = (repo_root / clean).resolve() if not Path(clean).is_absolute() else Path(clean)
        if not p.exists():
            # File was deleted from WT but still in HEAD — silently drop.
            # Caller likely produced the list via `git diff --name-only`
            # without `--diff-filter=AM`.
            continue
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _run_one_batch(
    config_args: list[str],
    paths: list[str],
    timeout_sec: int,
    repo_root: Path,
) -> tuple[dict, str | None]:
    """Run semgrep on one batch. Returns (parsed_json, error_path_hint).

    error_path_hint is the path semgrep complained about (if extractable
    from stderr) when it crashed in a way that left no JSON. The caller
    uses it to drop the file and retry.
    """
    cmd = ["semgrep"]
    for cfg in config_args:
        cmd.extend(["--config", cfg])
    cmd.extend([
        "--json",
        "--timeout", str(timeout_sec // max(1, len(paths))),
        "--no-rewrite-rule-ids",
        "--quiet",
        "--error",
    ])
    cmd.extend(paths)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=str(repo_root),
        )
    except subprocess.TimeoutExpired:
        return ({"results": [], "errors": [{"type": "timeout", "paths": paths}]}, None)
    except FileNotFoundError:
        sys.stderr.write("run_semgrep_loop: 'semgrep' not found on PATH\n")
        sys.exit(2)

    # Try to parse stdout regardless of exit code. Semgrep writes a valid
    # JSON document even on non-zero exit in most error cases.
    parsed: dict = {}
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError:
            parsed = {}

    if parsed and isinstance(parsed.get("results"), list):
        # Successful parse — return whatever semgrep gave us.
        return (parsed, None)

    # No JSON. Try to extract the offending path from stderr to drop it.
    hint = None
    if proc.stderr:
        for line in proc.stderr.splitlines():
            for p in paths:
                if p in line:
                    hint = p
                    break
            if hint:
                break

    return (
        {"results": [], "errors": [{"type": "no-json", "stderr_tail": proc.stderr[-2000:]}]},
        hint,
    )


def _dedupe_findings(findings: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for f in findings:
        key = (
            f.get("path", ""),
            f.get("check_id", ""),
            (f.get("start") or {}).get("line", 0),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def run(
    paths: list[str],
    config_args: list[str],
    repo_root: Path,
    max_retries: int,
    max_batch: int,
    timeout_sec: int,
) -> dict:
    if not paths:
        return {"results": [], "errors": [], "scanned": 0, "skipped": []}

    all_results: list[dict] = []
    all_errors: list[dict] = []
    skipped: list[str] = []
    successful_batches = 0

    # Process in batches of max_batch.
    queue: list[list[str]] = [paths[i:i + max_batch] for i in range(0, len(paths), max_batch)]

    for batch in queue:
        attempt = 0
        current = list(batch)
        while attempt < max_retries and current:
            attempt += 1
            parsed, hint = _run_one_batch(config_args, current, timeout_sec, repo_root)

            results = parsed.get("results") or []
            errors = parsed.get("errors") or []

            # We accept the batch if semgrep returned results OR an errors
            # array with structured semgrep errors (not the "no-json" sentinel).
            structured_errors = any(
                isinstance(e, dict) and e.get("type") not in ("no-json", "timeout")
                for e in errors
            )

            if results or structured_errors:
                all_results.extend(results)
                all_errors.extend(errors)
                successful_batches += 1
                break  # batch done

            # No-JSON path: try to drop the offending file and retry.
            if hint and hint in current:
                current = [p for p in current if p != hint]
                skipped.append(hint)
                all_errors.append({
                    "type": "skipped-after-crash",
                    "path": hint,
                    "attempt": attempt,
                })
                continue

            # No hint and no JSON — binary-search style fallback: split
            # the batch in half and re-queue both halves.
            if len(current) > 1:
                mid = len(current) // 2
                queue.append(current[mid:])
                current = current[:mid]
                continue

            # Single file, no hint, no JSON — give up on it.
            skipped.append(current[0])
            all_errors.append({
                "type": "give-up-after-retries",
                "path": current[0],
                "attempts": attempt,
            })
            break

    if successful_batches == 0 and not skipped:
        # Nothing worked AND no file was identified as the culprit.
        sys.stderr.write(
            "run_semgrep_loop: no batch produced parsable output across all retries\n"
        )
        sys.exit(3)

    return {
        "results": _dedupe_findings(all_results),
        "errors": all_errors,
        "scanned": len(paths) - len(skipped),
        "skipped": skipped,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Robust semgrep loop runner")
    ap.add_argument("--config", action="append", default=[],
                    help="Semgrep --config value (repeatable)")
    ap.add_argument("--repo-root", default=".",
                    help="Repo root (cwd for semgrep). Default: cwd")
    ap.add_argument("--scope-file", default=None,
                    help="Optional file with one path per line")
    ap.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    ap.add_argument("--max-batch", type=int, default=DEFAULT_BATCH_SIZE)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SEC,
                    help="Per-batch timeout in seconds")
    ap.add_argument("paths", nargs="*", help="Additional explicit paths")
    args = ap.parse_args()

    if shutil.which("semgrep") is None:
        sys.stderr.write("run_semgrep_loop: 'semgrep' not on PATH\n")
        sys.exit(2)

    repo_root = Path(args.repo_root).resolve()

    raw_paths: list[str] = []
    if args.scope_file:
        raw_paths.extend(_read_scope_file(Path(args.scope_file)))
    raw_paths.extend(args.paths)

    if not args.config:
        # Default to "auto" if caller didn't specify any config.
        args.config = ["auto"]

    paths = _normalize_paths(raw_paths, repo_root)
    summary = run(
        paths=paths,
        config_args=args.config,
        repo_root=repo_root,
        max_retries=args.max_retries,
        max_batch=args.max_batch,
        timeout_sec=args.timeout,
    )

    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
