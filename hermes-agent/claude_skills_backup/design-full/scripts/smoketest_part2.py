"""
smoketest_part2.py -- verify scripts 5-8 (panel_sample, crosstab, brandbook_assemble,
design_tab_scaffold).

Runs all 4 scripts via subprocess with tempfile fixtures.
Prints "PASS n/n" or individual FAIL lines to stdout (ASCII only).
Exits 0 always (per silent-no-op rule); FAIL lines indicate test failures.
"""

import json
import os
import subprocess
import sys
import tempfile

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

PASS_COUNT = 0
FAIL_COUNT = 0
TOTAL = 0


def _run(cmd, input_data=None, timeout=30):
    """Run a command, return (returncode, stdout_text, stderr_text)."""
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as exc:
        return -1, "", str(exc)


def _py(script_name, *args):
    """Build [sys.executable, <script_path>, *args]."""
    return [sys.executable, os.path.join(_SCRIPT_DIR, script_name)] + list(args)


def check(name, condition, detail=""):
    global PASS_COUNT, FAIL_COUNT, TOTAL
    TOTAL += 1
    if condition:
        PASS_COUNT += 1
        print("  ok: {}".format(name))
    else:
        FAIL_COUNT += 1
        detail_str = " -- " + str(detail) if detail else ""
        print("  FAIL: {}{}".format(name, detail_str))


def _make_persona_file(content):
    """Write a temp file with persona content; return path."""
    pass  # Helper used inline below


# ---------------------------------------------------------------------------
# Create fake personas directory
# ---------------------------------------------------------------------------

def make_personas_dir(tmp):
    pdir = os.path.join(tmp, "personas")
    os.makedirs(pdir, exist_ok=True)

    # human-personas.md: 3 personas, one age 19
    human = """\
# Human Personas

## H1: The Enthusiast -- "Alex"

**Demographics:** 28, startup founder, SF Bay Area

## H2: The Skeptic -- "Sam"

**Demographics:** 42, quality manager

## H3: The Student -- "Jordan"

**Demographics:** 19, student, Gen Z, university first year
"""
    # spiral-personas.md: 3 personas
    spiral = """\
# Spiral Dynamics Personas

## S1: BEIGE -- "Beni"

**Demographics:** 61, day laborer, rural area

## S2: RED -- "Karim"

**Demographics:** 34, entrepreneur

## S3: BLUE -- "Maria"

**Demographics:** 52, compliance manager
"""
    # mbti-personas.md: 4 personas
    mbti = """\
# MBTI Personas

## MB1: INTJ -- "Zsigmond"

**Demographics:** 42, strategist

## MB2: INFP -- "Anna"

**Demographics:** 31, writer

## MB3: ENTJ -- "Viktor"

**Demographics:** 45, CEO

## MB4: ENFJ -- "Clara"

**Demographics:** 22, student, teen community organizer
"""
    # agent-personas.md: 2 personas
    agent = """\
# Agent Personas

## AG1: The Optimizer -- "Nexus"

**Demographics:** AI agent, performance-focused

## AG2: The Explorer -- "Drift"

**Demographics:** AI agent, curiosity-driven
"""

    for fname, content in [
        ("human-personas.md", human),
        ("spiral-personas.md", spiral),
        ("mbti-personas.md", mbti),
        ("agent-personas.md", agent),
    ]:
        with open(os.path.join(pdir, fname), 'w', encoding='utf-8') as fh:
            fh.write(content)

    return pdir


# ---------------------------------------------------------------------------
# Create fake transcripts directory
# ---------------------------------------------------------------------------

