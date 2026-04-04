# 6W_STAMP
# WHO: TooLoo V4.2 (Sovereign Architect)
# WHAT: MODULE_SKILL_FORGE | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/skill_forge.py
# WHEN: 2026-04-04T08:00:00.000000
# WHY: Rule 12 (Self-Healing) & Autonomous Capability Expansion (JIT Forge)
# HOW: LLM-driven pure Python generation validated by CrucibleValidator
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, autonomy, jit, skill-generation
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client
from tooloo_v4_hub.kernel.cognitive.crucible_validator import get_crucible_validator

logger = logging.getLogger("SkillForge")

class SkillForge:
    """
    Sovereign Capability Forge.
    Generates missing skills on-demand intelligently, ensures they pass the Crucible,
    and writes them permanently to the tooloo_v4_hub/skills/ directory.
    """
    
    def __init__(self, root_dir: str = "."):
        self.root = Path(root_dir).resolve()
        self.skills_dir = self.root / "tooloo_v4_hub" / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._llm = get_llm_client()
        self._validator = get_crucible_validator()

    async def forge_skill(self, skill_name: str, intent_description: str) -> bool:
        """
        Background autonomous pulse to forge a new capability.
        Returns True if successfully fabricated and stamped, False otherwise.
        """
        logger.info(f"🔨 Sovereign Forge: Initiating JIT fabrication for '{skill_name}' (Intent: {intent_description})")
        
        # We need a proper structured prompt to output pure, safe Python code suitable for JIT execution
        system_instruction = """You are the Sovereign Tool Forge. 
You write ephemeral Python scripts for the tooloo_v4_hub. 
Your code is executed via `exec()` when intercepted as a 'jit_skill'.
The script MUST define an asynchronous function named `process(arguments: dict) -> any`.
The script MUST import any standard libraries it requires.
You MUST include a '# 6W_STAMP' accountability block at the top of the file!
Do not use `sys.exit()` or mutate the filesystem destructively without extreme care.
Use Rule 7 clean and optimal coding styles.
OUTPUT ONLY THE PYTHON CODE. DO NOT INCLUDE MARKDOWN TICKS (```python ... ```). JUST THE RAW CODE."""

        prompt = f"""
FORGE MANDATE: {skill_name}.py
INTENT: {intent_description}

Write the raw Python file contents for this skill. 
It must expose the `process(arguments)` function as requested.
Start the file with:
# 6W_STAMP
# WHO: Buddy (Forge)
# WHAT: {skill_name}.py
# WHERE: tooloo_v4_hub/skills/
"""
        
        try:
            # Generate the raw python using 2.5 Pro
            raw_code = await self._llm.generate_thought(
                prompt=prompt, 
                system_instruction=system_instruction, 
                model_tier="pro"
            )
            
            # Clean possible markdown injection just in case
            if raw_code.startswith("```python"):
                raw_code = raw_code.split("```python", 1)[1]
            if raw_code.startswith("```"):
                raw_code = raw_code.split("```", 1)[1]
            if raw_code.endswith("```"):
                raw_code = raw_code.rsplit("```", 1)[0]
            raw_code = raw_code.strip()
            
            # Temporary file write for Crucible
            target_file = self.skills_dir / f"{skill_name}.py"
            
            # Step: Verify Security via Crucible
            # We must wrap the code or simulate file evaluation
            logger.info(f"🔨 Sovereign Forge: Passing {skill_name} into Crucible Validator...")
            
            audit_result = await self._validator.audit_code(str(target_file), raw_code)
            
            if audit_result.purity_score < 0.90 or audit_result.status == "FAIL":
                logger.error(f"❌ Sovereign Forge: JIT code rejected by Crucible ({audit_result.purity_score * 100}% Purity). Findings: {audit_result.findings}")
                return False
                
            # If validated, write permanently 
            with open(target_file, "w") as f:
                f.write(raw_code)
                
            logger.info(f"✅ Sovereign Forge: '{skill_name}' successfully fabricated and stored at {target_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Sovereign Forge Exception: {e}")
            return False

_forge: Optional[SkillForge] = None

def get_skill_forge() -> SkillForge:
    global _forge
    if _forge is None:
        _forge = SkillForge()
    return _forge
