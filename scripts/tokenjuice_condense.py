#!/usr/bin/env python3
"""tokenjuice_condense.py -- structure-aware condenser for big blobs.

WHAT THIS IS
------------
A deterministic, stdlib-only condenser for LARGE tool-output blobs (JSON dumps,
source code, build/test logs, long prose) that preserves the STRUCTURE the
model needs to navigate the content while squeezing the bulk:

  - JSON : every key, bracket, colon, comma, boolean, null and short/ID-like
           value survives; long string values are squeezed. The model still
           sees the full schema.
  - code : import lines and function/class signatures survive; bodies are
           squeezed. The model still sees the full API surface.
  - log  : errors, failures, warnings (deduped), stack traces and summary
           lines survive with context; INFO/DEBUG noise is dropped with an
           omission note.
  - text : high-entropy words (API keys, UUIDs, hashes -- length >= 20)
           survive; the rest is squeezed head+tail.

Content type is auto-detected with cheap heuristics (JSON parse, code/log
indicator scans) -- no ML, no network, no non-stdlib import.

PROVENANCE / ATTRIBUTION
------------------------
The structure-mask design and the JSON/code/log preservation policies are
ported (with simplifications) from chopratejas/headroom, Apache License 2.0:
    headroom/compression/masks.py                (StructureMask, entropy mask)
    headroom/compression/handlers/json_handler.py (JSON tokenizer + policy)
    headroom/compression/handlers/code_handler.py (regex signature fallback)
    headroom/compression/detector.py              (FallbackDetector heuristics)
    headroom/transforms/log_compressor.py         (log scoring + selection)
Deliberate simplifications vs upstream: no Magika ML detection, no
tree-sitter AST path (regex fallback only), no Rust text crusher, no CCR
retrieval store, no adaptive Kneedle sizing (fixed caps instead). Everything
here is pure stdlib so it can never add a dependency to the hook layer.
The upstream package itself is NOT installed (its plugin/proxy layer was
security-reviewed and rejected); only the audited compression logic was
ported. See okf/ai-radar/agent-tooling/headroom.md for the audit trail.

USAGE
-----
    python tokenjuice_condense.py < blob.txt            # auto-detect, condense
    python tokenjuice_condense.py --file big.json
    python tokenjuice_condense.py --type code < foo.py
    some-cmd | python tokenjuice_condense.py --json     # stat footer on stderr

Also used by tokenjuice.py as the `condense` strategy (lazy import; if this
file is missing the strategy is a silent no-op).

KILL SWITCH: TOKENJUICE_DISABLE=1 (honored by the CLI here too) -> pass-through.
Dependencies: none (standard library only). ASCII-only output markers.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter

# ----------------------------------------------------------------------------
# Tunables (mirror upstream defaults where they exist)
# ----------------------------------------------------------------------------

MIN_CONTENT_LENGTH = 100        # below this, return unchanged
CONDENSE_MAX_BYTES = 10_000_000  # above this, return unchanged (mask alloc is ~9x input)
MIN_SPAN_TO_SQUEEZE = 50        # only squeeze compressible spans longer than this
SQUEEZE_RATIO = 0.3             # target fraction kept inside a squeezed span
ENTROPY_THRESHOLD = 0.85        # normalized Shannon entropy floor for "secret-like"
SECRET_ENTROPY_MIN_LENGTH = 20  # matches trufflehog/detect-secrets length floor

# JSON policy (upstream JSONStructureHandler defaults)
JSON_SHORT_VALUE_MAX = 20       # string values this short are preserved
JSON_NUMBER_MAX_DIGITS = 10     # numbers up to this many chars are preserved
JSON_ARRAY_ITEMS_FULL = 3       # array items after this index squeeze harder

# Log policy (upstream LogCompressorConfig defaults, minus adaptive sizing)
LOG_MAX_ERRORS = 10
LOG_CONTEXT_LINES = 3
LOG_MAX_STACK_TRACES = 3
LOG_STACK_TRACE_MAX_LINES = 20
LOG_MAX_WARNINGS = 5
LOG_MAX_TOTAL_LINES = 100

SQUEEZE_MARKER = " ...[condensed %d chars]... "


# ----------------------------------------------------------------------------
# Entropy scoring (port of masks.EntropyScore + compute_entropy_mask_for_content)
# ----------------------------------------------------------------------------

def _normalized_entropy(text):
    """Shannon entropy of the character distribution, normalized to 0..1."""
    if not text:
        return 0.0
    counter = Counter(text)
    total = len(text)
    entropy = 0.0
    for count in counter.values():
        p = count / total
        entropy -= p * math.log2(p)
    max_entropy = math.log2(len(counter)) if len(counter) > 1 else 1.0
    return entropy / max_entropy if max_entropy > 0 else 0.0


def _entropy_word_spans(content, threshold=ENTROPY_THRESHOLD,
                        min_len=SECRET_ENTROPY_MIN_LENGTH):
    """Character index ranges of high-entropy words (API keys, UUIDs, hashes).

    Word-level (not char-level) scoring: single characters never reach the
    length floor, so scoring words and mapping back to character positions is
    what makes entropy preservation actually fire (upstream lesson).
    """
    spans = []
    for match in re.finditer(r"\S+", content):
        word = match.group()
        if len(word) < min_len:
            continue
        if _normalized_entropy(word) >= threshold:
            spans.append((match.start(), match.end()))
    return spans


def _mark(mask, start, end):
    for i in range(max(0, start), min(end, len(mask))):
        mask[i] = True


# ----------------------------------------------------------------------------
# Content-type detection (port of detector.FallbackDetector, log check first)
# ----------------------------------------------------------------------------

_CODE_INDICATORS = ("def ", "class ", "function ", "import ", "const ",
                    "let ", "var ", "func ", "fn ", "pub ", "package ",
                    "struct ", "interface ")
_LOG_LEVEL_RE = re.compile(
    r"\b(?:ERROR|error|Error|FATAL|fatal|Fatal|CRITICAL|critical"
    r"|FAIL|FAILED|fail|failed|Fail|Failed"
    r"|WARN|WARNING|warn|warning|Warn|Warning"
    r"|INFO|info|Info|DEBUG|debug|Debug|TRACE|trace|Trace)\b")


def detect_content_type(content):
    """Return one of: json | code | log | text. Cheap heuristics, no deps.

    Deviation from upstream FallbackDetector: logs are checked BEFORE code
    with a line-ratio heuristic, because build/test logs routinely contain
    the word `import` and would otherwise misroute to the code handler.
    """
    stripped = content.strip()
    if not stripped:
        return "text"

    if stripped.startswith(("{", "[")):
        # full json.loads on a multi-MB blob is O(n) time + a full parse
        # tree; above the cap trust the start character (the JSON mask
        # tokenizer tolerates invalid JSON anyway)
        if len(stripped) > 1_000_000:
            return "json"
        try:
            json.loads(stripped)
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass

    lines = content.split("\n")
    if len(lines) >= 5:
        level_hits = sum(1 for ln in lines if _LOG_LEVEL_RE.search(ln))
        if level_hits >= 3 and level_hits / len(lines) >= 0.15:
            return "log"

    if any(ind in content for ind in _CODE_INDICATORS):
        return "code"

    if _LOG_LEVEL_RE.search(content):
        return "log"

    return "text"


# ----------------------------------------------------------------------------
# Span squeeze (port of UniversalCompressor._simple_compress)
# ----------------------------------------------------------------------------

def _squeeze(text, ratio=SQUEEZE_RATIO):
    """Keep head 2/3 + tail 1/3 of the target length; single-line marker so a
    squeeze inside a JSON string value cannot produce invalid JSON."""
    target = int(len(text) * ratio)
    if len(text) <= target or target <= 0:
        return text
    keep_start = target * 2 // 3
    keep_end = target // 3
    dropped = len(text) - keep_start - keep_end
    tail = text[-keep_end:] if keep_end > 0 else ""
    return text[:keep_start] + (SQUEEZE_MARKER % dropped) + tail


def _apply_mask(content, mask, ratio=SQUEEZE_RATIO):
    """Squeeze every contiguous non-preserved span longer than the floor."""
    out = []
    i = 0
    n = len(content)
    while i < n:
        j = i
        preserved = mask[i]
        while j < n and mask[j] == preserved:
            j += 1
        span = content[i:j]
        if preserved or len(span) <= MIN_SPAN_TO_SQUEEZE:
            out.append(span)
        else:
            out.append(_squeeze(span, ratio))
        i = j
    return "".join(out)


# ----------------------------------------------------------------------------
# JSON structure mask (port of JSONStructureHandler)
# ----------------------------------------------------------------------------

def _json_mask(content):
    """Character mask: True = preserve. Keys, syntax, booleans, nulls, short
    numbers and short/high-entropy string values are preserved; long values
    (and values deep in arrays past the first few items) are compressible."""
    mask = [False] * len(content)
    i = 0
    n = len(content)
    expect_key = False
    container_stack = []   # "{" or "["
    array_item_stack = []  # item index per open array

    def cur_array_index():
        return array_item_stack[-1] if array_item_stack else 0

    while i < n:
        ch = content[i]

        if ch in " \t\n\r":
            i += 1
            continue

        if ch in "{}[]":
            mask[i] = True
            if ch == "{":
                container_stack.append("{")
                expect_key = True
            elif ch == "}":
                if container_stack and container_stack[-1] == "{":
                    container_stack.pop()
                expect_key = False
            elif ch == "[":
                container_stack.append("[")
                array_item_stack.append(0)
                expect_key = False
            elif ch == "]":
                if container_stack and container_stack[-1] == "[":
                    container_stack.pop()
                    if array_item_stack:
                        array_item_stack.pop()
            i += 1
            continue

        if ch == ":":
            mask[i] = True
            expect_key = False
            i += 1
            continue

        if ch == ",":
            mask[i] = True
            if container_stack and container_stack[-1] == "[" and array_item_stack:
                array_item_stack[-1] += 1
            if container_stack and container_stack[-1] == "{":
                expect_key = True
            i += 1
            continue

        if ch == '"':
            start = i
            i += 1
            while i < n and content[i] != '"':
                if content[i] == "\\":
                    i = min(i + 2, n)  # clamp: trailing backslash at EOF
                else:
                    i += 1
            i += 1  # include closing quote
            # key or value? look ahead for a colon
            j = i
            while j < n and content[j] in " \t\n\r":
                j += 1
            is_key = j < n and content[j] == ":" and expect_key
            if is_key:
                _mark(mask, start, i)
                expect_key = False
            else:
                # payload between the quotes (not .strip('"'): thresholds
                # apply to the value, and strip would eat escaped quotes)
                value = content[start + 1:i - 1] if i - start >= 2 else ""
                preserve = False
                if array_item_stack and cur_array_index() >= JSON_ARRAY_ITEMS_FULL:
                    preserve = False  # deep in an array: squeeze harder
                elif len(value) <= JSON_SHORT_VALUE_MAX:
                    preserve = True
                elif " " not in value and _normalized_entropy(value) >= ENTROPY_THRESHOLD:
                    preserve = True  # identifier-shaped (UUID/hash/key)
                if preserve:
                    _mark(mask, start, i)
            continue

        if ch in "-0123456789":
            start = i
            if ch == "-":
                i += 1
            while i < n and content[i] in "0123456789":
                i += 1
            if i < n and content[i] == ".":
                i += 1
                while i < n and content[i] in "0123456789":
                    i += 1
            if i < n and content[i] in "eE":
                i += 1
                if i < n and content[i] in "+-":
                    i += 1
                while i < n and content[i] in "0123456789":
                    i += 1
            if i - start <= JSON_NUMBER_MAX_DIGITS:
                _mark(mask, start, i)
            continue

        matched = False
        for lit in ("true", "false", "null"):
            if content[i:i + len(lit)] == lit:
                _mark(mask, i, i + len(lit))
                i += len(lit)
                matched = True
                break
        if matched:
            continue

        i += 1

    return mask


# ----------------------------------------------------------------------------
# Code structure mask (port of CodeStructureHandler regex fallback)
# ----------------------------------------------------------------------------

_SIGNATURE_PATTERNS = {
    "python": [
        re.compile(r"^[ \t]*(async\s+)?def\s+\w+\s*\([^)]*\)\s*(->\s*[^:]+)?:", re.M),
        re.compile(r"^[ \t]*class\s+\w+(\([^)]*\))?:", re.M),
        re.compile(r"^[ \t]*@\w+(\([^)]*\))?\s*$", re.M),
    ],
    "javascript": [
        re.compile(r"^[ \t]*(async\s+)?function\s+\w+\s*\([^)]*\)", re.M),
        re.compile(r"^[ \t]*class\s+\w+(\s+extends\s+\w+)?", re.M),
        re.compile(r"^[ \t]*(const|let|var)\s+\w+\s*=\s*(async\s+)?\([^)]*\)\s*=>", re.M),
    ],
    "typescript": [
        re.compile(r"^[ \t]*(async\s+)?function\s+\w+\s*(<[^>]+>)?\s*\([^)]*\)", re.M),
        re.compile(r"^[ \t]*class\s+\w+(<[^>]+>)?(\s+extends\s+\w+)?", re.M),
        re.compile(r"^[ \t]*interface\s+\w+(<[^>]+>)?", re.M),
        re.compile(r"^[ \t]*type\s+\w+(<[^>]+>)?\s*=", re.M),
    ],
    "go": [
        re.compile(r"^[ \t]*func\s+(\([^)]+\)\s+)?\w+\s*\([^)]*\)", re.M),
        re.compile(r"^[ \t]*type\s+\w+\s+(struct|interface)", re.M),
    ],
    "rust": [
        re.compile(r"^[ \t]*(pub\s+)?(async\s+)?fn\s+\w+\s*(<[^>]+>)?\s*\([^)]*\)", re.M),
        re.compile(r"^[ \t]*(pub\s+)?struct\s+\w+", re.M),
        re.compile(r"^[ \t]*(pub\s+)?enum\s+\w+", re.M),
        re.compile(r"^[ \t]*(pub\s+)?trait\s+\w+", re.M),
        re.compile(r"^[ \t]*impl(<[^>]+>)?\s+\w+", re.M),
    ],
    "java": [
        re.compile(r"^[ \t]*(public|private|protected)?\s*(static\s+)?\w+\s+\w+\s*\([^)]*\)", re.M),
        re.compile(r"^[ \t]*(public\s+)?(class|interface|enum)\s+\w+", re.M),
        re.compile(r"^[ \t]*@\w+(\([^)]*\))?\s*$", re.M),
    ],
}

_IMPORT_PATTERNS = {
    "python": re.compile(r"^[ \t]*(import\s+\w+|from\s+\w+\s+import)", re.M),
    "javascript": re.compile(r"^[ \t]*(import\s+.*from|require\s*\()", re.M),
    "typescript": re.compile(r"^[ \t]*(import\s+.*from|require\s*\()", re.M),
    "go": re.compile(r'^\s*import\s+(\(|")', re.M),
    "rust": re.compile(r"^[ \t]*use\s+\w+", re.M),
    "java": re.compile(r"^[ \t]*import\s+[\w.]+;", re.M),
}

_LANGUAGE_MARKERS = {
    "python": ["def ", "import ", "from ", "class ", "async def"],
    "javascript": ["function ", "const ", "let ", "var ", "=>"],
    "typescript": ["interface ", "type ", ": string", ": number"],
    "go": ["func ", "package ", "import (", "type "],
    "rust": ["fn ", "let mut", "impl ", "pub fn", "use "],
    "java": ["public class", "private ", "protected ", "void "],
}


def _detect_language(content):
    scores = {lang: sum(1 for p in pats if p in content)
              for lang, pats in _LANGUAGE_MARKERS.items()}
    if not scores or max(scores.values()) == 0:
        return "python"
    return max(scores, key=lambda k: scores[k])


def _code_mask(content, language=None):
    """Character mask preserving import lines and signatures (whole line)."""
    if language is None:
        language = _detect_language(content)
    mask = [False] * len(content)

    imp = _IMPORT_PATTERNS.get(language)
    if imp:
        for match in imp.finditer(content):
            end = content.find("\n", match.end())
            if end == -1:
                end = len(content)
            _mark(mask, match.start(), end)

    for pattern in _SIGNATURE_PATTERNS.get(language, []):
        for match in pattern.finditer(content):
            _mark(mask, match.start(), match.end())

    return mask


# ----------------------------------------------------------------------------
# Log condenser (port of LogCompressor's Python selection logic, fixed caps)
# ----------------------------------------------------------------------------

_LEVEL_PATTERNS = [
    ("error", re.compile(r"\b(?:ERROR|error|Error|FATAL|fatal|Fatal|CRITICAL|critical)\b")),
    ("fail", re.compile(r"\b(?:FAIL|FAILED|fail|failed|Fail|Failed)\b")),
    ("warn", re.compile(r"\b(?:WARN|WARNING|warn|warning|Warn|Warning)\b")),
    ("info", re.compile(r"\b(?:INFO|info|Info)\b")),
    ("debug", re.compile(r"\b(?:DEBUG|debug|Debug)\b")),
    ("trace", re.compile(r"\b(?:TRACE|trace|Trace)\b")),
]
_STACK_TRACE_PATTERNS = [
    re.compile(r"^[ \t]*Traceback \(most recent call last\)"),
    re.compile(r'^\s*File ".+", line \d+'),
    re.compile(r"^[ \t]*at [^(\n]+\([^()\n]*:\d+:\d+\)"),
    re.compile(r"^[ \t]+at [\w.$]+\("),
    re.compile(r"^[ \t]*--> .+:\d+:\d+"),
    re.compile(r"^[ \t]*\d+:\s+0x[0-9a-f]+"),
]
_SUMMARY_PATTERNS = [
    re.compile(r"^={3,}"),
    re.compile(r"^-{3,}"),
    re.compile(r"^\d+ (passed|failed|skipped|error|warning)"),
    re.compile(r"^(?:Tests?|Suites?):?\s+\d+"),
    re.compile(r"^(?:TOTAL|Total|Summary)"),
    re.compile(r"^(?:Build|Compile|Test).*(?:succeeded|failed|complete)"),
]
_LEVEL_SCORES = {"error": 1.0, "fail": 1.0, "warn": 0.5, "info": 0.1,
                 "debug": 0.05, "trace": 0.02, "unknown": 0.1}


def _dedupe_similar_lines(indexed_lines):
    """Conservative dedupe: keep the message prefix, normalize only the
    trailing variable region (digits, hex, paths) after the first `:`/`=`."""
    digit_re = re.compile(r"\d+")
    hex_re = re.compile(r"0x[0-9a-fA-F]+")
    path_re = re.compile(r"/[\w/]+/")
    seen = set()
    deduped = []
    for idx, content in indexed_lines:
        split_at = next((k for k, c in enumerate(content) if c in (":", "=")),
                        len(content))
        prefix = content[:split_at]
        suffix = content[split_at:]
        suffix = digit_re.sub("N", suffix)
        suffix = hex_re.sub("ADDR", suffix)
        suffix = path_re.sub("/PATH/", suffix)
        normalized = prefix + suffix
        if normalized not in seen:
            seen.add(normalized)
            deduped.append((idx, content))
    return deduped


def condense_log(content):
    """Line-based log condense: keep errors/fails (first+last+highest scored),
    deduped warnings, stack traces, summary lines, plus context lines; drop
    the rest with an omission note."""
    lines = content.split("\n")
    n = len(lines)

    levels = []
    is_stack = [False] * n
    is_summary = [False] * n
    in_stack = False
    stack_len = 0
    for i, line in enumerate(lines):
        level = "unknown"
        for name, pattern in _LEVEL_PATTERNS:
            if pattern.search(line):
                level = name
                break
        levels.append(level)
        for pattern in _STACK_TRACE_PATTERNS:
            if pattern.search(line):
                # a frame line EXTENDS an open trace; only a fresh trace
                # resets the length counter, so the max-lines cap can fire
                if not in_stack:
                    stack_len = 0
                in_stack = True
                break
        if in_stack:
            is_stack[i] = True
            stack_len += 1
            if stack_len > LOG_STACK_TRACE_MAX_LINES or not line.strip():
                in_stack = False
        for pattern in _SUMMARY_PATTERNS:
            if pattern.search(line):
                is_summary[i] = True
                break

    def score(i):
        s = _LEVEL_SCORES.get(levels[i], 0.1)
        if is_stack[i]:
            s += 0.3
        if is_summary[i]:
            s += 0.4
        return min(1.0, s)

    def first_last_top(indices, cap):
        if len(indices) <= cap:
            return list(indices)
        if cap <= 0:
            return []
        if cap == 1:
            return [indices[0]]
        picked = [indices[0], indices[-1]]
        remaining = cap - 2
        if remaining > 0:
            middle = sorted((i for i in indices[1:-1]),
                            key=lambda i: score(i), reverse=True)
            picked.extend(middle[:remaining])
        return picked

    errors = [i for i in range(n) if levels[i] == "error"]
    fails = [i for i in range(n) if levels[i] == "fail"]
    warns = [(i, lines[i]) for i in range(n) if levels[i] == "warn"]

    stacks = []
    current = []
    for i in range(n):
        if is_stack[i]:
            current.append(i)
        elif current:
            stacks.append(current)
            current = []
    if current:
        stacks.append(current)

    selected = set()
    selected.update(first_last_top(errors, LOG_MAX_ERRORS))
    selected.update(first_last_top(fails, LOG_MAX_ERRORS))
    for i, _line in _dedupe_similar_lines(warns)[:LOG_MAX_WARNINGS]:
        selected.add(i)
    for stack in stacks[:LOG_MAX_STACK_TRACES]:
        selected.update(stack[:LOG_STACK_TRACE_MAX_LINES])
    selected.update(i for i in range(n) if is_summary[i])

    # context lines around every selected line
    with_context = set(selected)
    for idx in selected:
        for k in range(max(0, idx - LOG_CONTEXT_LINES),
                       min(n, idx + LOG_CONTEXT_LINES + 1)):
            with_context.add(k)

    picked = sorted(with_context)
    if len(picked) > LOG_MAX_TOTAL_LINES:
        picked = sorted(picked, key=lambda i: score(i), reverse=True)
        picked = sorted(picked[:LOG_MAX_TOTAL_LINES])

    out = [lines[i] for i in picked]
    omitted = n - len(picked)
    if omitted > 0:
        picked_set = set(picked)
        stats = Counter(levels[i] for i in range(n) if i not in picked_set)
        parts = ["%d %s" % (stats[k], k.upper())
                 for k in ("error", "fail", "warn", "info") if stats.get(k)]
        note = "[%d lines omitted%s]" % (
            omitted, (": " + ", ".join(parts)) if parts else "")
        out.append(note)
    return "\n".join(out)


# ----------------------------------------------------------------------------
# Main entry
# ----------------------------------------------------------------------------

def condense(content, content_type=None, ratio=SQUEEZE_RATIO):
    """Condense a blob, preserving its structure. Returns (text, meta dict).

    content_type: json | code | log | text | None (auto-detect).
    Never raises: any internal failure returns the input unchanged.
    """
    meta = {"content_type": "unknown", "skipped": None}
    try:
        if not content or len(content) < MIN_CONTENT_LENGTH:
            meta["content_type"] = content_type or "unknown"
            meta["skipped"] = "too short"
            return content, meta
        if len(content) > CONDENSE_MAX_BYTES:
            meta["content_type"] = content_type or "unknown"
            meta["skipped"] = "too large"
            return content, meta

        ctype = content_type or detect_content_type(content)
        meta["content_type"] = ctype

        if ctype == "log":
            out = condense_log(content)
            if len(out) >= len(content):
                meta["skipped"] = "no gain"
                return content, meta
            return out, meta

        if ctype == "json":
            mask = _json_mask(content)
        elif ctype == "code":
            mask = _code_mask(content)
        else:
            mask = [False] * len(content)

        # union with entropy preservation (secrets / UUIDs / hashes survive)
        for start, end in _entropy_word_spans(content):
            _mark(mask, start, end)

        out = _apply_mask(content, mask, ratio)
        # never emit MORE than came in (markers can inflate tiny spans)
        if len(out) >= len(content):
            meta["skipped"] = "no gain"
            return content, meta
        return out, meta
    except Exception as exc:  # noqa: BLE001 -- condense must never lose output
        meta["skipped"] = "error: %s" % exc.__class__.__name__
        return content, meta


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def _reconfigure_utf8():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main(argv=None):
    _reconfigure_utf8()
    p = argparse.ArgumentParser(
        description="Structure-aware condenser for big blobs (JSON/code/log/text).")
    p.add_argument("--file", default=None, help="Read this file instead of stdin.")
    p.add_argument("--type", dest="ctype", default=None,
                   choices=["json", "code", "log", "text"],
                   help="Force content type (default: auto-detect).")
    p.add_argument("--ratio", type=float, default=SQUEEZE_RATIO,
                   help="Target keep-fraction inside squeezed spans (default 0.3).")
    p.add_argument("--json", action="store_true",
                   help="Machine-readable stat line on stderr.")
    p.add_argument("--quiet", action="store_true",
                   help="Suppress the savings footer on stderr.")
    args = p.parse_args(argv)

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
                original = fh.read()
        except OSError as exc:
            sys.stderr.write("[condense] cannot read %s: %s\n" % (args.file, exc))
            return 2
    else:
        try:
            original = sys.stdin.read()
        except OSError as exc:
            sys.stderr.write("[condense] cannot read stdin: %s\n" % exc)
            return 2

    if os.environ.get("TOKENJUICE_DISABLE") == "1":
        sys.stdout.write(original)
        return 0

    out, meta = condense(original, content_type=args.ctype, ratio=args.ratio)
    sys.stdout.write(out)
    if out and not out.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()

    o, c = len(original), len(out)
    if args.json:
        sys.stderr.write(json.dumps({
            "content_type": meta["content_type"], "skipped": meta["skipped"],
            "chars_in": o, "chars_out": c,
            "pct_saved": round((1 - c / o) * 100, 1) if o else 0.0,
        }) + "\n")
    elif not args.quiet and o:
        sys.stderr.write("[condense] %s: saved %.1f%% (%d -> %d chars)\n" % (
            meta["content_type"], (1 - c / o) * 100 if o else 0.0, o, c))
    sys.stderr.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
