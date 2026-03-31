# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: HUB_MAIN_v3.0.0 — Cognitive Entry Point
# WHERE: tooloo_v3_hub/main.py
# WHEN: 2026-03-29T09:30:00.000000
# WHY: Bootstrap the Sovereign Pure Hub
# HOW: Pure Sovereign Infrastructure Protocol
# ==========================================================

import asyncio
import logging
import sys
from tooloo_v3_hub.kernel.orchestrator import get_orchestrator
from tooloo_v3_hub.kernel.mcp_nexus import get_nexus

# Setup structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TooLoo-V3-Hub")

async def main():
    logger.info("Initializing TooLoo V3 Hub...")
    
    # 1. Initialize Nexus and attach Federated Organs (CLOUD RUN / SSE)
    nexus = get_nexus()
    
    # Federated Memory Organ (Cloud Run)
    await nexus.attach_organ("memory_organ", "https://memory-organ-v3-gru3xdvw6a-ew.a.run.app/sse")
    
    # Federated Audio Organ (Claudio - Cloud Run)
    await nexus.attach_organ("audio_organ", "https://claudio-organ-v3-gru3xdvw6a-ew.a.run.app/sse")
    
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
    
    calibration = get_calibration_engine()
    proactive = get_proactive_agent()
    ouroboros = get_ouroboros()
    
    logger.info("Sovereign Context Established. Launching Federated Hub Pulse.")
    
    # We run the initial strategic goal, the proactive soul, the autonomous calibration, and Ouroboros in parallel
    await asyncio.gather(
        orchestrator.execute_goal(goal, context, mode="PATHWAY_B"),
        proactive.start_proactive_loop(),
        calibration.start_calibration_loop(interval=180), # Pulse every 3 minutes
        ouroboros.start_self_healing_loop(interval=300)   # Self-heal every 5 minutes
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Sovereign Hub Terminated by Architect.")
