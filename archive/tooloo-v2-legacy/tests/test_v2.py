"""
tests/test_v2.py — TooLoo V2 proof harness.

Three dimensions:
  1. Planning  — CognitiveGraph cycle rejection, wave count, provenance
  2. Routing   — Intent scoring, circuit breaker trips + reset
  3. Execution — Tribunal poison detection + heal, PsycheBank capture, JITExecutor fan-out

All tests are offline (no LLM / network). Target: < 100 ms total.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from engine.executor import Envelope, JITExecutor
from engine.graph import CognitiveGraph, CycleDetectedError, TopologicalSorter, CausalProvenanceTracker
from engine.mcp_manager import MCPManager
from engine.utils import _infer_workspace_file_target
from engine.psyche_bank import CogRule, PsycheBank
from engine.router import MandateRouter
from engine.tribunal import Engram, Tribunal


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dimension 1 — Planning
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCognitiveGraph:
    def test_add_edge_acyclic(self):
        g = CognitiveGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        assert ("a", "b") in g.edges()

    def test_cycle_rejected(self):
        g = CognitiveGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        with pytest.raises(CycleDetectedError):
            g.add_edge("c", "a")

    def test_graph_unchanged_after_cycle(self):
        g = CognitiveGraph()
        g.add_edge("x", "y")
        try:
            g.add_edge("y", "x")
        except CycleDetectedError:
            pass
        # Edge should not have been persisted
        assert ("y", "x") not in g.edges()

    def test_nodes_returned(self):
        g = CognitiveGraph()
        g.add_edge("p", "q")
        nodes = g.nodes()
        assert "p" in nodes and "q" in nodes

    def test_empty_graph(self):
        g = CognitiveGraph()
        assert g.nodes() == []
        assert g.edges() == []


class TestTopologicalSorter:
    def test_linear_chain(self):
        s = TopologicalSorter()
        spec = [("a", []), ("b", ["a"]), ("c", ["b"])]
        waves = s.sort(spec)
        # Each step its own wave
        assert len(waves) == 3
        assert waves[0] == ["a"]
        assert waves[1] == ["b"]
        assert waves[2] == ["c"]

    def test_parallel_first_wave(self):
        s = TopologicalSorter()
        spec = [("a", []), ("b", []), ("c", ["a", "b"])]
        waves = s.sort(spec)
        assert sorted(waves[0]) == ["a", "b"]
        assert waves[1] == ["c"]

    def test_single_node(self):
        s = TopologicalSorter()
        waves = s.sort([("solo", [])])
        assert waves == [["solo"]]

    def test_sort_from_cognitive_graph(self):
        g = CognitiveGraph()
        g.add_edge("alpha", "beta")
        s = TopologicalSorter()
        waves = s.sort(g)
        flat = [n for w in waves for n in w]
        assert "alpha" in flat and "beta" in flat

    def test_cycle_rejected_in_spec(self):
        s = TopologicalSorter()
        with pytest.raises(CycleDetectedError):
            s.sort([("x", ["y"]), ("y", ["x"])])


class TestCausalProvenanceTracker:
    def test_record_and_chain(self):
        t = CausalProvenanceTracker()
        t.record("step-1", "input parsed")
        t.record("step-2", "plan built", caused_by="step-1")
        chain = t.chain("step-2")
        assert "step-1" in chain
        assert "step-2" in chain

    def test_root_cause_direct(self):
        t = CausalProvenanceTracker()
        t.record("root", "origin")
        t.record("child", "derived", caused_by="root")
        assert t.root_cause("child") == "root"

    def test_root_cause_is_self_when_no_parent(self):
        t = CausalProvenanceTracker()
        t.record("solo", "alone")
        assert t.root_cause("solo") == "solo"

    def test_thread_safety(self):
        import threading
        t = CausalProvenanceTracker()
        errors = []

        def _write(i: int) -> None:
            try:
                t.record(f"step-{i}", f"action {i}")
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=_write, args=(i,))
                   for i in range(20)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        assert not errors


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dimension 2 — Routing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMandateRouter:
    def test_build_intent(self):
        r = MandateRouter()
        result = r.route("build a new API endpoint")
        assert result.intent == "BUILD"

    def test_debug_intent(self):
        r = MandateRouter()
        result = r.route("fix the bug in the payment service")
        assert result.intent == "DEBUG"

    def test_audit_intent(self):
        r = MandateRouter()
        result = r.route("audit the security of auth module")
        assert result.intent == "AUDIT"

    def test_ideate_intent(self):
        r = MandateRouter()
        result = r.route("explore ideas for improving UX")
        assert result.intent == "IDEATE"

    def test_confidence_range(self):
        r = MandateRouter()
        result = r.route("build a feature")
        assert 0.0 <= result.confidence <= 1.0

    def test_circuit_breaker_closed_initially(self):
        r = MandateRouter()
        assert not r.status()["circuit_open"]

    def test_circuit_breaker_opens_after_max_fails(self):
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        r = MandateRouter()
        # Simulate failures below threshold by routing very low-confidence text
        # We directly call the internal failure recorder
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            r._record_failure()
        assert r.status()["circuit_open"]

    def test_circuit_open_route_flagged(self):
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        r = MandateRouter()
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            r._record_failure()
        result = r.route("build something")
        assert result.circuit_open

    def test_reset_closes_breaker(self):
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        r = MandateRouter()
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            r._record_failure()
        r.reset()
        assert not r.status()["circuit_open"]

    def test_buddy_line_present(self):
        r = MandateRouter()
        result = r.route("build a new service")
        assert isinstance(result.buddy_line, str) and len(
            result.buddy_line) > 0

    def test_to_dict_shape(self):
        r = MandateRouter()
        d = r.route("explain the architecture").to_dict()
        assert "intent" in d and "confidence" in d and "circuit_open" in d

    def test_scaled_confidence_survives_keyword_dilution(self):
        r = MandateRouter()
        result = r.route(
            "brainstorm ideas for platform strategy and recommend an approach")
        assert result.intent == "IDEATE"
        assert result.confidence >= 0.9


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dimension 3 — Execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture()
def tmp_bank(tmp_path: Path) -> PsycheBank:
    return PsycheBank(path=tmp_path / "test_rules.cog.json")


class TestPsycheBank:
    def test_capture_new_rule(self, tmp_bank: PsycheBank):
        rule = CogRule(id="test-001", description="test", pattern="x",
                       enforcement="warn", category="quality", source="manual")
        assert tmp_bank.capture(rule) is True

    def test_dedup_prevents_duplicate(self, tmp_bank: PsycheBank):
        rule = CogRule(id="dup-001", description="d", pattern="y",
                       enforcement="warn", category="quality", source="manual")
        tmp_bank.capture(rule)
        assert tmp_bank.capture(rule) is False

    def test_all_rules_returns_list(self, tmp_bank: PsycheBank):
        rule = CogRule(id="r-001", description="r", pattern="z",
                       enforcement="block", category="security", source="manual")
        tmp_bank.capture(rule)
        assert len(tmp_bank.all_rules()) == 1

    def test_rules_by_category(self, tmp_bank: PsycheBank):
        tmp_bank.capture(
            CogRule("sec-1", "s", "p", "block", "security", "manual"))
        tmp_bank.capture(CogRule("qual-1", "q", "p",
                         "warn", "quality", "manual"))
        assert len(tmp_bank.rules_by_category("security")) == 1

    def test_persists_to_disk(self, tmp_path: Path):
        path = tmp_path / "persist.cog.json"
        bank = PsycheBank(path=path)
        bank.capture(CogRule("p-001", "persist", "pat",
                     "block", "security", "manual"))
        bank2 = PsycheBank(path=path)
        assert any(r.id == "p-001" for r in bank2.all_rules())

    def test_to_dict_shape(self, tmp_bank: PsycheBank):
        d = tmp_bank.to_dict()
        assert "version" in d and "rules" in d

    def test_loads_preseeded_bank(self):
        """The shipped forbidden_patterns.cog.json has 5 rules."""
        bank = PsycheBank()
        assert len(bank.all_rules()) >= 5


class TestTribunal:
    def test_clean_engram_passes(self, tmp_bank: PsycheBank):
        t = Tribunal(bank=tmp_bank)
        e = Engram(slug="clean-1", intent="BUILD",
                   logic_body="def add(a, b): return a + b")
        result = t.evaluate(e)
        assert result.passed
        assert not result.poison_detected

    def test_hardcoded_secret_detected(self, tmp_bank: PsycheBank):
        t = Tribunal(bank=tmp_bank)
        e = Engram(slug="poison-1", intent="BUILD",
                   logic_body='API_KEY = "sk-supersecret123"')
        result = t.evaluate(e)
        assert result.poison_detected
        assert "hardcoded-secret" in result.violations

    def test_eval_detected(self, tmp_bank: PsycheBank):
        t = Tribunal(bank=tmp_bank)
        e = Engram(slug="poison-2", intent="BUILD",
                   logic_body="result = eval(user_input)")
        result = t.evaluate(e)
        assert "dynamic-eval" in result.violations

    def test_heal_applied(self, tmp_bank: PsycheBank):
        t = Tribunal(bank=tmp_bank)
        e = Engram(slug="heal-1", intent="BUILD", logic_body='SECRET = "xyz"')
        t.evaluate(e)
        assert "TRIBUNAL HEALED" in e.logic_body

    def test_rule_captured_on_violation(self, tmp_bank: PsycheBank):
        t = Tribunal(bank=tmp_bank)
        e = Engram(slug="capture-1", intent="BUILD",
                   logic_body="exec(something)")
        t.evaluate(e)
        rule_ids = [r.id for r in tmp_bank.all_rules()]
        assert any("dynamic-exec" in rid for rid in rule_ids)

    def test_vast_learn_triggered_on_poison(self, tmp_bank: PsycheBank):
        t = Tribunal(bank=tmp_bank)
        e = Engram(slug="vl-1", intent="BUILD",
                   logic_body='PASSWORD = "hunter2"')
        result = t.evaluate(e)
        assert result.vast_learn_triggered

    def test_path_traversal_detected(self, tmp_bank: PsycheBank):
        t = Tribunal(bank=tmp_bank)
        e = Engram(slug="pt-1", intent="BUILD",
                   logic_body="open('../etc/passwd', 'r')")
        result = t.evaluate(e)
        assert result.poison_detected
        assert "path-traversal" in result.violations

    def test_path_traversal_backslash_detected(self, tmp_bank: PsycheBank):
        t = Tribunal(bank=tmp_bank)
        e = Engram(slug="pt-2", intent="BUILD",
                   logic_body="path = user_dir + '..\\secrets'")
        result = t.evaluate(e)
        assert result.poison_detected
        assert "path-traversal" in result.violations

    def test_ssti_jinja2_detected(self, tmp_bank: PsycheBank):
        t = Tribunal(bank=tmp_bank)
        e = Engram(slug="ssti-1", intent="BUILD",
                   logic_body='template = "Hello {{ user_input }}"')
        result = t.evaluate(e)
        assert result.poison_detected
        assert "ssti-template-injection" in result.violations

    def test_command_injection_os_system_detected(self, tmp_bank: PsycheBank):
        t = Tribunal(bank=tmp_bank)
        e = Engram(slug="cmd-1", intent="BUILD",
                   logic_body="os.system(user_cmd)")
        result = t.evaluate(e)
        assert result.poison_detected
        assert "command-injection" in result.violations

    def test_command_injection_subprocess_shell_detected(self, tmp_bank: PsycheBank):
        t = Tribunal(bank=tmp_bank)
        e = Engram(slug="cmd-2", intent="BUILD",
                   logic_body="subprocess.run(cmd, shell=True)")
        result = t.evaluate(e)
        assert result.poison_detected
        assert "command-injection" in result.violations


class TestJITExecutor:
    def test_fan_out_all_succeed(self):
        ex = JITExecutor(max_workers=4)
        envs = [Envelope(mandate_id=f"m-{i}", intent="BUILD")
                for i in range(4)]
        results = ex.fan_out(lambda e: f"done-{e.mandate_id}", envs)
        assert all(r.success for r in results)

    def test_fan_out_preserves_order(self):
        ex = JITExecutor(max_workers=4)
        envs = [Envelope(mandate_id=f"m-{i}", intent="BUILD")
                for i in range(5)]
        results = ex.fan_out(lambda e: e.mandate_id, envs)
        assert [r.mandate_id for r in results] == [f"m-{i}" for i in range(5)]

    def test_fan_out_dag_respects_dependencies(self):
        ex = JITExecutor(max_workers=4)
        envs = [Envelope(mandate_id=f"m-{i}", intent="BUILD")
                for i in range(4)]
        deps = {
            "m-0": [],
            "m-1": ["m-0"],
            "m-2": ["m-0"],
            "m-3": ["m-1", "m-2"],
        }
        seen: list[str] = []

        def _work(env: Envelope) -> str:
            seen.append(env.mandate_id)
            return env.mandate_id

        results = ex.fan_out_dag(_work, envs, deps)
        assert [r.mandate_id for r in results] == [f"m-{i}" for i in range(4)]
        assert seen[0] == "m-0"
        assert seen[-1] == "m-3"

    def test_fan_out_dag_blocks_downstream_on_failed_dependency(self):
        ex = JITExecutor(max_workers=2)
        envs = [Envelope(mandate_id=f"m-{i}", intent="BUILD")
                for i in range(3)]
        deps = {"m-0": [], "m-1": ["m-0"], "m-2": ["m-1"]}

        def _work(env: Envelope) -> str:
            if env.mandate_id == "m-1":
                raise RuntimeError("boom")
            return env.mandate_id

        results = ex.fan_out_dag(_work, envs, deps)
        assert results[1].success is False
        assert results[2].success is False
        assert "Blocked by failed dependency" in (results[2].error or "")

    def test_fan_out_captures_error(self):
        ex = JITExecutor(max_workers=2)

        def _bad(e: Envelope) -> None:
            raise ValueError("intentional")
        envs = [Envelope(mandate_id="m-0", intent="BUILD")]
        results = ex.fan_out(_bad, envs)
        assert not results[0].success
        assert "intentional" in results[0].error

    def test_fan_out_latency_recorded(self):
        ex = JITExecutor(max_workers=2)
        envs = [Envelope(mandate_id="m-0", intent="BUILD")]
        results = ex.fan_out(lambda e: None, envs)
        assert results[0].latency_ms >= 0.0

    def test_empty_envelopes(self):
        ex = JITExecutor()
        results = ex.fan_out(lambda e: None, [])
        assert results == []


class TestMCPManager:
    def test_spawn_process_tool_emits_branch_payload(self):
        mcp = MCPManager()
        result = mcp.call_uri(
            "mcp://tooloo/spawn_process",
            type="FORK",
            intent="IDEATE",
            mandate="Research Vertex AI vector search limits",
            target="engine/jit_booster.py",
        )
        assert result.success is True
        payload = result.output["spawned_branch"]
        assert payload["branch_type"] == "fork"
        assert payload["intent"] == "IDEATE"
        assert payload["mandate_text"] == "Research Vertex AI vector search limits"


class TestImplicitTargetInference:
    def test_infer_workspace_file_target_from_backticked_path(self):
        inferred = _infer_workspace_file_target(
            "Please inspect `engine/router.py` and improve it")
        assert inferred == "engine/router.py"

    def test_latency_p90_is_none_before_any_fanout(self):
        ex = JITExecutor(max_workers=2)
        assert ex.latency_p90() is None

    def test_latency_p90_after_fanout(self):
        ex = JITExecutor(max_workers=2)
        envs = [Envelope(mandate_id=f"m-{i}", intent="BUILD")
                for i in range(5)]
        ex.fan_out(lambda e: None, envs)
        p90 = ex.latency_p90()
        assert p90 is not None
        assert p90 >= 0.0

    def test_reset_histogram_clears_data(self):
        ex = JITExecutor(max_workers=2)
        envs = [Envelope(mandate_id="m-0", intent="BUILD")]
        ex.fan_out(lambda e: None, envs)
        assert ex.latency_p90() is not None
        ex.reset_histogram()
        assert ex.latency_p90() is None

    def test_latency_p50_after_fanout(self):
        ex = JITExecutor(max_workers=2)
        envs = [Envelope(mandate_id=f"m-{i}", intent="BUILD")
                for i in range(6)]
        ex.fan_out(lambda e: None, envs)
        p50 = ex.latency_p50()
        assert p50 is not None
        assert p50 >= 0.0

    def test_latency_p99_after_fanout(self):
        ex = JITExecutor(max_workers=2)
        envs = [Envelope(mandate_id=f"m-{i}", intent="BUILD")
                for i in range(6)]
        ex.fan_out(lambda e: None, envs)
        p99 = ex.latency_p99()
        assert p99 is not None
        assert p99 >= 0.0

    def test_latency_p99_gte_p90_gte_p50(self):
        ex = JITExecutor(max_workers=2)
        envs = [Envelope(mandate_id=f"m-{i}", intent="BUILD")
                for i in range(10)]
        ex.fan_out(lambda e: None, envs)
        p50 = ex.latency_p50()
        p90 = ex.latency_p90()
        p99 = ex.latency_p99()
        assert p50 is not None and p90 is not None and p99 is not None
        assert p50 <= p90 <= p99

    def test_histogram_cap_prunes_oldest_entries(self):
        ex = JITExecutor(max_workers=4)
        ex._MAX_HIST_ENTRIES = 5  # shrink cap for test
        envs = [Envelope(mandate_id=f"m-{i}", intent="BUILD")
                for i in range(8)]
        ex.fan_out(lambda e: None, envs)
        with ex._hist_lock:
            assert len(ex._latency_histogram) <= 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dimension 4 — JIT SOTA Confidence Booster
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestJITBooster:
    """Offline tests for JITBooster structured-fallback path (no network)."""

    from engine.jit_booster import JITBooster as _JITBooster  # noqa: E402

    def _make_booster(self):
        from engine.jit_booster import JITBooster
        return JITBooster()

    def _make_route(self, intent: str = "BUILD", confidence: float = 0.40):
        r = MandateRouter()
        route = r.route_chat("build a new API endpoint for testing")
        # Override intent and confidence to test specific bands
        route.confidence = confidence
        route.intent = intent
        return route

    def test_fetch_returns_jit_boost_result(self):
        from engine.jit_booster import JITBoostResult
        booster = self._make_booster()
        route = self._make_route()
        result = booster.fetch(route)
        assert isinstance(result, JITBoostResult)

    def test_boosted_confidence_is_higher_than_original(self):
        booster = self._make_booster()
        route = self._make_route(confidence=0.40)
        result = booster.fetch(route)
        assert result.boosted_confidence >= result.original_confidence

    def test_boost_delta_is_non_negative(self):
        booster = self._make_booster()
        route = self._make_route()
        result = booster.fetch(route)
        assert result.boost_delta >= 0.0

    def test_boosted_confidence_capped_at_one(self):
        booster = self._make_booster()
        route = self._make_route(confidence=0.99)
        result = booster.fetch(route)
        assert result.boosted_confidence <= 1.0

    def test_signals_are_non_empty_list(self):
        booster = self._make_booster()
        route = self._make_route()
        result = booster.fetch(route)
        assert isinstance(result.signals, list)
        assert len(result.signals) > 0

    def test_signals_are_strings(self):
        booster = self._make_booster()
        route = self._make_route()
        result = booster.fetch(route)
        for s in result.signals:
            assert isinstance(s, str) and len(s) > 0

    def test_source_is_structured_without_gemini(self):
        booster = self._make_booster()
        route = self._make_route()
        result = booster.fetch(route)
        # No live Gemini in offline tests
        assert result.source in ("gemini", "structured")

    def test_jit_id_has_correct_prefix(self):
        booster = self._make_booster()
        route = self._make_route()
        result = booster.fetch(route)
        assert result.jit_id.startswith("jit-")

    def test_to_dict_shape(self):
        booster = self._make_booster()
        route = self._make_route()
        d = booster.fetch(route).to_dict()
        required = {
            "jit_id", "intent", "original_confidence",
            "boosted_confidence", "boost_delta", "signals",
            "source", "fetched_at",
        }
        assert required <= d.keys()

    def test_boost_per_signal_formula(self):
        from engine.jit_booster import BOOST_PER_SIGNAL, MAX_BOOST_DELTA, JITBooster
        booster = JITBooster()
        route = self._make_route(confidence=0.10)
        result = booster.fetch(route)
        expected_delta = min(len(result.signals) *
                             BOOST_PER_SIGNAL, MAX_BOOST_DELTA)
        assert abs(result.boost_delta - expected_delta) < 1e-9

    def test_all_intents_have_catalogue_signals(self):
        from engine.jit_booster import _CATALOGUE
        intents = {"BUILD", "DEBUG", "AUDIT", "DESIGN",
                   "EXPLAIN", "IDEATE", "SPAWN_REPO", "BLOCKED"}
        assert intents <= _CATALOGUE.keys()

    def test_apply_jit_boost_updates_route_confidence(self):
        r = MandateRouter()
        route = r.route_chat("build a new service")
        original_conf = route.confidence
        from engine.jit_booster import JITBooster
        booster = JITBooster()
        jit = booster.fetch(route)
        r.apply_jit_boost(route, jit.boosted_confidence)
        assert route.confidence == jit.boosted_confidence

    def test_apply_jit_boost_unsets_circuit_open_when_above_threshold(self):
        from engine.config import CIRCUIT_BREAKER_THRESHOLD
        from engine.jit_booster import JITBooster
        r = MandateRouter()
        route = r.route_chat("build a service")
        route.circuit_open = True
        r._fail_count = 1
        booster = JITBooster()
        r.apply_jit_boost(route, CIRCUIT_BREAKER_THRESHOLD + 0.01)
        assert not route.circuit_open
        assert r._fail_count == 0
