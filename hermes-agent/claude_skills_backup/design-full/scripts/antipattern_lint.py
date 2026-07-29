"""
antipattern_lint.py <dir-or-file>

Scan .html/.css/.scss files for ~35 mechanically-checkable design anti-patterns.
Rules AP01..AP35.  Stdlib-only, ASCII-safe, exit-0 always.

Called by design-full/SKILL.md P4 step before showing mockups.
Output: {"findings": [...], "files_scanned": N, "clean": bool}
"""

import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return ""


def scan_paths(target):
    """Yield absolute paths to .html/.css/.scss files under target."""
    target = os.path.abspath(target)
    if os.path.isfile(target):
        ext = os.path.splitext(target)[1].lower()
        if ext in (".html", ".css", ".scss", ".less"):
            yield target
        return
    for dirpath, dirs, files in os.walk(target, topdown=True):
        dirs[:] = [d for d in dirs if d not in (
            "node_modules", ".git", "dist", "build", ".next", ".nuxt",
            "__pycache__", ".worktrees", "exclude",
        )]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in (".html", ".css", ".scss", ".less"):
                yield os.path.join(dirpath, fname)


def line_of(content, idx):
    """Return 1-based line number for character index idx in content."""
    return content[:idx].count("\n") + 1


# ---------------------------------------------------------------------------
# Individual rule implementations
# ---------------------------------------------------------------------------

def ap01_transition_all(path, content, findings):
    """AP01: transition: all"""
    for m in re.finditer(r"transition\s*:\s*all\b", content, re.IGNORECASE):
        findings.append({"rule": "AP01", "file": path, "line": line_of(content, m.start()),
                         "detail": "transition: all (prefer specific properties)"})


def ap02_no_focus_visible(path, content, findings, file_set_content):
    """AP02: interactive elements styled but no :focus-visible anywhere in file set."""
    has_interactive = bool(re.search(
        r"(?:button|a|input|select|textarea)\s*\{", content, re.IGNORECASE
    ))
    if not has_interactive:
        return
    combined = "\n".join(file_set_content)
    if not re.search(r":focus-visible", combined, re.IGNORECASE):
        findings.append({"rule": "AP02", "file": path, "line": 1,
                         "detail": "interactive elements styled but no :focus-visible found in file set"})


def ap03_pure_black_bg(path, content, findings):
    """AP03: pure black (#000/#000000) as background of body or large surface."""
    for m in re.finditer(
        r"(?:body|\.wrapper|\.container|\.app|main)\s*\{[^}]*?background(?:-color)?\s*:\s*(#000000?)\b",
        content, re.IGNORECASE | re.DOTALL
    ):
        findings.append({"rule": "AP03", "file": path, "line": line_of(content, m.start()),
                         "detail": "pure black background on large surface: " + m.group(1)})


def ap04_white_on_black(path, content, findings):
    """AP04: pure #fff text color with #000 bg in same rule."""
    for m in re.finditer(
        r"\{[^}]*?color\s*:\s*(?:#fff(?:fff)?|white)\b[^}]*?background(?:-color)?\s*:\s*(?:#000(?:000)?|black)\b[^}]*\}",
        content, re.IGNORECASE | re.DOTALL
    ):
        findings.append({"rule": "AP04", "file": path, "line": line_of(content, m.start()),
                         "detail": "pure white text on pure black background"})
    # also the reverse order
    for m in re.finditer(
        r"\{[^}]*?background(?:-color)?\s*:\s*(?:#000(?:000)?|black)\b[^}]*?color\s*:\s*(?:#fff(?:fff)?|white)\b[^}]*\}",
        content, re.IGNORECASE | re.DOTALL
    ):
        findings.append({"rule": "AP04", "file": path, "line": line_of(content, m.start()),
                         "detail": "pure white text on pure black background"})


def ap05_tiny_font(path, content, findings):
    """AP05: font-size < 12px"""
    for m in re.finditer(r"font-size\s*:\s*([\d.]+)px\b", content, re.IGNORECASE):
        val = float(m.group(1))
        if val < 12:
            findings.append({"rule": "AP05", "file": path, "line": line_of(content, m.start()),
                             "detail": "font-size: {:.0f}px (below 12px minimum)".format(val)})


