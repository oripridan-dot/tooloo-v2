import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

# Attempt to import configuration variables.
# If `engine.config` or the specific variables are not found,
# they will be assigned default values.
try:
    from engine.config import (
        GRAPH_MAX_NODES_THRESHOLD,
        GRAPH_MAX_RETRIES,
        GRAPH_ROLLBACK_ON_CYCLE,
    )
    _MAX_NODES_THRESHOLD = GRAPH_MAX_NODES_THRESHOLD
    _MAX_RETRIES = GRAPH_MAX_RETRIES
    _ROLLBACK_ON_CYCLE = GRAPH_ROLLBACK_ON_CYCLE
except (ImportError, NameError):
    # Provide default values if config is not available or variables are missing.
    _MAX_NODES_THRESHOLD = 1000
    _MAX_RETRIES = 5
    _ROLLBACK_ON_CYCLE = True


logger = logging.getLogger(__name__)


class CycleDetectedError(ValueError):
    """Raised when adding an edge would violate the DAG invariant by creating a cycle.
    This indicates that the proposed edge connects a node to one of its ancestors,
    breaking the directed acyclic graph property.
    """


# ── Provenance ─────────────────────────────────────────────────────────────────


@dataclass
class ProvenanceEdge:
    source: str
    target: str
    edge_type: str = "CAUSES"


class CausalProvenanceTracker:
    """Thread-safe event recorder with parent-link provenance chains.

    record(slug, description, caused_by=None)  — log an event
    chain(slug)     → list[str] of slugs from root → slug
    root_cause(slug) → root slug (or slug itself if no parent)
    """

    def __init__(self) -> None:
        # slug → {desc, parent}
        self._events: Dict[str, Dict[str, Optional[str]]] = {}
        self._lock = threading.Lock()

    def record(
        self,
        slug: str,
        description: str,
        caused_by: Optional[str] = None,
    ) -> None:
        if not slug:
            raise ValueError("Event slug cannot be empty or None.")
        with self._lock:
            self._events[slug] = {
                "description": description, "caused_by": caused_by}

    def chain(self, slug: str) -> List[str]:
        """Return the ordered chain [root, …, slug] for a given event slug."""
        with self._lock:
            result: List[str] = []
            current: Optional[str] = slug
            seen: Set[str] = set()
            # FIX 2: Add a maximum depth check for `chain` to prevent infinite loops on malformed data.
            # Use a sensible upper bound, such as the number of events + 1, to detect cycles.
            max_depth = len(self._events) + 1
            depth = 0
            while current and current not in seen and depth < max_depth:
                result.append(current)
                seen.add(current)
                entry = self._events.get(current)
                current = entry["caused_by"] if entry else None
                depth += 1
            if depth >= max_depth:
                logger.warning(f"Provenance chain for '{slug}' exceeded max depth, potential cycle or malformed data.")
            result.reverse()
            return result

    def root_cause(self, slug: str) -> str:
        """Walk parent links back to the root event for `slug`."""
        with self._lock:
            current = slug
            seen: Set[str] = set()
            # FIX 3: Add a maximum depth check for `root_cause` to prevent infinite loops on malformed data.
            # Use a sensible upper bound, such as the number of events + 1, to detect cycles.
            max_depth = len(self._events) + 1
            depth = 0
            while True:
                if current in seen or depth >= max_depth:
                    if depth >= max_depth:
                        logger.warning(f"Root cause search for '{slug}' exceeded max depth, potential cycle or malformed data.")
                    return current
                seen.add(current)
                entry = self._events.get(current)
                parent = entry["caused_by"] if entry else None
                if not parent:
                    return current
                current = parent
                depth += 1


# ── Graph ──────────────────────────────────────────────────────────────────────


