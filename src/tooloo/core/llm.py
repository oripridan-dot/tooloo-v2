import os
import json
import logging
import asyncio
import httpx
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Optional Anthropic SDK for Vertex
try:
    from anthropic import AsyncAnthropicVertex
except ImportError:
    AsyncAnthropicVertex = None

try:
    import google.auth
    from google.auth.transport.requests import Request
    from openai import AsyncOpenAI
except ImportError:
    google = None
    AsyncOpenAI = None

load_dotenv()

logger = logging.getLogger("Tooloo.LLMRouter")

class ModelRouter:
    """Multidimensional Sovereign Model Router for Vertex Model Garden (Anthropic, Gemini, DeepSeek)."""

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "too-loo-zi8g7e") # From conversation history
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "me-west1")
        
        # Anthropic Vertex client setup
        self.anthropic_client = None
        if AsyncAnthropicVertex and self.project_id:
            try:
                # Initialization requires authenticated gcloud session or service account
                self.anthropic_client = AsyncAnthropicVertex(
                    project_id=self.project_id,
                    region="global"
                )
            except Exception as e:
                logger.warning(f"Could not initialize AsyncAnthropicVertex: {e}")

    async def generate_structured(self, prompt: str, schema: Dict[str, Any], system_instruction: str = "", model: Optional[str] = None) -> Dict[str, Any]:
        """Routes a structured generation request. Defaults to Gemini; routes to Claude or Vertex MaaS when the model name matches."""
        target_model = model or "gemini-flash-latest"
        
        # If deeply specified as Claude
        if "claude" in target_model.lower():
            if not self.anthropic_client:
                raise RuntimeError("AnthropicVertex not initialized.")
            
            # Build tool with strict schema + prompt caching on the definition (KI: tool_use_overview)
            tool = {
                "name": "respond_with_structure",
                "description": "Output the final result in this specific structure.",
                "input_schema": schema,
                "strict": True,
                # Cache the tool definition to reduce cost across repeated multi-turn loops (KI: prompt_caching)
                "cache_control": {"type": "ephemeral"}
            }

            # System prompt as a list block with cache_control so it is cached (KI: prompt_caching)
            system_block = [
                {"type": "text", "text": system_instruction, "cache_control": {"type": "ephemeral"}}
            ] if system_instruction else system_instruction

            # tool_choice:auto is required when extended thinking may be active (KI: extended_thinking §Tool Choice)
            response = await self.anthropic_client.messages.create(
                model=target_model,
                max_tokens=2048,
                system=system_block or system_instruction,
                messages=[{"role": "user", "content": prompt}],
                tools=[tool],
                tool_choice={"type": "auto"}
            )

            # Extract tool use arguments
            for content in response.content:
                if content.type == "tool_use" and content.name == "respond_with_structure":
                    return content.input
            return {}

        elif "deepseek" in target_model.lower():
             return await self._call_vertex_maas(target_model, prompt, schema, system_instruction, region="me-west1")
        
        elif "llama" in target_model.lower():
             return await self._call_vertex_maas(target_model, prompt, schema, system_instruction, region="us-east5")

        # Fallback to pure Gemini Vertex/REST API logic
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.gemini_api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema
            }
        }
        
        _GEMINI_RETRY_DELAYS = [1.0, 3.0, 8.0]  # seconds — exponential backoff
        last_err: Exception = RuntimeError("No attempt made")
        for attempt, delay in enumerate([0.0] + _GEMINI_RETRY_DELAYS, start=1):
            if delay:
                logger.warning(f"[LLM] Gemini retry {attempt}/4 after {delay}s (prev err: {last_err})")
                await asyncio.sleep(delay)
            try:
                t0 = time.monotonic()
                async with httpx.AsyncClient(timeout=120.0) as client:
                    res = await client.post(url, json=payload)
                    res.raise_for_status()
                    data = res.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    result = json.loads(text)
                latency = round(time.monotonic() - t0, 2)
                logger.info(f"[LLM] generate_structured OK model={target_model} latency={latency}s attempt={attempt}")
                return result
            except Exception as e:
                last_err = e
                # Only retry on transient errors (429, 503, network)
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code not in (429, 500, 502, 503, 504):
                    break  # Non-retryable (e.g. 400 Bad Request)
        logger.error(f"[LLM] generate_structured FAILED after {attempt} attempts: {last_err}")
        raise last_err

    async def stream_text(self, prompt: str, system_instruction: str = "", model: Optional[str] = None):
        """
        Async generator that yields text tokens as they stream.
        Routes to Anthropic SDK streaming if model is Claude, otherwise Gemini REST SSE.
        """
        target_model = model or "gemini-2.5-pro-exp-03-25"

        # --- Anthropic Claude streaming branch (KI: tool_use_overview §Server Tools) ---
        if "claude" in target_model.lower():
            if not self.anthropic_client:
                raise RuntimeError("AnthropicVertex not initialized for Claude streaming.")
            async with self.anthropic_client.messages.stream(
                model=target_model,
                max_tokens=4096,
                system=system_instruction,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
            return

        # --- Gemini REST SSE streaming branch ---
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}"
            f":streamGenerateContent?alt=sse&key={self.gemini_api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(raw)
                            token = (
                                chunk.get("candidates", [{}])[0]
                                .get("content", {})
                                .get("parts", [{}])[0]
                                .get("text", "")
                            )
                            if token:
                                yield token
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue
        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            raise

    async def _call_vertex_maas(self, model_id: str, prompt: str, schema: Dict[str, Any], system_instruction: str, region: str = "me-west1") -> Dict[str, Any]:
        """Generic Vertex Model-as-a-Service integration (OpenAI compatible)."""
        logger.info(f"Routing to Vertex MaaS Endpoint for model: {model_id} in {region}")
        
        if not google or not AsyncOpenAI:
            raise RuntimeError("google-auth and openai packages are required for Vertex MaaS integration.")

        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_request = Request()
        credentials.refresh(auth_request)
        
        base_url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{region}/endpoints/openapi"
        
        client = AsyncOpenAI(
            base_url=base_url,
            api_key=credentials.token,
        )

        tools = [{
            "type": "function",
            "function": {
                "name": "respond_with_structure",
                "description": "Output the final result in this specific structure.",
                "parameters": schema
            }
        }]

        if "llama" in model_id.lower():
            # Llama 4 on Vertex MaaS does not currently support forced tool choice (mode=ANY)
            tool_choice_payload = "auto"
        else:
            tool_choice_payload = {"type": "function", "function": {"name": "respond_with_structure"}}

        try:
            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                tools=tools,
                tool_choice=tool_choice_payload
            )
            
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls:
                for tc in tool_calls:
                    if tc.function.name == "respond_with_structure":
                        return json.loads(tc.function.arguments)
            
            # Fallback for models like Llama without forced tool structures
            return {"insight": response.choices[0].message.content}
        except Exception as e:
            logger.error(f"Failed to generate structured logic via Vertex MaaS ({model_id}): {e}")
            raise

    async def generate_anthropic_sota(self, prompt: str, system_instruction: str = "", model="claude-sonnet-4-6") -> str:
        """
        Executes Anthropic with SOTA primitives:
        - adaptive extended thinking
        - compaction headers
        - context editing
        """
        if not self.anthropic_client:
            raise RuntimeError("AnthropicVertex not initialized. Cannot perform SOTA execution.")

        logger.info(f"Executing SOTA Anthropic Reasoning via {model}...")
        
        # Anthropic SOTA Beta Headers
        headers = {
            "anthropic-beta": "compact-2026-01-12,context-management-2025-06-27"
        }

        # Context pruning to trim bloated history natively
        context_management = {
            "edits": [
                {"type": "clear_tool_uses_20250919"},
                {"type": "clear_thinking_20251015", "keep": "last"}
            ]
        }

        # Cache the system prompt block (KI: prompt_caching) — same pattern as generate_structured
        system_block = (
            [{"type": "text", "text": system_instruction, "cache_control": {"type": "ephemeral"}}]
            if system_instruction
            else system_instruction
        )

        try:
            t0 = time.monotonic()
            response = await self.anthropic_client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_block or system_instruction,
                messages=[{"role": "user", "content": prompt}],
                thinking={"type": "adaptive"},
                extra_headers=headers,
                extra_body={"context_management": context_management}
            )
            latency = round(time.monotonic() - t0, 2)
            logger.info(f"[LLM] generate_anthropic_sota OK model={model} latency={latency}s")

            final_text = ""
            for block in response.content:
                if block.type == "text":
                    final_text += block.text

            return final_text

        except Exception as e:
            logger.error(f"Failed Anthropic SOTA execution: {e}")
            raise

_client = None

def get_llm_client() -> ModelRouter:
    global _client
    if _client is None:
        _client = ModelRouter()
    return _client
