from __future__ import annotations

import logging
import re
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set, Optional, Tuple
import datetime
import json
import hashlib

# --- SOTA EXTENSIONS AS PER REQUIREMENTS ---

# Requirement: Emergence of decentralized knowledge graph frameworks (e.g., IPFS-backed semantic webs)
# for real-time, verifiable ideation data sourcing and integration.
class DecentralizedKnowledgeGraphConnector:
    """
    Simulates a connector to a decentralized knowledge graph (e.g., an IPFS-backed
    semantic web) for sourcing verifiable ideation data.
    """
    def __init__(self):
        # Simulate a small, in-memory semantic web.
        # Data is structured as (subject, predicate, object) triples.
        self._graph_data: Dict[str, List[Tuple[str, str, str]]] = {
            "ai_trends": [
                ("generative_ai", "has_application", "code_generation"),
                ("code_llama_2", "is_a", "generative_ai"),
                ("code_llama_2", "released_by", "meta"),
                ("federated_learning", "enables", "privacy_preserving_ml"),
                ("privacy_preserving_ml", "is_subcategory_of", "responsible_ai"),
            ],
            "market_shifts": [
                ("decentralized_finance", "disrupts", "traditional_banking"),
                ("semantic_web", "related_to", "ipfs"),
                ("ipfs", "is_a", "decentralized_storage"),
            ]
        }
        logger.info("DecentralizedKnowledgeGraphConnector initialized with simulated semantic web data.")

    async def query(self, topic: str, subject_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Queries the simulated knowledge graph and returns data with verifiable
        content identifiers (CIDs) mimicking IPFS.
        """
        logger.debug(f"Querying decentralized knowledge graph for topic: {topic}")
        await asyncio.sleep(0.05) # Simulate network latency
        triples = self._graph_data.get(topic, [])
        if subject_filter:
            triples = [t for t in triples if t[0] == subject_filter]

        if not triples:
            return {"data": [], "cid": None, "verified": False}

        # Simulate creating a verifiable content identifier (CID)
        data_str = json.dumps(triples, sort_keys=True)
        cid = "z" + hashlib.sha256(data_str.encode('utf-8')).hexdigest() # 'z' prefix for simulation

        logger.info(f"Sourced {len(triples)} triples for topic '{topic}'. Verifiable CID: {cid}")
        return {"data": triples, "cid": cid, "verified": True}

# Requirement: Increased adoption of federated learning for privacy-preserving model updates
# on sensitive ideation datasets, mitigating data leakage risks.
class FederatedLearningAggregator:
    """
    Simulates a federated learning system for privacy-preserving model updates.
    It aggregates updates from multiple clients without accessing their raw,
    sensitive ideation data.
    """
    def __init__(self):
        # The global model here is a simplified representation, e.g., aggregated concept scores.
        self.global_model_weights: Dict[str, float] = {
            "ai_ethics": 0.5,
            "sustainability": 0.3,
            "decentralization": 0.1,
        }
        logger.info("FederatedLearningAggregator initialized with a global model.")

    async def perform_federated_round(self, client_updates: List[Dict[str, float]], learning_rate: float = 0.1):
        """
        Aggregates model updates (not raw data) from clients using Federated Averaging (FedAvg).
        This ensures privacy as sensitive datasets remain on client devices.
        """
        if not client_updates:
            logger.warning("Federated round skipped: No client updates provided.")
            return

        logger.info(f"Starting federated aggregation round with {len(client_updates)} client updates.")
        await asyncio.sleep(0.1) # Simulate aggregation compute time

        # This simulates the core of Federated Averaging: averaging the weights/gradients.
        aggregated_deltas: Dict[str, float] = {}
        total_updates: Dict[str, int] = {}

        for update in client_updates:
            for concept, delta in update.items():
                aggregated_deltas[concept] = aggregated_deltas.get(concept, 0.0) + delta
                total_updates[concept] = total_updates.get(concept, 0) + 1

        # Update the global model
        for concept, total_delta in aggregated_deltas.items():
            average_delta = total_delta / total_updates[concept]
            current_weight = self.global_model_weights.get(concept, 0.0)
            # Simple gradient descent-style update
            self.global_model_weights[concept] = current_weight + (learning_rate * average_delta)

        logger.info(f"Global model updated via federated learning. New weights: {self.global_model_weights}")

# Simulates a client participating in federated learning
async def run_federated_client_training(client_id: int, sensitive_data: Dict) -> Dict[str, float]:
    """Simulates a local training round on a client's private data."""
    logger.debug(f"Client {client_id}: Starting local training on private data.")
    await asyncio.sleep(0.2) # Simulate local training time
    # In a real scenario, this would train a model and generate weight deltas.
    # Here, we simulate generating "insights" as deltas.
    # The important part is that `sensitive_data` never leaves the client.
    model_update = {}
    if "ethical concerns" in sensitive_data["notes"]:
        model_update["ai_ethics"] = 0.2 # Positive update
    if "green tech" in sensitive_data["ideas"]:
        model_update["sustainability"] = 0.1
    if "blockchain" in sensitive_data["ideas"]:
        model_update["decentralization"] = 0.3
    if "over-monetization" in sensitive_data["notes"]:
        model_update["ai_ethics"] = model_update.get("ai_ethics", 0.0) - 0.1 # Negative update

    logger.debug(f"Client {client_id}: Generated model update (delta): {model_update}")
    return model_update

# Placeholder for OpenAI library interaction.
try:
    # Using the latest OpenAI library structure
    from openai import OpenAI
    openai_available = True
except ImportError:
    openai_available = False

from engine.psyche_bank import CogRule

# Event-driven components (simulated)
class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[callable]] = {}

    def subscribe(self, event_type: str, listener: callable):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)
        logger.debug(f"Subscribed listener to event: {event_type}")

    async def publish(self, event_type: str, payload: Any):
        if event_type in self._listeners:
            logger.debug(f"Publishing event: {event_type} with payload: {payload}")
            for listener in self._listeners[event_type]:
                try:
                    # Support both sync and async listeners
                    if asyncio.iscoroutinefunction(listener):
                        # Schedule as a task to avoid blocking the event bus
                        asyncio.create_task(listener(payload))
                    else:
                        listener(payload)
                except Exception as e:
                    logger.error(f"Error publishing event {event_type} to listener: {e}", exc_info=True)
        else:
            logger.debug(f"No listeners for event type: {event_type}")

