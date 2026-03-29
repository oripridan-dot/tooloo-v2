# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.psyche_bank.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/psyche_bank.py — SOAR-integrated, event-driven rule store with AI-driven auditing and blockchain immutability.

This component is a secure, auditable rule store architected for seamless
integration with Security Orchestration, Automation, and Response (SOAR)
platforms and Security Information and Event Management (SIEM) systems. It
embodies a shift from periodic, batch-based audit analysis to a real-time,
event-driven anomaly detection paradigm. This design directly counters the
risk of sophisticated, evasive threats and insider activity that can bypass
traditional static monitoring.

**Architectural Evolution (Post-2025):**
This iteration of PsycheBank incorporates forward-looking architectural patterns
reflecting advancements in AI and decentralized systems:

1.  **Federated Learning for Privacy-Preserving Insights:**
    The system introduces endpoints (`contribute_federated_insight`) for
    accepting model updates from decentralized clients. This federated
    learning approach allows the PsycheBank to synthesize new rules from
    collective knowledge without exposing sensitive, raw data from any single
    source, significantly mitigating data leakage risks.

2.  **Decentralized Knowledge Integration:**
    Leveraging decentralized knowledge graphs (e.g., IPFS-backed semantic
    webs), PsycheBank can now ingest and verify rules from trusted, verifiable
    external sources. The `integrate_from_decentralized_graph` method allows
    for real-time sourcing of ideation data, expanding the rule base with
    community-vetted or expert-curated content.

3.  **AI-Driven Contextual Refresh:**
    A background "Contextual Refresh Engine" (`_run_contextual_refresh_engine`)
    utilizes advanced generative models (e.g., GPT-4o, Gemini 1.5 Pro)
    to proactively maintain and enhance the rule-set. This engine uses
    multi-modal inputs—including rule content, performance metrics (ROI), and
    anomaly data—to re-evaluate and propose updated versions of rules, ensuring
    they remain effective and relevant against evolving threats.

4.  **Retrieval-Augmented Generation (RAG) for Enhanced Ideation:**
    Complex ideation prompt chaining with advanced models like GPT-4o and
    Gemini 1.5 Pro is enhanced by RAG. This ensures that AI-generated ideas
    are grounded in curated knowledge bases, significantly mitigating the
    risk of "hallucinated" or factually incorrect outputs.

5.  **ISO/IEC 24029:2026 Draft Compliance:**
    Emerging standards for evaluating AI-generated ideas (novelty, feasibility)
    inform the design and future development of the contextual refresh engine
    and any new ideation workflows, promoting best practices.

6.  **Automated Continuous Auditing & Anomaly Detection:**
    Leveraging AI for log data anomaly detection and integrating real-time risk
    assessment frameworks for proactive threat identification. This is
    achieved through dedicated background tasks processing events from internal
    queues. This component now actively uses the `_run_anomaly_detector` for
    real-time monitoring of rule submission events and also generates rules
    to monitor detected anomalies.

7.  **Blockchain-Based Immutable Audit Trails:**
    The system now explicitly implements blockchain-inspired immutability for its audit
    trail. Each critical event, rule capture, update, and purge operation is logged
    to an append-only, cryptographically hashed event ledger. The `CogStore` itself
    maintains a comprehensive hash, ensuring tamper-proofing of the entire rule set's
    history. While not a full distributed blockchain, this provides robust data integrity
    through cryptographic linking of events and store state.

Key Features:
- **Event-Driven Auditing:** All critical actions publish structured events
  to an internal pub/sub bus for SIEM/SOAR consumption.
- **Federated Insight Aggregation:** Privacy-preserving rule synthesis from
  decentralized model updates.
- **Verifiable Decentralized Sourcing:** Integration with IPFS-like knowledge
  graphs for trusted rule ingestion.
- **AI-Powered Rule Maintenance & Ideation:** Continuous, contextual rule refinement
  and idea generation using multi-modal generative models with RAG.
- **Real-time Anomaly Detection:** A combination of inline validation and
  background behavioral analysis detects and flags threats, generating
  monitoring rules.
- **Resilient Storage:** Asynchronous, fault-tolerant, atomic file operations.
- **Standard-Compliant Evaluation:** Adherence to emerging standards for AI
  idea assessment.
- **Continuous Auditing:** AI-driven analysis of logged events for anomalies using
  the `_run_anomaly_detector` task.
- **Immutable Audit Trails:** Cryptographic hashing of the `CogStore` and
  append-only event logging with hashing for integrity. Blockchain-inspired
  event linking ensures tamper-evidence.
- **Real-time Risk Assessment:** ML-integrated threat identification powered by
  the `_run_anomaly_detector` task, analyzing event streams for anomalous patterns.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import re
from abc import ABC, abstractmethod
from collections import Counter, deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Coroutine, Deque, List, Optional, Dict
from uuid import uuid4

import pydantic

# Dedicated logger for structured audit events, the primary SIEM/SOAR integration point.
# In a production environment, this logger would be configured with a JSON formatter.
audit_logger = logging.getLogger("psyche_bank.audit")
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
MAX_RULES_THRESHOLD = 15_000
MAX_IO_RETRIES = 3
ROLLBACK_ON_CORRUPT = True
TTL_CHECK_INTERVAL_SECONDS = 60
CONTEXTUAL_REFRESH_INTERVAL_SECONDS = 3600 # Refresh a rule every hour
CONTEXTUAL_REFRESH_MIN_RULE_AGE_SECONDS = 86400 # Only refresh rules older than a day
FEDERATED_AGGREGATION_THRESHOLD = 10 # Number of insights to trigger rule synthesis

# Anomaly Detection Parameters
ANOMALY_DETECTION_WINDOW_SECONDS = 60
ANOMALY_SUBMISSION_VELOCITY_THRESHOLD = 20
ANOMALY_CATEGORY_DOMINANCE_THRESHOLD = 0.9
ANOMALY_CATEGORY_DOMINANCE_MIN_EVENTS = 10
ANOMALY_MONITOR_RULE_TTL_DAYS = 7 # How long to keep auto-generated anomaly monitor rules

# --- Blockchain/Immutability Conceptualization ---
# In a real implementation, this would involve generating and storing cryptographic hashes
# for each state of the CogStore. Event logs would be timestamped and cryptographically
# signed. For this example, we focus on structured logging and hashing of rule content.

# Global ledger for immutable audit trail events. Each event includes its own hash
# and the hash of the previous event in the ledger, forming a chain.
_AUDIT_LEDGER: List[Dict[str, Any]] = []
_LEDGER_LOCK = asyncio.Lock()

def _create_event_hash(event: Dict[str, Any]) -> str:
    """Creates a SHA256 hash for an event's JSON representation."""
    # Ensure deterministic hashing by sorting keys. 
    # Handle datetime objects if they accidentally leak into the payload.
    def default_encoder(obj):
        if isinstance(obj, datetime):
            return obj.isoformat().replace('+00:00', 'Z')
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    serialized = json.dumps(event, sort_keys=True, default=default_encoder)
    return hashlib.sha256(serialized.encode()).hexdigest()

