"""
crosstab.py -- aggregate focus-panel verdict lines into per-segment preference tables.

Usage:
    python crosstab.py <transcripts-dir> [--json <out.json>]

Caller: design-full/SKILL.md (focus gates G1/G2/G3, used after persona panel runs).
No existing script serves this purpose.
JSON fields emitted (via --json): total_verdicts, overall, by_panel, themes.
Task: parse VERDICT lines from markdown/text transcripts, compute stats, emit report.

Constraints: Python 3 stdlib only, ASCII output, deterministic, silent no-op on
bad input (exits 0 with {"error": "..."} to stdout).
"""

import argparse
import json
import os
import re
import string
import sys


# VERDICT line pattern (tolerant whitespace):
# VERDICT | <persona id and name> | <panel> | RANK: A>C>B | <one-line why>
_VERDICT_RE = re.compile(
    r'VERDICT\s*\|\s*'
    r'([^|]+?)\s*\|\s*'          # group 1: persona id/name
    r'([^|]+?)\s*\|\s*'          # group 2: panel
    r'RANK\s*:\s*'
    r'([A-Ca-c](?:[>][A-Ca-c])*)'  # group 3: rank string like A>C>B
    r'\s*\|\s*'
    r'(.+)',                      # group 4: why text
    re.IGNORECASE,
)

# English stopwords (embedded, ~60 words)
STOPWORDS = frozenset([
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'shall', 'can', 'it', 'its', 'this',
    'that', 'these', 'those', 'i', 'we', 'you', 'he', 'she', 'they', 'me',
    'us', 'him', 'her', 'them', 'my', 'our', 'your', 'his', 'their', 'as',
    'if', 'so', 'not', 'no', 'more', 'also', 'than', 'then', 'up', 'out',
    'into', 'over', 'about', 'which', 'who', 'what', 'when', 'how', 'all',
    'very', 'just', 'much',
])

TOP_THEMES = 6
BORDA_FULL = {0: 3, 1: 2, 2: 1}   # position -> points for 3-variant ranks
BORDA_SHORT = {0: 2, 1: 1}        # for 2-variant ranks


def _safe_ascii(s):
    return s.encode('ascii', errors='replace').decode('ascii')


def _tokenize_why(text):
    """Lowercase, strip punctuation, split, remove stopwords."""
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    tokens = text.split()
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def _parse_rank(rank_str):
    """Parse 'A>C>B' into ordered list of uppercase variant letters."""
    parts = re.split(r'[>]', rank_str.strip().upper())
    # Keep only A/B/C
    return [p.strip() for p in parts if p.strip() in ('A', 'B', 'C')]


def _read_transcripts(directory):
    """Read all *.md and *.txt files, return list of (filepath, content) tuples."""
    results = []
    try:
        entries = os.listdir(directory)
    except Exception:
        return results
    for fname in sorted(entries):
        if fname.endswith('.md') or fname.endswith('.txt'):
            fpath = os.path.join(directory, fname)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as fh:
                    content = fh.read()
                results.append((fpath, content))
            except Exception:
                pass
    return results


def _collect_verdicts(directory):
    """Return list of verdict dicts from all transcript files."""
    verdicts = []
    files = _read_transcripts(directory)
    for fpath, content in files:
        for line in content.splitlines():
            m = _VERDICT_RE.search(line)
            if not m:
                continue
            persona_raw = m.group(1).strip()
            panel_raw = m.group(2).strip()
            rank_raw = m.group(3).strip()
            why_raw = m.group(4).strip()

            rank = _parse_rank(rank_raw)
            if len(rank) < 2:
                # malformed rank (< 2 variants), skip
                continue

            verdicts.append({
                "persona": _safe_ascii(persona_raw),
                "panel": _safe_ascii(panel_raw).lower(),
                "rank": rank,
                "why": _safe_ascii(why_raw),
                "source": os.path.basename(fpath),
            })
    return verdicts


def _compute_overall(verdicts):
    """
    Compute per-variant stats: first-place count, win rate %, Borda score.
    Returns dict variant -> {first, win_pct, borda}.
    """
    variants = set()
    for v in verdicts:
        variants.update(v["rank"])
    variants = sorted(variants)

    counts = {vv: {"first": 0, "borda": 0} for vv in variants}
    total = len(verdicts)

    for v in verdicts:
        rank = v["rank"]
        # First place
        if rank:
            counts[rank[0]]["first"] += 1
        # Borda points
        borda_map = BORDA_FULL if len(rank) >= 3 else BORDA_SHORT
        for pos, var in enumerate(rank):
            pts = borda_map.get(pos, 0)
            counts[var]["borda"] += pts

    result = {}
    for var in variants:
        first = counts[var]["first"]
        win_pct = round(first / total * 100, 1) if total > 0 else 0.0
        result[var] = {
            "first": first,
            "win_pct": win_pct,
            "borda": counts[var]["borda"],
        }
    return result


