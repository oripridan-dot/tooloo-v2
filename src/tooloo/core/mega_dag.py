import asyncio
import logging
import uuid
import time
import json
import os
import inspect
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from src.tooloo.core.llm import get_llm_client
from src.tooloo.tools.sota_sources import build_source_context, infer_domain
# Import lazily in methods below to avoid circular import during module load
# from src.tooloo.core.memory import MemorySystem  # (deferred)

logger = logging.getLogger("Tooloo.ContinuousMegaDAG")

class NodeType(str, Enum):
    OBSERVATION = "OBSERVATION"
    PLANNING = "PLANNING"
    EXECUTION = "EXECUTION"
    TOOLOO = "TOOLOO"
    VERIFICATION = "VERIFICATION"
    REFLECTION = "REFLECTION"
    SOTA_JIT = "SOTA_JIT"
    BUDDY = "BUDDY"
    CHAT = "CHAT"
    UNKNOWN = "UNKNOWN"

class KnowledgeBank:
    """Persistent storage for backward-DAG lessons formulated by reflection."""
    _DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "knowledge_lessons.json")

    def __init__(self, storage_path: str = ""):
        self.storage_path = os.path.abspath(storage_path) if storage_path else os.path.abspath(self._DEFAULT_PATH)
        self.lessons = {}
        self.load()
        
    def load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                self.lessons = json.load(f)
                
    def save(self):
        with open(self.storage_path, "w") as f:
            json.dump(self.lessons, f, indent=2)
            
    def store_lesson(self, concept: str, heuristic: str):
        logger.info(f"[KNOWLEDGE BANK] New Lesson Formulated -> {concept}: {heuristic}")
        self.lessons[concept] = heuristic
        self.save()

class GlobalContext(BaseModel):
    """Shared state for the MegaDAG execution timeline."""
    goal: str
    state: Dict[str, Any] = Field(default_factory=dict)
    iterations: int = 0
    start_time: float = Field(default_factory=time.time)
    dag_instance: Any = Field(default=None)
    narrative: str = Field(default="Initial objective instantiated.")
    mandate: str = Field(default="Maintain Brutal Honesty, 1.00 Purity, and systemic clarity.")
    contextual_story: str = Field(default="The system awakens.")
    # Tier 1+2+3 memory — attached after construction by ContinuousMegaDAG.ignite()
    memory: Any = Field(default=None)
    # Tracks how many QA-triggered auto-healer chains have been spawned this session.
    # Capped at qa_healer_max to prevent sandbox runaway from cascading QA failures.
    qa_healer_depth: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)

