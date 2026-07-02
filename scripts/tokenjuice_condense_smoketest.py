#!/usr/bin/env python3
"""Smoketest for tokenjuice_condense.py. Run: python tokenjuice_condense_smoketest.py
Exit 0 = all pass. ASCII-only output (cp1252-safe)."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tokenjuice_condense as tc  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print("[ok]   %s" % name)
    else:
        print("[fail] %s %s" % (name, detail))
        FAILURES.append(name)


def main():
    # 1. short content is returned unchanged
    short = "hello world"
    out, meta = tc.condense(short)
    check("short-unchanged", out == short and meta["skipped"] == "too short")

    # 2. JSON: keys survive, long values squeeze, valid-ish schema visible
    big_json = json.dumps({
        "users": [
            {"id": i, "name": "user%d" % i,
             "bio": ("this is a very long biography text that repeats itself "
                     * 20)}
            for i in range(8)
        ],
        "token": "sk-Ab3dEf9hIjK2mNoPqRsTuVwXyZ01234567890abcdef",
        "active": True,
    }, indent=2)
    out, meta = tc.condense(big_json)
    check("json-detected", meta["content_type"] == "json", str(meta))
    check("json-smaller", len(out) < len(big_json),
          "%d -> %d" % (len(big_json), len(out)))
    check("json-keys-survive", '"bio"' in out and '"users"' in out and '"id"' in out)
    check("json-bool-survives", "true" in out)
    check("json-secret-survives",
          "sk-Ab3dEf9hIjK2mNoPqRsTuVwXyZ01234567890abcdef" in out)

    # 3. code: signatures + imports survive, bodies squeeze
    code = "import os\nimport sys\n\n"
    code += "\n\n".join(
        "def func_%d(a, b, c):\n    %s\n    return a + b" % (
            i, "\n    ".join('x%d = "filler line %d for body bulk"' % (j, j)
                             for j in range(25)))
        for i in range(6))
    out, meta = tc.condense(code)
    check("code-detected", meta["content_type"] == "code", str(meta))
    check("code-smaller", len(out) < len(code), "%d -> %d" % (len(code), len(out)))
    check("code-imports-survive", "import os" in out and "import sys" in out)
    check("code-signatures-survive",
          all("def func_%d(a, b, c):" % i in out for i in range(6)))

    # 4. log: errors + summary survive, INFO noise drops
    log_lines = []
    for i in range(300):
        log_lines.append("2026-07-02 00:0%d INFO worker heartbeat ok seq=%d" % (i % 10, i))
    log_lines.append("2026-07-02 00:11 ERROR db connection refused host=10.0.0.5")
    log_lines.extend("2026-07-02 00:11 INFO retry %d" % i for i in range(50))
    log_lines.append("2026-07-02 00:12 ERROR db connection refused host=10.0.0.9")
    log_lines.append("=== 2 failed, 348 passed ===")
    log = "\n".join(log_lines)
    out, meta = tc.condense(log)
    check("log-detected", meta["content_type"] == "log", str(meta))
    check("log-much-smaller", len(out.split("\n")) < 130,
          "%d lines" % len(out.split("\n")))
    check("log-errors-survive", "connection refused host=10.0.0.5" in out
          and "connection refused host=10.0.0.9" in out)
    check("log-summary-survives", "=== 2 failed, 348 passed ===" in out)
    check("log-omission-note", "lines omitted" in out)

    # 5. text: big prose squeezes, high-entropy token survives
    secret = "ghp_9aB3cD7eF1gH5iJ8kL2mN6oP0qR4sT9uVwXy"
    prose = ("The quick brown fox jumps over the lazy dog again and again. "
             * 100) + " credential: " + secret + " . " + (
             "More filler prose follows to pad the tail of the blob. " * 50)
    out, meta = tc.condense(prose)
    check("text-detected", meta["content_type"] == "text", str(meta))
    check("text-smaller", len(out) < len(prose))
    check("text-secret-survives", secret in out, "entropy preservation")

    # 6. invalid JSON falls through without crashing
    broken = '{"key": "value", broken' + "x" * 200
    out, meta = tc.condense(broken)
    check("broken-json-no-crash", isinstance(out, str))

    # 7. condense never raises on binary-ish garbage
    garbage = "\x00\x01\x02" * 200
    out, meta = tc.condense(garbage)
    check("garbage-no-crash", isinstance(out, str))

    # 8. tokenjuice integration: condense strategy is registered + works
    import tokenjuice as tj
    check("strategy-registered", "condense" in tj.STRATEGIES)
    out2 = tj.s_condense(big_json, {"content_type": "auto"})
    check("strategy-works", len(out2) < len(big_json))

    # 9. regression: small ratio must NOT inflate a squeezed span (keep_end==0 bug)
    span = "A" * 200
    sq = tc._squeeze(span, ratio=0.04)
    check("squeeze-small-ratio-no-inflate", len(sq) <= len(span),
          "%d -> %d" % (len(span), len(sq)))

    # 10. regression: _code_mask must be near-linear on adversarial newlines (ReDoS)
    import time as _t
    adv = "def f():\n" + ("\n" * 40000)
    _start = _t.time()
    tc._code_mask(adv)
    elapsed = _t.time() - _start
    check("code-mask-not-quadratic", elapsed < 2.0, "%.2fs (must be <2s)" % elapsed)

    # 11. regression: oversized input is skipped, never mask-allocated
    huge = "x " * (tc.CONDENSE_MAX_BYTES // 2 + 1000)
    out, meta = tc.condense(huge)
    check("oversized-skipped", meta["skipped"] == "too large" and out is huge)

    # 12. regression: --condense CLI flag path in tokenjuice.main compresses JSON
    import io as _io, contextlib as _cl, sys as _sys
    old_stdin = _sys.stdin
    try:
        _sys.stdin = _io.StringIO(big_json)
        buf = _io.StringIO()
        with _cl.redirect_stdout(buf):
            tj.main(["--stdin", "--condense", "--quiet"])
        cli_out = buf.getvalue()
    finally:
        _sys.stdin = old_stdin
    check("cli-condense-flag", len(cli_out) < len(big_json) and '"bio"' in cli_out)

    print()
    if FAILURES:
        print("FAILED: %d case(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
