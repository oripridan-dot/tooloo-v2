# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.intent_analyzer.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/intent_analyzer.py - Vector Mathematics for Human Intent

Implements the "Action Gap" mathematical model:
    Vector(Look) - Vector(See) = Intent

This module calculates the cosine similarity of user prompts against
the Global Intent Vector to classify mandates into LISTEN, COLLABORATE, or EXECUTE.
"""

import math
import logging
from typing import Tuple, Dict, Any, List

logger = logging.getLogger(__name__)

class IntentAnalyzer:
    """
    Analyzes user mandates using vector mathematics to determine true human intent.
    Differentiates between passive observation and active instruction.
    """
    
    def __init__(self):
        # The true Global Intent Vector (as calculated during Tooloo v2 research)
        # Represents the mathematical gap between passive perception and active agency
        # [Visual, Auditory, Tactile, Agency/Action] -> Dimension scaled for production
        self.global_intent_vector = [0.05, 0.05, 0.025, 0.75]
        
        # Hardcoded embedding dictionary to avoid blocking LLM calls for latency
        # In a fully productionized system, this would call text-embedding-ada-002
        self.known_vectors = {
            # Examples of passive/descriptive prompts
            "the button is blue": [0.7, 0.0, 0.0, 0.1],
            "it looks weird": [0.6, 0.0, 0.1, 0.1],
            "when clicked it loads": [0.2, 0.0, 0.5, 0.2],
            "i see a bug": [0.8, 0.0, 0.0, 0.1],
            
            # Examples of active/instructional prompts
            "make the button blue": [0.7, 0.0, 0.0, 0.8],
            "rewrite the login logic": [0.1, 0.1, 0.1, 0.9],
            "fix the recursion": [0.1, 0.1, 0.0, 0.85],
            
            # Examples of exploratory/collaborative prompts
            "how does the pipeline work": [0.5, 0.5, 0.0, 0.4],
            "why is the api looping": [0.3, 0.4, 0.0, 0.5]
        }
        
    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        mag1 = math.sqrt(sum(a * a for a in v1))
        mag2 = math.sqrt(sum(a * a for a in v2))
        if mag1 == 0 or mag2 == 0:
            return 0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        return dot_product / (mag1 * mag2)
        
    def _get_vector(self, text: str) -> List[float]:
        """
        Fallback logic to generate vectors mathematically based on linguistic cues
        when a pure LLM embedding isn't available.
        """
        text_lower = text.lower()
        if text_lower in self.known_vectors:
            return self.known_vectors[text_lower]
            
        # Mathematical approximation of intent vector based on active/passive verbs
        active_verbs = {"make", "do", "rewrite", "fix", "change", "update", "add", "remove"}
        passive_verbs = {"see", "look", "is", "has", "when"}
        question_words = {"how", "why", "what", "where"}
        
        words = set(text_lower.split())
        
        agency = 0.2 # default baseline
        if words.intersection(active_verbs):
            agency += 0.6
        elif words.intersection(question_words):
            agency += 0.3
            
        visual = 0.5 if "button" in words or "color" in words or "see" in words else 0.1
        auditory = 0.5 if "hear" in words or "sound" in words else 0.1
        tactile = 0.5 if "click" in words or "touch" in words else 0.1
        
        return [visual, auditory, tactile, agency]

    def analyze(self, mandate_text: str) -> Tuple[float, str]:
        """
        Calculates intent score and returns action category.
        
        Returns:
            (intent_score, ActionCategory) where ActionCategory is one of:
            "EXECUTE" (High Intent), "COLLABORATE" (Medium Intent), "LISTEN" (Low Intent)
        """
        vector = self._get_vector(mandate_text)
        score = self._cosine_similarity(vector, self.global_intent_vector)
        
        if score > 0.75:
            action = "EXECUTE"
        elif score > 0.45:
            action = "COLLABORATE"
        else:
            action = "LISTEN"
            
        logger.info(f"Intent Math [Analyzer]: mandate='{mandate_text}' -> score={score:.3f} -> {action}")
        return score, action
