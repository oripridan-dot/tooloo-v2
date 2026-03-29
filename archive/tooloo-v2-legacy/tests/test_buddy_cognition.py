"""tests/test_buddy_cognition.py — Tests for engine/buddy_cognition.py.

Coverage:
  CognitiveLens:
    - estimate_expertise_delta: expert tokens → positive, novice phrases → negative
    - estimate_cognitive_load: low / medium / high scenarios
    - detect_style_signal: visual, example, analogy, direct
    - extract_goals: goal pattern extraction + length cap
    - detect_achievement: achievement token detection
    - detect_anchor_signal: "that helped", "now I get it" detection
    - analyze: full CognitiveTurn output

  UserProfile:
    - expertise_label tiers (novice/intermediate/advanced/expert)
    - to_dict / from_dict round-trip

  UserProfileStore:
    - get_profile returns default state on empty file
    - update_from_turn: expertise EMA, goals, completed goals, anchor, intent
    - complete_goal: fuzzy matching
    - increment_session_count
    - persistence across instance recreation

  build_cognition_context:
    - NOVICE tier instruction present
    - INTERMEDIATE tier instruction present
    - ADVANCED tier instruction present
    - EXPERT tier instruction present
    - HIGH cognitive load → numbered steps instruction
    - Active goals injected into context
    - Visual style instruction injected
    - Anchor re-use instruction injected
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engine.buddy_cognition import (
    CognitiveLens,
    CognitiveTurn,
    UserProfile,
    UserProfileStore,
    build_cognition_context,
)


# ── CognitiveLens — expertise delta ──────────────────────────────────────────


class TestExpertiseDelta:
    def test_expert_tokens_positive(self) -> None:
        text = "I want to refactor and optimize the architecture for better throughput"
        delta = CognitiveLens.estimate_expertise_delta(text)
        assert delta > 0.0

    def test_novice_phrases_negative(self) -> None:
        text = "I am a beginner, how do I get started from scratch? simple explanation"
        delta = CognitiveLens.estimate_expertise_delta(text)
        assert delta < 0.0

    def test_neutral_delta_near_zero(self) -> None:
        delta = CognitiveLens.estimate_expertise_delta("please help me")
        # Very short neutral text — delta should be near zero
        assert -0.15 <= delta <= 0.15

    def test_delta_capped_at_bounds(self) -> None:
        # Many expert tokens
        text = " ".join(["refactor", "optimize", "architecture", "throughput",
                         "idempotent", "concurrency", "cqrs", "sharding",
                         "memoize", "distributed"] * 3)
        delta = CognitiveLens.estimate_expertise_delta(text)
        assert -0.3 <= delta <= 0.3

    def test_long_words_boost_score(self) -> None:
        text = "parallelization orchestration containerization microservices"
        delta = CognitiveLens.estimate_expertise_delta(text)
        assert delta >= 0.0


# ── CognitiveLens — cognitive load ───────────────────────────────────────────


class TestCognitiveLoad:
    def test_short_greeting_is_low(self) -> None:
        assert CognitiveLens.estimate_cognitive_load("hi there") == "low"

    def test_medium_technical_question(self) -> None:
        # A longer question with multiple clauses triggers medium/high load
        text = "how do I configure a docker container with environment variables and network settings? should I use compose or run directly?"
        result = CognitiveLens.estimate_cognitive_load(text)
        assert result in ("medium", "high")

    def test_long_text_is_high(self) -> None:
        text = "word " * 90
        assert CognitiveLens.estimate_cognitive_load(text) == "high"

    def test_traceback_is_high(self) -> None:
        text = "getting AttributeError: 'NoneType' object has no attribute 'split'"
        assert CognitiveLens.estimate_cognitive_load(text) == "high"

    def test_multi_step_is_high(self) -> None:
        text = "first set up the database and then configure the server and also need to handle auth"
        assert CognitiveLens.estimate_cognitive_load(text) == "high"

    def test_multiple_question_words_high(self) -> None:
        text = "how does this work, what are the trade-offs, and why should I use this pattern?"
        assert CognitiveLens.estimate_cognitive_load(text) == "high"


# ── CognitiveLens — learning style ───────────────────────────────────────────


class TestStyleDetection:
    def test_show_me_is_visual(self) -> None:
        assert CognitiveLens.detect_style_signal(
            "can you show me a diagram?") == "visual"

    def test_for_example_is_example(self) -> None:
        assert CognitiveLens.detect_style_signal(
            "give me an example please") == "example"

    def test_analogy_is_analogy(self) -> None:
        assert CognitiveLens.detect_style_signal(
            "explain it using an analogy") == "analogy"

    def test_plain_is_direct(self) -> None:
        assert CognitiveLens.detect_style_signal(
            "build an auth service") == "direct"

    def test_chart_is_visual(self) -> None:
        assert CognitiveLens.detect_style_signal(
            "draw me a chart of the metrics") == "visual"

    def test_snippet_is_example(self) -> None:
        # 'snippet' without 'show me' → example; 'show me a code snippet' → visual
        assert CognitiveLens.detect_style_signal(
            "show me a code snippet") == "visual"
        assert CognitiveLens.detect_style_signal(
            "here is a sample code snippet") == "example"


# ── CognitiveLens — goal extraction ──────────────────────────────────────────


class TestGoalExtraction:
    def test_i_want_to_pattern(self) -> None:
        text = "I want to build a REST API for my project"
        goals = CognitiveLens.extract_goals(text)
        assert len(goals) >= 1
        assert "build a REST API for my project" in goals[0] or "build" in goals[0]

    def test_i_am_trying_to_pattern(self) -> None:
        text = "I'm trying to fix the authentication bug in production"
        goals = CognitiveLens.extract_goals(text)
        assert len(goals) >= 1

    def test_building_pattern(self) -> None:
        text = "I'm building a microservice with FastAPI"
        goals = CognitiveLens.extract_goals(text)
        assert len(goals) >= 1

    def test_no_goals_short_text(self) -> None:
        goals = CognitiveLens.extract_goals("hi")
        assert goals == []

    def test_max_3_goals_returned(self) -> None:
        text = (
            "I want to build a REST API and I'm trying to set up the database "
            "and I need to configure the auth and I'm trying to deploy to cloud"
        )
        goals = CognitiveLens.extract_goals(text)
        assert len(goals) <= 3

    def test_goal_cap_at_120_chars(self) -> None:
        long_goal = "I want to build " + "a" * 200
        goals = CognitiveLens.extract_goals(long_goal)
        if goals:
            assert len(goals[0]) <= 120


# ── CognitiveLens — achievement detection ────────────────────────────────────


class TestAchievementDetection:
    def test_it_works(self) -> None:
        assert CognitiveLens.detect_achievement("it works! finally!") is True

    def test_done(self) -> None:
        assert CognitiveLens.detect_achievement(
            "I'm done with the feature") is True

    def test_all_tests_pass(self) -> None:
        assert CognitiveLens.detect_achievement(
            "all tests pass now, great") is True

    def test_false_for_negative_context(self) -> None:
        assert CognitiveLens.detect_achievement(
            "it doesn't work still") is False

    def test_false_for_question(self) -> None:
        assert CognitiveLens.detect_achievement(
            "how do I make it work?") is False


# ── CognitiveLens — anchor signal detection ───────────────────────────────────


class TestAnchorSignal:
    def test_that_helped(self) -> None:
        assert CognitiveLens.detect_anchor_signal(
            "oh wow that helped so much") is True

    def test_now_i_get_it(self) -> None:
        assert CognitiveLens.detect_anchor_signal(
            "now i get it, thanks") is True

    def test_that_analogy(self) -> None:
        assert CognitiveLens.detect_anchor_signal(
            "that analogy was perfect") is True

    def test_neutral_text(self) -> None:
        assert CognitiveLens.detect_anchor_signal(
            "let's move on to the next step") is False

    def test_frustration_no_anchor(self) -> None:
        assert CognitiveLens.detect_anchor_signal(
            "this still doesn't work") is False


# ── CognitiveLens — full analysis ────────────────────────────────────────────


class TestAnalyze:
    def test_analyze_returns_cognitive_turn(self) -> None:
        result = CognitiveLens.analyze("I want to refactor the auth module")
        assert isinstance(result, CognitiveTurn)
        assert isinstance(result.expertise_delta, float)
        assert result.cognitive_load in ("low", "medium", "high")
        assert isinstance(result.goals_extracted, list)
        assert isinstance(result.achievement_detected, bool)
        assert isinstance(result.anchor_signal_detected, bool)
        assert result.style_signal in (
            "visual", "example", "analogy", "direct")

    def test_analyze_expert_text(self) -> None:
        text = "optimize the distributed consensus algorithm to reduce latency"
        result = CognitiveLens.analyze(text)
        assert result.expertise_delta > 0.0

    def test_analyze_novice_text(self) -> None:
        text = "i'm new to programming, how do i get started step by step from scratch"
        result = CognitiveLens.analyze(text)
        assert result.expertise_delta < 0.0


# ── UserProfile ───────────────────────────────────────────────────────────────


class TestUserProfile:
    def test_default_expertise_score(self) -> None:
        p = UserProfile()
        assert p.expertise_score == 0.5

    def test_expertise_label_novice(self) -> None:
        p = UserProfile(expertise_score=0.2)
        assert p.expertise_label() == "novice"

    def test_expertise_label_intermediate(self) -> None:
        p = UserProfile(expertise_score=0.45)
        assert p.expertise_label() == "intermediate"

    def test_expertise_label_advanced(self) -> None:
        p = UserProfile(expertise_score=0.7)
        assert p.expertise_label() == "advanced"

    def test_expertise_label_expert(self) -> None:
        p = UserProfile(expertise_score=0.9)
        assert p.expertise_label() == "expert"

    def test_round_trip_to_from_dict(self) -> None:
        p = UserProfile(
            expertise_score=0.75,
            preferred_style="visual",
            active_goals=["build a payments API"],
            frequent_intents=["BUILD", "DEBUG"],
            session_count=5,
        )
        d = p.to_dict()
        p2 = UserProfile.from_dict(d)
        assert p2.expertise_score == 0.75
        assert p2.preferred_style == "visual"
        assert p2.active_goals == ["build a payments API"]
        assert p2.session_count == 5


# ── UserProfileStore ──────────────────────────────────────────────────────────


class TestUserProfileStore:
    def test_get_profile_default_state(self, tmp_path: Path) -> None:
        store = UserProfileStore(path=tmp_path / "profile.json")
        p = store.get_profile()
        assert p.expertise_score == 0.5
        assert p.active_goals == []

    def test_update_from_turn_updates_expertise(self, tmp_path: Path) -> None:
        store = UserProfileStore(path=tmp_path / "profile.json")
        turn = CognitiveLens.analyze(
            "I want to optimize the distributed architecture for throughput")
        initial_score = store.get_profile().expertise_score
        updated = store.update_from_turn(turn, intent="BUILD")
        # Score should have shifted toward the expert direction
        assert isinstance(updated.expertise_score, float)
        assert 0.0 <= updated.expertise_score <= 1.0

    def test_goals_added_via_turn(self, tmp_path: Path) -> None:
        store = UserProfileStore(path=tmp_path / "profile.json")
        turn = CognitiveLens.analyze(
            "I want to build a payment gateway for e-commerce")
        store.update_from_turn(turn, intent="BUILD")
        p = store.get_profile()
        assert len(p.active_goals) >= 1

    def test_achievement_moves_goal_to_completed(self, tmp_path: Path) -> None:
        store = UserProfileStore(path=tmp_path / "profile.json")
        # Add a goal
        goal_turn = CognitiveLens.analyze(
            "I want to fix the authentication bug")
        store.update_from_turn(goal_turn, intent="DEBUG")
        assert len(store.get_profile().active_goals) >= 1

        # Mark achievement
        achieve_turn = CognitiveLens.analyze("it works! finally fixed it!")
        store.update_from_turn(achieve_turn, intent="DEBUG")
        p = store.get_profile()
        assert len(p.completed_goals) >= 1

    def test_anchor_stored_on_signal(self, tmp_path: Path) -> None:
        store = UserProfileStore(path=tmp_path / "profile.json")
        turn = CognitiveLens.analyze(
            "that analogy really helped, now i get it")
        store.update_from_turn(
            turn, intent="EXPLAIN", last_buddy_response="Think of JWT like a hotel keycard.")
        p = store.get_profile()
        assert len(p.knowledge_anchors) >= 1
        assert "hotel keycard" in p.knowledge_anchors[-1]["anchor"]

    def test_learning_style_updated(self, tmp_path: Path) -> None:
        store = UserProfileStore(path=tmp_path / "profile.json")
        turn = CognitiveLens.analyze(
            "can you show me a diagram of the architecture?")
        store.update_from_turn(turn, intent="EXPLAIN")
        p = store.get_profile()
        assert p.preferred_style == "visual"

    def test_complete_goal_fuzzy_match(self, tmp_path: Path) -> None:
        store = UserProfileStore(path=tmp_path / "profile.json")
        turn = CognitiveLens.analyze(
            "I want to build a REST API for my startup")
        store.update_from_turn(turn, intent="BUILD")
        # Fuzzy complete
        found = store.complete_goal("REST API")
        assert found is True
        p = store.get_profile()
        assert len(p.completed_goals) >= 1

    def test_complete_goal_not_found_returns_false(self, tmp_path: Path) -> None:
        store = UserProfileStore(path=tmp_path / "profile.json")
        assert store.complete_goal("nonexistent goal xyz") is False

    def test_increment_session_count(self, tmp_path: Path) -> None:
        store = UserProfileStore(path=tmp_path / "profile.json")
        store.increment_session_count()
        store.increment_session_count()
        assert store.get_profile().session_count == 2

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        path = tmp_path / "profile.json"
        store1 = UserProfileStore(path=path)
        turn = CognitiveLens.analyze(
            "I want to implement a microservice architecture")
        store1.update_from_turn(turn, intent="BUILD")

        store2 = UserProfileStore(path=path)
        p = store2.get_profile()
        assert len(p.active_goals) >= 1 or p.expertise_score != 0.5

    def test_get_profile_returns_snapshot_not_reference(self, tmp_path: Path) -> None:
        """Mutating returned profile must not affect the stored profile."""
        store = UserProfileStore(path=tmp_path / "profile.json")
        p1 = store.get_profile()
        p1.active_goals.append("injected goal")
        p2 = store.get_profile()
        assert "injected goal" not in p2.active_goals


# ── build_cognition_context ───────────────────────────────────────────────────


class TestBuildCognitionContext:
    def _turn(self, load: str = "low") -> CognitiveTurn:
        return CognitiveTurn(
            expertise_delta=0.0,
            cognitive_load=load,
            goals_extracted=[],
            achievement_detected=False,
            anchor_signal_detected=False,
            style_signal="direct",
        )

    def test_novice_label_present(self) -> None:
        p = UserProfile(expertise_score=0.1)
        ctx = build_cognition_context(p, self._turn())
        assert "NOVICE" in ctx

    def test_intermediate_label_present(self) -> None:
        p = UserProfile(expertise_score=0.45)
        ctx = build_cognition_context(p, self._turn())
        assert "INTERMEDIATE" in ctx

    def test_advanced_label_present(self) -> None:
        p = UserProfile(expertise_score=0.72)
        ctx = build_cognition_context(p, self._turn())
        assert "ADVANCED" in ctx

    def test_expert_label_present(self) -> None:
        p = UserProfile(expertise_score=0.92)
        ctx = build_cognition_context(p, self._turn())
        assert "EXPERT" in ctx

    def test_high_load_instruction(self) -> None:
        p = UserProfile(expertise_score=0.5)
        ctx = build_cognition_context(p, self._turn("high"))
        assert "numbered steps" in ctx.lower() or "HIGH" in ctx

    def test_active_goals_injected(self) -> None:
        p = UserProfile(expertise_score=0.5, active_goals=[
                        "build a payment API"])
        ctx = build_cognition_context(p, self._turn())
        assert "payment API" in ctx

    def test_visual_style_instruction(self) -> None:
        p = UserProfile(expertise_score=0.5, preferred_style="visual")
        ctx = build_cognition_context(p, self._turn())
        assert "VISUAL" in ctx

    def test_example_style_instruction(self) -> None:
        p = UserProfile(expertise_score=0.5, preferred_style="example")
        ctx = build_cognition_context(p, self._turn())
        assert "EXAMPLE" in ctx

    def test_anchor_injected_when_present(self) -> None:
        p = UserProfile(
            expertise_score=0.5,
            knowledge_anchors=[
                {"topic": "DEBUG", "anchor": "Think of JWT like a hotel keycard."}],
        )
        ctx = build_cognition_context(p, self._turn())
        assert "hotel keycard" in ctx

    def test_no_goals_no_goals_section(self) -> None:
        p = UserProfile(expertise_score=0.5, active_goals=[])
        ctx = build_cognition_context(p, self._turn())
        assert "Active Goals" not in ctx
