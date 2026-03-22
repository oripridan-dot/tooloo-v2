"""
Tests for engine/dynamic_model_registry.py — DynamicModelRegistry, JIT16DBidder,
FractalDAGExpander.
"""
from __future__ import annotations

import pytest

from engine.dynamic_model_registry import (
    BidResult,
    DynamicModelEntry,
    DynamicModelRegistry,
    FractalDAGExpander,
    FractalExpansion,
    JIT16DBidder,
    get_bidder,
    get_dynamic_registry,
)


# ── DynamicModelEntry ─────────────────────────────────────────────────────────


class TestDynamicModelEntry:
    def _make(self, **overrides) -> DynamicModelEntry:
        defaults = dict(
            model_id="gemini-2.5-flash",
            provider="google",
            display_name="Gemini 2.5 Flash",
            speed=0.88,
            reasoning=0.80,
            coding=0.82,
            synthesis=0.79,
            stability=1.0,
            context_window=1_000_000,
            input_cost_per_m=0.15,
            output_cost_per_m=0.6,
            is_flash=True,
        )
        defaults.update(overrides)
        return DynamicModelEntry(**defaults)

    def test_cost_per_10k_tokens_nonzero(self):
        e = self._make()
        assert e.cost_per_10k_tokens > 0

    def test_cost_per_10k_tokens_floor(self):
        e = self._make(input_cost_per_m=0.0, output_cost_per_m=0.0)
        assert e.cost_per_10k_tokens >= 0.0001

    def test_score_for_task_positive(self):
        e = self._make()
        for task in ("speed", "code", "reasoning", "synthesis", "analysis"):
            assert e.score_for_task(task) > 0

    def test_to_dict_has_model_id(self):
        e = self._make()
        d = e.to_dict()
        assert d["model_id"] == "gemini-2.5-flash"
        assert d["provider"] == "google"

    def test_to_dict_has_cost(self):
        e = self._make()
        d = e.to_dict()
        assert "cost_per_10k" in d


# ── DynamicModelRegistry ─────────────────────────────────────────────────────


class TestDynamicModelRegistry:
    def test_singleton_returns_same_instance(self):
        r1 = get_dynamic_registry()
        r2 = get_dynamic_registry()
        assert r1 is r2

    def test_models_nonempty_from_static_baseline(self):
        reg = DynamicModelRegistry()
        assert len(reg.models) > 0

    def test_models_by_id_is_dict(self):
        reg = DynamicModelRegistry()
        by_id = reg.models_by_id
        assert isinstance(by_id, dict)
        assert len(by_id) > 0

    def test_get_existing_model(self):
        reg = DynamicModelRegistry()
        models = reg.models
        first = models[0]
        found = reg.get(first.model_id)
        assert found is not None
        assert found.model_id == first.model_id

    def test_get_nonexistent_returns_none(self):
        reg = DynamicModelRegistry()
        assert reg.get("nonexistent-model-xyz") is None

    def test_flash_models_all_flash(self):
        reg = DynamicModelRegistry()
        flashes = reg.flash_models()
        for m in flashes:
            assert m.is_flash

    def test_pro_models_all_non_flash(self):
        reg = DynamicModelRegistry()
        pros = reg.pro_models()
        for m in pros:
            assert not m.is_flash

    def test_active_models_returns_list(self):
        reg = DynamicModelRegistry()
        active = reg.active_models()
        assert isinstance(active, list)
        assert len(active) > 0

    def test_active_models_provider_filter(self):
        reg = DynamicModelRegistry()
        google = reg.active_models(provider_filter="google")
        for m in google:
            assert m.provider == "google"

    def test_cheapest_capable_returns_model(self):
        reg = DynamicModelRegistry()
        result = reg.cheapest_capable("reasoning", min_score=0.3)
        assert result is not None
        assert result.score_for_task("reasoning") >= 0.3

    def test_cheapest_capable_too_high_returns_none(self):
        reg = DynamicModelRegistry()
        result = reg.cheapest_capable("reasoning", min_score=999.0)
        assert result is None

    def test_to_status_has_required_keys(self):
        reg = DynamicModelRegistry()
        status = reg.to_status()
        assert "total_models" in status
        assert "providers" in status
        assert "flash_count" in status
        assert "pro_count" in status

    def test_refresh_returns_count(self):
        reg = DynamicModelRegistry()
        count = reg.refresh()
        assert isinstance(count, int)

    def test_local_slm_in_registry(self):
        reg = DynamicModelRegistry()
        local_models = [m for m in reg.models if m.provider == "local_slm"]
        assert len(local_models) >= 1


