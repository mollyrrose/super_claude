"""Unit tests for smart_router_rules.classify_prompt.

Run with: python -m unittest test_smart_router_rules
from the claude_code_integration directory.
"""

from __future__ import annotations

import unittest

from smart_router_rules import (
    Suggestion,
    _rule_fable_orchestration,
    classify_prompt,
    format_suggestion,
    recommend_mode_effort,
    recommend_model_tier,
)


class TestClassifyPrompt(unittest.TestCase):
    def assertSkill(self, prompt: str, expected_skill: str) -> None:
        result = classify_prompt(prompt)
        self.assertIsNotNone(
            result, f"Expected {expected_skill}, got None for: {prompt!r}"
        )
        assert result is not None
        self.assertEqual(
            result.skill,
            expected_skill,
            f"For prompt {prompt!r}: expected {expected_skill}, got {result.skill}",
        )

    def assertNoSuggestion(self, prompt: str) -> None:
        result = classify_prompt(prompt)
        self.assertIsNone(result, f"Expected None, got {result!r} for: {prompt!r}")

    # ── Bug / hunt ─────────────────────────────────────────────────────
    def test_error_trace_routes_to_hunt(self) -> None:
        self.assertSkill(
            "Traceback (most recent call last): ValueError in foo.py", "/hunt"
        )

    def test_broken_test_routes_to_hunt(self) -> None:
        self.assertSkill(
            "git diff shows my test broke after the rebase", "/hunt"
        )

    def test_hungarian_nem_mukodik_routes_to_hunt(self) -> None:
        self.assertSkill(
            "a session_handler nem működik a wed-cross trades-en", "/hunt"
        )

    def test_regression_routes_to_hunt(self) -> None:
        self.assertSkill("this used to work last week, what regressed?", "/hunt")

    def test_crash_routes_to_hunt(self) -> None:
        self.assertSkill(
            "the live engine crashed at startup with exit code 137", "/hunt"
        )

    # ── Release / check ────────────────────────────────────────────────
    def test_before_release_routes_to_check(self) -> None:
        self.assertSkill(
            "am I ready to release the new geo session handler?", "/check"
        )

    def test_ready_to_merge_routes_to_check(self) -> None:
        self.assertSkill(
            "this PR is ready to merge — any final issues?", "/check"
        )

    def test_close_this_issue_routes_to_check(self) -> None:
        self.assertSkill(
            "can we close this issue with the latest commits?", "/check"
        )

    # ── Sprint audit / rev (user correction: review → /rev not /qMin) ──
    def test_review_my_code_routes_to_rev(self) -> None:
        self.assertSkill(
            "review my code before I merge this branch", "/rev"
        )

    def test_audit_routes_to_rev(self) -> None:
        self.assertSkill(
            "can you audit the whole pipeline directory?", "/rev"
        )

    def test_sprint_close_routes_to_rev(self) -> None:
        self.assertSkill(
            "sprint close, please review what shipped", "/rev"
        )

    def test_hungarian_atnezel_routes_to_rev(self) -> None:
        self.assertSkill(
            "kérlek nézd át a teljes l2_worker pipeline-t", "/rev"
        )

    # ── Research / learn ───────────────────────────────────────────────
    def test_deep_dive_routes_to_learn(self) -> None:
        self.assertSkill(
            "can you deep-dive on how the kafka rebalancer protocol works under load?",
            "/learn",
        )

    def test_help_me_understand_routes_to_learn(self) -> None:
        self.assertSkill(
            "help me understand the actor model fundamentals at the runtime level",
            "/learn",
        )

    # ── Design / think ─────────────────────────────────────────────────
    def test_how_should_i_routes_to_think(self) -> None:
        self.assertSkill(
            "how should I structure the new auth flow?", "/think"
        )

    def test_should_we_routes_to_think(self) -> None:
        self.assertSkill(
            "should we drop the legacy migration path?", "/think"
        )

    def test_compare_routes_to_think(self) -> None:
        self.assertSkill(
            "compare Redis vs Postgres for our session cache layer", "/think"
        )

    def test_hungarian_hogyan_erdemes_routes_to_think(self) -> None:
        self.assertSkill(
            "hogyan érdemes a session handler-t bekötni a live engine-be?",
            "/think",
        )

    # ── Refactor / implement ───────────────────────────────────────────
    def test_implement_feature_routes_to_think(self) -> None:
        self.assertSkill(
            "implement the new geo session handler feature end-to-end across the backtest",
            "/think",
        )

    def test_three_files_routes_to_think(self) -> None:
        prompt = (
            "change /app/foo.py and /app/bar.py and /app/baz.py to use the new API"
        )
        self.assertSkill(prompt, "/think")

    # ── No suggestion (trivia / unclear / explicit) ────────────────────
    def test_short_prompt_no_suggestion(self) -> None:
        self.assertNoSuggestion("ls")

    def test_two_word_prompt_no_suggestion(self) -> None:
        self.assertNoSuggestion("show status")

    def test_explicit_slash_command_skipped(self) -> None:
        self.assertNoSuggestion("/think how should I refactor this whole module")

    def test_explicit_namespaced_slash_command_skipped(self) -> None:
        self.assertNoSuggestion("/sc:analyze look at this codebase end-to-end")

    def test_empty_no_suggestion(self) -> None:
        self.assertNoSuggestion("")

    def test_whitespace_no_suggestion(self) -> None:
        self.assertNoSuggestion("   \n\t  ")

    def test_status_question_no_suggestion(self) -> None:
        self.assertNoSuggestion("what time is it now")

    def test_thank_you_no_suggestion(self) -> None:
        self.assertNoSuggestion("thanks, that looks good")

    # ── Rule precedence ────────────────────────────────────────────────
    def test_bug_beats_review(self) -> None:
        # "review" word present, but also "broken" — bug rule fires first.
        self.assertSkill(
            "review of yesterday's session shows the engine broken on Wed-cross",
            "/hunt",
        )

    def test_release_beats_design(self) -> None:
        # "should we" and "ready to release" both present — release rule fires first.
        self.assertSkill(
            "should we mark this ready to release after the smoke test passes?",
            "/check",
        )


