"""
tests/test_workflow_proof.py — TooLoo V2 workflow proof: simple → complex.

Five progressive steps that prove the full cognitive OS pipeline end-to-end.
Each step builds on the last, exercising progressively deeper behaviour.
All tests are fully offline (no LLM / network). Target: < 400 ms total.

  Step 1 — Advanced Intent Disambiguation   : all 7 intents, confidence boost,
                                              full circuit-breaker round-trip via route()
  Step 2 — Multi-Vector Security Analysis   : multi-violation engrams, SQL + __import__,
                                              rule dedup, category enforcement, tombstone
  Step 3 — Complex DAG Topology + Provenance: diamond graphs, 6-wave deep plans,
                                              CausalProvenanceTracker chain + root-cause,
                                              concurrent graph writes
  Step 4 — Execution Under Stress           : 10 mixed-fail envelopes, metadata round-trip,
                                              multiple exception types, throughput assertion,
                                              result.to_dict() schema validation
  Step 5 — Stateful Multi-Mandate Session   : shared PsycheBank across 3 mandates,
                                              circuit-breaker at the route() level,
                                              provenance chain across all 4 pipeline stages,
                                              intent-conditional plan depth, 5-intent JSON proof
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from engine.executor import Envelope, JITExecutor
from engine.graph import (
    CausalProvenanceTracker,
    CognitiveGraph,
    CycleDetectedError,
    TopologicalSorter,
)
from engine.psyche_bank import CogRule, PsycheBank
from engine.router import MandateRouter
from engine.tribunal import Engram, Tribunal


# ---------------------------------------------------------------------------
#  STEP 1 — Advanced Intent Disambiguation
#
#  Prove: all 7 intents are reachable; keyword density lifts confidence;
#  the circuit breaker trips naturally through route() alone and can be reset;
#  to_dict() and status() expose correct live state.
# ---------------------------------------------------------------------------

class TestStep1_AdvancedIntentDisambiguation:
    """
    Step 1 — beyond simple routing.
    Drive EVERY intent, verify that more keywords push confidence higher,
    exercise the full circuit-breaker lifecycle via route() (no direct
    access to _record_failure), and verify all serialised fields.
    """

    def test_all_seven_intents_are_reachable(self):
        """Every intent in the catalogue can be triggered by a tailored mandate."""
        probes: dict[str, str] = {
            "BUILD":      "build implement create add write generate scaffold",
            "DEBUG":      "fix bug error broken fail crash root cause patch",
            "AUDIT":      "audit scan review check validate verify security report",
            "DESIGN":     "design redesign layout mockup wireframe visual theme prototype",
            "EXPLAIN":    "explain why how does what is describe clarify breakdown",
            "IDEATE":     "brainstorm ideate ideas strategy recommend advise how should",
            "SPAWN_REPO": "new repo new repository create repo spawn repo bootstrap repo initialise repo",
        }
        for expected_intent, text in probes.items():
            router = MandateRouter()
            result = router.route(text)
            assert result.intent == expected_intent, (
                f"Expected {expected_intent!r}, got {result.intent!r} for: {text!r}"
            )

    def test_denser_mandate_yields_higher_confidence(self):
        """Packing more keywords for the same intent lifts the confidence score."""
        router = MandateRouter()
        sparse = router.route("build an API")
        dense  = router.route(
            "build implement create add write generate scaffold initialise setup wire")
        assert dense.confidence >= sparse.confidence, (
            f"Dense mandate should score >= sparse: {dense.confidence} vs {sparse.confidence}"
        )

    def test_circuit_breaker_trips_via_route_only(self):
        """
        Submitting mandates that score below CIRCUIT_BREAKER_THRESHOLD through
        route() — not _record_failure() — eventually trips the breaker.
        """
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        router = MandateRouter()
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            router.route("???")
            if router.is_tripped:
                break
        assert router.is_tripped, "Breaker should trip after max consecutive low-confidence routes"

    def test_tripped_breaker_returns_blocked_intent(self):
        """After the circuit trips, every subsequent route() returns BLOCKED."""
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        router = MandateRouter()
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            router.route("???")

        blocked = router.route("build a very important feature")
        assert blocked.intent == "BLOCKED"
        assert blocked.circuit_open is True
        assert len(blocked.buddy_line) > 0

    def test_reset_restores_full_routing_capability(self):
        """After Governor reset the router classifies mandates normally again."""
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        router = MandateRouter()
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            router.route("???")
        assert router.is_tripped

        router.reset()
        assert not router.is_tripped

        result = router.route("build a new authentication service")
        assert result.intent == "BUILD"
        assert result.intent != "BLOCKED"

    def test_status_reflects_live_failure_count(self):
        """status() accurately reports consecutive failures as they accumulate."""
        router = MandateRouter()
        assert router.status()["consecutive_failures"] == 0
        assert router.status()["circuit_open"] is False

        router.route("???")
        assert router.status()["consecutive_failures"] == 1

    def test_to_dict_contains_all_required_fields(self):
        """RouteResult.to_dict() exposes every field the studio API depends on."""
        router = MandateRouter()
        d = router.route("audit the production security posture").to_dict()
        required = {"intent", "confidence", "circuit_open", "mandate_text", "buddy_line", "ts"}
        assert required <= d.keys(), f"Missing keys: {required - d.keys()}"
        assert isinstance(d["ts"], str) and len(d["ts"]) > 0

    def test_confidence_strictly_bounded_for_all_intents(self):
        """Confidence is always in [0, 1] regardless of the mandate text."""
        router = MandateRouter()
        mandates = [
            "build an API",
            "fix the null pointer",
            "audit the repo",
            "design a new UI layout",
            "explain how DAG waves work",
            "brainstorm ideas for scaling",
            "initialise a new repository",
            "???",
            " " * 50,
        ]
        for text in mandates:
            r = router.route(text)
            assert 0.0 <= r.confidence <= 1.0, f"Confidence {r.confidence} out of range for {text!r}"


# ---------------------------------------------------------------------------
#  STEP 2 — Multi-Vector Security Analysis
#
#  Prove: the Tribunal catches compound attacks (multiple OWASP patterns in
#  one engram), SQL injection and __import__ are flagged, the PsycheBank
#  deduplicates rules across repeated evaluations, the tombstone is an exact
#  known string, and rules_by_category reflects correct post-heal state.
# ---------------------------------------------------------------------------

class TestStep2_MultiVectorSecurityAnalysis:
    """
    Step 2 — beyond single-violation detection.
    Prove compound attacks, SQL injection, __import__, rule deduplication,
    tombstone accuracy, and category-level enforcement.
    """

    _TOMBSTONE = (
        "# [TRIBUNAL HEALED] Poisoned logic redacted. "
        "Rule captured in psyche_bank/."
    )

    @pytest.fixture()
    def bank(self, tmp_path: Path) -> PsycheBank:
        return PsycheBank(path=tmp_path / "security_proof.cog.json")

    def test_compound_attack_captures_multiple_violations(self, bank: PsycheBank):
        """An engram with both eval( and a hardcoded secret triggers both violations."""
        tribunal = Tribunal(bank=bank)
        payload = 'SECRET = "hunter2"\nresult = eval(user_input)'
        engram = Engram(slug="compound-001", intent="BUILD", logic_body=payload)
        result = tribunal.evaluate(engram)

        assert result.poison_detected is True
        assert "hardcoded-secret" in result.violations
        assert "dynamic-eval" in result.violations
        assert len(result.violations) >= 2

    def test_sql_injection_pattern_is_detected(self, bank: PsycheBank):
        """String-concatenation SQL is flagged as sql-injection."""
        tribunal = Tribunal(bank=bank)
        engram = Engram(
            slug="sql-001",
            intent="BUILD",
            logic_body="query = 'SELECT * FROM users WHERE name = ' + username",
        )
        result = tribunal.evaluate(engram)
        assert result.poison_detected is True
        assert "sql-injection" in result.violations

    def test_dynamic_import_pattern_is_detected(self, bank: PsycheBank):
        """__import__() dynamic import is flagged."""
        tribunal = Tribunal(bank=bank)
        engram = Engram(
            slug="import-001",
            intent="BUILD",
            logic_body="lib = __import__('os')\nlib.system('rm -rf /')",
        )
        result = tribunal.evaluate(engram)
        assert result.poison_detected is True
        assert "dynamic-import" in result.violations

    def test_healed_engram_contains_exact_tombstone(self, bank: PsycheBank):
        """After healing, logic_body is replaced with the exact known sentinel."""
        tribunal = Tribunal(bank=bank)
        engram = Engram(slug="tombstone-001", intent="DEBUG", logic_body="exec(cmd)")
        tribunal.evaluate(engram)
        assert engram.logic_body == self._TOMBSTONE

    def test_rule_deduplication_across_repeated_evaluations(self, bank: PsycheBank):
        """Evaluating the same violation twice does not double-count rules in the bank."""
        tribunal = Tribunal(bank=bank)
        for i in range(3):
            e = Engram(slug=f"dup-eval-{i:03}", intent="BUILD", logic_body="eval(x)")
            tribunal.evaluate(e)

        matching = [r for r in bank.all_rules() if r.pattern == "dynamic-eval"]
        assert len(matching) == 1, f"Expected 1 dynamic-eval rule, got {len(matching)}"

    def test_violated_rules_are_security_category_block_enforcement(self, bank: PsycheBank):
        """Auto-captured rules have category=security and enforcement=block."""
        tribunal = Tribunal(bank=bank)
        engram = Engram(slug="cat-001", intent="BUILD", logic_body="exec(dangerous)")
        tribunal.evaluate(engram)

        sec_rules = bank.rules_by_category("security")
        assert any(r.source == "tribunal" for r in sec_rules)
        for r in sec_rules:
            if r.source == "tribunal":
                assert r.enforcement == "block"

    def test_bank_grows_only_on_novel_violations(self, bank: PsycheBank):
        """Rule count increases per distinct violation, not per evaluation."""
        tribunal = Tribunal(bank=bank)
        initial = len(bank.all_rules())

        tribunal.evaluate(Engram(slug="n1", intent="BUILD", logic_body="eval(a)"))
        after_first = len(bank.all_rules())
        assert after_first == initial + 1

        tribunal.evaluate(Engram(slug="n2", intent="BUILD", logic_body="eval(b)"))
        assert len(bank.all_rules()) == after_first  # deduped

        tribunal.evaluate(Engram(slug="n3", intent="BUILD", logic_body="exec(c)"))
        assert len(bank.all_rules()) == after_first + 1  # new pattern

    def test_clean_engram_leaves_bank_unchanged(self, bank: PsycheBank):
        """A violation-free engram does not add any rules to the bank."""
        tribunal = Tribunal(bank=bank)
        before = len(bank.all_rules())
        result = tribunal.evaluate(Engram(slug="clean", intent="BUILD", logic_body="return validate(user)"))
        assert result.passed is True
        assert len(bank.all_rules()) == before


# ---------------------------------------------------------------------------
#  STEP 3 — Complex DAG Topology + Provenance
#
#  Prove: diamond fan-out/fan-in, a 6-wave deep pipeline, CausalProvenance-
#  Tracker chains across recorded events, concurrent graph writes, and that
#  graph state is exactly preserved after a rejected cycle attempt.
# ---------------------------------------------------------------------------

class TestStep3_ComplexDagTopologyAndProvenance:
    """
    Step 3 — beyond linear chains.
    Diamond topologies, multi-wave deep plans, provenance chains,
    concurrent edge writes, and confirmed rollback semantics.
    """

    def test_diamond_dependency_produces_correct_waves(self):
        """
        Diamond pattern:  recon-a --+
                          recon-b --+--> merge --> generate --> validate
        Wave 0 = [recon-a, recon-b], Wave 1 = [merge], ...
        """
        sorter = TopologicalSorter()
        spec = [
            ("recon-a",   []),
            ("recon-b",   []),
            ("merge",     ["recon-a", "recon-b"]),
            ("generate",  ["merge"]),
            ("validate",  ["generate"]),
        ]
        waves = sorter.sort(spec)
        assert sorted(waves[0]) == ["recon-a", "recon-b"]
        assert waves[1] == ["merge"]
        assert waves[2] == ["generate"]
        assert waves[3] == ["validate"]

    def test_double_diamond_with_parallel_validation(self):
        """
        Full double-diamond:
          [recon-a, recon-b] --> plan --> [gen-fast, gen-safe]
                             --> [val-unit, val-integ] --> ship
        Proves two parallel waves inside a single pipeline.
        """
        sorter = TopologicalSorter()
        spec = [
            ("recon-a",   []),
            ("recon-b",   []),
            ("plan",      ["recon-a", "recon-b"]),
            ("gen-fast",  ["plan"]),
            ("gen-safe",  ["plan"]),
            ("val-unit",  ["gen-fast", "gen-safe"]),
            ("val-integ", ["gen-fast", "gen-safe"]),
            ("ship",      ["val-unit", "val-integ"]),
        ]
        waves = sorter.sort(spec)
        assert sorted(waves[0]) == ["recon-a", "recon-b"]
        assert sorted(waves[2]) == ["gen-fast", "gen-safe"]
        assert sorted(waves[3]) == ["val-integ", "val-unit"]
        assert waves[-1] == ["ship"]

    def test_six_wave_deep_pipeline(self):
        """A strictly linear 6-node pipeline produces exactly 6 sequential waves."""
        sorter = TopologicalSorter()
        spec = [
            ("intake",   []),
            ("enrich",   ["intake"]),
            ("classify", ["enrich"]),
            ("plan",     ["classify"]),
            ("execute",  ["plan"]),
            ("audit",    ["execute"]),
        ]
        waves = sorter.sort(spec)
        assert len(waves) == 6
        assert [w[0] for w in waves] == ["intake", "enrich", "classify", "plan", "execute", "audit"]

    def test_graph_state_exact_after_cycle_rejection(self):
        """After a rejected cycle attempt, nodes and edges are exactly as before."""
        g = CognitiveGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        nodes_before = set(g.nodes())
        edges_before = set(g.edges())

        with pytest.raises(CycleDetectedError):
            g.add_edge("c", "a")

        assert set(g.nodes()) == nodes_before
        assert set(g.edges()) == edges_before

    def test_causal_provenance_four_stage_chain(self):
        """
        Record route -> tribunal -> plan -> execute;
        chain("execute") must return all four in order.
        """
        tracker = CausalProvenanceTracker()
        tracker.record("route",    "mandate routed to BUILD")
        tracker.record("tribunal", "security evaluation passed", caused_by="route")
        tracker.record("plan",     "4-wave DAG constructed",     caused_by="tribunal")
        tracker.record("execute",  "all waves completed",        caused_by="plan")

        assert tracker.chain("execute") == ["route", "tribunal", "plan", "execute"]

    def test_causal_provenance_root_cause_traces_back_to_route(self):
        """root_cause('execute') must be 'route' — the origin of the pipeline."""
        tracker = CausalProvenanceTracker()
        tracker.record("route",    "routed")
        tracker.record("tribunal", "evaluated",   caused_by="route")
        tracker.record("plan",     "planned",     caused_by="tribunal")
        tracker.record("execute",  "executed",    caused_by="plan")

        assert tracker.root_cause("execute") == "route"

    def test_concurrent_graph_writes_all_edges_committed(self):
        """20 threads each add a unique disjoint edge — all 20 must survive."""
        g = CognitiveGraph()
        errors: list[Exception] = []

        def add_edge(i: int) -> None:
            try:
                g.add_edge(f"src-{i}", f"dst-{i}")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=add_edge, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        for i in range(20):
            assert (f"src-{i}", f"dst-{i}") in g.edges()

    def test_provenance_tracker_thread_safety_50_writers(self):
        """50 concurrent record() calls leave the tracker in a consistent state."""
        tracker = CausalProvenanceTracker()
        errors: list[Exception] = []

        def record(i: int) -> None:
            try:
                tracker.record(f"event-{i}", f"desc {i}")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=record, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(tracker._events) == 50


# ---------------------------------------------------------------------------
#  STEP 4 — Execution Under Stress
#
#  Prove: 10 envelopes with targeted failures at known positions; metadata
#  round-trip; multiple exception types all captured; throughput assertion
#  (8 x 20 ms in < 70 ms); to_dict() schema on every result.
# ---------------------------------------------------------------------------

class TestStep4_ExecutionUnderStress:
    """
    Step 4 — beyond basic fan-out.
    Targeted multi-failure positions, metadata propagation, heterogeneous
    exception types, throughput proof, and full schema validation.
    """

    _RESULT_SCHEMA = {"mandate_id", "success", "output", "latency_ms", "error"}

    def _envelope(self, mid: str, intent: str = "BUILD", **meta: Any) -> Envelope:
        return Envelope(mandate_id=mid, intent=intent, domain="backend", metadata=dict(meta))

    def test_targeted_failures_at_known_positions(self):
        """
        10 envelopes; workers at indices 2, 5, 8 raise — exactly 3 failures,
        order preserved, failure positions match input.
        """
        fail_positions = {2, 5, 8}
        envelopes = [self._envelope(f"env-{i}") for i in range(10)]
        ids = [e.mandate_id for e in envelopes]

        def work(env: Envelope) -> str:
            idx = ids.index(env.mandate_id)
            if idx in fail_positions:
                raise ValueError(f"injected failure at position {idx}")
            return f"ok-{idx}"

        results = JITExecutor(max_workers=5).fan_out(work, envelopes)

        assert len(results) == 10
        assert [r.mandate_id for r in results] == ids  # order preserved
        failures = [r for r in results if not r.success]
        assert len(failures) == 3
        assert {r.mandate_id for r in failures} == {f"env-{i}" for i in fail_positions}

    def test_metadata_round_trip_through_worker(self):
        """
        Metadata packed into an Envelope survives the thread boundary and
        is readable by the work function.
        """
        envelopes = [
            self._envelope("m-0", seq=0, tag="alpha"),
            self._envelope("m-1", seq=1, tag="beta"),
            self._envelope("m-2", seq=2, tag="gamma"),
        ]

        def work(env: Envelope) -> dict[str, Any]:
            return {"seq": env.metadata["seq"], "tag": env.metadata["tag"]}

        results = JITExecutor(max_workers=3).fan_out(work, envelopes)

        assert results[0].output == {"seq": 0, "tag": "alpha"}
        assert results[1].output == {"seq": 1, "tag": "beta"}
        assert results[2].output == {"seq": 2, "tag": "gamma"}

    def test_heterogeneous_exception_types_all_captured(self):
        """ValueError, RuntimeError, TypeError from different workers all land in .error."""
        exc_map: dict[str, type] = {
            "val": ValueError,
            "run": RuntimeError,
            "typ": TypeError,
        }
        envelopes = [self._envelope(k) for k in exc_map]

        def work(env: Envelope) -> str:
            raise exc_map[env.mandate_id](f"{env.mandate_id}-boom")

        results = JITExecutor(max_workers=3).fan_out(work, envelopes)

        for r in results:
            assert r.success is False
            assert r.error is not None
            assert f"{r.mandate_id}-boom" in r.error

    def test_throughput_eight_tasks_faster_than_serial(self):
        """8 x 20 ms tasks in parallel must finish in < 70 ms (serial ~160 ms)."""
        envelopes = [self._envelope(f"t-{i}") for i in range(8)]

        def work(env: Envelope) -> str:
            time.sleep(0.02)
            return "done"

        t0 = time.monotonic()
        JITExecutor(max_workers=8).fan_out(work, envelopes)
        elapsed_ms = (time.monotonic() - t0) * 1000

        assert elapsed_ms < 70, f"Throughput too slow: {elapsed_ms:.1f} ms"

    def test_result_to_dict_schema_on_every_result(self):
        """Every ExecutionResult.to_dict() has at minimum the required schema keys."""
        envelopes = [self._envelope(f"s-{i}") for i in range(5)]

        def work(env: Envelope) -> str:
            if env.mandate_id == "s-2":
                raise RuntimeError("schema test failure")
            return "value"

        results = JITExecutor(max_workers=5).fan_out(work, envelopes)

        for r in results:
            d = r.to_dict()
            assert self._RESULT_SCHEMA <= d.keys(), f"Missing keys: {self._RESULT_SCHEMA - d.keys()}"
            assert isinstance(d["latency_ms"], float)
            assert isinstance(d["success"], bool)

    def test_empty_envelope_list_returns_empty(self):
        """fan_out with an empty list returns an empty list without error."""
        assert JITExecutor(max_workers=4).fan_out(lambda env: "x", []) == []

    def test_single_failing_worker_does_not_affect_others(self):
        """One crashing worker does not prevent the other 9 from succeeding."""
        envelopes = [self._envelope(f"z-{i}") for i in range(10)]

        def work(env: Envelope) -> str:
            if env.mandate_id == "z-0":
                raise RuntimeError("only me fails")
            return "ok"

        results = JITExecutor(max_workers=10).fan_out(work, envelopes)
        assert results[0].success is False
        assert all(r.success for r in results[1:])


# ---------------------------------------------------------------------------
#  STEP 5 — Stateful Multi-Mandate Session
#
#  Prove: a shared PsycheBank accumulates rules across sequential mandates;
#  the circuit breaker trips naturally through repeated route() calls and
#  recovers after reset(); a CausalProvenanceTracker spans all 4 pipeline
#  stages; intent-conditional plan depth; 5 distinct intents all produce
#  valid fully JSON-serialisable results.
# ---------------------------------------------------------------------------

class TestStep5_StatefulMultiMandateSession:
    """
    Step 5 — the full cognitive OS under real session conditions.
    Shared state, lifecycle transitions, provenance spanning the whole
    pipeline, intent-conditional plan depth, and end-to-end serialisation
    proof across all major intents.
    """

    # Intent -> plan depth (number of DAG waves in the intent-specific plan)
    _INTENT_PLANS: dict[str, list[tuple[str, list[str]]]] = {
        "BUILD": [
            ("recon",    []),
            ("plan",     ["recon"]),
            ("generate", ["plan"]),
            ("test",     ["generate"]),
            ("validate", ["test"]),
            ("ship",     ["validate"]),
        ],
        "DEBUG": [
            ("trace",   []),
            ("isolate", ["trace"]),
            ("patch",   ["isolate"]),
            ("verify",  ["patch"]),
        ],
        "AUDIT": [
            ("scan",    []),
            ("analyse", ["scan"]),
            ("report",  ["analyse"]),
        ],
        "EXPLAIN": [
            ("gather",    []),
            ("summarise", ["gather"]),
        ],
        "IDEATE": [
            ("diverge",  []),
            ("converge", ["diverge"]),
            ("propose",  ["converge"]),
        ],
    }

    def _run_pipeline(
        self,
        text: str,
        bank: PsycheBank,
        router: MandateRouter,
        tracker: CausalProvenanceTracker,
        mandate_id: str = "session-mandate",
    ) -> dict[str, Any]:
        """Full in-process pipeline with shared router/bank/tracker."""
        t_start = time.monotonic()
        sorter   = TopologicalSorter()
        tribunal = Tribunal(bank=bank)
        executor = JITExecutor(max_workers=6)

        # Stage 1: Route
        route = router.route(text)
        tracker.record(f"{mandate_id}.route", f"intent={route.intent}", caused_by=None)

        if route.intent == "BLOCKED":
            return {
                "mandate_id": mandate_id,
                "mandate_text": text,
                "route": route.to_dict(),
                "tribunal": None,
                "plan": [],
                "execution": [],
                "latency_ms": round((time.monotonic() - t_start) * 1000, 2),
                "blocked": True,
            }

        # Stage 2: Tribunal
        engram = Engram(slug=mandate_id, intent=route.intent, logic_body=text)
        tribunal_result = tribunal.evaluate(engram)
        tracker.record(
            f"{mandate_id}.tribunal",
            f"passed={tribunal_result.passed}",
            caused_by=f"{mandate_id}.route",
        )

        # Stage 3: Plan — depth varies by intent
        plan_spec = self._INTENT_PLANS.get(route.intent, self._INTENT_PLANS["BUILD"])
        waves = sorter.sort(plan_spec)
        tracker.record(
            f"{mandate_id}.plan",
            f"waves={len(waves)}",
            caused_by=f"{mandate_id}.tribunal",
        )

        # Stage 4: Execute
        envelopes = [
            Envelope(
                mandate_id=f"{mandate_id}.wave-{i}",
                intent=route.intent,
                domain="backend",
                metadata={"wave": wave, "tribunal_passed": tribunal_result.passed},
            )
            for i, wave in enumerate(waves)
        ]
        execution = executor.fan_out(lambda env: f"{env.mandate_id}-done", envelopes)
        tracker.record(
            f"{mandate_id}.execute",
            f"wave_count={len(execution)}",
            caused_by=f"{mandate_id}.plan",
        )

        return {
            "mandate_id": mandate_id,
            "mandate_text": text,
            "route": route.to_dict(),
            "tribunal": tribunal_result.to_dict(),
            "plan": waves,
            "execution": [r.to_dict() for r in execution],
            "latency_ms": round((time.monotonic() - t_start) * 1000, 2),
            "blocked": False,
        }

    @pytest.fixture()
    def session(self, tmp_path: Path):
        """Shared session state: one PsycheBank, one Router, one Tracker."""
        bank    = PsycheBank(path=tmp_path / "session.cog.json")
        router  = MandateRouter()
        tracker = CausalProvenanceTracker()
        return bank, router, tracker

    def test_psyche_bank_accumulates_rules_across_mandates(self, session):
        """
        Mandate 1 (clean BUILD) -> no new rules.
        Mandate 2 (eval poison) -> +1 rule captured.
        Mandate 3 (clean AUDIT) -> no further rules added.
        """
        bank, router, tracker = session
        initial = len(bank.all_rules())

        self._run_pipeline("build a clean login flow",        bank, router, tracker, "m1")
        assert len(bank.all_rules()) == initial

        self._run_pipeline("build a route with eval(user)",   bank, router, tracker, "m2")
        after_poison = len(bank.all_rules())
        assert after_poison > initial

        self._run_pipeline("audit all security dependencies", bank, router, tracker, "m3")
        assert len(bank.all_rules()) == after_poison

    def test_circuit_breaker_round_trip_through_route(self, session):
        """
        Submit enough low-confidence mandates via route() to trip the circuit,
        verify BLOCKED is returned, reset, then verify full recovery.
        """
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        bank, router, tracker = session

        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            router.route("???")

        assert router.is_tripped

        blocked = self._run_pipeline("build a critical feature", bank, router, tracker, "blocked-check")
        assert blocked["blocked"] is True
        assert blocked["route"]["intent"] == "BLOCKED"
        assert blocked["tribunal"] is None
        assert blocked["plan"] == []

        router.reset()
        assert not router.is_tripped

        recovered = self._run_pipeline("build a new authentication module", bank, router, tracker, "recovered")
        assert recovered["blocked"] is False
        assert recovered["route"]["intent"] == "BUILD"

    def test_provenance_chain_spans_all_four_pipeline_stages(self, session):
        """
        root_cause('m4.execute') must be 'm4.route' — the four-stage causal
        chain is correctly threaded through the shared tracker.
        """
        bank, router, tracker = session
        self._run_pipeline("debug the login failure", bank, router, tracker, "m4")

        chain = tracker.chain("m4.execute")
        assert chain[0]  == "m4.route"
        assert chain[-1] == "m4.execute"
        assert "m4.tribunal" in chain
        assert "m4.plan"     in chain
        assert tracker.root_cause("m4.execute") == "m4.route"

    def test_intent_conditional_plan_depth(self, session):
        """
        BUILD mandates get a 6-wave plan; EXPLAIN gets only 2.
        The pipeline honours intent-specific depth, not a fixed stub.
        """
        bank, router, tracker = session

        build_result   = self._run_pipeline(
            "build implement create add generate scaffold initialise", bank, router, tracker, "depth-build")
        explain_result = self._run_pipeline(
            "explain how does what is describe breakdown clarify",     bank, router, tracker, "depth-explain")

        assert build_result["route"]["intent"]   == "BUILD"
        assert explain_result["route"]["intent"] == "EXPLAIN"

        assert len(build_result["plan"])   == len(self._INTENT_PLANS["BUILD"])
        assert len(explain_result["plan"]) == len(self._INTENT_PLANS["EXPLAIN"])
        assert len(build_result["plan"])   > len(explain_result["plan"])

    def test_five_intents_all_produce_valid_json_results(self, session):
        """
        Run BUILD, DEBUG, AUDIT, EXPLAIN, IDEATE through the full pipeline.
        Every result must be JSON-serialisable and carry the correct shape.
        """
        bank, router, tracker = session

        mandates: list[tuple[str, str]] = [
            ("build a REST API with auth and refresh tokens",   "BUILD"),
            ("fix the crash caused by an unhandled exception",  "DEBUG"),
            ("audit security and review all outdated licences", "AUDIT"),
            ("explain how does the DAG sorter produce waves",   "EXPLAIN"),
            ("brainstorm ideas for a distributed rate-limiter", "IDEATE"),
        ]
        required_keys = {"mandate_id", "mandate_text", "route", "tribunal",
                         "plan", "execution", "latency_ms", "blocked"}

        for i, (text, expected_intent) in enumerate(mandates):
            result = self._run_pipeline(text, bank, router, tracker, f"five-{i}")

            assert result["route"]["intent"] == expected_intent, (
                f"Intent mismatch for {text!r}: expected {expected_intent!r}, "
                f"got {result['route']['intent']!r}"
            )
            assert result["blocked"] is False
            assert required_keys <= result.keys()
            assert all(w["success"] for w in result["execution"])
            assert result["latency_ms"] < 500

            serialised = json.dumps(result)
            assert isinstance(serialised, str) and len(serialised) > 0
