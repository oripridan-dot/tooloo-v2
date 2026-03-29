"""Tests for engine/engram_visual.py — VisualEngramGenerator deterministic fallback."""
from __future__ import annotations

from engine.engram_visual import VisualEngramGenerator, VisualEngram, _PALETTE


class TestVisualEngramGeneratorDeterministicFallback:
    def test_idle_returns_visual_engram(self):
        generator = VisualEngramGenerator()
        engram = generator.idle()
        assert isinstance(engram, VisualEngram)

    def test_idle_uses_structured_source(self):
        """In offline mode (conftest patches _gemini_client=None), source must be 'structured'."""
        generator = VisualEngramGenerator()
        engram = generator.idle()
        assert engram.source == "structured"

    def test_idle_mode_is_idle(self):
        generator = VisualEngramGenerator()
        engram = generator.idle()
        assert engram.mode == "idle"

    def test_idle_pulse_rate_is_low(self):
        """Idle mode must have a slow pulse rate (< 1.0 Hz)."""
        generator = VisualEngramGenerator()
        engram = generator.idle()
        # _pulse_rate("idle", 0.22) ≈ 0.22 * (0.7 + 0.22 * 0.6) = ~0.18
        assert 0.0 < engram.pulse_rate < 1.0, (
            f"Idle pulse_rate should be < 1.0, got {engram.pulse_rate}"
        )

    def test_idle_engram_has_id(self):
        generator = VisualEngramGenerator()
        engram = generator.idle()
        assert engram.engram_id.startswith("ve-")

    def test_idle_narrative_is_nonempty(self):
        generator = VisualEngramGenerator()
        engram = generator.idle()
        assert len(engram.narrative) > 0

    def test_current_returns_idle_when_no_prior_engram(self):
        """A fresh generator's current() falls back to idle."""
        generator = VisualEngramGenerator()
        engram = generator.current()
        assert engram.mode == "idle"

    def test_palette_contains_all_intents(self):
        required = {"BUILD", "DEBUG", "AUDIT", "DESIGN", "EXPLAIN", "IDEATE",
                    "SPAWN_REPO", "BLOCKED", "NONE"}
        assert required <= set(_PALETTE.keys())

    def test_idle_color_primary_is_hex(self):
        """color_primary must be a hex color string (#rrggbb)."""
        generator = VisualEngramGenerator()
        engram = generator.idle()
        assert engram.color_primary.startswith("#")

    def test_idle_intensity_is_low(self):
        """Idle intensity should be low (< 0.5)."""
        generator = VisualEngramGenerator()
        engram = generator.idle()
        assert engram.intensity < 0.5

    def test_to_dict_contains_required_keys(self):
        generator = VisualEngramGenerator()
        d = generator.idle().to_dict()
        for key in ("engram_id", "mode", "intent", "intensity",
                    "color_primary", "pulse_rate", "source", "narrative"):
            assert key in d, f"Missing key: {key}"
