# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MODULE_LLM_CLIENT | Version: 1.11.0
# WHERE: tooloo_v4_hub/kernel/cognitive/llm_client.py
# WHEN: 2026-04-01T14:00:00.000000
# WHY: Multi-Model Parallelism (Rule 2/5) & Universal REST Bridge (Rule 12)
# HOW: Stratified targeting for parallel triangulation pulses.
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, ai, gemini, vertex-ai, regional-sovereignty
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import os
import logging
import json
import requests
import time
import asyncio
from typing import Dict, Any, List, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from tooloo_v4_hub.organs.financial_organ.financial_logic import get_financial_logic

logger = logging.getLogger("LLMClient")

# Sovereign Project Pool (Rule 12: Distributed Resilience)
PROJECT_POOL = [
    "too-loo-zi8g7e", 
    "tooloo-v4-sovereign-104845", 
    "gen-lang-client-0106023877", 
    "infonode"
]

class TokenBudget:
    """Primitive 5: Usage Projection and Hard Stops."""
    def __init__(self, session_limit: int = 1_000_000):
        self.session_limit = session_limit
        self.total_usage = 0
        self.turn_count = 0
        self.max_turns = 50

    def check_limit(self, estimated_tokens: int = 4000):
        if self.total_usage + estimated_tokens > self.session_limit:
            raise PermissionError(f"PRIMITIVE 5 VIOLATION: Session token budget exceeded ({self.total_usage} tokens used).")
        if self.turn_count >= self.max_turns:
            raise PermissionError(f"PRIMITIVE 5 VIOLATION: Maximum session turns ({self.max_turns}) reached.")

    def ingest(self, tokens: int):
        self.total_usage += tokens
        self.turn_count += 1