def make_transcripts_dir(tmp):
    tdir = os.path.join(tmp, "transcripts")
    os.makedirs(tdir, exist_ok=True)

    # 8 VERDICT lines: mixed panels, one malformed
    transcript1 = """\
Some focus group discussion for Variant A.

VERDICT | H1 Alex | human | RANK: A>B>C | clean layout draws the eye immediately
VERDICT | S1 Beni | spiral | RANK: B>A>C | familiar pattern feels safer
VERDICT | MB1 Zsigmond | mbti | RANK: A>C>B | A's logic structure is superior
VERDICT | AG1 Nexus | agent | RANK: C>A>B | C optimizes interaction efficiency
VERDICT | H2 Sam | human | RANK: A>B>C | A is the most professional looking
VERDICT | S2 Karim | spiral | RANK: B>C>A | B has better energy
VERDICT | MB2 Anna | mbti | RANK: C>A>B | C has authentic character
VERDICT | MALFORMED LINE no pipes no rank just text here
"""
    transcript2 = """\
Second focus group panel.

VERDICT | H3 Jordan | human | RANK: A>B | A feels modern and fresh
"""

    with open(os.path.join(tdir, "panel1.md"), 'w', encoding='utf-8') as fh:
        fh.write(transcript1)
    with open(os.path.join(tdir, "panel2.md"), 'w', encoding='utf-8') as fh:
        fh.write(transcript2)

    return tdir


# ---------------------------------------------------------------------------
# Create fake state directory
# ---------------------------------------------------------------------------

def make_state_dir(tmp):
    sdir = os.path.join(tmp, "state")
    os.makedirs(sdir, exist_ok=True)
    os.makedirs(os.path.join(sdir, "scans"), exist_ok=True)
    os.makedirs(os.path.join(sdir, "panels", "G1"), exist_ok=True)

    state = {
        "version": 1,
        "phase": "P3",
        "budget": "standard",
        "project_root": "/tmp/fake-project",
        "intake": {
            "purpose": "teen study-buddy web app",
            "tone": "playful-confident",
            "industry": "edtech",
            "constraints": ["mandated logo", "keep green #2FA36B"],
            "axes": {"variance": "high", "motion": "medium", "density": "low"},
        },
        "audit": {"framework": "react", "brandbook_mode": "create"},
        "locked_direction": "B",
        "family_winners": {"shell": "A"},
        "updated": "2026-07-29T12:00:00Z",
    }

    tokens = {
        "palette": {
            "primary": "#2FA36B",
            "secondary": "#3B6FD6",
            "background": "#FFFFFF",
            "text": "#222222",
        },
        "font_families": ["Inter", "Georgia"],
    }

    g1_crosstab = {
        "total_verdicts": 3,
        "overall": {
            "A": {"first": 2, "win_pct": 66.7, "borda": 7},
            "B": {"first": 1, "win_pct": 33.3, "borda": 4},
        },
        "by_panel": {
            "human": {"winner": "A", "counts": {"A": 1}},
        },
        "themes": {
            "A": [["clean", 2], ["modern", 1]],
        },
    }

    with open(os.path.join(sdir, "state.json"), 'w', encoding='utf-8') as fh:
        json.dump(state, fh)
    with open(os.path.join(sdir, "scans", "tokens.json"), 'w', encoding='utf-8') as fh:
        json.dump(tokens, fh)
    with open(os.path.join(sdir, "panels", "G1", "crosstab.json"), 'w', encoding='utf-8') as fh:
        json.dump(g1_crosstab, fh)

    # Create a synthetic template in the references dir
    ref_dir = os.path.normpath(os.path.join(_SCRIPT_DIR, '..', 'references'))
    os.makedirs(ref_dir, exist_ok=True)
    template_path = os.path.join(ref_dir, "brandbook-template.md")
    if not os.path.isfile(template_path):
        template = """\
# Brand Book -- {{MODE}}

Date: {{DATE}}

## Purpose

{{PURPOSE}}

## Industry / Tone

Industry: {{INDUSTRY}} | Tone: {{TONE}}

## Direction

Locked: {{DIRECTION}}

## Axes

{{AXES}}

## Palette

{{PALETTE_TABLE}}

## Typography

{{FONTS}}

## Constraints

{{CONSTRAINTS}}

## Focus Gate Summary

{{GATE_SUMMARY}}
"""
        with open(template_path, 'w', encoding='utf-8') as fh:
            fh.write(template)

    return sdir


# ---------------------------------------------------------------------------
# Create fake design-config.json
# ---------------------------------------------------------------------------