def ap06_bounce_easing(path, content, findings):
    """AP06: bounce/back easing (cubic-bezier y outside [0,1] or keyword bounce/back)."""
    for m in re.finditer(r"cubic-bezier\s*\(\s*[\d.+-]+\s*,\s*([\d.+-]+)\s*,\s*[\d.+-]+\s*,\s*([\d.+-]+)\s*\)",
                          content, re.IGNORECASE):
        y1, y2 = float(m.group(1)), float(m.group(2))
        if y1 < 0 or y1 > 1 or y2 < 0 or y2 > 1:
            findings.append({"rule": "AP06", "file": path, "line": line_of(content, m.start()),
                             "detail": "cubic-bezier y params outside [0,1]: ({:.2f}, {:.2f})".format(y1, y2)})
    for m in re.finditer(r"\b(bounce|ease-in-back|ease-out-back|ease-in-out-back)\b",
                          content, re.IGNORECASE):
        findings.append({"rule": "AP06", "file": path, "line": line_of(content, m.start()),
                         "detail": "bounce/back easing keyword: " + m.group(1)})


def ap07_no_reduced_motion(path, content, findings, file_set_content):
    """AP07: @keyframes or animation: present but no prefers-reduced-motion in file set."""
    has_animation = bool(re.search(r"@keyframes\b|animation\s*:", content, re.IGNORECASE))
    if not has_animation:
        return
    combined = "\n".join(file_set_content)
    if not re.search(r"prefers-reduced-motion", combined, re.IGNORECASE):
        findings.append({"rule": "AP07", "file": path, "line": 1,
                         "detail": "animations present but no prefers-reduced-motion media query in file set"})


def ap08_overused_font(path, content, findings):
    """AP08: primary font-family is a cliche system font."""
    overused = ["inter", "roboto", "arial", "space grotesk", "open sans", "lato"]
    for m in re.finditer(r"font-family\s*:\s*([^;}{]+);", content, re.IGNORECASE):
        val = m.group(1).lower().strip()
        for of in overused:
            if val.startswith(("'" + of, '"' + of, of)):
                findings.append({"rule": "AP08", "file": path, "line": line_of(content, m.start()),
                                 "detail": "overused primary font: " + of})
                break


def ap09_cliche_indigo(path, content, findings):
    """AP09: cliche indigo palette (#6366f1/#8b5cf6/#7c3aed)."""
    cliche = ["#6366f1", "#8b5cf6", "#7c3aed"]
    for m in re.finditer(r"#([0-9a-fA-F]{6})", content):
        h = "#" + m.group(1).lower()
        if h in cliche:
            findings.append({"rule": "AP09", "file": path, "line": line_of(content, m.start()),
                             "detail": "cliche indigo color: " + h})


def ap10_uniform_radius(path, content, findings):
    """AP10: one distinct border-radius value with >=8 uses and no other."""
    all_radii = re.findall(r"border-radius\s*:\s*([\d.]+(?:px|rem|em|%))\b", content, re.IGNORECASE)
    if not all_radii:
        return
    distinct = {}
    for r in all_radii:
        distinct[r] = distinct.get(r, 0) + 1
    if len(distinct) == 1:
        val, cnt = next(iter(distinct.items()))
        if cnt >= 8:
            findings.append({"rule": "AP10", "file": path, "line": 1,
                             "detail": "uniform border-radius: {} used {} times, no variation".format(val, cnt)})


def ap11_harsh_shadow(path, content, findings):
    """AP11: box-shadow blur=0 or rgba alpha > 0.5."""
    for m in re.finditer(r"box-shadow\s*:[^;}{]+;", content, re.IGNORECASE):
        val = m.group(0)
        # blur is 0: patterns like "0 2px 0 ..." (3rd number is blur)
        if re.search(r"\d+px\s+\d+px\s+0(?:px)?\s", val):
            findings.append({"rule": "AP11", "file": path, "line": line_of(content, m.start()),
                             "detail": "harsh shadow with 0 blur"})
            continue
        # rgba alpha > 0.5
        for am in re.finditer(r"rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([\d.]+)\s*\)", val, re.IGNORECASE):
            alpha = float(am.group(1))
            if alpha > 0.5:
                findings.append({"rule": "AP11", "file": path, "line": line_of(content, m.start()),
                                 "detail": "harsh shadow rgba alpha {:.2f} > 0.5".format(alpha)})
                break


