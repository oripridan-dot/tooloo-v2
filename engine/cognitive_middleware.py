# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining cognitive_middleware.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.917499
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/cognitive_middleware.py — 4D Cognitive State Router

Rides *before* the mandate_executor to establish the Timeframe and Mental
Dimensions of a mandate. By forcing the AI to consider the 4D context
before generating code, we escape the 'local minimum' trap.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from engine.config import (
    _vertex_client,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    VERTEX_DEFAULT_MODEL,
)

logger = logging.getLogger(__name__)

# LLM clients (initialised once at import)
_gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai as _genai_mod  # type: ignore[import-untyped]
        _gemini_client = _genai_mod.Client(api_key=GEMINI_API_KEY)
    except Exception:  # pragma: no cover
        pass


class CognitiveState(BaseModel):
    """The 4D Cognitive State of an execution mandate."""
    intent: str = Field(description="The primary intent, e.g., BUILD, DEBUG, REFACTOR, ARCHITECT")
    timeframe: str = Field(description="Micro (minutes/hours), Meso (days/weeks), or Macro (months/years). Meso/Macro forces decoupling and technical foresight.")
    dimensions: Dict[str, float] = Field(
        description="Dictionary mapping mental dimensions to weights (0.0 to 1.0). e.g., {'Architectural_Foresight': 0.95, 'Execution_Bias': 0.1, 'Refactoring_Depth': 0.8}"
    )


class CognitiveMiddleware:
    """
    Evaluates mandates using a fast model (Gemini Flash) to generate
    a strictly-typed CognitiveState JSON object.
    """
    
    _SYSTEM_PROMPT = (
        "You are the Cognitive Middleware of TooLoo V2. "
        "Your job is to analyze the user mandate and define the 4D Cognitive State "
        "(Intent, Timeframe, and Mental Dimensions). "
        "By defining 'Meso' or 'Macro' timeframes, you prevent the execution engine "
        "from applying short-term, technical-debt 'band-aid' solutions.\n\n"
        "Respond ONLY with a valid JSON object matching this schema:\n"
        "```json\n{schema}\n```\n"
        "Do NOT include markdown formatting wrappers like ```json around the response if possible, just the raw JSON."
    )

    def analyze_mandate(self, mandate_text: str, model_id: Optional[str] = None) -> CognitiveState:
        """
        Calculates and returns the CognitiveState using an LLM.
        Falls back to a default state if validation fails or LLMs are unavailable.
        """
        schema_json = json.dumps(CognitiveState.model_json_schema(), indent=2)
        system_msg = self._SYSTEM_PROMPT.format(schema=schema_json)
        prompt = f"{system_msg}\n\nMandate: {mandate_text[:1000]}"
        
        target_model = model_id or VERTEX_DEFAULT_MODEL

        raw_json = self._call_llm(prompt, target_model)
        if raw_json:
            raw_json = self._clean_json(raw_json)
            try:
                state = CognitiveState.model_validate_json(raw_json)
                logger.info(f"Cognitive Middleware [Analyzer]: Generated state - Timeframe={state.timeframe}")
                return state
            except Exception as e:
                logger.warning(f"Cognitive Middleware failed to parse output. Falling back to default. Error: {e}")
                
        # Fallback default if completely failed
        return CognitiveState(
            intent="EXECUTE",
            timeframe="Meso",
            dimensions={"Architectural_Foresight": 0.8, "Execution_Bias": 0.5}
        )
        
    def _clean_json(self, raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        return raw.strip()

    def _call_llm(self, full_prompt: str, model_id: str) -> Optional[str]:
        if _gemini_client is not None:
            try:
                resp = _gemini_client.models.generate_content(
                    model=GEMINI_MODEL, contents=full_prompt,
                )
                text = (resp.text or "").strip()
                if text:
                    return text
            except Exception as e:
                logger.debug(f"Gemini fast model failed: {e}")
                
        if _vertex_client is not None:
            try:
                resp = _vertex_client.models.generate_content(
                    model=model_id, contents=full_prompt,
                )
                text = (resp.text or "").strip()
                if text:
                    return text
            except Exception as e:
                logger.debug(f"Vertex model failed: {e}")

        return None
