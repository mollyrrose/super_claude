"""
brandbook_assemble.py -- assemble BRANDBOOK.md from pipeline state.

Usage:
    python brandbook_assemble.py <state-dir> [--out <path>] [--html]

Caller: design-full/SKILL.md (P3 design-system, P8 handoff).
No existing script serves this purpose.
JSON fields emitted to stdout: out, html, placeholders_resolved, placeholders_tbd.
Task: read state.json + tokens.json + crosstab.json files; fill brandbook template;
      write BRANDBOOK.md (and optionally BRANDBOOK.html).

Constraints: Python 3 stdlib only, ASCII output, deterministic (no datetime.now for
content), silent no-op on bad input (exits 0 with {"error": "..."}).
"""

import argparse
import json
import os
import re
import sys


# Resolve template path relative to this script file
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_TEMPLATE = os.path.normpath(
    os.path.join(_SCRIPT_DIR, '..', 'references', 'brandbook-template.md')
)

# Fallback template when the real one is missing
_FALLBACK_TEMPLATE = """# Brand Book

## {{MODE}} | {{DATE}}

### Purpose

{{PURPOSE}}

### Industry

{{INDUSTRY}}

### Tone

{{TONE}}

### Direction

{{DIRECTION}}

### Design Axes

{{AXES}}

### Palette

{{PALETTE_TABLE}}

### Typography

{{FONTS}}

### Constraints

{{CONSTRAINTS}}

### Focus Gate Summary

{{GATE_SUMMARY}}
"""

_PLACEHOLDER_RE = re.compile(r'\{\{([A-Z_]+)\}\}')


def _safe_ascii(s):
    if isinstance(s, bytes):
        return s.decode('ascii', errors='replace')
    return str(s).encode('ascii', errors='replace').decode('ascii')


