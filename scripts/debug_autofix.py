# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining debug_autofix.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.405037
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================


import sys
import os
import traceback
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

try:
    from engine.auto_fixer import AutoFixLoop
    from engine.config import settings
    
    print(f"Debugger: settings.gcp_project_id={settings.gcp_project_id}")
    
    loop = AutoFixLoop()
    print("Debugger: AutoFixLoop initialized.")
    
    # Simulate a tiny fix
    code = "def hello(): pass"
    error = "SyntaxError: at line 1"
    
    print("Debugger: Calling analyze_and_fix...")
    result = loop.analyze_and_fix("test_file.py", code, error)
    print(f"Debugger: Result={result}")
    
except Exception as e:
    print("DEBUGGER CAUGHT EXCEPTION:")
    traceback.print_exc()
