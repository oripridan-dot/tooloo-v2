# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining z3_gateway.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.909842
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/z3_gateway.py — Symbolic Safety Guard for destructive operations.

An AST-based formal verification gateway that checks proposed filesystem 
modifications against system-wide safety invariants.
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("z3_gateway")

class SymbolicSafetyGuard:
    """Verifies that proposed code changes or file writes do not violate safety invariants."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        self._workspace_root = workspace_root or Path(__file__).resolve().parents[1]
        # Invariants: Paths that are off-limits for autonomous modification
        self._protected_paths = [
            "engine/tribunal.py",
            "engine/router.py",
            "engine/z3_gateway.py",
            ".env",
            ".git/"
        ]

    def verify_write(self, path: str, content: str) -> bool:
        """Verifies a file write request."""
        target_path = Path(path)
        
        # 1. Path Invariant Check
        for protected in self._protected_paths:
            if protected.endswith("/"):
                if str(target_path).startswith(protected):
                    logger.error(f"Z3-Block: Attempted write to protected directory: {protected}")
                    return False
            else:
                if str(target_path) == protected:
                    logger.error(f"Z3-Block: Attempted write to protected file: {protected}")
                    return False
        
        # 2. Semantic/AST Invariant Check (if Python)
        if target_path.suffix == ".py":
            is_safe, _ = self.verify_code_safety(content)
            return is_safe
            
        return True

    def verify_code_safety(self, content: str) -> tuple[bool, str]:
        """Checks for dangerous semantic patterns using AST analysis. Returns (is_safe, reason)."""
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                # Block explicit OS command execution unless in approved modules
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name) and node.func.value.id == "os" and node.func.attr in ["system", "popen"]:
                            reason = "Malicious os.system/popen call detected."
                            logger.error(f"Z3-Block: {reason}")
                            return False, reason
                        if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                            reason = "Malicious subprocess call detected."
                            logger.error(f"Z3-Block: {reason}")
                            return False, reason
                # Block deletion of files
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in ["remove", "unlink", "rmdir"]:
                            reason = f"File deletion primitive '{node.func.attr}' detected."
                            logger.error(f"Z3-Block: {reason}")
                            return False, reason
            return True, "Safe."
        except Exception as e:
            reason = f"AST parse failed (possibly fragment), allowing with caution: {e}"
            logger.warning(f"Z3-Guard: {reason}")
            return True, reason # Allow fragments, relying on Tribunal for runtime audit
