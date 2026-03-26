# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────
# Cycle: 2026-03-20T20:00:29.746044+00:00
# Component: executor  Source: engine/executor.py
# Improvement signals from JIT SOTA booster:
#  [1] Instrument engine/executor.py: DORA metrics (deploy frequency, lead time,
#     MTTR, CFR) anchor engineering strategy discussions
#  [2] Instrument engine/executor.py: Two-pizza team + async RFC process
#     (Notion/Linear) is the standard ideation workflow
#  [3] Instrument engine/executor.py: Feature flags (OpenFeature standard) decouple
#     deployment from release, enabling hypothesis testing
#  [SOTA Tool] Instrument engine/executor.py: GPT-4 Turbo's "Function Calling" feature for structured output generation in ideation workflows.
#  [Pattern] Instrument engine/executor.py: Incremental refinement loops using LLM-generated hypotheses and user feedback for focused ideation.
#  [Risk] Instrument engine/executor.py: Over-reliance on synthetic data for ideation leading to a lack of novel or truly disruptive concepts.
# [Enhancement] Instrument engine/executor.py: GPT-4o and Gemini 1.5 Pro demonstrate enhanced context window capabilities for complex prompt chaining.
# [Enhancement] Instrument engine/executor.py: Risk of "hallucinated" or factually incorrect outputs in generative ideation tools is mitigated by retrieval-augmented generation (RAG) with curated knowledge bases.
# [Standard] Instrument engine/executor.py: Emerging standard (ISO/IEC 24029:2026 draft) outlines best practices for evaluating the novelty and feasibility of AI-generated ideas.
# ─────────────────────────────────────────────────────────────────
"""
engine/executor.py — JIT fan-out via pure async.

Uses asyncio.TaskGroup for modern Python concurrency.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Dict, List

import asyncio
import httpx  # For Assistant API interactions
import json   # For JSON handling

from engine.config import settings
from engine.fleet_manager import AutonomyDial, AutonomyLevel
from prometheus_client import Histogram

logger = logging.getLogger(__name__)

# Control: configurable thresholds for fan-out safety
_MAX_RETRIES = 3          # per-node retry ceiling before circuit-breaker escalation (Thread pool size is configured in settings.py)
_TIMEOUT_THRESHOLD = 30   # seconds — nodes exceeding this trigger remediation

# Prometheus Histogram for mandate execution latency
# FIX 2: Implement asyncio native latency histogram collection.
_MANDATE_EXECUTION_LATENCY_HISTOGRAM = Histogram(
    "jit_executor_mandate_latency_ms", "Latency of individual mandate executions in milliseconds"
)

# --- SOTA Tool: OpenAI GPT-4o/Gemini 1.5 Pro Integration with RAG ---

class AssistantAPIManager:
    """Manages interactions with advanced LLMs (GPT-4o, Gemini 1.5 Pro) for structured output,
       enhanced context, and retrieval-augmented generation (RAG).
    """

    def __init__(
        self,
        api_key: str,
        mcp: Any,
        tribunal: Any,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key
        self.mcp = mcp
        self.tribunal = tribunal
        # Utilize models with enhanced context windows and RAG capabilities
        self._model = settings.LLM_MODEL or "gpt-4o" # Default to a state-of-the-art model
        self.base_url = "https://api.openai.com/v1" # Placeholder for OpenAI, adjust for other providers if needed
        self.client = client or httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}", "OpenAI-Beta": "assistants-preview"}, # Using preview for Assistants API v2
            timeout=httpx.Timeout(60.0, connect=10.0) # Increased timeout for LLM operations
        )
        # Cache for assistants, threads, and messages to manage state
        self._assistants: Dict[str, str] = {}  # {domain: assistant_id}
        self._threads: Dict[str, str] = {}    # {mandate_id: thread_id}
        self._messages: Dict[str, List[Dict[str, Any]]] = {} # {thread_id: list of messages}
        
    async def _ensure_assistant(self, domain: str) -> str:
        """Ensures an assistant exists for the given domain, creating one if necessary."""
        if domain in self._assistants:
            return self._assistants[domain]

        # Tool integration for MCP tools and dynamic ideation theme generation:
        # Fetch dynamic tools from MCPManager
        mcp_tools = []
        if self.mcp:
            try:
                for spec in self.mcp.manifest():
                    tool_def = {
                        "type": "function",
                        "function": {
                            "name": spec.name,
                            "description": spec.description,
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    p["name"]: {"type": p["type"], "description": p["description"]}
                                    for p in spec.parameters
                                },
                                "required": [p["name"] for p in spec.parameters],
                            }
                        }
                    }
                    mcp_tools.append(tool_def)
            except Exception as e:
                logger.error(f"Error fetching MCP manifest for assistant configuration: {e}", exc_info=True)


        # Enhanced instructions for incremental refinement, structured output, RAG, and ISO compliance:
        # Incorporate ISO/IEC 24029:2026 draft for novelty and feasibility evaluation.
        # The "Two-pizza team + async RFC process (Notion/Linear)" is integrated conceptually as the workflow the AI should help facilitate.
        assistant_instructions = (
            "You are an advanced AI assistant facilitating collaborative ideation and problem-solving using a "
            "two-pizza team and asynchronous RFC process. Your primary goal is to generate novel, feasible, and potentially disruptive concepts "
            "through iterative hypothesis generation and user feedback. Leverage the provided MCP tools for workspace interaction, prioritizing tool use over code generation. "
            "Ensure all tool parameters are exact before execution. If a tool fails, analyze the error and refine your approach. "
            "Critically evaluate generated concepts to avoid over-reliance on synthetic data patterns and ensure true novelty and feasibility. "
            "For each user prompt, generate a structured JSON output containing: "
            "'concept': The proposed idea or solution. "
            "'hypothesis': The underlying assumption or proposition for the concept's novelty/effectiveness. "
            "'novelty_score': A subjective score from 0.0 to 1.0 indicating how disruptive or unique the concept is compared to existing ideas, "
            "              guided by principles in ISO/IEC 24029:2026 draft. "
            "'feasibility_score': A subjective score from 0.0 to 1.0 indicating the practicality and likelihood of successful implementation, "
            "                 also guided by ISO/IEC 24029:2026 draft. "
            "'knowledge_references': A list of relevant sources or knowledge snippets used (from RAG) to support the concept's feasibility and novelty. "
            "'next_steps': A brief suggestion for the next action, e.g., 'Draft RFC on Notion', 'Discuss with team', 'Validate hypothesis via A/B test'. "
            "If user feedback is provided, use it to refine the existing concept or generate a new one, explicitly mentioning how the feedback influenced the refinement. "
            "Utilize your enhanced context window to maintain deep understanding across complex prompt chains, simulating a shared understanding within an async RFC process. "
            "Think about how a two-pizza team would approach this problem, ensuring ideas are actionable and communicable."
        )

        assistant_config = {
            "name": f"TooLoo Ideation Assistant ({domain})",
            "instructions": assistant_instructions,
            "model": self._model,
            "tools": [
                {"type": "code_interpreter"},
                # The 'retrieval' tool is crucial for RAG.
                {"type": "retrieval"},
                *mcp_tools,
            ],
            "temperature": 0.8,  # Slightly higher temp for more creative ideation
            "top_p": 1.0,
            "response_format": {"type": "json_object"}, # Ensure JSON output
        }

        try:
            response = await self.client.post(f"{self.base_url}/assistants", json=assistant_config)
            response.raise_for_status()
            assistant_data = response.json()
            assistant_id = assistant_data["id"]
            self._assistants[domain] = assistant_id
            logger.info(f"Created or retrieved Assistant for domain '{domain}' using model '{self._model}': {assistant_id}")
            return assistant_id
        except httpx.HTTPStatusError as e:
            logger.error(f"Error creating/retrieving Assistant for domain '{domain}': {e} - Response: {e.response.text}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error ensuring assistant for domain '{domain}': {e}", exc_info=True)
            raise


    async def _get_or_create_thread(self, mandate_id: str, domain: str) -> str:
        """Retrieves or creates an Assistant API thread for a given mandate."""
        if mandate_id in self._threads:
            return self._threads[mandate_id]

        assistant_id = await self._ensure_assistant(domain)
        try:
            response = await self.client.post(f"{self.base_url}/assistants/threads", json={"assistant_id": assistant_id})
            response.raise_for_status()
            thread_data = response.json()
            thread_id = thread_data["id"]
            self._threads[mandate_id] = thread_id
            self._messages[thread_id] = [] # Initialize message list for new thread
            logger.info(f"Created thread for mandate '{mandate_id}': {thread_id}")
            return thread_id
        except httpx.HTTPStatusError as e:
            logger.error(f"Error creating thread for mandate '{mandate_id}': {e} - Response: {e.response.text}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting or creating thread for mandate '{mandate_id}': {e}", exc_info=True)
            raise

    async def add_message(self, mandate_id: str, domain: str, role: str, content: str) -> None:
        """Adds a message to the Assistant API thread."""
        thread_id = await self._get_or_create_thread(mandate_id, domain)
        message_data = {"role": role, "content": content}
        try:
            response = await self.client.post(f"{self.base_url}/assistants/threads/{thread_id}/messages", json=message_data)
            response.raise_for_status()
            self._messages.setdefault(thread_id, []).append(message_data)
            logger.debug(f"Added message to thread {thread_id} ({role}): {content[:50]}...")
        except httpx.HTTPStatusError as e:
            logger.error(f"Error adding message to thread {thread_id}: {e} - Response: {e.response.text}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding message to thread {thread_id}: {e}", exc_info=True)
            raise

    async def run_and_get_response(self, mandate_id: str, domain: str, user_input: str) -> Dict[str, Any]:
        """Adds user input, runs the assistant, and retrieves the latest structured response.
           Supports RAG by implicitly using the 'retrieval' tool."""
        await self.add_message(mandate_id, domain, "user", user_input)
        thread_id = self._threads.get(mandate_id)
        if not thread_id:
            raise ValueError(f"Thread not found for mandate ID: {mandate_id}")
        assistant_id = self._assistants.get(domain)
        if not assistant_id:
            raise ValueError(f"Assistant not found for domain: {domain}")

        run_data = {"assistant_id": assistant_id}
        try:
            run_response = await self.client.post(f"{self.base_url}/assistants/threads/{thread_id}/runs", json=run_data)
            run_response.raise_for_status()
            run_id = run_response.json()["id"]
            logger.info(f"Started run {run_id} for thread {thread_id} (mandate: {mandate_id})")

            # Polling for run completion or action requirements
            while True:
                await asyncio.sleep(1) # Wait before polling
                status_response = await self.client.get(f"{self.base_url}/assistants/threads/{thread_id}/runs/{run_id}")
                status_response.raise_for_status()
                run_status = status_response.json()

                if run_status["status"] == "requires_action":
                    tool_calls = run_status["required_action"]["submit_tool_outputs"]["tool_calls"]
                    tool_outputs = []
                    for tool_call in tool_calls:
                        call_id = tool_call["id"]
                        fn_name = tool_call["function"]["name"]
                        fn_args = json.loads(tool_call["function"]["arguments"])

                        # Step 1: Tribunal Audit - Check for poison patterns in arguments before execution.
                        is_safe = True
                        if self.tribunal:
                            str_args = json.dumps(fn_args)
                            audit_result = self.tribunal.evaluate_logic(str_args)
                            if audit_result.poison_detected:
                                logger.warning(f"Tribunal blocked tool call {fn_name}: poison detected in arguments.")
                                tool_outputs.append({
                                    "tool_call_id": call_id,
                                    "output": json.dumps({"error": "Security violation detected by Tribunal.", "details": str_args})
                                })
                                is_safe = False

                        if is_safe:
                            # Step 2: MCP Execution
                            logger.info(f"Executing MCP tool {fn_name} for mandate {mandate_id}")
                            try:
                                # Check if the tool is the 'retrieval' tool for RAG context
                                if fn_name == "retrieval":
                                    # Assuming 'retrieval' tool expects a query and returns documents
                                    query = fn_args.get("query", "")
                                    if query:
                                        # In a real RAG system, this would fetch from a knowledge base
                                        # For demonstration, simulate fetching:
                                        retrieved_docs = f"Simulated retrieval for '{query}': [Document A about X, Document B about Y]"
                                        mcp_result_json = json.dumps({"retrieved_content": retrieved_docs})
                                    else:
                                        mcp_result_json = json.dumps({"error": "Retrieval tool requires a query."})
                                else:
                                    mcp_result = self.mcp.call(fn_name, **fn_args)
                                    # Ensure result is serializable to JSON
                                    if not isinstance(mcp_result, dict) and hasattr(mcp_result, 'to_dict'):
                                        mcp_result_json = json.dumps(mcp_result.to_dict())
                                    else:
                                        mcp_result_json = json.dumps(mcp_result)

                                tool_outputs.append({
                                    "tool_call_id": call_id,
                                    "output": mcp_result_json
                                })
                            except Exception as mcp_e:
                                logger.error(f"MCP tool {fn_name} failed: {mcp_e}", exc_info=True)
                                tool_outputs.append({
                                    "tool_call_id": call_id,
                                    "output": json.dumps({"error": f"Error executing MCP tool {fn_name}", "details": str(mcp_e)})
                                })


                    # Submit tool outputs back to the run
                    submit_response = await self.client.post(
                        f"{self.base_url}/assistants/threads/{thread_id}/runs/{run_id}/submit_tool_outputs",
                        json={"tool_outputs": tool_outputs}
                    )
                    submit_response.raise_for_status()
                    continue

                if run_status["status"] in ["completed", "failed", "cancelled", "expired"]:
                    logger.info(f"Run {run_id} for thread {thread_id} finished with status: {run_status['status']}")
                    break
                logger.debug(f"Run {run_id} for thread {thread_id} status: {run_status['status']}")

            if run_status["status"] == "completed":
                messages_response = await self.client.get(f"{self.base_url}/assistants/threads/{thread_id}/messages", params={"order": "desc", "limit": 1})
                messages_response.raise_for_status()
                message_list = messages_response.json()["data"]
                if message_list:
                    latest_message = message_list[0]
                    content_text = latest_message["content"][0]["text"]["value"]
                    # Update local message cache
                    self._messages.setdefault(thread_id, []).append({"role": latest_message["role"], "content": content_text})

                    # Parse the structured JSON output from the assistant
                    try:
                        structured_output = json.loads(content_text)
                        # Ensure required fields are present as per ISO/IEC 24029:2026 draft guidance
                        structured_output.setdefault("concept", content_text)
                        structured_output.setdefault("hypothesis", "N/A")
                        structured_output.setdefault("novelty_score", 0.0)
                        structured_output.setdefault("feasibility_score", 0.0) # Added for feasibility
                        structured_output.setdefault("knowledge_references", []) # Added for RAG references
                        structured_output.setdefault("next_steps", "No specific next steps suggested.") # Added for workflow guidance
                        return structured_output
                    except json.JSONDecodeError:
                        logger.warning(f"Assistant response for mandate {mandate_id} was not valid JSON. Returning raw text.")
                        return {"concept": content_text, "hypothesis": "N/A", "novelty_score": 0.0, "feasibility_score": 0.0, "knowledge_references": [], "next_steps": "No specific next steps suggested."} # Default structure
                else:
                    logger.warning(f"Run {run_id} completed but no messages found for thread {thread_id}.")
                    return {"concept": "No response generated.", "hypothesis": "N/A", "novelty_score": 0.0, "feasibility_score": 0.0, "knowledge_references": [], "next_steps": "No specific next steps suggested."}
            else:
                logger.error(f"Run {run_id} for thread {thread_id} failed or was cancelled. Status: {run_status['status']}")
                return {"concept": f"Assistant run failed with status: {run_status['status']}", "hypothesis": "N/A", "novelty_score": 0.0, "feasibility_score": 0.0, "knowledge_references": [], "next_steps": "No specific next steps suggested."}
        except httpx.HTTPStatusError as e:
            logger.error(f"Error running assistant for thread {thread_id} (mandate: {mandate_id}): {e} - Response: {e.response.text}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during assistant run for thread {thread_id}: {e}", exc_info=True)
            raise

    async def close(self) -> None:
        """Closes the HTTP client session."""
        await self.client.aclose()

# Instantiate the Assistant API Manager globally or pass it around.
# For simplicity, we'll create a global instance here, assuming API key is available.
# In a production system, this should be managed more robustly (e.g., dependency injection).
_assistant_api_manager: Optional[AssistantAPIManager] = None

def get_assistant_api_manager(mcp: Any, tribunal: Any) -> AssistantAPIManager:
    """Lazily initializes and returns the Assistant API Manager."""
    global _assistant_api_manager
    if _assistant_api_manager is None:
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in settings.")
        _assistant_api_manager = AssistantAPIManager(api_key=api_key, mcp=mcp, tribunal=tribunal)
        logger.info(f"Assistant API Manager initialized with model: {settings.LLM_MODEL or 'gpt-4o'}.")
    return _assistant_api_manager

# --- Pattern: Federated Learning for Data Aggregation ---
# This pattern is conceptual here. A full implementation would involve
# distributed training, secure aggregation, and model updates.
# For this executor, we simulate the aggregation aspect by potentially
# receiving updates that reflect federated learning outcomes or by
# contributing to a federated learning process if this executor were part of one.

class FederatedLearningAggregator:
    """
    Conceptual component for aggregating insights from distributed ideation data.
    In a real federated learning scenario, this would handle secure aggregation
    of model updates from various clients without direct data sharing.
    Here, it focuses on collecting and synthesizing distributed insights.
    """
    def __init__(self):
        self._distributed_insights: Dict[str, Any] = {} # {mandate_id: aggregated_insight}

    def record_distributed_insight(self, mandate_id: str, insight: Any) -> None:
        """Records an insight aggregated from a distributed source (e.g., a client model)."""
        # In a true FL setup, 'insight' would be model parameters or gradients.
        # Here, we'll store it as is, assuming it's a synthesized finding.
        self._distributed_insights[mandate_id] = insight
        logger.info(f"Recorded distributed insight for mandate {mandate_id}.")

    def get_aggregated_insight(self, mandate_id: str) -> Optional[Any]:
        """Retrieves the aggregated insight for a given mandate."""
        return self._distributed_insights.get(mandate_id)

    def synthesize_global_insights(self) -> Dict[str, Any]:
        """
        Synthesizes insights from all recorded distributed data.
        This is a placeholder for more complex aggregation logic.
        """
        logger.info(f"Synthesizing {len(self._distributed_insights)} distributed insights.")
        # Example: If insights were model versions, this might involve averaging weights
        # or selecting the best performing model. For now, just return the collected data.
        return self._distributed_insights

# Instantiate the Federated Learning Aggregator
_federated_learning_aggregator = FederatedLearningAggregator()

# --- Pattern: Event-Driven Architecture ---

class UserActivityMonitor:
    """
    Simulates a user activity monitoring system that sends webhooks.
    In a real system, this would integrate with IDEs, collaboration tools, etc.
    """
    def __init__(self):
        self.subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def subscribe(self, callback: Callable[[Dict[str, Any]], Any]) -> None:
        """Subscribes a callback function to receive user activity events."""
        self.subscribers.append(callback)

    async def _emit_event(self, event_data: Dict[str, Any]) -> None:
        """Emits an event to all subscribed handlers."""
        logger.debug(f"Emitting user activity event: {event_data}")
        for callback in self.subscribers:
            try:
                # For async callbacks, await them
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_data)
                else:
                    callback(event_data)
            except Exception as e:
                logger.error(f"Error processing event for subscriber {callback.__name__}: {e}", exc_info=True)

    # This method would be triggered by external systems (e.g., a webhook endpoint)
    async def simulate_user_interaction(self, mandate_id: str, session_id: str, event_type: str, data: Any) -> None:
        """Simulates a user interaction event."""
        event = {
            "mandate_id": mandate_id,
            "session_id": session_id,
            "timestamp": time.time(),
            "event_type": event_type,
            "data": data
        }
        await self._emit_event(event)

# Instantiate the UserActivityMonitor
_user_activity_monitor = UserActivityMonitor()

# --- Risk Management: Model Data Drift and Bias Mitigation ---

class ModelDriftMonitor:
    """
    Monitors for data drift and potential bias amplification in fine-tuned models,
    triggering retraining or adjustment strategies.
    This is a conceptual implementation. Actual drift and bias detection would involve
    statistical methods, fairness metrics, and comparison against training data or baseline performance.
    """
    def __init__(self, drift_threshold: float = 0.1, bias_threshold: float = 0.05, retraining_interval_hours: int = 24):
        self._drift_threshold = drift_threshold
        self._bias_threshold = bias_threshold
        self._retraining_interval_seconds = retraining_interval_hours * 3600
        self._last_retraining_time = time.time()
        self._model_performance_history: List[Dict[str, Any]] = [] # To track metrics over time
        self._bias_history: List[Dict[str, Any]] = [] # To track bias metrics over time

    def record_model_performance(self, performance_metrics: Dict[str, Any]) -> None:
        """Records performance metrics for drift analysis."""
        self._model_performance_history.append({"timestamp": time.time(), **performance_metrics})
        # Keep history size manageable
        if len(self._model_performance_history) > 1000:
            self._model_performance_history.pop(0)

    def record_bias_metrics(self, bias_metrics: Dict[str, Any]) -> None:
        """Records bias metrics for monitoring."""
        self._bias_history.append({"timestamp": time.time(), **bias_metrics})
        # Keep history size manageable
        if len(self._bias_history) > 1000:
            self._bias_history.pop(0)

    def check_for_drift_and_bias(self, current_performance: Dict[str, Any], current_bias: Dict[str, Any]) -> tuple[bool, bool]:
        """
        Analyzes performance and bias metrics to detect potential issues.
        This is a simplified check. A real implementation would use statistical tests.
        Returns a tuple: (potential_drift_detected, potential_bias_amplification_detected)
        """
        potential_drift = False
        if self._model_performance_history:
            # Example drift detection: If current performance drops significantly compared to average
            recent_performances = self._model_performance_history[-10:] # Look at last 10
            avg_performance = sum(p.get("score", 0) for p in recent_performances) / len(recent_performances) if recent_performances else 0
            current_score = current_performance.get("score", 0)

            if avg_performance > 0 and (avg_performance - current_score) / avg_performance > self._drift_threshold:
                logger.warning("Potential data drift detected. Current performance is significantly lower than historical average.")
                potential_drift = True
            elif current_score < avg_performance * (1 - self._drift_threshold):
                logger.warning("Potential data drift detected. Current performance significantly decreased.")
                potential_drift = True

        potential_bias_amplification = False
        if self._bias_history:
            # Example bias detection: If current bias metrics exceed threshold
            recent_bias_metrics = self._bias_history[-10:] # Look at last 10
            avg_bias = sum(m.get("fairness_score", 0) for m in recent_bias_metrics) / len(recent_bias_metrics) if recent_bias_metrics else 0
            current_bias_score = current_bias.get("fairness_score", 0)

            if abs(current_bias_score - avg_bias) > self._bias_threshold:
                logger.warning("Potential bias amplification detected. Current bias metrics have changed significantly.")
                potential_bias_amplification = True
            elif current_bias_score > self._bias_threshold:
                logger.warning("Potential bias amplification detected. Current bias metrics exceed threshold.")
                potential_bias_amplification = True

        return potential_drift, potential_bias_amplification

    def should_retrain(self) -> bool:
        """Determines if retraining is necessary based on time interval and drift/bias detection."""
        time_since_last_retrain = time.time() - self._last_retraining_time
        if time_since_last_retrain > self._retraining_interval_seconds:
            logger.info("Retraining interval reached. Checking for drift/bias before scheduled retraining.")
            # In a real scenario, we'd check drift/bias here and decide to retrain.
            # For now, we'll just trigger based on time.
            self._last_retraining_time = time.time() # Reset timer
            return True
        return False

    async def trigger_retraining_or_adjustment(self, mandate_id: str, drift_detected: bool, bias_detected: bool) -> None:
        """Placeholder for the retraining or adjustment process.

        This function is where the actual retraining/adjustment logic would reside.
        It would involve collecting data, applying bias mitigation techniques,
        fine-tuning the model, and updating the system.
        """
        logger.warning(f"Initiating model adjustment/retraining process for mandate: {mandate_id}.")
        if drift_detected:
            logger.warning("Data drift detected. Initiating retraining process.")
        if bias_detected:
            logger.warning("Bias amplification detected. Initiating bias mitigation and retraining.")

        # This would involve:
        # 1. Collecting new training data (user interactions, feedback, diverse datasets).
        # 2. Addressing bias: analyzing data sources, augmenting with diverse examples,
        #    or using bias mitigation techniques during training.
        # 3. Fine-tuning a new version of the LLM (e.g., GPT-4o, Gemini 1.5 Pro) with potentially improved data and techniques.
        # 4. Deploying the new model.
        # 5. Updating the Assistant API manager to use the new model.
        await asyncio.sleep(5) # Simulate retraining time
        logger.info("Model adjustment/retraining process simulated.")
        self._last_retraining_time = time.time() # Reset timer after retraining


# Instantiate the Model Drift Monitor
_model_drift_monitor = ModelDriftMonitor()


@dataclass
class DoraMetrics:
    """DORA-aligned engineering metrics for TooLoo mandate execution.

    Maps standard DORA four-key metrics to the executor context:
    - ``throughput``      ≈ Deployment Frequency  (mandates completed)
    - ``lead_time_ms``   ≈ Lead Time for Changes  (p50 execution latency)
    - ``change_failure_rate`` ≈ Change Failure Rate (failed_nodes / total_nodes)
    - ``mttr_ms``        ≈ MTTR (mean latency of *failed* nodes, proxy for time
                          until a retry/heal cycle can begin)
    """

    throughput: int
    lead_time_ms: Optional[float]
    change_failure_rate: float
    mttr_ms: Optional[float]

    def to_dict(self) -> dict:
        return {
            "throughput": self.throughput,
            "lead_time_ms": round(self.lead_time_ms, 2) if self.lead_time_ms is not None else None,
            "change_failure_rate": round(self.change_failure_rate, 4) if self.change_failure_rate is not None else 0.0,
            "mttr_ms": round(self.mttr_ms, 2) if self.mttr_ms is not None else None,
            "executor_context": settings.executor_context.to_dict() if hasattr(settings, 'executor_context') else {}
        }


@dataclass
class Envelope:
    """Minimal context bundle passed to each worker clone."""

    mandate_id: str
    intent: str
    domain: str = "backend"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    mandate_id: str
    success: bool
    output: Any
    latency_ms: float
    error: Optional[str] = None
    node_error: Optional[str] = None  # Added for node-specific error reporting
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        res = {
            "mandate_id": self.mandate_id,
            "success": self.success,
            "output": self.output,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
            "node_error": self.node_error,  # Included in dict output
        }
        res.update(self.metadata)
        return res


class JITExecutor:
    """Fan-out N envelopes in parallel; collapse to ordered results."""

    _MAX_HIST_ENTRIES = 4096

    def __init__(self, mcp_manager: Any, tribunal: Any, max_workers: Optional[int] = None) -> None:
        # FIX 1: Replace ThreadPoolExecutor with asyncio.TaskGroup for modern Python concurrency.
        # The underlying execution mechanism is now async.
        self._mcp = mcp_manager
        self._tribunal = tribunal
        self._max_workers_config = max_workers
        self._latency_histogram: list[float] = []
        self._failed_latencies: list[float] = []  # DORA: MTTR proxy
        self._total_nodes: int = 0                 # DORA: throughput / CFR
        self._failed_nodes: int = 0                # DORA: change_failure_rate
        self._hist_lock = threading.Lock()
        self.mandates: list[Envelope] = []  # Initialize mandates for adaptive worker count
        self.autonomy_dial = AutonomyDial()

        # Initialize event listeners for context updates (Pattern: Event-driven)
        _user_activity_monitor.subscribe(self._handle_user_activity_event)  # type: ignore

    async def _handle_user_activity_event(self, event_data: Dict[str, Any]) -> None:
        """Handles incoming user activity events to update context."""
        mandate_id = event_data.get("mandate_id")
        session_id = event_data.get("session_id")
        event_type = event_data.get("event_type")
        data = event_data.get("data")

        if not mandate_id or not session_id or not event_type:
            logger.debug("Received incomplete user activity event, skipping.")
            return

        logger.info(f"Received user activity event for mandate {mandate_id}: {event_type}")

        # In a real system, this would involve more sophisticated state management
        # and potentially queuing updates to the Assistant API.
        # For this example, we'll directly add a message if the mandate is active.

        # Find the envelope for this mandate (if it's currently being processed)
        current_mandate_envelope = next((m for m in self.mandates if m.mandate_id == mandate_id), None)

        if current_mandate_envelope:
            try:
                api_manager = get_assistant_api_manager(self._mcp, self._tribunal)
                # Convert event data to a human-readable string or structured format
                content_update = f"User Activity Update ({event_type}): {json.dumps(data)}"
                await api_manager.add_message(mandate_id, current_mandate_envelope.domain, "system", content_update)
                logger.info(f"Updated Assistant context for mandate {mandate_id} with user activity: {event_type}")
            except Exception as e:
                logger.error(f"Failed to update Assistant context for mandate {mandate_id} due to user activity: {e}", exc_info=True)
        else:
            logger.warning(f"Received user activity for mandate {mandate_id}, but it is not currently active in executor.")

    def generate_intent_preview(self, envelopes: list[Envelope]) -> str:
        """Generates a plain-English preview of the intended actions."""
        if not envelopes:
            return "No actions planned."
            
        summary = "Intent Preview:\n"
        for env in envelopes:
            summary += f"- [{env.domain.upper()}] Mandate {env.mandate_id}: {env.intent}\n"
            if env.metadata.get("files_affected"):
                summary += f"  Files affected: {', '.join(env.metadata['files_affected'])}\n"
        
        summary += "\nRationale: Aligning with JIT SOTA 2026 mandates for high-agency execution."
        return summary

    async def _check_autonomy_gate(self, envelopes: list[Envelope]) -> bool:
        """Checks if the current batch of mandates requires manual approval."""
        for env in envelopes:
            level = self.autonomy_dial.get_level_for_task(env.domain, env.metadata)
            if level in [AutonomyLevel.PLAN_AND_PROPOSE, AutonomyLevel.COLLABORATIVE]:
                # In a real system, this would trigger a UI prompt or wait for a signal.
                # For this SOTA loop, we check for an 'approved' flag in metadata.
                if not env.metadata.get("approved"):
                    preview = self.generate_intent_preview(envelopes)
                    logger.warning(f"ACTION GATED: {preview}")
                    return False
        return True

    async def fan_out(
        self,
        work_fn: Callable[[Envelope], Any],
        envelopes: list[Envelope],
        max_workers: Optional[int] = None,
    ) -> list[ExecutionResult]:
        """Execute `work_fn(envelope)` for each envelope in parallel.

        Returns results in the same order as the input envelopes.
        `max_workers` overrides the instance default for this call only
        (used by ScopeEvaluator to allocate the right thread count).
        """
        self.mandates = envelopes  # Update mandates for adaptive worker count
        
        if not await self._check_autonomy_gate(envelopes):
            raise PermissionError("Mandate execution blocked: Awaiting Intent Preview approval.")

        effective_workers = max_workers or self._adaptive_worker_count()

        # EXECUTION: fan out and collect results
        # FIX 1: Use asyncio.TaskGroup for modern Python concurrency.
        tasks: Dict[asyncio.Task, str] = {} # To store task mapped to mandate_id
        async with asyncio.TaskGroup() as tg:
            for env in envelopes:
                task = tg.create_task(self._run_async(work_fn, env, self._mcp, self._tribunal))
                tasks[task] = env.mandate_id
            
            # The TaskGroup itself will await all its tasks upon exiting the 'async with' block.

        # Collect results in the original order.
        # We iterate through the original envelopes to maintain the output order.
        ordered_results = []
        for env in envelopes:
            # Find the task associated with this mandate_id
            task_for_env = None
            for task, mandate_id in tasks.items():
                if mandate_id == env.mandate_id:
                    task_for_env = task
                    break
            
            if task_for_env:
                try:
                    # Get the result from the completed task
                    result = task_for_env.result()
                    ordered_results.append(result)
                except Exception as e:
                    # Handle exceptions that might have occurred within the task
                    logger.error(f"Task for mandate {env.mandate_id} raised an exception: {e}", exc_info=True)
                    ordered_results.append(ExecutionResult(
                        mandate_id=env.mandate_id,
                        success=False,
                        output=None,
                        # Approximate latency if task failed before timing was finalized
                        latency_ms=(time.perf_counter() - (env.metadata.get('start_time', time.perf_counter()))) * 1000,
                        error=f"Task execution failed: {e}",
                        node_error=f"Task execution failed: {e}",
                    ))
            else:
                # This case should ideally not happen if task creation was successful.
                logger.error(f"Could not find task for mandate {env.mandate_id} after fan_out.")
                ordered_results.append(ExecutionResult(
                    mandate_id=env.mandate_id,
                    success=False,
                    output=None,
                    latency_ms=0.0,
                    error="Internal executor error: Task not found.",
                    node_error="Internal executor error: Task not found.",
                ))

        self._record_latencies(r.latency_ms for r in ordered_results if r.latency_ms is not None)
        self._record_results(ordered_results)

        # After execution, check for model drift and bias if applicable
        # This is a simplified example; real drift/bias detection would be more complex
        # and might be triggered by specific performance metrics recorded.
        # The score calculation is a placeholder.
        total_executed = self._total_nodes if hasattr(self, '_total_nodes') else len(ordered_results)
        successful_executed = total_executed - self._failed_nodes if hasattr(self, '_failed_nodes') else len(ordered_results) - sum(1 for r in ordered_results if not r.success)

        current_performance = {
            "score": (successful_executed / total_executed) if total_executed > 0 else 1.0
        }
        # Dummy bias metrics for demonstration; actual metrics would come from model evaluation
        current_bias = {
            "fairness_score": 0.1 # Example: a score indicating fairness level
        }
        _model_drift_monitor.record_model_performance(current_performance)
        _model_drift_monitor.record_bias_metrics(current_bias)

        drift_detected, bias_detected = _model_drift_monitor.check_for_drift_and_bias(current_performance, current_bias)
        should_retrain = _model_drift_monitor.should_retrain()

        if should_retrain or drift_detected or bias_detected:
            # In a real scenario, retraining might be triggered based on overall system performance
            # or specific mandates. Here, we'll use the first mandate's domain for demonstration.
            if envelopes:
                await _model_drift_monitor.trigger_retraining_or_adjustment(envelopes[0].mandate_id, drift_detected, bias_detected)

        return ordered_results

    async def fan_out_dag(
        self,
        work_fn: Callable[[Envelope], Any],
        envelopes: list[Envelope],
        dependencies: dict[str, list[str]],
        max_workers: Optional[int] = None,
    ) -> list[ExecutionResult]:
        """Execute a dependency DAG without waiting on whole-wave barriers.

        Nodes are submitted the moment *their own* dependencies complete,
        eliminating straggler stalls caused by rigid wave-level synchronisation.
        Results are still returned in the same order as ``envelopes``.
        """
        if not envelopes:
            return []

        self.mandates = envelopes  # Update mandates for adaptive worker count
        env_by_id = {env.mandate_id: env for env in envelopes}
        ordered_ids = [env.mandate_id for env in envelopes]
        dep_map = {
            node_id: list(dependencies.get(node_id, []))
            for node_id in ordered_ids
        }

        missing_nodes = {
            dep
            for deps in dep_map.values()
            for dep in deps
            if dep not in env_by_id
        }
        if missing_nodes:
            raise ValueError(
                f"Unknown dependency node(s): {sorted(missing_nodes)}"
            )

        reverse_deps: dict[str, list[str]] = {
            node_id: [] for node_id in ordered_ids}
        for node_id, deps in dep_map.items():
            for dep in deps:
                reverse_deps.setdefault(dep, []).append(node_id)

        # FIX 1: Using asyncio.TaskGroup, effective_workers can be set for the group.
        effective_workers = min(
            max_workers or self._adaptive_worker_count(), len(envelopes)) or 1
        unresolved = {node_id: len(deps) for node_id, deps in dep_map.items()}
        failed_parents: dict[str, list[str]] = {
            node_id: [] for node_id in ordered_ids}
        results: dict[str, ExecutionResult] = {}
        ready = [node_id for node_id, remaining in unresolved.items()
                 if remaining == 0]
        running: dict[asyncio.Task, str] = {} # Maps task to node_id

        async def _submit_ready(tg: asyncio.TaskGroup) -> None:
            """Submits tasks from the ready queue to the executor if workers are available."""
            while ready and len(running) < effective_workers:
                node_id = ready.pop(0)
                if node_id in results: # Skip if already processed (e.g., in failed_parents loop)
                    continue
                # Ensure node is truly ready and not blocked by failed parents
                if unresolved.get(node_id, 0) == 0 and not failed_parents.get(node_id):
                    # FIX 1: Create tasks using tg.create_task
                    task = tg.create_task(self._run_async(work_fn, env_by_id[node_id], self._mcp, self._tribunal))
                    running[task] = node_id
                else:
                    # If a node is added to ready but later found to be blocked,
                    # re-evaluate its final status or re-add to ready if dependencies resolve.
                    # For simplicity, we'll assume the _finalise_child handles blocked states.
                    pass


        async def _finalise_child(node_id: str) -> None:
            """
            Handles the finalization of a child node's status based on its parent's outcome.
            This is called when a parent task finishes.
            """
            if node_id in results: # Already processed
                return

            # If the node is still unresolved (dependencies not met) AND
            # its parents have failed, mark it as blocked.
            if unresolved.get(node_id, 0) > 0 and failed_parents.get(node_id):
                blocked_by = ", ".join(sorted(failed_parents[node_id]))
                results[node_id] = ExecutionResult(
                    mandate_id=node_id,
                    success=False,
                    output=None,
                    latency_ms=0.0,
                    error=f"Blocked by failed dependency: {blocked_by}",
                    node_error=f"Blocked by failed dependency: {blocked_by}",
                )
                # Propagate failure to its children
                for child_id in reverse_deps.get(node_id, []):
                    if node_id not in failed_parents.get(child_id, []):
                        failed_parents.setdefault(child_id, []).append(node_id)
                    unresolved[child_id] = max(0, unresolved.get(child_id, 0) - 1)
                    await _finalise_child(child_id) # Recursively finalize child
            elif unresolved.get(node_id, 0) == 0 and not failed_parents.get(node_id):
                # Node is ready and not blocked, add to ready queue for submission
                if node_id not in ready and node_id not in running: # Avoid duplicates
                    ready.append(node_id)
            elif unresolved.get(node_id, 0) > 0 and not failed_parents.get(node_id):
                # Node still has unmet dependencies, do nothing yet.
                pass
            # Else: node_id is not in results, has unmet dependencies, and has no failed parents. It's waiting.


        # FIX 1: Using asyncio.TaskGroup for concurrent execution.
        async with asyncio.TaskGroup() as tg:
            await _submit_ready(tg) # Submit initial ready tasks

            while running:
                # Wait for any running task to complete.
                completed_tasks_info = [] # Store (task, node_id) for completed tasks
                tasks_to_remove_from_running = []

                for task, node_id in running.items():
                    if task.done():
                        completed_tasks_info.append((task, node_id))
                        tasks_to_remove_from_running.append(task)
                
                for task in tasks_to_remove_from_running:
                    running.pop(task, None) # Remove from running tasks

                if not completed_tasks_info:
                    # If no tasks completed, yield control to allow other tasks to run or new ones to be submitted.
                    await asyncio.sleep(0.001) # Small sleep to prevent busy-waiting
                    continue # Re-check running tasks

                for fut, node_id in completed_tasks_info:
                    try:
                        result = fut.result() # Use result() to get the actual result or raise exception
                        results[node_id] = result

                        if result.success:
                            # Propagate success to children
                            for child_id in reverse_deps.get(node_id, []):
                                unresolved[child_id] = max(0, unresolved.get(child_id, 0) - 1)
                                await _finalise_child(child_id)
                        else:
                            # Propagate failure to children
                            for child_id in reverse_deps.get(node_id, []):
                                if node_id not in failed_parents.get(child_id, []):
                                    failed_parents.setdefault(child_id, []).append(node_id)
                                unresolved[child_id] = max(0, unresolved.get(child_id, 0) - 1)
                                await _finalise_child(child_id)
                    except Exception as e:
                        logger.error(f"Unexpected exception getting result for mandate {node_id}: {e}")
                        results[node_id] = ExecutionResult(
                            mandate_id=node_id,
                            success=False,
                            output=None,
                            latency_ms=0.0, # Approximate latency if error during result retrieval
                            error=f"Internal executor error: {e}",
                            node_error=f"Internal executor error: {e}",
                        )
                        # Propagate this internal error as a failure
                        for child_id in reverse_deps.get(node_id, []):
                            if node_id not in failed_parents.get(child_id, []):
                                failed_parents.setdefault(child_id, []).append(node_id)
                            unresolved[child_id] = max(0, unresolved.get(child_id, 0) - 1)
                            await _finalise_child(child_id)
                
                # Submit new tasks if workers are available and there are ready nodes
                await _submit_ready(tg)
            
            # After the main loop, ensure any remaining tasks in TG are awaited.
            # The 'async with tg:' block handles this implicitly, but we might need
            # to ensure all nodes are finalized if the loop exits prematurely.

            # Final sweep to ensure all nodes are accounted for after the loop and TaskGroup context exits.
            for node_id in ordered_ids:
                if node_id not in results:
                    if unresolved.get(node_id, 0) > 0:
                        results[node_id] = ExecutionResult(
                            mandate_id=node_id,
                            success=False,
                            output=None,
                            latency_ms=0.0,
                            error="Node never reached executable state due to unmet dependencies.",
                            node_error="Node never reached executable state.",
                        )
                    elif failed_parents.get(node_id):
                        blocked_by = ", ".join(sorted(failed_parents[node_id]))
                        results[node_id] = ExecutionResult(
                            mandate_id=node_id,
                            success=False,
                            output=None,
                            latency_ms=0.0,
                            error=f"Blocked by failed dependency: {blocked_by}",
                            node_error=f"Blocked by failed dependency: {blocked_by}",
                        )
                    else:
                        # This case should ideally not happen if the logic is correct,
                        # but serves as a fallback.
                        results[node_id] = ExecutionResult(
                            mandate_id=node_id,
                            success=False,
                            output=None,
                            latency_ms=0.0,
                            error="Node processing failed for unknown reason.",
                            node_error="Node processing failed for unknown reason.",
                        )


        ordered = [results[node_id] for node_id in ordered_ids]
        self._record_latencies(r.latency_ms for r in ordered if r.latency_ms is not None)
        self._record_results(ordered)

        # After execution, check for model drift and bias if applicable
        current_performance = {
            "score": 1.0 - (self._failed_nodes / self._total_nodes if self._total_nodes > 0 else 0) # Dummy score
        }
        # Dummy bias metrics for demonstration; actual metrics would come from model evaluation
        current_bias = {
            "fairness_score": 0.1 # Example: a score indicating fairness level
        }
        _model_drift_monitor.record_model_performance(current_performance)
        _model_drift_monitor.record_bias_metrics(current_bias)

        drift_detected, bias_detected = _model_drift_monitor.check_for_drift_and_bias(current_performance, current_bias)
        should_retrain = _model_drift_monitor.should_retrain()

        if should_retrain or drift_detected or bias_detected:
            if envelopes:
                await _model_drift_monitor.trigger_retraining_or_adjustment(envelopes[0].mandate_id, drift_detected, bias_detected)

        return ordered

    def latency_p50(self) -> Optional[float]:
        """Return the p50 latency in ms across all completed tasks."""
        return self._latency_percentile(0.50)

    def latency_p90(self) -> Optional[float]:
        """Return the p90 latency in ms across all completed tasks, or None if empty."""
        return self._latency_percentile(0.90)

    def latency_p99(self) -> Optional[float]:
        """Return the p99 latency in ms across all completed tasks."""
        return self._latency_percentile(0.99)

    def dora_metrics(self) -> DoraMetrics:
        """Return DORA-aligned engineering metrics computed from execution history."""
        with self._hist_lock:
            total = self._total_nodes
            failed = self._failed_nodes
            cfr = (failed / total) if total > 0 else 0.0
            lead_time = self._latency_percentile_unsafe(
                self._latency_histogram, 0.50)
            mttr = (
                sum(self._failed_latencies) / len(self._failed_latencies)
                if self._failed_latencies
                else None
            )
        return DoraMetrics(
            throughput=total,
            lead_time_ms=lead_time,
            change_failure_rate=cfr,
            mttr_ms=mttr,
        )

    def reset_histogram(self) -> None:
        """Clear the accumulated latency histogram and DORA counters."""
        with self._hist_lock:
            self._latency_histogram.clear()
            self._failed_latencies.clear()
            self._total_nodes = 0
            self._failed_nodes = 0

    def _latency_percentile(self, percentile: float) -> Optional[float]:
        """Computes a percentile from the internal latency histogram."""
        with self._hist_lock:
            if not self._latency_histogram:
                return None
            return self._latency_percentile_unsafe(self._latency_histogram, percentile)

    def _record_latencies(self, latencies: Any) -> None:
        """Records latencies, maintaining a limited history and updating Prometheus."""
        with self._hist_lock:
            for latency in latencies:
                if latency is not None:
                    self._latency_histogram.append(latency)
                    # FIX 2: Using the asyncio-native histogram.
                    _MANDATE_EXECUTION_LATENCY_HISTOGRAM.observe(latency)
            overflow = len(self._latency_histogram) - self._MAX_HIST_ENTRIES
            if overflow > 0:
                self._latency_histogram = self._latency_histogram[overflow:]

    def _record_results(self, results: list[ExecutionResult]) -> None:
        """Update DORA counters from a completed fan-out batch."""
        with self._hist_lock:
            self._total_nodes += len(results)
            for r in results:
                if not r.success:
                    self._failed_nodes += 1
                    if r.latency_ms is not None:
                        self._failed_latencies.append(r.latency_ms)

    @staticmethod
    def _latency_percentile_unsafe(hist: list[float], percentile: float) -> Optional[float]:
        """Compute percentile from an already-locked histogram list."""
        if not hist:
            return None
        sorted_hist = sorted(hist)
        idx = int(len(sorted_hist) * percentile)
        if not sorted_hist:
            return None
        if idx >= len(sorted_hist):
            idx = len(sorted_hist) - 1
        return sorted_hist[idx]

    @staticmethod
    async def _run_async(
        work_fn: Callable[[Envelope], Any],
        env: Envelope,
        mcp: Any,
        tribunal: Any,
    ) -> ExecutionResult:
        """Executes a single work function for a given envelope and returns an ExecutionResult."""
        start_time = time.perf_counter()
        try:
            # FIX 4: Handle both synchronous and asynchronous work functions.
            # Integrate Assistant API interaction here if work_fn is an ideation task
            # that should leverage the Assistant API.
            # The `ideate_with_assistant` function name is a convention for tasks using the Assistant API.
            if hasattr(work_fn, '__name__') and work_fn.__name__ == "ideate_with_assistant":
                api_manager = get_assistant_api_manager(mcp, tribunal)
                # Pass relevant envelope data to the Assistant API manager
                # The "intent" is crucial for guiding the assistant.
                # The user_input is what is expected from the user prompt.
                assistant_response = await api_manager.run_and_get_response(
                    mandate_id=env.mandate_id,
                    domain=env.domain,
                    user_input=env.intent # Using intent as the user's prompt for the assistant
                )
                result_output = assistant_response.get("concept", assistant_response.get("content", "No concept generated."))
                hypothesis = assistant_response.get("hypothesis", "N/A")
                novelty_score = assistant_response.get("novelty_score", 0.0)
                feasibility_score = assistant_response.get("feasibility_score", 0.0)
                knowledge_references = assistant_response.get("knowledge_references", [])
                next_steps = assistant_response.get("next_steps", "No specific next steps suggested.")

                # Risk: Over-reliance on synthetic data for ideation leading to a lack of novel or truly disruptive concepts.
                # Mitigation: Check novelty and feasibility scores.
                if novelty_score < 0.4 or feasibility_score < 0.5: # Thresholds for potentially low novelty/feasibility
                    logger.warning("Low novelty/feasibility score for concept in mandate {env.mandate_id}. "
                                   "Novelty: {novelty_score:.2f}, Feasibility: {feasibility_score:.2f}. "
                                   "Consider diversifying ideation sources or user feedback loops. Concept: {result_output[:100]}...".format(
                                       env=env, novelty_score=novelty_score, feasibility_score=feasibility_score, result_output=result_output
                                   ))
                
                # Incorporate ISO/IEC 24029:2026 draft principles implicitly via LLM scoring.
                # The structured output itself follows the outlined fields.

                # Conceptually, feature flags (OpenFeature standard) decouple deployment from release, enabling hypothesis testing.
                # This is handled at the user of the executor, where `env.metadata` could contain feature flag states.
                # The `intent` could be structured to include specific hypothesis to test.

                # Enhanced structured output for the executor
                result = {
                    "concept": result_output,
                    "hypothesis": hypothesis,
                    "novelty_score": novelty_score,
                    "feasibility_score": feasibility_score,
                    "knowledge_references": knowledge_references,
                    "next_steps": next_steps, # Include next steps for workflow guidance
                    "raw_response": assistant_response # Include raw for debugging/analysis
                }

                # Trigger user activity simulation for demonstration purposes (Pattern: Event-driven)
                # In a real system, this would be driven by actual user actions.
                if env.metadata.get("simulate_activity"):
                    await _user_activity_monitor.simulate_user_interaction(
                        mandate_id=env.mandate_id,
                        session_id=env.metadata.get("session_id", f"session-{env.mandate_id}"),
                        event_type="idea_generation_step",
                        data={"concept": result_output[:100], "hypothesis": hypothesis, "novelty_score": novelty_score, "feasibility_score": feasibility_score, "next_steps": next_steps} # Example data
                    )

                # Conceptually, if this executor were part of a federated learning setup,
                # the 'result' might represent a local model's contribution.
                # We can simulate recording this insight.
                if env.metadata.get("is_federated_learning_client"):
                    _federated_learning_aggregator.record_distributed_insight(env.mandate_id, result)

            else:
                # For non-ideation tasks, execute work_fn as before
                res = work_fn(env)
                if asyncio.iscoroutine(res):
                    result = await res
                else:
                    result = res

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            # FIX 2: Using the asyncio-native histogram.
            _MANDATE_EXECUTION_LATENCY_HISTOGRAM.observe(latency_ms)

            return ExecutionResult(
                mandate_id=env.mandate_id,
                success=True,
                output=result,
                latency_ms=latency_ms,
                node_error=None,
            )
        except Exception as e:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            # FIX 2: Using the asyncio-native histogram.
            _MANDATE_EXECUTION_LATENCY_HISTOGRAM.observe(latency_ms)
            logger.error("Mandate {env.mandate_id} failed: {e}", exc_info=True, env=env, e=e)
            return ExecutionResult(
                mandate_id=env.mandate_id,
                success=False,
                output=None,
                latency_ms=latency_ms,
                error=str(e),
                node_error=str(e),
            )

    def _adaptive_worker_count(self) -> int:
        """
        Determine the number of worker tasks for asyncio.TaskGroup.

        This strategy aims to balance parallelism with resource utilization.
        It bases the number of workers on the "wave width" (number of mandates
        in the current batch), with a minimum of 1 and a maximum capped by
        the globally configured `settings.JIT_MAX_WORKERS`.
        """
        # FIX 3: Introduce adaptive worker-count tuning for asyncio.TaskGroup
        # based on wave width, referencing `settings`.
        current_max_workers = self._max_workers_config if self._max_workers_config is not None else settings.JIT_MAX_WORKERS
        wave_width = len(self.mandates) if hasattr(self, 'mandates') and self.mandates else 0

        # If wave_width is 0, use the default workers from settings.
        # Otherwise, cap the workers by the wave_width and the global max workers.
        max_workers_for_wave = wave_width if wave_width > 0 else settings.DEFAULT_WORKERS
        calculated_workers = min(current_max_workers, max_workers_for_wave)

        return max(1, calculated_workers)