def ap12_tight_body_leading(path, content, findings):
    """AP12: line-height < 1.4 on body/p."""
    for m in re.finditer(
        r"(?:body|p)\s*\{[^}]*?line-height\s*:\s*([\d.]+)\s*;",
        content, re.IGNORECASE | re.DOTALL
    ):
        val = float(m.group(1))
        if val < 1.4:
            findings.append({"rule": "AP12", "file": path, "line": line_of(content, m.start()),
                             "detail": "body/p line-height {:.2f} (below 1.4)".format(val)})


def ap13_unbounded_measure(path, content, findings):
    """AP13: HTML body text container without max-width when p tags exist."""
    if not path.lower().endswith(".html"):
        return
    has_p = bool(re.search(r"<p[\s>]", content, re.IGNORECASE))
    if not has_p:
        return
    # heuristic: if no max-width anywhere in the HTML file (inline style or style tag)
    has_max_width = bool(re.search(r"max-width\s*:", content, re.IGNORECASE))
    if not has_max_width:
        findings.append({"rule": "AP13", "file": path, "line": 1,
                         "detail": "body text container lacks max-width (unbounded measure)"})


def ap14_low_contrast_gray(path, content, findings):
    """AP14: #999 or lighter (>=0x99 on all channels) used as text color."""
    for m in re.finditer(r"(?:^|\s)color\s*:\s*(#[0-9a-fA-F]{3,6})\b", content, re.IGNORECASE | re.MULTILINE):
        h = m.group(1)
        try:
            if len(h) == 4:
                r, g, b = int(h[1]*2, 16), int(h[2]*2, 16), int(h[3]*2, 16)
            elif len(h) == 7:
                r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
            else:
                continue
            if r >= 0x99 and g >= 0x99 and b >= 0x99:
                findings.append({"rule": "AP14", "file": path, "line": line_of(content, m.start()),
                                 "detail": "low-contrast gray text color: " + h.lower()})
        except ValueError:
            continue


def ap15_gradient_text_overuse(path, content, findings):
    """AP15: >2 background-clip: text."""
    matches = re.findall(r"background-clip\s*:\s*text\b", content, re.IGNORECASE)
    if len(matches) > 2:
        findings.append({"rule": "AP15", "file": path, "line": 1,
                         "detail": "background-clip: text used {} times (overused gradient text)".format(len(matches))})


def ap16_emoji_in_ui(path, content, findings):
    """AP16: emoji codepoints in HTML body text."""
    if not path.lower().endswith(".html"):
        return
    # Check for high-plane codepoints (emoji range U+1F300+) in text nodes (rough heuristic)
    emoji_re = re.compile("[" + chr(0x1F300) + "-" + chr(0x1FAFF) + chr(0x2600) + "-" + chr(0x27BF) + "]", re.UNICODE)
    if emoji_re.search(content):
        findings.append({"rule": "AP16", "file": path, "line": 1,
                         "detail": "emoji characters found in HTML (may be decorative in UI)"})


def ap17_lorem_ipsum(path, content, findings):
    """AP17: Lorem ipsum placeholder text."""
    if re.search(r"\blorem\s+ipsum\b", content, re.IGNORECASE):
        findings.append({"rule": "AP17", "file": path, "line": 1,
                         "detail": "lorem ipsum placeholder text found"})


def ap18_missing_viewport_meta(path, content, findings):
    """AP18: HTML without <meta name="viewport">."""
    if not path.lower().endswith(".html"):
        return
    if not re.search(r'<meta[^>]+name=["\']viewport["\']', content, re.IGNORECASE):
        findings.append({"rule": "AP18", "file": path, "line": 1,
                         "detail": "missing <meta name=\"viewport\"> in HTML"})


def ap19_no_hover(path, content, findings, file_set_content):
    """AP19: buttons styled but zero :hover in file set."""
    has_button = bool(re.search(r"button\s*\{", content, re.IGNORECASE))
    if not has_button:
        return
    combined = "\n".join(file_set_content)
    if not re.search(r":hover", combined, re.IGNORECASE):
        findings.append({"rule": "AP19", "file": path, "line": 1,
                         "detail": "buttons styled but no :hover states found in file set"})


