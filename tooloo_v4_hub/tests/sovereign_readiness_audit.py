# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: SOVEREIGN_READINESS_AUDIT.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/tests/sovereign_readiness_audit.py
# WHEN: 2026-04-01T16:31:40
# WHY: Verify Buddy is fully capable and resilient (User Request)
# HOW: Orchestrated 5-Pulse System Validation
# TIER: T3:architectural-purity
# DOMAINS: kernel, verification, sota, recovery, mcp, audit
# PURITY: 1.00
# TRUST: T3:arch-purity
# ==========================================================

import asyncio
import logging
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus
from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client
from tooloo_v4_hub.kernel.cognitive.recovery_pulse import get_recovery_pulse
from tooloo_v4_hub.kernel.cognitive.audit_agent import get_audit_agent

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ReadinessAudit")

class SovereignAudit:
    def __init__(self):
        self.nexus = get_mcp_nexus()
        self.manifest_path = Path("tooloo_v4_hub/psyche_bank/readiness_manifest.json")
        self.report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "overall_status": "PENDING",
            "pulses": {}
        }

    async def pulse_1_nerve(self):
        """Verify MCP Organ connectivity (Nerve Pulse)."""
        logger.info("Pulse 1: Nerve (MCP Connectivity Check)...")
        results = {}
        
        # We try to initialize default organs first
        await self.nexus.initialize_default_organs()
        
        # Wait a bit for tethering
        await asyncio.sleep(2)
        
        for name, tether in self.nexus.tethers.items():
            results[name] = tether.get("status", "Offline")
        
        status = "PASS" if all(s == "Online" or s == "Tethering..." for s in results.values()) else "WARN"
        self.report["pulses"]["nerve"] = {"status": status, "organs": results}
        return status

    async def pulse_2_reasoning(self):
        """Verify SOTA Fallback / Reasoning (Reasoning Pulse)."""
        logger.info("Pulse 2: Reasoning (SOTA Fallback / Thinking Heartbeat)...")
        llm = get_llm_client()
        
        # Explicit test for Claude 4.6 with expected fallback
        prompt = "Explain the importance of Rule 12 for Buddy's autonomy."
        try:
            # This should trigger the fallback to Gemini or REST bridge
            # Note: We're calling the raw generate_thought which handles the SDK/REST pivot
            thought = await llm.generate_thought(
                prompt=prompt,
                model_name="claude-sonnet-4-6@default",
                system_instruction="You are the TooLoo Sovereign Hub Architect."
            )
            
            status = "PASS" if thought else "FAIL"
            self.report["pulses"]["reasoning"] = {
                "status": status,
                "sample_thought": thought[:200] + "..." if thought else "None"
            }
        except Exception as e:
            logger.error(f"Reasoning Pulse Fault: {e}")
            self.report["pulses"]["reasoning"] = {"status": "FAIL", "error": str(e)}
            status = "FAIL"
        
        return status

    async def pulse_3_heartbeat(self):
        """Verify Recovery Checkpointing (Heartbeat Pulse)."""
        logger.info("Pulse 3: Heartbeat (Ouroboros Recovery Pulsar)...")
        recovery = get_recovery_pulse()
        
        # Trigger manual snapshot
        snapshot_time = time.time()
        recovery.update_context(mission="Sovereign Readiness Audit", thought="Performing Pulse 3...")
        await recovery.snapshot(event_description="AUDIT_HEARTBEAT")
        
        # Check disk
        registry_path = Path("tooloo_v4_hub/psyche_bank/active_cognition.json")
        if registry_path.exists():
            status = "PASS"
            self.report["pulses"]["heartbeat"] = {"status": "PASS", "path": str(registry_path)}
        else:
            status = "FAIL"
            self.report["pulses"]["heartbeat"] = {"status": "FAIL", "reason": "active_cognition.json not found"}
        
        return status

    async def pulse_4_physical(self):
        """Verify System Organ / Hands (Physical Pulse)."""
        logger.info("Pulse 4: Physical (System Organ / Hands)...")
        try:
            # We use the nexus to call the system organ's 'fs_ls' tool
            res = await self.nexus.call_tool("system_organ", "fs_ls", {"path": "."})
            
            # MCPNexus.call_tool returns a list of content blocks
            if isinstance(res, list) and len(res) > 0:
                status = "PASS"
                # Extract first block's text (simulated, real SDK behavior)
                content = res[0].get("text", "[]") if isinstance(res[0], dict) else str(res[0])
                num_files = len(json.loads(content)) if "[" in content else 0
                self.report["pulses"]["physical"] = {"status": "PASS", "root_files": num_files}
            else:
                status = "FAIL"
                self.report["pulses"]["physical"] = {"status": "FAIL", "reason": "No content from system organ"}
        except Exception as e:
            logger.error(f"Physical Pulse Fault: {e}")
            self.report["pulses"]["physical"] = {"status": "FAIL", "error": str(e)}
            status = "FAIL"
            
        return status

    async def pulse_5_vitality(self):
        """Verify Constitutional Purity (Vitality Pulse)."""
        logger.info("Pulse 5: Vitality (Constitutional Audit Agent)...")
        auditor = get_audit_agent()
        try:
            vitality = await auditor.calculate_vitality_index()
            status = "PASS" if vitality.get("purity_score", 0) > 0.9 else "WARN"
            self.report["pulses"]["vitality"] = {"status": status, "metrics": vitality}
        except Exception as e:
            logger.error(f"Vitality Pulse Fault: {e}")
            self.report["pulses"]["vitality"] = {"status": "FAIL", "error": str(e)}
            status = "FAIL"
            
        return status

    async def run_audit(self):
        logger.info("=== STARTING SOVEREIGN READINESS AUDIT ===")
        
        p1 = await self.pulse_1_nerve()
        p2 = await self.pulse_2_reasoning()
        p3 = await self.pulse_3_heartbeat()
        p4 = await self.pulse_4_physical()
        p5 = await self.pulse_5_vitality()
        
        results = [p1, p2, p3, p4, p5]
        if all(r == "PASS" for r in results):
            self.report["overall_status"] = "AUTHENTICATED"
        elif any(r == "FAIL" for r in results):
            self.report["overall_status"] = "COMPROMISED"
        else:
            self.report["overall_status"] = "STABLE"
            
        # Final Manifestation
        with open(self.manifest_path, "w") as f:
            json.dump(self.report, f, indent=2)
            
        logger.info(f"=== AUDIT COMPLETE. STATUS: {self.report['overall_status']} ===")
        logger.info(f"Manifest saved to: {self.manifest_path}")
        return self.report

if __name__ == "__main__":
    audit = SovereignAudit()
    asyncio.run(audit.run_audit())