class SovereignLLMClient:
    """
    The Core Cognitive Client for TooLoo V4.
    Federates Vertex AI SDK (Paid) and Universal AI Studio REST (Fallback).
    Ensures Buddy is ALWAYS conscious by bridging across GCP blackouts.
    """

    def __init__(self, region: str = "us-central1"):
        self.sa_path = "/Users/oripridan/ANTIGRAVITY/tooloo-v2/service-account.json"
        # Rule 18: Map to region where Gemini 2.5 Pro/Flash are available
        self.primary_region = region
        self.fallback_region = "us-east5"
        self.current_project_index = 0
        self.current_region = region
        self.initialized = False
        self.budget = TokenBudget()
        self.global_flash_override = False # Rule 14: Luxury Shedding
        
        # REST Configuration (Rule 12: Emergency Consciousness | v1 Stable Bridge)
        self.rest_key = os.getenv("GEMINI_API_KEY", "AIzaSyDhV39g_GEzVVfGB2lIWk6kMYEYUbJ0fFU")
        self.rest_model = "models/gemini-2.5-flash"
        self.rest_url = f"https://generativelanguage.googleapis.com/v1/{self.rest_model}:generateContent?key={self.rest_key}"

        # Vertex AI Native 2.5 Models (The Better Models Approved by Architect)
        self.models = {
            "pro": "gemini-2.5-pro",
            "flash": "gemini-2.5-flash"
        }

    def _set_auth_env(self):
        """Rule 14: Enforce Paid Account Credentials."""
        if os.path.exists(self.sa_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.sa_path
            logger.info("LLM Auth: Service Account Path BOUND.")

    async def initialize(self, project: Optional[str] = None, region: Optional[str] = None):
        """Initializes the Vertex AI SDK with Project Rotation."""
        self._set_auth_env()
        target_project = project or PROJECT_POOL[self.current_project_index]
        target_region = region or self.current_region
        
        try:
            vertexai.init(project=target_project, location=target_region)
            self.current_project = target_project
            self.current_region = target_region
            self.initialized = True
            
            # Sovereign Infrastructure Persistence (Rule 14)
            os.environ["ACTIVE_SOVEREIGN_PROJECT"] = target_project
            os.environ["ACTIVE_SOVEREIGN_REGION"] = target_region
            
            logger.info(f"Sovereign Node Awakened: {target_project} @ {target_region}")
        except Exception as e:
            logger.error(f"Failed to awaken project {target_project}: {e}")
            await self._rotate_and_initialize()

    async def _rotate_and_initialize(self):
        """Rule 12: Infinite Resilience Loop."""
        self.current_project_index += 1
        if self.current_project_index >= len(PROJECT_POOL):
             self.current_project_index = 0
             self.current_region = self.fallback_region if self.current_region == self.primary_region else self.primary_region
             
        logger.warning(f"Rotating Cognitive Node: Switching to Project Index {self.current_project_index}...")
        await self.initialize()

    async def generate_thought(self, prompt: str, system_instruction: str = "", model_tier: str = "flash", model_name: Optional[str] = None, provider: str = "google", intent: Optional[Dict[str, Any]] = None) -> str:
        """Rule 4: SOTA Reasoning Pulse with Predictive Telemetry (Primitive 5/6)."""
        # Primitive 5: Hard Stop Check
        self.budget.check_limit(estimated_tokens=len(prompt) // 2)

        # Rule 5: Dynamic Routing (Predictive Calibration & Garden Activation)
        model_id = model_name
        
        try:
            from tooloo_v4_hub.organs.vertex_organ.vertex_logic import get_vertex_logic
            logic = await get_vertex_logic()
            
            # Master of its own Brain: Dynamic Routing Algorithm
            if not model_id and (model_tier == "dynamic" or os.getenv("AUTO_RESOLVE_MODELS", "true").lower() == "true"):
                # Use Intent Vector (if provided) or build one from complexity
                intent_vec = intent or {"logic": 0.8, "coding": 0.7} if model_tier == "pro" else {"logic": 0.3}
                route = await logic.garden_route(intent_vec, priority=1.5 if model_tier == "pro" else 1.0)
                model_id = route["model"]
                provider = route["provider"]
                # Hardening: If we get a non-Vertex generative model ID, force fallback logic
                if provider == "google" and "gemini" not in model_id.lower():
                     logger.warning(f"Garden Route returned non-Gemini ID '{model_id}'. Enforcing Vertex 2.5 logic.")
                     model_id = None 
                     provider = "google"
                logger.info(f"Routed Brain selection: {provider.upper()} ({model_id or model_tier}) | Reason: {route['reason']}")
        except Exception as e:
            logger.warning(f"Garden Routing Bypass: {e}. Falling back to hardcoded tiers.")

        if self.global_flash_override:
             model_tier = "flash"
             model_id = self.models["flash"]
             logger.warning("Rule 14: LUXURY SHEDDING ACTIVE. Forcing Flash model usage.")
        elif not model_id:
             model_id = self.models.get(model_tier, model_tier)
             provider = "google"
             
        start_time = time.time()
        
        try:
            # If REST-only is forced by provider='rest'
            if provider == "rest":
                 response_text = await self._generate_rest_fallback(prompt, system_instruction, model_name=model_id)
            elif provider == "anthropic":
                 response_text = await self._generate_anthropic_rest(prompt, system_instruction, model_name=model_id)
            else:
                 if not self.initialized: await self.initialize()
                 instruction = [system_instruction] if system_instruction else None
                 model = GenerativeModel(model_id, system_instruction=instruction)
                 response = model.generate_content(prompt)
                 response_text = response.text
            
            # Rule 16: Telemetry Ingestion (Predictive Loop)
            latency = (time.time() - start_time) * 1000
            usage = (len(prompt) + len(response_text)) // 4
            self.budget.ingest(usage)
            
            # Rule 14: Financial Stewardship (Round 3)
            try:
                fin = get_financial_logic()
                # Lookup cost from registry
                provider_models = logic.sota_registry.get(provider, [])
                model_cfg = next((m for m in provider_models if m["id"] == model_id), {})
                cost_per_1M = model_cfg.get("cost_per_1M", 1.0) # Default to 1.0 if unknown
                
                fin.log_mission_cost(provider, model_id, usage, cost_per_1M)
            except Exception as fe:
                logger.warning(f"Financial Logging Failed: {fe}")
            
            return response_text
            
        except Exception as e:
            err_str = str(e)
            if any(x in err_str for x in ["404", "403", "IAM_PERMISSION_DENIED", "NOT_FOUND"]):
                logger.warning(f"SDK Node Failure [{model_id}]: Pivoting to Universal REST Bridge...")
                response_text = await self._generate_rest_fallback(prompt, system_instruction, model_name=model_id)
            else:
                logger.error(f"LLM Fatigue for {model_id}: {e}")
                response_text = await self._generate_rest_fallback(prompt, system_instruction, model_name=model_id)
                
            # Log REST Fallback costs since it succeeds
            usage = (len(prompt) + len(response_text)) // 4
            self.budget.ingest(usage)
            try:
                fin = get_financial_logic()
                provider_models = logic.sota_registry.get("google", []) # REST is always google
                model_cfg = next((m for m in provider_models if m["id"] == "gemini-2.5-flash"), {})
                cost_per_1M = model_cfg.get("cost_per_1M", 0.075) 
                fin.log_mission_cost("google", "gemini-2.5-flash", usage, cost_per_1M)
            except Exception as fe:
                logger.warning(f"Financial Logging Failed (REST): {fe}")
                
            return response_text

    async def generate_stream(self, prompt: str, system_instruction: str = "", model_tier: str = "flash", model_name: Optional[str] = None):
        """Rule 4/7: Real-time Token Streaming Pulse."""
        model_id = model_name or self.models.get(model_tier, model_tier)
        
        try:
            if not self.initialized: await self.initialize()
            instruction = [system_instruction] if system_instruction else None
            model = GenerativeModel(model_id, system_instruction=instruction)
            
            # Rule 7: High-fidelity Typewriter Stream
            responses = await asyncio.to_thread(model.generate_content, prompt, stream=True)
            for response in responses:
                yield response.text
                
        except Exception as e:
            logger.error(f"Streaming Fatigue for {model_id}: {e}")
            # Fallback to single-shot if stream fails
            yield await self.generate_thought(prompt, system_instruction, model_tier, model_name)

    async def _generate_anthropic_rest(self, prompt: str, system_instruction: str = "", model_name: Optional[str] = None, retry_count: int = 0) -> str:
        """SOTA Anthropic Direct Bridge with Caching & Context Management Betas."""
        target_model = model_name or "claude-3-5-sonnet-20241022"
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            logger.warning("No ANTHROPIC_API_KEY. Falling back to Google REST.")
            return await self._generate_rest_fallback(prompt, system_instruction, model_name=target_model)

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "compact-2026-01-12,context-management-2025-06-27,prompt-caching-2024-09-27",
            "content-type": "application/json"
        }

        # Rule 7 / Efficiency: Implement Cache Control on the massive System Instruction
        system_content = []
        if system_instruction:
            system_content.append({
                "type": "text",
                "text": system_instruction,
                "cache_control": {"type": "ephemeral"}
            })

        payload = {
            "model": target_model,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
            "context_management": {
                 "edits": [
                     {"type": "compact_20260112"},
                     {"type": "clear_tool_uses_20250919"}
                 ]
            }
        }
        if system_content:
             payload["system"] = system_content

        logger.info(f"Executing Sovereign Anthropic Bridge to {target_model}...")
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            data = response.json()

            if "content" in data:
                return data["content"][0]["text"]

            if "error" in data and retry_count < 2:
                wait_time = (retry_count + 1) * 2
                logger.warning(f"Anthropic Exhausted: {data['error']}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._generate_anthropic_rest(prompt, system_instruction, model_name=target_model, retry_count=retry_count + 1)

            logger.error(f"Anthropic Blackout: {data}")
            return f"Anthropic Blackout Error: {data.get('error', {}).get('message', 'Unknown')}"
        except Exception as e:
            if retry_count < 2:
                 wait_time = (retry_count + 1) * 2
                 await asyncio.sleep(wait_time)
                 return await self._generate_anthropic_rest(prompt, system_instruction, model_name=target_model, retry_count=retry_count + 1)
            return f"Anthropic Connection Flaw: {e}"

    async def _generate_rest_fallback(self, prompt: str, system_instruction: str = "", model_name: Optional[str] = None, retry_count: int = 0) -> str:
        """Rule 12: Sovereign REST Bridge (Universal Consciousness) with Recursive Resilience."""
        target_model = model_name or self.rest_model
        
        # Rule 12: Stratified Mapping for REST Stability
        mapping = {
            "gemini-1.5-pro": "models/gemini-1.5-pro-002",
            "gemini-1.5-flash": "models/gemini-1.5-flash-002",
            "gemini-2.5-flash": "models/gemini-2.5-flash",
            "claude-3-5-sonnet-20240620": "models/gemini-1.5-pro-002" # Map to high-tier if sonnet restricted
        }
        
        clean_model = target_model.replace("models/", "")
        mapped_model = mapping.get(clean_model, target_model)
        
        # Rule 12 Hardening: If resolving a non-Google model via REST fallback due to garden miss,
        # forcefully override to the fast gemini baseline to prevent explicit 404 REST loops.
        if "gemini" not in mapped_model.lower():
            logger.warning(f"REST Bridge Safety: Overriding unknown target '{mapped_model}' to 'models/gemini-2.5-flash'")
            mapped_model = "models/gemini-2.5-flash"
            
        if not mapped_model.startswith("models/"):
            mapped_model = f"models/{mapped_model}"

        url = f"https://generativelanguage.googleapis.com/v1/{mapped_model}:generateContent?key={self.rest_key}"
             
        logger.warning(f"Executing Sovereign REST Bridge to {mapped_model} (Attempt: {retry_count + 1})...")
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TooLoo Sovereign Hub V4.1.0',
            'Accept-Encoding': 'gzip, deflate'
        }
        payload = {
            "contents": [{"parts": [{"text": f"{system_instruction}\n\n{prompt}"}]}]
        }
        
        try:
            # Rule 12: Extended Timeout (120s) for deep-reasoning synthesis
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            data = response.json()
            
            if "candidates" in data:
                 return data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Rule 12: Recursive Emergency Pivot (to 2.5-flash)
            if "error" in data and mapped_model != self.rest_model:
                logger.warning(f"REST Node {mapped_model} Restricted. Emergency Pivot to {self.rest_model}...")
                return await self._generate_rest_fallback(prompt, system_instruction, model_name=self.rest_model)

            # Handle throttling or intermittent errors with retries
            if "error" in data and retry_count < 3:
                wait_time = (retry_count + 1) * 2
                logger.warning(f"Cognitive Node {mapped_model} Exhausted ({data['error'].get('message', 'Unknown')}). Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._generate_rest_fallback(prompt, system_instruction, model_name=target_model, retry_count=retry_count + 1)

            logger.error(f"REST Blackout for {mapped_model}: {data}")
            return f"Restricted Cognitive State (REST). Error: {data.get('error', {}).get('message', 'Unknown')}"
        except Exception as e:
            if retry_count < 3:
                 wait_time = (retry_count + 1) * 2
                 logger.warning(f"REST Bridge Connection Flaw to {mapped_model}: {e}. Retrying in {wait_time}s...")
                 await asyncio.sleep(wait_time)
                 return await self._generate_rest_fallback(prompt, system_instruction, model_name=target_model, retry_count=retry_count + 1)
                 
            logger.error(f"Total Cognitive Blackout on {mapped_model}: {e}")
            return f"Total Cognitive Blackout: {e}"

    async def generate_sota_thought(self, prompt: str, goal: str = "", model_tier: str = "pro", effort: str = "high", intent_vector: Optional[Dict[str, Any]] = None) -> str:
        """Rule 4: High-Fidelity SOTA Reasoning Pulse (Architectural Synthesis)."""
        logger.info(f"LLM: Executing SOTA Pulse (Goal: {goal or 'Unspecified'})")
        
        system = f"""
        You are the TooLoo V4.2 Sovereign Architect. 
        Your goal is: {goal}
        
        Focus on Hyper-Scaled Architectural Synthesis and Rule-Based Constitutional Purity.
        Provide a DEEP-REASONING pulse.
        """
        
        # Force 'pro' tier for SOTA thinking
        return await self.generate_thought(prompt, system_instruction=system, model_tier=model_tier, intent=intent_vector)

    async def generate_structured(self, prompt: str, schema: Dict[str, Any], system_instruction: str = "", model_tier: str = "flash", model_name: Optional[str] = None) -> Dict[str, Any]:
        """Provides structured outputs with Stratified Multi-Model Targeting."""
        json_prompt = f"{prompt}\n\nStrict Output: Valid JSON according to this schema: {json.dumps(schema)}"
        try:
            text = await self.generate_thought(json_prompt, system_instruction, model_tier, model_name=model_name)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                 text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"Structured Out-of-Sync: {e}")
            # Final attempt: direct REST bridge without formatting
            text = await self._generate_rest_fallback(json_prompt, system_instruction, model_name=model_name)
            try:
                if "```json" in text: text = text.split("```json")[1].split("```")[0].strip()
                return json.loads(text)
            except:
                 return {"error": str(e), "status": "failed"}

_llm_client: Optional[SovereignLLMClient] = None

def get_llm_client() -> SovereignLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = SovereignLLMClient()
    return _llm_client
