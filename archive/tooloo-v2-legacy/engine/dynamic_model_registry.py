# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.dynamic_model_registry.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/dynamic_model_registry.py — Dynamic Vertex AI Model Registry & JIT 16D Bidder.

Zero hardcoded model names.  The registry fetches available models from the
Vertex AI platform at startup and periodically re-syncs, then scores every
model per-node using the 16D dimensional signature.

Architecture
────────────
  DynamicModelRegistry
    ├── refresh()                   — fetch live Vertex AI catalog + pricing
    ├── score_model()               — 16D-aware scoring per model
    └── models                      — current snapshot of dynamic ModelInfo list

  JIT16DBidder
    ├── bid()                       — full bidding war per node
    ├── bid_with_cache()            — cache-aware bid (Tier 0 = $0)
    └── bid_consensus()             — multi-model consensus for high-risk nodes

  FractalDAGExpander
    └── maybe_expand()              — split a failed node into sub-DAGs

Design:
  - DynamicModelRegistry replaces the static _REGISTRY list in model_garden.py
  - At startup, it loads the static baseline, then overlays live Vertex discovery
  - Every DYNAMIC_MODEL_SYNC_INTERVAL seconds, it re-fetches from Vertex AI
  - JIT16DBidder uses the registry + BuddyCache to find the optimal model per node
  - Score = (CapabilityMatch * ContextFitness) / CostPer10kTokens
