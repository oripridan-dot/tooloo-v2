# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: TEST_PATHWAY_B_v1.0.0
# WHERE: tooloo_v3_hub/tests/test_pathway_b.py
# WHEN: 2026-03-29T16:55:00.000000
# WHY: Ensure competitive reasoning logic is mathematically sound
# HOW: Integrated Pytest Suite
# ==========================================================

import asyncio
import pytest
from tooloo_v3_hub.kernel.cognitive.pathway_b import get_pathway_manager

@pytest.mark.anyio
async def test_pathway_b_selection():
    """Verifies that PathwayB correctly selects the winner based on telemetry."""
    manager = get_pathway_manager()
    
    # Mock strategies with different scoring characteristics
    strategies = [
        {"name": "Slow-But-Perfect", "drift_bias": 0.01}, # Low latency, high alignment
        {"name": "Fast-But-Drifting", "drift_bias": 0.8}, # High latency penalty, low alignment
    ]
    
    # Mock executor that simulates different latencies
    async def mock_executor(goal, context, strategy):
        if strategy["name"] == "Slow-But-Perfect":
            await asyncio.sleep(0.5)
        else:
            await asyncio.sleep(0.01)
            
        return {
            "status": "success",
            "payload": {
                "stamp": {"who": "test", "what": "test", "where": "test", "why": "test", "how": "test", "when": "now"}
            }
        }

    winner = await manager.resolve_competitive("test goal", {}, strategies, mock_executor)
    
    assert winner is not None
    assert winner.status == "SUCCESS"
    # Slow-But-Perfect should win due to high alignment (drift_bias 0.01) 
    # despite the 500ms vs 10ms latency (latency penalty is small -0.001 * 500 = -0.5)
    assert winner.name == "Slow-But-Perfect"

@pytest.mark.anyio
async def test_pathway_b_failure_handling():
    """Verifies that failed variants do not win."""
    manager = get_pathway_manager()
    
    strategies = [{"name": "Failure-Path", "drift_bias": 0.0}]
    
    async def failing_executor(goal, context, strategy):
        raise ValueError("Critical System Fault")

    winner = await manager.resolve_competitive("test goal", {}, strategies, failing_executor)
    assert winner is None