class DagNode(BaseModel):
    """A unit of execution within the Continuous Mega DAG."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_type: NodeType = NodeType.UNKNOWN
    goal: str
    action: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    depth: int = 0
    
    # Execution state
    status: str = "PENDING"
    outcome: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

class NodeResult(BaseModel):
    """The result of executing a node, potentially containing new node definitions."""
    outcome: Dict[str, Any]
    spawned_nodes: List[DagNode] = Field(default_factory=list)

class AbstractOperator:
    """Base class for specific domain operations."""
    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        raise NotImplementedError

class ReflectionOperator(AbstractOperator):
    """Parses execution results via LLM, learns heuristics, writes to KnowledgeBank."""
    def __init__(self):
        self.llm = get_llm_client()

    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        bank = KnowledgeBank()
        prompt = f"""
        You are a reflection engine. Analyze the following execution narrative and extract 1-3 concrete lessons.
        Each lesson must be a specific, actionable heuristic — not a generic observation.

        EXECUTION NARRATIVE:
        {context.narrative[-3000:]}

        GOAL THAT WAS PURSUED:
        {context.goal}

        Output lessons only if genuinely warranted by the data. Do not hallucinate lessons.
        """
        schema = {
            "type": "object",
            "properties": {
                "lessons": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "concept": {"type": "string"},
                            "heuristic": {"type": "string"}
                        },
                        "required": ["concept", "heuristic"]
                    }
                }
            }
        }
        try:
            response = await self.llm.generate_structured(
                prompt, schema,
                system_instruction="Extract only actionable lessons grounded in the actual execution data."
            )
            for lesson in response.get("lessons", []):
                # Write through MemorySystem if available, else fall back to direct KnowledgeBank
                if context.memory is not None:
                    context.memory.cold_write(lesson["concept"], lesson["heuristic"])
                else:
                    bank.store_lesson(lesson["concept"], lesson["heuristic"])
        except Exception as e:
            logger.error(f"ReflectionOperator LLM call failed: {e}")

        return NodeResult(outcome={"status": "reflection_complete"})


class QAValidationError(Exception):
    """Raised by QAValidationOperator on FAIL verdict. Triggers the auto-healer sidechain."""


class QAValidationOperator(AbstractOperator):
    """
    QA/Validation pipeline gate — runs at 3 mandatory checkpoints in every DAG execution:
      1. Post-PLANNING: schema compliance check before nodes execute.
      2. Post-tool: output integrity check (exit_code, status, content).
      3. Pre-REFLECTION: constitutional purity check on full narrative.

    Verdict schema: PASS | WARN | FAIL
    - PASS: no action, continues.
    - WARN: logged, continues.
    - FAIL: raises QAValidationError → caught by _process_node sandbox → auto-healer spawned.
             QA-triggered healers are capped by context.qa_healer_depth < qa_healer_max
             to prevent sandbox runaway.

    Grounded in KnowledgeBank lessons (tooloo:Tool Execution Validation,
    tooloo:Parameter Validation, tooloo:Multi-Layer Success Validation, etc.).
    """
    QA_HEALER_MAX = 3  # Max QA-triggered auto-healer chains per DAG session

    def __init__(self, target_model: str = "gemini-flash-latest"):
        self.llm = get_llm_client()
        self.target_model = target_model

    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        bank = KnowledgeBank()

        # Pull relevant QA lessons from KnowledgeBank to ground the validator
        qa_lessons = {
            k: v for k, v in bank.lessons.items()
            if any(kw in k for kw in [
                "Validation", "Verification", "Execution", "Parameter", "Milestone",
                "Persistence", "Continuity", "Identification", "Monitoring"
            ])
        }

        prompt = f"""You are the QA Validation Gate for the TooLoo Sovereign Hub. Rule 0: Brutal Honesty — never mask failures.

VALIDATION TARGET:
{node.goal}

EXECUTION NARRATIVE (last 2000 chars):
{context.narrative[-2000:]}

CURRENT STATE:
{json.dumps(context.state, indent=2)}

RELEVANT QA HEURISTICS (from KnowledgeBank):
{json.dumps(qa_lessons, indent=2)}

