import asyncio
import logging
import sys
import os
import hashlib
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic, TIER_LONG

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("KnowledgeIngestion")

KNOWLEDGE_TARGETS = [
    "GEMINI.md",
    "docs/architecture/system_mapping.md",
    "docs/architecture/SOVEREIGN_CHAT_ARCHITECTURE.md"
]

async def run_ingestion_pulse():
    print("============================================================")
    print(" SOVEREIGN HUB: ROUND 4 - KNOWLEDGE INGESTION PULSE")
    print("============================================================")
    
    memory = await get_memory_logic()
    root = Path("/Users/oripridan/ANTIGRAVITY/tooloo-v2")
    
    ingested_count = 0
    
    for relative_path in KNOWLEDGE_TARGETS:
        full_path = root / relative_path
        if not full_path.exists():
            logger.warning(f"  !! Missing Knowledge Target: {relative_path}")
            continue
            
        print(f"[INGESTING] {relative_path}...")
        try:
            content = full_path.read_text(errors="ignore")
            # Generate a stable ID based on path
            engram_id = f"core_kb_{hashlib.md5(relative_path.encode()).hexdigest()[:8]}"
            
            # Use store_engram (Rule 3/9)
            result = await memory.store_engram(
                engram_id=engram_id,
                data={
                    "text": content,
                    "type": "architectural_blueprint",
                    "source": relative_path
                },
                layer=TIER_LONG
            )
            
            if result.get("status") == "success":
                print(f"  -> SUCCESS: Stored in LONG_TIER memory.")
                ingested_count += 1
            else:
                 logger.error(f"  !! Ingestion Error: {result.get('message')}")
        except Exception as e:
            logger.error(f"  !! Failed to ingest {relative_path}: {e}")

    print(f"\n[VERDICT] {ingested_count}/{len(KNOWLEDGE_TARGETS)} Knowledge Nodes Synchronized.")
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(run_ingestion_pulse())
