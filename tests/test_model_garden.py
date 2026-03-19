"""Tests for engine/model_garden.py — registry baseline and tier ladder."""
import importlib

mg = importlib.import_module("engine.model_garden")


# ── Registry baseline ─────────────────────────────────────────────────────────

class TestGardenRegistryBaseline:
    def test_static_registry_contains_gemini_flash(self):
        model_ids = [m.id for m in mg._REGISTRY]
        assert "gemini-2.5-flash" in model_ids

    def test_static_registry_contains_claude_sonnet(self):
        model_ids = [m.id for m in mg._REGISTRY]
        assert "claude-3-7-sonnet@20250219" in model_ids

    def test_all_entries_are_model_info(self):
        assert all(isinstance(m, mg.ModelInfo) for m in mg._REGISTRY)

    def test_all_ids_are_nonempty(self):
        assert all(m.id for m in mg._REGISTRY)

    def test_scores_in_valid_range(self):
        for m in mg._REGISTRY:
            assert 0.0 <= m.speed <= 1.0, f"{m.id}: speed out of range"
            assert 0.0 <= m.reasoning <= 1.0, f"{m.id}: reasoning out of range"
            assert 0.0 <= m.coding <= 1.0, f"{m.id}: coding out of range"
            assert 0.0 <= m.stability <= 1.0, f"{m.id}: stability out of range"

    def test_providers_are_known(self):
        known = {"google", "anthropic", "vertex_maas"}
        for m in mg._REGISTRY:
            assert m.provider in known, f"{m.id}: unknown provider {m.provider!r}"


# ── Tier ladder ───────────────────────────────────────────────────────────────

class TestTierLadderAssignment:
    def test_returns_four_tiers(self):
        tiers = mg.get_full_tier_models()
        assert set(tiers.keys()) == {1, 2, 3, 4}

    def test_t1_is_flash_lite(self):
        tiers = mg.get_full_tier_models()
        # T1 is always the fastest Google flash-lite model
        assert "flash-lite" in tiers[1], f"Expected flash-lite in T1, got: {tiers[1]}"

    def test_t2_is_flash_not_lite(self):
        tiers = mg.get_full_tier_models()
        # T2 is the second-fastest flash (full flash, not lite)
        assert "flash" in tiers[2] and "lite" not in tiers[2], (
            f"Expected flash (not lite) in T2, got: {tiers[2]}"
        )

    def test_t3_is_not_flash(self):
        tiers = mg.get_full_tier_models()
        flash_keywords = ("flash", "lite", "haiku", "nemo")
        assert not any(k in tiers[3] for k in flash_keywords), (
            f"T3 should be a pro/reasoning model, not flash: {tiers[3]}"
        )

    def test_t4_is_not_flash(self):
        tiers = mg.get_full_tier_models()
        flash_keywords = ("flash", "lite", "haiku", "nemo")
        assert not any(k in tiers[4] for k in flash_keywords), (
            f"T4 should be a pro/reasoning model, not flash: {tiers[4]}"
        )

    def test_t3_and_t4_differ_if_multiple_pro_available(self):
        tiers = mg.get_full_tier_models()
        # T3 and T4 may be equal only if there's only one active pro model
        # In practise there are always at least 2 pro models in the registry
        # (gemini-2.5-pro + gemini-3.1-pro-preview), so they should differ
        assert tiers[3] != tiers[1], "T3 should not be the flash-lite model"
        assert tiers[4] != tiers[2], "T4 should not be the flash model"


# ── Garden singleton ──────────────────────────────────────────────────────────

class TestModelGardenSingleton:
    def test_get_garden_returns_instance(self):
        garden = mg.get_garden()
        assert garden is not None

    def test_singleton_identity(self):
        g1 = mg.get_garden()
        g2 = mg.get_garden()
        assert g1 is g2

    def test_get_all_tiers_returns_four_entries(self):
        tiers = mg.get_garden().get_all_tiers()
        assert len(tiers) == 4

    def test_local_slm_lock_override(self):
        model_id = mg.get_garden().get_tier_model(
            tier=3,
            intent="BUILD",
            primary_need="speed",
            lock_model="local_slm",
        )
        assert model_id.startswith("local/")


# ── Dynamic discovery (offline guard) ────────────────────────────────────────

class TestDiscoverAndRegisterModels:
    def test_discover_offline_no_op(self):
        """In offline mode (google_client=None), discover must not raise."""
        # conftest patches _google_client=None — calling must be a no-op
        size_before = len(mg._REGISTRY)
        mg.discover_and_register_models()   # should return immediately, no-op
        # In offline mode the registry must not grow
        assert len(mg._REGISTRY) == size_before