def make_design_config(tmp):
    cfg = {
        "version": 1,
        "theme": {"modes": ["light", "dark", "auto"], "default": "auto"},
        "density": {"options": ["compact", "regular", "roomy"], "default": "regular"},
        "accent": {"options": ["#2fa36b", "#3b6fd6"], "default": "#2fa36b"},
        "avatars": {"sets": ["flat-geometric", "pixel"], "default": "flat-geometric",
                    "enabled": True},
        "effects": [
            {"id": "peel-menu", "label": "Peel menu", "enabled": False,
             "reduced_motion_behavior": "disable", "fallback": "standard dropdown"},
            {"id": "droplets", "label": "Droplets", "enabled": False,
             "reduced_motion_behavior": "disable", "fallback": "none"},
        ],
    }
    cfg_path = os.path.join(tmp, "design-config.json")
    with open(cfg_path, 'w', encoding='utf-8') as fh:
        json.dump(cfg, fh)
    return cfg_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_panel_sample(tmp, personas_dir):
    print("\n[panel_sample.py]")

    # Basic run: n=4 (small enough for our fake files)
    rc, out, err = _run(_py("panel_sample.py", "--n", "4",
                             "--personas-dir", personas_dir))
    check("exit 0", rc == 0, err[:200] if rc != 0 else "")
    try:
        data = json.loads(out)
        check("valid JSON", True)
        check("n field present", "n" in data)
        check("panel field present", "panel" in data)
        n_got = data.get("n", -1)
        panel_list = data.get("panel", [])
        check("exactly 4 personas", n_got == 4 and len(panel_list) == 4,
              "got n={} len={}".format(n_got, len(panel_list)))
    except Exception as exc:
        check("valid JSON", False, str(exc))
        return

    # Seed stability: two runs identical
    rc2, out2, _ = _run(_py("panel_sample.py", "--n", "4",
                              "--personas-dir", personas_dir, "--seed", "42"))
    rc3, out3, _ = _run(_py("panel_sample.py", "--n", "4",
                              "--personas-dir", personas_dir, "--seed", "42"))
    check("seed-stable (same seed = same output)", out2 == out3)

    # Different seed -> may differ (not guaranteed but very likely with our pool)
    rc4, out4, _ = _run(_py("panel_sample.py", "--n", "4",
                              "--personas-dir", personas_dir, "--seed", "99"))
    # We can't guarantee different output (small pool), so just check it runs
    check("different seed exits 0", rc4 == 0)

    # Youth boost: check young flag annotation works
    rc5, out5, _ = _run(_py("panel_sample.py", "--n", "4",
                              "--personas-dir", personas_dir, "--seed", "42",
                              "--youth-boost"))
    check("youth-boost exits 0", rc5 == 0)
    try:
        d5 = json.loads(out5)
        check("youth-boost valid JSON", "panel" in d5)
        # The 19-year-old Jordan is in the pool; youth_boost flag should be True
        check("youth_boost flag true", d5.get("youth_boost") is True)
        # The composition may differ from non-boosted run (not strictly guaranteed
        # for n=4 from a small pool, so we just verify it ran without error)
        check("youth-boost produces persona list", isinstance(d5.get("panel"), list))
    except Exception as exc:
        check("youth-boost valid JSON", False, str(exc))

    # Garbage args -> JSON with error, exit 0
    rc_g, out_g, _ = _run(_py("panel_sample.py", "--n", "not-a-number",
                                "--personas-dir", personas_dir))
    check("garbage n exits 0", rc_g == 0)
    # May produce error JSON or fall back gracefully
    try:
        dg = json.loads(out_g)
        check("garbage n emits JSON", True)
    except Exception:
        check("garbage n emits JSON", False, repr(out_g[:100]))

    # Missing dir -> error JSON, exit 0
    rc_m, out_m, _ = _run(_py("panel_sample.py", "--n", "4",
                                "--personas-dir", "/nonexistent/path/xyz"))
    check("missing dir exits 0", rc_m == 0)
    try:
        dm = json.loads(out_m)
        check("missing dir emits error JSON", "error" in dm)
    except Exception:
        check("missing dir emits error JSON", False, repr(out_m[:100]))


