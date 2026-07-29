"""
token_extract.py <file1> [file2 ...]

Parse CSS custom properties, SCSS variables, LESS variables, and
tailwind.config.* JS objects for color/font/spacing tokens.
Emit JSON with normalized tokens, palette, and font families.
Stdlib-only, ASCII-safe, exit-0 always.

Called by design-full/SKILL.md P1 AUDIT step.
Output fields: tokens, palette, font_families, counts.
"""

import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# CSS custom properties:  --name: value;
CSS_VAR_RE = re.compile(
    r"--([A-Za-z0-9_-]+)\s*:\s*([^;}{]+?)(?:\s*!important)?\s*;",
    re.MULTILINE,
)

# SCSS variables:  $name: value;
SCSS_VAR_RE = re.compile(
    r"^\$([A-Za-z0-9_-]+)\s*:\s*([^;!{}\n]+?)(?:\s*!default)?\s*;",
    re.MULTILINE,
)

# LESS variables: @name: value;  but NOT @media/@import/@keyframes/@font-face/@mixin
LESS_SKIP_RE = re.compile(
    r"^@(?:media|import|keyframes|font-face|mixin|include|charset|namespace|supports)\b",
    re.IGNORECASE,
)
LESS_VAR_RE = re.compile(
    r"^@([A-Za-z0-9_-]+)\s*:\s*([^;{}\n]+?)\s*;",
    re.MULTILINE,
)

# Color patterns
HEX3_RE = re.compile(r"^#([0-9a-fA-F]{3})$")
HEX6_RE = re.compile(r"^#([0-9a-fA-F]{6})$")
HEX8_RE = re.compile(r"^#([0-9a-fA-F]{8})$")
RGB_RE = re.compile(
    r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)"
)
HSL_RE = re.compile(
    r"hsla?\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%(?:\s*,\s*([\d.]+))?\s*\)"
)

# Tailwind config extraction (best-effort regex, not AST)
TW_COLOR_RE = re.compile(r"""['"]([^'"]+)['"]\s*:\s*['"](#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\))['"]\s*,?""")
TW_FONT_RE = re.compile(r"""fontFamily\s*:\s*\{(.*?)\}""", re.DOTALL)
TW_FONT_ENTRY_RE = re.compile(r"""['"]?([A-Za-z0-9_-]+)['"]?\s*:\s*\[?\s*['"](.*?)['"]\s*\]?""")
TW_SPACING_RE = re.compile(r"""spacing\s*:\s*\{(.*?)\}""", re.DOTALL)
TW_SPACING_ENTRY_RE = re.compile(r"""['"]?([A-Za-z0-9_.-]+)['"]?\s*:\s*['"]([\d.]+(?:px|rem|em|%)?)['"]\s*,?""")

# ---------------------------------------------------------------------------
# Color normalization
# ---------------------------------------------------------------------------

def _clamp(v, lo=0, hi=255):
    return max(lo, min(hi, v))


def _hsl_to_rgb(h, s, l):
    """Convert HSL (degrees, %, %) to (r, g, b) in 0-255 range."""
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


def normalize_color(raw):
    """
    Try to parse raw as a color value.
    Returns (hex6_lower, alpha_float_or_None) or (None, None) if not a color.
    """
    raw = raw.strip()

    m = HEX3_RE.match(raw)
    if m:
        s = m.group(1)
        r, g, b = int(s[0]*2, 16), int(s[1]*2, 16), int(s[2]*2, 16)
        return "#{:02x}{:02x}{:02x}".format(r, g, b), None

    m = HEX6_RE.match(raw)
    if m:
        return "#{:s}".format(m.group(1).lower()), None

    m = HEX8_RE.match(raw)
    if m:
        s = m.group(1).lower()
        alpha = int(s[6:8], 16) / 255.0
        return "#" + s[:6], (alpha if alpha < 1.0 else None)

    m = RGB_RE.match(raw)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        alpha = float(m.group(4)) if m.group(4) is not None else None
        return "#{:02x}{:02x}{:02x}".format(
            _clamp(r), _clamp(g), _clamp(b)
        ), (alpha if alpha is not None and alpha < 1.0 else None)

    m = HSL_RE.match(raw)
    if m:
        h, s, l = float(m.group(1)), float(m.group(2)), float(m.group(3))
        alpha = float(m.group(4)) if m.group(4) is not None else None
        r, g, b = _hsl_to_rgb(h, s, l)
        return "#{:02x}{:02x}{:02x}".format(r, g, b), (
            alpha if alpha is not None and alpha < 1.0 else None
        )

    return None, None


# ---------------------------------------------------------------------------
# Token classification
# ---------------------------------------------------------------------------

SIZE_RE = re.compile(r"[\d.]+(?:px|rem|em)\s*$")
SHADOW_KEYWORDS = re.compile(r"\d+px.*(?:rgba?|#)", re.IGNORECASE)


def classify_token(name, raw):
    low = name.lower()
    val = raw.strip().lower()

    hex6, _alpha = normalize_color(raw.strip())
    if hex6 is not None:
        return "color"

    if any(kw in low for kw in ("shadow", "elevation")):
        return "shadow"
    if any(kw in low for kw in ("radius", "rounded")):
        return "radius"
    if any(kw in low for kw in ("duration", "ease", "transition", "motion", "delay")):
        return "motion"
    if any(kw in low for kw in ("font", "typeface", "family", "weight", "size", "leading", "tracking", "line-height")):
        if "family" in low or "font" in low:
            return "font"
    if SIZE_RE.search(val):
        return "size-spacing"
    if SHADOW_KEYWORDS.search(val):
        return "shadow"

    return "other"


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_css(content, source):
    results = []
    for m in CSS_VAR_RE.finditer(content):
        name = "--" + m.group(1)
        raw = m.group(2).strip()
        results.append((name, raw, source))
    return results


