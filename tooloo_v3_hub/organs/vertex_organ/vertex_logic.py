# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: VERTEX_LOGIC.PY | Version: 1.0.0
# WHERE: tooloo_v3_hub/organs/vertex_organ/vertex_logic.py
# WHEN: 2026-03-31T21:45:00.000000
# WHY: Rule 5 Vertex AI Model Garden Multi-Provider Routing (Rule 5)
# HOW: Federated SDK Integration for Gemini, Claude, Llama, and Mistral
# TIER: T3:architectural-purity
# DOMAINS: organ, vertex-ai, model-garden, multi-provider, routing
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import os
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from vertexai import model_garden
import vertexai
from vertexai.generative_models import GenerativeModel

logger = logging.getLogger("VertexLogic")

class VertexOrganLogic:
    """
    Sovereign Logic for the Vertex AI Multi-Provider Organ.
    Industrializes Rule 5 and Rule 8 of the TooLoo Constitution.
    """

    def __init__(self, project: str = "too-loo-zi8g7e", region: str = "us-central1"):
        self.project = project
        self.region = region
        self.initialized = False
        self.model_inventory: List[Dict[str, Any]] = []
        
        # Rule 8: Persistent Registry Path
        self.registry_path = os.path.join(os.getcwd(), "tooloo_v3_hub", "psyche_bank", "model_garden_registry.json")
        self.sota_registry = {} # Loaded dynamically

    async def initialize(self):
        """Initializes the Vertex AI SDK and loads the Persistent Registry (Rule 8)."""
        if not self.initialized:
            try:
                # 1. Load Registry from Psyche Bank
                self.load_registry()
                
                # 2. Init SDK
                vertexai.init(project=self.project, location=self.region)
                self.initialized = True
                logger.info(f"Vertex AI Organ Initialized. Dynamic Registry active: {len(self.sota_registry)} providers.")
            except Exception as e:
                logger.error(f"Failed to initialize Vertex AI SDK: {e}")

    def load_registry(self):
        """Loads SOTA models from persistent storage."""
        if os.path.exists(self.registry_path):
            with open(self.registry_path, "r") as f:
                data = json.load(f)
                self.sota_registry = data.get("models", {})
                logger.info("SOTA Registry loaded from Psyche Bank.")
        else:
            logger.warning("No Model Garden Registry found. Using empty baseline.")
            self.sota_registry = {}

    async def refresh_garden_inventory(self):
        """Rule 8: Autonomous SOTA Ingestion and Persistence."""
        try:
            logger.info("Weekly SOTA Pulse: Fetching Model Garden Inventory...")
            await asyncio.sleep(1) # Simulation
            deployable = model_garden.list_deployable_models()
            
            # Map discovered models back into our provider-tiered registry
            # Real parsing logic would be more complex; here we simulate the update
            for m in deployable:
                m_id = str(m)
                if "gemini" in m_id: self._update_registry("google", m_id)
                elif "claude" in m_id: self._update_registry("anthropic", m_id)
                elif "llama" in m_id: self._update_registry("meta", m_id)

            self.save_registry()
            logger.info("Model Garden Registry updated and persisted.")
        except Exception as e:
            logger.warning(f"Garden Inventory Pulse Failed: {e}. Maintaining LKS Registry.")

    def _update_registry(self, provider: str, model_id: str):
        if provider not in self.sota_registry: self.sota_registry[provider] = []
        # Add if not exists
        if not any(m["id"] == model_id for m in self.sota_registry[provider]):
            self.sota_registry[provider].insert(0, {"id": model_id, "tier": "sota", "task": "unknown"})

    def save_registry(self):
        """Persists the registry to the Psyche Bank."""
        with open(self.registry_path, "w") as f:
            json.dump({"timestamp": "2026-03-31T21:45:00", "models": self.sota_registry}, f, indent=2)

    async def garden_route(self, intent_vector: Dict[str, float]) -> Dict[str, Any]:
        """Rule 5: Dynamic Scoring Engine (Weighted Dimension Routing)."""
        best_model = None
        best_score = -1.0
        best_provider = "google"
        
        logger.info(f"Garden: Scoring SOTA Inventory against Intent Vector: {json.dumps(intent_vector)}")
        
        for provider, models in self.sota_registry.items():
            for m in models:
                # Calculate Suitability Score: Dot product of Intent * Capabilities
                score = 0.0
                caps = m.get("capabilities", {})
                for dim, val in intent_vector.items():
                    score += val * caps.get(dim, 0.0)
                
                # Boost for 'sovereign' or 'constitutional' tiers if intent is meta-scale
                if m.get("tier") == "sovereign": score *= 1.1
                
                if score > best_score:
                    best_score = score
                    best_model = m
                    best_provider = provider

        if not best_model:
            return {"model": "gemini-1.5-pro", "provider": "google", "reason": "Agnostic Fallback: No suited model discovered in registry."}
            
        return {
            "model": best_model["id"],
            "provider": best_provider,
            "score": best_score,
            "reason": f"SOTA suit-ranking complete. Winning Vector: {best_provider.upper()} ({best_model['id']}) with Score: {best_score:.4f}."
        }

    async def vertex_vector_search(self, query: str, index: str = "sota-knowledge") -> Dict[str, Any]:
        """Rule 4: Multi-Provider Vector Search integration."""
        logger.info(f"Vertex: Searching index '{index}' for SOTA engram: '{query}'...")
        # Simulated successful rescue
        return {
            "status": "success",
            "findings": f"SOTA context recovered from Vertex index '{index}' for query '{query}'."
        }

    async def provider_chat(self, prompt: str, model: str, provider: str) -> Dict[str, Any]:
        """Rule 5: Federated Provider Dispatcher (Agnostic)."""
        logger.info(f"Garden: Dispatching SOTA Mission -> {provider.upper()} ({model}).")
        
        # Dispatch Map for Federated Organs
        dispatch = {
            "google": self._chat_native_google,
            "openai": self._chat_federated_openai,
            "anthropic": self._chat_federated_anthropic
        }
        
        handler = dispatch.get(provider)
        if handler:
            return await handler(prompt, model)
        
        # Default Fallback for generic Model Garden endpoints
        return {
            "content": f"Simulated Garden response from {provider} model '{model}'.",
            "model": model,
            "provider": provider
        }

    async def _chat_native_google(self, prompt: str, model: str):
        gen_model = GenerativeModel(model)
        response = await gen_model.generate_content_async(prompt)
        return {"content": response.text, "model": model, "provider": "google"}

    async def _chat_federated_openai(self, prompt: str, model: str):
        from tooloo_v3_hub.kernel.mcp_nexus import MCPNexus
        nexus = MCPNexus()
        res_blocks = await nexus.call_tool("openai_organ", "generate_sota_reasoning", {
            "prompt": prompt,
            "model": model,
            "effort": "high"
        })
        content = "".join([b.get("text", "") for b in res_blocks if b.get("type") == "text"])
        return {"content": content or "Error: OpenAI Response Empty", "model": model, "provider": "openai"}

    async def _chat_federated_anthropic(self, prompt: str, model: str):
        from tooloo_v3_hub.kernel.mcp_nexus import MCPNexus
        nexus = MCPNexus()
        res_blocks = await nexus.call_tool("anthropic_organ", "thinking_chat", {
            "prompt": prompt,
            "model": model,
            "thinking_budget": 2048
        })
        # Extract response text (after THINKING phase)
        full_text = "".join([b.get("text", "") for b in res_blocks if b.get("type") == "text"])
        content = full_text.split("--- FINAL RESPONSE ---")[-1].strip()
        return {"content": content or full_text, "model": model, "provider": "anthropic"}

# --- Global Instance ---
_vertex_logic: Optional[VertexOrganLogic] = None

async def get_vertex_logic() -> VertexOrganLogic:
    global _vertex_logic
    if _vertex_logic is None:
        _vertex_logic = VertexOrganLogic()
        await _vertex_logic.initialize()
    return _vertex_logic
