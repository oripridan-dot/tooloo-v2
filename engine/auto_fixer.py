"""
engine/auto_fixer.py — Automated Code-Fixer (Pyright).

Integrates the "Self-Healing" static analysis loop. Plugs in Pyright
diagnostics, parses the JSON error output, and runs an automated fix loop
using the dynamic model tier.
"""
import subprocess
import json
import logging
from typing import List, Dict, Any

from engine.model_garden import get_garden

logger = logging.getLogger(__name__)

class AutoFixLoop:
    def __init__(self):
        self.garden = get_garden()
        
    def _run_pyright(self, filepath: str) -> List[Dict[str, Any]]:
        """Runs pyright --outputjson on a target file."""
        try:
            # Assumes pyright is available in the environment path
            result = subprocess.run(
                ["pyright", "--outputjson", filepath],
                capture_output=True,
                text=True
            )
            # Pyright exists with non-zero code if it finds type errors
            data = json.loads(result.stdout)
            return data.get("generalDiagnostics", [])
        except Exception as e:
            logger.error(f"Pyright execution failed: {e}")
            return []

    def analyze_and_fix(self, filepath: str, model_tier: int = 3) -> bool:
        """
        Analyzes a file using Pyright. If errors exist, uses the model
        to propose fixes, returning True if fixes were applied.
        """
        diagnostics = self._run_pyright(filepath)
        if not diagnostics:
            logger.info(f"AutoFix: {filepath} is clean.")
            return False
            
        logger.warning(f"AutoFix: Found {len(diagnostics)} issues in {filepath}. Attempting heal...")
        
        # Read the file
        try:
            with open(filepath, "r") as f:
                code_content = f.read()
        except:
            return False
            
        # Distill error list
        error_summary = []
        for d in diagnostics:
            if d.get("severity") in ("error", "warning"):
                msg = d.get("message", "")
                r = d.get("range", {}).get("start", {})
                line = r.get("line", 0) + 1
                error_summary.append(f"Line {line}: {msg}")
                
        if not error_summary:
            return False
            
        prompt = (
            "You are the TooLoo V2 Auto-Correction Agent.\n"
            "The following Python code has static analysis type errors/warnings reported by Pyright.\n"
            "Analyze the errors, fix the code, and return the ENTIRE updated file content.\n\n"
            "Do NOT include markdown formatting. Return purely raw code.\n\n"
            f"ERRORS:\n" + "\n".join(error_summary) + "\n\n"
            "ORIGINAL CODE:\n" + code_content
        )
        
        model_id = self.garden.get_tier_model(tier=model_tier, intent="HEAL")
        try:
            response = self.garden.invoke(model_id, prompt)
            new_code = response.text.strip()
            
            # Basic sanitize
            if new_code.startswith("```python"):
                new_code = new_code[9:]
            elif new_code.startswith("```"):
                new_code = new_code[3:]
            if new_code.endswith("```"):
                new_code = new_code[:-3]
                
            # Overwrite file
            with open(filepath, "w") as f:
                f.write(new_code.strip() + "\n")
                
            logger.info(f"AutoFix: Applied patch to {filepath}.")
            return True
        except Exception as e:
            logger.error(f"AutoFix: Refinement failed: {e}")
            return False

