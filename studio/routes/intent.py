from fastapi import APIRouter
from typing import Any, Dict, List
from engine.tribunal import TribunalResult, TribunalVerdict
from engine.auto_fixer import AutoFixLoop

router = APIRouter(prefix="/v2/intent", tags=["intent"])

_latest_gap: Dict[str, Any] = {
    "delta": 0.0,
    "verdict": "STABLE_SUCCESS",
    "violations": []
}

@router.get("/gap")
async def get_intent_gap() -> Dict[str, Any]:
    """Returns the divergence between predicted and actual emergence for the last mandate."""
    # In a real system, this would poll the NotificationBus or a sliding window of Engrams
    return _latest_gap

@router.get("/remediation")
async def get_remediation_history() -> List[Dict[str, Any]]:
    """Returns the history of autonomous self-healing (AutoFixLoop) actions."""
    # For now, we return a mock of recent autonomous fixes to prove the UI hook
    return [
        {
            "timestamp": "2026-03-28T09:12:00Z",
            "component": "engine/vector_store.py",
            "issue": "Missing 'os' import",
            "fix": "Inserted 'import os' at line 26",
            "verdict": "SUCCESS"
        }
    ]

def update_gap(result: TribunalResult):
    global _latest_gap
    _latest_gap = {
        "delta": result.delta,
        "verdict": result.verdict.value,
        "violations": result.violations
    }
