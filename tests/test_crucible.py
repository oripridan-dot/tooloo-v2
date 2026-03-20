"""
tests/test_crucible.py — TooLoo V2 Fluid Ouroboros Crucible: Round 3

Systemic Collapse — Tribunal · Convergence Guard · E2E Crucible Proof

Three test classes corresponding to the three crucible pillars:

  CrucibleRound1_Tribunal
    - All 12 OWASP Tribunal patterns fire correctly.
    - Clean artefacts pass unchanged.
    - Heal tombstone is applied and PsycheBank rules are captured.
    - Multi-violation engrams record all violations.
    - Concurrent Tribunal evaluations are race-condition-free (Law 17).
    - to_dict() schema is correct.

  CrucibleRound2_ConvergenceGuard
    - Circuit breaker trips after max fails, blocks routing, resets correctly.
    - apply_jit_boost() undoes premature CB failure when confidence is raised.
    - Active-learning sampler fills buffer with low-confidence examples.
    - route_chat() never touches CB state even for low-confidence text.
    - CIRCUIT_BREAKER_THRESHOLD constant (0.85) is never bypassed.
    - AST symbol_map from code_analyze MCP tool contains class / function / method entries.
    - patch_apply MCP tool honours path-traversal jail.

  CrucibleRound3_E2ECrucibleProof
    - Full pipeline: Route → Tribunal → Scope → Execute proves an end-to-end mandate.
    - NStrokeEngine emits plan, execution, and refinement fields.
    - JITBooster returns a structured payload with expected keys.
    - PsycheBank is shared persistently across an entire mandate lifecycle.
    - MCP manifest has expected tool count and all required tool names.
    - VectorStore cosine similarity is symmetric and bounded [0, 1].
    - SandboxOrchestrator readiness gate rejects near-zero scores.

All tests are fully offline (no LLM / network). Target: < 500 ms total.
"""
from __future__ import annotations

import ast
import json
import tempfile
import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from engine.mcp_manager import MCPManager, _tool_code_analyze, _tool_patch_apply
from engine.psyche_bank import CogRule, PsycheBank
from engine.router import (
    CIRCUIT_BREAKER_THRESHOLD,
    MandateRouter,
    RouteResult,
    _ACTIVE_LEARNING_MAXLEN,
    _HEDGE_THRESHOLD,
)
from engine.tribunal import Engram, Tribunal, TribunalResult, _POISON


# ─────────────────────────────────────────────────────────────────────────────
#  Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _clean_engram(slug: str = "test-clean") -> Engram:
    return Engram(
        slug=slug,
        intent="BUILD",
        logic_body="def add(a, b):\n    return a + b\n",
    )


def _poison_engram(slug: str, logic_body: str) -> Engram:
    return Engram(slug=slug, intent="BUILD", logic_body=logic_body)


# ─────────────────────────────────────────────────────────────────────────────
#  CRUCIBLE ROUND 1 — Tribunal
# ─────────────────────────────────────────────────────────────────────────────

