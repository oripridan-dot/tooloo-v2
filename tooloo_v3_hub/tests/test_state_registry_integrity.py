# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: TEST_STATE_REGISTRY_INTEGRITY.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v3_hub/tests/test_state_registry_integrity.py
# WHEN: 2026-03-31T14:26:13.340166+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: test, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
import json
from pathlib import Path
from tooloo_v3_hub.kernel.cognitive.ouroboros import get_ouroboros

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestRegistry")

async def test_registry_persistence():
    logger.info("--- Testing Registry Persistence ---")
    registry_path = Path("tooloo_v3_hub/kernel/governance/state_registry.json")
    
    assert registry_path.exists(), "State Registry is missing"
    
    # Verify Content
    with open(registry_path, "r") as f:
        registry = json.load(f)
        
    assert "tooloo_v3_hub/main.py" in registry, "main.py entry missing"
    assert "_v1_0_1.py" in registry["tooloo_v3_hub/main.py"]["pure_path"], "Redirect path incorrect"
    logger.info("✅ Registry Persistence Verified.")

async def test_diagnostic_redirection():
    logger.info("--- Testing Diagnostic Redirection (Rule 17) ---")
    ouro = get_ouroboros()
    
    # 1. Verify 0 flaws found because it's scanning the pure variants
    flaws = await ouro.run_diagnostics()
    
    assert len(flaws) == 0, f"Diagnostic failed to redirect. Found {len(flaws)} legacy flaws."
    logger.info("✅ Diagnostic Redirection Verified.")

if __name__ == "__main__":
    asyncio.run(test_registry_persistence())
    print("\n")
    asyncio.run(test_diagnostic_redirection())