Your task:
1. Assess whether the target goal was achieved correctly based on the narrative and state.
2. Check for: missing status fields, non-zero exit codes, empty outputs, schema violations, unchecked assumptions.
3. Apply the KnowledgeBank heuristics — especially Multi-Layer Success Validation (boolean + status string), State Persistence Validation, and Parameter Validation.
4. Output a verdict: PASS, WARN, or FAIL.
   - PASS: all checks satisfied.
   - WARN: minor issues that do not block progress.
   - FAIL: a critical issue that MUST be corrected before proceeding."""

        schema = {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["PASS", "WARN", "FAIL"]},
                "issues": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of specific issues found. Empty if PASS."
                },
                "corrective_action": {
                    "type": "string",
                    "description": "Concrete corrective action if FAIL or WARN. Empty string if PASS."
                }
            },
            "required": ["verdict", "issues", "corrective_action"]
        }

        try:
            response = await self.llm.generate_structured(
                prompt, schema,
                system_instruction="QA Gate: output only grounded verdicts. Rule 0: no hallucination.",
                model=self.target_model
            )
        except Exception as e:
            logger.error(f"[QA] Validator LLM call failed: {e}")
            return NodeResult(outcome={"verdict": "WARN", "issues": [str(e)], "corrective_action": "LLM unavailable — manual review required."})

        verdict = response.get("verdict", "WARN")
        issues = response.get("issues", [])
        corrective_action = response.get("corrective_action", "")

        logger.info(f"[QA] Verdict={verdict} | Issues={issues}")

        # Append QA result to narrative for traceability
        context.narrative = (
            f"{context.narrative}\n[QA:{verdict}] Target='{node.goal[:100]}' "
            f"Issues={issues} Corrective='{corrective_action[:150]}'"
        )

        if verdict == "FAIL":
            # Check sandbox cycle cap BEFORE raising
            if context.qa_healer_depth >= self.QA_HEALER_MAX:
                logger.error(
                    f"[QA] FAIL verdict on '{node.goal[:80]}' — healer cap reached "
                    f"({self.QA_HEALER_MAX}). Suppressing further QA healer chains."
                )
                return NodeResult(outcome={"verdict": "FAIL", "issues": issues, "healer_suppressed": True})

            # Store failure as a new lesson so it persists across sessions
            lesson_key = f"tooloo:QA_FAIL:{node.goal[:60]}"
            lesson_val = f"FAIL: {'; '.join(issues)}. Fix: {corrective_action}"
            if context.memory is not None:
                context.memory.cold_write(lesson_key, lesson_val)
            else:
                bank.store_lesson(lesson_key, lesson_val)

            context.qa_healer_depth += 1
            raise QAValidationError(
                f"QA FAIL [{context.qa_healer_depth}/{self.QA_HEALER_MAX}] — "
                f"{'; '.join(issues)}. Corrective: {corrective_action}"
            )

        if verdict == "WARN" and issues:
            # Store warnings as lessons too — non-blocking
            for issue in issues:
                bank.store_lesson(f"tooloo:QA_WARN:{issue[:60]}", corrective_action)

        return NodeResult(outcome={"verdict": verdict, "issues": issues, "corrective_action": corrective_action})


class SotaJitOperator(AbstractOperator):
    """
    SOTA JIT Enrichment Operator.
    Runs BEFORE planning and execution nodes to:
      1. Inject internal KnowledgeBank lessons relevant to the goal.
      2. Select and inject canonical trusted SOTA web sources for the inferred domain.
      3. Output enriched, schema-validated execution nodes grounded in real data.
    Also used as the auto-healer sidechain on node crashes.
    """
    def __init__(self, target_model: str = "gemini-flash-latest"):
        self.llm = get_llm_client()
        self.target_model = target_model

    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        # Fix: always instantiate KnowledgeBank locally
        bank = KnowledgeBank()

        available_tools = []
        if context.dag_instance:
            for action_name, config in context.dag_instance.tool_configs.items():
                available_tools.append(config.get("schema", {"name": action_name}))

        # Build domain-aware source context (internal lessons + trusted web sources)
        source_context = build_source_context(node.goal, bank.lessons)

        prompt = f"""
You are the SOTA JIT Enrichment Engine for the TooLoo Sovereign Hub.
Your role: analyze the current goal, enrich it with verified knowledge, and produce
precise, schema-validated execution nodes that are directly actionable.

RULE 0: Do NOT hallucinate APIs, parameters, or capabilities.
All actions MUST be selected ONLY from AVAILABLE ACTIONS. All params MUST match the schema exactly.

CURRENT GOAL:
{node.goal}

GLOBAL CONTEXT STATE:
{json.dumps(context.state, indent=2)}

{source_context}

AVAILABLE ACTIONS WITH PARAMETER SCHEMAS:
{json.dumps(available_tools, indent=2)}

