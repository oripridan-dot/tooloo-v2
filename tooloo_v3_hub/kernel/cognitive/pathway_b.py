# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: KERNEL_PATHWAY_B_v3.0.0 — Competitive Reasoning
# WHERE: tooloo_v3_hub/kernel/cognitive/pathway_b.py
# WHEN: 2026-03-29T16:45:00.000000
# WHY: Multi-variant resolution ensures the most aligned & performant outcome
# HOW: Parallel Async Dispatches + Weighted Scoring
# ==========================================================

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Callable, Awaitable
from pydantic import BaseModel, Field
from tooloo_v3_hub.kernel.governance.stamping import SixWProtocol, StampingEngine

logger = logging.getLogger("PathwayB")

class ResolutionVariant(BaseModel):
    """Data model representing a single parallel reasoning path."""
    id: str
    name: str
    status: str = "PENDING"
    result: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0
    drift_score: float = 1.0 # (0.0 to 1.0, lower is more aligned target)
    six_w_score: float = 0.0 # (0.0 to 1.0 compliance)
    total_score: float = 0.0
    error: Optional[str] = None

class PathwayBManager:
    """
    The Competitive Resolution Supervisor for TooLoo V3.
    Spawns multiple strategies and selects the optimal path.
    """
    
    def __init__(self):
        self.variants: List[ResolutionVariant] = []
        self.logger = logging.getLogger("PathwayBManager")

    async def resolve_competitive(
        self, 
        goal: str, 
        context: Dict[str, Any], 
        strategies: List[Dict[str, Any]],
        executor: Callable[[str, Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]
    ) -> ResolutionVariant:
        """
        Runs multiple strategies in parallel and returns the Winning Variant.
        """
        self.logger.info(f"Pathway B: Initiating competition for goal: '{goal}'")
        self.variants = []
        
        tasks = []
        for i, strategy in enumerate(strategies):
            variant_id = f"v-{i:02d}"
            variant = ResolutionVariant(id=variant_id, name=strategy["name"])
            self.variants.append(variant)
            tasks.append(self._execute_variant(variant, goal, context, strategy, executor))
            
        # Execute all in parallel
        await asyncio.gather(*tasks)
        
        # Calculate scores and select winner
        winner = self._select_winner()
        
        if winner:
            self.logger.info(f"Pathway B Complete. WINNER: {winner.name} (Score: {winner.total_score:.4f})")
        else:
            self.logger.error("Pathway B: Failed to resolve any valid variants.")
            
        return winner

    async def _execute_variant(
        self, 
        variant: ResolutionVariant, 
        goal: str, 
        context: Dict[str, Any], 
        strategy: Dict[str, Any],
        executor: Callable[[str, Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]
    ):
        """Orchestrates a single execution path."""
        t0 = time.perf_counter()
        variant.status = "RUNNING"
        
        try:
            # Execute the variant using the provided executor (usually Orchestrator instance)
            variant.result = await executor(goal, context, strategy)
            variant.status = "SUCCESS"
            
            # 1. Telemetry: Latency
            variant.latency_ms = (time.perf_counter() - t0) * 1000
            
            # 2. Telemetry: 6W Compliance
            variant.six_w_score = self._calculate_6w_compliance(variant.result)
            
            # 3. Telemetry: Drift (Mocked for current implementation)
            variant.drift_score = strategy.get("drift_bias", 0.5) 
            
            # Finalize Scoring
            variant.total_score = self._compute_score(variant)
            
        except Exception as e:
            variant.status = "FAILED"
            variant.error = str(e)
            self.logger.warning(f"Variant {variant.id} ({variant.name}) failed: {e}")

    def _calculate_6w_compliance(self, result: Dict[str, Any]) -> float:
        """Heuristic check for 6W field presence in the result stamp."""
        stamp = result.get("payload", {}).get("stamp", {}) if isinstance(result, dict) else {}
        required = ["who", "what", "where", "why", "how", "when"]
        matches = sum(1 for k in required if k in stamp)
        return matches / len(required)

    def _compute_score(self, variant: ResolutionVariant) -> float:
        """Weighted selection algorithm (HFN standard)."""
        # Weight vectors
        w_latency = -0.001  # penalized high latency
        w_6w = 1.0          # rewarded compliance
        w_drift = -2.0      # penalized drift from target (Sovereign Purity)
        
        # Base score starts with 1.0
        score = 10.0 
        score += variant.latency_ms * w_latency
        score += variant.six_w_score * w_6w
        score += variant.drift_score * w_drift
        
        return max(0.0, score)

    def _select_winner(self) -> Optional[ResolutionVariant]:
        """Returns the variant with the highest total_score."""
        successful = [v for v in self.variants if v.status == "SUCCESS"]
        if not successful:
            return None
        return max(successful, key=lambda v: v.total_score)

# Global Manager instance
_pathway_manager: Optional[PathwayBManager] = None

def get_pathway_manager() -> PathwayBManager:
    global _pathway_manager
    if _pathway_manager is None:
        _pathway_manager = PathwayBManager()
    return _pathway_manager
