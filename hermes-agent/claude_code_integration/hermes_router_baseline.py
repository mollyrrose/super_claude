#!/usr/bin/env python3
"""Generate the smart-router baseline + label-distribution report.

Loads the backfill log (Phase 0) and the forward log (Phase 1), joins
on prompt_hash where possible, and writes a Markdown report to
``~/.claude/.hermes_data/baseline_report.md``.

The dataset is intentionally feature-poor — we only have prompt hashes,
not bodies. That means the report is **label-distribution analytics**,
not a trained-model evaluation. If a future learned router becomes
worth pursuing, this is the report that argues for it (or against).

Usage:
    python hermes_router_baseline.py [--report]
                                     [--backfill PATH] [--forward PATH]
                                     [--out PATH]

Exit codes:
    0 success (always — empty / missing inputs are reported, not raised)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
DEFAULT_BACKFILL = CLAUDE_DIR / ".smart_router_eval_backfill.jsonl"
DEFAULT_FORWARD = CLAUDE_DIR / ".smart_router_eval.jsonl"
DEFAULT_OUT = CLAUDE_DIR / ".hermes_data" / "baseline_report.md"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip():
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return rows


def sha_of(path: Path) -> str:
    if not path.exists():
        return "(missing)"
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return "(unreadable)"
    return h.hexdigest()[:16]


def iso_week(ts: str) -> str:
    try:
        # Handle both Z-terminated and offset forms.
        clean = ts.rstrip("Z")
        # Python's fromisoformat in 3.13 accepts these directly.
        dt = datetime.fromisoformat(clean)
    except (ValueError, TypeError):
        return "?"
    yr, wk, _ = dt.isocalendar()
    return f"{yr}-W{wk:02d}"


def fmt_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return f"| {' | '.join(headers)} |\n| {' | '.join('---' for _ in headers)} |\n| {' | '.join('(none)' for _ in headers)} |\n"
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    sep = "| " + " | ".join("-" * w for w in widths) + " |"
    head = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |"
    body = [
        "| " + " | ".join(r[i].ljust(widths[i]) for i in range(len(headers))) + " |"
        for r in rows
    ]
    return "\n".join([head, sep, *body]) + "\n"


def build_report(
    backfill_rows: list[dict],
    forward_rows: list[dict],
    backfill_path: Path,
    forward_path: Path,
) -> str:
    all_rows = backfill_rows + forward_rows
    total = len(all_rows)
    backfill_count = len(backfill_rows)
    forward_count = len(forward_rows)

    labeled = [r for r in all_rows if r.get("invoked_skill_or_null")]
    labeled_count = len(labeled)

    # Top skills by invocation frequency.
    skill_counter: Counter[str] = Counter()
    for r in labeled:
        s = r.get("invoked_skill_or_null")
        if isinstance(s, str):
            skill_counter[s] += 1

    # Top projects (by prompt volume).
    project_total: Counter[str] = Counter()
    project_labeled: Counter[str] = Counter()
    for r in all_rows:
        p = r.get("project") or "(unknown)"
        project_total[p] += 1
        if r.get("invoked_skill_or_null"):
            project_labeled[p] += 1

    # Per-week volume.
    week_total: Counter[str] = Counter()
    week_labeled: Counter[str] = Counter()
    for r in all_rows:
        wk = iso_week(r.get("ts") or "")
        week_total[wk] += 1
        if r.get("invoked_skill_or_null"):
            week_labeled[wk] += 1

    # Forward-only: regex agreement.
    # We have suggested_skill (from the live router) in forward rows.
    # For each forward row with BOTH a suggestion AND an invocation, did
    # they agree? This is the cheapest possible router-accuracy proxy.
    fwd_with_both = [
        r for r in forward_rows
        if r.get("suggested_skill_or_null") and r.get("invoked_skill_or_null")
    ]
    fwd_with_suggestion_only = [
        r for r in forward_rows
        if r.get("suggested_skill_or_null") and not r.get("invoked_skill_or_null")
    ]
    fwd_with_invocation_only = [
        r for r in forward_rows
        if r.get("invoked_skill_or_null") and not r.get("suggested_skill_or_null")
    ]

    # Cleaning: the router emits "/hunt" with a leading slash; backfill / Skill
    # tool stores "hermes-curate" without one. Normalize for comparison.
    def norm(s: str) -> str:
        return s.lstrip("/").strip().lower()

    agree = sum(
        1 for r in fwd_with_both
        if norm(r["suggested_skill_or_null"]) == norm(r["invoked_skill_or_null"])
    )
    disagree = len(fwd_with_both) - agree

    # Build markdown.
    lines: list[str] = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines.append("# Smart-router baseline + label-distribution report")
    lines.append("")
    lines.append(f"Generated: `{now}`")
    lines.append("")
    lines.append("## Input sources")
    lines.append("")
    lines.append(fmt_table(
        ["File", "Rows", "SHA256[:16]"],
        [
            [str(backfill_path), str(backfill_count), sha_of(backfill_path)],
            [str(forward_path), str(forward_count), sha_of(forward_path)],
        ],
    ))

    lines.append("## Overall counts")
    lines.append("")
    pct = (labeled_count / total * 100.0) if total else 0.0
    lines.append(f"- Total prompts: **{total}**")
    lines.append(f"- Labeled prompts (Skill tool_use invoked in window): **{labeled_count}** ({pct:.2f}%)")
    lines.append("")
    lines.append("Label rate is sparse by design — most skill invocations happen via slash commands ")
    lines.append("(`<command-name>/foo</command-name>`) which we deliberately filter out of this dataset. ")
    lines.append("Those are user-driven routing decisions; this dataset captures **assistant-driven** ")
    lines.append("Skill tool calls, which is the only signal where a learned router could plausibly add value.")
    lines.append("")

    lines.append("## Top skills (assistant-invoked)")
    lines.append("")
    rows = [[s, str(c)] for s, c in skill_counter.most_common(20)]
    lines.append(fmt_table(["Skill", "Count"], rows))

    lines.append("## Top projects (by prompt volume)")
    lines.append("")
    rows = []
    for p, n in project_total.most_common(15):
        labeled_n = project_labeled.get(p, 0)
        rate = (labeled_n / n * 100.0) if n else 0.0
        rows.append([p, str(n), str(labeled_n), f"{rate:.2f}%"])
    lines.append(fmt_table(["Project", "Prompts", "Labeled", "Label rate"], rows))

    lines.append("## Volume per ISO week (last 12 weeks)")
    lines.append("")
    weeks_sorted = sorted(week_total.keys(), reverse=True)[:12]
    rows = [[w, str(week_total[w]), str(week_labeled.get(w, 0))] for w in weeks_sorted]
    lines.append(fmt_table(["Week", "Prompts", "Labeled"], rows))

    lines.append("## Regex baseline accuracy (forward subset)")
    lines.append("")
    lines.append(f"- Forward rows with both suggestion and invocation: **{len(fwd_with_both)}**")
    lines.append(f"- Forward rows with suggestion but no invocation: **{len(fwd_with_suggestion_only)}**")
    lines.append(f"- Forward rows with invocation but no suggestion (router missed it): **{len(fwd_with_invocation_only)}**")
    if fwd_with_both:
        acc = agree / len(fwd_with_both) * 100.0
        lines.append("")
        lines.append(f"Among the rows where both are present, the regex router suggestion matched ")
        lines.append(f"the actual Skill invocation **{agree} / {len(fwd_with_both)} times ({acc:.1f}%)**.")
    else:
        lines.append("")
        lines.append("**Not enough forward rows with both fields to compute regex accuracy yet** ")
        lines.append("— this metric stabilises only after several weeks of forward logging.")
    lines.append("")

    lines.append("## Learnability note (the genuine trade-off)")
    lines.append("")
    lines.append("This dataset is **label-rich but feature-poor by design**. We store only the SHA-256 ")
    lines.append("prefix of each prompt — no body, no embeddings. That means the dataset is suitable for:")
    lines.append("")
    lines.append("- label-distribution analytics (which skills get invoked, by which projects, over time)")
    lines.append("- regex-router agreement analysis (where suggestion and invocation overlap)")
    lines.append("- volume / cadence trends")
    lines.append("")
    lines.append("It is **NOT** suitable for training a prompt-to-skill classifier — you can't featurize ")
    lines.append("a hash. To train a learned router (FabricPC PCN, small transformer, or even logistic ")
    lines.append("regression over sentence embeddings), a separate decision is needed about feature ")
    lines.append("logging: either an opt-in body store, or a small sentence-embedding logged at hook time. ")
    lines.append("That trade-off should be made deliberately, not by accident.")
    lines.append("")
    lines.append("If, after reading the volume + agreement numbers above, the regex baseline already ")
    lines.append("explains most of the assistant-invocation pattern, **no learned router is needed** ")
    lines.append("— rules are enough. If the volume is high and the regex misses a lot of invocations, ")
    lines.append("that's the empirical case for the next plan (Phase 3) to grapple with.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate router baseline + label-distribution report.")
    ap.add_argument("--report", action="store_true", help="Write the report (default action).")
    ap.add_argument("--backfill", type=Path, default=DEFAULT_BACKFILL)
    ap.add_argument("--forward", type=Path, default=DEFAULT_FORWARD)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    backfill_rows = load_jsonl(args.backfill)
    forward_rows = load_jsonl(args.forward)

    text = build_report(backfill_rows, forward_rows, args.backfill, args.forward)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(
        f"[baseline] backfill_rows={len(backfill_rows)} forward_rows={len(forward_rows)} "
        f"report={args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