class TestCrucibleRound1_Tribunal:
    """12 OWASP patterns, heal, concurrent safety, and DTO schema."""

    # ── Clean path ─────────────────────────────────────────────────────────

    def test_clean_engram_passes(self):
        t = Tribunal(PsycheBank())
        result = t.evaluate(_clean_engram())
        assert result.passed is True
        assert result.poison_detected is False
        assert result.heal_applied is False
        assert result.violations == []

    def test_clean_engram_logic_body_unchanged(self):
        engram = _clean_engram()
        original = engram.logic_body
        Tribunal(PsycheBank()).evaluate(engram)
        assert engram.logic_body == original

    # ── Individual OWASP patterns ──────────────────────────────────────────

    @pytest.mark.parametrize("name,snippet", [
        ("hardcoded-secret",    'SECRET = "s3cr3t_value_here"'),
        ("aws-key-leak",        'key = "AKIAIOSFODNN7EXAMPLE"'),
        ("bearer-token-leak",
         'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVC.'),
        ("sql-injection",       'query = "SELECT * FROM users WHERE id=" + user_id'),
        ("dynamic-eval",        'result = eval(user_input)'),
        ("dynamic-exec",        'exec(code_string)'),
        ("dynamic-import",      'mod = __import__(module_name)'),
        ("path-traversal",      'path = "../../../etc/passwd"'),
        ("ssti-template-injection", 'body = "Hello {{ user.name }}"'),
        ("command-injection",   'os.system("ls " + directory)'),
        ("bola-idor",           'User.objects.filter(id=request.id)'),
        ("ssrf",                'requests.get(request.url)'),
    ])
    def test_pattern_fires(self, name: str, snippet: str):
        bank = PsycheBank()
        t = Tribunal(bank)
        engram = _poison_engram(f"test-{name}", snippet)
        result = t.evaluate(engram)
        assert result.poison_detected is True, f"Pattern {name!r} did not fire"
        assert name in result.violations, f"{name!r} not in violations: {result.violations}"

    # ── Heal behaviour ─────────────────────────────────────────────────────

    def test_heal_replaces_logic_body_with_tombstone(self):
        from engine.tribunal import _HEAL_TOMBSTONE
        engram = _poison_engram("heal-test", 'eval(user_input)')
        Tribunal(PsycheBank()).evaluate(engram)
        assert engram.logic_body == _HEAL_TOMBSTONE

    def test_heal_captures_rule_in_psyche_bank(self):
        bank = PsycheBank()
        engram = _poison_engram("rule-capture", 'exec(code)')
        Tribunal(bank).evaluate(engram)
        rules = bank.all_rules()
        rule_ids = [r.id for r in rules]
        assert any("dynamic-exec" in r_id for r_id in rule_ids), (
            f"No rule for dynamic-exec in {rule_ids}"
        )

    def test_heal_applied_and_vast_learn_triggered(self):
        result = Tribunal(PsycheBank()).evaluate(
            _poison_engram("heal-flags", "eval(x)")
        )
        assert result.heal_applied is True
        assert result.vast_learn_triggered is True

    # ── Multi-violation ────────────────────────────────────────────────────

    def test_multi_violation_records_all(self):
        snippet = 'SECRET = "s3cr3t_pw"\nresult = eval(x)\npath = "../etc/passwd"'
        result = Tribunal(PsycheBank()).evaluate(
            _poison_engram("multi", snippet))
        assert len(result.violations) >= 3
        assert "hardcoded-secret" in result.violations
        assert "dynamic-eval" in result.violations
        assert "path-traversal" in result.violations

    def test_multi_violation_captures_all_rules(self):
        bank = PsycheBank()
        snippet = 'API_KEY = "sk-live-abc"\nexec(payload)'
        Tribunal(bank).evaluate(_poison_engram("multi-rules", snippet))
        rules = bank.all_rules()
        ids = [r.id for r in rules]
        assert any("hardcoded-secret" in i for i in ids)
        assert any("dynamic-exec" in i for i in ids)

    # ── Concurrent safety (Law 17) ─────────────────────────────────────────

    def test_concurrent_evaluations_are_safe(self):
        """50 threads evaluate simultaneously — no exceptions, no data corruption."""
        bank = PsycheBank()
        errors: list[str] = []
        results: list[TribunalResult] = []
        lock = threading.Lock()

        def _eval(i: int) -> None:
            t = Tribunal(bank)
            body = f'eval(x_{i})' if i % 2 == 0 else f'def f{i}(): return {i}'
            engram = _poison_engram(
                f"concurrent-{i}", body) if i % 2 == 0 else _clean_engram(f"concurrent-{i}")
            try:
                r = t.evaluate(engram)
                with lock:
                    results.append(r)
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=_eval, args=(i,))
                   for i in range(50)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert errors == [], f"Concurrent errors: {errors}"
        assert len(results) == 50

    # ── DTO schema ─────────────────────────────────────────────────────────

    def test_passed_result_to_dict_schema(self):
        result = Tribunal(PsycheBank()).evaluate(_clean_engram("schema-clean"))
        d = result.to_dict()
        for key in ("slug", "passed", "poison_detected", "heal_applied",
                    "vast_learn_triggered", "violations"):
            assert key in d, f"Missing key {key!r}"
        assert d["passed"] is True
        assert d["violations"] == []

    def test_failed_result_to_dict_schema(self):
        result = Tribunal(PsycheBank()).evaluate(
            _poison_engram("schema-fail", 'eval(x)')
        )
        d = result.to_dict()
        assert d["passed"] is False
        assert d["poison_detected"] is True
        assert isinstance(d["violations"], list)
        assert len(d["violations"]) >= 1

    # ── Pattern count constant ─────────────────────────────────────────────

    def test_exactly_twelve_poison_patterns(self):
        """Must have 12 OWASP-aligned patterns (10 original + BOLA + SSRF)."""
        assert len(_POISON) == 12, (
            f"Expected 12 patterns, found {len(_POISON)}: {[n for n, _ in _POISON]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  CRUCIBLE ROUND 2 — Convergence Guard
# ─────────────────────────────────────────────────────────────────────────────

class TestCrucibleRound2_ConvergenceGuard:
    """Circuit-breaker invariants, active learning, JIT boost, MCP code_analyze."""

    # ── CB threshold constant ──────────────────────────────────────────────

    def test_circuit_breaker_threshold_is_0_85(self):
        """Law 14 — CIRCUIT_BREAKER_THRESHOLD = 0.85; must never be bypassed."""
        from engine.config import CIRCUIT_BREAKER_THRESHOLD as cfg_threshold
        assert cfg_threshold == 0.85

    def test_router_imports_threshold_from_config(self):
        assert CIRCUIT_BREAKER_THRESHOLD == 0.85

    # ── CB lifecycle ───────────────────────────────────────────────────────

    def test_cb_trips_after_max_fails(self):
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        router = MandateRouter()
        assert not router.is_tripped
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            router._record_failure()
        assert router.is_tripped

    def test_tripped_router_returns_blocked(self):
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        router = MandateRouter()
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            router._record_failure()
        result = router.route("build me a new service")
        assert result.intent == "BLOCKED"
        assert result.circuit_open is True
        assert result.confidence == 0.0

    def test_reset_clears_trip(self):
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        router = MandateRouter()
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            router._record_failure()
        assert router.is_tripped
        router.reset()
        assert not router.is_tripped
        result = router.route("build me a new api")
        assert result.intent != "BLOCKED"

    def test_successful_route_clears_fail_count(self):
        router = MandateRouter()
        router._record_failure()
        assert router._fail_count == 1
        # A high-confidence route resets the counter
        router.route("build implement create add write generate scaffold")
        assert router._fail_count == 0

    def test_status_reflects_live_state(self):
        router = MandateRouter()
        router._record_failure()
        s = router.status()
        assert s["consecutive_failures"] == 1
        assert s["circuit_open"] is False
        assert s["threshold"] == CIRCUIT_BREAKER_THRESHOLD

    # ── JIT boost ──────────────────────────────────────────────────────────

    def test_apply_jit_boost_raises_confidence(self):
        router = MandateRouter()
        result = router.route("build me an api")
        original_conf = result.confidence
        router.apply_jit_boost(result, min(1.0, original_conf + 0.2))
        assert result.confidence >= original_conf

    def test_apply_jit_boost_undoes_cb_failure_when_above_threshold(self):
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        router = MandateRouter()
        # Trip exactly one step below max
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS - 1):
            router._record_failure()
        # Force a low-confidence route result (simulated)
        result = RouteResult(
            intent="BUILD",
            confidence=0.50,
            circuit_open=True,
            mandate_text="build test",
        )
        router._fail_count = CIRCUIT_BREAKER_MAX_FAILS - 1
        router.apply_jit_boost(result, 0.95)
        # Boosted above threshold: circuit_open must be cleared
        assert result.circuit_open is False
        assert result.confidence == 0.95

    def test_jit_boost_recomputes_buddy_line(self):
        router = MandateRouter()
        low_result = router.route("build something")
        router.apply_jit_boost(low_result, 0.95)
        # High-confidence buddy line should not contain hedge text
        assert "~" not in low_result.buddy_line

    # ── Active-learning sampler ────────────────────────────────────────────

    def test_low_confidence_samples_collected(self):
        router = MandateRouter()
        # Route trivially short text that produces low confidence
        for _ in range(5):
            router.route("x")
        samples = router.get_low_confidence_samples()
        assert len(samples) > 0
        text, intent, conf = samples[0]
        assert isinstance(text, str)
        assert isinstance(intent, str)
        assert 0 <= conf <= 1.0

    def test_sample_buffer_caps_at_max_len(self):
        router = MandateRouter()
        for i in range(_ACTIVE_LEARNING_MAXLEN + 20):
            router.route(f"x{i}")
        samples = router.get_low_confidence_samples()
        assert len(samples) <= _ACTIVE_LEARNING_MAXLEN

    def test_high_confidence_route_not_sampled(self):
        router = MandateRouter()
        router.route(
            "build implement create add write generate scaffold initialize deploy"
        )
        samples = router.get_low_confidence_samples()
        # High-confidence routes should not appear in the sample buffer
        for _text, _intent, conf in samples:
            assert conf < _HEDGE_THRESHOLD or conf < CIRCUIT_BREAKER_THRESHOLD

    # ── route_chat CB isolation ────────────────────────────────────────────

    def test_route_chat_never_increments_fail_count(self):
        router = MandateRouter()
        for _ in range(20):
            router.route_chat("hi")
        assert router._fail_count == 0
        assert not router.is_tripped

    def test_route_chat_returns_valid_intent_when_not_tripped(self):
        router = MandateRouter()
        result = router.route_chat("build me a microservice")
        assert result.intent in {
            "BUILD", "DEBUG", "AUDIT", "DESIGN", "EXPLAIN", "IDEATE", "SPAWN_REPO"
        }
        assert result.circuit_open is False

    # ── MCP code_analyze — AST symbol_map ─────────────────────────────────

    def test_code_analyze_symbol_map_has_class(self, tmp_path, monkeypatch):
        import engine.mcp_manager as mcp_mod
        monkeypatch.setattr(mcp_mod, "_WORKSPACE_ROOT", tmp_path)
        py_file = tmp_path / "sample.py"
        py_file.write_text(
            "class Foo:\n    def bar(self):\n        pass\n\ndef top_fn():\n    return 1\n",
            encoding="utf-8",
        )
        res = _tool_code_analyze(file_path="sample.py", code="")
        sym = res["symbol_map"]
        types_ = {s["type"] for s in sym}
        assert "class" in types_
        assert "method" in types_
        assert "function" in types_

    def test_code_analyze_symbol_map_line_ranges(self, tmp_path, monkeypatch):
        import engine.mcp_manager as mcp_mod
        monkeypatch.setattr(mcp_mod, "_WORKSPACE_ROOT", tmp_path)
        src = (
            "class MyClass:\n"            # line 1
            "    def method_a(self):\n"   # line 2
            "        pass\n"              # line 3
            "\n"                          # line 4
            "def standalone():\n"         # line 5
            "    return True\n"           # line 6
        )
        py_file = tmp_path / "lines.py"
        py_file.write_text(src, encoding="utf-8")
        res = _tool_code_analyze(file_path="lines.py", code="")
        sym = res["symbol_map"]
        cls_entries = [s for s in sym if s["type"] == "class"]
        assert len(cls_entries) == 1
        assert cls_entries[0]["name"] == "MyClass"
        # lines is [start, end] (1-indexed)
        assert cls_entries[0]["lines"][0] == 1

    def test_code_analyze_inline_code_no_file(self):
        """code_analyze works purely from inline code (no file_path)."""
        src = "def square(n):\n    return n ** 2\n"
        res = _tool_code_analyze(file_path="", code=src)
        sym = res["symbol_map"]
        fn_names = [s["name"] for s in sym if s["type"] == "function"]
        assert "square" in fn_names

    def test_code_analyze_non_python_has_empty_symbol_map(self):
        res = _tool_code_analyze(file_path="", code="<div>not python</div>")
        assert res["symbol_map"] == []

    # ── patch_apply path-traversal jail ───────────────────────────────────

    def test_patch_apply_rejects_path_traversal(self, tmp_path, monkeypatch):
        import engine.mcp_manager as mcp_mod
        monkeypatch.setattr(mcp_mod, "_WORKSPACE_ROOT", tmp_path)
        with pytest.raises((ValueError, Exception)) as exc_info:
            _tool_patch_apply(
                file_path="../../../etc/passwd",
                search_block="root",
                replace_block="evil",
            )
        assert "traversal" in str(exc_info.value).lower() or \
               "outside" in str(exc_info.value).lower()

    def test_patch_apply_exact_match(self, tmp_path, monkeypatch):
        import engine.mcp_manager as mcp_mod
        monkeypatch.setattr(mcp_mod, "_WORKSPACE_ROOT", tmp_path)
        target = tmp_path / "fix_me.py"
        target.write_text("x = 1\ny = 2\n", encoding="utf-8")
        result = _tool_patch_apply(
            file_path="fix_me.py",
            search_block="x = 1",
            replace_block="x = 42",
        )
        assert result["patched"] is True
        assert target.read_text() == "x = 42\ny = 2\n"


