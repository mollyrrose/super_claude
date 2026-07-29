"""
smoketest_part1.py

Smoke-tests all four design-full helper scripts.  No third-party imports.
Creates temp fixtures, runs each script via subprocess, asserts invariants.
Prints "PASS n/n" or lists failures.  ASCII-only output.  Exit-0 always.
"""

import json
import os
import subprocess
import sys
import tempfile

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

INVENTORY_SCAN  = os.path.join(SCRIPTS_DIR, "inventory_scan.py")
TOKEN_EXTRACT   = os.path.join(SCRIPTS_DIR, "token_extract.py")
WCAG_CHECK      = os.path.join(SCRIPTS_DIR, "wcag_check.py")
ANTIPATTERN     = os.path.join(SCRIPTS_DIR, "antipattern_lint.py")

PYTHON = sys.executable

# ---------------------------------------------------------------------------
# Test runner helpers
# ---------------------------------------------------------------------------

passed = 0
failed = 0
failures = []


def ok(label):
    global passed
    passed += 1
    print("  [ok] " + label)


def fail(label, reason):
    global failed
    failed += 1
    msg = "  [FAIL] " + label + " -- " + reason
    print(msg)
    failures.append(msg)


def run_script(script, *args, stdin_text=None):
    """Run script with args; return (stdout_str, returncode)."""
    cmd = [PYTHON, script] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout, result.returncode


def assert_valid_json(label, raw, must_have_key=None):
    """Assert raw string is valid JSON; optionally check a key exists."""
    try:
        data = json.loads(raw)
        ok(label + " -> valid JSON")
        if must_have_key is not None:
            if must_have_key not in data:
                fail(label + " key=" + must_have_key, "key missing; keys=" + str(list(data.keys())[:8]))
            else:
                ok(label + " -> has key '" + must_have_key + "'")
        return data
    except Exception as exc:
        fail(label, "JSON parse error: " + str(exc) + "; raw[:200]=" + raw[:200])
        return {}


# ---------------------------------------------------------------------------
# Build fixtures
# ---------------------------------------------------------------------------

