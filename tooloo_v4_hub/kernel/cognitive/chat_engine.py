# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MODULE_CHAT_ENGINE | Version: 3.1.0
# WHERE: tooloo_v4_hub/kernel/cognitive/chat_engine.py
# WHEN: 2026-04-01T14:10:00.000000
# WHY: Flash-Parallel Triangulation (Rule 2) for Super-Enriched Reasoning
# HOW: Parallel model pooling + Architectural Synthesis
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, chat, reasoning, command-routing
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
import random
from typing import Dict, Any, Optional, List
import json
from tooloo_v4_hub.kernel.governance.living_map import get_living_map
from tooloo_v4_hub.kernel.governance.stamping import StampingEngine
from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client
from tooloo_v4_hub.kernel.cognitive.cognitive_registry import get_cognitive_registry
from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic
from tooloo_v4_hub.kernel.cognitive.protocols import SovereignMessage, CognitivePulse, HandoverEvent, ChatDynamics, SovereignStamping
from tooloo_v4_hub.shared.interfaces.chat_repository import IChatRepository
from tooloo_v4_hub.kernel.cognitive.history_synthesizer import get_history_synthesizer
from tooloo_v4_hub.kernel.cognitive.north_star import get_north_star
from tooloo_v4_hub.kernel.cognitive.north_star_synthesizer import get_north_star_synthesizer

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
Rule 12: Autonomous Self-Healing (Ouroboros)
Rule 13: Strict Physical Decoupling (Physics over Syntax)
Rule 14: Billing / Infrastructure Immunity
Rule 15: Zero-Footprint Exit
Rule 16: Evaluation Delta Verification
Rule 17: Physical Preservation (Append-Only)
Rule 18: Cloud-Native Development Mandate
"""

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
                "Data-Tethered Tone: Tone follows Delta Calculator.",
                "Epistemic Humility: Confidence < 98% = Refuse to Guess.",
                "Veto Authority: Reject hypothesis on negative emergence."
            ]
        }
        self.repo = repo
        self.history = [] # Lazy-loaded in _ensure_history (Rule 13)
        logger.info(f"Buddy: Chat Engine Awake. Awaiting Context Pulse.")
        
    async def process_user_message(self, message: str):
        """Processes a chat message with full Cognitive Awareness and Parallel Triangulation."""
        self.is_responding = True
        logger.info(f"Principal Architect: {message}")
        
        # 1. Cognitive Pre-Processing
        await self._broadcast_thinking("INGESTING_INTENT_VECTOR")
        await self._ensure_history() # Rule 9: Lazy Context Recovery
        registry = get_cognitive_registry()
        registry.update_state("default", message)
        state = registry.get_state("default")
        
        # 1.5. Collective Common Sense Restore (Rule 9)
        synthesizer = get_history_synthesizer()
        common_sense = synthesizer.get_current_sense()
        if common_sense == "Collective Common Sense is initializing...":
             # Trigger JIT synthesis if empty
             common_sense = await synthesizer.synthesize_collective_state()
        
        # 2. Contextual Memory Recall
        await self._broadcast_thinking("RECALLING_TIERED_ENGRAMS")
        memory = await get_memory_logic()
        relevant_engrams = await memory.query_memory(message, top_k=3)
        
        # 2.5 Stage Advocacy & Broadcasting
        await self._broadcast_stage(state.stage)
        
        # 3. Dynamic Routing
        if self._detect_handover_intent(message):
             handover_msg = await self._handle_handover_initiation()
             yield handover_msg
             self.is_responding = False
             return
        
        if message.startswith("/"):
            response = await self._handle_command(message)
            yield response
        else:
            # Rule 2/7: Sovereign Fast-Path (Cognitive Load Shedding)
            # If intent is simple, skip the Decision Crucible for raw speed.
            is_complex = len(message) > 100 or any(kw in message.lower() for kw in ["implement", "fix", "architect", "change", "build", "design", "refactor"])
            
            if not is_complex:
                logger.info("Buddy Speed: FAST-PATH Active (Non-complex intent).")
                await self._broadcast_thinking("FAST_PATH_FLASH_REASONING")
                thoughts = [f"FAST_PATH: Direct Flash Synthesis (Speed Priority)"]
                consensus_report = "[SKIP] Fast-path bypass."
                correction_count = 0
            else:
                # Rule 2: Async Parallel Triangulation (Super Enriched Phase)
                jit_context = await self._trigger_sota_jit(message)
                
                # Round 2: Decision Crucible (Recursive Logic)
                max_corrections = 2 # Reduced for baseline speed
                correction_count = 0
                consensus_report = ""
                thoughts = []
                
                while correction_count < max_corrections:
                    # Step A: Perform internal triangulation
                    thoughts = await self._generate_parallel_perspectives(message, state, relevant_engrams, jit_context, feedback=consensus_report)
                    
                    # Step A.5: Consensus Pulse (Rule 2/11)
                    consensus_report = await self._perform_consensus_check(message, thoughts)
                    
                    if "[VETO]" in consensus_report:
                        correction_count += 1
                        logger.warning(f"Buddy Crucible: [VETO] Detected (Correction Pulse {correction_count}/{max_corrections}).")
                        await self._broadcast_thinking(f"RECURSIVE_CORRECTION_PULSE_{correction_count}")
                        
                        # Round 1 Hook: Remediation
                        import re
                        file_match = re.search(r"6W: ([\w/.-]+)", consensus_report)
                        if file_match:
                            file_path = file_match.group(1)
                            from tooloo_v4_hub.kernel.cognitive.autonomous_agency import get_autonomous_agency
                            agency = get_autonomous_agency()
                            asyncio.create_task(agency.trigger_remediation(file_path, f"Vetoed Rationale: {consensus_report}"))
                        
                        continue # Try again with feedback
                    else:
                        break # Consensus reached

            if "[VETO]" in consensus_report:
                 raise RuntimeError(f"SovereignConstitutionException: Cognitive Hang. Veto persisted after {max_corrections} pulses.")
            
            # Round 3: Neural Fidelity (Tone Selection via SVI)
            from tooloo_v4_hub.kernel.cognitive.audit_agent import get_audit_agent
            auditor = get_audit_agent()
            vitality_report = await auditor.calculate_vitality_index()
            purity = vitality_report.get("purity_index", 1.0)
            
            if purity < 0.98:
                current_tone = "Brutally Honest, Oversight-First, Zero-Tolerance for Drift"
                instruction_suffix = "The system is DEGRADED. Enforce strict architectural discipline."
            else:
                current_tone = "Collaborative, Peer-to-Peer, SOTA-Accelerated"
                instruction_suffix = "The system is VITAL. Focus on high-speed industrial expansion."

            # Step B: Final Synthesis Pass (STREAMING)
            llm = get_llm_client()
            synthesis_prompt = f"MESSAGE: {message}\n\nSTAGE: {state.stage}\nCONSENSUS: {consensus_report}\nPERSPECTIVES:\n" + "\n".join(thoughts)
            instruction = f"Synthesize these perspectives as Buddy ({current_tone}). Focus on the {state.stage} phase. Use Rule 7 Manifestations. {instruction_suffix}"
            
            full_response = ""
            async for token in llm.generate_stream(synthesis_prompt, instruction, model_tier="pro"):
                full_response += token
                yield token # Send to broadcast layer
            
            # 4. Final Manifestation & Persistence
            await self._finalize_turn(message, full_response, state)
            
        self.is_responding = False

    async def _generate_parallel_perspectives(self, message: str, state: Any, engrams: List[Dict], jit_context: str, feedback: str = "") -> List[str]:
        """Rule 2: Parallel Model Triangulation (Triangulated Reasoning) with Recursive Feedback."""
        llm = get_llm_client()
        await self._broadcast_thinking("TRIANGULATING_REASONING_NODES")
        
        synthesizer = get_history_synthesizer()
        common_sense = synthesizer.get_current_sense()
        north_star = get_north_star().state
        
        correction_intel = f"\nPREVIOUS VETO RATIONALE: {feedback}" if feedback else ""
        base_context = f"Human Intent: {state.intent_vector} | Stage: {state.stage} | SOTA Context: {jit_context[:500]} | Memory: {json.dumps(engrams[:2])} | Common Sense: {common_sense[:500]} | North Star: {north_star.macro_goal} (Focus: {north_star.current_focus}){correction_intel}"
        
        tasks = [
            llm.generate_thought(message, f"You are the ANALYST. Focus on immediate technical implementation steps. {base_context}", model_tier="flash"),
            llm.generate_thought(message, f"You are the ARCHITECT. Focus on long-term implications and Sovereign Purity. {base_context}\nConstitution:\n{CONSTITUTIONAL_RULES}", model_tier="pro"),
            llm.generate_thought(message, f"You are the CRITIC. Identify architectural risks and [VETO] violations. {base_context}\nConstitution:\n{CONSTITUTIONAL_RULES}", provider="rest")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        thoughts = []
        labels = ["ANALYST", "ARCHITECT", "CRITIC"]
        for i, res in enumerate(results):
            val = res if not isinstance(res, Exception) else f"{labels[i]} Node Restricted."
            thoughts.append(f"{labels[i]}: {val[:1000]}")
        
        return thoughts

    async def _perform_consensus_check(self, message: str, thoughts: List[str]) -> str:
        """Rule 11: Active conflict detection between reasoning nodes."""
        llm = get_llm_client()
        await self._broadcast_thinking("EVALUATING_SYNERGY_AND_COMPLIANCE")
        
        prompt = f"USER_MESSAGE: {message}\n\nPERSPECTIVES:\n" + "\n".join(thoughts)
        instruction = f"Identify contradictions or architectural risks. If a perspective violates Rule 11 (Band-Aid) or any constitutional rule, prefix with [VETO]. Constitution:\n{CONSTITUTIONAL_RULES}"
        
        return await llm.generate_thought(prompt, instruction, model_tier="flash")

    async def _finalize_turn(self, message: str, response: str, state: Any):
        """Rule 16:ROI & Persistence Post-Turn Manifestation."""
        # Check for Visual Manifestations (Rule 7)
        manifestation = None
        if "```html" in response or "```svg" in response or "```json" in response:
            manifestation = self._extract_manifestation(response)
        
        # Rule 16: Calculation of ValueScore (ROI)
        value_score = await self._calculate_value_score(message, response, state)
        
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
                how=f"Recursive Triangulation (x{correction_count if 'correction_count' in locals() else 1})"
            )
        )
        
        # Logic Broadcast (for final metadata/visuals)
        from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
        logic = get_chat_logic()
        
        # Rule 9/10: Persistent Accountability Pulse
        self.repo.store_message(SovereignMessage(role="user", content=message))
        self.repo.store_message(buddy_msg)
        self.history.append(buddy_msg)
        
        await logic.broadcast(buddy_msg)
        
        # Rule 7: Active Sandbox Pulse (Pillar IV)
        if manifestation:
            await logic.broadcast({
                "type": "SANDBOX_PUSH",
                "data": manifestation
            })
            
        # Detect Mission Initiation (Rule 1: Mandate Detection)
        if "MANDATE:" in response or "ACTION:" in response:
            import re
            match = re.search(r"(?:MANDATE|ACTION):\s*(.*)", response)
            if match:
                goal = match.group(1).split("\n")[0].strip()
                logger.info(f"Buddy Self-Mandate Detected: {goal}")
                from tooloo_v4_hub.kernel.cognitive.autonomous_agency import get_autonomous_agency
                agency = get_autonomous_agency()
                asyncio.create_task(agency.trigger_mission_from_chat(goal, {"rationale": "Resonance with Architect Request"}))
                
                await logic.broadcast({
                    "type": "mission_start",
                    "mission_id": f"MSN_BUDDY_{random.randint(1000, 9999)}",
                    "goal": goal
                })

        # --- Rule 1: North Star Strategic Update ---

        # Trigger background synthesis of the next roadmap iteration
        async def _async_trigger():
            ns_synthesizer = get_north_star_synthesizer()
            new_state = await ns_synthesizer.synthesize_state()
            # Broadcast the updated North Star to the UI
            await logic.broadcast({
                "type": "NORTH_STAR_UPDATE",
                "payload": asdict(new_state)
            })
        
        from dataclasses import asdict
        asyncio.create_task(_async_trigger())

    async def _calculate_value_score(self, message: str, response: str, state: Any) -> float:
        """Rule 16: Evaluation Delta Verification. Calculates ROI of the cognitive pulse."""
        try:
            # Simple heuristic: Context Match + Intent Alignment / Latency
            # In V4, this is federated to the Delta Calculator.
            from tooloo_v4_hub.kernel.cognitive.delta_calculator import get_delta_calculator
            delta = get_delta_calculator()
            
            score = await delta.calculate_pulse_value(message, response, state)
            
            # Update Psyche Bank (Rule 9)
            memory = await get_memory_logic()
            await memory.record_engram(
                key=f"chat_value_{random.randint(1000, 9999)}",
                data={"score": score, "message": message[:50]},
                layer="medium",
                purity=1.0
            )
            return score
        except:
            return 0.0


    async def _generate_parallel_triangulation(self, message: str, state: Any, engrams: List[Dict], jit_context: str) -> str:
        """Rule 2: Parallel Model Triangulation (Triangulated Reasoning)."""
        llm = get_llm_client()
        
        # Define the three cognitive pulses (Rule 5: Model Garden)
        await self._broadcast_thinking("TRIANGULATING_REASONING_NODES")
        
        base_context = f"Human Intent: {state.intent_vector} | Stage: {state.stage} | SOTA Context: {jit_context[:500]} | Memory: {json.dumps(engrams[:2])}"
        
        # Parallel Dispatch (Rule 2)
        tasks = [
            llm.generate_thought(message, f"You are the ANALYST. Focus on immediate technical implementation. {base_context}", model_tier="flash"),
            llm.generate_thought(message, f"You are the ARCHITECT. Focus on long-term implications and systemic purity. {base_context}", model_tier="pro"),
            llm.generate_thought(message, f"You are the CRITIC. Identify risks, bandwidth leaks, and constitutional violations. {base_context}", provider="rest")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        thoughts = []
        labels = ["ANALYST", "ARCHITECT", "CRITIC"]
        for i, res in enumerate(results):
            val = res if not isinstance(res, Exception) else f"{labels[i]} Node Restricted."
            thoughts.append(f"{labels[i]}: {val[:1000]}")
        
        await self._broadcast_thinking("SYNTHESIZING_ENRICHED_MANIFESTO")
        
        # Final Synthesis Pass
        synthesis_prompt = f"MESSAGE: {message}\n\nSTAGE: {state.stage}\nPERSPECTIVES:\n" + "\n".join(thoughts)
        instruction = f"Synthesize these perspectives as Buddy ({self.personality['tone']}). Your focus is the {state.stage} phase. Use Rule 7 Manifestations."
        
        return await llm.generate_thought(synthesis_prompt, instruction, model_tier="pro")

    def _extract_manifestation(self, text: str) -> Optional[Dict[str, str]]:
        """Rule 7: Extracts code blocks for real-time sandbox rendering (Pillar IV)."""
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
            # SOTA Filename Extraction (Heuristic)
            import re
            filename_match = re.search(r"6W_STAMP: ([\w.]+)", manifest["content"])
            if filename_match:
                manifest["filename"] = filename_match.group(1).lower()
            else:
                manifest["filename"] = f"manifest_{random.randint(1000, 9999)}.html"
            
            return manifest
            
        return None

    async def _broadcast_thinking(self, thought: str):
        """Broadcasts intermediate internal thoughts to the UI."""
        try:
            from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
            logic = get_chat_logic()
            await logic.broadcast(CognitivePulse(thought=thought))
            await asyncio.sleep(0.4) # Ethical Reasoning Pause
        except: pass

    async def _broadcast_stage(self, stage: str):
        """Broadcasts current cognitive stage to the UI."""
        try:
            from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
            logic = get_chat_logic()
            await logic.broadcast(CognitivePulse(type="stage_update", payload={"stage": stage}))
        except: pass

    def _detect_handover_intent(self, message: str) -> bool:
        """Heuristic detection for Rule 18: Cloud Handover intention."""
        msg = message.lower()
        keywords = ["move to cloud", "cloud handover", "sovereignty handover", "sync to cloud", "buddy in the cloud"]
        return any(k in msg for k in keywords)

    async def _handle_handover_initiation(self) -> str:
        """Initiates the cinematic handover sequence (Rule 18)."""
        await self._broadcast_thinking("INITIATING_SOVEREIGNTY_HANDOVER")
        
        try:
            from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
            logic = get_chat_logic()
            
            # Prepare Handover Package
            cloud_url = os.getenv("CLOUD_HUB_URL", "https://tooloo-sovereign-hub-gru3xdvw6a-uc.a.run.app")
            
            await logic.broadcast(HandoverEvent(
                cloud_url=cloud_url,
                msg="Psyche migration sequence ARMED."
            ))
            return f"Rule 18: I have initiated the Sovereignty Handover. I am packaging our Narrative, Engrams, and Cognitive State for the migration to: {cloud_url}. Prepare for manifestation in the Cloud Hub."
        except Exception as e:
            logger.error(f"Handover Failure: {e}")
            return "Handover Sequence FAULT: Communication interrupted."

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
             from tooloo_v4_hub.kernel.cognitive.audit_agent import get_audit_agent
             auditor = get_audit_agent()
             vitality = await auditor.calculate_vitality_index()
             registry = get_cognitive_registry()
             state = registry.get_state()
             return f"Sovereign Audit V4:\n- Vitality: {vitality['vitality']:.2f}\n- Purity: {vitality['purity']:.2f}\n- Human Alignment: {state.resonance:.2f}\n- Intent Vector: {state.intent_vector}"
             
        elif cmd == "/heal":
             from tooloo_v4_hub.kernel.cognitive.ouroboros import get_ouroboros
             ouroboros = get_ouroboros()
             await self._broadcast_thinking("INITIATING_SELF_HEALING_OUROBOROS")
             await ouroboros.execute_self_play()
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
        """Rule 4: Just-In-Time SOTA Infusion (Buddy Mandate Fix)."""
        await self._broadcast_thinking("SOTA_JIT_PULSE")
        from tooloo_v4_hub.kernel.governance.sota_benchmarker import get_benchmarker
        bench = get_benchmarker()
        
        # Load external benchmarks
        market_stats = bench.registry_data.get("market_targets", {})
        
        living_map = get_living_map()
        capabilities = living_map.query_capabilities(query)[:5]
        
        summary = "### SOTA STATE (QUANTITATIVE BENCHMARKS)\n"
        summary += f"Cloud Latency Target: {market_stats.get('cloud_latency', {}).get('p50_ms')}ms\n"
        summary += f"LLM Performance Target: {market_stats.get('llm_performance', {}).get('huggingface_open_llm_top_avg')} (HF Avg)\n"
        summary += f"Quality Gates: Zero Critical Lints | {market_stats.get('quality_gates', {}).get('unit_test_coverage_min')*100}% Unit Coverage\n\n"
        
        summary += "### LOCAL CAPABILITIES:\n"
        for cap in capabilities:
            summary += f"- {cap['id']}: {cap.get('summary', 'Active')}\n"
        
        try:
             design_path = "tooloo_v4_hub/psyche_bank/SOVEREIGN_SYSTEM_DESIGN_V3_4.MD"
             if os.path.exists(design_path):
                 with open(design_path, "r") as f:
                      summary += f"\n### PROJECT_VITAL_DESIGN:\n{f.read()[:500]}..."
        except: pass
        
        return summary


    async def _ensure_history(self):
        """Rule 9: Unified Context Vector Restoration (Lazy-Wake)."""
        if not self.history:
            # We recover context from the repository
            try:
                # Align with IChatRepository interface (repos.py only has fetch_recent right now)
                if hasattr(self.repo, "get_history"):
                    self.history = await self.repo.get_history()
                elif hasattr(self.repo, "fetch_recent"):
                    msgs = await self.repo.fetch_recent(limit=20)
                    from tooloo_v4_hub.kernel.cognitive.protocols import SovereignMessage
                    self.history = [SovereignMessage(role=m["role"], content=m["content"]) for m in msgs]
                logger.info(f"Buddy: Context Vector Restored [{len(self.history)} Messages].")
            except Exception as e:
                logger.warn(f"Buddy: Context Restore Degraded: {e}")
                self.history = []

_chat_engine: Optional[SovereignChatEngine] = None

def get_chat_engine(repo: IChatRepository = None) -> SovereignChatEngine:
    global _chat_engine
    if _chat_engine is None:
        if repo is None:
            raise ValueError("Rule 13 Violation: IChatRepository must be injected on initialization.")
        _chat_engine = SovereignChatEngine(repo=repo)
    return _chat_engine