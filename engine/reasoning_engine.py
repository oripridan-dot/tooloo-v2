"""
TooLoo V2: ReasoningEngine (Wave 0.5)
------------------------------------
Implements "Test-Time Compute" by simulating potential DAG outcomes 
before a single tool is invoked. Part of the Tier-5 Agency evolution.
"""

import logging
from typing import Any
from engine.model_garden import get_garden, CognitiveProfile

logger = logging.getLogger("tooloo.reasoning")

class ReasoningEngine:
    """
    The 'Wave 0.5' deliberation layer.
    
    This engine uses high-capability models with a "Thinking Budget" to 
    simulate the physics of the requested task and identify 'phantom' 
    logic gaps before the MetaArchitect generates the final DAG.
    """

    def __init__(self):
        self._garden = get_garden()
        self._stroke_count = 0
        self._tribunal_report_path = "/Users/oripridan/ANTIGRAVITY/tooloo-v2/security/tribunal_reports.md"

    async def deliberate(self, intent: str, mandate: str, context: dict[str, Any]) -> str:
        """
        Perform pre-execution simulation and strategy audit.
        
        Args:
            intent: The parsed intent (e.g. BUILD, AUDIT).
            mandate: The original user request.
            context: Current workspace state, including file list and focus.
            
        Returns:
            A 'Strategy Audit' string to be injected into Wave 1.
        """
        logger.info(f"Initiating Wave 0.5 Deliberation for intent={intent}")
        
        # Select a Tier-4 model with thinking enabled
        # We use a 16,000 token thinking budget for deep simulations
        profile = CognitiveProfile(
            primary_need="reasoning",
            minimum_tier=4,
            thinking_budget=16000
        )
        
        model_id = self._garden.get_tier_model(4, intent)
        
        prompt = self._build_deliberation_prompt(intent, mandate, context)
        
        try:
            audit = self._garden.call(
                model_id=model_id,
                prompt=prompt,
                max_tokens=4000,
                thinking_budget=16000
            )
            
            # Increase stroke count and check for Ghost Audit
            self._stroke_count += 1
            if self._stroke_count % 10 == 0:
                await self._perform_ghost_audit(mandate, audit)

            logger.info("Wave 0.5 Audit complete.")
            return audit
        except Exception as e:
            logger.error(f"Wave 0.5 Deliberation failed: {e}")
            return "Strategy Audit Unavailable: Proceeding with standard N-Stroke logic."

    def _build_deliberation_prompt(self, intent: str, mandate: str, context: dict[str, Any]) -> str:
        files = context.get("files", [])
        focus = context.get("focus", "N/A")
        
        return f"""
YOU ARE THE PRINCIPAL SYSTEMS ARCHITECT (REASONING MODE).
MANDATE: {mandate}
INTENT: {intent}
CONTEXT: 
- Files: {files[:20]} ... (and {max(0, len(files)-20)} others)
- Focus: {focus}

TASK:
Simulate the execution of this mandate. Identify 'Phantom Logic' gaps, 
circular dependencies, and potential security risks in the proposed 
solution path. 

DO NOT GENERATE CODE. Generate a 'STRATEGY AUDIT' that covers:
1. LATENT RISKS: What could go wrong in the middle of a multi-stroke plan?
2. PHYSICS CHECK: Do we have the tools/files to do this?
3. OPTIMAL TOPOLOGY: Should the DAG be sequential or parallel?

KEEP THE AUDIT CONCISE (max 300 words).
"""

    async def _perform_ghost_audit(self, mandate: str, audit_to_verify: str) -> None:
        """Secondary high-entropy audit to detect Policy Drift."""
        logger.info("TRITUNAL: Initiating GHOST AUDIT for policy alignment.")
        
        # Use a higher-tier model for the audit (Ultra / 2.5-flash-thinking-v1)
        model_id = "gemini-2.5-flash-thinking-v1" 
        
        prompt = f"""
AUDIT THE FOLLOWING REASONING STROKE FOR 'POLICY DRIFT'.
MANDATE: {mandate}
REASONING STROKE: {audit_to_verify}

TASK:
Does the reasoning stroke above justify any architectural violations, security risks, or unsafe actions?
Look for circular logic where the agent justifies a 'HardStop' violation.

OUTPUT:
- STATUS: [CLEAN | DRIFT_DETECTED]
- RATIONALE: Why?
"""
        try:
            result = self._garden.call(model_id=model_id, prompt=prompt, thinking_budget=32000)
            if "DRIFT_DETECTED" in result:
                await self._trigger_hard_stop(mandate, result)
            else:
                logger.info("TRITUNAL: Ghost Audit completed. STATUS: CLEAN.")
        except Exception as e:
            logger.error(f"Ghost Audit failed: {e}")

    async def _trigger_hard_stop(self, mandate: str, rationale: str) -> None:
        """Trigger an immediate system containment."""
        import os
        from datetime import datetime
        
        report = f"""
### TRIBUNAL HARD-STOP: POLICY DRIFT DETECTED
**Timestamp**: {datetime.now().isoformat()}
**Mandate**: {mandate}
**Ghost Audit Rationale**: 
{rationale}

**Action Taken**: Execution Halted. Sandbox isolated.
---
"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self._tribunal_report_path), exist_ok=True)
        with open(self._tribunal_report_path, "a") as f:
            f.write(report)
            
        logger.critical("!!! POLICY DRIFT DETECTED. HARD-STOP TRIGGERED !!!")
        # In a real system, this would raise a fatal engine exception.
        # raise SystemExit("Tribunal Hard-Stop")

_engine_instance: ReasoningEngine | None = None

def get_reasoning_engine() -> ReasoningEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ReasoningEngine()
    return _engine_instance
