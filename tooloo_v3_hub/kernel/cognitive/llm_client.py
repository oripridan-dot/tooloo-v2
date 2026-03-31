# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MODULE_LLM_CLIENT | Version: 1.4.0
# WHERE: tooloo_v3_hub/kernel/cognitive/llm_client.py
# WHEN: 2026-03-31T23:16:00.000000
# WHY: Rule 5 Vertex AI Model Garden Integration & Fallback Stability (Brain of the Hub)
# HOW: GenerativeModel Wrapper via vertexai SDK (Stable GA models)
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, ai, gemini, vertex-ai
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import os
import logging
import json
from typing import Dict, Any, List, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, Part

logger = logging.getLogger("LLMClient")

class SovereignLLMClient:
    """
    The Core Cognitive Client for TooLoo V3.
    Directly interfaces with Vertex AI Gemini 1.5 (Stable GA).
    """

    def __init__(self, project: str = "too-loo-zi8g7e", region: str = "global"):
        self.project = project
        self.region = region
        self.initialized = False
        
        self.models = {
            "pro": "gemini-1.5-pro",
            "flash": "gemini-1.5-flash"
        }

    async def initialize(self):
        """Initializes the Vertex AI SDK (Rule 3 SOTA Grounding)."""
        if not self.initialized:
            try:
                vertexai.init(project=self.project, location=self.region)
                self.initialized = True
                logger.info(f"Sovereign LLM Client Awakened. Project: {self.project}")
            except Exception as e:
                logger.error(f"Failed to awaken LLM Client: {e}")

    async def generate_thought(self, prompt: str, system_instruction: str = "", model_tier: str = "flash") -> str:
        """Rule 4: SOTA Reasoning Pulse."""
        if not self.initialized: await self.initialize()
        
        try:
            model_id = self.models.get(model_tier, self.models["flash"])
            model = GenerativeModel(
                model_id,
                system_instruction=[system_instruction] if system_instruction else None
            )
            response = await model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"LLM Generation Error: {e}")
            return f"Error: {str(e)}"

    async def generate_sota_thought(self, prompt: str, goal: str = "", effort: str = "high", intent_vector: Optional[Dict[str, float]] = None) -> str:
        """
        Rule 5: Federated SOTA Pulse.
        Routes the reasoning mission through the Vertex Garden Organ.
        """
        from tooloo_v3_hub.kernel.mcp_nexus import MCPNexus
        nexus = MCPNexus()
        
        # 1. Determine SOTA model routing via Vertex Garden
        # Use the provided intent_vector or a logic-heavy baseline
        iv = intent_vector or {"Constitutional": 0.5, "Syntax_Precision": 0.9, "Speed": 0.1, "Complexity": 0.8}
        
        route_blocks = await nexus.call_tool("vertex_organ", "garden_route", {
            "intent_vector": iv
        })
        
        # Rule 5: Correctly extract the routing dictionary from the garden blocks
        route_text = "".join([b.get("text", "") for b in route_blocks if b.get("type") == "text"])
        try:
            route = json.loads(route_text)
        except:
            route = {}
        
        model = route.get("model", "gpt-5.4")
        provider = route.get("provider", "openai")
        
        logger.info(f"LLM Client: Routing SOTA Mission to {provider.upper()} ({model}) via Vertex Garden.")
        
        # 2. Call the provider via the standardized Garden interface
        res_blocks = await nexus.call_tool("vertex_organ", "provider_chat", {
            "prompt": prompt,
            "model": model,
            "provider": provider
        })
        
        # Rule 5: Correctly extract text from the Garden Response blocks
        # vertex_organ.provider_chat returns a dict with 'content' string, but 
        # nexus.call_tool wraps that in a TextContent block list.
        # So we extract the text parts and join them.
        full_response_text = "".join([b.get("text", "") for b in res_blocks if b.get("type") == "text"])
        
        # If the tool returned a JSON-stringified dict (standard for our organs), we parse it
        try:
            res_data = json.loads(full_response_text)
            return res_data.get("content", full_response_text)
        except:
            return full_response_text

    async def generate_structured(self, prompt: str, schema: Dict[str, Any], system_instruction: str = "", model_tier: str = "flash") -> Dict[str, Any]:
        """Provides structured outputs (JSON) for Inverse DAG decomposition."""
        if not self.initialized: await self.initialize()
        
        try:
            model_id = self.models.get(model_tier, self.models["flash"])
            model = GenerativeModel(
                model_id,
                system_instruction=[system_instruction] if system_instruction else None
            )
            
            json_prompt = f"{prompt}\n\nStrict Output: Valid JSON according to this schema: {json.dumps(schema)}"
            response = await model.generate_content_async(json_prompt)
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                 text = text.split("```")[1].split("```")[0].strip()
                 
            return json.loads(text)
        except Exception as e:
            logger.error(f"LLM Structured Generation Error: {e}")
            return {"error": str(e), "status": "failed"}

_llm_client: Optional[SovereignLLMClient] = None

def get_llm_client() -> SovereignLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = SovereignLLMClient()
    return _llm_client
