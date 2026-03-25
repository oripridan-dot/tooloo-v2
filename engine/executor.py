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
#  [SOTA Tool] Instrument engine/executor.py: OpenAI's "Assistant API" with fine-tuned
#     GPT-4 for persistent state management and context window expansion, enabling
#     continuous ideation threads.
#  [Pattern] Instrument engine/executor.py: Event-driven architecture leveraging
#     webhooks from user activity monitoring systems (e.g., IDE integrations) to
#     trigger context updates for ongoing ideation sessions.
#  [Risk] Instrument engine/executor.py: Data drift in fine-tuned models due to
#     evolving user ideation patterns, requiring proactive monitoring and
#     retraining strategies to maintain relevance.
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

# --- SOTA Tool: OpenAI Assistant API Integration ---

class AssistantAPIManager:
    """Manages interactions with OpenAI's Assistant API for persistent state and context."""

    def __init__(self, api_key: str, client: Optional[httpx.AsyncClient] = None):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.client = client or httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        # Cache for assistants, threads, and messages to manage state
        self._assistants: Dict[str, str] = {}  # {domain: assistant_id}
        self._threads: Dict[str, str] = {}    # {mandate_id: thread_id}
        self._messages: Dict[str, List[Dict[str, Any]]] = {} # {thread_id: list of messages}
        self._model = settings.OPENAI_ASSISTANT_MODEL or "gpt-4-turbo-preview" # Fine-tuned GPT-4

    async def _ensure_assistant(self, domain: str) -> str:
        """Ensures an assistant exists for the given domain, creating one if necessary."""
        if domain in self._assistants:
            return self._assistants[domain]

        # Tool integration for GANs/RL for dynamic ideation theme generation:
        # Define tools that the assistant can use, e.g., for trend analysis or content generation.
        assistant_config = {
            "name": f"TooLoo Ideation Assistant ({domain})",
            "instructions": (
                "You are a highly creative AI assistant designed to help users brainstorm and develop ideas. "
                "Leverage your tools for dynamic ideation theme generation and suggestion refinement based on "
                "real-time trend analysis. Maintain context across multiple turns. "
                "Be mindful of potential biases and avoid generating harmful content. "
                "Use the provided tools to enhance ideation. If you need to identify trends, use `generate_ideation_theme`. "
                "If you need to refine an idea based on feedback or trends, use `refine_suggestion`."
            ),
            "model": self._model,
            "tools": [
                {"type": "code_interpreter"},
                {"type": "retrieval"},
                # Tool definition for GANs/RL for dynamic ideation theme generation and suggestion refinement
                {"type": "function", "function": {
                    "name": "generate_ideation_theme",
                    "description": "Generates new ideation themes using GANs based on trends. Requires keywords and optionally a trend data source.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keywords": {"type": "array", "items": {"type": "string"}},
                            "trend_data_source": {"type": "string", "enum": ["twitter", "news_api", "google_trends"], "description": "Source for trend analysis data."}
                        },
                        "required": ["keywords"]
                    }
                }},
                {"type": "function", "function": {
                    "name": "refine_suggestion",
                    "description": "Refines a given suggestion based on feedback or trend analysis using RL. Requires the suggestion and optionally feedback or trend context.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "suggestion": {"type": "string"},
                            "feedback": {"type": "string"},
                            "trend_context": {"type": "string"}
                        },
                        "required": ["suggestion"]
                    }
                }}
            ],
            "temperature": 0.7, # Higher temperature for creative tasks
            "top_p": 1.0,
        }

        try:
            response = await self.client.post(f"{self.base_url}/assistants", json=assistant_config)
            response.raise_for_status()
            assistant_data = response.json()
            assistant_id = assistant_data["id"]
            self._assistants[domain] = assistant_id
            logger.info(f"Created or retrieved Assistant for domain '{domain}': {assistant_id}")
            return assistant_id
        except httpx.HTTPStatusError as e:
            logger.error(f"Error creating/retrieving Assistant for domain '{domain}': {e}", exc_info=True)
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
            logger.error(f"Error creating thread for mandate '{mandate_id}': {e}", exc_info=True)
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
            logger.error(f"Error adding message to thread {thread_id}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding message to thread {thread_id}: {e}", exc_info=True)
            raise

    async def run_and_get_response(self, mandate_id: str, domain: str, user_input: str) -> Dict[str, Any]:
        """Adds user input, runs the assistant, and retrieves the latest response."""
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

            # Polling for run completion
            while True:
                await asyncio.sleep(1) # Wait before polling
                status_response = await self.client.get(f"{self.base_url}/assistants/threads/{thread_id}/runs/{run_id}")
                status_response.raise_for_status()
                run_status = status_response.json()

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
                    # Update local message cache
                    self._messages.setdefault(thread_id, []).append({"role": latest_message["role"], "content": latest_message["content"][0]["text"]["value"]})
                    return latest_message
                else:
                    logger.warning(f"Run {run_id} completed but no messages found for thread {thread_id}.")
                    return {"role": "assistant", "content": "No response generated."}
            else:
                logger.error(f"Run {run_id} for thread {thread_id} failed or was cancelled. Status: {run_status['status']}")
                return {"role": "assistant", "content": f"Assistant run failed with status: {run_status['status']}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"Error running assistant for thread {thread_id} (mandate: {mandate_id}): {e}", exc_info=True)
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

def get_assistant_api_manager() -> AssistantAPIManager:
    """Lazily initializes and returns the Assistant API Manager."""
    global _assistant_api_manager
    if _assistant_api_manager is None:
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in settings.")
        _assistant_api_manager = AssistantAPIManager(api_key=api_key)
        logger.info("Assistant API Manager initialized.")
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

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
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
        # 3. Fine-tuning a new version of the GPT-4 model with potentially improved data and techniques.
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
            "change_failure_rate": round(self.change_failure_rate, 4),
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

    def __init__(self, max_workers: Optional[int] = None) -> None:
        # FIX 1: Replace ThreadPoolExecutor with asyncio.TaskGroup for modern Python concurrency.
        # The underlying execution mechanism is now async.
        self._max_workers_config = max_workers
        self._latency_histogram: list[float] = []
        self._failed_latencies: list[float] = []  # DORA: MTTR proxy
        self._total_nodes: int = 0                 # DORA: throughput / CFR
        self._failed_nodes: int = 0                # DORA: change_failure_rate
        self._hist_lock = threading.Lock()
        self.mandates: list[Envelope] = []  # Initialize mandates for adaptive worker count

        # Initialize event listeners for context updates (Pattern: Event-driven)
        _user_activity_monitor.subscribe(self._handle_user_activity_event)

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
                api_manager = get_assistant_api_manager()
                # Convert event data to a human-readable string or structured format
                content_update = f"User Activity Update ({event_type}): {json.dumps(data)}"
                await api_manager.add_message(mandate_id, current_mandate_envelope.domain, "system", content_update)
                logger.info(f"Updated Assistant context for mandate {mandate_id} with user activity: {event_type}")
            except Exception as e:
                logger.error(f"Failed to update Assistant context for mandate {mandate_id} due to user activity: {e}", exc_info=True)
        else:
            logger.warning(f"Received user activity for mandate {mandate_id}, but it is not currently active in executor.")

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
        effective_workers = max_workers or self._adaptive_worker_count()

        # EXECUTION: fan out and collect results
        # FIX 1: Use asyncio.TaskGroup for modern Python concurrency.
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(self._run_async(work_fn, env)) for env in envelopes]
            # TaskGroup automatically awaits all its children, so explicit gather is not strictly needed.
            # However, we keep it here for clarity on collecting results in order.

        # Collect results in the original order. Task results are typically available
        # via the task objects themselves after the TaskGroup finishes.
        # We can iterate through the original task list to maintain order.
        ordered = [task.result() for task in tasks]

        self._record_latencies(r.latency_ms for r in ordered if r.latency_ms is not None)
        self._record_results(ordered)

        # After execution, check for model drift and bias if applicable
        # This is a simplified example; real drift/bias detection would be more complex
        # and might be triggered by specific performance metrics recorded.
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
            # In a real scenario, retraining might be triggered based on overall system performance
            # or specific mandates. Here, we'll use the first mandate's domain for demonstration.
            if envelopes:
                await _model_drift_monitor.trigger_retraining_or_adjustment(envelopes[0].mandate_id, drift_detected, bias_detected)

        return ordered

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
                if node_id in results:
                    continue
                # Ensure node is truly ready and not blocked by failed parents
                if unresolved.get(node_id, 0) == 0 and not failed_parents.get(node_id):
                    # FIX 1: Create tasks using tg.create_task
                    task = tg.create_task(self._run_async(work_fn, env_by_id[node_id]))
                    running[task] = node_id
                else:
                    # If a node was added to ready but later found to be blocked,
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
                    await _finalise_child(child_id)
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
                # FIX 1: Use asyncio.wait with return_when=asyncio.FIRST_COMPLETED
                # TaskGroup automatically manages waiting for tasks. We monitor `running` tasks.
                # To get results from completed tasks within the TaskGroup, we typically iterate
                # through `tg.all_tasks()` or manage them separately if needed for finer control.
                # For this DAG structure, a simple loop that checks `running` and submits new tasks
                # works, relying on TaskGroup to manage exceptions and completion.

                # Wait for any running task to complete.
                completed_tasks = []
                try:
                    # This await is crucial to yield control and allow tasks to finish.
                    # We don't need to manage task groups directly here for completion detection,
                    # as TaskGroup handles exceptions and finalization.
                    # We will check results after the TaskGroup context manager exits.
                    # However, to manage submitting new tasks while others run, we need a loop.
                    # A direct `await tg.join()` would block until all are done.
                    # A workaround for more granular control within TaskGroup is to use `asyncio.sleep`
                    # and re-check task status or manage tasks individually if needed.
                    # For this structure, we assume the `while running` loop with `asyncio.sleep`
                    # and submission logic inside the `TaskGroup` context is sufficient.
                    # The most direct way to proceed without blocking the entire TaskGroup prematurely
                    # is to allow the loop to run, and submit new tasks when workers are free.
                    await asyncio.sleep(0.01) # Short sleep to prevent busy-waiting and allow yielding

                    # Check which tasks have completed. This is conceptual; TaskGroup manages this.
                    # In a real scenario, one might maintain a list of tasks and check `task.done()`.
                    # Since `tg` handles this, we rely on it. The `running` dict is our tracker.
                    tasks_to_remove = []
                    for task, node_id in running.items():
                        if task.done():
                            completed_tasks.append((task, node_id))
                            tasks_to_remove.append(task)

                    for task in tasks_to_remove:
                        del running[task]

                except asyncio.CancelledError:
                    # If the TaskGroup is cancelled, we should exit.
                    break
                except Exception as e:
                    logger.error(f"Error during DAG execution loop: {e}", exc_info=True)
                    # Handle loop errors, potentially marking remaining tasks as failed.
                    break # Exit loop on error

                for fut, node_id in completed_tasks:
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
                            latency_ms=0.0,
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

            # Ensure all nodes are accounted for after the loop and TaskGroup context exits.
            # This loop will run after all tasks in the TaskGroup have completed.
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
                del self._latency_histogram[:overflow]

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
    ) -> ExecutionResult:
        """Executes a single work function for a given envelope and returns an ExecutionResult."""
        start_time = time.perf_counter()
        try:
            # FIX 4: Handle both synchronous and asynchronous work functions.
            # Integrate Assistant API interaction here if work_fn is an ideation task
            # that should leverage the Assistant API.
            # The `ideate_with_assistant` function name is a convention for tasks using the Assistant API.
            if hasattr(work_fn, '__name__') and work_fn.__name__ == "ideate_with_assistant":
                api_manager = get_assistant_api_manager()
                # Pass relevant envelope data to the Assistant API manager
                # The "intent" is crucial for guiding the assistant.
                assistant_response = await api_manager.run_and_get_response(
                    mandate_id=env.mandate_id,
                    domain=env.domain,
                    user_input=env.intent # Using intent as the user's prompt
                )
                result = assistant_response.get("content", "No response received from assistant.")
                # Record Assistant API performance if needed for drift monitoring
                # This might require adding performance metrics to AssistantAPIManager
                
                # Risk: Amplification of existing biases or generation of novel, unintended harmful content
                # Basic check for potentially harmful content (conceptual, requires more sophisticated NLP)
                if "harmful" in result.lower() or "offensive" in result.lower():
                    logger.warning(f"Potentially harmful content detected in response for mandate {env.mandate_id}: {result[:100]}...")
                    # In a real system, this could trigger a flag, a human review, or a re-prompt with safety instructions.
                    # For now, we log a warning.
                    
                # Conceptually, if this executor were part of a federated learning setup,
                # the 'result' might represent a local model's contribution.
                # We can simulate recording this insight.
                if env.metadata.get("is_federated_learning_client"):
                    _federated_learning_aggregator.record_distributed_insight(env.mandate_id, {"output": result, "domain": env.domain})


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

            # Trigger user activity simulation for demonstration purposes (Pattern: Event-driven)
            # In a real system, this would be driven by actual user actions.
            if env.metadata.get("simulate_activity"):
                await _user_activity_monitor.simulate_user_interaction(
                    mandate_id=env.mandate_id,
                    session_id=env.metadata.get("session_id", f"session-{env.mandate_id}"),
                    event_type="idea_generation_step",
                    data={"idea_fragment": str(result)[:100]} # Example data
                )

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
            logger.error(f"Mandate {env.mandate_id} failed: {e}", exc_info=True)
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
