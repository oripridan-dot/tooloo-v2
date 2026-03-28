# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining migrate_adversarial_history.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.397856
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import sys
import asyncio
from pathlib import Path

# Ensure repo root is on path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engine.recursive_summarizer import RecursiveSummaryAgent

async def main():
    print("🚀 Initializing RecursiveSummaryAgent...")
    agent = RecursiveSummaryAgent()
    print("📦 Migrating adversarial evolution logs to Cold Memory (Firestore)...")
    result = await agent.migrate_adversarial_logs()
    print(f"✅ Migration Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
