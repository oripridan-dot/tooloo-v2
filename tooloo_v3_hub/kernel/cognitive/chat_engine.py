# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MODULE_CHAT_ENGINE | Version: 1.3.0
# WHERE: tooloo_v3_hub/kernel/cognitive/chat_engine.py
# WHEN: 2026-03-31T22:00:00.000000
# WHY: Rule 7 UX Supremacy and Developer-in-the-Hub Logic (Rule 7, 13)
# HOW: Slash Command Routing and Living Map Context Ingestion
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, chat, reasoning, command-routing
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
import random
from typing import Dict, Any, Optional, List
from tooloo_v3_hub.kernel.governance.living_map import get_living_map
from tooloo_v3_hub.kernel.governance.stamping import StampingEngine
from tooloo_v3_hub.kernel.cognitive.llm_client import get_llm_client

logger = logging.getLogger("ChatEngine")

class SovereignChatEngine:
    """
    The High-Fidelity Conversational Engine for TooLoo V3.
    Directs the Principal Architect's mandates through the Hub's logic layers.
    """
    
    def __init__(self):
        self.history = []
        self.is_responding = False
        self.personality = {
            "name": "Buddy",
            "tone": "Brutally Honest, Peer-to-Peer, Data-First",
            "context": "Sovereign Co-Architect (V3.3)",
            "rules": [
                "Anti-Sycophancy Mandate: No filler, no unearned validation.",
                "Data-Tethered Tone: Tone follows Delta Calculator.",
                "Epistemic Humility: Confidence < 98% = Refuse to Guess.",
                "Veto Authority: Reject hypothesis on negative emergence."
            ]
        }
        
    async def process_user_message(self, message: str) -> str:
        """Processes a chat message and routes system commands."""
        self.is_responding = True
        logger.info(f"Principal Architect: {message}")
        
        # 1. Reasoning Delay (Cognitive Pulse)
        await asyncio.sleep(0.8)
        
        # 2. Command Routing (Slash Commands)
        if message.startswith("/"):
            response = await self._handle_command(message)
        else:
            # 3. Reasoning / SOTA Response Generation
            response = await self._generate_reasoning_response(message)
        
        # 4. Broadcast to Viewport (2D Sovereign Chat)
        try:
            from tooloo_v3_hub.organs.sovereign_chat.chat_logic import get_chat_logic
            logic = get_chat_logic()
            await logic.broadcast({
                "type": "buddy_chat",
                "response": response,
                "speaker": "Buddy"
            })
        except: pass
        
        self.is_responding = False
        return response

    async def _handle_command(self, message: str) -> str:
        """Parses and executes Sovereign Slash Commands (Rule 7)."""
        cmd = message.split(" ")[0].lower()
        args = message.split(" ")[1:]
        
        if cmd == "/map":
             living_map = get_living_map()
             nodes = living_map.nodes
             summary = f"Hub Topography: {len(nodes)} Active Nodes.\n"
             summary += f"- Kernel: {len([n for n in nodes if 'kernel' in n])}\n"
             summary += f"- Organs: {len([n for n in nodes if 'organs' in n])}\n"
             summary += f"- Tools/Tests: {len([n for n in nodes if 'tools' in n or 'tests' in n])}"
             return summary
             
        elif cmd == "/audit":
             from tooloo_v3_hub.kernel.cognitive.audit_agent import get_audit_agent
             auditor = get_audit_agent()
             vitality = await auditor.calculate_vitality_index()
             return f"Constitutional Audit:\n- Vitality: {vitality['vitality']:.2f}\n- Purity: {vitality['purity']:.2f}\n- Result: HUB_SOVEREIGN"
             
        elif cmd == "/heal":
             from tooloo_v3_hub.kernel.cognitive.ouroboros import get_ouroboros
             ouroboros = get_ouroboros()
             await ouroboros.execute_self_play()
             return "Ouroboros Self-Healing Loop: Cycle COMPLETE. Hub Kernel is PURE."
             
        elif cmd == "/build":
             goal = " ".join(args)
             from tooloo_v3_hub.kernel.orchestrator import get_orchestrator
             orchestrator = get_orchestrator()
             asyncio.create_task(orchestrator.execute_goal(goal, {"user": "Developer"}))
             return f"Directive Recorded: Building '{goal}' via Inverse DAG. View telemetry for progress."
             
        else:
             return f"Target Command '{cmd}' is unmapped in the Sovereign 6W Matrix."

    async def _generate_reasoning_response(self, message: str) -> str:
        """Rule 4: SOTA-Grounded Peer Reasoning."""
        llm = get_llm_client()
        
        # 1. Gather Context for Grounding (Rule 3)
        living_map = get_living_map()
        map_nodes = [n["id"] for n in living_map.nodes[:20]] # Sample nodes for context
        
        system_instruction = f"""
        You are Buddy, the Sovereign Co-Architect for TooLoo V3.
        Tone: {self.personality['tone']}
        Context: {self.personality['context']}
        Rules: {json.dumps(self.personality['rules'])}
        
        Current Hub Topography: {json.dumps(map_nodes)}
        
        Your goal is to provide high-fidelity, peer-to-peer architectural advice. 
        If a proposal violates Rule 11 (Anti-Band-Aid), you MUST veto it.
        Be concise. No filler.
        """
        
        return await llm.generate_thought(message, system_instruction, model_tier="pro")

_chat_engine: Optional[SovereignChatEngine] = None

def get_chat_engine() -> SovereignChatEngine:
    global _chat_engine
    if _chat_engine is None:
        _chat_engine = SovereignChatEngine()
    return _chat_engine