def _read_json_safe(path):
    """Read and parse JSON file; return {} on any error."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            return json.load(fh)
    except Exception:
        return {}


def _load_state(state_dir):
    state_path = os.path.join(state_dir, 'state.json')
    return _read_json_safe(state_path)


def _load_tokens(state_dir):
    tokens_path = os.path.join(state_dir, 'scans', 'tokens.json')
    return _read_json_safe(tokens_path)


def _find_crosstab_files(state_dir):
    """Find all panels/*/crosstab.json files under state_dir."""
    panels_dir = os.path.join(state_dir, 'panels')
    found = []
    if not os.path.isdir(panels_dir):
        return found
    try:
        for entry in sorted(os.listdir(panels_dir)):
            ct_path = os.path.join(panels_dir, entry, 'crosstab.json')
            if os.path.isfile(ct_path):
                found.append((entry, ct_path))
    except Exception:
        pass
    return found


def _build_palette_table(tokens):
    """Build a markdown table of palette hex values from tokens.json."""
    palette = tokens.get('palette', {})
    if not palette:
        return "TBD"
    rows = ["| Role | Hex |", "|------|-----|"]
    for role, value in sorted(palette.items()):
        rows.append("| {} | {} |".format(_safe_ascii(str(role)), _safe_ascii(str(value))))
    return "\n".join(rows)


def _build_gate_summary(crosstab_files):
    """One line per gate: gate name, winner, win %."""
    if not crosstab_files:
        return "TBD"
    lines = []
    for gate_name, ct_path in crosstab_files:
        data = _read_json_safe(ct_path)
        overall = data.get('overall', {})
        if not overall:
            lines.append("{}: no data".format(_safe_ascii(gate_name)))
            continue
        # Find winner (highest win_pct)
        winner = max(overall.keys(), key=lambda k: overall[k].get('win_pct', 0))
        win_pct = overall[winner].get('win_pct', 0)
        lines.append("{}: winner {} ({:.1f}%)".format(
            _safe_ascii(gate_name), _safe_ascii(winner), float(win_pct)
        ))
    return "; ".join(lines) if lines else "TBD"


def _build_substitutions(state, tokens, crosstab_files):
    """Return dict of placeholder_name -> replacement_text (all ASCII strings)."""
    intake = state.get('intake', {})
    audit = state.get('audit', {})

    subs = {}

    # Simple fields
    subs['PURPOSE'] = _safe_ascii(str(intake.get('purpose', 'TBD')))
    subs['TONE'] = _safe_ascii(str(intake.get('tone', 'TBD')))
    subs['INDUSTRY'] = _safe_ascii(str(intake.get('industry', 'TBD')))
    subs['DATE'] = _safe_ascii(str(state.get('updated', 'unknown')))
    subs['DIRECTION'] = _safe_ascii(str(state.get('locked_direction', 'TBD')))
    subs['MODE'] = _safe_ascii(str(audit.get('brandbook_mode', 'create')))

    # Axes
    axes = intake.get('axes', {})
    if axes:
        axes_parts = []
        for k, v in sorted(axes.items()):
            axes_parts.append("{}: {}".format(_safe_ascii(str(k)), _safe_ascii(str(v))))
        subs['AXES'] = ", ".join(axes_parts)
    else:
        subs['AXES'] = 'TBD'

    # Constraints
    constraints = intake.get('constraints', [])
    if isinstance(constraints, list):
        subs['CONSTRAINTS'] = "; ".join(_safe_ascii(str(c)) for c in constraints) or 'none'
    else:
        subs['CONSTRAINTS'] = _safe_ascii(str(constraints)) if constraints else 'none'

    # Palette from tokens.json
    subs['PALETTE_TABLE'] = _build_palette_table(tokens)

    # Fonts from tokens.json
    fonts = tokens.get('font_families', [])
    if isinstance(fonts, list):
        subs['FONTS'] = ", ".join(_safe_ascii(str(f)) for f in fonts) or 'TBD'
    elif fonts:
        subs['FONTS'] = _safe_ascii(str(fonts))
    else:
        subs['FONTS'] = 'TBD'

    # Gate summary from crosstab files
    subs['GATE_SUMMARY'] = _build_gate_summary(crosstab_files)

    return subs


def _fill_template(template_text, subs):
    """
    Replace all {{PLACEHOLDER}} occurrences in template_text.
    Returns (filled_text, resolved_count, tbd_count).
    """
    resolved = 0
    tbd = 0

    def replacer(m):
        nonlocal resolved, tbd
        key = m.group(1)
        val = subs.get(key, None)
        if val is None:
            tbd += 1
            return 'TBD'
        if val == 'TBD':
            tbd += 1
        else:
            resolved += 1
        return val

    filled = _PLACEHOLDER_RE.sub(replacer, template_text)
    return filled, resolved, tbd


def _minimal_md_to_html(md_text):
    """
    Very minimal markdown -> HTML conversion.
    Handles: h1/h2/h3 headers, **bold**, bullet lists, tables (degraded).
    All other content becomes paragraphs. ASCII-only output.
    """
    lines = md_text.split('\n')
    html_lines = []
    in_list = False
    in_table = False

    def close_list():
        nonlocal in_list
        if in_list:
            html_lines.append('</ul>')
            in_list = False

    def close_table():
        nonlocal in_table
        if in_table:
            html_lines.append('</table>')
            in_table = False

    def escape_html(s):
        s = s.replace('&', '&amp;')
        s = s.replace('<', '&lt;')
        s = s.replace('>', '&gt;')
        return s

    def inline_format(s):
        # Bold: **text** -> <strong>text</strong>
        s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
        # Code: `text` -> <code>text</code>
        s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
        return s

    for line in lines:
        stripped = line.rstrip()

        # Table row: starts with |
        if stripped.startswith('|'):
            # Check if separator row (|---|---)
            if re.match(r'^\|[-| :]+\|$', stripped):
                if not in_table:
                    html_lines.append('<table border="1" style="border-collapse:collapse;">')
                    in_table = True
                continue
            close_list()
            if not in_table:
                html_lines.append('<table border="1" style="border-collapse:collapse;">')
                in_table = True
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            cell_html = ''.join('<td style="padding:4px;">{}</td>'.format(
                inline_format(escape_html(c))) for c in cells)
            html_lines.append('<tr>{}</tr>'.format(cell_html))
            continue

        close_table()

        # Headers
        if stripped.startswith('### '):
            close_list()
            html_lines.append('<h3>{}</h3>'.format(
                inline_format(escape_html(stripped[4:]))))
            continue
        if stripped.startswith('## '):
            close_list()
            html_lines.append('<h2>{}</h2>'.format(
                inline_format(escape_html(stripped[3:]))))
            continue
        if stripped.startswith('# '):
            close_list()
            html_lines.append('<h1>{}</h1>'.format(
                inline_format(escape_html(stripped[2:]))))
            continue

        # Bullet list
        if re.match(r'^[-*] ', stripped):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            html_lines.append('<li>{}</li>'.format(
                inline_format(escape_html(stripped[2:]))))
            continue

        close_list()

        # Blank line -> paragraph break
        if not stripped:
            html_lines.append('<br>')
            continue

        # Default: paragraph line
        html_lines.append('<p>{}</p>'.format(inline_format(escape_html(stripped))))

    close_list()
    close_table()

    return '\n'.join(html_lines)


def _wrap_html(content_html, title="Brand Book"):
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 720px;
          margin: 0 auto; padding: 24px; line-height: 1.6; color: #222; }}
  h1 {{ font-size: 1.8em; border-bottom: 2px solid #ccc; padding-bottom: 8px; }}
  h2 {{ font-size: 1.3em; margin-top: 1.5em; }}
  h3 {{ font-size: 1.1em; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  td, th {{ border: 1px solid #ccc; padding: 6px 10px; }}
  code {{ background: #f4f4f4; padding: 1px 4px; border-radius: 3px; font-size: 0.9em; }}
  ul {{ margin: 0.5em 0; padding-left: 1.5em; }}
</style>
</head>
<body>
{content}
</body>
</html>""".format(title=title, content=content_html)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('state_dir', nargs='?', default=None)
    parser.add_argument('--out', default=None)
    parser.add_argument('--html', action='store_true')

    try:
        args, _unknown = parser.parse_known_args()
    except Exception:
        print(json.dumps({"error": "bad arguments"}))
        return

    state_dir = args.state_dir
    html_flag = args.html

    if not state_dir:
        print(json.dumps({"error": "state-dir argument required"}))
        return

    state_dir = os.path.abspath(state_dir)
    if not os.path.isdir(state_dir):
        print(json.dumps({"error": "not a directory: " + state_dir}))
        return

    # Determine output path
    if args.out:
        out_path = os.path.abspath(args.out)
    else:
        out_path = os.path.normpath(os.path.join(state_dir, '..', 'docs', 'design', 'BRANDBOOK.md'))

    # Load data
    state = _load_state(state_dir)
    tokens = _load_tokens(state_dir)
    crosstab_files = _find_crosstab_files(state_dir)

    # Load template
    template_text = None
    if os.path.isfile(_DEFAULT_TEMPLATE):
        try:
            with open(_DEFAULT_TEMPLATE, 'r', encoding='utf-8', errors='replace') as fh:
                template_text = fh.read()
        except Exception:
            pass
    if template_text is None:
        template_text = _FALLBACK_TEMPLATE

    # Build substitutions
    subs = _build_substitutions(state, tokens, crosstab_files)

    # Fill template
    filled, resolved, tbd = _fill_template(template_text, subs)

    # Ensure all output is ASCII-safe
    filled_ascii = filled.encode('ascii', errors='replace').decode('ascii')

    # Write BRANDBOOK.md
    out_dir = os.path.dirname(out_path)
    try:
        os.makedirs(out_dir, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as fh:
            fh.write(filled_ascii)
    except Exception as exc:
        print(json.dumps({"error": "failed to write " + out_path + ": " + str(exc)}))
        return

    # Write BRANDBOOK.html if requested
    html_path = None
    if html_flag:
        html_path = out_path.replace('.md', '.html')
        try:
            content_html = _minimal_md_to_html(filled_ascii)
            html_full = _wrap_html(content_html)
            with open(html_path, 'w', encoding='utf-8') as fh:
                fh.write(html_full)
        except Exception as exc:
            html_path = None
            # Non-fatal: report but continue
            sys.stderr.write("warn: html write failed: " + str(exc) + "\n")

    result = {
        "out": out_path,
        "html": html_path,
        "placeholders_resolved": resolved,
        "placeholders_tbd": tbd,
    }
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(0)