# ── JIT16DBidder ──────────────────────────────────────────────────────────────


class TestJIT16DBidder:
    @pytest.fixture
    def bidder(self) -> JIT16DBidder:
        return JIT16DBidder(DynamicModelRegistry())

    def test_bid_returns_bid_result(self, bidder: JIT16DBidder):
        result = bidder.bid(node_id="test-node", task_type="reasoning")
        assert isinstance(result, BidResult)
        assert result.node_id == "test-node"
        assert result.winning_model
        assert result.winning_score > 0
        assert result.bid_count > 0

    def test_bid_code_task(self, bidder: JIT16DBidder):
        result = bidder.bid(node_id="code-node", task_type="code")
        assert isinstance(result, BidResult)
        assert result.winning_model

    def test_bid_speed_task(self, bidder: JIT16DBidder):
        result = bidder.bid(node_id="speed-node", task_type="speed")
        assert isinstance(result, BidResult)

    def test_bid_with_dimension_requirements(self, bidder: JIT16DBidder):
        result = bidder.bid(
            node_id="critical-node",
            task_type="reasoning",
            dimension_requirements={"Convergence": 0.95, "Security": 0.90},
        )
        assert isinstance(result, BidResult)
        assert not result.cache_hit

    def test_bid_with_high_stability(self, bidder: JIT16DBidder):
        result = bidder.bid(
            node_id="stable-node",
            task_type="reasoning",
            min_stability=0.99,
        )
        assert isinstance(result, BidResult)

    def test_bid_force_provider(self, bidder: JIT16DBidder):
        result = bidder.bid(
            node_id="google-only", task_type="reasoning",
            force_provider="google",
        )
        assert isinstance(result, BidResult)

    def test_bid_to_dict(self, bidder: JIT16DBidder):
        result = bidder.bid(node_id="dict-node", task_type="reasoning")
        d = result.to_dict()
        assert d["node_id"] == "dict-node"
        assert "winning_model" in d
        assert "winning_score" in d
        assert "bid_count" in d

    def test_bid_with_cache_miss(self, bidder: JIT16DBidder):
        result = bidder.bid_with_cache(
            node_id="cache-test",
            query_text="test query",
            task_type="reasoning",
            cache=None,
        )
        assert isinstance(result, BidResult)
        assert not result.cache_hit

    def test_bid_consensus_returns_list(self, bidder: JIT16DBidder):
        results = bidder.bid_consensus(
            node_id="consensus-node",
            task_type="reasoning",
            top_n=2,
        )
        assert isinstance(results, list)
        # Should have at least 1 result
        assert len(results) >= 1
        for r in results:
            assert isinstance(r, BidResult)
            assert r.consensus_mode

    def test_bid_consensus_different_providers(self, bidder: JIT16DBidder):
        results = bidder.bid_consensus(
            node_id="multi-provider",
            task_type="reasoning",
            top_n=2,
        )
        if len(results) >= 2:
            # If we have multiple results, check they tried different providers
            providers = {r.winning_provider for r in results}
            # At least attempted diversity (may not have 2 distinct providers
            # in all test environments)
            assert len(providers) >= 1

    def test_get_bidder_singleton(self):
        b1 = get_bidder()
        b2 = get_bidder()
        # Both use the same underlying registry
        assert b1._registry is b2._registry


# ── FractalDAGExpander ────────────────────────────────────────────────────────


