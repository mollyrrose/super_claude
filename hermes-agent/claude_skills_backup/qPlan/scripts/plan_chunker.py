"""Shared plan-chunking helpers for qPlan's cross-model critics.

Both openai_critic.py and deepseek_critic.py import from this module so
that a fix to the splitting/merging logic applies to both at once.
Stdlib-only by design; lives in the same directory as the importing
scripts so the relative import works without sys.path manipulation.

Public API:
- MAX_CHUNK_DEPTH : int
- VERDICT_SEVERITY : dict[str, int]   # worst -> best
- split_plan(plan: str) -> list[str]
- merge_verdicts(sub_verdicts: list[dict]) -> dict

Both critics also need their own provider-specific call_*() wrapper that
handles the actual HTTP request and decides when to invoke this module
(typically on HTTP 429 with depth < MAX_CHUNK_DEPTH).
"""

# Maximum recursion depth for chunked retry. depth=4 fans a single huge
# plan out to at most 16 sub-requests, which is the most we'll burn on
# one critic round before failing loud. Bump this only if you also wire
# in MAX_TOTAL_CHUNKS in the caller (see openai_critic.py for the
# pattern) so we don't accidentally explode billing on a pathological
# 429 storm.
MAX_CHUNK_DEPTH = 4

# Worst-to-best severity order. Used by merge_verdicts to promote a
# unified verdict to the most severe verdict any sub-chunk returned.
VERDICT_SEVERITY = {
    "major issue": 0,
    "minor issue": 1,
    "no material issue": 2,
}


def split_plan(plan: str) -> list[str]:
    """Split a plan in half on the most natural boundary available.

    Preference order:
      1. Top-level Markdown headers (lines starting with `## `).
      2. Sub-section headers (`### `).
      3. Blank-line paragraph boundaries near the middle.
      4. Line-count halve (last resort).

    Returns [plan] when the plan is genuinely atomic (one line or less).
    Returns [left, right] otherwise. Callers check len(parts) >= 2
    before recursing.
    """
    lines = plan.splitlines(keepends=True)

    # Atomic plan — no split possible. Hoisted to the top so 2-3 line
    # plans don't fall through to paragraph-detection that requires >=4
    # lines and then silently return [plan] from a different branch.
    if len(lines) <= 1:
        return [plan]

    for prefix in ("## ", "### "):
        starts = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
        if len(starts) >= 2:
            mid_idx = starts[len(starts) // 2]
            return ["".join(lines[:mid_idx]), "".join(lines[mid_idx:])]

    # Paragraph break — search outward from the middle for a blank line.
    if len(lines) >= 4:
        mid = len(lines) // 2
        for offset in range(0, mid):
            for sign in (-1, 1):
                idx = mid + sign * offset
                if 0 < idx < len(lines) and lines[idx].strip() == "":
                    return ["".join(lines[:idx]), "".join(lines[idx:])]

    # Last resort: split by line count. Works for 2-line and up.
    mid = len(lines) // 2
    return ["".join(lines[:mid]), "".join(lines[mid:])]


def merge_verdicts(sub_verdicts: list[dict]) -> dict:
    """Merge findings from N chunk-verdicts.

    - Concatenate suggestions across chunks; dedupe by exact-text match.
    - Promote the unified verdict tier to the worst sub-verdict tier
      (`major issue` > `minor issue` > `no material issue`).
    - Tracks total chunks submitted under `_chunks_submitted` so the
      caller can surface the count in its public output.
    """
    seen_texts: set = set()
    suggestions: list = []
    worst = 2  # default: no material issue
    for sub in sub_verdicts:
        sub_score = VERDICT_SEVERITY.get(sub.get("verdict", "no material issue"), 2)
        if sub_score < worst:
            worst = sub_score
        for s in sub.get("suggestions", []) or []:
            text = s.get("text", "").strip()
            if not text or text in seen_texts:
                continue
            seen_texts.add(text)
            suggestions.append(s)
    # Renamed the inner generator variable from `v` to `score` to avoid
    # shadowing any outer loop variable (was flagged as P2 in the qRev
    # review).
    verdict_str = next(k for k, score in VERDICT_SEVERITY.items() if score == worst)
    return {"verdict": verdict_str, "suggestions": suggestions}
