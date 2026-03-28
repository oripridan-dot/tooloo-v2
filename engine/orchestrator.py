# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.orchestrator.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

from __future__ import annotations

import logging
import asyncio
import numpy as np
import time
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
from pydantic import BaseModel

from engine.schemas.six_w import SixWProtocol
from engine.graph import CognitiveGraph
from engine.engram import Engram, EmergenceVector, Intent16D
from engine.tribunal import Tribunal, TribunalVerdict, TribunalResult
from engine.evolution_sota import SurrogateWorldModel, MENTAL_DIMENSIONS_16D, COGNITIVE_DIM
from engine.executor import JITExecutor, Envelope, ExecutionResult
from engine.spoke import SpokeOrgan, SpokeArtifact
from engine.model_garden import get_garden
from engine.auto_fixer import AutoFixLoop
from engine.mcp_manager import MCPManager
from engine.memory.sovereign_memory import SovereignMemoryManager

logger = logging.getLogger(__name__)

class SovereignOrchestrator:
    """
    The Sovereign Cognitive Orchestrator for TooLoo V2.
    Orchestrates high-level Goals into Macro-DAGs of Milestones.
    Enforces the (C+I) x E = EM universal law across all execution nodes.
    """

    def __init__(self, memory_manager: Optional[SovereignMemoryManager] = None) -> None:
        self.memory_manager = memory_manager or SovereignMemoryManager()
        self.tribunal = Tribunal()
        self.mcp_manager = MCPManager()
        self.spoke = SpokeOrgan(mcp_manager=self.mcp_manager, tribunal=self.tribunal)
        self.sim_model = SurrogateWorldModel()
        self.reasoning_cache = {}
        # For DAG orchestration, we use the spoke's internal executor
        self.executor = self.spoke.executor 
        self.graph = CognitiveGraph()
        logger.info("SovereignOrchestrator initialized. Macro-DAG mode active.")

    async def execute_goal(self, goal: str, context: Dict[str, Any]) -> List[Engram]:
        """
        The Sovereign Execution Loop:
        1. Macro-Planning: Break Goal into Milestones (Nodes)
        2. DAG Construction: Establish dependencies
        3. Orchestrated Execution: Fan-out Milestones via TaskGroup
        4. Global Audit: Final verification and evolution
        """
        logger.info(f"Initiating Sovereign Execution for Goal: {goal}")
        
        # 0. Hidden Reasoning Wave (O1-Style)
        reasoning = await self._hidden_reasoning_wave(goal, context)
        context["reasoning_scratchpad"] = reasoning
        
        # 1. Macro-Planning
        milestones = await self._plan_milestones(goal, context)
        
        # 2. DAG Construction
        envelopes = []
        dependencies = {}
        prev_node = None
        
        results = []
        
        # 3. Orchestrated Execution
        for i, ms in enumerate(milestones):
            node_id = f"ms-{i}-{ms['id']}"
            engram = await self._synthesize_engram(ms["task"], context, node_id)
            
            # Record in graph for architectural foresight
            self.graph.add_node(node_id, task=ms["task"], engram=engram.dict())
            if prev_node:
                self.graph.add_edge(prev_node, node_id)
            
            env = Envelope(
                mandate_id=node_id,
                intent=engram.intent.json(),
                domain=ms.get("domain", "system"),
                metadata={"engram": engram}
            )
            envelopes.append(env)
            if prev_node:
                dependencies[node_id] = [prev_node]
            prev_node = node_id

        # Execute the Macro-DAG
        exec_results = await self.executor.fan_out_dag(
            self._execute_milestone,
            envelopes,
            dependencies
        )
        
        for res in exec_results:
            if isinstance(res, Engram):
                results.append(res)
            
        logger.info(f"Sovereign Goal finalized: {goal}. Success rate: {sum(1 for r in results if r.em_actual and r.em_actual.val[0] > 0.5)/len(results) if results else 0:.2f}")
        
        # Trigger autonomous retraining if we have enough new evidence
        if len(results) > 0:
            await self.autonomous_retraining()
            
        return results

    async def autonomous_retraining(self, threshold: int = 5) -> float:
        """
        Retrains the internal SurrogateWorldModel using Sovereign Engrams.
        Ensures the engine's predictions converge toward physical emergence.
        """
        logger.info("Initiating Sovereign Self-Correction (Retraining Loop)...")
        
        # 1. Fetch Sovereign Engrams
        # Note: In a production system, we'd query by 'tier' or 'delta'
        records = self.memory_manager._load_learned_engrams()
        if len(records) < threshold:
            logger.info(f"Retraining deferred: insufficient engrams ({len(records)}/{threshold})")
            return 0.0

        # 2. Prepare Training Batch
        inputs = []
        targets = []
        
        for mid, rec in records.items():
            try:
                # Extract data based on different record formats (Legacy vs Sovereign)
                data = rec.get("data", rec)
                
                # We need context and intent for input, and em_actual for target
                # Handle Sovereign format
                if "context" in data and "intent" in data and "em_actual" in data:
                    ctx = SixWProtocol(**data["context"])
                    intent_vals = data["intent"].get("values", {})
                    # Vectorize intent (16D)
                    intent_vec = np.array([intent_vals.get(d, 0.5) for d in MENTAL_DIMENSIONS_16D])
                    
                    inputs.append((ctx, intent_vec))
                    targets.append(np.array(data["em_actual"]["val"]))
                
                # Handle Legacy format (e.g. from SOTABootloader)
                elif "upgrade" in data:
                    upgrade = data["upgrade"]
                    ctx = SixWProtocol(**upgrade["context"])
                    intent_vals = upgrade["intent"]
                    intent_vec = np.array([intent_vals.get(d, 0.5) for d in MENTAL_DIMENSIONS_16D])
                    
                    inputs.append((ctx, intent_vec))
                    targets.append(np.array(upgrade["emergence"]))
                    
            except Exception as e:
                logger.warning(f"Skipping malformed engram {mid} during retraining: {e}")
                continue

        if not inputs:
            logger.warning("No valid training samples found in sovereign memory.")
            return 0.0

        # 3. Train Batch
        loss = self.sim_model.train_batch(inputs, targets)
        logger.info(f"Sovereign Retraining Complete. Convergence Loss: {loss:.6f}")
        
        # 4. Persist Evolution
        model_path = os.path.join(self.memory_manager.repo_path, "psyche_bank", "world_model_v2.json")
        self.sim_model.save_weights(model_path)
        
        return loss

    async def _spoke_work_fn(self, env: Envelope) -> Any:
        """The internal work function executed by the Spoke's JIT Body."""
        # For our tracer bullet, it returns a successful symbolic object
        return {"status": "proven", "payload": env.mandate_id}

    async def _execute_milestone(self, env: Envelope) -> Engram:
        """
        Governing logic for a single Milestone:
        (C+I) x E = EM
        """
        engram: Engram = env.metadata["engram"]
        
        # 0. Hidden Reasoning Wave (Task-Specific)
        # If the task is complex or high-stakes, we perform a deep reasoning wave
        # We use 'Security' as a proxy for 'High-Risk' complexity in the 16D vector
        if engram.intent.values.get("Security", 0.5) > 0.8 or "HIGH-RISK" in env.mandate_id:
            logger.info(f"Inhibiting mandate {env.mandate_id} for Hidden Reasoning Wave...")
            reasoning = await self._hidden_reasoning_wave(env.mandate_id, {"task": engram.context.what})
            engram.metadata["reasoning_scratchpad"] = reasoning

        # 1. Prediction (EM_pred)
        engram.em_pred = EmergenceVector.from_vec(self.sim_model.predict(engram.context, engram.intent.vectorize()))
        
        # 2. Execution (Physical Emergence)
        # Delegate to the Spoke Organ for physical execution
        start = time.time()
        try:
            artifact: SpokeArtifact = await self.spoke.execute_mandate(env, self._spoke_work_fn)
            success = 1.0 if artifact.success else 0.0
            engram.metadata["artifact_identity"] = artifact.identity_hash
            engram.metadata["spoke_signature"] = artifact.signature
        except Exception as e:
            logger.error(f"Milestone execution failure: {e}", exc_info=True)
            success = 0.0
            
        latency = time.time() - start
        
        # 3. Capture Emergence (EM_actual)
        em_vec = np.array([
            success, 
            min(1.0, latency / 10.0), 
            1.0 if success > 0 else 0.0,
            0.9, # Quality (Placeholder)
            0.8, # ROI (Placeholder)
            1.0  # Safety
        ])
        engram.em_actual = EmergenceVector.from_vec(em_vec)
        
        # 4. Audit & Evolve
        audit_result = await self.tribunal.evaluate_async(engram, engram.em_actual)
        
        # 5. Δ-Closure Calculation (The Learning Gap)
        delta = 0.0
        if engram.em_pred:
            delta = float(np.linalg.norm(engram.em_pred.to_vec() - engram.em_actual.to_vec()))
            engram.metadata["delta_closure"] = delta
            logger.info(f"Δ-Closure Gap for {env.mandate_id}: {delta:.4f}")

        await self._evolve(engram, audit_result, delta)
        
        return engram

    async def _plan_milestones(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Breaks a high-level goal into actionable milestones using Tier-3 reasoning."""
        garden = get_garden()
        model_id = garden.get_tier_model(tier=3, intent="MACRO_PLANNING")
        
        prompt = (
            f"Goal: {goal}\n\n"
            "Break this goal into a sequence of actionable milestones.\n"
            "Return ONLY a JSON list of objects: [{\"id\": \"string\", \"task\": \"string\", \"domain\": \"string\"}]"
        )
        
        try:
            resp = garden.call(model_id, prompt)
            import json
            text = resp.strip()
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"Planning failure: {e}")
            return [{"id": "ms-0-primary", "task": goal, "domain": "core"}]

    async def _hidden_reasoning_wave(self, mandate_id: str, context: Dict[str, Any]) -> str:
        """
        Performs a high-latency reasoning cycle (O1-Style) to reconcile intent.
        Uses the Tier-3 model to generate a 'Mental Scratchpad'.
        """
        garden = get_garden()
        # Prefer the local Llama failover if available, otherwise Tier-3 Cloud
        try:
             # Check if Ollama is responsive
             import httpx
             async with httpx.AsyncClient(timeout=2.0) as client:
                 resp = await client.get("http://localhost:11434/api/tags")
                 if resp.status_code == 200:
                     model_id = "ollama/llama3.2:1b" # Use the local reasoning tier
                     logger.info(f"Reasoning Phase: routing to local Sovereign Tier ({model_id})")
                 else:
                     model_id = garden.get_tier_model(tier=3, intent="REASONING")
        except Exception:
             model_id = garden.get_tier_model(tier=3, intent="REASONING")

        prompt = (
            f"Mandate: {mandate_id}\n"
            f"Context: {context}\n\n"
            "Perform a hidden reasoning cycle. Identify potential bottlenecks, "
            "security risks, and 16D intent reconciliation requirements. "
            "Return a terse, actionable reasoning scratchpad."
        )
        
        try:
            # Simulated high-latency reasoning
            await asyncio.sleep(0.5) 
            resp = garden.call(model_id, prompt)
            return resp.strip()
        except Exception as e:
            logger.error(f"Reasoning Wave failure: {e}")
            return "Reasoning session failed. Proceeding with default heuristics."

    async def _synthesize_engram(self, mandate: str, context: Dict[str, Any], node_id: str) -> Engram:
        """Standardized 6W Synthesis for a Milestone."""
        s = SixWProtocol(
            who=context.get("user_id", "principal-architect"),
            what=mandate,
            where=context.get("env", "isolated-spoke"),
            why=context.get("parent_goal", "sovereign-evolution"),
            how="dag-orchestration"
        )
        
        # Intent extraction (The 16 Mental Dimensions)
        garden = get_garden()
        model_id = garden.get_tier_model(tier=3, intent="INTENT_VECTORIZATION")
        
        from engine.engram import MENTAL_DIMENSIONS_16D
        prompt = (
            f"Mandate: {mandate}\n\n"
            "Analyze the intent behind this mandate and assign weights [0.0 to 1.0] for the following 16 Mental Dimensions.\n"
            "Return ONLY a JSON object: {\"dimension_name\": weight}"
        )
        
        try:
            resp = garden.call(model_id, prompt)
            import json
            text = resp.strip()
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            intent_values = json.loads(text)
        except Exception as e:
            intent_values = {dim: 0.8 for dim in MENTAL_DIMENSIONS_16D}
            
        i = Intent16D(values=intent_values)
        return Engram(context=s, intent=i)

    async def _evolve(self, engram: Engram, audit: TribunalResult, delta: float = 0.0):
        """Self-healing Pathway routing and Sovereign Memory persistence."""
        if audit.verdict == TribunalVerdict.ERROR_CORRECTION:
            logger.warning(f"Pathway A: Self-Healing triggered for {engram.context.what}")
            fixer = AutoFixLoop()
            await fixer.analyze_and_fix(engram.context.what)
        
        # Pathway B: Evolutionary Growth
        await self.memory_manager.record_evolution(
            mandate_id=engram.context.what[:30].replace(" ", "-"),
            delta=delta,
            engram_data=engram.dict(),
            stamp=engram.context
        )
        
        if audit.verdict == TribunalVerdict.SUCCESS_WITH_GROWTH or delta > 0.15:
            logger.info(f"Pathway B: Evolutionary data captured for {engram.context.what}")
