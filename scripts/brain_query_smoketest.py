"""Smoketest for brain_query.py.

Uses temp fixture files so tests are hermetic -- no dependency on real ~/.claude/ data.
Kill switch: delete this file. Run: python brain_query_smoketest.py
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile


def _make_fixture_env(tmp: pathlib.Path) -> dict[str, str]:
    """Write minimal fixture files and return env overrides pointing at them."""
    router = tmp / "router.jsonl"
    decisions = tmp / "decisions.jsonl"
    mem = tmp / "memory"
    mem.mkdir()

    router.write_text(
        json.dumps({
            "ts": "2026-07-07T10:00:00+00:00",
            "suggested_skill_or_null": "/think",
            "suggested_model_or_null": "sonnet",
            "invoked_skill_or_null": None,
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
    (mem / "fable5_legacy_index.md").write_text(
        "---\nname: fable5-legacy\n---\nFable 5 orchestration notes.\n",
        encoding="utf-8",
    )
    (mem / "MEMORY.md").write_text(
        "- [fable5_legacy_index](fable5_legacy_index.md) -- fable routing\n",
        encoding="utf-8",
    )

    return {
        **os.environ,
        "BRAIN_QUERY_ROUTER_FILE": str(router),
        "BRAIN_QUERY_DECISIONS_FILE": str(decisions),
        "BRAIN_QUERY_VERDICTS_FILE": str(tmp / "verdicts_missing.jsonl"),
        "BRAIN_QUERY_MEMORY_DIR": str(mem),
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


def test(label: str, args: list[str], must_contain: str, env: dict[str, str]) -> bool:
    code, out = run(args, env)
    ok = code == 0 and must_contain.lower() in out.lower()
    status = "pass" if ok else "FAIL"
    print(f"  [{status}] {label}")
    if not ok:
        print(f"         exit={code}")
        print(f"         out={out[:300]}")
    return ok


def main() -> None:
    os.chdir(pathlib.Path(__file__).parent)

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = pathlib.Path(tmp_str)
        env = _make_fixture_env(tmp)

        print("brain_query_smoketest")
        results = [
            test("health", ["health"], "brain_query health", env),
            test("router summary", ["router"], "Router eval rows", env),
            test("router --misses", ["router", "--misses"], "Router misses", env),
            test("decisions", ["decisions"], "Decisions:", env),
            test("verdicts missing ok", ["verdicts"], "stream", env),
            test("facts fable", ["facts", "fable"], "file(s)", env),
            test("stale", ["stale"], "stale", env),
        ]

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