class TestFableOrchestrationRule(unittest.TestCase):
    """Regression coverage for the two 2026-07-07 pattern fixes:
    (a) `/advisor fable` uses a plain prefix (a \\b before `/` never matches
        after whitespace), (b) fable+opus requires a delegation co-signal so
        plain comparison questions stay unrouted. The rule takes LOWERCASED
        text (classify_prompt lowercases before dispatch)."""

    def test_advisor_fable_mid_prompt_matches(self) -> None:
        # classify_prompt skips prompts STARTING with a slash command, so the
        # /advisor pattern only ever fires mid-prompt -- test it there.
        r = _rule_fable_orchestration(
            "set the model to opus 4.8 then run /advisor fable to wire it up"
        )
        self.assertIsNotNone(r)
        assert r is not None
        self.assertEqual(r.skill, "/fable-orchestration")

    def test_fable_orchestrate_matches(self) -> None:
        r = _rule_fable_orchestration("use fable to orchestrate opus delegates")
        self.assertIsNotNone(r)

    def test_route_fable_matches(self) -> None:
        r = _rule_fable_orchestration("how do i route fable to opus workers")
        self.assertIsNotNone(r)

    def test_fable_driven_matches(self) -> None:
        r = _rule_fable_orchestration("fable-driven pipeline setup for the repo")
        self.assertIsNotNone(r)

    def test_fable_opus_with_cosignal_matches(self) -> None:
        r = _rule_fable_orchestration("wire fable above opus to orchestrate the build")
        self.assertIsNotNone(r)

    def test_fable_opus_comparison_no_match(self) -> None:
        # The narrowed fable+opus pattern must NOT fire on comparison questions.
        self.assertIsNone(
            _rule_fable_orchestration("is fable better than opus on benchmarks?")
        )

    def test_fable_opus_no_cosignal_no_match(self) -> None:
        self.assertIsNone(
            _rule_fable_orchestration("fable opus comparison benchmark results")
        )

    def test_plain_fable_mention_no_match(self) -> None:
        self.assertIsNone(
            _rule_fable_orchestration("what do you think about the fable model?")
        )


