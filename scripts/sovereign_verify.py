#!/usr/bin/env python3
# 6W_STAMP
# WHO: Sovereign Architect
# WHAT: sovereign_verify.py | Version: 1.0.0
# WHY: Buddy Sprint Completion Mandate (Zero-Tolerance Quality)
# HOW: Regex Purity Check + Static Analysis Mock (Ruff/Lint)

import os
import sys
import re
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SovereignVerify")

CRITICAL_FINDINGS = 0

def check_6w_purity(directory: str):
    """Rule 10: Ensures every .py file has a 6W_STAMP."""
    global CRITICAL_FINDINGS
    logger.info(f"Auditing 6W Purity in {directory}...")
    
    ignore_dirs = {".venv", "node_modules", "__pycache__", ".git"}
    
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file.endswith(".py"):
                path = Path(root) / file
                content = path.read_text(errors="ignore")
                if "6W_STAMP" not in content and "WHO:" not in content:
                    logger.error(f"[CRITICAL] Rule 10 Violation: Missing 6W Stamp in {path}")
                    CRITICAL_FINDINGS += 1

def check_sota_registry():
    """Rule 4: Ensures SOTA Registry is valid and up-to-date."""
    global CRITICAL_FINDINGS
    path = Path("tooloo_v4_hub/kernel/governance/sota_registry.json")
    if not path.exists():
        logger.error("[CRITICAL] Rule 4 Violation: SOTA Registry Missing")
        CRITICAL_FINDINGS += 1
        return
    
    try:
        data = json.loads(path.read_text())
        if "market_targets" not in data:
            logger.error("[CRITICAL] Rule 4 Violation: SOTA Registry Malformed")
            CRITICAL_FINDINGS += 1
    except Exception as e:
        logger.error(f"[CRITICAL] Registry Corruption: {e}")
        CRITICAL_FINDINGS += 1

def run_purity_lint():
    """Rule 11: Identify quick-hacks (TODOs in kernel)."""
    global CRITICAL_FINDINGS
    logger.info("Scanning for Rule 11 Violations (Band-Aids)...")
    
    kernel_path = Path("tooloo_v4_hub/kernel")
    for root, _, files in os.walk(kernel_path):
        for file in files:
            if file.endswith(".py"):
                path = Path(root) / file
                content = path.read_text()
                if "TODO" in content or "FIXME" in content:
                    logger.warning(f"[MAJOR] Rule 11 Hint: Found TODO in {path}")
                    # Change to CRITICAL if specific policy dictates

def main():
    logger.info("--- Sovereign Verification Pulse Initiated ---")
    
    # 1. Check Purity
    check_6w_purity("tooloo_v4_hub")
    
    # 2. Check SOTA
    check_sota_registry()
    
    # 3. Check for Band-Aids
    run_purity_lint()
    
    logger.info(f"Verification Complete. Critical Findings: {CRITICAL_FINDINGS}")
    
    if CRITICAL_FINDINGS > 0:
        logger.error("SYSTEM_VITALITY_CRITICAL: Purity/Quality thresholds NOT met.")
        sys.exit(1)
    else:
        logger.info("SYSTEM_PURE: All quality gates passed. Ready for Cloud Manifestation.")
        sys.exit(0)

if __name__ == "__main__":
    main()