def ap20_no_active_focus(path, content, findings, file_set_content):
    """AP20: zero :active AND zero :focus in file set."""
    combined = "\n".join(file_set_content)
    has_active = bool(re.search(r":active\b", combined, re.IGNORECASE))
    has_focus = bool(re.search(r":focus\b", combined, re.IGNORECASE))
    if not has_active and not has_focus:
        findings.append({"rule": "AP20", "file": path, "line": 1,
                         "detail": "no :active or :focus states found in entire file set"})


def ap21_fixed_width_container(path, content, findings):
    """AP21: width: NNNpx >= 600 without max-width."""
    for m in re.finditer(r"width\s*:\s*(\d+)px\b", content, re.IGNORECASE):
        val = int(m.group(1))
        if val >= 600:
            # check if there's a max-width in the surrounding rule block
            start = content.rfind("{", 0, m.start())
            end = content.find("}", m.start())
            if start >= 0 and end >= 0:
                block = content[start:end]
                if "max-width" not in block.lower():
                    findings.append({"rule": "AP21", "file": path, "line": line_of(content, m.start()),
                                     "detail": "fixed width: {}px without max-width in same rule".format(val)})


def ap22_img_no_alt(path, content, findings):
    """AP22: <img> tags without alt attribute."""
    if not path.lower().endswith(".html"):
        return
    for m in re.finditer(r"<img\b([^>]*)>", content, re.IGNORECASE | re.DOTALL):
        attrs = m.group(1)
        if not re.search(r'\balt\s*=', attrs, re.IGNORECASE):
            findings.append({"rule": "AP22", "file": path, "line": line_of(content, m.start()),
                             "detail": "<img> missing alt attribute"})


def ap23_heading_skip(path, content, findings):
    """AP23: h1 then h3 with no h2 in between."""
    if not path.lower().endswith(".html"):
        return
    headings = re.findall(r"<(h[1-6])\b", content, re.IGNORECASE)
    heading_nums = [int(h[1]) for h in headings]
    for i in range(len(heading_nums) - 1):
        if heading_nums[i] == 1 and heading_nums[i+1] == 3:
            # check no h2 in between
            findings.append({"rule": "AP23", "file": path, "line": 1,
                             "detail": "heading level skip: h1 followed by h3 with no h2"})
            break


def ap24_multiple_h1(path, content, findings):
    """AP24: more than one h1 tag."""
    if not path.lower().endswith(".html"):
        return
    count = len(re.findall(r"<h1\b", content, re.IGNORECASE))
    if count > 1:
        findings.append({"rule": "AP24", "file": path, "line": 1,
                         "detail": "{} h1 elements found (should be exactly 1)".format(count)})


def ap25_slow_animation(path, content, findings):
    """AP25: animation duration > 1s and < 10s (excluding likely infinite ambient)."""
    for m in re.finditer(r"animation(?:-duration)?\s*:[^;}{]+;", content, re.IGNORECASE):
        val_str = m.group(0)
        # skip infinite
        if re.search(r"\binfinite\b", val_str, re.IGNORECASE):
            continue
        # find duration values like 1.5s or 1500ms
        for dm in re.finditer(r"([\d.]+)(s|ms)\b", val_str, re.IGNORECASE):
            num, unit = float(dm.group(1)), dm.group(2).lower()
            secs = num if unit == "s" else num / 1000.0
            if 1.0 < secs < 10.0:
                findings.append({"rule": "AP25", "file": path, "line": line_of(content, m.start()),
                                 "detail": "slow animation duration: {:.1f}s".format(secs)})
                break


def ap26_too_many_infinite(path, content, findings):
    """AP26: >5 'infinite' animation keywords."""
    count = len(re.findall(r"\binfinite\b", content, re.IGNORECASE))
    if count > 5:
        findings.append({"rule": "AP26", "file": path, "line": 1,
                         "detail": "{} 'infinite' animations (> 5 threshold)".format(count)})


def ap27_extreme_z(path, content, findings):
    """AP27: z-index > 1000."""
    for m in re.finditer(r"z-index\s*:\s*(\d+)\b", content, re.IGNORECASE):
        val = int(m.group(1))
        if val > 1000:
            findings.append({"rule": "AP27", "file": path, "line": line_of(content, m.start()),
                             "detail": "extreme z-index: {}".format(val)})


