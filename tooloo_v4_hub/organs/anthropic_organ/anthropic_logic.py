# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MODULE_VERTEX_ANTHROPIC_LOGIC | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/anthropic_organ/anthropic_logic.py
# WHEN: 2026-03-31T22:31:00.000000
# WHY: Paid Infrastructure SOTA Infusion (Rule 4, 14)
# HOW: AnthropicVertex SDK + Global Dynamic Routing
# TIER: T3:architectural-purity
# DOMAINS: anthropic, vertex-ai, thinking, sota, cognitive
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import logging
import json
from typing import Dict, Any, List, Optional
from anthropic import AnthropicVertex

logger = logging.getLogger("AnthropicLogic")

class VertexAnthropicLogic:
    """
    The SOTA Bridge for Claude on Vertex AI (Paid Infrastructure).
    Directly leverages the AnthropicVertex SDK for Adaptive Thinking.
    """

    def __init__(self, project_id: Optional[str] = None, region: Optional[str] = None):
        self.project_id = project_id or os.getenv("ACTIVE_SOVEREIGN_PROJECT", "too-loo-zi8g7e")
        self.region = region or os.getenv("ACTIVE_SOVEREIGN_REGION", "us-east5")
        self._client = AnthropicVertex(project_id=self.project_id, region=self.region)
        logger.info(f"Vertex Anthropic Logic Awakened. Project: {self.project_id} (Region: {self.region})")

    async def thinking_chat(
        self, 
        messages: List[Dict[str, str]], 
        system: str = "", 
        max_tokens: int = 8192,
        thinking_budget: int = 4096,
        model: str = "claude-sonnet-4-6@default"
    ) -> Dict[str, Any]:
        """
        Rule 4: SOTA Adaptive Thinking Pulse (Claude 4.6).
        Executes a high-reasoning chat session with 'extended thinking' Phase (Rule 4).
        """
        logger.info(f"Anthropic -> {model}: Initiating Extended Thinking (Budget: {thinking_budget})")
        
        try:
            # Note: client.messages.create is synchronous in current SDK v0.39, 
            # we use run_in_executor if needed, but for now we assume async context.
            # actually anthropic sdk 0.39 has AsyncAnthropicVertex but the Vertex one might be different.
            # I'll check if AsyncAnthropicVertex exists. 
            
            # For now, implementing with standard messages pattern.
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                thinking={
                    "type": "enabled",
                    "budget_tokens": thinking_budget
                }
            )
            
            # SOTA Extraction: Thinking block + Content block
            thinking_content = ""
            final_content = ""
            
            for block in response.content:
                if block.type == "thinking":
                    thinking_content = block.thinking
                elif block.type == "text":
                    final_content = block.text
            
            return {
                "status": "success",
                "thinking": thinking_content,
                "content": final_content,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
        except Exception as e:
            logger.error(f"Anthropic Thinking Phase Error: {e}")
            return {"status": "error", "error": str(e)}

    async def computer_use_pulse(
        self,
        screenshot_base64: str,
        goal: str,
        model: str = "claude-sonnet-4-6@default"
    ) -> Dict[str, Any]:
        """
        Rule 15: GUI Autonomy Foundation.
        Analyzes 2D visual state to derive 6W-stamped system actions.
        """
        logger.info(f"Anthropic -> {model}: Computer Use Pulse Check...")
        
        system_prompt = "You are the TooLoo GUI Manifestation Organ. Analyze the screenshot and provide the next interaction step."
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": screenshot_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": f"Current Goal: {goal}"
                    }
                ]
            }
        ]
        
        try:
            # Vision requests typically don't use 'thinking' for latency reasons in the current doc.
            response = self._client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages
            )
            return {"status": "success", "action": response.content[0].text}
        except Exception as e:
            logger.error(f"Computer Use Pulse Error: {e}")
            return {"status": "error", "error": str(e)}

_logic: Optional[VertexAnthropicLogic] = None

def get_anthropic_logic() -> VertexAnthropicLogic:
    global _logic
    if _logic is None:
        _logic = VertexAnthropicLogic()
    return _logic
