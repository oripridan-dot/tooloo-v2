# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_CONSTITUTIONAL_INGESTION.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/tools/constitutional_ingestion.py
# WHEN: 2026-04-03T10:37:24.380458+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

# WHAT: CONSTITUTIONAL_INGESTION.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/tools/constitutional_ingestion.py
# WHY: Rule 1/9: Grounding the AI in Sovereign Identity
# HOW: Parsing GEMINI.md and storing into LONG-tier memory

import asyncio
import re
import logging
import json
from pathlib import Path
from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic, TIER_LONG

logger = logging.getLogger("ConstitutionIngest")

async def ingest():
    print("--- 16-Rule Constitution Ingestion Started ---")
    constitution_path = Path("/Users/oripridan/ANTIGRAVITY/tooloo-v2/GEMINI.md")
    if not constitution_path.exists():
        print(f"Error: {constitution_path} not found.")
        return

    with open(constitution_path, 'r') as f:
        content = f.read()

    # Regex to extract Rules
    # Look for "* **Rule X: Name:** Description" or similar patterns
    rules = re.findall(r"Rule (\d+): (.*?)\*\*(.*?)\n", content, re.DOTALL)
    
    memory = await get_memory_logic()
    count = 0
    
    for r_num, r_name, r_desc in rules:
        r_id = f"rule-{r_num.strip()}"
        payload = {
            "type": "constitutional_rule",
            "number": int(r_num),
            "name": r_name.strip().replace(":", ""),
            "text": r_desc.strip(),
            "full_md": f"Rule {r_num}: {r_name}\n{r_desc}"
        }
        
        # Rule 10 Stamping
        from tooloo_v4_hub.kernel.governance.stamping import SixWProtocol
        protocol = SixWProtocol(
            who="Principal-Architect",
            what=f"SOVEREIGN_LAW_INGESTION: Rule {r_num}",
            where="GEMINI.md",
            why="Rule 1 Grounding",
            how="Manual Mission-Scale Ingestion"
        )
        payload["stamp"] = json.loads(protocol.model_dump_json())
        
        await memory.store_engram(r_id, payload, layer=TIER_LONG)
        count += 1
        print(f"Ingested {r_id} into LONG tier.")

    # Also ingest the 3 Pillars
    pillars = re.findall(r"## The 3 Pillars of Cognitive Routing\n(.*?)\n##", content, re.DOTALL)
    if pillars:
        await memory.store_engram("pillar-routing", {
            "type": "architectural_foundation",
            "name": "3 Pillars of Cognitive Routing",
            "text": pillars[0].strip()
        }, layer=TIER_LONG)
        count += 1
        print("Ingested 3 Pillars into LONG tier.")

    print(f"--- Ingestion Complete. {count} Foundations Manifested in LONG Memory ---")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(ingest())