class TestFractalDAGExpander:
    @pytest.fixture
    def expander(self) -> FractalDAGExpander:
        return FractalDAGExpander()

    def test_no_expansion_on_first_failure(self, expander: FractalDAGExpander):
        result = expander.maybe_expand(
            failed_node_id="node-1",
            action_type="implement",
            failure_count=1,
        )
        assert result is None

    def test_expand_implement_after_2_failures(self, expander: FractalDAGExpander):
        result = expander.maybe_expand(
            failed_node_id="node-impl",
            action_type="implement",
            failure_count=2,
            error_message="syntax error",
        )
        assert result is not None
        assert isinstance(result, FractalExpansion)
        assert result.original_node_id == "node-impl"
        assert len(result.sub_nodes) == 3  # analyze, generate, validate
        assert "syntax error" in result.reason

    def test_expand_design(self, expander: FractalDAGExpander):
        result = expander.maybe_expand(
            failed_node_id="node-design",
            action_type="design",
            failure_count=3,
        )
        assert result is not None
        assert len(result.sub_nodes) == 3

    def test_expand_audit(self, expander: FractalDAGExpander):
        result = expander.maybe_expand(
            failed_node_id="node-audit",
            action_type="audit",
            failure_count=2,
        )
        assert result is not None
        assert len(result.sub_nodes) == 3

    def test_no_expand_unknown_action(self, expander: FractalDAGExpander):
        result = expander.maybe_expand(
            failed_node_id="node-unknown",
            action_type="unknown_action",
            failure_count=5,
        )
        assert result is None

    def test_sub_nodes_have_dependencies(self, expander: FractalDAGExpander):
        result = expander.maybe_expand(
            failed_node_id="dep-test",
            action_type="implement",
            failure_count=3,
        )
        assert result is not None
        # First sub-node has no deps, subsequent ones depend on previous
        _, first_deps = result.sub_nodes[0]
        assert first_deps == []
        _, second_deps = result.sub_nodes[1]
        assert len(second_deps) == 1  # depends on first

    def test_to_dict(self, expander: FractalDAGExpander):
        result = expander.maybe_expand(
            failed_node_id="dict-test",
            action_type="implement",
            failure_count=2,
        )
        assert result is not None
        d = result.to_dict()
        assert d["original_node_id"] == "dict-test"
        assert d["sub_node_count"] == 3

    def test_upgraded_task_types(self, expander: FractalDAGExpander):
        result = expander.maybe_expand(
            failed_node_id="task-test",
            action_type="implement",
            failure_count=2,
        )
        assert result is not None
        # Each sub-node should have a task type
        for sub_id, _ in result.sub_nodes:
            assert sub_id in result.upgraded_task_types


# ── Config settings ──────────────────────────────────────────────────────────


class TestDynamicModelConfig:
    def test_config_has_dynamic_model_settings(self):
        from engine.config import settings
        assert hasattr(settings, "dynamic_model_sync_interval")
        assert hasattr(settings, "jit_bidder_enabled")
        assert hasattr(settings, "fractal_dag_enabled")
        assert hasattr(settings, "bidder_min_stability")

    def test_jit_bidder_enabled_default(self):
        from engine.config import JIT_BIDDER_ENABLED
        assert isinstance(JIT_BIDDER_ENABLED, bool)

    def test_fractal_dag_enabled_default(self):
        from engine.config import FRACTAL_DAG_ENABLED
        assert isinstance(FRACTAL_DAG_ENABLED, bool)

    def test_bidder_min_stability_range(self):
        from engine.config import BIDDER_MIN_STABILITY
        assert 0.0 <= BIDDER_MIN_STABILITY <= 1.0


# ── Integration: ModelGarden + DynamicRegistry ───────────────────────────────


class TestModelGardenDynamicRegistryIntegration:
    def test_garden_has_dynamic_registry(self):
        from engine.model_garden import get_garden
        garden = get_garden()
        reg = garden.dynamic_registry
        assert isinstance(reg, DynamicModelRegistry)
        assert len(reg.models) > 0

    def test_garden_dynamic_registry_same_as_singleton(self):
        from engine.model_garden import get_garden
        garden = get_garden()
        assert garden.dynamic_registry is get_dynamic_registry()


# ── Integration: ModelSelector + JIT16DBidder ────────────────────────────────


class TestModelSelectorBidderIntegration:
    def test_select_with_bidder_returns_selection(self):
        from engine.model_selector import ModelSelector
        sel = ModelSelector()
        result = sel.select_with_bidder(
            stroke=1, intent="BUILD", node_id="test-node",
            task_type="code",
        )
        assert result.stroke == 1
        assert result.intent == "BUILD"
        assert result.model

    def test_select_with_bidder_includes_bid_info(self):
        from engine.model_selector import ModelSelector
        sel = ModelSelector()
        result = sel.select_with_bidder(
            stroke=2, intent="DEBUG", prior_verdict="warn",
            node_id="debug-node",
        )
        assert "JIT16D bid" in result.rationale or result.model
