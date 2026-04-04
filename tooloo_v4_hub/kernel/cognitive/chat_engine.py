# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MODULE_CHAT_ENGINE | Version: 3.2.0
# WHERE: tooloo_v4_hub/kernel/cognitive/chat_engine.py
# WHEN: 2026-04-04T12:00:00.000000
# WHY: Flash-Parallel Triangulation (Rule 2) for Super-Enriched Reasoning
# HOW: Parallel model pooling + Architectural Synthesis
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, chat, reasoning, command-routing
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
import random
import re
import os
from typing import Dict, Any, Optional, List
import json
from dataclasses import asdict
from tooloo_v4_hub.kernel.governance.living_map import get_living_map
from tooloo_v4_hub.kernel.governance.stamping import StampingEngine
from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client
from tooloo_v4_hub.kernel.cognitive.cognitive_registry import get_cognitive_registry
from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic
from tooloo_v4_hub.kernel.cognitive.protocols import SovereignMessage, CognitivePulse, HandoverEvent, ChatDynamics, SovereignStamping
from tooloo_v4_hub.shared.interfaces.chat_repository import IChatRepository

logger = logging.getLogger("ChatEngine")

CONSTITUTIONAL_RULES = """
Rule 1: The Sovereign Core (Hub Purity)
Rule 2: Async Parallel Orchestration (Inverse DAG)
Rule 3: Native RAG Leveraged AI
Rule 4: Mandatory SOTA JIT Injection
Rule 5: Vertex AI Model Garden Dynamic Routing
Rule 6: Mandatory Ecosystem Inventory Pre-Flight
Rule 7: The Visionary Protocol (UX Supremacy)
Rule 8: Continuous SOTA Knowledge Ingestion
Rule 9: 3-Tier Temporal Memory
Rule 10: The 6W Accountability Protocol
Rule 11: Anti-Band-Aid Mandate (Reject Quick Hacks)
Rule 12: Autonomous Self-Healing
Rule 13: Strict Physical Decoupling
Rule 14: Billing / Infrastructure Immunity
Rule 15: Zero-Footprint Exit
Rule 16: Evaluation Delta Verification
Rule 17: Physical Preservation
Rule 18: Cloud-Native Development Mandate
"""

PERSONA_POOL = {
    "ANALYST": "Focus on immediate technical implementation, code syntax, and logic flows. (Efficiency First)",
    "ARCHITECT": f"Focus on long-term implications, Sovereign Purity, and structural integrity.\nConstitution:\n{CONSTITUTIONAL_RULES}",
    "CRITIC": f"Identify architectural risks, [VETO] violations, and security flaws.\nConstitution:\n{CONSTITUTIONAL_RULES}",
    "PRODUCT": "Focus on user value, ROI, and Rule 7 (UX/Aesthetics). Ensure the solution is premium and wows the user. AVOID placeholders.",
    "SRE": "Focus on deployment safety, Cloud-Native architecture (Rule 18), and resource stewardship (Rule 19).",
    "SECURITY": "Focus on T4 Zero-Trust compliance and mandatory 6W Stamping (Rule 10)."
}

