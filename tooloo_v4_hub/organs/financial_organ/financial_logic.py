import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("FinancialOrgan")

LEDGER_PATH = "/Users/oripridan/ANTIGRAVITY/tooloo-v2/tooloo_v4_hub/psyche_bank/sovereign_ledger.json"

class FinancialOrganLogic:
    """
    Rule 14: Sovereign Financial Stewardship and Budgetary Discipline.
    Tracks every token and cent spent across the Brain's providers.
    """
    def __init__(self):
        self.ledger = self._load_ledger()

    def _load_ledger(self) -> Dict[str, Any]:
        if os.path.exists(LEDGER_PATH):
            try:
                with open(LEDGER_PATH, "r") as f:
                    return json.load(f)
            except:
                logger.error("Ledger Corruption. Initializing reset.")
        
        return {
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "provider_breakdown": {},
            "mission_history": []
        }

    def log_mission_cost(self, provider: str, model: str, tokens: int, cost_per_1M: float):
        """Logs the cost of a specific cognitive mission (Rule 14)."""
        cost = (tokens / 1_000_000) * cost_per_1M
        self.ledger["total_cost_usd"] += cost
        self.ledger["total_tokens"] += tokens
        
        if provider not in self.ledger["provider_breakdown"]:
            self.ledger["provider_breakdown"][provider] = {"cost": 0.0, "tokens": 0}
            
        self.ledger["provider_breakdown"][provider]["cost"] += cost
        self.ledger["provider_breakdown"][provider]["tokens"] += tokens
        
        # Keep recent history
        self.ledger["mission_history"].append({
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "model": model,
            "tokens": tokens,
            "cost": round(cost, 6)
        })
        
        if len(self.ledger["mission_history"]) > 100:
            self.ledger["mission_history"].pop(0)
            
        self.save_ledger()
        logger.info(f"Financial: Mission Logged ($ {cost:.6f} via {provider}). Total: $ {self.ledger['total_cost_usd']:.4f}")

    def save_ledger(self):
        os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
        with open(LEDGER_PATH, "w") as f:
            json.dump(self.ledger, f, indent=2)

_financial: Any = None

def get_financial_logic() -> FinancialOrganLogic:
    global _financial
    if _financial is None:
        _financial = FinancialOrganLogic()
    return _financial
