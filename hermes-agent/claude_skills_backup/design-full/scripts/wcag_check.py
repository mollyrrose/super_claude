"""
wcag_check.py <tokens.json>

Read token_extract output OR a simple {"pairs": [["#fg", "#bg"], ...]} form.
Compute WCAG 2.1 relative luminance and contrast ratio for each pair.
Also generate pairs from the token file: every color against white #ffffff,
black #111111, and the 2 most-used palette colors as backgrounds.

Stdlib-only, ASCII-safe, exit-0 always.

Output: {"pairs": [...], "failures_aa_normal": N}
"""

import json
import os
import sys
import re

# ---------------------------------------------------------------------------
# Color parsing (inline; no import from token_extract to keep scripts independent)
# ---------------------------------------------------------------------------

HEX3_RE = re.compile(r"^#([0-9a-fA-F]{3})$")
HEX6_RE = re.compile(r"^#([0-9a-fA-F]{6})$")
HEX8_RE = re.compile(r"^#([0-9a-fA-F]{8})$")
RGB_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)")
HSL_RE = re.compile(r"hsla?\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%(?:\s*,\s*([\d.]+))?\s*\)")


def _clamp(v, lo=0, hi=255):
    return max(lo, min(hi, v))


def _hsl_to_rgb(h, s, l):
    s /= 100.0
    l /= 100.0
    c = (1.0 - abs(2 * l - 1)) * s
    x = c * (1.0 - abs((h / 60.0) % 2 - 1))
    m = l - c / 2.0
    if h < 60:
        r1, g1, b1 = c, x, 0.0
    elif h < 120:
        r1, g1, b1 = x, c, 0.0
    elif h < 180:
        r1, g1, b1 = 0.0, c, x
    elif h < 240:
        r1, g1, b1 = 0.0, x, c
    elif h < 300:
        r1, g1, b1 = x, 0.0, c
    else:
        r1, g1, b1 = c, 0.0, x
    return (
        _clamp(int((r1 + m) * 255 + 0.5)),
        _clamp(int((g1 + m) * 255 + 0.5)),
        _clamp(int((b1 + m) * 255 + 0.5)),
    )


def parse_hex(raw):
    """Return (r, g, b) tuple 0-255 from a hex/rgb/hsl string, or None."""
    raw = raw.strip()

    m = HEX3_RE.match(raw)
    if m:
        s = m.group(1)
        return int(s[0]*2, 16), int(s[1]*2, 16), int(s[2]*2, 16)

    m = HEX6_RE.match(raw)
    if m:
        s = m.group(1)
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)

    m = HEX8_RE.match(raw)
    if m:
        s = m.group(1)
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)

    m = RGB_RE.match(raw)
    if m:
        return _clamp(int(m.group(1))), _clamp(int(m.group(2))), _clamp(int(m.group(3)))

    m = HSL_RE.match(raw)
    if m:
        return _hsl_to_rgb(float(m.group(1)), float(m.group(2)), float(m.group(3)))

    return None


# ---------------------------------------------------------------------------
# WCAG 2.1 contrast
# ---------------------------------------------------------------------------

def _linearize(c):
    """sRGB channel 0-1 -> linear."""
    c = c / 255.0
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb):
    r, g, b = rgb
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def contrast_ratio(rgb1, rgb2):
    l1 = relative_luminance(rgb1)
    l2 = relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def check_pair(fg_hex, bg_hex):
    """Return a result dict or None if either color is unparseable."""
    fg_rgb = parse_hex(fg_hex)
    bg_rgb = parse_hex(bg_hex)
    if fg_rgb is None or bg_rgb is None:
        return None

    ratio = contrast_ratio(fg_rgb, bg_rgb)
    ratio_r = round(ratio, 2)

    return {
        "fg": fg_hex.lower(),
        "bg": bg_hex.lower(),
        "ratio": ratio_r,
        "aa_normal": ratio >= 4.5,
        "aa_large": ratio >= 3.0,
        "aaa_normal": ratio >= 7.0,
    }


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

STANDARD_BACKGROUNDS = ["#ffffff", "#111111"]


def run(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
    except Exception as exc:
        return {"error": "cannot read " + str(path) + ": " + str(exc)}

    pairs_out = []
    seen_pairs = set()

    def add_pair(fg, bg):
        key = (fg.lower(), bg.lower())
        if key in seen_pairs:
            return
        seen_pairs.add(key)
        res = check_pair(fg, bg)
        if res is not None:
            pairs_out.append(res)

    # Mode 1: simple {"pairs": [["#fg", "#bg"], ...]}
    if "pairs" in data and "tokens" not in data:
        for item in data.get("pairs", []):
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                add_pair(str(item[0]), str(item[1]))
        failures = sum(1 for p in pairs_out if not p["aa_normal"])
        return {"pairs": pairs_out, "failures_aa_normal": failures}

    # Mode 2: token_extract output
    tokens = data.get("tokens", [])
    palette = data.get("palette", [])

    # Collect all color hex values from tokens
    color_hexes = []
    color_counts = {}
    for t in tokens:
        if t.get("class") == "color" and t.get("hex"):
            h = t["hex"].lower()
            cnt = t.get("count", 1)
            if h not in color_counts:
                color_hexes.append(h)
                color_counts[h] = 0
            color_counts[h] += cnt

    # 2 most-used palette colors as extra backgrounds
    top2_bg = []
    if palette:
        top2_bg = [p.lower() for p in palette[:2]]

    backgrounds = list(dict.fromkeys(STANDARD_BACKGROUNDS + top2_bg))

    for fg_hex in color_hexes:
        for bg_hex in backgrounds:
            if fg_hex != bg_hex:
                add_pair(fg_hex, bg_hex)

    failures = sum(1 for p in pairs_out if not p["aa_normal"])
    return {"pairs": pairs_out, "failures_aa_normal": failures}


def main():
    try:
        path = sys.argv[1] if len(sys.argv) > 1 else ""
        if not path:
            print(json.dumps({"error": "usage: wcag_check.py <tokens.json>"}))
            return
        result = run(path)
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))


if __name__ == "__main__":
    main()
