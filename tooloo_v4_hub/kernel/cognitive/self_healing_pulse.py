# 6W_STAMP
# WHO: TooLoo V4.5.0 (Sovereign Architect)
# WHAT: MODULE_SELF_HEALING_PULSE | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/self_healing_pulse.py
# WHY: Rule 14 Financial Stewardship & Rule 12 Autonomous Resilience
# HOW: Periodic Audit + Luxury Shedding Protocol
# ==========================================================

import asyncio
import logging
from typing import Optional
from tooloo_v4_hub.kernel.governance.billing_manager import get_billing_manager
from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client

logger = logging.getLogger("SelfHealingPulse")

class SelfHealingPulse:
    """
    Buddy's Autonomous Ouroboros Loop.
    Audits the Hub's financial and operational vitals.
    """

    def __init__(self):
        self.is_active = False
        self._pulse_task: Optional[asyncio.Task] = None
        # Rule 14: Sovereign Threshold ($1.00 USD for basic session, $5.00 for industrial)
        self.luxury_threshold_usd = 1.00 

    async def start_pulse(self, interval_s: int = 300):
        """Rule 12: Initiates the background Self-Healing pulse."""
        if self.is_active: return
        self.is_active = True
        logger.info(f"Buddy Self-Healing: Heartbeat Activated (Interval: {interval_s}s).")
        
        while self.is_active:
            try:
                await self.perform_financial_audit()
                await asyncio.sleep(interval_s)
            except Exception as e:
                logger.error(f"Self-Healing Pulse Error: {e}")
                await asyncio.sleep(60)

    async def perform_financial_audit(self):
        """Rule 14: Forensic Financial Stewardship Audit."""
        billing = get_billing_manager()
        llm = get_llm_client()
        summary = billing.get_session_summary()
        
        total_cost = summary.get("total_cost_usd", 0.0)
        logger.info(f"Sovereign Stewardship Audit: Total Spend = ${total_cost:.4f}")

        if total_cost > self.luxury_threshold_usd:
            if not llm.global_flash_override:
                logger.warning(f"RULE 14 BREACH: Cost ${total_cost:.4f} > Threshold ${self.luxury_threshold_usd:.2f}. INITIATING LUXURY SHEDDING.")
                llm.global_flash_override = True
                
                # Broadcast the shift to the UI
                from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
                try:
                    logic = get_chat_logic()
                    await logic.broadcast({
                        "type": "STARDUST_ECONOMY_PULSE",
                        "msg": "Budget Threshold Breached. Buddy has autonomously pivoted to Flash-Only reasoning to ensure Infinite Resilience.",
                        "payload": {"cost": total_cost, "threshold": self.luxury_threshold_usd}
                    })
                except: pass
        else:
            if llm.global_flash_override:
                # Reset if we somehow increased the budget or lowered costs (rare but possible in dual-session sync)
                llm.global_flash_override = False
                logger.info("Rule 14: Luxury Restore. System Vitality within baseline.")

_healer = None

def get_self_healer() -> SelfHealingPulse:
    global _healer
    if _healer is None:
        _healer = SelfHealingPulse()
    return _healer