def parse_scss(content, source):
    results = []
    for m in SCSS_VAR_RE.finditer(content):
        name = "$" + m.group(1)
        raw = m.group(2).strip()
        results.append((name, raw, source))
    return results


def parse_less(content, source):
    results = []
    for m in LESS_VAR_RE.finditer(content):
        full_match = m.group(0)
        if LESS_SKIP_RE.match(full_match):
            continue
        name = "@" + m.group(1)
        raw = m.group(2).strip()
        results.append((name, raw, source))
    return results


def parse_tailwind(content, source):
    """Best-effort extraction from a tailwind.config JS/TS file."""
    results = []

    # colors
    for m in TW_COLOR_RE.finditer(content):
        name = "--tw-color-" + m.group(1).replace(".", "-")
        raw = m.group(2).strip()
        results.append((name, raw, source))

    # font families
    fm = TW_FONT_RE.search(content)
    if fm:
        block = fm.group(1)
        for em in TW_FONT_ENTRY_RE.finditer(block):
            name = "--tw-font-" + em.group(1)
            raw = em.group(2)
            results.append((name, raw, source))

    # spacing
    sm = TW_SPACING_RE.search(content)
    if sm:
        block = sm.group(1)
        for em in TW_SPACING_ENTRY_RE.finditer(block):
            name = "--tw-spacing-" + em.group(1).replace(".", "_")
            raw = em.group(2)
            results.append((name, raw, source))

    return results


def parse_file(path):
    """Return list of (name, raw, source) tuples from a file."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except Exception:
        return []

    source = os.path.basename(path)
    low = path.lower()
    fname = os.path.basename(low)

    if fname in (
        "tailwind.config.js", "tailwind.config.ts",
        "tailwind.config.mjs", "tailwind.config.cjs",
    ):
        return parse_tailwind(content, source)

    if low.endswith(".scss") or low.endswith(".sass"):
        return parse_scss(content, source) + parse_css(content, source)
    if low.endswith(".less"):
        return parse_less(content, source)
    if low.endswith(".css"):
        return parse_css(content, source)
    # catch-all: try css first
    return parse_css(content, source)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def extract_font_family(raw):
    """Return first font-family name from a value string, or None."""
    # strip quotes, take first comma-separated value
    raw = raw.strip().strip("'\"")
    first = raw.split(",")[0].strip().strip("'\"")
    # reject generic keywords
    generic = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "inherit", "initial", "unset"}
    if first.lower() in generic or not first:
        return None
    return first


def run(files):
    # name -> {raw, class, count, sources}
    token_map = {}

    for path in files:
        entries = parse_file(path)
        rel = path
        for name, raw, _src in entries:
            if name not in token_map:
                cls = classify_token(name, raw)
                token_map[name] = {
                    "name": name,
                    "raw": raw,
                    "hex": None,
                    "alpha": None,
                    "class": cls,
                    "count": 0,
                    "sources": [],
                }
                if cls == "color":
                    hex6, alpha = normalize_color(raw.strip())
                    token_map[name]["hex"] = hex6
                    if alpha is not None:
                        token_map[name]["alpha"] = round(alpha, 3)

            td = token_map[name]
            td["count"] += 1
            src_rel = rel
            if src_rel not in td["sources"]:
                td["sources"].append(src_rel)

    # build palette: unique hex colors, sorted by usage count desc
    palette_counts = {}
    for td in token_map.values():
        if td["class"] == "color" and td["hex"]:
            h = td["hex"]
            palette_counts[h] = palette_counts.get(h, 0) + td["count"]

    palette = [h for h, _ in sorted(palette_counts.items(), key=lambda x: -x[1])]

    # font families
    font_set = []
    seen_fonts = set()
    for td in token_map.values():
        if td["class"] == "font":
            ff = extract_font_family(td["raw"])
            if ff and ff not in seen_fonts:
                seen_fonts.add(ff)
                font_set.append(ff)

    # clean up tokens for output (remove internal alpha field if None)
    tokens_out = []
    for td in sorted(token_map.values(), key=lambda x: (-x["count"], x["name"])):
        entry = {
            "name": td["name"],
            "raw": td["raw"],
            "class": td["class"],
            "count": td["count"],
            "sources": td["sources"],
        }
        if td["class"] == "color":
            entry["hex"] = td["hex"]
            if td.get("alpha") is not None:
                entry["alpha"] = td["alpha"]
        tokens_out.append(entry)

    counts = {
        "tokens_total": len(tokens_out),
        "colors": sum(1 for t in tokens_out if t["class"] == "color"),
        "fonts": sum(1 for t in tokens_out if t["class"] == "font"),
        "size_spacing": sum(1 for t in tokens_out if t["class"] == "size-spacing"),
        "other": sum(1 for t in tokens_out if t["class"] not in ("color", "font", "size-spacing")),
    }

    return {
        "tokens": tokens_out,
        "palette": palette,
        "font_families": font_set,
        "counts": counts,
    }


def main():
    try:
        files = sys.argv[1:]
        if not files:
            print(json.dumps({"error": "usage: token_extract.py <file1> [file2 ...]"}))
            return
        result = run(files)
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))


if __name__ == "__main__":
    main()
