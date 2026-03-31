# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MAIN.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v3_hub/main.py
# WHEN: 2026-03-31T14:26:13.334540+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: component, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
import sys
from tooloo_v3_hub.kernel.mcp_nexus import get_mcp_nexus
from tooloo_v3_hub.kernel.orchestrator import get_orchestrator
from tooloo_v3_hub.kernel.governance.living_map import get_living_map

# Setup structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TooLoo-V3-Hub")

async def main():
    logger.info("Initializing TooLoo V3 Hub...")
    
    # 1. Initialize Nexus and attach Federated Organs (CLOUD RUN / SSE)
    nexus = get_mcp_nexus()
    
    # Federated Memory Organ (Cloud Run)
    await nexus.attach_organ("memory_organ", "https://memory-organ-v3-gru3xdvw6a-ew.a.run.app/sse")
    
    # Federated Audio Organ (Claudio - Cloud Run)
    await nexus.attach_organ("audio_organ", "https://claudio-organ-v3-gru3xdvw6a-ew.a.run.app/sse")
    
    # Federated Vertex AI Multi-Provider Organ (SOTA Garden)
    await nexus.attach_organ("vertex_organ", [sys.executable, "-m", "tooloo_v3_hub.organs.vertex_organ.mcp_server"])
    
    # Circus Spoke is still local for the Viz interface
    await nexus.attach_organ("circus_spoke", [sys.executable, "-m", "tooloo_v3_hub.organs.circus_spoke.mcp_server"])
    
    # 2. Get Orchestrator
    orchestrator = get_orchestrator()
    
    # 3. Define Strategic Goal
    goal = "Harden the Spectral Identity of acoustic_drum_break.wav via Claudio and manifest the outcome."
    context = {"user_id": "principal-architect", "priority": "high"}
    
    # 4. Integrate Cognitive Background Loops
    from tooloo_v3_hub.kernel.cognitive.calibration import get_calibration_engine
    from tooloo_v3_hub.kernel.cognitive.proactive_agent import get_proactive_agent
    from tooloo_v3_hub.kernel.cognitive.ouroboros import get_ouroboros
    from tooloo_v3_hub.kernel.cognitive.sota_pulse import get_sota_pulse
    
    calibration = get_calibration_engine()
    proactive = get_proactive_agent()
    ouroboros = get_ouroboros()
    sota_pulse = get_sota_pulse()
    
    logger.info("Sovereign Context Established. Launching Federated Hub Pulse.")
    
    # We run the initial strategic goal, the proactive soul, the autonomous calibration, SOTA Pulse, and Ouroboros in parallel
    await asyncio.gather(
        orchestrator.execute_goal(goal, context, mode="PATHWAY_B"),
        proactive.start_proactive_loop(),
        calibration.start_calibration_loop(interval=180), # Pulse every 3 minutes
        ouroboros.start_self_healing_loop(interval=300),  # Self-heal every 5 minutes
        sota_pulse.start_pulse_loop()                    # Weekly SOTA Pulse (Rule 8)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Sovereign Hub Terminated by Architect.")