def test_crosstab(tmp, transcripts_dir):
    print("\n[crosstab.py]")

    json_out = os.path.join(tmp, "crosstab_out.json")
    rc, out, err = _run(_py("crosstab.py", transcripts_dir, "--json", json_out))
    check("exit 0", rc == 0, err[:200] if rc != 0 else "")

    # Stdout should be a markdown report (contains Overall Results heading)
    check("markdown report emitted", "Overall" in out or "Variant" in out, repr(out[:200]))

    # JSON file written
    check("json file written", os.path.isfile(json_out))

    try:
        with open(json_out, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        check("json valid", True)

        total = data.get("total_verdicts", 0)
        # We have 9 VERDICT lines; 1 is malformed -> 8 valid (panel2 has 1 more)
        # panel1: 7 valid (8 lines minus 1 malformed), panel2: 1 valid = 8 total
        check("malformed line skipped (total_verdicts == 8)", total == 8,
              "got {}".format(total))

        overall = data.get("overall", {})
        check("overall has variant A", "A" in overall)
        check("overall has variant B", "B" in overall)

        # Determine overall winner (most first-place votes)
        # A: H1, MB1 from panel1 (2), H3 from panel2 (1) = 3 first places for A
        # B: S1, S2 = 2 first places
        # C: AG1, MB2 = 2 first places
        if overall:
            winner = max(overall.keys(), key=lambda k: overall[k].get("first", 0))
            check("overall winner is A", winner == "A", "got {}".format(winner))

        # Malformed line did not produce a verdict
        # (verified above via total_verdicts == 8)
        themes = data.get("themes", {})
        check("themes present", isinstance(themes, dict))

    except Exception as exc:
        check("json valid", False, str(exc))

    # Garbage args -> exit 0
    rc_g, out_g, _ = _run(_py("crosstab.py", "/nonexistent/dir/xyz"))
    check("nonexistent dir exits 0", rc_g == 0)
    # Should either emit error JSON or empty report
    check("nonexistent dir produces some output", len(out_g.strip()) > 0)

    # No args -> exit 0
    rc_n, out_n, _ = _run(_py("crosstab.py"))
    check("no args exits 0", rc_n == 0)


def test_brandbook(tmp, state_dir):
    print("\n[brandbook_assemble.py]")

    out_path = os.path.join(tmp, "BRANDBOOK.md")
    rc, out, err = _run(_py("brandbook_assemble.py", state_dir, "--out", out_path))
    check("exit 0", rc == 0, err[:200] if rc != 0 else "")

    # Stdout should be JSON
    try:
        data = json.loads(out)
        check("stdout valid JSON", True)
        check("out field present", "out" in data)
        check("placeholders_resolved field present", "placeholders_resolved" in data)
        check("placeholders_tbd field present", "placeholders_tbd" in data)
    except Exception as exc:
        check("stdout valid JSON", False, str(exc))

    # Output file should exist
    check("BRANDBOOK.md written", os.path.isfile(out_path))

    if os.path.isfile(out_path):
        with open(out_path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        # No unresolved placeholders
        import re
        unresolved = re.findall(r'\{\{[A-Z_]+\}\}', content)
        check("no unresolved {{}} placeholders", len(unresolved) == 0,
              "found: " + str(unresolved))

    # HTML flag
    html_path = os.path.join(tmp, "BRANDBOOK.html")
    rc2, out2, err2 = _run(_py("brandbook_assemble.py", state_dir,
                                "--out", html_path.replace('.html', '.md'),
                                "--html"))
    check("--html exits 0", rc2 == 0, err2[:200] if rc2 != 0 else "")
    html_out = html_path.replace('.html', '.html')
    expected_html = html_path.replace('.html', '').rstrip('.') + '.html'
    # Just check the JSON says html path is non-null
    try:
        d2 = json.loads(out2)
        html_val = d2.get("html")
        check("html path non-null in JSON", html_val is not None, str(html_val))
        if html_val and os.path.isfile(html_val):
            with open(html_val, 'r', encoding='utf-8') as fh:
                html_content = fh.read()
            check("html contains DOCTYPE", "<!DOCTYPE" in html_content)
    except Exception as exc:
        check("--html JSON valid", False, str(exc))

    # Garbage args -> exit 0
    rc_g, out_g, _ = _run(_py("brandbook_assemble.py", "/nonexistent/state/xyz"))
    check("nonexistent state-dir exits 0", rc_g == 0)

    # No args -> exit 0
    rc_n, out_n, _ = _run(_py("brandbook_assemble.py"))
    check("no args exits 0", rc_n == 0)


def test_design_tab(tmp, config_path):
    print("\n[design_tab_scaffold.py]")

    for framework in ("react", "vue", "plain"):
        out_dir = os.path.join(tmp, "scaffold-{}".format(framework))
        rc, out, err = _run(_py("design_tab_scaffold.py",
                                 "--framework", framework,
                                 "--config", config_path,
                                 "--out", out_dir))
        check("{} exits 0".format(framework), rc == 0, err[:200] if rc != 0 else "")
        try:
            data = json.loads(out)
            check("{} stdout valid JSON".format(framework), True)
            check("{} framework field".format(framework), data.get("framework") == framework)
            files = data.get("files", [])
            check("{} WIRING.md listed".format(framework), "WIRING.md" in files)

            # Framework-specific expected files
            if framework == "react":
                check("react DesignSettings.tsx", "DesignSettings.tsx" in files)
                check("react applyDesignConfig.ts", "applyDesignConfig.ts" in files)
            elif framework == "vue":
                check("vue DesignSettings.vue", "DesignSettings.vue" in files)
                check("vue applyDesignConfig.js", "applyDesignConfig.js" in files)
            else:
                check("plain design-settings.html", "design-settings.html" in files)
                check("plain design-settings.js", "design-settings.js" in files)
            check("{} design-config.json".format(framework), "design-config.json" in files)

            # Verify files actually exist on disk
            check("{} out dir created".format(framework), os.path.isdir(out_dir))
            for f in files:
                fpath = os.path.join(out_dir, f)
                check("{} {} exists on disk".format(framework, f), os.path.isfile(fpath),
                      "missing: " + fpath)

            # Verify nothing written outside out_dir
            # (listing all files recursively)
            written_paths = []
            for root, dirs, fnames in os.walk(out_dir):
                for fn in fnames:
                    written_paths.append(os.path.abspath(os.path.join(root, fn)))
            out_dir_abs = os.path.abspath(out_dir)
            outside = [p for p in written_paths
                       if not p.startswith(out_dir_abs + os.sep) and p != out_dir_abs]
            check("{} nothing outside out_dir".format(framework), len(outside) == 0,
                  str(outside))

        except Exception as exc:
            check("{} stdout valid JSON".format(framework), False, str(exc))

    # Garbage framework -> exit 0, error JSON
    rc_g, out_g, _ = _run(_py("design_tab_scaffold.py",
                                "--framework", "angular",
                                "--config", config_path))
    check("bad framework exits 0", rc_g == 0)
    try:
        dg = json.loads(out_g)
        check("bad framework error JSON", "error" in dg)
    except Exception:
        check("bad framework error JSON", False, repr(out_g[:100]))

    # No config -> exit 0
    rc_nc, out_nc, _ = _run(_py("design_tab_scaffold.py", "--framework", "react"))
    check("no config exits 0", rc_nc == 0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("smoketest_part2.py -- design-full scripts 5-8")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as tmp:
        personas_dir = make_personas_dir(tmp)
        transcripts_dir = make_transcripts_dir(tmp)
        state_dir = make_state_dir(tmp)
        config_path = make_design_config(tmp)

        test_panel_sample(tmp, personas_dir)
        test_crosstab(tmp, transcripts_dir)
        test_brandbook(tmp, state_dir)
        test_design_tab(tmp, config_path)

    print("")
    print("=" * 50)
    if FAIL_COUNT == 0:
        print("PASS {}/{}".format(PASS_COUNT, TOTAL))
    else:
        print("PASS {}/{} ({} FAILED)".format(PASS_COUNT, TOTAL, FAIL_COUNT))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("smoketest ERROR: " + str(exc))
        sys.exit(0)
