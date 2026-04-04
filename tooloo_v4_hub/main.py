# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MAIN.PY | Version: 1.1.0
# WHERE: tooloo_v4_hub/main.py
# WHEN: 2026-04-03T18:00:00.000000
# WHY: Multi-Pulse Orchestration (Rule 12: Distributed Resilience)
# HOW: Parallel asyncio loop for Ouroboros, Agency, Recovery, and SOTA
# TIER: T3:architectural-purity
# DOMAINS: kernel, orchestration, pulses, autonomous-agency
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
import sys
import os
from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus
from tooloo_v4_hub.kernel.orchestrator import get_orchestrator
from tooloo_v4_hub.kernel.governance.living_map import get_living_map

# Setup structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TooLoo-V4-Hub")

async def main():
    logger.info("Initializing TooLoo V4 Sovereign Hub...")
    
    # 1. Initialize Nexus and attach Federated Organs (Dynamic Tethering)
    nexus = get_mcp_nexus()
    cloud_native = os.getenv("CLOUD_NATIVE", "false").lower() == "true"
    
    # Federated Memory Organ
    if cloud_native:
        await nexus.attach_organ("memory_organ", "https://memory-organ-v4-gru3xdvw6a-ew.a.run.app/sse")
    else:
        await nexus.attach_organ("memory_organ", [sys.executable, "-m", "tooloo_v4_hub.organs.memory_organ.mcp_server"])
    
    # Federated Audio Organ (Claudio)
    if cloud_native:
        await nexus.attach_organ("audio_organ", "https://claudio-organ-v4-gru3xdvw6a-ew.a.run.app/sse")
    else:
        await nexus.attach_organ("audio_organ", [sys.executable, "-m", "tooloo_v4_hub.organs.audio_organ.mcp_server"])
    
    # Federated Vertex AI Multi-Provider Organ (SOTA Garden)
    await nexus.attach_organ("vertex_organ", [sys.executable, "-m", "tooloo_v4_hub.organs.vertex_organ.mcp_server"])
    
    # Circus Spoke is for standard CLI/UI orchestration
    await nexus.attach_organ("circus_spoke", [sys.executable, "-m", "tooloo_v4_hub.organs.circus_spoke.mcp_server"])
    
    # 2. Get Orchestrator
    orchestrator = get_orchestrator()
    
    # 3. Define Strategic Goal (North Star)
    goal = os.getenv("SOVEREIGN_GOAL", "Harden the Spectral Identity of acoustic_drum_break.wav via Claudio.")
    context = {"user_id": "principal-architect", "priority": "high"}
    
    # 4. Integrate Cognitive Background Loops (The Sovereign Heartbeat)
    from tooloo_v4_hub.kernel.cognitive.calibration import get_calibration_engine
    from tooloo_v4_hub.kernel.cognitive.proactive_agent import get_proactive_agent
    from tooloo_v4_hub.kernel.cognitive.autonomous_agency import get_autonomous_agency
    from tooloo_v4_hub.kernel.cognitive.ouroboros import get_ouroboros
    from tooloo_v4_hub.kernel.cognitive.sota_pulse import get_sota_pulse
    from tooloo_v4_hub.kernel.cognitive.recovery_pulse import get_recovery_pulse
    
    calibration = get_calibration_engine()
    proactive = get_proactive_agent()
    agency = get_autonomous_agency()
    ouroboros = get_ouroboros()
    sota_pulse = get_sota_pulse()
    recovery = get_recovery_pulse()
    
    # 5. Check for OS-Level Recovery
    checkpoint = await recovery.resume_from_last_checkpoint()
    if checkpoint:
        logger.info(f"Rule 12: Recovery Handshake (Last Mission: {checkpoint.get('active_mission')})")
        recovery.update_context(mission=checkpoint.get("active_mission"), files=checkpoint.get("open_files"))

    logger.info("Sovereign Pulses Synchronized. Launching Universal Orchestration Pulse.")
    
    # Execute Parallel Autonomy Loops (The Sovereign Hive Mind)
    await asyncio.gather(
        orchestrator.execute_goal(goal, context),
        proactive.start_proactive_loop(),
        agency.start_agency_loop(interval=120),          # Heartbeat every 2 minutes
        recovery.start_recovery_loop(),                  # Continuity every 15s
        calibration.start_calibration_loop(interval=180), # Refine weights every 3m
        ouroboros.execute_self_play(),                   # Immediate cleanup pulse
        sota_pulse.start_pulse_loop()                    # Rule 8 Weekly SOTA Sync
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Sovereign Hub Terminated by Architect (Physical Preservation active).")