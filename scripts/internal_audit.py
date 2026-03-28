# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining internal_audit.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.391604
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import os
import sys
import logging
import asyncio
from pathlib import Path
from engine.config import settings
from engine.model_garden import get_garden
from engine.utils import extract_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inward_audit")

async def audit_providers():
    print("\n--- INWARD POWER AUDIT: LLM Providers ---")
    garden = get_garden()
    
    providers = ["google", "openai", "deepseek", "gemini_api"]
    for p in providers:
        has_key = False
        if p == "google": has_key = bool(os.getenv("GCP_PROJECT_ID"))
        elif p == "openai": has_key = "your_key" not in (os.getenv("OPENAI_API_KEY") or "")
        elif p == "gemini_api": has_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        
        status = "READY" if has_key else "MISSING_KEY"
        print(f"[{p.upper():<10}] {status}")

async def audit_models():
    print("\n--- INWARD POWER AUDIT: Regional Availability ---")
    garden = get_garden()
    # Test a Tier 1 Flash call (lightweight)
    try:
        model_id = garden.get_tier_model(1, "AUDIT")
        print(f"Tier 1 (Flash) Selection: {model_id}")
    except Exception as e:
        print(f"Tier 1 Selection Failed: {e}")

async def audit_filesystem():
    print("\n--- INWARD POWER AUDIT: Repository Integrity ---")
    paths = [
        "engine/config.py",
        "engine/model_garden.py",
        "engine/auto_fixer.py",
        "engine/utils.py",
        ".env"
    ]
    for p in paths:
        exists = Path(p).exists()
        print(f"[{'FOUND' if exists else 'MISSING':<7}] {p}")

async def audit_6w():
    print("\n--- INWARD POWER AUDIT: 6W Coverage ---")
    try:
        from engine.stamping_engine import StampingEngine
        engine = StampingEngine()
        
        # Audit engine/ and scripts/
        e_report = engine.audit_directory("engine")
        s_report = engine.audit_directory("scripts")
        
        stamped = len(e_report["stamped"]) + len(s_report["stamped"])
        unstamped = len(e_report["unstamped"]) + len(s_report["unstamped"])
        total = stamped + unstamped
        
        percentage = (stamped / total * 100) if total > 0 else 0
        print(f"Total Files Audited: {total}")
        print(f"Stamped: {stamped}")
        print(f"Unstamped: {unstamped}")
        print(f"6W COVERAGE: {percentage:.1f}%")
        
        if unstamped > 0:
            print("\nWARNING: Some files are missing 6W stamps!")
            for f in e_report["unstamped"][:5]: print(f" - {f}")
    except Exception as e:
        print(f"6W Audit Failed: {e}")

async def main():
    print("\n" + "★" * 60)
    print("  TOO LOO V2 — INTERNAL AUDIT (INWARD POWER)")
    print("★" * 60)
    
    await audit_providers()
    await audit_models()
    await audit_filesystem()
    await audit_6w()
    
    print("\nAudit Complete.\n")

if __name__ == "__main__":
    asyncio.run(main())
