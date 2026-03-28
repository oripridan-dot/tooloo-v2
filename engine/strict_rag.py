# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining strict_rag.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.918299
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""engine/strict_rag.py — The Deterministic Cage Implementation.

This module implements Strict RAG, forcing the LLM to output ONLY verified ground truth.
If the truth is not found, it returns 'I do not have the verified documentation.'
"""
import logging
from google import genai
from google.genai import types
from engine.cloud_rag import retrieve_strict_context
from engine.critic import CriticAgent
from engine.config import GCP_PROJECT_ID, GCP_REGION, VERTEX_DEFAULT_MODEL

_client = None
_critic_agent = None

def _init_models():
    """Lazily initialize the Generative models."""
    global _client, _critic_agent
    if _client is None:
        import google.auth
        credentials, _ = google.auth.default()
        _client = genai.Client(
            vertexai=True, project=GCP_PROJECT_ID, location=GCP_REGION, credentials=credentials
        )
        _critic_agent = CriticAgent()

def retrieve_ground_truth(prompt: str, threshold: float = 0.85) -> str:
    """Queries the Firestore Vector Database to enforce Law 2."""
    try:
        # Calls the true Cloud RAG Engine
        return retrieve_strict_context(prompt, threshold=threshold)
    except ValueError as e:
        # Fallback to local mock ONLY if GCP is not configured yet for testing
        logging.warning(f"Cloud vector search disabled: {e}. Falling back to strict rejection.")
        return "I do not have the verified documentation to answer this."

async def ask_buddy_strict(prompt: str) -> str:
    """The new 16D engine response router using the Multi-Agent Deterministic Cage."""
    _init_models()
    
    # Phase 1: Retrieve Verified Documentation first
    source_context = retrieve_ground_truth(prompt)
    
    # Pre-Flight Catch
    if source_context == "I do not have the verified documentation to answer this.":
        return source_context
        
    # Phase 2 & 3: Generation & Multi-Agent Critic Loop
    generator_system = (
        "You are the strict Generator. Answer the following prompt accurately, "
        "but ONLY using facts present in the provided Ground Truth Context. "
        "Do not invent words, facts, or expand. Transcribe the direct answer."
    )
    
    max_retries = 3
    for attempt in range(max_retries):
        generation_prompt = f"{generator_system}\n\nContext:\n{source_context}\n\nPrompt:\n{prompt}"
        
        try:
            response = _client.models.generate_content(
                model=VERTEX_DEFAULT_MODEL,
                contents=generation_prompt,
                config=types.GenerateContentConfig(temperature=0.0)
            )
            draft = response.text.strip()
            
            # The Critic Gate (Pillar 2)
            is_valid = _critic_agent.evaluate(draft, source_context)
            if is_valid:
                return draft
            else:
                logging.warning(f"[STRICT RAG] Critic rejected draft on attempt {attempt+1}. Hallucination detected. Retrying...")
                
        except Exception as e:
            logging.error(f"Generator/Critic pipeline failed: {e}")
            break
            
    # If the Critic rejects all 3 attempts, the system MUST FAIL CLOSED!
    return "I do not have the verified documentation to answer this reliably without hallucination."