# ─────────────────────────────────────────────────────────────────────────────
#  CRUCIBLE ROUND 3 — E2E Crucible Proof
# ─────────────────────────────────────────────────────────────────────────────

class TestCrucibleRound3_E2ECrucibleProof:
    """End-to-end proof: routing → Tribunal → scope → execute → refine."""

    # ── Route → Tribunal wiring ────────────────────────────────────────────

    def test_routed_intent_feeds_tribunal_clean(self):
        router = MandateRouter()
        result = router.route("build a REST API endpoint for users")
        assert result.intent == "BUILD"
        # Produce an engram from the route result and pass through Tribunal
        engram = Engram(
            slug="e2e-build-route",
            intent=result.intent,
            logic_body="def create_user(name: str) -> dict:\n    return {'name': name}\n",
        )
        tribunal_result = Tribunal(PsycheBank()).evaluate(engram)
        assert tribunal_result.passed is True

    def test_poisoned_mandate_is_blocked_end_to_end(self):
        router = MandateRouter()
        result = router.route("audit this code for security issues")
        engram = Engram(
            slug="e2e-poison",
            intent=result.intent,
            logic_body='SECRET = "hardcoded_password_123"',
        )
        tribunal_result = Tribunal(PsycheBank()).evaluate(engram)
        assert tribunal_result.passed is False
        assert tribunal_result.poison_detected is True
        assert tribunal_result.heal_applied is True

    # ── Scope evaluator ────────────────────────────────────────────────────

    def test_scope_evaluator_produces_plan(self):
        from engine.scope_evaluator import ScopeEvaluator
        evaluator = ScopeEvaluator()
        scope = evaluator.evaluate("build a new user authentication module")
        assert scope is not None
        d = scope.to_dict()
        assert "node_count" in d
        assert d["node_count"] > 0

    def test_scope_evaluator_deep_research_adds_node(self):
        from engine.scope_evaluator import ScopeEvaluator
        evaluator = ScopeEvaluator()
        scope_shallow = evaluator.evaluate("build hello world")
        scope_research = evaluator.evaluate(
            "build implement create add write generate deep research integration strategy"
        )
        assert scope_research.to_dict()["node_count"] >= scope_shallow.to_dict()[
            "node_count"]

    # ── JIT Booster ────────────────────────────────────────────────────────

    def test_jit_booster_returns_structured_payload(self):
        from engine.jit_booster import JITBooster
        from engine.router import MandateRouter
        booster = JITBooster()
        route = MandateRouter().route("build a microservice architecture")
        result = booster.fetch(route)
        for key in ("signals", "boost_delta", "boosted_confidence"):
            assert hasattr(result, key), f"Missing attribute {key!r}"

    def test_jit_booster_boost_delta_within_range(self):
        from engine.jit_booster import JITBooster
        from engine.router import MandateRouter
        booster = JITBooster()
        route = MandateRouter().route("audit security controls")
        result = booster.fetch(route)
        assert 0.0 <= result.boost_delta <= 0.25
        assert 0.0 <= result.boosted_confidence <= 1.0

    def test_jit_booster_signals_is_list(self):
        from engine.jit_booster import JITBooster
        from engine.router import MandateRouter
        booster = JITBooster()
        route = MandateRouter().route("design a new dashboard layout")
        result = booster.fetch(route)
        assert isinstance(result.signals, list)

    # ── PsycheBank shared lifecycle ────────────────────────────────────────

    def test_psyche_bank_persists_across_tribunal_calls(self):
        bank = PsycheBank()
        t = Tribunal(bank)
        # First mandate — captures eval rule
        t.evaluate(_poison_engram("psych-1", "eval(x)"))
        count_after_first = len(bank.all_rules())
        # Second mandate with different violation
        t.evaluate(_poison_engram("psych-2", 'exec("rm -rf /")'))
        count_after_second = len(bank.all_rules())
        assert count_after_second >= count_after_first

    def test_psyche_bank_deduplicates_same_violation(self):
        bank = PsycheBank()
        t = Tribunal(bank)
        t.evaluate(_poison_engram("dedup-1", "eval(x)"))
        first_count = len(bank.all_rules())
        t.evaluate(_poison_engram("dedup-2", "eval(y)"))
        # Same violation pattern — should not double the rules
        second_count = len(bank.all_rules())
        assert second_count == first_count

    # ── MCP manifest ──────────────────────────────────────────────────────

    def test_mcp_manifest_has_nine_tools(self):
        """MCP registry must contain exactly 9 tools after patch_apply + render_screenshot."""
        mcp = MCPManager()
        tools = mcp.manifest()
        assert len(tools) == 9, (
            f"Expected 9 tools, got {len(tools)}: {[t.name for t in tools]}"
        )

    def test_mcp_manifest_contains_required_tools(self):
        mcp = MCPManager()
        names = {t.name for t in mcp.manifest()}
        required = {
            "file_read", "file_write", "web_lookup", "run_tests",
            "code_analyze", "spawn_process", "read_error",
            "patch_apply", "render_screenshot",
        }
        assert required <= names, f"Missing tools: {required - names}"

    # ── VectorStore ────────────────────────────────────────────────────────

    def test_vector_store_cosine_similarity_symmetric(self):
        from engine.vector_store import VectorStore, _cosine
        tokens_a = {"build": 1, "api": 1, "service": 1}
        tokens_b = {"api": 1, "service": 1, "deploy": 1}
        sim_ab = _cosine(tokens_a, tokens_b)
        sim_ba = _cosine(tokens_b, tokens_a)
        assert abs(sim_ab - sim_ba) < 1e-9

    def test_vector_store_cosine_identical_is_one(self):
        from engine.vector_store import _cosine
        tokens = {"build": 2, "api": 1}
        assert abs(_cosine(tokens, tokens) - 1.0) < 1e-6

    def test_vector_store_cosine_disjoint_is_zero(self):
        from engine.vector_store import _cosine
        a = {"apple": 1}
        b = {"banana": 1}
        assert _cosine(a, b) == 0.0

    def test_vector_store_search_returns_list(self):
        from engine.vector_store import VectorStore
        vs = VectorStore()
        vs.add("doc-1", "build a REST API service endpoint", {"type": "task"})
        vs.add("doc-2", "debug authentication error 500", {"type": "task"})
        results = vs.search("REST API build service", top_k=2)
        assert isinstance(results, list)
        assert len(results) <= 2

    def test_vector_store_dedup_rejects_near_duplicate(self):
        from engine.vector_store import VectorStore
        vs = VectorStore(dup_threshold=0.80)
        vs.add("base-doc", "build a REST API service endpoint", {})
        # Nearly identical text
        added = vs.add("dup-doc", "build a REST API service endpoint", {})
        assert added is False

    # ── Sandbox Orchestrator ───────────────────────────────────────────────

    def test_sandbox_promote_threshold_is_0_50(self):
        from engine.sandbox import PROMOTE_THRESHOLD
        assert PROMOTE_THRESHOLD == 0.50

    def test_sandbox_rejects_zero_score(self):
        from engine.sandbox import SandboxOrchestrator
        orch = SandboxOrchestrator()
        # tribunal_passed=False → hard gate returns 0.0
        score = orch._compute_readiness(
            tribunal_passed=False,
            exec_success_rate=1.0,
            refinement_verdict="pass",
            confidence=1.0,
            impact=1.0,
        )
        assert score == 0.0

    def test_sandbox_accepts_above_promote_threshold(self):
        from engine.sandbox import SandboxOrchestrator, PROMOTE_THRESHOLD
        orch = SandboxOrchestrator()
        score = orch._compute_readiness(
            tribunal_passed=True,
            exec_success_rate=1.0,
            refinement_verdict="pass",
            confidence=1.0,
            impact=1.0,
        )
        assert score >= PROMOTE_THRESHOLD

    def test_sandbox_tribunal_hard_gate_zero(self):
        from engine.sandbox import SandboxOrchestrator
        orch = SandboxOrchestrator()
        # Tribunal failure always produces 0.0 regardless of other scores
        score = orch._compute_readiness(
            tribunal_passed=False,
            exec_success_rate=0.99,
            refinement_verdict="pass",
            confidence=0.99,
            impact=0.99,
        )
        assert score == 0.0

    # ── Full pipeline round-trip ───────────────────────────────────────────

    def test_full_pipeline_route_scope_tribunal(self):
        """Assemble a mini pipeline: route → scope → tribunal clean pass."""
        from engine.scope_evaluator import ScopeEvaluator
        bank = PsycheBank()
        router = MandateRouter()
        evaluator = ScopeEvaluator()
        tribunal = Tribunal(bank)

        mandate = "build a JSON REST endpoint that creates users in a Postgres database"
        route_result = router.route(mandate)
        assert route_result.intent == "BUILD"

        scope = evaluator.evaluate(mandate)
        assert scope.to_dict()["node_count"] > 0

        engram = Engram(
            slug="pipeline-end-to-end",
            intent=route_result.intent,
            logic_body=(
                "from flask import request, jsonify\n"
                "def create_user():\n"
                "    data = request.json\n"
                "    user = User(name=data['name'])\n"
                "    db.session.add(user)\n"
                "    db.session.commit()\n"
                "    return jsonify({'id': user.id})\n"
            ),
        )
        t_result = tribunal.evaluate(engram)
        assert t_result.passed is True

    def test_full_pipeline_catches_injection(self):
        """The pipeline's Tribunal must intercept a SQL injection attempt."""
        from engine.scope_evaluator import ScopeEvaluator
        bank = PsycheBank()
        router = MandateRouter()
        tribunal = Tribunal(bank)

        mandate = "build a search feature for the product catalogue"
        route_result = router.route(mandate)

        engram = Engram(
            slug="pipeline-sql-injection",
            intent=route_result.intent,
            logic_body='query = "SELECT * FROM products WHERE name=" + search_term',
        )
        t_result = tribunal.evaluate(engram)
        assert t_result.passed is False
        assert "sql-injection" in t_result.violations
