"""Smart-router rules: classify a user prompt into a skill suggestion.

Pure-Python, stdlib only. No LLM call — the router has to be cheap because
it runs in a UserPromptSubmit hook on every prompt.

Each rule is a function that takes the prompt text and returns either a
Suggestion or None. Rules are evaluated in priority order (most specific
first); the first match wins.

The router is intentionally conservative:
  - returns None for short prompts (< 4 words)
  - returns None when the user has already invoked an explicit slash
    command (their choice stands)
  - returns None for anything that doesn't unambiguously match one rule

False positives waste context budget and erode trust in the hint, so the
bar is high. Zero suggestions for a session is an acceptable outcome.

Skill choices are pinned to the user's installed skills, and reflect the
user's correction (2026-06-05): `/qMin` is NOT routed because it already
runs automatically after every session; "review" maps to `/rev` (sprint-
close multi-agent audit); pre-release / pre-merge maps to `/check`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass(frozen=True)
class Suggestion:
    skill: str  # canonical name with leading slash, e.g. "/think"
    why: str    # one-line explanation surfaced to the model


def _has_slash_command(text: str) -> bool:
    return bool(re.match(r"^\s*/[\w:-]+", text))


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _matches_any(text_lc: str, patterns: List[str]) -> bool:
    return any(re.search(p, text_lc) for p in patterns)


# ── Rules ──────────────────────────────────────────────────────────────


def _rule_bug(text_lc: str) -> Optional[Suggestion]:
    patterns = [
        r"\btraceback\b",
        r"\bstack trace\b",
        r"\b(error|exception|crash(?:ed|ing)?|broke|broken)\b",
        r"\bnem (működik|jó|fut|megy)\b",
        r"\b(regression|regressed)\b",
        r"\bused to work\b",
        r"\bwhy (?:is|isn?t|does)\b.{0,40}\b(broken|failing|crashing)\b",
        r"\bfails?\b.{0,30}\bwith\b",
        r"\bbug\b.{0,30}\b(in|with|on)\b",
    ]
    if _matches_any(text_lc, patterns):
        return Suggestion(
            "/hunt",
            "looks like a bug / regression report — /hunt finds the root cause before fixing",
        )
    return None


def _rule_release_check(text_lc: str) -> Optional[Suggestion]:
    patterns = [
        r"\b(?:before|ready to) (?:merge|release|publish|ship)\b",
        r"\bpr (?:ready|review)\b",
        r"\bclose (?:this|the) issue\b",
        r"\brelease (?:reaction|notes)\b",
        r"\bpublish (?:this|the)\b",
        r"\bbefore commit(?:ing|ting)?\b",
        r"\bnyomható\b",
        r"\bkiadás (?:előtt|kész)\b",
    ]
    if _matches_any(text_lc, patterns):
        return Suggestion(
            "/check",
            "looks like a release / PR / pre-merge check — /check reviews diffs against project constraints",
        )
    return None


def _rule_sprint_audit(text_lc: str) -> Optional[Suggestion]:
    patterns = [
        r"\breview (?:my )?(?:code|changes|branch|the (?:repo|project|whole)|everything)\b",
        r"\breview (?:this|that|it)\b",
        r"\baudit\b",
        r"\bsprint (?:close|review|end)\b",
        r"\bgo through (?:everything|the whole)\b",
        r"\bnézd át\b",
        r"\b(átnézés|átnézel|átnézed)\b",
        r"^\s*review\s*$",
        r"\b(review my code|code review|code-review)\b",
    ]
    if _matches_any(text_lc, patterns):
        return Suggestion(
            "/rev",
            "looks like an audit / sprint-close review — /rev launches 12-15 specialist agents in parallel",
        )
    return None


def _rule_research(text_lc: str) -> Optional[Suggestion]:
    patterns = [
        r"\bdeep[-\s]?dive\b",
        r"\bresearch (?:the|this|how|why)\b",
        r"\bhelp me understand\b",
        r"\b(study|learn about|tanuld? meg|értsd? meg)\b",
        r"\bmélyebben\b",
        r"\b(literature review|state of the art)\b",
    ]
    if _matches_any(text_lc, patterns) and _word_count(text_lc) >= 6:
        return Suggestion(
            "/learn",
            "looks like a research / deep-dive request — /learn runs the six-phase research workflow",
        )
    return None


def _rule_design(text_lc: str) -> Optional[Suggestion]:
    patterns = [
        r"\bhow should (?:i|we)\b",
        r"\bhow do (?:we|i) (?:design|architect|approach|structure)\b",
        r"\bwhat['’]?s the best (?:approach|way|design)\b",
        r"\bplan (?:this|out|the)\b",
        r"\bshould (?:i|we) (?:use|build|keep|remove|drop|switch|migrate)\b",
        r"\bis it worth\b",
        r"\b(compare|comparison|alternatives?|trade[-\s]?offs?)\b",
        r"\bdesign (?:the|a) (?:new|next)\b",
        r"\bhogyan érdemes\b",
        r"\bmi (?:a|az) (?:legjobb|jobb)\b",
        r"\bmegéri\b",
        r"\bvalue judgment\b",
        r"\bshould we keep\b",
    ]
    if _matches_any(text_lc, patterns):
        return Suggestion(
            "/think",
            "looks like a design / planning / value-judgment question — /think drafts a validated plan first",
        )
    return None


def _rule_refactor_implement(text_lc: str, raw: str) -> Optional[Suggestion]:
    keyword_patterns = [
        # `implement|build|add … noun` with up to 60 chars between
        r"\b(implement|build|add)\b.{0,60}\b(feature|component|module|system|endpoint|pipeline|handler|integration|service|migration)\b",
        # `implement|build|wire X end-to-end` (either order)
        r"\b(implement|build|wire)\b.{0,50}\bend[-\s]?to[-\s]?end\b",
        r"\bend[-\s]?to[-\s]?end\b.{0,30}\b(implement|build|wire)\b",
        r"\brefactor (?:the|this|that)\b",
        r"\bnew (?:feature|module)\b",
    ]
    file_hits = len(
        re.findall(
            r"[\\/][\w._-]+\.(?:py|js|ts|tsx|jsx|md|yaml|yml|json|sql|ps1|sh|rs|go|java|kt|cs|cpp|h)\b",
            raw,
            re.IGNORECASE,
        )
    )
    if _matches_any(text_lc, keyword_patterns) or file_hits >= 3:
        return Suggestion(
            "/think",
            "looks like a multi-file or non-trivial implementation — /think drafts a plan before code",
        )
    return None


# Order: most specific first. The rule that matches wins.
_RULES: List[Callable[..., Optional[Suggestion]]] = [
    _rule_bug,
    _rule_release_check,
    _rule_sprint_audit,
    _rule_research,
    _rule_design,
    # _rule_refactor_implement is special — needs the raw text for file-path detection.
]


def classify_prompt(text: str) -> Optional[Suggestion]:
    """Classify a user prompt; return a Suggestion or None."""
    if not text or not text.strip():
        return None
    raw = text.strip()
    if _has_slash_command(raw):
        return None
    if _word_count(raw) < 4:
        return None

    lc = raw.lower()
    for rule_fn in _RULES:
        result = rule_fn(lc)
        if result is not None:
            return result

    # Refactor/implement rule needs raw text for file-path globbing.
    result = _rule_refactor_implement(lc, raw)
    if result is not None:
        return result

    return None


def format_suggestion(suggestion: Suggestion) -> str:
    """Format a Suggestion for injection as UserPromptSubmit additionalContext."""
    return (
        f"[smart-router hint] This prompt {suggestion.why}. "
        f"Consider invoking `{suggestion.skill}` unless the user explicitly "
        f"chose a different approach or the request is smaller than the hint suggests. "
        f"This is a suggestion, not enforcement — the user can override."
    )
