"""
panel_sample.py -- deterministically sample a representative persona subset
from the focus-group skill's persona files for a lite design panel.

Usage:
    python panel_sample.py --n 24 [--youth-boost] [--seed N] [--personas-dir PATH]

Caller: design-full/SKILL.md (P2/P4/P7 focus gates, panel-lite budget).
No existing script serves this purpose.
JSON fields emitted: seed, n, youth_boost, panel (list of persona objects), quota.
Task: implement deterministic persona sampling across focus-group typology panels.

Constraints: Python 3 stdlib only, ASCII output, deterministic, silent no-op on
bad input (exits 0 with {"error": "..."}).
"""

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path


# Relative to this script's own install location (.../skills/design-full/scripts/),
# not a hardcoded user/drive, so it resolves correctly on any machine.
DEFAULT_PERSONAS_DIR = str(Path(__file__).resolve().parents[2] / "focus-group" / "references")

# Default quota for n=24 across panels (panel_name -> count).
# Panel name matches filename prefix before "-personas.md".
BASE_QUOTAS_24 = {
    "human": 2,
    "agent": 2,
    "spiral": 3,
    "mbti": 4,
    "enneagram": 3,
    "international": 3,
    "jung": 2,
    "rogers": 2,
    "disc": 1,
    "attachment": 1,
    "dark-triad": 1,
}
# Sum = 24


# Tolerant header regex: matches any ## ID: ... line where ID is alphanumeric+dash.
# Captures the full text after "ID:" for flexible downstream parsing.
# Handles all real formats found in focus-group references:
#   ## H1: The Enthusiast -- "Alex"
#   ## MB1: INTJ (Architect)
#   ## J1: Viktor -- The Hero
#   ## S1: Benedek "Beni" Varga -- BEIGE dominant
#   ## A1: Frontier -- The Capable Generalist Agent
#   ## I1: Istvan -- Hungarian / Central-Eastern European
_HEADER_RE = re.compile(
    r'^##\s+([A-Za-z0-9_-]+):\s+(.+?)\s*$',
    re.MULTILINE,
)

# Demographics age extraction: look for a number that is likely an age (< 100, > 0)
_AGE_RE = re.compile(r'\b(\d{1,2})\b')
_DEMOGRAPHICS_BLOCK_RE = re.compile(
    r'\*\*Demographics:\*\*[^\n]*\n?(.{0,300})',
    re.DOTALL,
)

YOUTH_AGE_THRESHOLD = 25
YOUTH_KEYWORDS = re.compile(r'\b(gen z|student|teen|teenager|youth|young)\b', re.IGNORECASE)


def _safe_ascii(s):
    """Replace non-ASCII chars with '?' for safe output."""
    return s.encode('ascii', errors='replace').decode('ascii')


_QUOTED_NAME_RE = re.compile(r'"([^"]+)"')
# Em-dash variants: unicode em-dash U+2014, en-dash U+2013, or "--" or " - "
_EMDASH_RE = re.compile("[ 	]*(?:" + chr(0x2014) + "|" + chr(0x2013) + "|--)[ 	]*")


def _parse_label(label_raw):
    """
    Parse the text after "ID:" into (title, name).
    Handles all real formats:
      'The Enthusiast -- "Alex"'     -> title="The Enthusiast", name="Alex"
      'INTJ (Architect)'             -> title="INTJ (Architect)", name=""
      'Viktor -- The Hero'           -> title="The Hero", name="Viktor"
      'Benedek "Beni" Varga -- ...'  -> title=part-after-dash, name="Beni" or full name
      'Frontier -- The Capable ...'  -> title="Frontier", name="" (no name to extract)
    Strategy: split on em-dash variant; if quoted name present anywhere extract it;
    left part = candidate name if it looks like a name (no leading 'The'/'An'),
    right part = title otherwise.
    """
    label = label_raw.strip()

    # Extract quoted name first
    qm = _QUOTED_NAME_RE.search(label)
    quoted_name = _safe_ascii(qm.group(1)) if qm else ""

    # Split on em-dash
    parts = _EMDASH_RE.split(label, maxsplit=1)
    left = _safe_ascii(parts[0].strip()) if parts else _safe_ascii(label)
    right = _safe_ascii(parts[1].strip()) if len(parts) > 1 else ""

    if quoted_name:
        # Format: "Title -- 'Name'" or similar
        # Left side is the title; quoted name is the name
        title = left
        name = quoted_name
    elif right:
        # Two parts separated by em-dash.
        # If left starts with 'The ' or 'An ' it is a title, right is subtitle.
        # Otherwise left is a person-name, right is the role/title.
        left_lower = left.lower()
        if left_lower.startswith('the ') or left_lower.startswith('an '):
            title = left
            name = ""
        else:
            # Left is a name (possibly with nickname in quotes already stripped)
            # Strip inline quotes from left to get clean name
            clean_left = _QUOTED_NAME_RE.sub('', left).strip()
            # If clean_left has more than one word and looks like a full name, use it
            name = clean_left if clean_left else left
            title = right
    else:
        # No dash -- the whole label is the title
        title = left
        name = ""

    return title, name


