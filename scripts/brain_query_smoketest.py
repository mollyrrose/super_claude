"""Smoketest for brain_query.py.

Uses temp fixture files so tests are hermetic -- no dependency on real ~/.claude/ data.
Covers the qRev Pass-1 findings: malformed-JSONL handling, the --misses 90%-null
guard (both branches), stale-marker detection, gate warnings, flag error paths,
and MEMORY_DIR-missing degradation.
Kill switch: delete this file. Run: python brain_query_smoketest.py
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile


def _make_fixture_env(tmp: pathlib.Path) -> dict[str, dict[str, str]]:
    """Write fixture files and return named env variants pointing at them."""
    router = tmp / "router.jsonl"
    router_paired = tmp / "router_paired.jsonl"
    decisions = tmp / "decisions.jsonl"
    decisions20 = tmp / "decisions20.jsonl"
    mem = tmp / "memory"
    mem.mkdir()

    # Base router stream: 1 valid row with a NULL invoked field (the forward
    # log's real shape) + 1 malformed line to exercise the bad-JSON counter.
    router.write_text(
        json.dumps({
            "ts": "2026-07-07T10:00:00+00:00",
            "suggested_skill_or_null": "/think",
            "suggested_model_or_null": "sonnet",
            "invoked_skill_or_null": None,
            "project": "super_claude",
        }) + "\n"
        + "{this is not valid json%%%\n",
        encoding="utf-8",
    )
    # Fully-paired router stream: 1 match + 1 miss -> guard must stay silent.
    router_paired.write_text(
        json.dumps({
            "ts": "2026-07-07T10:00:00+00:00",
            "suggested_skill_or_null": "/think",
            "invoked_skill_or_null": "/think",
            "project": "super_claude",
        }) + "\n" + json.dumps({
            "ts": "2026-07-07T11:00:00+00:00",
            "suggested_skill_or_null": "/think",
            "invoked_skill_or_null": "/rev",
            "project": "super_claude",
        }) + "\n",
        encoding="utf-8",
    )
    decisions.write_text(
        json.dumps({
            "ts": "2026-07-07T10:00:00+00:00",
            "title": "Use brain_query for learning stream access",
            "why": "Deterministic, no-LLM, read-only",
            "outcome": "open",
            "project": "super_claude",
        }) + "\n",
        encoding="utf-8",
    )
    # 20 rows = exactly at GATE -> the partial-data warning must NOT fire.
    decisions20.write_text(
        "".join(
            json.dumps({
                "ts": f"2026-07-{(i % 28) + 1:02d}T10:00:00+00:00",
                "title": f"Decision {i}",
                "outcome": "open",
                "project": "super_claude",
            }) + "\n"
            for i in range(20)
        ),
        encoding="utf-8",
    )
    (mem / "fable5_legacy_index.md").write_text(
        "---\nname: fable5-legacy\n---\nFable 5 orchestration notes.\n",
        encoding="utf-8",
    )
    (mem / "MEMORY.md").write_text(
        "- [fable5_legacy_index](fable5_legacy_index.md) -- fable routing\n",
        encoding="utf-8",
    )
    # Staleness markers: exercises cmd_stale's DETECTION branch, not just the
    # nothing-found fallback message.
    (mem / "marker_notes.md").write_text(
        "<!-- last-updated: 2026-01-01 -->\n<!-- stale -->\nOld notes body.\n",
        encoding="utf-8",
    )

    base = {
        **os.environ,
        "BRAIN_QUERY_ROUTER_FILE": str(router),
        "BRAIN_QUERY_DECISIONS_FILE": str(decisions),
        "BRAIN_QUERY_VERDICTS_FILE": str(tmp / "verdicts_missing.jsonl"),
        "BRAIN_QUERY_MEMORY_DIR": str(mem),
    }
    return {
        "base": base,
        "paired": {**base, "BRAIN_QUERY_ROUTER_FILE": str(router_paired)},
        "gate20": {**base, "BRAIN_QUERY_DECISIONS_FILE": str(decisions20)},
        "nomem": {**base, "BRAIN_QUERY_MEMORY_DIR": str(tmp / "no_such_dir")},
    }


def run(args: list[str], env: dict[str, str]) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, "brain_query.py"] + args,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    return r.returncode, r.stdout + r.stderr


def test(label: str, args: list[str], must_contain: str, env: dict[str, str],
         must_not_contain: str | None = None) -> bool:
    code, out = run(args, env)
    ok = code == 0 and must_contain.lower() in out.lower()
    if ok and must_not_contain is not None:
        ok = must_not_contain.lower() not in out.lower()
    status = "pass" if ok else "FAIL"
    print(f"  [{status}] {label}")
    if not ok:
        print(f"         exit={code}")
        print(f"         out={out[:300]}")
    return ok


def main() -> None:
    os.chdir(pathlib.Path(__file__).parent)

    with tempfile.TemporaryDirectory() as tmp_str:
        envs = _make_fixture_env(pathlib.Path(tmp_str))
        base, paired, gate20, nomem = (
            envs["base"], envs["paired"], envs["gate20"], envs["nomem"]
        )

        print("brain_query_smoketest")
        results = [
            test("health", ["health"], "brain_query health", base),
            test("router summary", ["router"], "Router eval rows", base),
            test("router malformed-line warn", ["router"],
                 "malformed line(s) skipped", base),
            test("router --misses all-null guard fires, no fall-through",
                 ["router", "--misses"], "unpopulated", base,
                 must_not_contain="Router misses:"),
            test("router --misses paired counts, guard silent",
                 ["router", "--misses"], "Router misses: 1 / 2 paired rows",
                 paired, must_not_contain="unpopulated"),
            test("router --last 0 errors", ["router", "--last", "0"],
                 "--last must be >= 1", base),
            test("decisions", ["decisions"], "Decisions:", base),
            test("decisions gate warn below GATE", ["decisions"],
                 "partial data", base),
            test("decisions gate silent at GATE", ["decisions"],
                 "Decisions: 20 matching", gate20,
                 must_not_contain="partial data"),
            test("decisions --open --reversed conflict warn",
                 ["decisions", "--open", "--reversed"],
                 "mutually exclusive", base),
            test("decisions --since invalid date errors",
                 ["decisions", "--since", "not-a-date"],
                 "--since must be YYYY-MM-DD", base),
            test("decisions --project case-insensitive",
                 ["decisions", "--project", "SUPER_CLAUDE"],
                 "Decisions: 1 matching", base),
            test("verdicts missing ok", ["verdicts"], "stream", base),
            test("facts fable", ["facts", "fable"], "file(s)", base),
            test("facts memory dir missing degrades", ["facts", "fable"],
                 "memory dir not found", nomem),
            test("stale detects last-updated marker", ["stale"],
                 "last-updated: 2026-01-01", base),
            test("stale detects stale marker", ["stale"],
                 "stale marker present", base),
            test("stale memory dir missing degrades", ["stale"],
                 "memory dir not found", nomem),
        ]

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