def ap28_important_overuse(path, content, findings):
    """AP28: >5 !important declarations."""
    count = len(re.findall(r"!\s*important\b", content, re.IGNORECASE))
    if count > 5:
        findings.append({"rule": "AP28", "file": path, "line": 1,
                         "detail": "{} !important declarations (> 5 threshold)".format(count)})


def ap29_inline_style_overuse(path, content, findings):
    """AP29: >10 style= attributes in HTML."""
    if not path.lower().endswith(".html"):
        return
    count = len(re.findall(r'\bstyle\s*=', content, re.IGNORECASE))
    if count > 10:
        findings.append({"rule": "AP29", "file": path, "line": 1,
                         "detail": "{} inline style= attributes (> 10 threshold)".format(count)})


def ap30_nested_cards(path, content, findings):
    """AP30: element with class containing 'card' nested inside another (HTML only)."""
    if not path.lower().endswith(".html"):
        return
    # Find all class="...card..." elements and check nesting
    card_re = re.compile(r'class=["\'][^"\']*\bcard\b[^"\']*["\']', re.IGNORECASE)
    positions = [m.start() for m in card_re.finditer(content)]
    if len(positions) >= 2:
        # heuristic: two card classes where one appears inside the other's tag block
        # Check that at least one card span is fully inside another
        for i, p1 in enumerate(positions):
            for p2 in positions[i+1:]:
                # find close of first card element (rough: next </div> after p1)
                close_re = re.compile(r"</div>", re.IGNORECASE)
                close_m = close_re.search(content, p1 + 1)
                if close_m and p1 < p2 < close_m.start():
                    findings.append({"rule": "AP30", "file": path, "line": line_of(content, p2),
                                     "detail": "nested card elements detected"})
                    return  # one finding per file is enough


def ap31_bad_letterspacing(path, content, findings):
    """AP31: negative letter-spacing on body text, or > 0.05em without uppercase."""
    for m in re.finditer(
        r"(?:body|p|\.body-text|\.text)\s*\{[^}]*?letter-spacing\s*:\s*(-?[\d.]+)(em|px)\b",
        content, re.IGNORECASE | re.DOTALL
    ):
        val, unit = float(m.group(1)), m.group(2).lower()
        if val < 0:
            findings.append({"rule": "AP31", "file": path, "line": line_of(content, m.start()),
                             "detail": "negative letter-spacing on body text: {:.3f}{}".format(val, unit)})
        elif unit == "em" and val > 0.05:
            # check if there's text-transform: uppercase nearby
            start = content.rfind("{", 0, m.start())
            end = content.find("}", m.start())
            block = content[start:end+1] if start >= 0 and end >= 0 else ""
            if "uppercase" not in block.lower():
                findings.append({"rule": "AP31", "file": path, "line": line_of(content, m.start()),
                                 "detail": "large letter-spacing {:.3f}em on body text without text-transform:uppercase".format(val)})


def ap32_long_all_caps(path, content, findings):
    """AP32: text-transform: uppercase on p or body selectors."""
    for m in re.finditer(
        r"(?:body|p)\s*\{[^}]*?text-transform\s*:\s*uppercase\b",
        content, re.IGNORECASE | re.DOTALL
    ):
        findings.append({"rule": "AP32", "file": path, "line": line_of(content, m.start()),
                         "detail": "text-transform: uppercase on body/p text"})


def ap33_tiny_touch_target(path, content, findings):
    """AP33: explicit height < 32px on button/.btn."""
    for m in re.finditer(
        r"(?:button|\.btn)\s*\{[^}]*?height\s*:\s*([\d.]+)px\b",
        content, re.IGNORECASE | re.DOTALL
    ):
        val = float(m.group(1))
        if val < 32:
            findings.append({"rule": "AP33", "file": path, "line": line_of(content, m.start()),
                             "detail": "touch target height {:.0f}px on button (below 32px minimum)".format(val)})


def ap34_color_explosion(path, content, findings):
    """AP34: >12 distinct non-grayscale hex colors."""
    hex_vals = re.findall(r"#([0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?)\b", content)
    distinct = set()
    for h in hex_vals:
        if len(h) == 3:
            r, g, b = int(h[0]*2, 16), int(h[1]*2, 16), int(h[2]*2, 16)
        else:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        # non-grayscale: channels not all equal within tolerance 10
        if not (abs(r - g) <= 10 and abs(g - b) <= 10 and abs(r - b) <= 10):
            distinct.add(h.lower())
    if len(distinct) > 12:
        findings.append({"rule": "AP34", "file": path, "line": 1,
                         "detail": "{} distinct non-grayscale hex colors (> 12 threshold)".format(len(distinct))})


