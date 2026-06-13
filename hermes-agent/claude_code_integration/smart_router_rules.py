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


# ── Model-tier routing ─────────────────────────────────────────────────────
#
# Claude Code cannot switch the MAIN session's model from a hook (hard
# architectural limit), and a /model switch is manual. The conversation
# transcript is model-agnostic, so the supported way to run a given phase on a
# different-strength model is to DELEGATE it to a subagent that carries its own
# `model` (Agent/Task `model: opus|sonnet|haiku|fable`). This router classifies
# the prompt's phase and recommends the subagent model to use when delegating;
# the main session keeps the full context regardless of what the subagent runs.
#
# Capability ladder (ascending): haiku < sonnet < opus. The recommendation bakes
# in a one-tier safety margin over the bare minimum for planning and
# implementation work, and ties break upward ("one version higher than
# needed"), capped at opus. Mechanical work stays on haiku. Fable is a separate
# fast line and is intentionally not placed on this ladder.


@dataclass(frozen=True)
class ModelTier:
    model: str   # subagent model alias: "opus" | "sonnet" | "haiku"
    phase: str   # human-readable phase label
    why: str     # one-line rationale surfaced to the model


# High tier (opus): planning, design, architecture, deep reasoning, audit,
# research, hard root-cause debugging, security review.
_TIER_HIGH_PATTERNS = [
    r"\b(architect|architecture|system design|design the)\b",
    r"\bplan (?:this|out|the|a)\b",
    r"\bhow should (?:i|we)\b",
    r"\bbest (?:approach|design|architecture|way)\b",
    r"\b(trade[-\s]?offs?|alternatives?)\b",
    r"\broot[-\s]?cause\b",
    r"\b(regression|regressed)\b",
    r"\baudit\b",
    r"\b(security|threat)[-\s]?(?:review|model|audit|analysis)\b",
    r"\b(research|deep[-\s]?dive)\b",
    r"\bhelp me understand\b",
    # Hungarian
    r"\b(tervezd|tervezz|hogyan érdemes|mi a legjobb|megéri)\b",
    r"\bgyökér ?ok\b",
    r"\bbiztonsági (?:átvizsgálás|audit|elemzés)\b",
    r"\b(kutass|mélyebben|értsd meg|tervezés)\b",
]

# Mechanical tier (haiku): low-effort, near-deterministic edits and lookups.
_TIER_MECH_PATTERNS = [
    r"\b(rename|reformat|re[-\s]?indent)\b",
    r"\bformat the\b",
    r"\bfix the (?:indentation|formatting|whitespace|spelling)\b",
    r"\b(typo|misspelling)\b",
    r"\b(list|show me)\b.{0,15}\b(files|functions|imports|occurrences|todos|directories|folders)\b",
    r"\b(grep|search for|find (?:all )?occurrences)\b",
    r"\bbump (?:the )?version\b",
    r"\bwhat files?\b",
    # Hungarian
    r"\b(nevezd át|formázd|elgépel|listázd|keresd meg|melyik fájl)\b",
]

# Implementation tier (sonnet): standard coding, refactors, tests, bug fixes.
_TIER_IMPL_PATTERNS = [
    r"\b(implement|build|add|wire|integrate|write|create)\b.{0,60}\b(feature|component|module|endpoint|function|method|handler|test|tests|class|migration|script|integration|service|pipeline|hook|route|model)\b",
    r"\brefactor (?:the|this|that|it)\b",
    r"\b(fix|patch) (?:the |this )?(?:bug|issue|function|method|test)\b",
    r"\bwrite (?:the )?(?:unit |integration )?tests?\b",
    # Hungarian
    r"\b(implementáld|csináld meg|írd meg|refaktoráld|kösd be|javítsd)\b",
]


def recommend_model_tier(text: str) -> Optional[ModelTier]:
    """Recommend a subagent model for the prompt's phase, or None when unsure.

    Same conservative bar as classify_prompt: no hint for slash commands, very
    short prompts, or anything that doesn't clearly match a phase. High tier is
    checked first so "security audit of the new module" routes to opus, not the
    implementation tier.
    """
    if not text or not text.strip():
        return None
    raw = text.strip()
    if _has_slash_command(raw):
        return None
    if _word_count(raw) < 4:
        return None
    lc = raw.lower()
    if _matches_any(lc, _TIER_HIGH_PATTERNS):
        return ModelTier(
            "opus",
            "planning / design / deep-reasoning",
            "hard reasoning -> top tier (one step above the bare minimum, capped at opus)",
        )
    if _matches_any(lc, _TIER_MECH_PATTERNS):
        return ModelTier(
            "haiku",
            "mechanical / trivial",
            "near-deterministic low-effort work -> the cheapest tier is enough",
        )
    if _matches_any(lc, _TIER_IMPL_PATTERNS):
        return ModelTier(
            "sonnet",
            "implementation / refactor",
            "standard coding -> mid tier (one step above the bare minimum)",
        )
    return None


def format_model_tier(tier: ModelTier) -> str:
    """Format a ModelTier for injection as UserPromptSubmit additionalContext."""
    return (
        f"[model-router hint] This looks like {tier.phase} work. "
        f"If you delegate it, prefer a `{tier.model}` subagent (Agent/Task model: {tier.model}); "
        f"{tier.why}. The main session keeps full context regardless of the subagent's model. "
        f"Suggestion only -- skip it for quick conversational turns or if the user chose otherwise."
    )
