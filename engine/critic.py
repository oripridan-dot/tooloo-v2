# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.critic.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""engine/critic.py — The Multi-Agent Debate Safety Catch.

This module houses the Critic agent, a zero-temperature evaluator 
that strictly compares a generated draft against a ground-truth context.
If it detects ANY deviation, addition, or hallucination, it fires a rejection.
"""
import logging
from google import genai
from google.genai import types
from engine.config import GCP_PROJECT_ID, GCP_REGION, VERTEX_DEFAULT_MODEL
logger = logging.getLogger(__name__)

# The strict mandate for the Critic agent
CRITIC_SYSTEM_PROMPT = (
    "You are the CRITIC, the ultimate safety and compliance gatekeeper. "
    "Your ONLY job is to compare a Generated Draft against a Ground Truth Context. "
    "Rule 1: If the Generated Draft contains ANY information, numbers, nouns, or facts "
    "that are NOT explicitly present in the Ground Truth Context, you must return FAILED. "
    "Rule 2: If the Generated Draft is perfectly supported by the Context without any "
    "outside additions, return PASSED. "
    "OUTPUT EXACTLY ONE WORD: either PASSED or FAILED."
)

class CriticAgent:
    def __init__(self, model_id: str = None):
        # We use a zero-temperature model for maximum deterministic verification
        self.model_id = model_id or VERTEX_DEFAULT_MODEL
        import google.auth
        credentials, _ = google.auth.default()
        self.client = genai.Client(
            vertexai=True, project=GCP_PROJECT_ID, location=GCP_REGION, credentials=credentials
        )
        self.config = types.GenerateContentConfig(temperature=0.0)
        
    def evaluate(self, draft: str, context: str) -> bool:
        """
        Evaluates if the draft hallucinates beyond the provided context.
        Returns True if passed (safe), False if failed (hallucination).
        """
        evaluation_prompt = (
            f"{CRITIC_SYSTEM_PROMPT}\n\n"
            f"--- GROUND TRUTH CONTEXT ---\n{context}\n\n"
            f"--- GENERATED DRAFT ---\n{draft}\n\n"
            "Result (PASSED or FAILED):"
        )
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=evaluation_prompt,
                config=self.config
            )
            verdict = response.text.strip().upper()
            
            if "PASSED" in verdict:
                return True
            else:
                logger.warning(f"Critic Agent detected a hallucination! Verdict: {verdict}")
                return False
                
        except Exception as e:
            logger.error(f"Critic Agent failed to evaluate: {e}")
            # Fail closed for security in a Strict RAG environment
            return False