def ap35_font_count(path, content, findings):
    """AP35: >3 distinct font-family stacks."""
    families = re.findall(r"font-family\s*:\s*([^;}{]+);", content, re.IGNORECASE)
    distinct = set()
    for f in families:
        first = f.strip().split(",")[0].strip().strip("'\"").lower()
        generic = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "inherit", "initial", "unset"}
        if first and first not in generic:
            distinct.add(first)
    if len(distinct) > 3:
        findings.append({"rule": "AP35", "file": path, "line": 1,
                         "detail": "{} distinct font-family stacks (> 3 threshold)".format(len(distinct))})


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def lint(target):
    paths = list(scan_paths(target))
    if not paths:
        return {"findings": [], "files_scanned": 0, "clean": True}

    # pre-load all file contents (needed for cross-file rules)
    file_contents = {}
    for p in paths:
        file_contents[p] = read_file(p)

    all_css_content = [v for p, v in file_contents.items()
                       if p.lower().endswith((".css", ".scss", ".less"))]
    all_content = list(file_contents.values())

    findings = []

    # Track which cross-file rules have already fired (emit once per file set)
    ap02_done = set()
    ap07_done = set()
    ap19_done = set()
    ap20_done = False

    for path in paths:
        content = file_contents[path]
        rel = path  # keep absolute for now; caller can relativize

        ap01_transition_all(rel, content, findings)

        if rel not in ap02_done:
            ap02_no_focus_visible(rel, content, findings, all_content)
            ap02_done.add(rel)

        ap03_pure_black_bg(rel, content, findings)
        ap04_white_on_black(rel, content, findings)
        ap05_tiny_font(rel, content, findings)
        ap06_bounce_easing(rel, content, findings)

        if rel not in ap07_done:
            ap07_no_reduced_motion(rel, content, findings, all_content)
            ap07_done.add(rel)

        ap08_overused_font(rel, content, findings)
        ap09_cliche_indigo(rel, content, findings)
        ap10_uniform_radius(rel, content, findings)
        ap11_harsh_shadow(rel, content, findings)
        ap12_tight_body_leading(rel, content, findings)
        ap13_unbounded_measure(rel, content, findings)
        ap14_low_contrast_gray(rel, content, findings)
        ap15_gradient_text_overuse(rel, content, findings)
        ap16_emoji_in_ui(rel, content, findings)
        ap17_lorem_ipsum(rel, content, findings)
        ap18_missing_viewport_meta(rel, content, findings)

        if rel not in ap19_done:
            ap19_no_hover(rel, content, findings, all_content)
            ap19_done.add(rel)

    # AP20: once per run, flag first file if failing
    if paths:
        if not ap20_done:
            ap20_no_active_focus(paths[0], file_contents[paths[0]], findings, all_content)
            ap20_done = True

    for path in paths:
        content = file_contents[path]
        rel = path
        ap21_fixed_width_container(rel, content, findings)
        ap22_img_no_alt(rel, content, findings)
        ap23_heading_skip(rel, content, findings)
        ap24_multiple_h1(rel, content, findings)
        ap25_slow_animation(rel, content, findings)
        ap26_too_many_infinite(rel, content, findings)
        ap27_extreme_z(rel, content, findings)
        ap28_important_overuse(rel, content, findings)
        ap29_inline_style_overuse(rel, content, findings)
        ap30_nested_cards(rel, content, findings)
        ap31_bad_letterspacing(rel, content, findings)
        ap32_long_all_caps(rel, content, findings)
        ap33_tiny_touch_target(rel, content, findings)
        ap34_color_explosion(rel, content, findings)
        ap35_font_count(rel, content, findings)

    return {
        "findings": findings,
        "files_scanned": len(paths),
        "clean": len(findings) == 0,
    }


def main():
    try:
        target = sys.argv[1] if len(sys.argv) > 1 else ""
        if not target:
            print(json.dumps({"error": "usage: antipattern_lint.py <dir-or-file>"}))
            return
        result = lint(target)
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))


if __name__ == "__main__":
    main()