def _extract_personas_from_file(filepath):
    """
    Parse a personas markdown file and return a list of dicts:
    [{"id": ..., "name": ..., "title": ..., "raw_block": ...}, ...]
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()
    except Exception:
        return []

    personas = []
    header_matches = list(_HEADER_RE.finditer(content))
    for i, m in enumerate(header_matches):
        pid = _safe_ascii(m.group(1).strip())
        label_raw = m.group(2)

        title, name = _parse_label(label_raw)

        # Extract the block between this header and the next
        block_start = m.end()
        block_end = header_matches[i + 1].start() if i + 1 < len(header_matches) else len(content)
        block = content[block_start:block_end]

        personas.append({
            "id": pid,
            "name": name,
            "title": title,
            "raw_block": block,
        })
    return personas


def _is_young(persona):
    """Return True if persona's demographics suggest age <= 25 or Gen Z / student / teen."""
    block = persona.get("raw_block", "")
    # Check keywords first (fast path)
    if YOUTH_KEYWORDS.search(block):
        return True
    # Try to find a Demographics line and extract first plausible age number
    dm = _DEMOGRAPHICS_BLOCK_RE.search(block)
    if dm:
        demo_text = dm.group(0)
    else:
        # Fall back to first 400 chars
        demo_text = block[:400]
    ages = _AGE_RE.findall(demo_text)
    for a in ages:
        age_int = int(a)
        if 10 <= age_int <= YOUTH_AGE_THRESHOLD:
            return True
    return False


def _discover_panel_files(personas_dir):
    """
    Return dict: panel_name -> filepath for every *-personas.md file found.
    """
    panels = {}
    try:
        entries = os.listdir(personas_dir)
    except Exception:
        return panels
    for fname in entries:
        if fname.endswith('-personas.md'):
            panel_name = fname[:-len('-personas.md')]
            panels[panel_name] = os.path.join(personas_dir, fname)
    return panels


def _compute_quotas(n, available_panels):
    """
    Compute per-panel quota for requested n, scaled from BASE_QUOTAS_24.
    Strategy:
      Pass 1 -- base panels present in available_panels get quota scaled from
                BASE_QUOTAS_24 proportionally. Missing base panels' weight is
                redistributed round-robin among present base panels.
      Pass 2 -- Extra panels (not in BASE_QUOTAS_24 but available) share any
                remaining slots after base panels are satisfied. Each extra
                panel gets at most 1 slot by default; if still remainder exists
                distribute round-robin.
    Result always sums to exactly n. Returns dict panel_name -> int count (>0 only).
    """
    if n <= 0:
        return {}

    available_set = set(available_panels)

    # Split into base-present, base-missing, and extra panels
    present_base = [p for p in BASE_QUOTAS_24 if p in available_set]
    missing_base = [p for p in BASE_QUOTAS_24 if p not in available_set]
    extra_panels = sorted(p for p in available_set if p not in BASE_QUOTAS_24)

    if not present_base and not extra_panels:
        return {}

    # Total base weight available (present only; missing weight redistributed)
    total_base_weight = sum(BASE_QUOTAS_24.values())  # always 24
    present_weight = sum(BASE_QUOTAS_24[p] for p in present_base)
    missing_weight = sum(BASE_QUOTAS_24[p] for p in missing_base)

    # Scale present base panels to fill n slots; extras get 0 in pass 1
    # Effective weight for present panels = present_weight + missing_weight (redistributed)
    # so they fill the full n, scaled proportionally
    raw = {}
    if present_base:
        effective_weight = present_weight + missing_weight
        for p in present_base:
            raw[p] = BASE_QUOTAS_24[p] / effective_weight * n
    # Extra panels get 0 raw weight initially
    for p in extra_panels:
        raw[p] = 0.0

    # Round with largest-remainder method (Hamilton method) to sum exactly to n
    all_panels = sorted(raw.keys())
    floored = {p: int(raw[p]) for p in all_panels}
    remainder = n - sum(floored.values())

    # Distribute remainder: prefer panels with largest fractional part, then alpha
    fracs = sorted(
        all_panels,
        key=lambda p: (-(raw[p] - int(raw[p])), p),
    )
    for i in range(max(0, remainder)):
        floored[fracs[i % len(fracs)]] += 1

    # If extra panels exist and there are still slots to spare (remainder > 0
    # was already consumed above), give extras round-robin from what base panels
    # might cede. But only if n > sum-of-base i.e. extras have capacity for slots.
    # Actually: at this point sum == n exactly; extras got 0. If we want to
    # include extras, we'd need to steal from base panels -- but the spec says
    # "redistribute remainder round-robin over available panels" for missing base
    # panels, not for extras. So extras participate only when ALL base quotas
    # are 0 (i.e. no base panels present). This keeps base panels as primary.
    # If present_base is empty, distribute n across extra panels equally:
    if not present_base and extra_panels:
        floored = {p: 0 for p in extra_panels}
        per = n // len(extra_panels)
        leftover = n - per * len(extra_panels)
        for i, p in enumerate(extra_panels):
            floored[p] = per + (1 if i < leftover else 0)

    return {p: v for p, v in floored.items() if v > 0}