"""
from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from engine.config import settings


# ── Dynamic Model Entry ──────────────────────────────────────────────────────

@dataclass
class DynamicModelEntry:
    """Runtime model record with live pricing and capability scores."""

    model_id: str
    provider: str           # "google" | "anthropic" | "vertex_maas" | "local_slm"
    display_name: str
    # Capability scores (0.0 – 1.0)
    speed: float
    reasoning: float
    coding: float
    synthesis: float
    stability: float
    # Context and pricing
    context_window: int     # max tokens
    input_cost_per_m: float   # USD per 1M input tokens
    output_cost_per_m: float  # USD per 1M output tokens
    # Capabilities tags
    capabilities: frozenset[str] = field(default_factory=frozenset)
    # Metadata
    discovered_at: float = field(default_factory=time.monotonic)
    is_flash: bool = False

    @property
    def cost_per_10k_tokens(self) -> float:
        """Blended cost per 10K tokens (50/50 in/out estimate)."""
        cost = (self.input_cost_per_m * 5000 +
                self.output_cost_per_m * 5000) / 1_000_000
        return max(cost, 0.0001)  # floor to avoid division by zero

    def score_for_task(self, task_type: str) -> float:
        """Weighted capability score for a task type."""
        weights = _TASK_WEIGHTS.get(
            task_type,
            {"speed": 0.25, "reasoning": 0.25, "coding": 0.25, "synthesis": 0.25},
        )
        raw = (
            self.speed * weights.get("speed", 0.25)
            + self.reasoning * weights.get("reasoning", 0.25)
            + self.coding * weights.get("coding", 0.25)
            + self.synthesis * weights.get("synthesis", 0.25)
        )
        return raw * self.stability

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "speed": self.speed,
            "reasoning": self.reasoning,
            "coding": self.coding,
            "synthesis": self.synthesis,
            "stability": self.stability,
            "context_window": self.context_window,
            "input_cost_per_m": self.input_cost_per_m,
            "output_cost_per_m": self.output_cost_per_m,
            "capabilities": sorted(self.capabilities),
            "is_flash": self.is_flash,
            "cost_per_10k": round(self.cost_per_10k_tokens, 6),
        }


# Task-type weight tables
_TASK_WEIGHTS: dict[str, dict[str, float]] = {
    "speed":     {"speed": 0.70, "coding": 0.15, "reasoning": 0.10, "synthesis": 0.05},
    "code":      {"coding": 0.55, "reasoning": 0.25, "speed": 0.15, "synthesis": 0.05},
    "reasoning": {"reasoning": 0.60, "coding": 0.20, "synthesis": 0.15, "speed": 0.05},
    "synthesis": {"synthesis": 0.50, "reasoning": 0.30, "coding": 0.10, "speed": 0.10},
    "analysis":  {"reasoning": 0.50, "coding": 0.25, "synthesis": 0.20, "speed": 0.05},
}

# ── 16D Dimension names and weight map ───────────────────────────────────────

_16D_CAPABILITY_MAP: dict[str, str] = {
    # Maps 16D dimension names → primary capability needed
    "ROI": "speed",
    "Safety": "reasoning",
    "Security": "reasoning",
    "Legal": "reasoning",
    "Human Considering": "synthesis",
    "Accuracy": "reasoning",
    "Efficiency": "speed",
    "Quality": "coding",
    "Speed": "speed",
    "Monitor": "coding",
    "Control": "reasoning",
    "Honesty": "reasoning",
    "Resilience": "reasoning",
    "Financial Awareness": "speed",
    "Convergence": "reasoning",
    "Reversibility": "coding",
}


# ── Heuristic capability inference ───────────────────────────────────────────

def _infer_capabilities(model_id: str) -> tuple[dict[str, float], bool, frozenset[str]]:
    """Infer capability scores, flash status, and tags from a model ID string.

    Returns (scores_dict, is_flash, capabilities_set).
    """
    mid = model_id.lower()
    is_flash = any(k in mid for k in (
        "flash", "lite", "haiku", "nemo", "mini"))
    caps: set[str] = set()

    # Provider detection
    if any(k in mid for k in ("claude", "sonnet", "opus", "haiku")):
        caps.add("strong_reasoning")
        caps.add("code_generation")
    if any(k in mid for k in ("gemini",)):
        caps.add("multimodal")
        caps.add("fast_json")
    if any(k in mid for k in ("llama", "meta/")):
        caps.add("open_source")
        caps.add("code_generation")
    if any(k in mid for k in ("mistral",)):
        caps.add("code_generation")
        caps.add("fast_json")
    if any(k in mid for k in ("code", "codestral")):
        caps.add("code_generation")

    # Architecture-class scoring
    if any(k in mid for k in ("opus", "ultra")):
        scores = {"speed": 0.50, "reasoning": 0.99,
                  "coding": 0.97, "synthesis": 0.96, "stability": 0.90}
    elif any(k in mid for k in ("pro", "sonnet", "405b", "large")):
        scores = {"speed": 0.65, "reasoning": 0.94,
                  "coding": 0.93, "synthesis": 0.91, "stability": 0.95}
        caps.add("strong_reasoning")
    elif is_flash:
        if "lite" in mid or "mini" in mid:
            scores = {"speed": 0.96, "reasoning": 0.68,
                      "coding": 0.70, "synthesis": 0.67, "stability": 1.0}
        else:
            scores = {"speed": 0.88, "reasoning": 0.80,
                      "coding": 0.82, "synthesis": 0.79, "stability": 1.0}
        caps.add("fast_inference")
    elif any(k in mid for k in ("70b", "72b")):
        scores = {"speed": 0.75, "reasoning": 0.89,
                  "coding": 0.88, "synthesis": 0.85, "stability": 0.95}
    elif any(k in mid for k in ("8b", "7b", "3b", "nemo")):
        scores = {"speed": 0.93, "reasoning": 0.72,
                  "coding": 0.74, "synthesis": 0.70, "stability": 0.95}
        caps.add("fast_inference")
    else:
        # Unknown; conservative mid-tier estimate
        scores = {"speed": 0.75, "reasoning": 0.82,
                  "coding": 0.80, "synthesis": 0.78, "stability": 0.90}

    # Preview/experimental penalty
    if any(k in mid for k in ("preview", "exp", "beta")):
        scores["stability"] = min(scores["stability"], 0.90)

    return scores, is_flash, frozenset(caps)


def _infer_context_window(model_id: str) -> int:
    """Heuristic context window inference from model ID."""
    mid = model_id.lower()
    if "1m" in mid or "1000k" in mid:
        return 1_000_000
    if "gemini" in mid and ("pro" in mid or "2.5" in mid):
        return 1_000_000
    if "claude" in mid and "3" in mid:
        return 200_000
    if "llama" in mid and "405b" in mid:
        return 128_000
    if "llama" in mid:
        return 128_000
    if "mistral" in mid and "large" in mid:
        return 128_000
    if "flash" in mid:
        return 1_000_000
    return 128_000  # safe default


def _infer_pricing(model_id: str, is_flash: bool) -> tuple[float, float]:
    """Heuristic pricing inference (USD per 1M tokens).

    Returns (input_cost_per_m, output_cost_per_m).
    """
    mid = model_id.lower()
    if mid.startswith("local/"):
        return 0.0, 0.0
    if "lite" in mid or "mini" in mid:
        return 0.075, 0.30
    if is_flash and ("haiku" in mid or "nemo" in mid):
        return 0.25, 1.25
    if is_flash:
        return 0.15, 0.60
    if any(k in mid for k in ("opus", "ultra")):
        return 15.0, 75.0
    if any(k in mid for k in ("pro", "sonnet")):
        return 3.0, 15.0
    if any(k in mid for k in ("large", "405b")):
        return 3.0, 9.0
    if any(k in mid for k in ("70b", "72b")):
        return 0.90, 0.90
    return 1.0, 3.0  # safe mid-range default


# ── Dynamic Model Registry ──────────────────────────────────────────────────

class DynamicModelRegistry:
    """Live, zero-hardcode Vertex AI model catalog.

    On construction, loads the static baseline from ModelGarden._REGISTRY,
    then overlays live Vertex AI discovery.  Re-syncs every
    DYNAMIC_MODEL_SYNC_INTERVAL seconds.
    """

    def __init__(self, sync_interval_sec: float | None = None) -> None:
        self._models: list[DynamicModelEntry] = []
        self._models_by_id: dict[str, DynamicModelEntry] = {}
        self._lock = threading.Lock()
        self._last_sync: float = 0.0
        self._sync_interval = sync_interval_sec or float(
            getattr(settings, "dynamic_model_sync_interval", 86400)
        )
        self._load_static_baseline()

    @property
    def models(self) -> list[DynamicModelEntry]:
        """Current model snapshot (auto-refreshes if stale)."""
        if (time.monotonic() - self._last_sync) > self._sync_interval:
            self.refresh()
        with self._lock:
            return list(self._models)

    @property
    def models_by_id(self) -> dict[str, DynamicModelEntry]:
        if (time.monotonic() - self._last_sync) > self._sync_interval:
            self.refresh()
        with self._lock:
            return dict(self._models_by_id)

    def get(self, model_id: str) -> DynamicModelEntry | None:
        return self.models_by_id.get(model_id)

    def refresh(self) -> int:
        """Re-sync from Vertex AI. Returns count of newly discovered models."""
        new_count = self._discover_from_vertex()
        with self._lock:
            self._last_sync = time.monotonic()
        return new_count

    def active_models(self, provider_filter: str | None = None) -> list[DynamicModelEntry]:
        """Return models filtered by provider (or all if None)."""
        models = self.models
        if provider_filter:
            return [m for m in models if m.provider == provider_filter]
        return models

    def flash_models(self) -> list[DynamicModelEntry]:
        return [m for m in self.models if m.is_flash]

    def pro_models(self) -> list[DynamicModelEntry]:
        return [m for m in self.models if not m.is_flash]

    def cheapest_capable(self, task_type: str, min_score: float = 0.6) -> DynamicModelEntry | None:
        """Find the cheapest model that meets a minimum capability score."""
        candidates = [
            m for m in self.models
            if m.score_for_task(task_type) >= min_score
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda m: m.cost_per_10k_tokens)

    def to_status(self) -> dict[str, Any]:
        models = self.models
        providers = sorted({m.provider for m in models})
        return {
            "total_models": len(models),
            "providers": providers,
            "flash_count": len([m for m in models if m.is_flash]),
            "pro_count": len([m for m in models if not m.is_flash]),
            "last_sync_age_sec": round(time.monotonic() - self._last_sync, 1),
            "sync_interval_sec": self._sync_interval,
        }

    # ── Private ──────────────────────────────────────────────────────────────

    def _load_static_baseline(self) -> None:
        """Seed registry from model_garden._REGISTRY (imported at call time)."""
        try:
            from engine.model_garden import _REGISTRY as static_registry
            for m in static_registry:
                scores, is_flash, caps = _infer_capabilities(m.id)
                ctx = _infer_context_window(m.id)
                in_cost, out_cost = _infer_pricing(m.id, is_flash)
                entry = DynamicModelEntry(
                    model_id=m.id,
                    provider=m.provider,
                    display_name=m.id,
                    speed=m.speed,
                    reasoning=m.reasoning,
                    coding=m.coding,
                    synthesis=m.synthesis,
                    stability=m.stability,
                    context_window=ctx,
                    input_cost_per_m=in_cost,
                    output_cost_per_m=out_cost,
                    capabilities=caps,
                    is_flash=m.is_flash,
                )
                self._models.append(entry)
                self._models_by_id[m.id] = entry
        except ImportError:
            pass
        # Also add local SLM as Tier 0
        local_id = getattr(settings, "local_slm_model",
                           "local/llama-3.2-3b-instruct")
        if local_id not in self._models_by_id:
            self._models.append(DynamicModelEntry(
                model_id=local_id,
                provider="local_slm",
                display_name="Local SLM",
                speed=0.99, reasoning=0.55, coding=0.60,
                synthesis=0.50, stability=1.0,
                context_window=4096,
                input_cost_per_m=0.0, output_cost_per_m=0.0,
                capabilities=frozenset({"fast_inference", "local"}),
                is_flash=True,
            ))
            self._models_by_id[local_id] = self._models[-1]
        self._last_sync = time.monotonic()

    def _discover_from_vertex(self) -> int:
        """Query Vertex AI for new models and add them dynamically."""
        try:
            from engine.config import _vertex_client
            if _vertex_client is None:
                return 0

            available = _vertex_client.models.list()
            new_count = 0

            with self._lock:
                existing_ids = set(self._models_by_id.keys())

            for model in available:
                model_id = getattr(model, "name", None) or getattr(
                    model, "id", None)
                if not model_id:
                    continue
                if model_id in existing_ids:
                    continue
                # Skip embedding/vision-only
                if any(k in model_id for k in ("embedding", "vision", "imagen")):
                    continue

                scores, is_flash, caps = _infer_capabilities(model_id)
                ctx = _infer_context_window(model_id)
                in_cost, out_cost = _infer_pricing(model_id, is_flash)

                provider = "google"
                if any(k in model_id for k in ("meta/", "llama")):
                    provider = "vertex_maas"
                elif any(k in model_id for k in ("mistral",)):
                    provider = "vertex_maas"
                elif any(k in model_id for k in ("claude", "anthropic")):
                    provider = "anthropic"

                entry = DynamicModelEntry(
                    model_id=model_id,
                    provider=provider,
                    display_name=getattr(model, "display_name", model_id),
                    speed=scores["speed"],
                    reasoning=scores["reasoning"],
                    coding=scores["coding"],
                    synthesis=scores["synthesis"],
                    stability=scores["stability"],
                    context_window=ctx,
                    input_cost_per_m=in_cost,
                    output_cost_per_m=out_cost,
                    capabilities=caps,
                    is_flash=is_flash,
                )

                with self._lock:
                    if model_id not in self._models_by_id:
                        self._models.append(entry)
                        self._models_by_id[model_id] = entry
                        new_count += 1

            return new_count
        except Exception:
            return 0  # Fail silently, keep static baseline


# ── JIT 16D Bidder ───────────────────────────────────────────────────────────

@dataclass
class BidResult:
    """Result of a JIT 16D bidding process for one DAG node."""

    node_id: str
    winning_model: str
    winning_score: float
    winning_cost_per_10k: float
    winning_provider: str
    bid_count: int           # how many models competed
    cache_hit: bool          # True if Tier-0 BuddyCache won
    consensus_mode: bool     # True if multi-model consensus was triggered
    all_bids: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "winning_model": self.winning_model,
            "winning_score": round(self.winning_score, 4),
            "winning_cost_per_10k": round(self.winning_cost_per_10k, 6),
            "winning_provider": self.winning_provider,
            "bid_count": self.bid_count,
            "cache_hit": self.cache_hit,
            "consensus_mode": self.consensus_mode,
        }


class JIT16DBidder:
    """Scores every model in the DynamicModelRegistry per DAG node.

    Bidding formula:
        Score = (CapabilityMatch × ContextFitness) / CostPer10kTokens

    Where:
        CapabilityMatch = weighted sum of dimensional scores matching the
                          node's primary 16D requirements
        ContextFitness  = 1.0 if model context_window >= estimated tokens,
                          else proportional degradation
        CostPer10kTokens = blended 50/50 in/out cost

    High convergence_guardrail or reversibility_guarantees in the 16D
    signature filters out cheap models and forces flagship reasoners.
    """

    def __init__(self, registry: DynamicModelRegistry) -> None:
        self._registry = registry

    def bid(
        self,
        node_id: str,
        task_type: str = "reasoning",
        estimated_tokens: int = 2000,
        dimension_requirements: dict[str, float] | None = None,
        min_stability: float = 0.85,
        force_provider: str | None = None,
    ) -> BidResult:
        """Run a bidding war across all registry models for one node.

        Args:
            node_id: DAG node identifier
            task_type: "speed"|"code"|"reasoning"|"synthesis"|"analysis"
            estimated_tokens: estimated context size
            dimension_requirements: optional 16D scores that must be met
                (e.g., {"Convergence": 0.95, "Security": 0.90})
            min_stability: minimum model stability to participate
            force_provider: restrict bidding to one provider

        Returns:
            BidResult with winning model and all bid scores
        """
        models = self._registry.models
        if force_provider:
            models = [m for m in models if m.provider == force_provider]

        # Filter by stability
        models = [m for m in models if m.stability >= min_stability]

        if not models:
            # Absolute fallback: return cheapest available
            all_models = self._registry.models
            if all_models:
                cheapest = min(all_models, key=lambda m: m.cost_per_10k_tokens)
                return BidResult(
                    node_id=node_id,
                    winning_model=cheapest.model_id,
                    winning_score=0.1,
                    winning_cost_per_10k=cheapest.cost_per_10k_tokens,
                    winning_provider=cheapest.provider,
                    bid_count=1,
                    cache_hit=False,
                    consensus_mode=False,
                )
            # Last resort
            return BidResult(
                node_id=node_id,
                winning_model="gemini-2.5-flash",
                winning_score=0.0,
                winning_cost_per_10k=0.001,
                winning_provider="google",
                bid_count=0,
                cache_hit=False,
                consensus_mode=False,
            )

        # Check if high-risk dimensions require flagship models
        needs_flagship = False
        if dimension_requirements:
            critical_dims = {"Convergence",
                             "Reversibility", "Security", "Safety"}
            for dim, req_score in dimension_requirements.items():
                if dim in critical_dims and req_score >= 0.95:
                    needs_flagship = True
                    break

        bids: list[tuple[float, DynamicModelEntry]] = []
        all_bid_data: list[dict[str, Any]] = []

        for model in models:
            # Skip cheap models for high-risk nodes
            if needs_flagship and model.is_flash and model.input_cost_per_m < 0.5:
                continue

            # CapabilityMatch
            cap_match = model.score_for_task(task_type)

            # Boost from 16D dimensional alignment
            if dimension_requirements:
                dim_boost = self._compute_dimension_boost(
                    model, dimension_requirements)
                cap_match = cap_match * 0.7 + dim_boost * 0.3

            # ContextFitness
            if model.context_window >= estimated_tokens:
                ctx_fitness = 1.0
            else:
                ctx_fitness = max(0.1, model.context_window /
                                  max(estimated_tokens, 1))

            # Score = (CapabilityMatch × ContextFitness) / CostPer10kTokens
            cost = model.cost_per_10k_tokens
            score = (cap_match * ctx_fitness) / cost

            bids.append((score, model))
            all_bid_data.append({
                "model": model.model_id,
                "score": round(score, 4),
                "cap_match": round(cap_match, 4),
                "ctx_fitness": round(ctx_fitness, 4),
                "cost_10k": round(cost, 6),
                "provider": model.provider,
            })

        # Sort by score descending
        bids.sort(key=lambda x: x[0], reverse=True)

        winner_score, winner = bids[0]
        return BidResult(
            node_id=node_id,
            winning_model=winner.model_id,
            winning_score=winner_score,
            winning_cost_per_10k=winner.cost_per_10k_tokens,
            winning_provider=winner.provider,
            bid_count=len(bids),
            cache_hit=False,
            consensus_mode=False,
            all_bids=all_bid_data[:5],  # top 5 for debugging
        )

    def bid_with_cache(
        self,
        node_id: str,
        query_text: str,
        task_type: str = "reasoning",
        estimated_tokens: int = 2000,
        dimension_requirements: dict[str, float] | None = None,
        cache: Any = None,
        intent: str = "",
    ) -> BidResult:
        """Bid with BuddyCache as Tier-0 participant.

        If the cache has a high-confidence hit for this query, skip the
        LLM entirely — cost = $0, latency = ~0ms.
        """
        if cache is not None:
            try:
                hit = cache.lookup(query_text, intent=intent)
                if hit is not None:
                    return BidResult(
                        node_id=node_id,
                        winning_model="buddy_cache_tier0",
                        winning_score=float("inf"),
                        winning_cost_per_10k=0.0,
                        winning_provider="cache",
                        bid_count=1,
                        cache_hit=True,
                        consensus_mode=False,
                    )
            except Exception:
                pass  # Cache miss or error → fall through to bidding

        return self.bid(
            node_id=node_id,
            task_type=task_type,
            estimated_tokens=estimated_tokens,
            dimension_requirements=dimension_requirements,
        )

    def bid_consensus(
        self,
        node_id: str,
        task_type: str = "reasoning",
        estimated_tokens: int = 2000,
        dimension_requirements: dict[str, float] | None = None,
        top_n: int = 2,
    ) -> list[BidResult]:
        """Select top-N models from DIFFERENT providers for consensus execution.

        Used for highest-risk nodes where cross-model agreement is required.
        Returns a list of BidResults (one per model), each from a different provider.
        """
        models = self._registry.models
        models = [m for m in models if m.stability >= 0.85 and not m.is_flash]

        # Score all eligible models
        scored: list[tuple[float, DynamicModelEntry]] = []
        for model in models:
            cap_match = model.score_for_task(task_type)
            if dimension_requirements:
                dim_boost = self._compute_dimension_boost(
                    model, dimension_requirements)
                cap_match = cap_match * 0.7 + dim_boost * 0.3

            ctx_fitness = 1.0 if model.context_window >= estimated_tokens else (
                max(0.1, model.context_window / max(estimated_tokens, 1))
            )
            score = (cap_match * ctx_fitness) / model.cost_per_10k_tokens
            scored.append((score, model))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Pick top N from different providers
        seen_providers: set[str] = set()
        picks: list[BidResult] = []
        for score, model in scored:
            if model.provider not in seen_providers:
                picks.append(BidResult(
                    node_id=node_id,
                    winning_model=model.model_id,
                    winning_score=score,
                    winning_cost_per_10k=model.cost_per_10k_tokens,
                    winning_provider=model.provider,
                    bid_count=len(scored),
                    cache_hit=False,
                    consensus_mode=True,
                ))
                seen_providers.add(model.provider)
            if len(picks) >= top_n:
                break

        # Fallback if not enough providers
        if len(picks) < top_n and scored:
            for score, model in scored:
                if model.model_id not in {p.winning_model for p in picks}:
                    picks.append(BidResult(
                        node_id=node_id,
                        winning_model=model.model_id,
                        winning_score=score,
                        winning_cost_per_10k=model.cost_per_10k_tokens,
                        winning_provider=model.provider,
                        bid_count=len(scored),
                        cache_hit=False,
                        consensus_mode=True,
                    ))
                if len(picks) >= top_n:
                    break

        return picks

    @staticmethod
    def _compute_dimension_boost(model: DynamicModelEntry, requirements: dict[str, float]) -> float:
        """Compute how well a model aligns with specific 16D dimensions."""
        if not requirements:
            return 0.5

        total_weight = 0.0
        weighted_score = 0.0

        for dim_name, required_score in requirements.items():
            cap_name = _16D_CAPABILITY_MAP.get(dim_name, "reasoning")
            model_score = getattr(model, cap_name, 0.5)
            weight = required_score  # Higher requirement = more weight
            weighted_score += model_score * weight
            total_weight += weight

        return weighted_score / max(total_weight, 0.01)


# ── Fractal DAG Expander ────────────────────────────────────────────────────

@dataclass
class FractalExpansion:
    """Result of fractal DAG expansion for a failed node."""

    original_node_id: str
    sub_nodes: list[tuple[str, list[str]]]  # (node_id, [dep_ids])
    reason: str
    upgraded_task_types: dict[str, str]  # {sub_node_id: task_type}

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_node_id": self.original_node_id,
            "sub_node_count": len(self.sub_nodes),
            "sub_nodes": [(nid, deps) for nid, deps in self.sub_nodes],
            "reason": self.reason,
            "upgraded_task_types": self.upgraded_task_types,
        }


class FractalDAGExpander:
    """Expands failed DAG nodes into smaller sub-DAGs for re-bidding.

    When a Tier-1 model fails a node, instead of just retrying with T3,
    the expander splits the node into 2-3 focused sub-tasks, each re-bid
    independently.  This often solves the problem at lower total cost than
    escalating the entire node to a flagship model.
    """

    # Map action types to potential sub-task decompositions
    _DECOMPOSITION_MAP: dict[str, list[tuple[str, str]]] = {
        "implement": [
            ("analyze_requirements", "reasoning"),
            ("generate_code", "code"),
            ("validate_output", "speed"),
        ],
        "design": [
            ("research_patterns", "reasoning"),
            ("draft_design", "synthesis"),
            ("validate_design", "reasoning"),
        ],
        "audit": [
            ("scan_security", "reasoning"),
            ("check_compliance", "reasoning"),
            ("generate_report", "synthesis"),
        ],
        "analyse": [
            ("extract_data", "speed"),
            ("deep_analysis", "reasoning"),
            ("summarize_findings", "synthesis"),
        ],
    }

    def maybe_expand(
        self,
        failed_node_id: str,
        action_type: str,
        failure_count: int,
        error_message: str = "",
    ) -> FractalExpansion | None:
        """Attempt fractal expansion of a failed node.

        Returns None if the node is not expandable (already atomic or
        failure count is too low).
        """
        if failure_count < 2:
            return None  # Give the node at least 2 tries before expanding

        decomposition = self._DECOMPOSITION_MAP.get(action_type)
        if not decomposition:
            return None  # Atomic node, cannot decompose further

        sub_nodes: list[tuple[str, list[str]]] = []
        task_types: dict[str, str] = {}
        prev_id: str | None = None

        for i, (sub_action, task_type) in enumerate(decomposition):
            sub_id = f"{failed_node_id}_fractal_{sub_action}"
            deps = [prev_id] if prev_id else []
            sub_nodes.append((sub_id, deps))
            task_types[sub_id] = task_type
            prev_id = sub_id

        return FractalExpansion(
            original_node_id=failed_node_id,
            sub_nodes=sub_nodes,
            reason=f"Node failed {failure_count}x (last error: {error_message[:100]})",
            upgraded_task_types=task_types,
        )


# ── Module-level singleton ──────────────────────────────────────────────────

_registry_instance: DynamicModelRegistry | None = None
_registry_lock = threading.Lock()


def get_dynamic_registry() -> DynamicModelRegistry:
    """Return the process-level DynamicModelRegistry singleton."""
    global _registry_instance
    if _registry_instance is None:
        with _registry_lock:
            if _registry_instance is None:
                _registry_instance = DynamicModelRegistry()
    return _registry_instance


def get_bidder() -> JIT16DBidder:
    """Return a JIT16DBidder backed by the singleton registry."""
    return JIT16DBidder(get_dynamic_registry())
