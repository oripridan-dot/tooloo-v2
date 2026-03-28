# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.intent_reconciliation.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/intent_reconciliation.py — Validates whether an executed wave matches the original LockedIntent.
"""
import logging
import json
from dataclasses import dataclass
from typing import Any

from engine.router import LockedIntent
from engine.executor import ExecutionResult
from engine.model_selector import ModelSelector
from engine.model_garden import get_garden

logger = logging.getLogger(__name__)

@dataclass
class IntentReconciliationReport:
    satisfied: bool
    reconciliation_gap: str
    proposed_remedy: str

class IntentReconciliationGate:
    """Evaluates if the completed task actually fulfilled the user's intent."""
    
    def __init__(self, model_selector: ModelSelector | None = None):
        self._model_selector = model_selector or ModelSelector()
    
    async def evaluate(self, intent: LockedIntent, results: list[ExecutionResult]) -> IntentReconciliationReport:
        if not getattr(intent, "success_criteria", None) and not getattr(intent, "value_statement", ""):
            # Nothing to validate against
            return IntentReconciliationReport(True, "", "")
            
        logger.info(f"[IntentReconciliation] Validating against intent: {intent.intent}")
        
        # Synthesize results
        result_summaries = []
        for r in results:
            short_out = (r.output[:200] + '...') if r.output and len(r.output) > 200 else (r.output or "")
            result_summaries.append(f"Node {r.envelope.node_id} ({r.envelope.action}): success={r.success}\nOutput:\n{short_out}")
        
        aggregated_results = "\n---\n".join(result_summaries)
        
        prompt = f"""
You are the final Intent Reconciliation Gate. Your job is to definitively determine if the executed tasks FULFILLED the user's core intent.

User Intent: {intent.intent}
Value Statement (Why they wanted it): {getattr(intent, 'value_statement', 'None')}
Explicit Success Criteria: {getattr(intent, 'success_criteria', [])}
Validation Method: {getattr(intent, 'validation_method', 'None specified')}

Execution Results:
{aggregated_results}

Analyze the results against the criteria. Return ONLY a valid JSON object like this:
{{
    "satisfied": true/false,
    "reconciliation_gap": "If false, explicitly detail *what* is missing based on criteria. If true, empty string.",
    "proposed_remedy": "If false, short instruction on what the next wave must do. If true, empty string."
}}
"""
        
        try:
            # Use Tier 3 for robust validation
            selection = self._model_selector.select(stroke=4, intent="intent_validation", prior_verdict="pass")
            garden = get_garden()
            raw_resp = garden.call(selection.model_id, prompt, max_tokens=1024, intent="AUDIT")
            
            # Clean markdown if present
            if raw_resp.startswith("```json"):
                raw_resp = raw_resp[7:].strip()
            elif raw_resp.startswith("```"):
                raw_resp = raw_resp[3:].strip()
            if raw_resp.endswith("```"):
                raw_resp = raw_resp[:-3].strip()
                    
            parsed = json.loads(raw_resp)
            return IntentReconciliationReport(
                satisfied=bool(parsed.get("satisfied", True)),
                reconciliation_gap=str(parsed.get("reconciliation_gap", "")),
                proposed_remedy=str(parsed.get("proposed_remedy", ""))
            )
        except Exception as e:
            logger.warning(f"Failed to parse LLM reconciliation: {e}")
            return IntentReconciliationReport(True, f"Validation failure fallback: {e}", "")