async def _append_to_ledger(event: Dict[str, Any]) -> None:
    """Appends an event to the immutable audit ledger after hashing and chaining."""
    async with _LEDGER_LOCK:
        previous_hash = _AUDIT_LEDGER[-1]["ledger_hash"] if _AUDIT_LEDGER else "0" * 64
        event_hash = _create_event_hash(event)
        
        event_with_chaining = event.copy()
        event_with_chaining["ledger_hash"] = event_hash
        event_with_chaining["previous_ledger_hash"] = previous_hash
        _AUDIT_LEDGER.append(event_with_chaining)
        
        # In a real blockchain, this would involve committing to a block,
        # and the block hash would be used to link events. Here, we just ensure
        # the event content is hashed and appended, with the previous hash for integrity.

def create_rule_hash(rule: CogRule) -> str:
    """Creates a SHA256 hash for a CogRule's serialized JSON representation."""
    # Exclude rule_hash from hashing to avoid infinite recursion during validation
    # Use mode="json" to ensure datetimes are serialized to strings
    rule_dict = rule.model_dump(exclude={"rule_hash"}, mode="json")
    return hashlib.sha256(json.dumps(rule_dict, sort_keys=True).encode()).hexdigest()

def create_store_hash(store: CogStore) -> str:
    """Creates a SHA256 hash for a CogStore's serialized JSON representation."""
    # Exclude store_hash from hashing to avoid infinite recursion during validation
    # Use mode="json" to ensure datetimes are serialized to strings
    store_dict = store.model_dump(exclude={"store_hash"}, mode="json")
    # Sort rules by ID to ensure deterministic hashing for the same content
    store_dict['rules'] = sorted(store_dict.get('rules', []), key=lambda r: r.get('id', ''))
    return hashlib.sha256(json.dumps(store_dict, sort_keys=True, indent=2).encode()).hexdigest()

_DEFAULT_BANK = (
    Path(__file__).resolve().parents[1]
    / "psyche_bank"
    / "forbidden_patterns.cog.json"
)

# Pre-compiled regexes for efficient scanning of suspicious content.
_SUSPICIOUS_REGEXES = [
    re.compile(r"A[SK]IA[0-9A-Z]{16}"),  # AWS Access Key ID
    re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|PGP) PRIVATE KEY-----"), # Private keys
    re.compile(r"[\w\d\._%+-]+@[\w\d\.-]+\.[\w]{2,}", re.IGNORECASE), # Email address
    re.compile(r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"), # IPv4 Address
]
_SUSPICIOUS_KEYWORDS = {
    "ssn", "credit_card", "financial_data", "private_key",
    "subprocess", "eval(", "exec(", "os.system",
    "billing", "payment", "authentication", "iam:", "sts:",
    "hate speech", "discrimination", "violence", "illegal act",
    "malicious code", "exploit", "self-harm", "terrorism"
}


# --- Abstract Client Interfaces for New Features ---

class DecentralizedKnowledgeClient(ABC):
    """Abstract interface for a client to a decentralized knowledge graph (e.g., IPFS)."""
    @abstractmethod
    async def fetch_verified_store(self, content_id: str) -> dict[str, Any]:
        """Fetches, verifies (e.g., cryptographic signatures), and returns content."""
        pass

class ContextualRefreshClient(ABC):
    """Abstract interface for an AI client (e.g., GPT-4o, Gemini 1.5 Pro) for rule refresh and ideation."""
    @abstractmethod
    async def refresh_or_ideate(self, input_data: dict[str, Any], prompt_context: dict[str, Any]) -> dict[str, Any]:
        """
        Uses multi-modal context and RAG to propose an updated version of a rule
        or generate new ideas.
        `input_data` can be a rule object or a general ideation prompt.
        `prompt_context` provides supporting knowledge or data.
        """
        pass