class TestRecommendModelTier(unittest.TestCase):
    def assertTier(self, prompt: str, expected_model: str) -> None:
        tier = recommend_model_tier(prompt)
        self.assertIsNotNone(tier, f"Expected {expected_model}, got None for: {prompt!r}")
        assert tier is not None
        self.assertEqual(
            tier.model, expected_model,
            f"For prompt {prompt!r}: expected {expected_model}, got {tier.model}",
        )

    def test_optimal_algorithm_routes_to_fable(self) -> None:
        self.assertTier(
            "prove this algorithm is optimal from first principles", "fable"
        )

    def test_security_audit_routes_to_opus(self) -> None:
        self.assertTier("security audit of the new payments module", "opus")

    def test_rename_routes_to_haiku(self) -> None:
        self.assertTier("rename the helper variable in this file please", "haiku")

    def test_implement_feature_routes_to_sonnet(self) -> None:
        self.assertTier(
            "implement the session handler feature with unit tests", "sonnet"
        )

    def test_high_beats_impl_precedence(self) -> None:
        # HIGH (opus) patterns are checked before IMPL (sonnet).
        self.assertTier(
            "plan the architecture and then implement the new feature", "opus"
        )

    def test_slash_command_returns_none(self) -> None:
        self.assertIsNone(recommend_model_tier("/think plan this out end to end"))

    def test_short_prompt_returns_none(self) -> None:
        self.assertIsNone(recommend_model_tier("show status now"))

    def test_empty_returns_none(self) -> None:
        self.assertIsNone(recommend_model_tier(""))


class TestFormatSuggestion(unittest.TestCase):
    def test_format_includes_skill_name(self) -> None:
        s = Suggestion(skill="/think", why="looks like a design question")
        text = format_suggestion(s)
        self.assertIn("/think", text)
        self.assertIn("looks like a design question", text)

    def test_format_typical_length_under_cap(self) -> None:
        s = Suggestion(
            skill="/think",
            why="looks like a design / planning / value-judgment question — /think drafts a validated plan first",
        )
        text = format_suggestion(s)
        # Typical suggestion stays well under the 400-char hard cap enforced
        # by the hook entry-point.
        self.assertLess(
            len(text), 400, f"format_suggestion output should be < 400 chars; got {len(text)}"
        )


class TestRecommendModeEffort(unittest.TestCase):
    def assertME(self, prompt, mode, effort, tier):
        me = recommend_mode_effort(prompt)
        self.assertIsNotNone(me, f"None for {prompt!r}")
        self.assertEqual((me.mode, me.effort, me.tier), (mode, effort, tier), prompt)

    def test_fable_algorithm_e5(self):
        self.assertME("prove this algorithm is optimal from first principles", "ALGORITHM", "E5", "fable")

    def test_opus_native_e4(self):
        self.assertME("security audit of the new payments module", "NATIVE", "E4", "opus")

    def test_sonnet_native_e3(self):
        self.assertME("implement the geo session handler feature end-to-end", "NATIVE", "E3", "sonnet")

    def test_haiku_minimal_e1(self):
        self.assertME("rename the helper variable in this file please", "MINIMAL", "E1", "haiku")

    def test_none_when_tier_none(self):
        self.assertIsNone(recommend_mode_effort("hi there how are you"))

    def test_slash_command_none(self):
        self.assertIsNone(recommend_mode_effort("/think plan this out end to end"))

    def test_consistency_with_tier(self):
        # mode/effort must never disagree with recommend_model_tier
        for p in ["prove this is optimal from first principles",
                  "how should we architect the new auth service",
                  "refactor the whole ingestion module for clarity",
                  "bump the version number in the setup file"]:
            t = recommend_model_tier(p); me = recommend_mode_effort(p)
            self.assertEqual(me.tier, t.model, p)


if __name__ == "__main__":
    unittest.main()
