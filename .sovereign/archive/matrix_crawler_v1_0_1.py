# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_MATRIX_CRAWLER.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/kernel/cognitive/matrix_crawler.py
# WHEN: 2026-04-01T16:35:57.955861+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MATRIX_CRAWLER | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/matrix_crawler.py
# WHEN: 2026-04-01T13:56:00.000000
# WHY: Rule 3/9 - Context Ingestion across 7 Federated Workspaces
# HOW: Recursive Traversal with Heuristic Value Extraction
# PURITY: 1.00
# ==========================================================

import os
import asyncio
import logging
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any
from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic, TIER_MEDIUM

logger = logging.getLogger("MatrixCrawler")

WORKSPACES = [
    "/Users/oripridan/ANTIGRAVITY/tooloo-v2",
    "/Users/oripridan/Downloads/MR1107_SigneJakobsen",
    "/Users/oripridan/Downloads/MR1202_SambasevamShanmugam",
    "/Users/oripridan/Downloads/RomanStyx_SevenFeel",
    "/Users/oripridan/Downloads/RomanStyx_SevenFeel 2",
    "/Users/oripridan/Downloads/Simplemachine_FollowMe",
    "/Users/oripridan/Downloads/Simplemachine_Ingloria"
]

class MatrixCrawler:
    """
    Ingests the 'Soul of the System' across all federated workspaces.
    Prioritizes .md, README, and core system files.
    """

    def __init__(self):
        self.priority_extensions = [".md", ".MD", ".txt", ".yaml", ".yml", ".py", ".js", ".json"]
        self.ignore_dirs = [".git", "node_modules", ".gemini", "dist", "build", "venv", "__pycache__"]

    async def execute_crawl(self, limit_per_ws=50):
        logger.info(f"Matrix Crawler: Starting Ingestion for {len(WORKSPACES)} Workspaces...")
        memory = await get_memory_logic()
        total_ingested = 0

        for ws in WORKSPACES:
            ws_path = Path(ws)
            if not ws_path.exists():
                logger.warning(f"Workspace Path not found: {ws}")
                continue

            logger.info(f" -> Ingesting Workspace: {ws_path.name}")
            ingested = await self._crawl_path(ws_path, memory, limit=limit_per_ws)
            total_ingested += ingested

        logger.info(f"Matrix Crawler: MISSION_COMPLETE. Total Engrams Ingested: {total_ingested}")
        await memory.soul_sync()
        return total_ingested

    async def _crawl_path(self, path: Path, memory, limit=50) -> int:
        count = 0
        for root, dirs, files in os.walk(path):
            # Prune ignore_dirs
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                f_path = Path(root) / file
                if f_path.suffix in self.priority_extensions:
                    try:
                        # Extract the Soul: First 2KB for context
                        with open(f_path, 'r', errors='ignore') as f:
                             content = f.read(2048)
                        
                        engram_id = f"en_ws_{hash(str(f_path)) % 100000}"
                        payload = {
                            "type": "workspace_context",
                            "source": str(f_path),
                            "workspace": str(path),
                            "extension": f_path.suffix,
                            "text": content,
                            "full_md": f"# CONTEXT_ENGRAM: {f_path.name}\n\n{content}",
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                        }
                        await memory.store_engram(engram_id, payload, layer=TIER_MEDIUM)
                        count += 1
                        if count >= limit: break
                    except Exception as e:
                        logger.error(f"Ingestion Fault for {f_path}: {e}")
            
            if count >= limit: break
        return count

if __name__ == "__main__":
    async def run_test():
        crawler = MatrixCrawler()
        await crawler.execute_crawl(limit_per_ws=10) # Quick test pulse
    asyncio.run(run_test())