Your task:
1. Identify the domain and the most relevant trusted sources listed above.
2. Enrich the goal: clarify ambiguities, fill in concrete parameter values, correct schema mismatches.
3. Output 1-4 highly confident, schema-compliant execution nodes.
4. If a web_search would resolve ambiguity, include it as the FIRST spawned node.
5. Never spawn more than 4 nodes. Quality over quantity.
"""
        schema = {
            "type": "object",
            "properties": {
                "enriched_goal": {
                    "type": "string",
                    "description": "The enriched, disambiguated version of the input goal."
                },
                "domain": {
                    "type": "string",
                    "description": "Inferred domain: ai_research, cloud_infra, software_engineering, security, data_science, or general."
                },
                "nodes": {
                    "type": "array",
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "properties": {
                            "goal": {"type": "string"},
                            "node_type": {"type": "string", "enum": ["OBSERVATION", "EXECUTION", "TOOLOO", "VERIFICATION"]},
                            "action": {"type": "string"},
                            "params": {"type": "object"}
                        },
                        "required": ["goal", "node_type"]
                    }
                }
            },
            "required": ["enriched_goal", "domain", "nodes"]
        }

        try:
            response = await self.llm.generate_structured(
                prompt, schema,
                system_instruction="SOTA JIT Enrichment Engine. Output only grounded, schema-exact execution nodes. Rule 0: no hallucination.",
                model=self.target_model
            )
        except Exception as e:
            logger.error(f"[SOTA_JIT] LLM call failed: {e}")
            return NodeResult(outcome={"status": "jit_failed", "error": str(e)})

        enriched_goal = response.get("enriched_goal", node.goal)
        raw_nodes = response.get("nodes", [])

        # Inject enriched goal back into context narrative
        context.narrative = f"{context.narrative}\n[JIT] Domain={response.get('domain','?')} Enriched: {enriched_goal[:200]}"
        context.state["jit_cycles"] = context.state.get("jit_cycles", 0) + 1

        spawned = []
        for n in raw_nodes:
            try:
                n_type = NodeType(n.get("node_type", "UNKNOWN"))
            except ValueError:
                n_type = NodeType.UNKNOWN
            spawned.append(DagNode(
                node_type=n_type,
                goal=f"[JIT:{response.get('domain','?')}] {n.get('goal', '')}",
                action=n.get("action"),
                params=n.get("params", {})
            ))

        logger.info(f"[SOTA_JIT] Enriched goal. Domain={response.get('domain')}. Spawned {len(spawned)} nodes.")
        return NodeResult(
            outcome={"status": "jit_enriched", "domain": response.get("domain"), "enriched_goal": enriched_goal},
            spawned_nodes=spawned
        )

class PlanningOperator(AbstractOperator):
    """Decomposes goals into new nodes asynchronously based on context."""
    def __init__(self, max_nodes: int = 15, target_model: str = "gemini-flash-latest"):
        self.llm = get_llm_client()
        self.max_nodes = max_nodes
        self.target_model = target_model

    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        bank = KnowledgeBank()
        available_tools = []
        if context.dag_instance:
            for action_name, config in context.dag_instance.tool_configs.items():
                available_tools.append(config.get("schema", {"name": action_name}))
        
        prompt = f"""
        GOAL: {node.goal}
        GLOBAL CONTEXT: {context.state}
        NARRATIVE: {context.narrative}
        PAST RELEVANT LESSONS: {bank.lessons}
        NODE CONTEXT: {node.params}
        AVAILABLE ACTIONS WITH PARAMETER SCHEMAS: {json.dumps(available_tools, indent=2)}

        Perform parallel task formulation. Create up to {self.max_nodes} next actionable steps.
        Use the narrative to understand the overarching story of what has occurred, not just raw state data.
        Each step must have a `node_type` (OBSERVATION, EXECUTION, TOOLOO, VERIFICATION), an `action` function name, and `params`. An `action` MUST be selected ONLY from the AVAILABLE ACTIONS list.
        CRITICAL RULES FOR `params`: You MUST strictly provide ALL exact parameters required mechanically by the specified action's JSON schema! DO NOT provide an empty object if the tool requires parameters! You will crash the entire DAG if you omit required parameters.
        """
        schema = {
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "goal": {"type": "string"},
                            "node_type": {"type": "string", "enum": ["OBSERVATION", "EXECUTION", "TOOLOO", "VERIFICATION"]},
                            "action": {"type": "string"},
                            "params": {"type": "object"}
                        },
                        "required": ["goal", "node_type"]
                    }
                }
            }
        }
        
        response = await self.llm.generate_structured(prompt, schema, system_instruction="You are a parallel task orchestrator.", model=self.target_model)
        raw_nodes = response.get("nodes", [])
        
        spawned = []
        for n in raw_nodes[:self.max_nodes]:
            n_type = NodeType(n.get("node_type", "UNKNOWN"))
            spawned.append(DagNode(
                node_type=n_type,
                goal=n.get("goal", ""),
                action=n.get("action"),
                params=n.get("params", {})
            ))

        # --- GATE 1: Post-planning QA ---
        # Validates that planned nodes are schema-compliant and non-hallucinated
        # before any of them enter the execution queue.
        if spawned:
            spawned.append(DagNode(
                node_type=NodeType.VERIFICATION,
                goal=f"Validate planned nodes are schema-compliant and action names are real registered tools. Plan count: {len(spawned)}. Goal: {node.goal[:120]}"
            ))

        return NodeResult(outcome={"status": "planned", "count": len(spawned)}, spawned_nodes=spawned)


class ToolooOperator(AbstractOperator):
    """
    Placeholder for TooLoo subprocess integration.
    NOT IMPLEMENTED: This operator is a stub. Register a real handler via dag.register_operator(NodeType.TOOLOO, ...)
    before relying on TOOLOO nodes in production.
    """
    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        logger.warning(f"[TOOLOO] ToolooOperator is a stub — node goal will NOT execute: {node.goal}")
        return NodeResult(outcome={"status": "not_implemented", "detail": "ToolooOperator requires a real handler. Register one via dag.register_operator."})

class ContinuousMegaDAG:
    """Orchestrates parallel capabilities dynamically via an event loop and async queue."""
    
    def __init__(self, concurrency_limit: int = 15, max_iterations: int = 5000, max_depth: int = 10, node_timeout_sec: float = 30.0, target_model: str = "gemini-flash-latest"):
        self._concurrency = asyncio.Semaphore(concurrency_limit)
        self.queue = asyncio.Queue()
        self.context: Optional[GlobalContext] = None
        self.max_iterations = max_iterations
        self.max_depth = max_depth
        self.node_timeout_sec = node_timeout_sec
        self.target_model = target_model
        
        # 3-tier memory for TooLoo DAG (namespaced, hot dict is context.state once ignited)
        # Instantiated here with a placeholder hot_store; re-pointed in ignite().
        from src.tooloo.core.memory import MemorySystem
        self.tooloo_memory = MemorySystem(namespace="tooloo")
        
        # Operations mapped by node type.
        # BUDDY is intentionally NOT registered here — it must be registered externally
        # via dag.register_operator(NodeType.BUDDY, BuddyOperator()) to avoid a circular import.
        self.operators: Dict[NodeType, AbstractOperator] = {
            NodeType.PLANNING: PlanningOperator(target_model=self.target_model),
            NodeType.TOOLOO: ToolooOperator(),
            NodeType.REFLECTION: ReflectionOperator(),
            NodeType.SOTA_JIT: SotaJitOperator(target_model=self.target_model),
            # QA gate: VERIFICATION nodes now route to QAValidationOperator.
            # FAIL verdict raises QAValidationError → auto-healer, capped at QA_HEALER_MAX.
            NodeType.VERIFICATION: QAValidationOperator(target_model=self.target_model),
        }
        # Tools mapped by action string and their configurations (schemas)
        self.tool_handlers = {}
        self.tool_configs = {}
        
    def register_tool(self, action_name: str, handler, schema: Optional[Dict[str, Any]] = None):
        self.tool_handlers[action_name] = handler
        self.tool_configs[action_name] = {"handler": handler, "schema": schema or {"name": action_name}}
        
    def register_operator(self, node_type: NodeType, operator: AbstractOperator):
        self.operators[node_type] = operator

    async def ignite(self, goal: str, initial_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Starts the continuous event loop processing the goal."""
        self.context = GlobalContext(goal=goal, state=initial_state or {}, dag_instance=self)
        
        # Re-point Tier 1 hot_store to the live context.state dict so hot_write/read
        # operate on the same dict that operators already read via context.state.
        from src.tooloo.core.memory import MemorySystem
        self.tooloo_memory = MemorySystem(namespace="tooloo", hot_store=self.context.state)
        self.context.memory = self.tooloo_memory
        logger.info(f"[MEMORY:tooloo] Attached to DAG context. T3 lessons: {len(self.tooloo_memory._cold.lessons)}")
        
        # Bootstrap the loop with an initial PLANNING node
        root_node = DagNode(node_type=NodeType.PLANNING, goal=goal)
        await self.queue.put(root_node)
        
        logger.info(f"Igniting Continuous Mega DAG for: {goal}")
        
        active_tasks = set()
        
        while not self.queue.empty() or active_tasks:
            if self.context.iterations >= self.max_iterations:
                logger.warning(f"🚨 Mega DAG reached max iterations ({self.max_iterations}). Halting propagation.")
                break
                
            if self.queue.empty() and active_tasks:
                done, active_tasks = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
                continue

            node = await self.queue.get()
            
            task = asyncio.create_task(self._process_node(node))
            active_tasks.add(task)
            
            active_tasks = {t for t in active_tasks if not t.done()}
            
        latency = time.time() - self.context.start_time
        logger.info(f"DAG Main Queue Complete. Iterations: {self.context.iterations}. Latency: {latency:.2f}s")
        
        # --- GATE 3: Pre-Reflection QA Check ---
        logger.info("[QA GATE 3] Running final constitutional purity check before reflection...")
        final_qa_node = DagNode(
            node_type=NodeType.VERIFICATION,
            goal=f"Final pipeline QA: validate narrative completeness, constitutional purity, and mandate adherence for goal: {goal[:120]}"
        )
        try:
            await self.operators[NodeType.VERIFICATION].execute(final_qa_node, self.context)
        except QAValidationError as e:
            logger.error(f"[QA GATE 3] Final QA FAIL — proceeding to reflection anyway: {e}")

        # --- THE BACKWARDS DAG ---
        # Automatically trigger reflection asynchronous dispatch.
        logger.info("[BACKWARDS DAG] Initiating Post-Execution Iterative Retrospective...")
        reflection_node = DagNode(node_type=NodeType.REFLECTION, goal="Learn from historical execution")
        await self.operators[NodeType.REFLECTION].execute(reflection_node, self.context)
        
        return {
            "status": "SUCCESS",
            "iterations": self.context.iterations,
            "latency_sec": round(latency, 2),
            "final_state": self.context.state
        }

    async def _process_node(self, node: DagNode):
        """Processes a single node in an isolated sandbox, enforcing timeouts and failure boundaries."""
        async with self._concurrency:
            self.context.iterations += 1
            node.status = "EXECUTING"
            logger.debug(f"[{node.node_type}] Executing: {node.goal} (Depth: {node.depth})")
            
            try:
                # Sandbox Execution wrapper
                result = await asyncio.wait_for(self._run_node_logic(node), timeout=self.node_timeout_sec)
                
                node.status = "COMPLETED"
                node.outcome = result.outcome
                
                if result.spawned_nodes:
                    for child in result.spawned_nodes:
                        child.depth = node.depth + 1
                        if child.depth > self.max_depth:
                            logger.warning(f"⚠️ Dropped node due to max_depth hit ({self.max_depth}): {child.goal}")
                            continue

                        logger.debug(f"Spawning ➜ [{child.node_type}] {child.goal}")
                        await self.queue.put(child)
                
            except asyncio.TimeoutError:
                logger.error(f"🛑 Node Sandbox Timeout ({node.id}): exceeded {self.node_timeout_sec}s")
                node.status = "TIMEOUT"
                node.outcome = {"error": "Sandbox Execution Timeout"}
            except Exception as e:
                logger.error(f"💥 Node Sandbox Crash ({node.id}): {e}")
                
                # Auto-Healing Reflex: Sidechain generation
                if node.depth + 1 <= self.max_depth:
                    logger.info(f"🔧 Spawning Reflexive Auto-Healer Sidechain for Node {node.id[:4]}")
                    sidechain_goal = (
                        f"Action '{node.action}' on goal '{node.goal}' crashed with Exception: {type(e).__name__}: {str(e)}. "
                        f"Previous params were: {node.params}. "
                        "Re-evaluate the parameters required for this tool. Patch the schema strictly and spawn a corrected step."
                    )
                    healer_node = DagNode(
                        node_type=NodeType.SOTA_JIT,
                        goal=sidechain_goal,
                        depth=node.depth + 1
                    )
                    await self.queue.put(healer_node)
                else:
                    logger.warning(f"⚠️ Auto-Healer suppressed due to max_depth limit ({self.max_depth})")
                    
                node.status = "FAILED"
                node.outcome = {"error": str(e), "sandbox_contained": True, "sidechain_spawned": node.depth + 1 <= self.max_depth}
                
    async def _run_node_logic(self, node: DagNode) -> NodeResult:
        """Internal un-sandboxed router. Wrapped by _process_node."""
        if node.node_type in self.operators:
            return await self.operators[node.node_type].execute(node, self.context)
        elif node.action:
            handler = self.tool_handlers.get(node.action)
            if handler:
                res = await handler(**node.params) if inspect.iscoroutinefunction(handler) else handler(**node.params)

                # Dynamic Feedback Loop: Inject result back into context narrative
                self.context.narrative = f"{self.context.narrative}\nRan {node.action}: {str(res)[:1000]}"

                spawned = []
                # --- GATE 2: Post-tool QA validation ---
                # Validates exit_code, status, content integrity before any further planning.
                spawned.append(DagNode(
                    node_type=NodeType.VERIFICATION,
                    goal=f"Validate outcome of '{node.action}': check exit_code, status field, and content integrity. Raw result: {str(res)[:400]}",
                    depth=node.depth
                ))

                # After a tool runs (except the final write), gate the next planning step
                # through SOTA_JIT to enrich it with domain knowledge and lessons.
                if node.action != "fs_write_report" and NodeType.SOTA_JIT in self.operators:
                    spawned.append(DagNode(
                        node_type=NodeType.SOTA_JIT,
                        goal=f"Analyze outcome of '{node.action}' and enrich next steps toward main goal: {self.context.goal}",
                        depth=node.depth
                    ))

                # Spawn Buddy weaver periodically (every 5 iterations) to avoid queue flooding.
                if self.context.iterations % 5 == 0 and NodeType.BUDDY in self.operators:
                    spawned.append(DagNode(
                        node_type=NodeType.BUDDY,
                        goal="Synthesize recent execution events into the cohesive contextual story.",
                        depth=node.depth
                    ))

                return NodeResult(outcome=res, spawned_nodes=spawned)
            else:
                return NodeResult(outcome={"status": "mocked", "action": node.action})
        else:
            return NodeResult(outcome={"status": "ignored"})