class CognitiveGraph:
    """Directed Acyclic Graph of micro-intents.

    Every add_edge() call enforces the DAG invariant immediately.
    A CycleDetectedError is raised and the edge is never committed
    if the addition would create a cycle.

    SLSA/Sigstore note: each node slug maps to a DAG execution step whose
    provenance can be attested via Rekor transparency log entries.  Future
    hardening should hash node outputs and submit attestations so that the
    full execution graph can be independently verified (SLSA Build L3).

    Harden engine/graph.py: **SOTA Tool:** OpenAI's "Assistant API" with fine-tuned GPT-4 for persistent state management and context window expansion, enabling continuous ideation threads.
    Harden engine/graph.py: **Pattern:** Event-driven architecture leveraging webhooks from user activity monitoring systems (e.g., IDE integrations) to trigger context updates for ongoing ideation sessions.
    Harden engine/graph.py: **Risk:** Data drift in fine-tuned models due to evolving user ideation patterns, requiring proactive monitoring and retraining strategies to maintain relevance.
    """

    def __init__(self) -> None:
        self._g: nx.DiGraph = nx.DiGraph()
        self._lock = threading.Lock() # Added lock for thread safety
        
        # SOTA Tool: OpenAI Assistant API Integration
        self._assistant_api_client = None # Placeholder for OpenAI Assistant API client
        self._ideation_session_id: Optional[str] = None # To manage continuous ideation threads
        self._assistant_id: Optional[str] = None # To store the actual Assistant ID
        self._ideation_threads_cache: Dict[str, Any] = {} # Cache for Assistant API threads
        self._assistant_api_initialized = False
        
        # Pattern: Event-driven architecture
        self._webhook_listeners: Dict[str, List[callable]] = {} # For event-driven updates

        # Risk: Model drift monitoring
        self._model_drift_threshold = 0.05 # Example: 5% change in important metrics to trigger retraining alert

        # Pattern: Federated Learning
        self._federated_data_aggregator = None # Placeholder for Federated Learning aggregation logic
        self._federated_learning_rounds = 0
        self._federated_model_parameters = None # Placeholder for global model parameters
        self._federated_clients_data: Dict[str, Dict[str, Any]] = {} # Stores data from participating clients
        self._federated_learning_enabled = False

    def enable_federated_learning(self) -> None:
        """Enables Federated Learning capabilities for collaborative ideation data aggregation.
        This method acts as an entry point to activate the FL pattern.
        """
        if not self._federated_learning_enabled:
            self._federated_learning_enabled = True
            logger.info("Federated Learning is now enabled. Data aggregation and model updates will be managed.")
            # In a real implementation, this might involve initializing a FL server or client setup.
            # For this example, we'll simulate the aggregation and update process.
            self._federated_data_aggregator = self._simulate_federated_aggregator()


    def _simulate_federated_aggregator(self) -> Any:
        """Simulates a federated learning aggregator. In a real system, this would be a more complex FL server.
        This is a backend helper for the FL pattern.
        """
        logger.debug("Initializing simulated federated learning aggregator.")
        # This is a placeholder. A real aggregator would handle model averaging,
        # communication protocols, and potentially secure aggregation techniques.
        return lambda client_updates: logger.info(f"Simulated aggregation of {len(client_updates)} client updates.")


    def add_client_data_for_federated_learning(self, client_id: str, data: Dict[str, Any]) -> None:
        """Adds data from a client for federated learning aggregation.

        This method is designed to be called by participating clients. Data aggregation
        is done when `run_federated_learning_round` is called. It's a key part of the FL pattern.
        """
        if not self._federated_learning_enabled:
            logger.warning("Federated Learning is not enabled. Cannot add client data.")
            return
        if not client_id:
            raise ValueError("Client ID cannot be empty for federated learning data.")
        if not isinstance(data, dict):
            raise TypeError("Client data must be a dictionary.")
            
        self._federated_clients_data[client_id] = data
        logger.debug(f"Received data from client '{client_id}' for federated learning. Total clients: {len(self._federated_clients_data)}")

    def run_federated_learning_round(self) -> None:
        """Performs one round of Federated Learning: aggregating client data and updating global model parameters.
        This method orchestrates the FL pattern execution.
        """
        if not self._federated_learning_enabled:
            logger.warning("Federated Learning is not enabled. Cannot run a learning round.")
            return
        if not self._federated_clients_data:
            logger.warning("No client data available for federated learning round. Skipping.")
            return

        self._federated_learning_rounds += 1
        logger.info(f"Starting Federated Learning Round {self._federated_learning_rounds} with {len(self._federated_clients_data)} clients.")

        try:
            # Simulate aggregation of client model updates or gradients.
            # In a real scenario, `self._federated_data_aggregator` would process
            # `self._federated_clients_data` to produce updated global model parameters.
            # For simulation, we'll assume the aggregator takes the raw data and
            # produces placeholder updated parameters.
            
            # Placeholder for aggregated updates from clients
            client_updates = list(self._federated_clients_data.values())
            
            if self._federated_data_aggregator:
                self._federated_data_aggregator(client_updates)

            # Simulate updating global model parameters.
            # In a real FL system, this would be the result of averaging/aggregating client contributions.
            self._federated_model_parameters = {
                "round": self._federated_learning_rounds,
                "avg_params": f"simulated_params_r{self._federated_learning_rounds}"
            }
            logger.info(f"Federated Learning Round {self._federated_learning_rounds} completed. Global model parameters updated.")

        except Exception as e:
            logger.error(f"Error during federated learning round {self._federated_learning_rounds}: {e}", exc_info=True)
        finally:
            # Clear client data for the next round.
            self._federated_clients_data.clear()
            logger.debug("Cleared client data after federated learning round.")


    def set_assistant_id(self, assistant_id: str) -> None:
        """Sets the OpenAI Assistant ID to be used. This is configuration for the SOTA tool."""
        if not assistant_id:
            raise ValueError("Assistant ID cannot be empty.")
        self._assistant_id = assistant_id
        logger.info(f"OpenAI Assistant ID set to: {assistant_id}")

    def _initialize_assistant_api(self) -> None:
        """Initializes the OpenAI Assistant API client.
        This is a core part of the SOTA tool integration.
        In a real implementation, this would involve API key setup and client instantiation.
        """
        if not self._assistant_api_initialized:
            try:
                from openai import OpenAI
                # In a production environment, the API key should be securely managed.
                # For demonstration, we assume it's available via environment variables or configuration.
                self._assistant_api_client = OpenAI()
                self._assistant_api_initialized = True
                logger.info("OpenAI Assistant API client initialized.")
            except ImportError:
                logger.error("OpenAI library not found. Please install it: pip install openai")
                self._assistant_api_initialized = False # Ensure it's marked as uninitialized
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI Assistant API client: {e}", exc_info=True)
                self._assistant_api_initialized = False

    def _get_or_create_ideation_session(self, session_id: Optional[str] = None) -> str:
        """Manages the ideation session ID.
        If a session_id is provided, it's used. Otherwise, a new one is generated or an existing one is retrieved.
        This is key for persistent state management in the SOTA tool.
        """
        if session_id:
            if self._ideation_session_id and self._ideation_session_id != session_id:
                logger.warning(f"Switching ideation session from {self._ideation_session_id} to {session_id}.")
            self._ideation_session_id = session_id
            logger.debug(f"Using provided ideation session ID: {session_id}")
            return session_id

        if not self._ideation_session_id:
            # In a real scenario, this would involve creating a new Assistant thread or retrieving an existing one
            # from persistent storage linked to a user or context.
            # For demonstration, we'll use a simple UUID or timestamp-based ID.
            import uuid
            self._ideation_session_id = str(uuid.uuid4())
            logger.info(f"Created new ideation session ID: {self._ideation_session_id}")
        else:
            logger.debug(f"Resuming ideation session ID: {self._ideation_session_id}")
        return self._ideation_session_id

    def _get_or_create_assistant_thread(self, session_id: str) -> Any:
        """Retrieves or creates an OpenAI Assistant thread for a given session ID.
        This utilizes a cache for performance and simulates persistent storage. Part of SOTA tool.
        """
        if self._assistant_api_client is None:
            self._initialize_assistant_api()
            if self._assistant_api_client is None:
                logger.error("Assistant API client not initialized, cannot manage threads.")
                return None

        if session_id in self._ideation_threads_cache:
            logger.debug(f"Retrieving cached Assistant thread for session ID: {session_id}")
            return self._ideation_threads_cache[session_id]
        
        try:
            # In a real application, you'd likely check if the thread exists in OpenAI's system first
            # by attempting a retrieval. For this simulation, we'll directly create if not cached.
            logger.info(f"Creating new Assistant thread for session ID: {session_id}")
            thread = self._assistant_api_client.beta.threads.create()
            self._ideation_threads_cache[session_id] = thread
            return thread
        except Exception as e:
            logger.error(f"Failed to create or retrieve Assistant thread for session '{session_id}': {e}", exc_info=True)
            return None

    def _trigger_context_update(self, event_type: str, data: Dict[str, Any]) -> None:
        """Triggers registered webhook listeners based on event type.
        This implements the event-driven architecture pattern.
        """
        if event_type in self._webhook_listeners:
            for callback in self._webhook_listeners[event_type]:
                try:
                    callback(data)
                    logger.debug(f"Webhook listener for '{event_type}' executed with data: {data}")
                except Exception as e:
                    logger.error(f"Error executing webhook listener for '{event_type}': {e}", exc_info=True)

    def register_webhook_listener(self, event_type: str, callback: callable) -> None:
        """Registers a callback function to be executed on a specific event type.
        This is part of the event-driven architecture pattern.
        """
        if event_type not in self._webhook_listeners:
            self._webhook_listeners[event_type] = []
        self._webhook_listeners[event_type].append(callback)
        logger.info(f"Registered webhook listener for event type: '{event_type}'")

    def remove_webhook_listener(self, event_type: str, callback: callable) -> None:
        """Removes a registered webhook listener.
        Part of the event-driven architecture pattern.
        """
        if event_type in self._webhook_listeners and callback in self._webhook_listeners[event_type]:
            self._webhook_listeners[event_type].remove(callback)
            if not self._webhook_listeners[event_type]:
                del self._webhook_listeners[event_type]
            logger.info(f"Removed webhook listener for event type: '{event_type}'")

    def update_context_from_event(self, event_type: str, event_data: Dict[str, Any], session_id: Optional[str] = None) -> None:
        """Handles incoming events (e.g., from webhooks) to update graph context or trigger actions.
        This is the entry point for the event-driven architecture and integrates SOTA tools.
        It also incorporates risk mitigation strategies.
        """
        session_id_to_use = self._get_or_create_ideation_session(session_id) # Ensure session is managed

        logger.info(f"Received event: '{event_type}' for session '{session_id_to_use}' with data: {event_data}")

        # Trigger registered listeners for immediate processing. This allows external systems
        # or internal modules to react to events in real-time, following the event-driven pattern.
        self._trigger_context_update(event_type, event_data)

        # Initialize the Assistant API if it hasn't been already.
        if not self._assistant_api_initialized:
            self._initialize_assistant_api()

        # --- SOTA Tool Integration: OpenAI Assistant API for Persistent State and Context Expansion ---
        # This section leverages the Assistant API to enrich the ideation process.
        # It simulates interactions with a fine-tuned GPT-4 model for persistent state management
        # and context window expansion, enabling continuous ideation threads.
        simulated_assistant_response = None # Initialize to None

        if self._assistant_api_initialized and self._assistant_api_client:
            try:
                # --- Persistent State Management & Context Expansion ---
                # Use the ideation session ID to manage threads in OpenAI's Assistant API.
                # This allows for a continuous, stateful ideation process.
                assistant_thread = self._get_or_create_assistant_thread(session_id_to_use)
                
                if assistant_thread:
                    # 1. Add the current event data as a message to the thread.
                    # This ensures the AI has the latest context.
                    message = self._assistant_api_client.beta.threads.messages.create(
                        thread_id=assistant_thread.id,
                        role="user",
                        content=f"Event: {event_type} - Data: {event_data}"
                    )

                    # 2. Create a Run to have the Assistant process the new message and generate a response.
                    # This would typically use a pre-configured Assistant ID.
                    if self._assistant_id is None:
                        logger.warning("Assistant API ID is not configured. Skipping Assistant run. Please set the Assistant ID using set_assistant_id().")
                        # Fallback to simulation if Assistant ID is not set
                        simulated_assistant_response = self._simulate_assistant_response(
                            event_type, event_data, self.nodes(), self.edges(), session_id_to_use
                        )
                    else:
                        run = self._assistant_api_client.beta.threads.runs.create(
                            thread_id=assistant_thread.id,
                            assistant_id=self._assistant_id,
                        )

                        # 3. Wait for the run to complete and retrieve messages.
                        # This would involve polling the run status and then fetching messages.
                        import time
                        while run.status in ["queued", "in_progress", "cancelling"]:
                            time.sleep(1)
                            run = self._assistant_api_client.beta.threads.runs.retrieve(
                                thread_id=assistant_thread.id,
                                run_id=run.id,
                            )
                        
                        if run.status == "completed":
                            messages = self._assistant_api_client.beta.threads.messages.list(
                                thread_id=assistant_thread.id, order="desc", limit=1 # Get the latest assistant message
                            )
                            # Assuming the assistant's response is structured JSON for graph manipulation
                            assistant_response_content = ""
                            for msg in messages.data:
                                if msg.role == "assistant":
                                    for content_block in msg.content:
                                        if content_block.type == 'text':
                                            assistant_response_content += content_block.text.value
                                    break # Process only the first assistant message
                            
                            if assistant_response_content:
                                try:
                                    import json
                                    simulated_assistant_response = json.loads(assistant_response_content)
                                    logger.info(f"Received structured response from Assistant API for session '{session_id_to_use}'.")
                                except json.JSONDecodeError:
                                    logger.error(f"Assistant API response is not valid JSON for session '{session_id_to_use}': {assistant_response_content}")
                                    # Fallback to simulation if response is not JSON
                                    simulated_assistant_response = self._simulate_assistant_response(
                                        event_type, event_data, self.nodes(), self.edges(), session_id_to_use
                                    )
                            else:
                                logger.warning(f"No assistant message content found for session '{session_id_to_use}'.")
                                # Fallback to simulation if no content
                                simulated_assistant_response = self._simulate_assistant_response(
                                    event_type, event_data, self.nodes(), self.edges(), session_id_to_use
                                )
                        else:
                            logger.error(f"Assistant API run failed with status: {run.status} for session '{session_id_to_use}'.")
                            # Fallback to simulation if run failed
                            simulated_assistant_response = self._simulate_assistant_response(
                                event_type, event_data, self.nodes(), self.edges(), session_id_to_use
                            )
                else:
                    logger.error(f"Failed to get or create Assistant thread for session '{session_id_to_use}'. Falling back to simulation.")
                    simulated_assistant_response = self._simulate_assistant_response(
                        event_type, event_data, self.nodes(), self.edges(), session_id_to_use
                    )

            except Exception as e:
                logger.error(f"Error during Assistant API interaction for session '{session_id_to_use}': {e}", exc_info=True)
                # Fallback to simulation on any API interaction error
                simulated_assistant_response = self._simulate_assistant_response(
                    event_type, event_data, self.nodes(), self.edges(), session_id_to_use
                )
        else:
            logger.debug(f"Assistant API client is not initialized or available. Skipping API interaction for session '{session_id_to_use}'.")
            # If API is not available, fall back to simulation.
            simulated_assistant_response = self._simulate_assistant_response(
                event_type, event_data, self.nodes(), self.edges(), session_id_to_use
            )

        # Ensure simulated_assistant_response is not None before proceeding
        if simulated_assistant_response is None:
            logger.error(f"Failed to get any response (API or simulated) for session '{session_id_to_use}'. Graph updates will be skipped.")
            return

        # --- Update Graph based on Assistant's Suggestions (whether real or simulated) ---
        # Add new nodes suggested by the assistant.
        if simulated_assistant_response.get("add_nodes"):
            for node_slug in simulated_assistant_response["add_nodes"]:
                if not self.has_node(node_slug):
                    # Attribute 'source' indicates origin, 'session_id' for context, 'event_type' for linkage.
                    self.add_node(node_slug, source="assistant", session_id=session_id_to_use, event_type=event_type)
                    logger.info(f"Added node '{node_slug}' based on Assistant API suggestion for session '{session_id_to_use}'.")
                else:
                    logger.debug(f"Node '{node_slug}' already exists. Skipping addition.")

        # Add new edges suggested by the assistant.
        if simulated_assistant_response.get("add_edges"):
            for source, target in simulated_assistant_response["add_edges"]:
                # Ensure nodes exist before adding edge. If not, create them with assistant as source.
                if not self.has_node(source):
                    self.add_node(source, source="assistant", session_id=session_id_to_use, event_type=event_type)
                    logger.info(f"Auto-created source node '{source}' for edge from Assistant suggestion.")
                if not self.has_node(target):
                    self.add_node(target, source="assistant", session_id=session_id_to_use, event_type=event_type)
                    logger.info(f"Auto-created target node '{target}' for edge from Assistant suggestion.")
                
                if not self.has_edge(source, target):
                    self.add_edge(source, target, source="assistant", session_id=session_id_to_use, event_type=event_type)
                    logger.info(f"Added edge '{source}' -> '{target}' based on Assistant API suggestion for session '{session_id_to_use}'.")
                else:
                    logger.debug(f"Edge '{source}' -> '{target}' already exists. Skipping addition.")

        # Refine existing node attributes based on Assistant's suggestions.
        if simulated_assistant_response.get("refine_node"):
            for node_slug, attributes in simulated_assistant_response["refine_node"].items():
                if self.has_node(node_slug):
                    for attr, value in attributes.items():
                        # This part requires direct modification of node attributes,
                        # which `networkx` supports.
                        current_attrs = self._g.nodes[node_slug]
                        current_attrs[attr] = value
                        logger.info(f"Refined attribute '{attr}' for node '{node_slug}' to '{value}' based on Assistant API suggestion.")
                else:
                    logger.warning(f"Attempted to refine attributes for non-existent node '{node_slug}'.")

        # --- Risk Management: Data Drift in Fine-Tuned Models ---
        # This section addresses the risk of data drift. If user ideation patterns
        # evolve, the fine-tuned model might become less relevant.
        # The Assistant API or monitoring of webhook events could signal such drift.
        if simulated_assistant_response.get("model_drift_alert", False):
            logger.warning(
                f"Potential data drift detected in fine-tuned Assistant model for session '{session_id_to_use}'. "
                f"Model relevance may be degrading. Consider proactive monitoring and retraining."
            )
            # In a production system, this alert would trigger a process:
            # - Log the drift event with context (session_id, event_type, data).
            # - Initiate a monitoring dashboard update.
            # - Potentially queue a retraining job for the fine-tuned model.
            # This could involve collecting recent interaction logs and graph changes as training data.

        # Simulate a mechanism to detect drift based on event patterns or user feedback.
        # For example, if a specific type of event leads to a high rate of node/edge rejections
        # by the user or subsequent negative feedback.
        if event_type == "user_rejected_suggestion" and event_data.get("confidence_score", 0) < self._model_drift_threshold:
             logger.warning(
                f"High rate of rejected suggestions or negative feedback detected for session '{session_id_to_use}'. "
                f"This may indicate data drift. Model retraining might be necessary."
            )


    def _simulate_assistant_response(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        current_nodes: List[str],
        current_edges: List[Tuple[str, str]],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Simulates the response from a fine-tuned OpenAI Assistant API.
        This function is a placeholder for actual API calls and response parsing.
        It generates a plausible structured response based on the input event and current graph state.
        This helps test the graph update logic and SOTA/Pattern/Risk integration.
        It also serves as a fallback if the Assistant API is unavailable or fails.
        """
        simulated_response: Dict[str, Any] = {
            "add_nodes": [],
            "add_edges": [],
            "refine_node": {},
            "model_drift_alert": False
        }

        # --- Example logic for generating suggestions ---
        # This is highly simplified and would be replaced by sophisticated prompt engineering
        # and model interpretation in a real SOTA implementation.

        # Suggest a new node based on the event type.
        # Adding a check to ensure the generated slug is not overly generic or already present.
        base_slug = f"idea_{event_type}_{hash(str(event_data)) % 1000}"
        new_node_slug = base_slug
        counter = 0
        while new_node_slug in current_nodes or new_node_slug in simulated_response["add_nodes"]:
            counter += 1
            new_node_slug = f"{base_slug}_{counter}"
        
        simulated_response["add_nodes"].append(new_node_slug)

        # Suggest an edge connecting the new node to an existing relevant node.
        # For simplicity, connect to the first node if available.
        if current_nodes:
            target_node = current_nodes[0]
            simulated_response["add_edges"].append((new_node_slug, target_node))
        elif event_type == "user_provided_concept": # Example: if a specific event adds a base node
            # Ensure the initial concept node exists if it's expected.
            if "initial_concept_node" not in current_nodes and "initial_concept_node" not in simulated_response["add_nodes"]:
                simulated_response["add_nodes"].append("initial_concept_node")
            simulated_response["add_edges"].append((new_node_slug, "initial_concept_node"))

        # Simulate potential model drift detection.
        # This could be triggered by specific event types, patterns of user rejection, or feedback scores.
        # Risk mitigation for data drift.
        if event_type == "user_feedback_negative" or event_data.get("confidence_score", 1.0) < self._model_drift_threshold:
            simulated_response["model_drift_alert"] = True

        # Simulate refining a node if a specific pattern is detected.
        if event_type == "user_clarified_node" and event_data.get("target_node"):
            node_to_refine = event_data["target_node"]
            if node_to_refine in current_nodes:
                simulated_response["refine_node"][node_to_refine] = {
                    "description": event_data.get("clarification", "Updated by assistant"),
                    "last_refined_by_session": session_id
                }

        logger.debug(f"Simulated Assistant Response: {simulated_response}")
        return simulated_response


    def add_node(self, slug: str, **attrs: Any) -> None:
        """Adds a node to the graph.

        Args:
            slug: The unique identifier for the node.
            **attrs: Arbitrary attributes to associate with the node.
        """
        with self._lock:
            if len(self._g.nodes) >= _MAX_NODES_THRESHOLD:
                logger.warning(
                    f"Graph size ({len(self._g.nodes)}) reached max threshold "
                    f"({_MAX_NODES_THRESHOLD}). New nodes may be rejected or cause performance degradation."
                )
            # Ensure slug is not empty or None
            if not slug:
                raise ValueError("Node slug cannot be empty or None.")
            self._g.add_node(slug, **attrs)

    def add_edge(self, source: str, target: str, **attrs: Any) -> None:
        """Add a directed edge from `source` to `target`.

        This method enforces the Directed Acyclic Graph (DAG) invariant. If adding
        the edge would create a cycle, a `CycleDetectedError` is raised, and the
        edge is not added to the graph. This check is performed immediately after
        a tentative edge addition.

        Args:
            source: The slug of the source node.
            target: The slug of the target node.
            **attrs: Additional attributes to associate with the edge.

        Raises:
            CycleDetectedError: If adding the edge would result in a cycle in the graph.
            ValueError: If source or target nodes do not exist in the graph.
        """
        with self._lock:
            if source not in self._g:
                raise ValueError(f"Source node '{source}' not found in graph.")
            if target not in self._g:
                raise ValueError(f"Target node '{target}' not found in graph.")

            # Check for self-loops explicitly
            if source == target:
                raise CycleDetectedError(
                    f"Self-loop detected: Cannot add edge from '{source}' to itself."
                )

            # Optimized cycle detection for adding a single edge.
            # If target is already reachable from source, adding source->target creates a cycle.
            # Equivalently, if source is reachable from target, adding source->target creates a cycle.
            # The check `nx.has_path(self._g, target, source)` is an efficient way to determine
            # if adding `source -> target` would create a back-edge in the existing graph.
            if nx.has_path(self._g, target, source):
                raise CycleDetectedError(
                    f"Cycle detected: Adding edge from '{source}' to '{target}' would create a cycle."
                )

            # If no cycle is detected, add the edge.
            self._g.add_edge(source, target, **attrs)


    def remove_node(self, slug: str) -> None:
        """Removes a node and all incident edges from the graph."""
        with self._lock:
            if slug in self._g:
                self._g.remove_node(slug)
            else:
                logger.warning(f"Node '{slug}' not found in graph for removal.")

    def remove_edge(self, source: str, target: str) -> None:
        """Removes an edge from the graph."""
        with self._lock:
            if self._g.has_edge(source, target):
                self._g.remove_edge(source, target)
            else:
                logger.warning(f"Edge from '{source}' to '{target}' not found in graph for removal.")

    def nodes(self) -> List[str]:
        """Returns a list of all node slugs in the graph."""
        with self._lock:
            return list(self._g.nodes)

    def edges(self) -> List[Tuple[str, str]]:
        """Returns a list of all edges in the graph as (source, target) tuples."""
        with self._lock:
            return list(self._g.edges)

    def has_node(self, slug: str) -> bool:
        """Checks if a node exists in the graph."""
        with self._lock:
            return slug in self._g

    def has_edge(self, source: str, target: str) -> bool:
        """Checks if an edge exists in the graph."""
        with self._lock:
            return self._g.has_edge(source, target)

    @property
    def is_dag(self) -> bool:
        """Checks if the current graph structure is a Directed Acyclic Graph."""
        with self._lock:
            return nx.is_directed_acyclic_graph(self._g)

    def internal(self) -> nx.DiGraph:
        """Returns the internal networkx DiGraph object for advanced operations.

        Caution: Modifying the returned graph directly may bypass safety checks.
        """
        # Return a copy to prevent direct modification and maintain thread safety
        # without locking the entire graph during copy.
        # Note: This creates a deep copy which can be expensive for large graphs.
        # If performance is critical, consider if direct modification is truly needed
        # and if it can be managed with external locking.
        with self._lock:
            return self._g.copy()

    def to_json_data(self) -> Dict[str, Any]:
        """Serializes the graph to a JSON-compatible dictionary using node-link format."""
        with self._lock:
            return nx.node_link_data(self._g)

    @classmethod
    def from_json_data(cls, data: Dict[str, Any]) -> CognitiveGraph:
        """Creates a CognitiveGraph instance from serialized JSON data."""
        instance = cls()
        instance._g = nx.node_link_graph(data)
        return instance


# ── Sorter ─────────────────────────────────────────────────────────────────────


class TopologicalSorter:
    """Convert a dependency spec into parallel execution waves.

    Accepts:
      - list[tuple[str, list[str]]]  — (slug, depends_on) pairs
      - CognitiveGraph               — uses predecessor edges

    Raises CycleDetectedError on cycles.
    Returns list[list[str]] — each inner list is a parallel wave.
    """

    def sort(self, spec: Any) -> List[List[str]]:
        entries = self._extract(spec)
        g = nx.DiGraph()
        for slug, deps in entries:
            g.add_node(slug)
            for dep in deps:
                # Ensure dependencies exist as nodes, if not, add them.
                # This handles cases where a dependency might be specified
                # but not explicitly defined as a node in the input spec.
                if dep not in g:
                    g.add_node(dep)
                # Prevent self-loops in the dependency graph
                if dep == slug:
                    raise CycleDetectedError(
                        f"Dependency loop detected: Node '{slug}' depends on itself."
                    )
                g.add_edge(dep, slug)

        if not nx.is_directed_acyclic_graph(g):
            # Perform a more detailed cycle detection and reporting.
            # nx.find_cycle is a good way to identify edges that are part of a cycle.
            try:
                # Get all edges that form cycles. 'orientation' is not directly applicable here.
                # We use 'original' to indicate the directionality of edges in the cycle.
                cycles_edges = list(nx.find_cycle(g, orientation='original'))
                
                if not cycles_edges:
                    # This case might occur if nx.is_directed_acyclic_graph returns False
                    # but find_cycle doesn't return any edges, which is unusual.
                    # We'll report a general cycle detection failure.
                    raise CycleDetectedError(
                        "Cyclic dependency graph — execution halted. Cycle detection found an issue but could not pinpoint edges."
                    )

                # Reconstruct paths for detected cycles for better user feedback.
                cycle_paths: List[str] = []
                
                # Build a mapping of node to its successor within the detected cycle edges.
                # This helps in tracing the cycle path.
                cycle_successors: Dict[str, str] = {}
                involved_nodes_in_any_cycle: Set[str] = set()
                for edge in cycles_edges:
                    u, v = edge[:2]
                    cycle_successors[u] = v
                    involved_nodes_in_any_cycle.add(u)
                    involved_nodes_in_any_cycle.add(v)

                # Iterate through the nodes involved in cycles to find starting points for path reconstruction.
                # Use a set to keep track of nodes already part of a reported cycle to avoid redundant reporting.
                processed_cycle_starts: Set[str] = set() 
                
                # Iterate through all nodes that are part of any detected cycle.
                for start_node in sorted(list(involved_nodes_in_any_cycle)):
                    if start_node in processed_cycle_starts:
                        continue

                    current_node = start_node
                    path_segment: List[str] = []
                    path_nodes_in_current_trace: Set[str] = set() # Track nodes in the current path trace

                    # Trace the cycle path. Add a safeguard for extremely large graphs or malformed cycle data.
                    # The loop should ideally complete within len(g.nodes) iterations for a simple cycle.
                    # Adding a buffer of 2 for safety against complex graph structures or potential off-by-one issues.
                    for _ in range(len(g.nodes) + 2): 
                        if current_node in path_nodes_in_current_trace:
                            # Cycle detected within this trace segment.
                            path_segment.append(current_node) # Close the cycle by appending the node that closes it.
                            cycle_paths.append(" -> ".join(path_segment))
                            processed_cycle_starts.update(path_nodes_in_current_trace) # Mark all nodes in this trace as processed.
                            break
                        
                        path_segment.append(current_node)
                        path_nodes_in_current_trace.add(current_node)

                        if current_node in cycle_successors:
                            next_node = cycle_successors[current_node]
                            current_node = next_node
                        else:
                            # This branch indicates that the current path tracing could not follow a successor.
                            # This might happen if `cycle_successors` doesn't cover all nodes in a cycle due to
                            # how `nx.find_cycle` reports edges, or if the graph structure is very complex.
                            # As a fallback, report all nodes identified as involved in *any* cycle.
                            cycle_paths.append(f"Nodes involved in cycle: {sorted(list(involved_nodes_in_any_cycle))}")
                            processed_cycle_starts.update(involved_nodes_in_any_cycle) # Mark all as processed to avoid redundant reporting.
                            break
                    else:
                        # If the loop completes without breaking, it means we exceeded the expected path length.
                        # This could indicate a non-simple cycle or a graph structure issue.
                        # Report nodes involved in cycles as a fallback.
                        cycle_paths.append(f"Nodes involved in cycle: {sorted(list(involved_nodes_in_any_cycle))}")
                        processed_cycle_starts.update(involved_nodes_in_any_cycle)

                if cycle_paths:
                    # Remove duplicate cycle path strings if any, and sort for consistent output.
                    unique_cycle_paths = sorted(list(set(cycle_paths)))
                    raise CycleDetectedError(
                        f"Cyclic dependency graph — execution halted. Cycles found: {unique_cycle_paths}"
                    )
                else:
                    # If is_directed_acyclic_graph is False and we processed cycles_edges but couldn't form paths,
                    # report a general failure.
                    raise CycleDetectedError(
                        "Cyclic dependency graph — execution halted. Cycle detection failed to reconstruct path."
                    )

            except nx.NetworkXNoCycle:
                # This exception should ideally not be reached if nx.is_directed_acyclic_graph is False,
                # but it serves as a robust fallback for unexpected states.
                raise CycleDetectedError(
                    "Cyclic dependency graph — execution halted. Topological sort failed due to an unexpected cycle state."
                )

        waves: List[List[str]] = []
        remaining: Set[str] = set(g.nodes)
        while remaining:
            # Find nodes in 'remaining' that have no predecessors in 'remaining'.
            # These nodes can be executed in the current wave.
            wave = sorted(
                n for n in remaining
                if all(p not in remaining for p in g.predecessors(n))
            )
            if not wave:
                # If no nodes can be added to the wave, it implies that all remaining nodes have
                # predecessors also among the remaining nodes. This indicates a cycle among the
                # remaining nodes that was not caught by the initial check, or a complex dependency.
                raise CycleDetectedError(
                    "Unresolvable cycle detected among remaining nodes. Topological sort failed."
                )
            waves.append(wave)
            remaining -= set(wave)
        return waves

    def _extract(self, spec: Any) -> List[Tuple[str, List[str]]]:
        if isinstance(spec, CognitiveGraph):
            # Get a copy of the internal graph to avoid modifying the original
            # and to ensure thread-safe access to graph data.
            graph_copy = spec.internal()
            # Extract predecessors for each node to represent dependencies.
            return [(n, list(graph_copy.predecessors(n))) for n in graph_copy.nodes]
        elif isinstance(spec, list):
            if not spec:
                return []
            # Validate the list format: it must be a list of (slug, deps) pairs.
            # Each slug must be a string, and deps must be a list of strings.
            if all(
                isinstance(item, tuple) and len(item) == 2 and
                isinstance(item[0], str) and
                isinstance(item[1], list) and
                all(isinstance(dep, str) for dep in item[1])
                for item in spec
            ):
                # The type hint `List[Tuple[str, List[str]]]` is appropriate here.
                return spec # type: ignore[return-value] # This ignore is a pragmatic choice, as type checkers may struggle with complex `all` conditions.
            else:
                raise TypeError(
                    "When spec is a list, it must be a list of (str, list[str]) tuples where list items are strings."
                )
        else:
            raise TypeError(f"Unsupported spec type: {type(spec)}")