def _sample_panel(rng, personas, count, youth_boost):
    """
    Sample `count` personas from the list.
    With youth_boost: fill up to half quota from young personas first,
    then fill remainder from normal sampling (no repeats).
    Returns list of persona dicts (without raw_block).
    """
    if not personas or count <= 0:
        return []
    count = min(count, len(personas))

    if youth_boost:
        young = [p for p in personas if p.get("young")]
        old = [p for p in personas if not p.get("young")]
        youth_quota = min(count // 2, len(young))
        remaining_quota = count - youth_quota
        chosen_young = rng.sample(young, youth_quota) if youth_quota > 0 else []
        chosen_old = rng.sample(old, min(remaining_quota, len(old)))
        chosen = chosen_young + chosen_old
        # If we still need more (old pool short), top up from young
        if len(chosen) < count:
            used_ids = {p["id"] for p in chosen}
            leftovers = [p for p in personas if p["id"] not in used_ids]
            still_need = count - len(chosen)
            chosen += rng.sample(leftovers, min(still_need, len(leftovers)))
    else:
        chosen = rng.sample(personas, count)

    # Strip raw_block before returning
    return [{k: v for k, v in p.items() if k != "raw_block"} for p in chosen]


def main():
    parser = argparse.ArgumentParser(add_help=False)
    # Use str for numeric args so argparse never calls sys.exit on bad input
    parser.add_argument('--n', type=str, default="24")
    parser.add_argument('--youth-boost', action='store_true')
    parser.add_argument('--seed', type=str, default="42")
    parser.add_argument('--personas-dir', default=DEFAULT_PERSONAS_DIR)

    try:
        args, _unknown = parser.parse_known_args()
    except Exception:
        print(json.dumps({"error": "bad arguments"}))
        return

    try:
        n = int(args.n)
    except (TypeError, ValueError):
        print(json.dumps({"error": "invalid --n value: " + str(args.n)}))
        return
    try:
        seed = int(args.seed)
    except (TypeError, ValueError):
        print(json.dumps({"error": "invalid --seed value: " + str(args.seed)}))
        return
    youth_boost = args.youth_boost
    personas_dir = args.personas_dir

    if n <= 0:
        print(json.dumps({"error": "n must be positive", "seed": seed, "n": n,
                          "youth_boost": youth_boost, "panel": [], "quota": {}}))
        return

    # Discover available panel files
    panel_files = _discover_panel_files(personas_dir)
    if not panel_files:
        print(json.dumps({"error": "no persona files found in " + str(personas_dir),
                          "seed": seed, "n": n, "youth_boost": youth_boost,
                          "panel": [], "quota": {}}))
        return

    # Compute quotas
    quotas = _compute_quotas(n, set(panel_files.keys()))
    if not quotas:
        print(json.dumps({"error": "quota computation failed",
                          "seed": seed, "n": n, "youth_boost": youth_boost,
                          "panel": [], "quota": {}}))
        return

    rng = random.Random(seed)

    sampled = []
    actual_quotas = {}

    for panel_name in sorted(quotas.keys()):
        count = quotas[panel_name]
        if count <= 0:
            continue
        filepath = panel_files.get(panel_name, "")
        raw_personas = _extract_personas_from_file(filepath)

        # Annotate each with young flag and panel info
        for p in raw_personas:
            p["young"] = _is_young(p)
            p["panel"] = panel_name
            p["file"] = os.path.basename(filepath)

        chosen = _sample_panel(rng, raw_personas, count, youth_boost)
        sampled.extend(chosen)
        actual_quotas[panel_name] = len(chosen)

    # Build output panel list
    panel_out = []
    for p in sampled:
        panel_out.append({
            "id": p.get("id", ""),
            "name": p.get("name", ""),
            "title": p.get("title", ""),
            "panel": p.get("panel", ""),
            "file": p.get("file", ""),
            "young": p.get("young", False),
        })

    result = {
        "seed": seed,
        "n": len(panel_out),
        "youth_boost": youth_boost,
        "panel": panel_out,
        "quota": actual_quotas,
    }
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(0)
