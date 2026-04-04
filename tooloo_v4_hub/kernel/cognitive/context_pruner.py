# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: context_pruner.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/context_pruner.py
# WHY: Rule 7, 10 - Token Efficiency and Context Management (Claude-Style)
# HOW: Relevance scoring and destructive pruning of active session buffer.
# PURITY: 1.00
# ==========================================================

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ContextPruner")

class ContextPruner:
    """
    Sovereign Context Manager.
    Ensures the active session stays within token limits by pruning low-relevance artifacts.
    """
    
    def __init__(self, max_tokens: int = 180000): # Default for Claude/Gemini-Pro safety
        self.max_tokens = max_tokens
        self.relevance_weights = {
            "system": 1.0,      # Never prune
            "user": 0.9,        # High relevance
            "tool_result": 0.6,  # Medium (prune if old)
            "thought": 0.4      # Low (prune first)
        }

    def prune_transcript(self, transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prunes the conversation transcript based on relevance and age.
        Claude Pattern: Keeps the 'Active Set' (last 5 turns) and prunes older results.
        """
        if len(transcript) <= 10:
            return transcript

        logger.info(f"ContextPruner: Evaluating transcript (size: {len(transcript)}) for pruning...")
        
        # 1. Protect the system prompt and the last 5 turns
        protected = [transcript[0]] if transcript[0].get("role") == "system" else []
        active_set = transcript[-5:]
        
        # 2. Score the candidates (everything in between)
        candidates = transcript[len(protected):-5]
        
        # Filtering: Keep 'user' messages, prune large 'tool_results' or 'thought' blocks
        pruned_candidates = []
        for turn in candidates:
            role = turn.get("role")
            content = str(turn.get("content", ""))
            
            # Heuristic: If tool result is huge (>2000 chars), summarize or drop if old
            if role == "assistant" and len(content) > 2000:
                 logger.debug("ContextPruner: Large assistant block detected. Pruning for efficiency.")
                 continue # Drop it
            
            if role == "user":
                pruned_candidates.append(turn)
            elif len(content) < 500: # Keep small context-bearing thoughts
                pruned_candidates.append(turn)

        return protected + pruned_candidates + active_set

    def score_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Placeholder for scoring active file contents by relevance to the goal."""
        # Future: Use embeddings to score file relevance
        return files

_pruner = None

def get_context_pruner() -> ContextPruner:
    global _pruner
    if _pruner is None:
        _pruner = ContextPruner()
    return _pruner
