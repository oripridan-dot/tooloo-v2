# 6W_STAMP
# WHO: TooLoo V4.2.0 (Sovereign Architect)
# WHAT: MODULE_SELF_EVALUATION_PULSE | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/self_evaluation_pulse.py
# WHEN: 2026-04-02T21:30:00.000000
# WHY: Rule 16 (Evaluation Delta Verification) - Autonomous System Audit
# HOW: Integrated Retrospective + Purity Audit + Calibration Loop
# TIER: T4:zero-trust
# DOMAINS: kernel, cognitive, audit, rule-16, calibration, vitality
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
import os
import json
import random
from pathlib import Path
from typing import Dict, Any, List, Optional
from tooloo_v4_hub.kernel.governance.stamping import StampingEngine
from tooloo_v4_hub.kernel.cognitive.calibration import get_calibration_engine
from tooloo_v4_hub.kernel.cognitive.value_evaluator import get_value_evaluator
from tooloo_v4_hub.kernel.cognitive.delta_calculator import get_delta_calculator
from tooloo_v4_hub.kernel.governance.billing_manager import get_billing_manager
from tooloo_v4_hub.kernel.cognitive.audit_agent import get_audit_agent

logger = logging.getLogger("SelfEvaluationPulse")

class SelfEvaluationPulse:
    """
    The Autopoietic Heartbeat of Rule 16.
    Recursively evaluates Hub performance and triggers calibration.
    """

    def __init__(self, base_path: Optional[str] = None):
        self._base_path = Path(base_path) if base_path else Path(".")
        self._last_vitality = 1.0 # Rule 16: Vitality Memory for Adaptive Sampling
        self._pulse_count = 0
        
    async def run_evaluation_cycle(self) -> Dict[str, Any]:
        """Synthesizes the Sovereign Vitality Index (SVI)."""
        self._pulse_count += 1
        logger.info(f"Initiating Sovereign Self-Evaluation Cycle (Pulse V1.0.0) - Count: {self._pulse_count}")
        
        calibrator = get_calibration_engine()
        auditor = get_audit_agent()

        # 1. RETROSPECTIVE: Audit recent mission outcomes (Rule 16)
        retrospective = await self.perform_retrospective(limit=10)
        avg_evd = retrospective.get("avg_eval_delta", 0.0)
        
        # 2. PURITY: Audit file system compliance (Rule 10)
        # Adaptive Deep Sampling: Full sweep if vitality is low or every 10 pulses
        is_deep = self._last_vitality < 0.95 or self._pulse_count % 10 == 0
        purity_report = await self.perform_purity_audit(sample_size=None if is_deep else 28)
        purity_score = purity_report.get("purity_index", 1.0)
        
        # 3. Financial Audit (Rule 14)
        billing = get_billing_manager()
        summary = billing.get_session_summary()
        financial_vitality = summary.get("financial_vitality", 1.0)
        
        # 4. Vitality Synthesis
        vitality_metrics = await auditor.calculate_vitality_index()
        # Autopoietic Weighting: 30% Logical, 30% Purity, 40% Fiscal Stability (Rule 14)
        hub_vitality = (float(vitality_metrics.get("vitality", 1.0)) * 0.3) + \
                       (purity_score * 0.3) + \
                       (financial_vitality * 0.4)
        
        report = {
            "status": "SOVEREIGN_AUDIT_COMPLETE",
            "hub_vitality": round(hub_vitality, 4),
            "purity_index": purity_score,
            "financial_vitality": financial_vitality,
            "session_cost_usd": summary.get("total_cost_usd", 0.0),
            "avg_prediction_delta": round(avg_evd, 6),
            "calibration_status": "PENDING",
            "missions_reviewed": retrospective.get("mission_count", 0),
            "files_audited": purity_report.get("files_scanned", 0),
            "unstamped_files": purity_report.get("unstamped_files", [])
        }
        
        # 4. Trigger Autonomous Calibration (Rule 16)
        if abs(avg_evd) > 0.05 or hub_vitality < 0.95:
             logger.warning(f"Cognitive Drift Detected (Δ={avg_evd:.4f}). Triggering Calibration Pulse.")
             await calibrator.refine_weights(domain="logic", delta=avg_evd * 0.1)
             report["calibration_status"] = "CALIBRATED"
        
        logger.info(f"Self-Evaluation Results: Vitality={hub_vitality:.4f} | EVD={avg_evd:.4f} {'[DEEP AUDIT]' if is_deep else ''}")
        self._last_vitality = hub_vitality
        return report

    async def perform_retrospective(self, limit: int = 10) -> Dict[str, Any]:
        """Scans mission history for Eval Prediction Deltas."""
        from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus
        nexus = get_mcp_nexus()
        
        try:
            # Rule 2: Federated Memory Query for missions
            # We look for engrams that contain 'eval_delta'
            # Note: memory_organ might need a specific query for this
            engrams = await nexus.call_tool("memory_organ", "memory_query", {
                "query": "eval_delta", 
                "top_k": limit
            })
            
            deltas: List[float] = []
            if isinstance(engrams, list):
                for e in engrams:
                    # Depending on engram structure (engram_query tool might return text/json)
                    content = e.get("data", {})
                    # If it's a list from call_tool(memory_organ, memory_query), 
                    # check for 'eval_delta'
                    if "eval_delta" in content:
                        deltas.append(float(content["eval_delta"]))
            
            avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
            return {"mission_count": len(deltas), "avg_eval_delta": avg_delta, "deltas": deltas}
        except Exception as e:
            logger.error(f"Retrospective Scan Failure: {e}")
            return {"mission_count": 0, "avg_eval_delta": 0.0}

    async def perform_purity_audit(self, sample_size: Optional[int] = 20) -> Dict[str, Any]:
        """Audits the file system for 6W-stamp compliance."""
        python_files = list(self._base_path.glob("**/*.py"))
        if not python_files: return {"purity_index": 1.0, "files_scanned": 0, "unstamped_files": []}
        
        if sample_size is None or sample_size >= len(python_files):
            sample = python_files
        else:
            sample = random.sample(python_files, sample_size)
        
        stamped_count = 0
        purity_sum = 0.0
        unstamped_files = []
        
        for file_path in sample:
            try:
                content = file_path.read_text(errors="ignore")
                metadata = StampingEngine.extract_metadata(content)
                if metadata:
                    stamped_count += 1
                    purity_sum += float(metadata.get("purity_score", 1.0))
                else:
                    unstamped_files.append(str(file_path))
            except Exception:
                continue
                
        purity_idx = (purity_sum / stamped_count) if stamped_count > 0 else 0.0
        coverage = stamped_count / len(sample) if sample else 1.0
        
        return {
            "files_scanned": len(sample),
            "stamped_files": stamped_count,
            "unstamped_files": unstamped_files,
            "purity_index": round(purity_idx * coverage, 4)
        }

    async def start_autonomous_pulse(self, interval: int = 600):
        """Rule 12: Autonomous Self-Healing Audit Loop."""
        logger.info(f"Sovereign Self-Evaluation Pulse initiated (Interval: {interval}s)")
        # Avoid immediate run if Hub just started (Cloud Run cold start safety)
        await asyncio.sleep(60) 
        while True:
            try:
                await self.run_evaluation_cycle()
            except Exception as e:
                logger.error(f"Pulse Cycle Fault: {e}")
            await asyncio.sleep(interval)

_self_evaluator = None

def get_self_evaluator() -> SelfEvaluationPulse:
    global _self_evaluator
    if _self_evaluator is None:
        _self_evaluator = SelfEvaluationPulse()
    return _self_evaluator