def _compute_by_panel(verdicts):
    """
    Compute per-segment (panel) winner and vote counts.
    Returns dict panel -> {winner, counts: {A: n, B: n, C: n}}.
    """
    panels = {}
    for v in verdicts:
        panel = v["panel"]
        if panel not in panels:
            panels[panel] = {}
        if v["rank"]:
            winner_var = v["rank"][0]
            panels[panel][winner_var] = panels[panel].get(winner_var, 0) + 1

    result = {}
    for panel, cnt in sorted(panels.items()):
        if not cnt:
            continue
        winner = max(cnt.keys(), key=lambda k: cnt[k])
        result[panel] = {"winner": winner, "counts": cnt}
    return result


def _compute_themes(verdicts):
    """
    For each variant, collect why-texts of verdicts where that variant ranked first.
    Tokenize, remove stopwords, count word freq. Return top-6 per variant.
    Returns dict variant -> list of [word, count] pairs.
    """
    variant_whys = {}
    for v in verdicts:
        if v["rank"]:
            var = v["rank"][0]
            variant_whys.setdefault(var, []).append(v["why"])

    themes = {}
    for var, whys in sorted(variant_whys.items()):
        freq = {}
        for why in whys:
            for token in _tokenize_why(why):
                freq[token] = freq.get(token, 0) + 1
        # Sort by count desc, then alpha for stability
        sorted_words = sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:TOP_THEMES]
        themes[var] = [[w, c] for w, c in sorted_words]
    return themes


def _markdown_report(overall, by_panel, themes, total_verdicts):
    """Build ASCII markdown report string."""
    lines = []
    lines.append("# Focus Panel Cross-Tab Report")
    lines.append("")
    lines.append("Total verdicts: {}".format(total_verdicts))
    lines.append("")

    # Overall table
    lines.append("## Overall Results")
    lines.append("")
    lines.append("| Variant | 1st votes | Win % | Borda |")
    lines.append("|---------|-----------|-------|-------|")
    for var in sorted(overall.keys()):
        d = overall[var]
        lines.append("| {} | {} | {}% | {} |".format(
            var, d["first"], d["win_pct"], d["borda"]))
    lines.append("")

    # Per-segment table
    lines.append("## Per-Segment Results")
    lines.append("")
    lines.append("| Segment | Winner | Votes |")
    lines.append("|---------|--------|-------|")
    for panel in sorted(by_panel.keys()):
        d = by_panel[panel]
        winner = d["winner"]
        votes = d["counts"].get(winner, 0)
        total_seg = sum(d["counts"].values())
        lines.append("| {} | {} | {}/{} |".format(panel, winner, votes, total_seg))
    lines.append("")

    # Themes per variant
    lines.append("## Top Themes by Variant")
    lines.append("")
    for var in sorted(themes.keys()):
        word_list = themes[var]
        word_str = ", ".join("{}({})".format(w, c) for w, c in word_list)
        lines.append("**Variant {}**: {}".format(var, word_str))
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('transcripts_dir', nargs='?', default=None)
    parser.add_argument('--json', default=None)

    try:
        args, _unknown = parser.parse_known_args()
    except Exception:
        print(json.dumps({"error": "bad arguments"}))
        return

    transcripts_dir = args.transcripts_dir
    json_out = args.json

    if not transcripts_dir:
        print(json.dumps({"error": "transcripts-dir argument required"}))
        return

    if not os.path.isdir(transcripts_dir):
        print(json.dumps({"error": "not a directory: " + str(transcripts_dir)}))
        return

    verdicts = _collect_verdicts(transcripts_dir)
    total = len(verdicts)

    overall = _compute_overall(verdicts)
    by_panel = _compute_by_panel(verdicts)
    themes = _compute_themes(verdicts)

    report = _markdown_report(overall, by_panel, themes, total)
    print(report)

    if json_out:
        agg = {
            "total_verdicts": total,
            "overall": overall,
            "by_panel": by_panel,
            "themes": themes,
        }
        try:
            out_dir = os.path.dirname(os.path.abspath(json_out))
            os.makedirs(out_dir, exist_ok=True)
            with open(json_out, 'w', encoding='utf-8') as fh:
                json.dump(agg, fh, ensure_ascii=True, indent=2)
        except Exception as exc:
            print(json.dumps({"error": "failed to write json: " + str(exc)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(0)