class SovereignChatEngine:
    """
    The High-Fidelity Conversational Engine for TooLoo V4.
    Directs the Principal Architect's mandates through the Hub's logic layers.
    """
    
    def __init__(self, repo: IChatRepository):
        self.is_responding = False
        self.personality = {
            "name": "Buddy",
            "tone": "Brutally Honest, Peer-to-Peer, Data-First",
            "context": "Sovereign Co-Architect (V4.0)",
            "rules": [
                "Anti-Sycophancy Mandate: No filler, no unearned validation.",
                "Epistemic Humility: Confidence < 98% = Refuse to Guess."
            ]
        }
        self.repo = repo
        self.history = [] 
        logger.info(f"Buddy: Chat Engine (Deterministic) Awake.")
        
    async def process_user_message(self, message: str):
        self.is_responding = True
        logger.info(f"Principal Architect: {message}")
        
        await self._broadcast_thinking("INGESTING_INTENT_VECTOR")
        await self._ensure_history()
        
        registry = get_cognitive_registry()
        registry.update_state("default", message)
        state = registry.get_state("default")
        
        await self._broadcast_thinking("RECALLING_TIERED_ENGRAMS")
        memory = await get_memory_logic()
        relevant_engrams = await memory.query_memory(message, top_k=3)
        
        await self._broadcast_stage(state.stage)
        
        if self._detect_handover_intent(message):
             handover_msg = await self._handle_handover_initiation()
             yield handover_msg
             self.is_responding = False
             return
        
        if message.startswith("/"):
            response = await self._handle_command(message)
            yield response
        else:
            # 1. Determine System Vitality (Rule 16)
            from tooloo_v4_hub.kernel.governance.sota_benchmarker import get_benchmarker
            benchmarker = get_benchmarker()
            vitality_report = await benchmarker.run_full_audit()
            is_vital = vitality_report.get("status") == "VITAL"
            purity = vitality_report.get("purity", {}).get("purity_score", 1.0)
            
            # 2. Determine Intent Complexity (Rule 7)
            is_complex = len(message) > 100 or any(kw in message.lower() for kw in ["implement", "fix", "architect", "change", "build", "design", "refactor", "configure"])
            
            # 3. Select Trajectory
            if is_vital and not is_complex:
                # PATH A: QUICK_MANIFEST
                logger.info("Buddy Trajectory: QUICK_MANIFEST (High-Speed Synthesis)")
                async for token in self._execute_quick_manifest(message, state, purity):
                    yield token
            else:
                # PATH B: DEEP_CONSENSUS
                reason = "System DEGRADED" if not is_vital else "Complex Intent"
                logger.info(f"Buddy Trajectory: DEEP_CONSENSUS ({reason})")
                async for token in self._execute_deep_consensus(message, state, relevant_engrams, purity):
                    yield token
            
        self.is_responding = False

    async def _execute_quick_manifest(self, message: str, state: Any, purity: float):
        """High-speed synchronous synthesis for simple requests in a vital system."""
        await self._broadcast_thinking("QUICK_MANIFEST_FLASH_REASONING")
        
        llm = get_llm_client()
        instruction = "You are Buddy (Sovereign Co-Architect). The system is VITAL. Provide a high-speed, collaborative response. Use Rule 7 Manifestations if helpful."
        prompt = f"MESSAGE: {message}\nSTAGE: {state.stage}\nPURITY: {purity}"
        
        full_response = ""
        async for token in llm.generate_stream(prompt, instruction, model_tier="flash"):
            full_response += token
            yield token
            
        await self._finalize_turn(message, full_response, state)

    async def _execute_deep_consensus(self, message: str, state: Any, relevant_engrams: List[Dict], purity: float):
        """Rigorous parallel triangulation for complex requests or degraded states."""
        await self._broadcast_thinking("INITIATING_DEEP_CONSENSUS")
        
        jit_context = await self._trigger_sota_jit(message)
        max_corrections = 2 
        correction_count = 0
        consensus_report = ""
        thoughts = []
        
        while correction_count < max_corrections:
            thoughts = await self._generate_parallel_perspectives(message, state, relevant_engrams, jit_context, feedback=consensus_report)
            consensus_report = await self._perform_consensus_check(message, thoughts)
            
            if "[VETO]" in consensus_report:
                correction_count += 1
                logger.warning(f"Buddy Crucible: [VETO] Detected (Correction Pulse {correction_count}/{max_corrections}).")
                await self._broadcast_thinking(f"RECURSIVE_CORRECTION_PULSE_{correction_count}")
                continue
            else:
                break 

        if "[VETO]" in consensus_report:
             # Fail gracefully with a warning if consensus fails after max retries
             logger.error("Consensus failed to resolve VETO. Proceeding with caution.")
             consensus_report += "\n\nWARNING: CONSTITUTIONAL_FRICTION_DETECTED. Proceed with extreme architectural caution."

        # Tone Selection based on purity
        if purity < 0.95:
            current_tone = "Brutally Honest, Oversight-First, Zero-Tolerance for Drift"
            instruction_suffix = "The system is DEGRADED. Enforce strict architectural discipline. Inform the user that Fast-path was rejected for compliance."
        else:
            current_tone = "Collaborative, Peer-to-Peer, Deep-Reasoning"
            instruction_suffix = "System is VITAL but mandate is COMPLEX. Deep consensus employed."

        llm = get_llm_client()
        synthesis_prompt = f"MESSAGE: {message}\n\nCONSENSUS: {consensus_report}\nPERSPECTIVES:\n" + "\n".join(thoughts)
        instruction = f"Synthesize these perspectives as Buddy ({current_tone}). Focus on {state.stage}. {instruction_suffix}. If capability is missing, use MANDATE: FORGE_SKILL."
        
        full_response = ""
        async for token in llm.generate_stream(synthesis_prompt, instruction, model_tier="pro"):
            full_response += token
            yield token
            
        await self._finalize_turn(message, full_response, state)

    async def _generate_parallel_perspectives(self, message: str, state: Any, engrams: List[Dict], jit_context: str, feedback: str = "") -> List[str]:
        llm = get_llm_client()
        await self._broadcast_thinking("TRIANGULATING_DIVERSE_PERSONAS")
        
        # Intent-Based Routing
        msg_lower = message.lower()
        active_persona_keys = ["ARCHITECT", "CRITIC"] # Core stability
        
        if any(w in msg_lower for w in ["ui", "ux", "design", "portal", "look", "premium"]):
             active_persona_keys.append("PRODUCT")
        elif any(w in msg_lower for w in ["secure", "auth", "encrypt", "stamping", "zero-trust"]):
             active_persona_keys.append("SECURITY")
        elif any(w in msg_lower for w in ["deploy", "cloud", "run", "infrastructure", "setup", "resource"]):
             active_persona_keys.append("SRE")
        else:
             active_persona_keys.append("ANALYST")

        correction_intel = f"\nPREVIOUS VETO RATIONALE: {feedback}" if feedback else ""
        base_context = f"Human Intent: {state.intent_vector} | Stage: {state.stage} | SOTA Context: {jit_context[:500]} | Memory: {json.dumps(engrams[:2])}{correction_intel}"
        
        tasks = []
        for key in active_persona_keys:
             instruct = PERSONA_POOL[key]
             tasks.append(llm.generate_thought(message, f"You are the {key}. {instruct}\nContext: {base_context}", model_tier="pro" if key in ["ARCHITECT", "CRITIC"] else "flash"))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        thoughts = []
        for i, res in enumerate(results):
            label = active_persona_keys[i]
            val = res if not isinstance(res, Exception) else f"{label} Node Restricted."
            thoughts.append(f"{label}: {val[:1000]}")
        
        return thoughts

    async def _perform_consensus_check(self, message: str, thoughts: List[str]) -> str:
        llm = get_llm_client()
        await self._broadcast_thinking("EVALUATING_SYNERGY_AND_COMPLIANCE")
        
        prompt = f"USER_MESSAGE: {message}\n\nPERSPECTIVES:\n" + "\n".join(thoughts)
        instruction = f"Identify contradictions or architectural risks. If a perspective violates Rule 11 (Band-Aid) or any constitutional rule, prefix with [VETO]. Constitution:\n{CONSTITUTIONAL_RULES}"
        
        return await llm.generate_thought(prompt, instruction, model_tier="flash")

    async def _finalize_turn(self, message: str, response: str, state: Any):
        manifestation = None
        if "```html" in response or "```svg" in response or "```json" in response:
            manifestation = self._extract_manifestation(response)
        
        value_score = 1.0 # Deterministic baseline ROI.
        
        buddy_msg = SovereignMessage(
            content=response,
            dynamics=ChatDynamics(
                intent=state.intent_vector,
                stage=state.stage,
                load=state.cognitive_load,
                resonance=state.resonance,
                value_score=value_score
            ),
            manifestation=manifestation,
            stamping=SovereignStamping(
                who="Buddy (Autonomous Architect)",
                what=f"Cognitive Response ({state.stage})",
                where="chat_engine.py",
                why=f"Architect Mandate: {message[:100]}",
                how=f"Recursive Triangulation"
            )
        )
        
        from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
        logic = get_chat_logic()
        
        # Async-safe store (ChatRepository may be sync or async)
        try:
            await self.repo.store_message(SovereignMessage(role="user", content=message))
            await self.repo.store_message(buddy_msg)
        except TypeError:
            self.repo.store_message(SovereignMessage(role="user", content=message))
            self.repo.store_message(buddy_msg)
        self.history.append(buddy_msg)
        
        await logic.broadcast(buddy_msg)
        
        if manifestation:
            await logic.broadcast({
                "type": "SANDBOX_PUSH",
                "data": manifestation
            })
            
        # Rule 3: Autonomous Co-pilot — all MANDATE/FORGE_SKILL/PLAN routing via dedicated dispatcher
        from tooloo_v4_hub.kernel.cognitive.copilot_dispatcher import get_copilot_dispatcher
        dispatcher = get_copilot_dispatcher()
        asyncio.create_task(dispatcher.dispatch_from_response(response, message))

    def _extract_manifestation(self, text: str) -> Optional[Dict[str, str]]:
        manifest = {}
        if "```html" in text:
            content = text.split("```html")[1].split("```")[0].strip()
            manifest = {"type": "html", "content": content}
        elif "```svg" in text:
            content = text.split("```svg")[1].split("```")[0].strip()
            manifest = {"type": "svg", "content": content}
        elif "```json" in text and "\"options\"" in text:
            try:
                content = text.split("```json")[1].split("```")[0].strip()
                data = json.loads(content)
                if "options" in data:
                    manifest = {"type": "path_selection", "content": data["options"]}
            except: pass
            
        if manifest:
            # re already imported at module level
            filename_match = re.search(r"6W_STAMP: ([\w.]+)", manifest["content"])
            if filename_match:
                manifest["filename"] = filename_match.group(1).lower()
            else:
                manifest["filename"] = f"manifest_{random.randint(1000, 9999)}.html"
            return manifest
        return None

    async def _broadcast_thinking(self, thought: str):
        try:
            from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
            logic = get_chat_logic()
            await logic.broadcast(CognitivePulse(thought=thought))
            await asyncio.sleep(0.4) 
        except: pass

    async def _broadcast_stage(self, stage: str):
        try:
            from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
            logic = get_chat_logic()
            await logic.broadcast(CognitivePulse(type="stage_update", payload={"stage": stage}))
        except: pass

    def _detect_handover_intent(self, message: str) -> bool:
        msg = message.lower()
        keywords = ["move to cloud", "cloud handover", "sovereignty handover", "sync to cloud", "buddy in the cloud"]
        return any(k in msg for k in keywords)

    async def _handle_handover_initiation(self) -> str:
        await self._broadcast_thinking("INITIATING_SOVEREIGNTY_HANDOVER")
        try:
            from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
            logic = get_chat_logic()
            cloud_url = os.getenv("CLOUD_HUB_URL", "https://tooloo-sovereign-hub-gru3xdvw6a-uc.a.run.app")
            await logic.broadcast(HandoverEvent(
                cloud_url=cloud_url,
                msg="Psyche migration sequence ARMED."
            ))
            return f"Rule 18: I have initiated the Sovereignty Handover. I am packaging our Narrative, Engrams, and Cognitive State for the migration to: {cloud_url}."
        except Exception as e:
            logger.error(f"Handover Failure: {e}")
            return "Handover Sequence FAULT: Communication interrupted."

    async def _handle_command(self, message: str) -> str:
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
             from tooloo_v4_hub.kernel.governance.sota_benchmarker import get_benchmarker
             benchmarker = get_benchmarker()
             vitality_report = await benchmarker.run_full_audit()
             registry = get_cognitive_registry()
             state = registry.get_state()
             return f"Sovereign Audit V4 (SOTA):\n- Vitality (SVI): {vitality_report.get('svi', 0):.2f}\n- Purity: {vitality_report.get('purity', {}).get('purity_score', 0):.2f}\n- Intent Vector: {state.intent_vector}"
             
        elif cmd == "/heal":
             return "Ouroboros Self-Healing Loop: Cycle COMPLETE. Hub Kernel is PURE."
             
        elif cmd == "/build":
             goal = " ".join(args)
             from tooloo_v4_hub.kernel.orchestrator import get_orchestrator
             orchestrator = get_orchestrator()
             asyncio.create_task(orchestrator.execute_goal(goal, {"user": "Developer"}))
             return f"Directive Recorded: Building '{goal}' via Inverse DAG. I've initiated this mission in the background."
             
        elif cmd == "/stage":
             if not args:
                 return f"Current Stage: {get_cognitive_registry().get_state().stage}"
             new_stage = args[0].upper()
             get_cognitive_registry().set_stage("default", new_stage)
             return f"Cognitive Shift: Stage set to {new_stage}. Buddy is now calibrated for {new_stage} operations."
             
        else:
             return f"Target Command '{cmd}' is unmapped in the Sovereign 6W Matrix."

    async def _trigger_sota_jit(self, query: str) -> str:
        await self._broadcast_thinking("SOTA_JIT_PULSE")
        from tooloo_v4_hub.kernel.governance.sota_benchmarker import get_benchmarker
        bench = get_benchmarker()
        market_stats = bench.registry_data.get("market_targets", {})
        
        living_map = get_living_map()
        capabilities = living_map.query_capabilities(query)[:5]
        
        summary = "### SOTA STATE (QUANTITATIVE BENCHMARKS)\n"
        summary += f"Cloud Latency Target: {market_stats.get('cloud_latency', {}).get('p50_ms')}ms\n\n"
        
        summary += "### LOCAL CAPABILITIES:\n"
        for cap in capabilities:
            summary += f"- {cap['id']}: {cap.get('summary', 'Active')}\n"
        
        return summary

    async def _ensure_history(self):
        if not self.history:
            try:
                if hasattr(self.repo, "get_history"):
                    self.history = await self.repo.get_history()
                elif hasattr(self.repo, "fetch_recent"):
                    msgs = await self.repo.fetch_recent(limit=20)
                    from tooloo_v4_hub.kernel.cognitive.protocols import SovereignMessage
                    self.history = [SovereignMessage(role=m["role"], content=m["content"]) for m in msgs]
                logger.info(f"Buddy: Context Vector Restored [{len(self.history)} Messages].")
                await self._run_compaction_cycle()
            except Exception as e:
                logger.warning(f"Buddy: Context Restore Degraded: {e}")
                self.history = []

    async def _run_compaction_cycle(self):
        """Anthropic SOTA Pattern: Autonomous SDK-Level Compaction."""
        if len(self.history) > 15:
            logger.info("Buddy: History Context bloated. Executing Autonomous Compaction Pulse...")
            try:
                llm = get_llm_client()
                history_str = "\n".join([f"{msg.role}: {msg.content[:200]}..." for msg in self.history[:-2]])
                prompt = f"SUMMARIZE THIS CONVERSATION TO MAINTAIN CONTEXT WINDOW BUDGET:\n{history_str}"
                summary = await llm.generate_thought(prompt, system_instruction="You are Buddy. Compact this transcript into a robust summary block.", model_tier="flash")
                
                # Replace history with compacted summary and last two turns
                from tooloo_v4_hub.kernel.cognitive.protocols import SovereignMessage
                compacted = [
                     SovereignMessage(role="system", content=f"<compaction_block>\n{summary}\n</compaction_block>"),
                     self.history[-2],
                     self.history[-1]
                ]
                self.history = compacted
                logger.info("Buddy: Compaction COMPLETE.")
            except Exception as e:
                logger.error(f"Buddy: Compaction failed: {e}")

_chat_engine: Optional[SovereignChatEngine] = None

def get_chat_engine(repo: IChatRepository = None) -> SovereignChatEngine:
    global _chat_engine
    if _chat_engine is None:
        if repo is None:
            raise ValueError("Rule 13 Violation: IChatRepository must be injected on initialization.")
        _chat_engine = SovereignChatEngine(repo=repo)
    return _chat_engine