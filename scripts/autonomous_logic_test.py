import asyncio
import logging
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tooloo_v4_hub.organs.vertex_organ.vertex_logic import get_vertex_logic
from tooloo_v4_hub.kernel.cognitive.crucible_validator import get_crucible_validator

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("ForensicLogic")

STRESS_PROMPT = """
MISSION: DESIGN A 16-DIMENSIONAL FEDERATED ORGAN SYNCHRONIZER.
CONSTRAINTS:
1. Enforce Rule 7 (Zero Bloat).
2. Handle eventual consistency via a CRDT-backed psyche layer.
3. Must use Federated SDK handshakes for all cross-region mutations.
4. Define the 6W Metadata stamp for the core synchronizer node.
"""

async def run_forensic_test():
    print("============================================================")
    print(" SOVEREIGN HUB: ROUND 1 - FORENSIC LOGIC VERIFICATION")
    print("============================================================")
    
    logic = await get_vertex_logic()
    validator = get_crucible_validator()
    
    specialists = [
        {"id": "claude-3-5-sonnet-20240620", "provider": "anthropic", "domain": "Logic/Architecture"},
        {"id": "gemini-1.5-pro", "provider": "google", "domain": "Context/Audit"},
        {"id": "gpt-4o", "provider": "openai", "domain": "Vision/Creative"},
        {"id": "meta/llama3-3@llama-3.3-70b-instruct", "provider": "meta", "domain": "Efficiency/Logistics"}
    ]
    
    results = []
    
    for spec in specialists:
        print(f"\n[STRESS TEST] Specialist: {spec['provider'].upper()} ({spec['id']})")
        print(f"Domain focus: {spec['domain']}")
        
        try:
            # Dispatch to provider
            res = await logic.provider_chat(STRESS_PROMPT, spec['id'], spec['provider'])
            content = res.get("content", "")
            
            # Audit the reasoning via Crucible (Primitive 8)
            audit = await validator.audit_code("forensic_reconstruction.py", content)
            
            print(f"  -> PURITY SCORE: {audit.purity_score:.2f}")
            print(f"  -> STATUS:       {audit.status}")
            
            results.append({
                "model": spec['id'],
                "score": audit.purity_score,
                "status": audit.status,
                "findings": audit.findings[:3]
            })
        except Exception as e:
            logger.error(f"  !! Logic Dispatch Fault: {e}")

    print("\n[VERDICT] Forensic Logic Synchronized.")
    print("============================================================")
    return results

if __name__ == "__main__":
    asyncio.run(run_forensic_test())