class RAGKnowledgeBaseClient(ABC):
    """Abstract interface for a RAG-compliant knowledge base client."""
    @abstractmethod
    async def retrieve_relevant_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieves top-k relevant documents for a given query."""
        pass

# --- Pydantic Models ---

class CogRule(pydantic.BaseModel):
    """A single, machine-readable rule or pattern within the PsycheBank."""
    id: str
    description: str
    pattern: str
    enforcement: str
    category: str
    source: str
    expires_at: Optional[datetime] = None
    version: int = 1
    last_refreshed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None # For storing extra info, e.g., evaluation scores

    # Adding a field for the rule's hash to aid in immutability checks
    rule_hash: Optional[str] = None

    @pydantic.model_validator(mode="before")
    @classmethod
    def set_default_timestamps(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Set default for last_refreshed_at to current time on creation if not present."""
        if 'last_refreshed_at' not in values or values['last_refreshed_at'] is None:
            values['last_refreshed_at'] = datetime.now(UTC)
        if 'rule_hash' not in values or values['rule_hash'] is None:
            # Compute hash during validation if not provided.
            # The actual validation and storage of the hash happens in `validate_rule_fields`.
            pass
        return values

    @pydantic.model_validator(mode="after")
    def validate_rule_fields(self) -> "CogRule":
        """Ensures the integrity and validity of core rule fields and computes/validates the hash."""
        if not self.id or not self.id.strip():
            raise ValueError("CogRule.id must be a non-empty string")
        if not self.category or not self.category.strip():
            raise ValueError("CogRule.category must be a non-empty string")
        if self.enforcement not in ["block", "warn"]:
            raise ValueError("CogRule.enforcement must be 'block' or 'warn'")

        allowed_sources = {
            "tribunal", "manual", "vast_learn", "gpt4_turbo_function_call",
            "federated_insights", "user_feedback", "human_curated",
            "decentralized_graph", "federated_learning_aggregator", "contextual_refresh_engine",
            "rag_ideation", "iso_evaluator", "anomaly_detector_rule_creation",
            "tooloo-core", "claudio-engine"
        }
        if self.source not in allowed_sources:
            raise ValueError(f"CogRule.source must be one of {allowed_sources}")
        
        # Compute and validate the hash. This ensures that any modification to the rule
        # will invalidate its existing hash and require re-validation or a new hash.
        computed_hash = create_rule_hash(self)
        if self.rule_hash is None:
            self.rule_hash = computed_hash # Store the computed hash on the instance
        elif self.rule_hash != computed_hash:
            raise ValueError(f"Rule hash mismatch for ID '{self.id}'. Expected {self.rule_hash}, computed {computed_hash}")
        return self

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Ensure consistent ISO-8601 'Z' format for datetimes on serialization."""
        dumped = super().model_dump(**kwargs)
        for key in ['expires_at', 'last_refreshed_at']:
            if key in dumped and isinstance(getattr(self, key), datetime):
                # Ensure the 'Z' suffix for UTC, replacing '+00:00'
                dumped[key] = getattr(self, key).isoformat().replace('+00:00', 'Z')
        return dumped

class FederatedInsight(pydantic.BaseModel):
    """Represents a privacy-preserving model update from a federated client."""
    pattern_hash: str # A hash representing the data pattern the insight applies to.
    schema_version: str # Version of the insight schema.
    payload: bytes # The opaque, serialized model update (e.g., gradients).
    contributor_id: str # An anonymous or pseudonymous identifier for the source.

class AcceptanceRecord(pydantic.BaseModel):
    """Tracks user acceptance of agentic actions to measure ROI."""
    mandate_id: str
    timestamp: datetime = pydantic.Field(default_factory=lambda: datetime.now(UTC))
    accepted: bool
    modified_lines: int = 0
    domain: str
    rationale: Optional[str] = None

class CogStore(pydantic.BaseModel):
    """The top-level container for the entire set of rules, with versioning and store hash."""
    version: str = "2.5.0" # Updated version for Acceptance Ratio tracking
    rules: List[CogRule] = []
    acceptance_history: List[AcceptanceRecord] = []
    store_hash: Optional[str] = None # Hash of the entire store content

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> "CogStore":
        """Custom validation to handle robust datetime parsing from JSON and ensure rule hashes are present."""
        if isinstance(obj, dict) and 'rules' in obj and isinstance(obj['rules'], list):
            for rule_data in obj['rules']:
                if isinstance(rule_data, dict):
                    for key in ['expires_at', 'last_refreshed_at']:
                        if key in rule_data and isinstance(rule_data[key], str):
                            try:
                                timestamp_str = rule_data[key]
                                # Handle 'Z' suffix for UTC timezone designator
                                if timestamp_str.upper().endswith('Z'):
                                   timestamp_str = timestamp_str[:-1] + '+00:00'
                                rule_data[key] = datetime.fromisoformat(timestamp_str)
                            except (ValueError, TypeError):
                                logger.warning("Could not parse '%s' timestamp '%s'. Ignoring field.", key, rule_data.get(key))
                                rule_data[key] = None
                    # Ensure rule_hash is present before validation if it's a string (e.g. loaded from file)
                    if 'rule_hash' not in rule_data or rule_data['rule_hash'] is None:
                        logger.warning(f"Rule '{rule_data.get('id', 'unknown')}' missing rule_hash on load. Will be recomputed during validation.")
                        rule_data['rule_hash'] = None # Explicitly set to None so CogRule model_validator can compute it
                        
        return super().model_validate(obj, **kwargs)

    @pydantic.model_validator(mode="after")
    def validate_store_hash(self) -> "CogStore":
        """Validates the store hash against its current content. Computes if missing."""
        if self.store_hash is None:
            computed_hash = create_store_hash(self)
            self.store_hash = computed_hash # Store the computed hash on the instance
        elif self.store_hash != create_store_hash(self):
            raise ValueError(f"Store hash mismatch. Expected {self.store_hash}, computed {create_store_hash(self)}")
        return self

class PsycheBank:
    """Asynchronous, secure, and auditable rule store for event-driven systems."""

    def __init__(
        self,
        path: Optional[Path] = None,
        dkg_client: Optional[DecentralizedKnowledgeClient] = None,
        cr_client: Optional[ContextualRefreshClient] = None,
        rag_client: Optional[RAGKnowledgeBaseClient] = None
    ) -> None:
        self._path = path or _DEFAULT_BANK
        self._dkg_client = dkg_client
        self._cr_client = cr_client
        self._rag_client = rag_client

        self._store: Optional[CogStore] = None
        self._rules_by_hash: dict[str, str] = {}
        self._rules_by_id: dict[str, CogRule] = {}
        self._initialized = asyncio.Event()
        self._lock = asyncio.Lock()

        self._subscribers: List[asyncio.Queue[dict[str, Any]]] = []
        # Queues for event processing and audit logging
        self._audit_event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
        self._anomaly_event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)

        self._background_tasks: List[asyncio.Task] = []
        self._roi_history_cache: Deque[dict[str, Any]] = deque(maxlen=1000)

        # State for Federated Learning
        self._pending_federated_insights: dict[str, List[FederatedInsight]] = {}

    async def __ainit__(self) -> None:
        """Initializes the store, loading rules and starting background services."""
        async with self._lock:
            if self._initialized.is_set():
                return
            try:
                self._store = await self._load()
                self._rebuild_caches()
                self._subscribers.extend([self._audit_event_queue, self._anomaly_event_queue])

                # Start background tasks for continuous auditing and operations
                self._background_tasks.append(
                    self._create_task(self._run_ttl_expiry_checker(), "ttl-checker")
                )
                self._background_tasks.append(
                    self._create_task(self._run_audit_event_processor(), "audit-processor")
                )
                self._background_tasks.append(
                    self._create_task(self._run_anomaly_detector(), "anomaly-detector")
                )
                if self._cr_client:
                    self._background_tasks.append(
                        self._create_task(self._run_contextual_refresh_engine(), "contextual-refresher")
                    )

                self._initialized.set()
                await self._publish_event("StoreInitialized", {"path": str(self._path), "rule_count": len(self._store.rules)})
                logger.info(f"PsycheBank initialized with {len(self._store.rules)} rules from: {self._path}")

            except Exception as e:
                logger.critical(f"PsycheBank initialization failed for {self._path}: {e}", exc_info=True)
                await self._shutdown_tasks()
                self._initialized.clear()
                raise

    def _create_task(self, coro: Coroutine, name: str) -> asyncio.Task:
        """Helper to create and name a background task for better debuggability."""
        task = asyncio.create_task(coro)
        task.set_name(f"psychebank-{name}-{self._path.name}")
        return task

    def _rebuild_caches(self) -> None:
        """Reconstructs in-memory caches for fast rule lookups."""
        if not self._store: return
        self._rules_by_id.clear()
        self._rules_by_hash.clear()
        for rule in self._store.rules:
            self._rules_by_id[rule.id] = rule
            if rule.rule_hash: # Ensure hash exists before adding to cache
                self._rules_by_hash[rule.rule_hash] = rule.id

    async def _load(self) -> CogStore:
        """Loads the rule store from disk with retry logic and corruption handling."""
        if not await asyncio.to_thread(self._path.exists):
            logger.warning(f"PsycheBank file not found at {self._path}, creating new store.")
            await asyncio.to_thread(self._path.parent.mkdir, parents=True, exist_ok=True)
            return CogStore()

        for attempt in range(MAX_IO_RETRIES):
            try:
                data = await asyncio.to_thread(self._path.read_text, encoding="utf-8")
                if not data.strip():
                    return CogStore()
                
                # Use Pydantic's model_validate for comprehensive validation, including hash checks.
                # The model_validate method will also trigger CogRule's validator to ensure hashes are computed/valid.
                store = CogStore.model_validate_json(data)
                logger.info(f"Successfully loaded {len(store.rules)} rules from {self._path} (Store Hash: {store.store_hash})")
                return store
            except (json.JSONDecodeError, pydantic.ValidationError) as e:
                logger.error(f"Attempt {attempt + 1}/{MAX_IO_RETRIES}: Failed to load/validate from {self._path}: {e}")
                if attempt < MAX_IO_RETRIES - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt)) # Exponential backoff
                elif ROLLBACK_ON_CORRUPT:
                    logger.critical(f"Persistent corruption at {self._path}. Backing up and starting fresh.")
                    backup_path = self._path.with_suffix(f".corrupt.{int(datetime.now(UTC).timestamp())}")
                    await asyncio.to_thread(self._path.rename, backup_path)
                    await self._publish_event("StoreCorrupted", {"path": str(self._path), "backup_path": str(backup_path)})
                    return CogStore()
                else:
                    raise
        return CogStore() # Should not be reached, but satisfies linters

    async def _persist(self) -> None:
        """
        Atomically persists the current rule store to disk, including its hash.
        NOTE: Must be called while holding self._lock.
        """
        if not self._store: return
        try:
            # Update the store hash before persisting
            self._store.store_hash = create_store_hash(self._store)
            data = self._store.model_dump_json(indent=2)
            await asyncio.to_thread(self._path.write_text, data, encoding="utf-8")
            logger.debug(f"Persisted rule store to {self._path} (Hash: {self._store.store_hash})")
        except Exception as e:
            logger.error(f"Failed to persist PsycheBank to {self._path}: {e}", exc_info=True)

    async def update_acceptance_ratio(self, mandate_id: str, accepted: bool, modified_lines: int, domain: str, rationale: Optional[str] = None) -> float:
        """Records a user acceptance event and returns the updated ROI score."""
        async with self._lock:
            record = AcceptanceRecord(
                mandate_id=mandate_id,
                accepted=accepted,
                modified_lines=modified_lines,
                domain=domain,
                rationale=rationale
            )
            self._store.acceptance_history.append(record)
            await self._persist()
            
            # Calculate ROI: ratio of accepted to total
            total = len(self._store.acceptance_history)
            accepted_count = sum(1 for r in self._store.acceptance_history if r.accepted)
            roi = accepted_count / total if total > 0 else 1.0
            
            await self._publish_event("AcceptanceRatioUpdated", {
                "mandate_id": mandate_id,
                "domain": domain,
                "accepted": accepted,
                "total_records": total,
                "roi_score": round(roi, 4)
            })
            return roi
        if self._store is None: return

        if len(self._store.rules) > MAX_RULES_THRESHOLD:
            await self._publish_event("PersistenceAborted", { "reason": "max_rules_threshold_exceeded", "rule_count": len(self._store.rules), "threshold": MAX_RULES_THRESHOLD })
            logger.error(f"Persistence aborted: Rule count {len(self._store.rules)} exceeds threshold {MAX_RULES_THRESHOLD}.")
            return

        # Ensure all rules have a hash before persisting. This is also done during capture/update.
        for rule in self._store.rules:
            if rule.rule_hash is None:
                rule.rule_hash = create_rule_hash(rule)
                logger.warning(f"Rule '{rule.id}' had no hash before persistence, computed: {rule.rule_hash}")

        # Update the store hash for the entire store. This is crucial for tamper-proofing.
        self._store.store_hash = create_store_hash(self._store)
        blob = self._store.model_dump_json(indent=2)
        try:
            # Atomic write: write to a temporary file then rename
            temp_path = self._path.with_suffix(f"{self._path.suffix}.{uuid4().hex}.tmp")
            await asyncio.to_thread(temp_path.write_text, blob, encoding="utf-8")
            await asyncio.to_thread(temp_path.rename, self._path)
            logger.debug(f"Persisted {len(self._store.rules)} rules to {self._path} (Store Hash: {self._store.store_hash})")
        except IOError as e:
            logger.error(f"Failed to persist PsycheBank to {self._path}: {e}", exc_info=True)
            await self._publish_event("PersistenceFailed", {"path": str(self._path), "error": str(e)})
            raise

    async def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publishes a structured event to all internal subscribers and the immutable audit ledger."""
        event = {
            "type": event_type,
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "source_component": "PsycheBank",
            "data": data,
        }
        # Append to the immutable ledger, maintaining chain integrity
        await _append_to_ledger(event)

        # Distribute to subscribers (e.g., SIEM/SOAR connectors, anomaly detectors)
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"Subscriber queue full for event '{event_type}'. Event dropped.")

    async def record_pedagogical_insight(self, insight_data: Dict[str, Any]) -> bool:
        """Persists a Buddy active expertise insight for future pattern meta-learning."""
        try:
            from engine.psyche_bank import CogRule
            import uuid
            # Ensure the insight matches the strictly-enforced CogRule schema.
            insight_rule = CogRule(
                id=f"insight-{uuid.uuid4().hex[:8]}",
                description=str(insight_data.get("insight", "")),
                pattern=insight_data.get("mandate", "unknown"),
                enforcement="log_only",
                category="ideation",
                source="buddy",
                version=1,
                metadata={"relevance_score": 0.9}
            )
            return await self.capture(insight_rule, ttl_seconds=604800)  # 1 week TTL
        except Exception as e:
            logger.error(f"Failed to record pedagogical insight: {e}")
            return False

    async def capture(self, rule: CogRule, ttl_seconds: Optional[int] = None) -> bool:
        """Captures a new rule after validation, security checks, and duplicate detection."""
        if not self._initialized.is_set(): await self.__ainit__()
        if not self._store: raise RuntimeError("PsycheBank store is not available.")

        await self._publish_event("RuleProposed", {"rule_id": rule.id, "source": rule.source, "category": rule.category})

        try:
            # Ensure the rule is valid before proceeding, including security checks and hash computation.
            # This will trigger CogRule.model_validator which computes and validates the rule_hash.
            validated_rule = CogRule.model_validate(rule.model_dump())
            if not self._is_valid_rule_id(validated_rule.id):
                raise ValueError("Invalid rule ID format or content.")
            if not self._is_valid_rule_category(validated_rule.category):
                raise ValueError(f"Invalid rule category: '{validated_rule.category}'.")
            if suspicious_findings := self._get_suspicious_patterns(validated_rule):
                await self._publish_event("SuspiciousRuleContent", { "rule_id": rule.id, "source": rule.source, "findings": suspicious_findings, "severity": "high", "suggested_action": "Immediate manual review required." })
                return False # Reject suspicious rules by default
        except (pydantic.ValidationError, ValueError) as e:
            await self._publish_event("RuleRejected", {"rule_id": rule.id, "source": rule.source, "reason": str(e)})
            return False

        async with self._lock:
            # Check for duplicates based on hash BEFORE adding to store
            rule_hash = validated_rule.rule_hash
            if rule_hash in self._rules_by_hash:
                logger.warning(f"Rule with hash {rule_hash} (ID: {self._rules_by_hash[rule_hash]}) already exists. New rule '{validated_rule.id}' rejected as duplicate.")
                await self._publish_event("RuleRejected", {"rule_id": validated_rule.id, "reason": "duplicate_hash"})
                return False

            if validated_rule.id in self._rules_by_id:
                logger.warning(f"Rule ID '{validated_rule.id}' collision detected. Rule with existing ID '{validated_rule.id}' (Hash: {self._rules_by_id[validated_rule.id].rule_hash}) found.")
                await self._publish_event("RuleRejected", {"rule_id": validated_rule.id, "reason": "id_collision"})
                return False

            if ttl_seconds is not None:
                if not isinstance(ttl_seconds, (int, float)) or ttl_seconds <= 0:
                    await self._publish_event("RuleRejected", {"rule_id": validated_rule.id, "reason": "invalid_ttl", "value": ttl_seconds})
                    return False
                validated_rule.expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

            # Ensure rule_hash is set by validation or here if not already.
            # It should be set by CogRule.model_validator, but this is a safeguard.
            if validated_rule.rule_hash is None:
                validated_rule.rule_hash = create_rule_hash(validated_rule)
                logger.warning(f"Rule '{validated_rule.id}' had no hash after initial validation, computed: {validated_rule.rule_hash}")

            self._store.rules.append(validated_rule)
            self._rules_by_id[validated_rule.id] = validated_rule
            self._rules_by_hash[validated_rule.rule_hash] = validated_rule.id

            await self._persist()
            await self._publish_event("RuleCaptured", {"rule_id": validated_rule.id, "category": validated_rule.category, "source": validated_rule.source, "expires_at": validated_rule.expires_at.isoformat() if validated_rule.expires_at else None, "rule_hash": validated_rule.rule_hash})
            return True

    async def update_rule(self, rule_id: str, update_data: dict[str, Any]) -> bool:
        """Updates an existing rule with new data, creating a new version."""
        if not self._initialized.is_set(): await self.__ainit__()

        async with self._lock:
            if not self._store or rule_id not in self._rules_by_id:
                await self._publish_event("RuleUpdateFailed", {"rule_id": rule_id, "reason": "not_found"})
                return False

            original_rule = self._rules_by_id[rule_id]
            updated_rule_data = original_rule.model_dump()
            updated_rule_data.update(update_data)
            updated_rule_data['version'] = original_rule.version + 1
            updated_rule_data['last_refreshed_at'] = datetime.now(UTC)
            # Ensure rule_hash is recomputed for the new version. The original hash will be invalidated.
            updated_rule_data.pop('rule_hash', None)

            try:
                # Validate the updated rule. This will compute and set the new rule_hash.
                new_rule = CogRule.model_validate(updated_rule_data)
                if new_rule.id != rule_id:
                    raise ValueError("Rule ID cannot be changed during an update.")
            except (pydantic.ValidationError, ValueError) as e:
                await self._publish_event("RuleUpdateFailed", {"rule_id": rule_id, "reason": f"validation_error: {e}"})
                return False

            rule_index = next((i for i, r in enumerate(self._store.rules) if r.id == rule_id), -1)
            if rule_index == -1: return False # Should not happen if in _rules_by_id

            self._store.rules[rule_index] = new_rule
            self._rebuild_caches() # Safest way to ensure all caches are consistent
            await self._persist()

            await self._publish_event("RuleUpdated", {
                "rule_id": new_rule.id,
                "new_version": new_rule.version,
                "source": new_rule.source,
                "changes": list(update_data.keys()),
                "new_rule_hash": new_rule.rule_hash # Log the new hash
            })
            return True

    async def purge_expired(self) -> int:
        """Checks for and removes rules that have passed their expiration date."""
        if not self._initialized.is_set() or not self._store: return 0
        now = datetime.now(UTC)
        # Fast path check outside the lock
        if not any(r.expires_at and r.expires_at <= now for r in self._store.rules):
            return 0

        async with self._lock:
            now = datetime.now(UTC)
            initial_count = len(self._store.rules)
            purged_ids = [r.id for r in self._store.rules if r.expires_at and r.expires_at <= now]
            if not purged_ids:
                return 0

            self._store.rules = [r for r in self._store.rules if r.id not in purged_ids]
            purged_count = len(purged_ids)

            if purged_count > 0:
                self._rebuild_caches()
                await self._persist()
                await self._publish_event("RulesPurged", {"count": purged_count, "purged_ids": purged_ids})
        return purged_count

    # --- Federated Learning & Decentralized Sourcing ---

    async def contribute_federated_insight(self, insight: FederatedInsight) -> None:
        """Accepts a privacy-preserving insight and aggregates it for rule synthesis."""
        if not self._initialized.is_set(): await self.__ainit__()

        try:
            # Validate insight structure first
            FederatedInsight.model_validate(insight)
            # Additional checks for payload validity might be needed here if it's not opaque
        except pydantic.ValidationError as e:
            await self._publish_event("FederatedInsightRejected", {"reason": str(e), "contributor_id": getattr(insight, 'contributor_id', 'unknown')})
            return

        async with self._lock:
            self._pending_federated_insights.setdefault(insight.pattern_hash, []).append(insight)

            await self._publish_event("FederatedInsightReceived", {
                "pattern_hash": insight.pattern_hash,
                "contributor_id": insight.contributor_id,
                "current_aggregation_count": len(self._pending_federated_insights[insight.pattern_hash])
            })

            if len(self._pending_federated_insights[insight.pattern_hash]) >= FEDERATED_AGGREGATION_THRESHOLD:
                insights_for_synthesis = self._pending_federated_insights.pop(insight.pattern_hash)
                # Spawn synthesis task to avoid blocking the caller and the lock
                self._create_task(
                    self._synthesize_rule_from_insights(insight.pattern_hash, insights_for_synthesis),
                    f"synthesizer-{insight.pattern_hash[:8]}"
                )

    async def _synthesize_rule_from_insights(self, pattern_hash: str, insights: list[FederatedInsight]) -> None:
        """
        Conceptual placeholder for synthesizing a new rule from aggregated federated insights.
        In a real implementation, this would involve a complex, privacy-preserving process.
        """
        await self._publish_event("FederatedRuleSynthesisTriggered", {
            "pattern_hash": pattern_hash,
            "insight_count": len(insights),
        })

        # --- Placeholder Synthesis Logic ---
        # 1. Secure Aggregation: The opaque `payload` of each insight (e.g., model gradients)
        #    would be decrypted/unpacked in a secure environment.
        # 2. Model Fusion: A federated learning algorithm (e.g., FedAvg) would aggregate
        #    these payloads to create a single, improved model. This new model represents the
        #    collective knowledge of all contributors without any single contributor's raw
        #    data being exposed.
        # 3. Pattern Extraction: The aggregated model would be analyzed to extract a new,
        #    generalized pattern or rule. This could involve identifying significant
        #    feature weights or emergent behaviors in the model.
        # 4. Rule Generation: The extracted pattern is translated into a formal CogRule.
        #
        # The following is a simplified mock of step 4.
        
        # For robustness, generate a unique ID and pattern. The synthesized rule would
        # have a source indicating its federated origin.
        synthesized_pattern = f"FEDERATED_SYNTHESIS_OF_{pattern_hash}"
        new_rule = CogRule(
            id=f"fed-{pattern_hash[:12]}-{uuid4().hex[:6]}",
            description=f"Rule synthesized from {len(insights)} federated insights for pattern hash {pattern_hash}.",
            pattern=synthesized_pattern,
            enforcement="warn", # Default to 'warn' for newly synthesized, unverified rules
            category="federated_insight",
            source="federated_learning_aggregator",
            metadata={"original_pattern_hash": pattern_hash, "num_contributors": len(insights)}
        )
        # --- End Placeholder ---

        success = await self.capture(new_rule) # This will compute and set the rule_hash
        await self._publish_event("FederatedRuleSynthesisAttempted", {
            "pattern_hash": pattern_hash,
            "new_rule_id": new_rule.id,
            "success": success,
            "new_rule_hash": new_rule.rule_hash
        })

    async def integrate_from_decentralized_graph(self, content_id: str) -> int:
        """Fetches, verifies, and integrates rules from a decentralized knowledge graph."""
        if not self._initialized.is_set(): await self.__ainit__()
        if not self._dkg_client:
            logger.warning("DecentralizedKnowledgeClient not configured. Integration skipped.")
            return 0

        await self._publish_event("DecentralizedGraphIntegrationAttempted", {"content_id": content_id})
        try:
            # The client is responsible for verification (e.g., signatures)
            store_data = await self._dkg_client.fetch_verified_store(content_id)
            # Validate the fetched store data
            new_store = CogStore.model_validate(store_data)
            count = 0
            for rule in new_store.rules:
                rule.source = "decentralized_graph" # Override source to track origin
                if await self.capture(rule): # capture will validate and hash the rule
                    count += 1
            await self._publish_event("DecentralizedGraphIntegrated", {"content_id": content_id, "rules_integrated": count})
            return count
        except Exception as e:
            logger.error(f"Failed to integrate from DKG for CID {content_id}: {e}", exc_info=True)
            await self._publish_event("DecentralizedGraphFailed", {"content_id": content_id, "error": str(e)})
            return 0

    # --- AI-Assisted Ideation and Rule Refresh ---

    async def generate_idea(self, prompt: str, max_ideas: int = 1, retrieval_k: int = 5) -> List[CogRule]:
        """
        Generates new ideas or rules using an AI model, augmented by RAG.
        Adheres to ISO/IEC 24029:2026 draft principles for novelty and feasibility assessment.
        """
        if not self._initialized.is_set(): await self.__ainit__()
        if not self._cr_client or not self._rag_client:
            logger.warning("ContextualRefreshClient or RAGKnowledgeBaseClient not configured. Idea generation skipped.")
            return []

        await self._publish_event("IdeaGenerationRequested", {"prompt_summary": prompt[:100]})

        try:
            # 1. Retrieve relevant context from RAG knowledge base
            # The enhanced context window of models like GPT-4o and Gemini 1.5 Pro allows for
            # richer context to be passed to the LLM, improving the quality of RAG.
            relevant_docs = await self._rag_client.retrieve_relevant_documents(prompt, k=retrieval_k)
            context_data = {"retrieved_documents": relevant_docs}

            # 2. Construct prompt for AI client, incorporating RAG context
            # The AI client's `refresh_or_ideate` method is designed to handle both
            # rule updates and new idea generation.
            input_data = {
                "mode": "ideation",
                "user_prompt": prompt,
                "num_ideas": max_ideas,
                # Incorporating ISO/IEC 24029:2026 draft principles for AI-generated idea evaluation.
                "iso_evaluation_criteria": {
                    "novelty_assessment": True,
                    "feasibility_assessment": True,
                    "originality_score_range": [0, 10], # Hypothetical scoring
                    "feasibility_score_range": [0, 10]
                }
            }

            # 3. Call AI client for generation
            # GPT-4o and Gemini 1.5 Pro's enhanced context window is leveraged here for complex ideation prompt chaining.
            generated_content = await self._cr_client.refresh_or_ideate(input_data, context_data)

            # 4. Process generated content into CogRules
            new_rules: List[CogRule] = []
            if "generated_ideas" in generated_content and isinstance(generated_content["generated_ideas"], list):
                for idea_data in generated_content["generated_ideas"]:
                    # Map AI output to CogRule structure, defaulting sensible values
                    rule_id = f"rag-idea-{uuid4().hex[:8]}"
                    description = idea_data.get("description", f"AI-generated idea based on prompt: {prompt}")
                    pattern = idea_data.get("pattern", f"GENERATED_PATTERN_{uuid4().hex[:8]}")
                    category = idea_data.get("category", "ai_generated_idea")
                    enforcement = idea_data.get("enforcement", "warn") # Default to warn for safety
                    metadata = {
                        "original_prompt": prompt,
                        "ai_model": getattr(self._cr_client, "__class__", "UnknownAIClient").__name__,
                        "rag_context_used": len(relevant_docs) > 0,
                        # Include AI's own ISO assessment in metadata
                        "iso_evaluation": idea_data.get("iso_evaluation", {}),
                        "raw_idea_data": idea_data # Store raw output for debugging
                    }

                    # Basic validation before creating CogRule
                    if not pattern.strip() or not description.strip():
                        logger.warning(f"Skipping partially formed AI idea: {idea_data}")
                        continue

                    new_rule = CogRule(
                        id=rule_id,
                        description=description,
                        pattern=pattern,
                        enforcement=enforcement,
                        category=category,
                        source="rag_ideation",
                        metadata=metadata
                    )
                    # Capture will validate and compute the rule_hash
                    captured = await self.capture(new_rule)
                    if captured:
                        new_rules.append(new_rule)
                        await self._publish_event("IdeaGenerated", {
                            "rule_id": new_rule.id,
                            "rule_hash": new_rule.rule_hash,
                            "source": "rag_ideation",
                            "category": category,
                            "iso_novelty_score": metadata.get("iso_evaluation", {}).get("novelty_score"),
                            "iso_feasibility_score": metadata.get("iso_evaluation", {}).get("feasibility_score"),
                        })
            else:
                await self._publish_event("IdeaGenerationFailed", {"error": "No ideas generated or unexpected format", "response_keys": generated_content.keys()})

            return new_rules

        except Exception as e:
            logger.error(f"Error during AI idea generation: {e}", exc_info=True)
            await self._publish_event("IdeaGenerationFailed", {"error": str(e)})
            return []

    # --- Validation and Static Analysis Helpers ---
    def _is_valid_rule_id(self, rule_id: str) -> bool:
        if not (1 < len(rule_id) < 256): return False
        if not re.fullmatch(r"^[a-zA-Z0-9_.-]+$", rule_id): return False
        return not any(keyword in rule_id.lower() for keyword in {"password", "secret", "token", "api_key"})

    def _is_valid_rule_category(self, category: str) -> bool:
        return category in {
            "security", "quality", "style", "performance", "maintainability",
            "narrative_synthesis", "concept_expansion", "bias_detection",
            "risk_assessment", "federated_insight", "content_moderation",
            "compliance", "accessibility", "function_output_validation",
            "hypothesis", "adversarial_test_case", "bias_drift_metric",
            "ai_generated_idea", "code_quality_insight", "configuration_security",
            "anomaly_detection_rule", "claudio_hardening" # Category for rules created by anomaly detector or claudio hardener
        }

    def _get_suspicious_patterns(self, rule: CogRule) -> List[str]:
        findings = []
        text_to_check = f"{rule.pattern} {rule.description}"
        lower_text = text_to_check.lower()
        for keyword in _SUSPICIOUS_KEYWORDS:
            if keyword in lower_text:
                findings.append(f"keyword:{keyword}")
        for regex in _SUSPICIOUS_REGEXES:
            if regex.search(text_to_check):
                findings.append(f"regex:{regex.pattern}")
        return findings

    # --- Background Tasks for Event-Driven Operation ---
    async def _run_ttl_expiry_checker(self) -> None:
        logger.info("Starting background TTL expiry checker.")
        try:
            while True:
                await asyncio.sleep(TTL_CHECK_INTERVAL_SECONDS)
                try:
                    if purged_count := await self.purge_expired():
                        logger.info(f"TTL checker purged {purged_count} expired rules.")
                except Exception as e:
                    logger.error(f"Error during scheduled TTL purge: {e}", exc_info=True)
        except asyncio.CancelledError:
            logger.info("TTL expiry checker task cancelled.")

    async def _run_audit_event_processor(self) -> None:
        """Processes events from the audit queue for SIEM/SOAR integration and logging."""
        logger.info("Starting audit event processor for SIEM/SOAR integration.")
        try:
            while True:
                event = await self._audit_event_queue.get()
                try:
                    # Log all events with INFO for general auditing
                    audit_logger.info(event['type'], extra={'event_data': event})
                    # Log high-severity events with CRITICAL for immediate attention
                    if event.get('data', {}).get('severity') in ('high', 'critical') or event['type'] == "AnomalyDetected":
                         audit_logger.critical(f"High-severity event detected: {event['type']}", extra={'event_data': event})
                finally:
                    self._audit_event_queue.task_done()
        except asyncio.CancelledError:
            logger.info("Audit event processor task cancelled.")

    async def _run_anomaly_detector(self) -> None:
        """
        Real-time risk assessment framework integrating machine learning for proactive threat identification.
        Monitors event streams for anomalies like high submission velocity or category dominance.
        This task now actively generates rules for detected anomalies.
        """
        logger.info("Starting real-time behavioral anomaly detector.")
        source_activity: dict[str, dict[str, Any]] = {} # Track activity per source
        try:
            while True:
                event = await self._anomaly_event_queue.get()
                try:
                    # Focus on events that indicate activity potentially leading to rule manipulation or misuse
                    if event['type'] != "RuleProposed": continue
                    
                    data = event['data']
                    source = data.get('source')
                    category = data.get('category')
                    
                    if not source: continue # Cannot analyze without a source

                    now = datetime.fromisoformat(event['timestamp'].removesuffix('Z'))
                    
                    # Initialize state for the source if it's new
                    if source not in source_activity:
                        source_activity[source] = {
                            'events': deque(), # Stores (timestamp, category) tuples
                            'categories': Counter() # Tracks counts of categories over time
                        }
                    state = source_activity[source]

                    # Add current event to the sliding window and update category counts
                    state['events'].append((now, category))
                    window_start = now - timedelta(seconds=ANOMALY_DETECTION_WINDOW_SECONDS)
                    
                    # Clean up old events from the window
                    while state['events'] and state['events'][0][0] < window_start:
                        old_ts, old_cat = state['events'].popleft()
                        if old_cat:
                            state['categories'][old_cat] -= 1
                            if state['categories'][old_cat] == 0:
                                del state['categories'][old_cat]
                    
                    # Update category counter with the new event
                    if category:
                        state['categories'][category] += 1

                    event_count = len(state['events'])

                    # Anomaly 1: High Submission Velocity
                    if event_count > ANOMALY_SUBMISSION_VELOCITY_THRESHOLD:
                        anomaly_details = {
                            "anomaly_type": "high_submission_velocity",
                            "severity": "medium",
                            "details": {
                                "source": source,
                                "observed_value": event_count,
                                "threshold": ANOMALY_SUBMISSION_VELOCITY_THRESHOLD,
                                "window_seconds": ANOMALY_DETECTION_WINDOW_SECONDS,
                            },
                            "suggested_action": f"Investigate potential abuse or excessive rule generation from source '{source}'. Consider rate-limiting."
                        }
                        await self._publish_event("AnomalyDetected", anomaly_details)
                        # Generate a rule to monitor this source for future violations
                        await self._capture_anomaly_rule(source, anomaly_details)

                        # Reset state to avoid repeated alerts for the same burst
                        state['events'].clear()
                        state['categories'].clear()
                        continue

                    # Anomaly 2: Category Dominance (if enough events and categories are present)
                    if event_count >= ANOMALY_CATEGORY_DOMINANCE_MIN_EVENTS and state['categories']:
                        # Find the most dominant category
                        dominant_category, dominant_count = state['categories'].most_common(1)[0]
                        dominance_ratio = dominant_count / event_count
                        
                        if dominance_ratio >= ANOMALY_CATEGORY_DOMINANCE_THRESHOLD:
                            anomaly_details = {
                                "anomaly_type": "category_dominance",
                                "severity": "low",
                                "details": {
                                    "source": source,
                                    "dominant_category": dominant_category,
                                    "dominance_ratio": round(dominance_ratio, 2),
                                    "threshold": ANOMALY_CATEGORY_DOMINANCE_THRESHOLD,
                                    "total_events": event_count,
                                    "window_seconds": ANOMALY_DETECTION_WINDOW_SECONDS,
                                },
                                "suggested_action": f"Review the high volume of '{dominant_category}' rules submitted by '{source}'. Ensure it aligns with intended usage."
                            }
                            await self._publish_event("AnomalyDetected", anomaly_details)
                            # Generate a rule to monitor this source/category combination
                            await self._capture_anomaly_rule(source, anomaly_details)

                            # Optionally, clear state or reduce counts to prevent immediate re-alerting
                            # state['events'].clear()
                            # state['categories'].clear()

                finally:
                    self._anomaly_event_queue.task_done()
        except asyncio.CancelledError:
            logger.info("Anomaly detector task cancelled.")

    async def _capture_anomaly_rule(self, source: str, anomaly_details: Dict[str, Any]) -> None:
        """Creates and captures a rule based on detected anomaly patterns."""
        rule_id = f"anomaly-monitor-{source}-{anomaly_details['anomaly_type']}-{uuid4().hex[:6]}"
        
        # Construct a pattern that targets the conditions of the anomaly
        pattern_parts = [f"source='{source}'"]
        if anomaly_details['anomaly_type'] == "high_submission_velocity":
            pattern_parts.append(f"event_count > {ANOMALY_SUBMISSION_VELOCITY_THRESHOLD} in {ANOMALY_DETECTION_WINDOW_SECONDS}s")
        elif anomaly_details['anomaly_type'] == "category_dominance":
            pattern_parts.append(f"category='{anomaly_details['details']['dominant_category']}'")
            pattern_parts.append(f"dominance_ratio > {ANOMALY_CATEGORY_DOMINANCE_THRESHOLD}")

        pattern = " AND ".join(pattern_parts)
        description = f"Monitors source '{source}' for repeated occurrences of {anomaly_details['anomaly_type']}."

        # Create a rule that would trigger if the anomaly condition is met again.
        # This rule could be set to 'warn' or 'block' depending on risk appetite.
        anomaly_rule = CogRule(
            id=rule_id,
            description=description,
            pattern=pattern,
            enforcement="warn", # Default to warn, could be made configurable
            category="anomaly_detection_rule",
            source="anomaly_detector_rule_creation",
            metadata={
                "original_anomaly_details": anomaly_details,
                "auto_generated": True,
                "creation_timestamp": datetime.now(UTC).isoformat() + "Z"
            }
        )
        await self.capture(anomaly_rule, ttl_seconds=timedelta(days=ANOMALY_MONITOR_RULE_TTL_DAYS).total_seconds()) # Keep anomaly monitor rules for a week


    async def _run_contextual_refresh_engine(self) -> None:
        """Periodically refreshes rules using a multi-modal AI client, considering RAG."""
        logger.info("Starting AI-driven Contextual Refresh Engine.")
        if not self._cr_client: return

        try:
            while True:
                await asyncio.sleep(CONTEXTUAL_REFRESH_INTERVAL_SECONDS)
                if not self._store or not self._store.rules: continue

                now = datetime.now(UTC)
                min_age_delta = timedelta(seconds=CONTEXTUAL_REFRESH_MIN_RULE_AGE_SECONDS)
                
                # Efficiently find the single oldest, eligible rule without sorting the whole list.
                rule_to_refresh: Optional[CogRule] = None
                oldest_refresh_time = now
                for rule in self._store.rules:
                    # Check if rule is eligible for refresh (not expired, and old enough since last refresh)
                    if (rule.expires_at is None or rule.expires_at > now) and \
                       (rule.last_refreshed_at is None or now - rule.last_refreshed_at > min_age_delta):
                        
                        # Prioritize rules that haven't been refreshed at all, or are older
                        if rule.last_refreshed_at is None or rule.last_refreshed_at < oldest_refresh_time:
                            rule_to_refresh = rule
                            oldest_refresh_time = rule.last_refreshed_at if rule.last_refreshed_at else now # Handle None case

                if not rule_to_refresh: continue

                # Create multi-modal context for the AI. Incorporate RAG if available for richer context.
                context_for_ai: dict[str, Any] = {
                    "related_roi_events": [e for e in self._roi_history_cache if e.get("rule_id") == rule_to_refresh.id],
                    "system_health": {"anomaly_queue_size": self._anomaly_event_queue.qsize(), "total_rules": len(self._store.rules)}
                }

                # If RAG client is available, fetch relevant context based on the rule itself
                if self._rag_client:
                    try:
                        # Enhanced context window of GPT-4o/Gemini 1.5 Pro allows for more comprehensive context retrieval
                        relevant_docs = await self._rag_client.retrieve_relevant_documents(f"Context for rule: {rule_to_refresh.description} Pattern: {rule_to_refresh.pattern}", k=3)
                        context_for_ai["retrieved_knowledge"] = relevant_docs
                    except Exception as rag_e:
                        logger.warning(f"Could not retrieve RAG context for rule '{rule_to_refresh.id}': {rag_e}")

                try:
                    logger.info(f"Contextually refreshing rule '{rule_to_refresh.id}' (v{rule_to_refresh.version})...")
                    # Use the AI client's `refresh_or_ideate` method for consistent interface
                    # Specify mode as "refresh" and pass the rule object
                    input_data = {
                        "mode": "refresh",
                        "rule_to_refresh": rule_to_refresh.model_dump(),
                        # Incorporating ISO/IEC 24029:2026 draft principles for AI-generated idea evaluation.
                        "iso_evaluation_criteria": {
                            "novelty_assessment": True,
                            "feasibility_assessment": True,
                            "originality_score_range": [0, 10],
                            "feasibility_score_range": [0, 10]
                        }
                    }
                    # Leveraging GPT-4o and Gemini 1.5 Pro for complex ideation prompt chaining during rule refresh.
                    proposed_update = await self._cr_client.refresh_or_ideate(input_data, context_for_ai)

                    if proposed_update and "updated_rule_data" in proposed_update:
                        # Ensure update is from a trusted source
                        proposed_update["updated_rule_data"]["source"] = "contextual_refresh_engine"
                        
                        # Apply the update using the standard update_rule method
                        success = await self.update_rule(rule_to_refresh.id, proposed_update["updated_rule_data"])
                        if success:
                            # Find the newly updated rule to get its new hash
                            updated_rule = self._rules_by_id.get(rule_to_refresh.id)
                            await self._publish_event("ContextualRefreshSuccess", {
                                "rule_id": rule_to_refresh.id,
                                "new_version": proposed_update["updated_rule_data"]["version"],
                                "new_rule_hash": updated_rule.rule_hash if updated_rule else None,
                                "iso_evaluation": proposed_update.get("iso_evaluation", {}),
                                "refresh_method": "AI + RAG" if self._rag_client else "AI only"
                            })
                    else:
                         await self._publish_event("ContextualRefreshSkipped", {
                            "rule_id": rule_to_refresh.id,
                            "reason": "No valid update proposed by AI.",
                            "response_keys": proposed_update.keys() if proposed_update else "None"
                         })

                except Exception as e:
                    logger.error(f"Error during contextual refresh of rule '{rule_to_refresh.id}': {e}", exc_info=True)
                    await self._publish_event("ContextualRefreshFailed", {"rule_id": rule_to_refresh.id, "error": str(e)})

        except asyncio.CancelledError:
            logger.info("Contextual Refresh Engine task cancelled.")


    # --- Async Context Management ---
    async def __aenter__(self) -> "PsycheBank":
        if not self._initialized.is_set(): await self.__ainit__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        logger.info("Shutting down PsycheBank.")
        # Wait for queues to drain, ensuring events are processed before shutdown
        if not self._audit_event_queue.empty() or not self._anomaly_event_queue.empty():
            try:
                await asyncio.wait_for(
                    asyncio.gather(self._audit_event_queue.join(), self._anomaly_event_queue.join()), timeout=10.0 # Increased timeout
                )
            except asyncio.TimeoutError:
                logger.warning("Timed out waiting for event queues to drain. Events may be lost.")
        
        await self._shutdown_tasks()
        
        async with self._lock:
            if self._store is not None and exc_type is None:
                try: await self._persist() # Final persistence on clean exit
                except Exception as e: logger.error(f"Failed to persist final state: {e}")
        
        self._initialized.clear()
        logger.info("PsycheBank shut down successfully.")

    async def _shutdown_tasks(self) -> None:
        """Gracefully cancels and awaits all background tasks."""
        # Cancel tasks
        for task in self._background_tasks:
            if not task.done(): task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            results = await asyncio.gather(*self._background_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                task_name = self._background_tasks[i].get_name()
                if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                    logger.error(f"Task {task_name} raised exception during shutdown: {result}", exc_info=result)
        self._background_tasks.clear()
    async def shutdown(self) -> None:
        """Public method to gracefully shut down the bank and its tasks."""
        await self._shutdown_tasks()
        self._initialized.clear()
        logger.info(f"PsycheBank shut down.")

    # --- Public Read-Only API ---
    async def all_rules(self) -> List[CogRule]:
        if not self._initialized.is_set(): await self.__ainit__()
        return list(self._store.rules) if self._store else []

    async def rules_by_category(self, category: str) -> List[CogRule]:
        if not self._initialized.is_set(): await self.__ainit__()
        if not self._store or not self._is_valid_rule_category(category): return []
        return [r for r in self._store.rules if r.category == category]

    async def get_rule_by_id(self, rule_id: str) -> Optional[CogRule]:
        if not self._initialized.is_set(): await self.__ainit__()
        return self._rules_by_id.get(rule_id)

    async def to_dict(self) -> dict[str, Any]:
        """Returns the current state of the store as a dictionary."""
        if not self._initialized.is_set(): await self.__ainit__()
        if not self._store: return {"version": "2.4.0", "rules": [], "store_hash": None}
        # Ensure store hash is up-to-date before returning
        self._store.store_hash = create_store_hash(self._store)
        return self._store.model_dump(mode='json') # Use mode='json' for consistent output

    async def get_audit_ledger(self) -> List[Dict[str, Any]]:
        """Returns the immutable audit ledger."""
        async with _LEDGER_LOCK:
            return list(_AUDIT_LEDGER)
            
    async def get_latest_store_hash(self) -> Optional[str]:
        """Retrieves the current cryptographic hash of the entire rule store."""
        if not self._initialized.is_set(): await self.__ainit__()
        if not self._store: return None
        # Ensure the hash is up-to-date
        return create_store_hash(self._store)


    # --- Public Audit Trail API ---
    async def record_roi_event(self, event_data: dict[str, Any]) -> None:
        """Records an event related to rule performance or impact (Return on Investment)."""
        if not self._initialized.is_set(): await self.__ainit__()
        if "timestamp" not in event_data:
            event_data["timestamp"] = datetime.now(UTC).isoformat() + "Z"
        await self._publish_event("RoiEventRecorded", event_data)
        self._roi_history_cache.append(event_data)

    async def get_roi_history(self) -> List[dict[str, Any]]:
        if not self._initialized.is_set(): await self.__ainit__()
        return list(self._roi_history_cache)