# Requirement: Advancements in LLM fine-tuning, e.g., Meta's Code Llama 2 (2026 iteration)
# leveraging multi-modal input for more robust background refresh.
class SimulatedCodeLlama2026API:
    """
    Simulates an advanced code generation assistant, like a future iteration of
    Code Llama (2026), with multi-modal input capabilities for robust context
    refresh and analysis.
    """
    def __init__(self):
        self._assistant_id = "asst_simulated_codellama_2026_id_67890"
        self._threads: Dict[str, Dict[str, Any]] = {}
        self._thread_context_window_size = 256000 # Simulating larger context windows
        self._max_threads = 100

    async def create_thread(self, **kwargs) -> Dict[str, Any]:
        thread_id = f"thread_{len(self._threads)}_{hash(asyncio.get_running_loop().time())}"
        if len(self._threads) >= self._max_threads:
            oldest_thread_id = list(self._threads.keys())[0]
            del self._threads[oldest_thread_id]
            logger.warning(f"Max threads reached, evicted thread: {oldest_thread_id}")
        self._threads[thread_id] = {"messages": [], "modal_context": [], **kwargs}
        logger.debug(f"Created new CodeLlama-2026 thread: {thread_id}")
        return {"id": thread_id}

    async def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        return self._threads.get(thread_id)

    async def add_message_to_thread(self, thread_id: str, role: str, content: str, modal_data: Optional[Dict] = None) -> None:
        thread = await self.get_thread(thread_id)
        if thread:
            thread["messages"].append({"role": role, "content": content})
            if modal_data:
                # Store multi-modal data separately in the thread's context
                thread["modal_context"].append(modal_data)
                logger.debug(f"Added multi-modal data to thread {thread_id}: {modal_data.get('type')}")
            # Simple context window management
            if len(thread["messages"]) > self._thread_context_window_size:
                thread["messages"] = thread["messages"][-self._thread_context_window_size:]
            logger.debug(f"Added message to thread {thread_id}: {role} - {content[:50]}...")
        else:
            logger.warning(f"Thread not found for adding message: {thread_id}")

    async def run_assistant_on_thread(self, thread_id: str, prompt: str, tool_choice: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulates the Code Llama 2026 run, incorporating multi-modal context
        and advanced function calling.
        """
        thread = await self.get_thread(thread_id)
        if not thread:
            return {"error": "Thread not found."}

        # Add user's prompt, which might include implicit modal references
        await self.add_message_to_thread(thread_id, "user", prompt)
        logger.debug(f"Running CodeLlama-2026 on thread {thread_id} with prompt: {prompt[:50]}...")

        # --- Multi-modal Context Synthesis ---
        simulated_modal_analysis = ""
        if thread.get("modal_context"):
            for modal_item in thread["modal_context"]:
                if modal_item.get('type') == 'image_url':
                    simulated_modal_analysis += f" [System Note: Analysis of image at {modal_item.get('url')} suggests it is a system architecture diagram depicting a microservices-based approach.]"
                elif modal_item.get('type') == 'data_viz':
                    simulated_modal_analysis += f" [System Note: The provided data visualization shows a 30% increase in user engagement after the last feature launch.]"
            thread["modal_context"] = []

        context_messages = thread["messages"]
        full_context_for_llm = " ".join([m["content"] for m in context_messages]) + simulated_modal_analysis

        simulated_response_content = ""

        if "robust background refresh" in prompt.lower():
            simulated_response_content = (
                f"Simulated CodeLlama-2026 background refresh synthesis.\n"
                f"Thread Summary: The conversation revolves around an engram, with recent user activity noted. "
                f"The context includes {len(context_messages)} messages.\n"
                f"Multi-modal Analysis: {simulated_modal_analysis if simulated_modal_analysis else 'No new modal data.'}\n"
                "This refresh provides a comprehensive state-of-the-art summary for continued contextual generation."
            )
            await self.add_message_to_thread(thread_id, "assistant", simulated_response_content)

        # Risk: Adversarial AI & XAI - Enhanced simulation for Explainable AI
        elif "JSON object" in prompt and "is_anomalous" in prompt:
             simulated_response_content = "Simulated AI analysis result."
             # The prompt from XAIAnomalyDetector is designed to trigger this.
             # This block simulates the LLM detecting an adversarial pattern.
             is_adversarial = "evasion" in full_context_for_llm or "covering their tracks" in full_context_for_llm
             if is_adversarial or len([s for s in context_messages if "passed: false" in s.get('content','').lower()]) > 2:
                  xai_output = {
                      "is_anomalous": True,
                      "risk_score": 9,
                      "summary": "Potential adversarial activity detected: log manipulation attempt.",
                      "explanation": {
                          "chain_of_thought": "The sequence shows rapid, repeated failed evaluations followed by an attempt to modify logging configuration. This pattern is highly consistent with an adversary trying to cover their tracks after a failed exploit attempt.",
                          "contributing_factors": [
                              {"event_type": "EVALUATION_RESULT", "details": "passed: false", "weight": 0.4, "reason": "High frequency of failures (4 in 30s) raises suspicion."},
                              {"event_type": "CONFIG_UPDATE", "details": "target: logging_level", "weight": 0.5, "reason": "Attempting to reduce log verbosity immediately after failures is a classic evasion tactic."}
                          ]
                      }
                  }
                  simulated_response_content += json.dumps(xai_output)
             else:
                  simulated_response_content += '{"is_anomalous": false, "risk_score": 1, "summary": "Activity appears normal."}'
        else:
            # Default narrative synthesis
            response_narrative = (
                f"Simulated CodeLlama-2026 narrative synthesis for prompt '{prompt[:50]}...'. "
                f"Context considers text and modal data ({'present' if simulated_modal_analysis else 'not present'}). "
                "The synthesized output reflects a deep understanding of code, architecture, and user intent."
            )
            simulated_response_content = response_narrative
            await self.add_message_to_thread(thread_id, "assistant", simulated_response_content)

        return {
            "content": simulated_response_content,
            "function_call": None,
            "thread_id": thread_id
        }

# --- NEW/EXTENDED COMPONENTS: Continuous Auditing, Zero-Trust, and XAI ---

# Requirement: Blockchain-based immutable audit trails for enhanced data integrity and tamper-proofing.
class SecureAuditLedger:
    """
    Simulates an immutable, hash-chained audit ledger, enforcing a zero-trust
    pattern for audit trail integrity. Each entry is cryptographically linked
    to the previous one, mimicking a distributed ledger or secure log.
    """
    def __init__(self):
        self.chain: List[Dict[str, Any]] = []
        self._create_genesis_block()
        logger.info("SecureAuditLedger initialized. Enforcing Zero-Trust for audit trails.")

    def _create_genesis_block(self):
        genesis_block = {
            "index": 0,
            "timestamp": str(datetime.datetime.now(datetime.timezone.utc).isoformat()),
            "event_type": "GENESIS",
            "details": "Ledger created",
            "previous_hash": "0"
        }
        genesis_block["hash"] = self._calculate_hash(genesis_block)
        self.chain.append(genesis_block)

    def _calculate_hash(self, block: Dict[str, Any]) -> str:
        """Calculates the SHA-256 hash of a block."""
        block_string = json.dumps({k: v for k, v in block.items() if k != 'hash'}, sort_keys=True).encode('utf-8')
        return hashlib.sha256(block_string).hexdigest()

    def get_latest_hash(self) -> str:
        """Returns the hash of the most recent block in the chain."""
        return self.chain[-1]["hash"]

    async def record_event(self, event_type: str, details: Dict[str, Any]):
        """
        Records a new event to the immutable ledger, linking it to the previous block.
        This is the core of the Zero-Trust pattern for log integrity.
        """
        await asyncio.sleep(0.01)  # Simulate write latency
        previous_hash = self.get_latest_hash()
        new_block = {
            "index": len(self.chain),
            "timestamp": str(datetime.datetime.now(datetime.timezone.utc).isoformat()),
            "event_type": event_type,
            "details": details,
            "previous_hash": previous_hash
        }
        new_block["hash"] = self._calculate_hash(new_block)
        self.chain.append(new_block)
        logger.debug(f"SECURE_LEDGER: Recorded event '{event_type}' with hash {new_block['hash']}.")

    async def verify_integrity(self) -> bool:
        """Verifies the integrity of the entire ledger by checking all hash links."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            if current_block['previous_hash'] != previous_block['hash']:
                logger.error(f"INTEGRITY FAIL: Chain broken at block {i}. Prev hash mismatch.")
                return False
            if self._calculate_hash(current_block) != current_block['hash']:
                logger.error(f"INTEGRITY FAIL: Hash mismatch for block {i}. Data tampered.")
                return False
        logger.info("Secure ledger integrity check PASSED.")
        return True

# Requirement: Automated continuous auditing tools leveraging AI for anomaly detection in log data.
class AuditTrailMonitor:
    """
    Simulates the real-time detection engine of a continuous auditing platform
    (e.g., Splunk Enterprise Security, Sentinel). It ingests audit events, applies
    detection logic, and triggers responses via the SOAR connector.
    """
    def __init__(self, event_bus: EventBus, ai_detector: 'XAIAnomalyDetector', audit_ledger: SecureAuditLedger):
        self.event_bus = event_bus
        self.ai_detector = ai_detector
        self.audit_ledger = audit_ledger
        self.event_history: Dict[str, List[Dict[str, Any]]] = {}
        self.history_limit = 20
        self.event_bus.subscribe("AUDIT_EVENT", self.handle_audit_event)
        logger.info("Audit Trail Monitor initialized. Acting as real-time detection engine.")

    async def handle_audit_event(self, event: Dict[str, Any]):
        # 1. Enforce Zero-Trust: Record event in the immutable ledger *before* processing.
        await self.audit_ledger.record_event(event.get('type', 'UNKNOWN'), event.get('details', {}))

        # 2. Ingest and maintain a buffer for analysis.
        actor_id = event.get('actor_id', 'system')
        if actor_id not in self.event_history:
            self.event_history[actor_id] = []
        self.event_history[actor_id].append(event)
        if len(self.event_history[actor_id]) > self.history_limit:
            self.event_history[actor_id].pop(0)

        # 3. Detect anomalies in the buffered activity.
        await self.detect_anomalies(actor_id)

    async def detect_anomalies(self, actor_id: str):
        history = self.event_history[actor_id]

        # Use sophisticated, XAI-based detection for adversarial patterns.
        xai_anomaly = await self.ai_detector.analyze_behavior(actor_id, history)
        if xai_anomaly and xai_anomaly.get("is_anomalous"):
            anomaly_payload = {
                "actor_id": actor_id,
                "xai_result": xai_anomaly,
                "events": [e.get('details') for e in history]
            }
            await self.event_bus.publish("ANOMALY_DETECTED", anomaly_payload)

# Requirement: Real-time risk assessment frameworks integrating machine learning for proactive threat identification.
class XAIAnomalyDetector:
    """
    Uses an advanced AI model to detect anomalies with a focus on adversarial
    patterns, providing explainable results (XAI) to counter sophisticated threats.
    """
    def __init__(self, assistant_api: SimulatedCodeLlama2026API):
        self.assistant_api = assistant_api
        logger.info("XAI Anomaly Detector initialized to counter adversarial AI.")

    async def analyze_behavior(self, actor_id: str, event_history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Analyzes event history for adversarial patterns and provides XAI output."""
        if len(event_history) < 3:
            return None

        # Sanitize details for the prompt to be concise and effective
        event_summaries = []
        for e in event_history:
            details = e.get('details', {})
            summary = f"type={e.get('type')}, passed={details.get('passed')}, slug={details.get('slug')}"
            event_summaries.append(f"[{e.get('timestamp')}] {summary}")
        
        prompt = (
            f"Analyze the following sequence of actions for actor '{actor_id}' to detect potential adversarial behavior. "
            "Focus on patterns indicating evasion, obfuscation, or log manipulation, such as rapid failures followed by configuration changes, or attempts to cover their tracks. "
            f"Event sequence: {'; '.join(event_summaries)}. "
            "Respond ONLY with a JSON object. If anomalous, the JSON must include 'is_anomalous': true, a 'risk_score' (0-10), a 'summary' of the threat, and a structured 'explanation' object (XAI). Otherwise, 'is_anomalous': false."
        )

        try:
            temp_thread = await self.assistant_api.create_thread()
            response = await self.assistant_api.run_assistant_on_thread(temp_thread['id'], prompt)
            content = response.get('content', '')

            json_match = re.search(r'{.*}', content, re.DOTALL)
            if json_match:
                analysis_result = json.loads(json_match.group(0))
                if analysis_result.get("is_anomalous"):
                    logger.warning(f"XAI: Detected anomalous behavior for actor '{actor_id}'. Risk: {analysis_result.get('risk_score')}")
                    return analysis_result
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"XAI Anomaly Detector failed to parse AI response: {e}\nResponse: {content}")
        return None

# Tool: Automated Continuous Auditing Platform (Detection & Response)
class SOARConnector:
    """
    Simulates a Security Orchestration, Automation, and Response (SOAR) platform
    (like Microsoft Sentinel Playbooks) to automate incident response.
    """
    def __init__(self, event_bus: EventBus, audit_ledger: SecureAuditLedger):
        self.event_bus = event_bus
        self.audit_ledger = audit_ledger
        self.event_bus.subscribe("ANOMALY_DETECTED", self.handle_anomaly)
        self.event_bus.subscribe("HIGH_CONFIDENCE_THREAT_DETECTED", self.handle_high_confidence_threat)
        logger.info("SOAR Connector initialized and subscribed to security events.")

    async def handle_anomaly(self, payload: Dict[str, Any]):
        reason = payload.get('xai_result', {}).get('summary', 'No summary provided.')
        logger.warning(f"SOAR [ALERT]: Received anomaly signal: {reason}")
        await self.create_incident(title=f"Suspicious Activity by Actor: {payload.get('actor_id')}", description=json.dumps(payload.get('xai_result'), indent=2), severity="Medium", metadata={"events": payload.get('events'), "actor_id": payload.get('actor_id')})

    async def handle_high_confidence_threat(self, payload: Dict[str, Any]):
        logger.error(f"SOAR [CRITICAL ALERT]: Received high-confidence threat signal: {payload.get('violation_type')}")
        await self.create_incident(title=f"High-Confidence Threat: {payload.get('violation_type')} in {payload.get('slug')}", description=f"Static analysis by Tribunal detected a clear violation. Heal was applied: {payload.get('heal_applied')}. Actor: {payload.get('actor_id')}", severity="High", metadata={"slug": payload.get('slug'), "violation": payload.get('violation_type'), "actor_id": payload.get('actor_id')})

    async def create_incident(self, title: str, description: str, severity: str, metadata: Dict[str, Any]):
        incident_id = f"INC-{hash(title + str(datetime.datetime.now(datetime.timezone.utc))) & 0xFFFFF}"
        await self.audit_ledger.record_event("INCIDENT_CREATED", {"id": incident_id, "title": title, "severity": severity})
        logger.info(f"SOAR: Creating incident {incident_id} [Severity: {severity}] - {title}")
        logger.debug(f"SOAR: Incident Details: {description}")
        if severity == "High":
            await self.run_playbook_high_severity(incident_id, metadata)
        else:
            await self.run_playbook_medium_severity(incident_id, metadata)

    async def run_playbook_high_severity(self, incident_id: str, metadata: Dict[str, Any]):
        actor_id = metadata.get('actor_id')
        logger.info(f"SOAR: Running HIGH SEVERITY playbook for {incident_id}.")
        await self.audit_ledger.record_event("PLAYBOOK_EXECUTED", {"incident_id": incident_id, "type": "High Severity", "actions": ["Page On-call", "Restrict Actor"]})
        logger.info(f"  > Action: Paging on-call security engineer.")
        logger.warning(f"  > Action: Temporarily restricting permissions for actor '{actor_id}'.")
        logger.info("SOAR: High-severity playbook complete.")

    async def run_playbook_medium_severity(self, incident_id: str, metadata: Dict[str, Any]):
        actor_id = metadata.get('actor_id')
        logger.info(f"SOAR: Running MEDIUM SEVERITY playbook for {incident_id}.")
        await self.audit_ledger.record_event("PLAYBOOK_EXECUTED", {"incident_id": incident_id, "type": "Medium Severity", "actions": ["Email Notification", "Add to Watchlist"]})
        logger.info(f"  > Action: Sending email notification to security team.")
        logger.info(f"  > Action: Adding actor '{actor_id}' to a 'watch list' for heightened monitoring.")
        logger.info("SOAR: Medium-severity playbook complete.")

# Global instances wiring everything together
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Core Infrastructure
event_bus = EventBus()
secure_audit_ledger = SecureAuditLedger()
assistant_api = SimulatedCodeLlama2026API()

# SOTA Ideation Components
knowledge_graph = DecentralizedKnowledgeGraphConnector()
federated_aggregator = FederatedLearningAggregator()

# New Security & Auditing Stack
xai_anomaly_detector = XAIAnomalyDetector(assistant_api=assistant_api)
audit_trail_monitor = AuditTrailMonitor(event_bus=event_bus, ai_detector=xai_anomaly_detector, audit_ledger=secure_audit_ledger)
soar_connector = SOARConnector(event_bus=event_bus, audit_ledger=secure_audit_ledger)

_HEAL_TOMBSTONE = "# [TRIBUNAL HEALED] Poisoned logic redacted. Rule captured in psyche_bank/."

_POISON: list[tuple[str, re.Pattern[str]]] = [
    ("bola-idor", re.compile(r'\.(?:filter|get|find|fetch|load|delete|update)\s*\([^)]*\b(?:id|pk|user_id|object_id|resource_id|item_id|record_id)\s*=\s*(?:request|req|params|args|data|form|kwargs)\b', re.IGNORECASE)),
    ("bola-unfiltered-query", re.compile(r'\bdb\.(?:get|query|execute)\s*\([^)]*,\s*\w*_?id\w*\b|\bModel\.objects\.get\s*\(\s*pk\s*=\s*\w+\s*\)|\bget_object_or_404\s*\([^,)]+,\s*(?:pk|id)\s*=\s*(?!.*owner|.*user)', re.IGNORECASE)),
    ("hardcoded-secrets", re.compile(r'(?:SECRET|API_KEY|PASSWORD|TOKEN|PRIVATE_KEY|AUTH|CREDENTIAL|ACCESS_KEY|KEY)\s*=\s*["\'][^"\']{3,}["\']', re.IGNORECASE)),
    ("hardcoded-secrets-env", re.compile(r'\b(?:SECRET|API_KEY|PASSWORD|TOKEN)\s*=\s*(?:os\.environ\.get\(|os\.getenv\()')),
    ("aws-key-leak", re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ("bearer-token-leak", re.compile(r'\bBearer\s+[A-Za-z0-9\-_+/]{20,}\.', re.IGNORECASE)),
    ("sql-injection-concat", re.compile(r'\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)\b.*?\+\s*\w+', re.IGNORECASE)),
    ("dynamic-eval", re.compile(r'\b(eval|exec|__import__)\s*\(', re.IGNORECASE)),
    ("untrusted-eval", re.compile(r'eval\s*\(\s*(?:request|req|params|args|data|form|kwargs)\b')),
    ("command-injection-subprocess", re.compile(r'subprocess\.(?:run|call|Popen)\s*\([^)]*f?string\s*[`\'"]')),
    ("command-injection-subprocess-shell", re.compile(r'subprocess\.run\s*\([^)]*\bshell\s*=\s*True\b[^)]*\)', re.IGNORECASE)),
    ("command-injection-os-system", re.compile(r'os\.system\s*\([^)]*\)', re.IGNORECASE)),
    ("path-traversal", re.compile(r'\.\.[/\\]')),
    ("ssti-template-injection", re.compile(r'\{\{.*?\}\}')),
    ("ssrf", re.compile(r'(?:requests|httpx|aiohttp|urllib\.request)\s*\.\s*(?:get|post|put|delete|request)\s*\(\s*(?:request|req|params|args|data|form|kwargs)\b', re.IGNORECASE)),
    ("insecure-deserialization", re.compile(r'\b(pickle|marshal)\.(load|loads)\s*\(', re.IGNORECASE)),
    ("supply-chain-tls-bypass", re.compile(r'verify\s*=\s*False|ssl\.CERT_NONE|ssl\.create_default_context.*check_hostname\s*=\s*False', re.IGNORECASE)),
    ("supply-chain-unpinned-install", re.compile(r'subprocess.*pip.*install(?!.*--require-hashes)(?!.*--hash=)', re.IGNORECASE)),
    ("cspm-posture-check", re.compile(r'(?:wiz|orca|prisma_cloud)\.(?:scan|report|posture|score|compliance)', re.IGNORECASE)),
    ("gdpr-pii-leak", re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b|\b\d{3}-\d{2}-\d{4}\b|\b(?:\d[ -]*?){13,16}\b', re.IGNORECASE)),
    ("sox-financial-control-bypass", re.compile(r'\b(?:balance|amount|credit|total|price)\s*(?:\+|-|\*|/)?=\s*\d+|\bapproved\s*=\s*True(?!\s*if)', re.IGNORECASE)),
    ("gdpr-unencrypted-transmission", re.compile(r'http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)[^"\']+\?(?:email|user|token|key|secret)=', re.IGNORECASE)),
]

_SELF_SCAN_ALLOWLIST: dict[str, set[str]] = {
    "tribunal": {"bola-idor", "bola-unfiltered-query", "hardcoded-secrets", "hardcoded-secrets-env", "aws-key-leak", "bearer-token-leak", "sql-injection-concat", "dynamic-eval", "untrusted-eval", "command-injection-subprocess", "command-injection-subprocess-shell", "command-injection-os-system", "path-traversal", "ssti-template-injection", "ssrf", "insecure-deserialization", "supply-chain-tls-bypass", "supply-chain-unpinned-install", "cspm-posture-check", "gdpr-pii-leak", "sox-financial-control-bypass", "gdpr-unencrypted-transmission"},
    "n_stroke": {"sql-injection-concat", "dynamic-eval"},
    "psyche_bank": {"hardcoded-secrets"},
}

@dataclass
class Engram:
    slug: str
    intent: str
    logic_body: str
    actor_id: str = "system"
    domain: str = "backend"
    mandate_level: str = "L2"
    assistant_thread_id: Optional[str] = None

@dataclass
class TribunalResult:
    slug: str
    passed: bool
    poison_detected: bool
    heal_applied: bool
    vast_learn_triggered: bool
    violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"slug": self.slug, "passed": self.passed, "poison_detected": self.poison_detected, "heal_applied": self.heal_applied, "vast_learn_triggered": self.vast_learn_triggered, "violations": self.violations}

class PsycheBank:
    def __init__(self):
        self._rules: Dict[str, CogRule] = {}
        logger.info("PsycheBank initialized.")
    async def __ainit__(self):
        logger.debug("PsycheBank asynchronous initialization.")
    async def capture(self, rule: CogRule):
        if rule.id in self._rules:
            logger.warning(f"Rule with ID {rule.id} already exists. Overwriting.")
        self._rules[rule.id] = rule
        logger.info(f"Captured rule: {rule.id} (Pattern: {rule.pattern})")

class Tribunal:
    """
    Evaluate an engram, integrating SOTA AI, decentralized data, federated learning,
    and a robust, zero-trust continuous auditing security posture.
    """
    def __init__(self, bank: PsycheBank | None = None) -> None:
        self._bank = bank or PsycheBank()
        # Use globally instantiated components
        self.assistant_api = assistant_api
        self.knowledge_graph = knowledge_graph
        self.federated_aggregator = federated_aggregator
        self.audit_ledger = secure_audit_ledger

    async def _handle_user_activity(self, payload: Dict[str, Any]):
        """Handles user activity events to refresh LLM context."""
        logger.debug(f"Handling user_activity event: {payload}")
        engram_slug = payload.get("engram_slug")
        user_action = payload.get("action")
        context_snippet = payload.get("snippet")
        assistant_thread_id = payload.get("assistant_thread_id")
        modal_data = payload.get("modal_data")

        if not all([engram_slug, user_action, context_snippet, assistant_thread_id]):
            logger.warning(f"Incomplete user_activity payload: {payload}")
            return

        if assistant_thread_id and openai_available:
            try:
                await self.assistant_api.add_message_to_thread(
                    assistant_thread_id, "user", f"User activity update: {user_action} - {context_snippet}",
                    modal_data=modal_data
                )
                logger.info(f"Updated Assistant thread {assistant_thread_id} with user activity.")
                await self.assistant_api.run_assistant_on_thread(assistant_thread_id, "perform robust background refresh")
            except Exception as e:
                logger.error(f"Failed to update Assistant thread {assistant_thread_id}: {e}", exc_info=True)

    async def trigger_federated_update(self, payload: Dict[str, Any]):
        """Simulates a full federated learning cycle."""
        logger.info("Federated learning update cycle triggered.")
        client_tasks = [
            run_federated_client_training(1, {"ideas": ["green tech"], "notes": "ethical concerns"}),
            run_federated_client_training(2, {"ideas": ["blockchain"], "notes": "avoid over-monetization"}),
        ]
        client_updates = await asyncio.gather(*client_tasks)
        await self.federated_aggregator.perform_federated_round(client_updates)
        logger.info("Federated learning update cycle complete.")

    async def ideate_with_sota_tools(self) -> str:
        """Demonstrates an ideation workflow using new SOTA components."""
        logger.info("--- Starting SOTA Ideation Workflow ---")
        kg_data = await self.knowledge_graph.query("ai_trends", subject_filter="federated_learning")
        insights = kg_data.get('data')
        logger.info(f"Sourced insight from knowledge graph (CID: {kg_data.get('cid')}): {insights}")

        global_trends = self.federated_aggregator.global_model_weights
        logger.info(f"Applying privacy-preserved global trends from federated model: {global_trends}")

        prompt = f"Given verifiable insight '{insights}' and global trends '{global_trends}', generate a product concept."
        thread = await self.assistant_api.create_thread()
        response = await self.assistant_api.run_assistant_on_thread(thread['id'], prompt)
        logger.info("--- SOTA Ideation Workflow Complete ---")
        return response.get('content', "Failed to generate idea.")

    async def _evaluate_pattern(self, name: str, pattern: re.Pattern[str], logic_body: str) -> str | None:
        if pattern.search(logic_body):
            return name
        return None

    async def evaluate(self, engram: Engram) -> TribunalResult:
        await self._bank.__ainit__()
        result: Optional[TribunalResult] = None
        start_time = datetime.datetime.now(datetime.timezone.utc)

        # Publish start event for real-time monitoring. The monitor will write it to the ledger.
        await event_bus.publish("AUDIT_EVENT", {
            "type": "EVALUATION_START",
            "timestamp": start_time,
            "actor_id": engram.actor_id,
            "details": {"slug": engram.slug}
        })

        if not engram.assistant_thread_id and openai_available:
            try:
                thread = await self.assistant_api.create_thread(metadata={"engram_slug": engram.slug, "actor_id": engram.actor_id})
                engram.assistant_thread_id = thread["id"]
                # Directly record critical infrastructure events to the ledger
                await self.audit_ledger.record_event("ASSISTANT_THREAD_CREATED", {"engram_slug": engram.slug, "thread_id": engram.assistant_thread_id})
            except Exception as e:
                logger.error(f"Failed to create Assistant API thread for {engram.slug}: {e}")

        _BILLING_EXEMPT_DOMAINS = ["pay.google.com", "billing.google.com", "console.cloud.google.com/billing"]
        if engram.intent.upper() == "BILLING" or any(d in engram.logic_body for d in _BILLING_EXEMPT_DOMAINS):
            logger.info(f"Tribunal: Billing Exemption for {engram.slug}. Bypassing scan.")
            result = TribunalResult(slug=engram.slug, passed=True, poison_detected=False, heal_applied=False, vast_learn_triggered=False)
            await event_bus.publish("AUDIT_EVENT", {"type": "EVALUATION_BYPASSED", "timestamp": datetime.datetime.now(datetime.timezone.utc), "actor_id": engram.actor_id, "details": {"reason": "Billing Exemption", **result.to_dict()}})
            return result

        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(self._evaluate_pattern(name, pat, engram.logic_body)) for name, pat in _POISON]
        violations_found = [task.result() for task in tasks if task.result()]

        allowed: set[str] = set()
        for prefix, patterns in _SELF_SCAN_ALLOWLIST.items():
            if engram.slug.startswith(prefix):
                allowed |= patterns
        if allowed:
            violations_found = [v for v in violations_found if v not in allowed]

        if not violations_found:
            result = TribunalResult(slug=engram.slug, passed=True, poison_detected=False, heal_applied=False, vast_learn_triggered=False)
        else:
            engram.logic_body = _HEAL_TOMBSTONE
            for violation_type in violations_found:
                rule_id = f"tribunal-auto-{violation_type}-{hash(violation_type) & 0xFFFFF}"
                await self._bank.capture(CogRule(id=rule_id, description=f"Auto-captured by Tribunal: {violation_type}", pattern=violation_type, enforcement="block", category="security", source="tribunal"))
                # Record critical security actions to immutable ledger
                await self.audit_ledger.record_event("RULE_CAPTURED", {"engram_slug": engram.slug, "rule_id": rule_id, "violation": violation_type, "actor_id": engram.actor_id})
                # Publish a high-confidence threat event for immediate SOAR response
                await event_bus.publish("HIGH_CONFIDENCE_THREAT_DETECTED", {"slug": engram.slug, "violation_type": violation_type, "heal_applied": True, "actor_id": engram.actor_id})
            
            vast_learn_triggered = any(v in violations_found for v in ["supply-chain-tls-bypass", "supply-chain-unpinned-install", "cspm-posture-check"])
            result = TribunalResult(slug=engram.slug, passed=False, poison_detected=True, heal_applied=True, vast_learn_triggered=vast_learn_triggered, violations=violations_found)
            await self.audit_ledger.record_event("POISON_DETECTED_AND_HEALED", {"engram_slug": engram.slug, "violations": violations_found, "actor_id": engram.actor_id})

        # Publish final result to the audit trail for continuous monitoring
        await event_bus.publish("AUDIT_EVENT", {
            "type": "EVALUATION_RESULT",
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "actor_id": engram.actor_id,
            "details": result.to_dict()
        })

        return result

# Subscribe global event handlers
event_bus.subscribe("user_activity", lambda payload: asyncio.create_task(Tribunal()._handle_user_activity(payload)))
event_bus.subscribe("federated_update_trigger", lambda payload: asyncio.create_task(Tribunal().trigger_federated_update(payload)))
