# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: OPENAI_CLIENT.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/openai_organ/openai_client.py
# WHEN: 2026-04-01T00:05:00.000000
# WHY: Rule 13 Federated SOTA Execution via bit-perfect Responses API (Rule 13)
# HOW: OpenAI Python SDK V2.30.0 (March 2026 Standard)
# TIER: T4:zero-trust
# DOMAINS: organ, openai, sota, reasoning, responses-api
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import os
import logging
from typing import Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger("OpenAIClient")

class OpenAIResponseEngine:
    """
    High-Fidelity Client for the OpenAI Responses API.
    Natively supports GPT-5.4 Reasoning tokens and effort calibration.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OpenAI API Key missing. SOTA Reasoning will fail.")
        
        self.client = OpenAI(api_key=self.api_key)

    async def generate_thought(self, prompt: str, model: str = "gpt-5.4", effort: str = "high") -> Dict[str, Any]:
        """
        Rule 4: SOTA Reasoning Pulse.
        Uses the Responses API to capture internal chain-of-thought (CoT).
        """
        try:
            logger.info(f"OpenAI: Initiating Responses API call ({model}) with effort='{effort}'...")
            
            # Using the March 2026 Responses API standard
            response = self.client.responses.create(
                model=model,
                reasoning={"effort": effort},
                input=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract content and reasoning summary
            # Note: GPT-5.4 returns reasoning metadata in the output_item
            content = response.output_item.content[0].text
            reasoning_summary = getattr(response.output_item, "reasoning", {}).get("summary", "N/A")
            
            return {
                "status": "success",
                "content": content,
                "reasoning_summary": reasoning_summary,
                "model": model,
                "usage": response.usage
            }
        except Exception as e:
            logger.error(f"OpenAI SOTA Execution Error: {e}")
            return {"status": "error", "message": str(e)}

_engine: Optional[OpenAIResponseEngine] = None

def get_openai_engine() -> OpenAIResponseEngine:
    global _engine
    if _engine is None:
        _engine = OpenAIResponseEngine()
    return _engine