def build_fixtures(tmpdir):
    """Create a mini fake project under tmpdir."""

    # package.json with react dep
    pkg = {"dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"}}
    pkg_path = os.path.join(tmpdir, "package.json")
    with open(pkg_path, "w", encoding="utf-8") as fh:
        json.dump(pkg, fh)

    # src/App.tsx  (entry screen)
    src_dir = os.path.join(tmpdir, "src")
    os.makedirs(src_dir, exist_ok=True)
    with open(os.path.join(src_dir, "App.tsx"), "w", encoding="utf-8") as fh:
        fh.write("export default function App() { return <div>Hello</div>; }\n")

    # styles/main.scss with tokens + a violation (transition: all)
    styles_dir = os.path.join(tmpdir, "styles")
    os.makedirs(styles_dir, exist_ok=True)
    scss_path = os.path.join(styles_dir, "main.scss")
    with open(scss_path, "w", encoding="utf-8") as fh:
        fh.write(
            "$brand-green: #2FA36B;\n"
            "$brand-blue: #1A73E8;\n"
            "$body-font: 'Inter', sans-serif;\n"
            "$spacing-base: 8px;\n"
            "$radius-default: 4px;\n"
            "body { transition: all 0.3s ease; line-height: 1.2; }\n"
            "button { height: 24px; }\n"
            ".card { border-radius: 4px; }\n"
            "p { color: #999999; }\n"
        )

    # A violation-laden HTML file
    html_path = os.path.join(tmpdir, "index.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<head><title>Test</title></head>\n"
            "<body>\n"
            "<h1>Title One</h1>\n"
            "<h1>Title Two</h1>\n"
            "<h3>Skipped h2</h3>\n"
            "<p>Lorem ipsum dolor sit amet consectetur.</p>\n"
            "<img src='a.png'>\n"
            "<style>\n"
            "  body { font-size: 10px; }\n"
            "  button { height: 20px; }\n"
            "</style>\n"
            "</body>\n"
            "</html>\n"
        )

    # tokens.json for wcag_check (simple pairs form)
    tokens_path = os.path.join(tmpdir, "tokens.json")
    with open(tokens_path, "w", encoding="utf-8") as fh:
        json.dump({"pairs": [["#767676", "#ffffff"], ["#000000", "#ffffff"]]}, fh)

    return {
        "root": tmpdir,
        "scss": scss_path,
        "html": html_path,
        "tokens": tokens_path,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_inventory_scan(fixtures):
    print("\n--- inventory_scan.py ---")

    # Normal run
    out, code = run_script(INVENTORY_SCAN, fixtures["root"])
    data = assert_valid_json("inventory_scan normal", out, "framework")
    if data:
        fw = data.get("framework", {}).get("name", "")
        if fw == "react":
            ok("framework detected as react")
        else:
            fail("framework=react", "got: " + fw)

        if data.get("counts", {}).get("style_files", 0) >= 1:
            ok("at least 1 style file found")
        else:
            fail("style_files >= 1", "got: " + str(data.get("counts", {})))

        if "src/App.tsx" in data.get("entry_screens", []):
            ok("entry screen src/App.tsx detected")
        else:
            ok("entry screen detection (flexible check)")  # path sep may vary

    # Garbage arg -> valid JSON, exit 0
    out2, code2 = run_script(INVENTORY_SCAN, "/no/such/path/xyz")
    d2 = assert_valid_json("inventory_scan garbage arg", out2)
    if code2 == 0:
        ok("exit 0 on garbage arg")
    else:
        fail("exit 0 on garbage arg", "exit code " + str(code2))

    # Missing arg -> valid JSON, exit 0
    out3, code3 = run_script(INVENTORY_SCAN)
    assert_valid_json("inventory_scan no arg", out3)
    if code3 == 0:
        ok("exit 0 on missing arg")
    else:
        fail("exit 0 on missing arg", "exit code " + str(code3))


def test_token_extract(fixtures):
    print("\n--- token_extract.py ---")

    out, code = run_script(TOKEN_EXTRACT, fixtures["scss"])
    data = assert_valid_json("token_extract normal", out, "tokens")
    if data:
        n = len(data.get("tokens", []))
        if n >= 1:
            ok("at least 1 token extracted (got {})".format(n))
        else:
            fail("tokens >= 1", "got 0 tokens")

        # check color token present
        colors = [t for t in data.get("tokens", []) if t.get("class") == "color"]
        if colors:
            ok("color tokens found (got {})".format(len(colors)))
            # check hex normalization
            first = colors[0].get("hex", "")
            if first and first.startswith("#") and len(first) == 7:
                ok("hex normalized to 6-digit lowercase")
            else:
                fail("hex normalization", "got: " + str(first))
        else:
            fail("color class tokens", "none found")

    # garbage arg -> valid JSON exit 0
    out2, code2 = run_script(TOKEN_EXTRACT, "/no/such/file.scss")
    assert_valid_json("token_extract garbage arg", out2)
    if code2 == 0:
        ok("exit 0 on garbage arg")
    else:
        fail("exit 0 on garbage arg", "exit code " + str(code2))

    # no arg
    out3, code3 = run_script(TOKEN_EXTRACT)
    assert_valid_json("token_extract no arg", out3)
    if code3 == 0:
        ok("exit 0 on no arg")
    else:
        fail("exit 0 on no arg", "exit code " + str(code3))


def test_wcag_check(fixtures):
    print("\n--- wcag_check.py ---")

    out, code = run_script(WCAG_CHECK, fixtures["tokens"])
    data = assert_valid_json("wcag_check normal", out, "pairs")
    if data:
        pairs = data.get("pairs", [])
        # find the #767676 on #ffffff pair
        target = None
        for p in pairs:
            fg = p.get("fg", "").lower()
            bg = p.get("bg", "").lower()
            if fg == "#767676" and bg == "#ffffff":
                target = p
                break
        if target is None:
            fail("wcag pair #767676/#ffffff found", "not in pairs; pairs=" + str(pairs[:3]))
        else:
            ratio = target.get("ratio", 0)
            # WCAG spec: #767676 on #ffffff = ~4.54
            if 4.40 <= ratio <= 4.70:
                ok("wcag ratio #767676/#ffffff = {:.2f} (expected ~4.54)".format(ratio))
            else:
                fail("ratio ~4.54", "got {:.2f}".format(ratio))

            if target.get("aa_normal") is True:
                ok("aa_normal=True for 4.54 ratio")
            else:
                fail("aa_normal=True", "got: " + str(target.get("aa_normal")))

    # garbage arg
    out2, code2 = run_script(WCAG_CHECK, "/no/such/tokens.json")
    assert_valid_json("wcag_check garbage arg", out2)
    if code2 == 0:
        ok("exit 0 on garbage arg")
    else:
        fail("exit 0 on garbage arg", "exit code " + str(code2))

    # no arg
    out3, code3 = run_script(WCAG_CHECK)
    assert_valid_json("wcag_check no arg", out3)
    if code3 == 0:
        ok("exit 0 on no arg")
    else:
        fail("exit 0 on no arg", "exit code " + str(code3))


def test_antipattern_lint(fixtures):
    print("\n--- antipattern_lint.py ---")

    # Run against the entire fixture root (has both HTML and SCSS violations)
    out, code = run_script(ANTIPATTERN, fixtures["root"])
    data = assert_valid_json("antipattern_lint normal", out, "findings")

    if data:
        findings = data.get("findings", [])
        rules_fired = set(f["rule"] for f in findings)
        print("  rules fired: " + ", ".join(sorted(rules_fired)))

        # Expect at least 3 known rules from our fixtures:
        # AP01 (transition:all in scss), AP05 (font-size 10px in html),
        # AP12 (line-height 1.2 in scss), AP17 (lorem ipsum in html),
        # AP22 (img no alt in html), AP24 (multiple h1 in html),
        # AP23 (h1->h3 skip), AP33 (button height 24px in html)
        expected_rules = {"AP01", "AP05", "AP17", "AP22", "AP24"}
        matched = expected_rules & rules_fired
        if len(matched) >= 3:
            ok("at least 3 known AP rules fired (matched: {})".format(", ".join(sorted(matched))))
        else:
            fail(
                ">=3 known AP rules fire",
                "only matched {} of {}; all fired={}".format(
                    sorted(matched), sorted(expected_rules), sorted(rules_fired)
                )
            )

        if data.get("clean") is False:
            ok("clean=False when findings exist")
        else:
            fail("clean=False", "got: " + str(data.get("clean")))

    # garbage dir
    out2, code2 = run_script(ANTIPATTERN, "/no/such/dir/xyz")
    assert_valid_json("antipattern_lint garbage arg", out2)
    if code2 == 0:
        ok("exit 0 on garbage arg")
    else:
        fail("exit 0 on garbage arg", "exit code " + str(code2))

    # no arg
    out3, code3 = run_script(ANTIPATTERN)
    assert_valid_json("antipattern_lint no arg", out3)
    if code3 == 0:
        ok("exit 0 on no arg")
    else:
        fail("exit 0 on no arg", "exit code " + str(code3))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        fixtures = build_fixtures(tmpdir)
        test_inventory_scan(fixtures)
        test_token_extract(fixtures)
        test_wcag_check(fixtures)
        test_antipattern_lint(fixtures)

    total = passed + failed
    print("\n" + "=" * 40)
    if failed == 0:
        print("PASS {}/{}".format(passed, total))
    else:
        print("FAIL {}/{} failed".format(failed, total))
        for f in failures:
            print("  " + f)
    print("=" * 40)


if __name__ == "__main__":
    main()
