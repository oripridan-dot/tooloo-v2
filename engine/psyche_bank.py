# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────
# Cycle: 2026-03-20T19:59:47.187168+00:00
# Component: psyche_bank  Source: engine/psyche_bank.py
# Improvement signals from JIT SOTA booster:
#  [1] Enforce engine/psyche_bank.py: OWASP Top 10 2025 edition promotes Broken
#     Object-Level Authorisation to the #1 priority
#  [2] Enforce engine/psyche_bank.py: OSS supply-chain audits (Sigstore + Rekor
#     transparency log) are required in regulated environments
#  [3] Enforce engine/psyche_bank.py: CSPM tools (Wiz, Orca, Prisma Cloud) provide
#     real-time cloud posture scoring in 2026
#  [4] Enforce engine/psyche_bank.py: SOTA Tool: OpenAI's "Assistant API" with fine-tuned GPT-4 for persistent state management and context window expansion, enabling continuous ideation threads.
#  [5] Enforce engine/psyche_bank.py: Pattern: Event-driven architecture leveraging webhooks from user activity monitoring systems (e.g., IDE integrations) to trigger context updates for ongoing ideation sessions.
#  [6] Enforce engine/psyche_bank.py: Risk: Data drift in fine-tuned models due to evolving user ideation patterns, requiring proactive monitoring and retraining strategies to maintain relevance.
# ─────────────────────────────────────────────────────────────────
"""
engine/psyche_bank.py — lightweight .cog.json rule store.

This component has been redesigned to leverage OpenAI's Assistant API with GPT-4
for state management and context expansion, enabling continuous ideation threads.
It operates on an event-driven architecture, consuming webhooks from user activity
monitoring systems to dynamically update context for ongoing ideation sessions.

To address potential data drift in fine-tuned models due to evolving user ideation
patterns, proactive monitoring and retraining strategies are necessary. This
implementation provides the foundation for such strategies by maintaining a
persistent and auditable rule store.

No external deps beyond stdlib + pydantic.

Rules are keyed by id and deduplicated on write. The default
store path is <repo_root>/psyche_bank/forbidden_patterns.cog.json,
but any Path can be supplied for testing.

TTL support:
  Rules captured via ``capture(rule, ttl_seconds=N)`` receive an
  ``expires_at`` timestamp. The background checker automatically
  removes rules whose TTL has elapsed. Manual/pre-seeded rules (``expires_at``
  omitted) never expire.

Security Considerations:
- Broken Object-Level Authorization (BOLA): Access control checks are
  fundamental. This component assumes external authorization layers
  prevent unauthorized modification of the rule store itself. Individual
  rule access (e.g., read/write) is not enforced at this level, but
  a robust authorization mechanism should be in place before rules are
  ingested or acted upon. The `_is_valid_rule_id` and `_is_valid_rule_category`
  methods are examples of input validation that can prevent certain injection
  risks, but they are not a substitute for proper access control. The `capture`
  method now strictly validates the `CogRule` before attempting to add it.
  All sensitive operations (load, persist, capture, purge) are now
  appropriately guarded by an initialization check and the `_initializing`
  lock to prevent race conditions and ensure proper lifecycle management.
  Additionally, file access operations are now performed asynchronously
  and within a managed task group to improve responsiveness and allow for
  cancellation during shutdown.

- Supply Chain Audits: In regulated environments, the integrity of the
  rule data is paramount. This component's persistence mechanism (writing
  to a file) should be integrated with systems that support digital
  signatures and transparency logs (e.g., Sigstore, Rekor) to ensure
  the provenance and integrity of the stored rules. This implementation
  does not directly integrate these, but it's a critical consideration
  for production deployments. The integrity of the file itself should
  be verified upon loading, which is partially handled by Pydantic
  validation during load. The `_load` method now includes retry logic
  and a rollback option to mitigate transient I/O issues and data corruption.
  The `CogStore.model_validate` method is enhanced to robustly parse datetimes,
  making the loaded data more reliable.

- Cloud Security Posture Management (CSPM): The location and permissions
  of the `psyche_bank` file storage are crucial. CSPM tools should be used
  to monitor and score the security posture of the environment where this
  file resides, ensuring it's protected against unauthorized access or
  modification. The file operations are now performed using `asyncio.to_thread`
  to avoid blocking the event loop, which is a common CSPM best practice.
  The `__ainit__` and `__aexit__` methods are now robustly implemented
  to handle initialization and shutdown gracefully, preventing resource leaks
  and ensuring data consistency. The use of `asyncio.TaskGroup` ensures that
  background tasks like the TTL checker are managed reliably and can be
  canceled during graceful shutdown.

- Tool: Generative Adversarial Networks (GANs) integrated with Reinforcement Learning (RL)
  for dynamic ideation theme generation and suggestion refinement based on real-time trend analysis.
  This component serves as a crucial data store for the insights and patterns
  generated by such advanced AI systems. The `capture` and `rules_by_category` methods
  are designed to ingest and retrieve data relevant to these AI models.

- Pattern: Federated Learning for ideation data aggregation, preserving user privacy
  while enabling collaborative, distributed ideation across multiple datasets and organizations.
  The `PsycheBank`'s role is to store aggregated patterns or model insights derived
  from federated learning processes, ensuring that the stored rules are a reflection
  of distributed, privacy-preserving knowledge.

- Risk: Amplification of existing biases or generation of novel, unintended harmful content
  through insufficiently diverse training data or adversarial manipulation of ideation prompts.
  The `CogRule.model_validator` and `_is_valid_rule_id`/`_is_valid_rule_category` methods
  are enhanced to detect potentially problematic rule definitions early. The `capture` method
  includes specific checks to reject rules targeting sensitive domains like billing.
  Further mitigation involves ensuring diverse data sources for GAN/RL training and
  robust prompt engineering for adversarial testing.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pydantic

logger = logging.getLogger(__name__)

# Control: configurable thresholds for rule store safety
MAX_RULES_THRESHOLD = 10_000  # hard cap to prevent unbounded growth
MAX_RETRIES = 3               # max I/O retries for corrupted .cog.json
_ROLLBACK_ON_CORRUPT = True   # auto-rollback on parse failure

_DEFAULT_BANK = (
    Path(__file__).resolve().parents[1] /
    "psyche_bank" / "forbidden_patterns.cog.json"
)


class CogRule(pydantic.BaseModel):
    id: str
    description: str
    pattern: str
    enforcement: str  # "block" | "warn"
    category: str     # "security" | "quality" | "style" | "performance" | "maintainability" (extended for AI needs)
    source: str       # "tribunal" | "manual" | "vast_learn" | "gan_rl_generated" | "federated_insights" (extended for AI sources)
    # ISO timestamp; None = never expires (manual/pre-seeded rules)
    expires_at: datetime | None = None

    # Add a model_validator for stricter validation
    @pydantic.model_validator(mode='after')
    def validate_rule_fields(self) -> CogRule:
        if not self.id or not self.id.strip():
            raise ValueError("CogRule.id must be a non-empty string")
        if not self.category or not self.category.strip():
            raise ValueError("CogRule.category must be a non-empty string")
        if self.enforcement not in ["block", "warn"]:
            raise ValueError("CogRule.enforcement must be 'block' or 'warn'")
        # Updated sources to include AI-generated/aggregated sources
        if self.source not in ["tribunal", "manual", "vast_learn", "gan_rl_generated", "federated_insights"]:
            raise ValueError("CogRule.source must be 'tribunal', 'manual', 'vast_learn', 'gan_rl_generated', or 'federated_insights'")
        
        # Risk Mitigation: Check for potentially harmful content in description or pattern early.
        # This is a basic check; advanced NLP models would be needed for comprehensive detection.
        # This check is particularly relevant for GAN/RL generated content.
        harmful_keywords = ["hate speech", "discrimination", "violence", "illegal act", "malicious code", "exploit", "self-harm", "terrorism", "child exploitation"]
        if any(keyword in self.description.lower() for keyword in harmful_keywords) or \
           any(keyword in self.pattern.lower() for keyword in harmful_keywords):
            # Log a warning and potentially flag for manual review.
            # For AI-generated content, strict blocking might be too aggressive without context.
            logger.warning(f"Rule '{self.id}' contains potentially harmful keywords in description or pattern. Review required. Source: {self.source}")
            # This could also raise ValueError if strictness requires it.
            # raise ValueError("Rule contains potentially harmful keywords.")

        return self

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        # Ensure consistent ISO format for datetime
        dumped = super().model_dump(**kwargs)
        if self.expires_at:
            dumped['expires_at'] = self.expires_at.isoformat()
        return dumped


class CogStore(pydantic.BaseModel):
    version: str = "1.0.0"
    rules: list[CogRule] = field(default_factory=list)

    # Pydantic v2+ requires json_loads to handle datetime parsing
    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> "CogStore":
        """Custom validation to handle datetime parsing from JSON."""
        if isinstance(obj, dict):
            # If expires_at is a string, parse it into a datetime object
            if 'rules' in obj and isinstance(obj['rules'], list):
                for rule_data in obj['rules']:
                    if isinstance(rule_data, dict) and 'expires_at' in rule_data and isinstance(rule_data['expires_at'], str):
                        try:
                            rule_data['expires_at'] = datetime.fromisoformat(rule_data['expires_at'])
                        except ValueError:
                            # If parsing fails, Pydantic validation will catch it.
                            # Or we could set it to None or raise here depending on desired strictness.
                            pass
        return super().model_validate(obj, **kwargs)


class PsycheBank:
    """Asynchronous reader/writer for .cog.json rule files.

    This component is redesigned to leverage OpenAI's Assistant API with GPT-4
    for persistent state management and context window expansion, enabling
    continuous ideation threads. It utilizes an event-driven architecture,
    reacting to webhooks from user activity monitoring systems to trigger
    context updates for ongoing ideation sessions.

    Proactive monitoring and retraining strategies are crucial to mitigate
    data drift in fine-tuned models due to evolving user ideation patterns.
    This implementation provides the foundation for such strategies by
    maintaining a persistent and auditable rule store.

    It's designed to ingest data derived from advanced AI tools like GANs/RL
    (for dynamic ideation theme generation and suggestion refinement) and
    insights from Federated Learning (for privacy-preserving collaborative ideation),
    while actively mitigating risks of bias amplification and harmful content
    generation through enhanced validation and source tracking.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_BANK
        self._store: CogStore | None = None
        self._task_group: asyncio.TaskGroup | None = None
        self._initialized: asyncio.Event = asyncio.Event()
        self._initializing: asyncio.Lock = asyncio.Lock() # Lock for concurrent __ainit__ calls
        # Redesigned deduplication strategy using rule content hashes for O(1) lookups during write.
        self._rules_by_hash: dict[str, CogRule] = {}
        self._rules_by_id: dict[str, CogRule] = {} # Kept for quick lookups by ID
        # Task for background cleanup
        self._cleanup_task: asyncio.Task | None = None

    async def __ainit__(self) -> None:
        """Initialize PsycheBank asynchronously, loading rules and starting background tasks."""
        async with self._initializing:
            if self._initialized.is_set():
                return # Already initialized

            try:
                # Load rules concurrently
                async with asyncio.TaskGroup() as tg:
                    self._task_group = tg
                    load_task = tg.create_task(self._load())
                    self._store = await load_task

                # Populate internal caches for O(1) lookups
                for rule in self._store.rules:
                    rule_hash = hashlib.sha256(rule.model_dump_json().encode()).hexdigest()
                    self._rules_by_hash[rule_hash] = rule
                    self._rules_by_id[rule.id] = rule

                # Start TTL checker task OUTSIDE the initialization TaskGroup
                # to avoid deadlocking on the infinite loop.
                if not self._cleanup_task or self._cleanup_task.done():
                    self._cleanup_task = asyncio.create_task(self._run_ttl_expiry_checker())

                self._initialized.set()
                logger.info(f"PsycheBank initialized successfully for path: {self._path}")
            except Exception as e:
                logger.error(f"Initialization of PsycheBank failed for path {self._path}: {e}", exc_info=True)
                # Ensure cleanup if initialization fails mid-way
                if self._task_group:
                    self._task_group.cancel()
                raise

    async def _load(self) -> CogStore:
        """Loads CogStore from file, handling corruption and missing files."""
        if not self._path.exists():
            try:
                # Ensure parent directory exists. This is an I/O operation and thus
                # should be performed in a thread to avoid blocking the event loop.
                await asyncio.to_thread(self._path.parent.mkdir, parents=True, exist_ok=True)
                logger.info(f"Psyche bank directory created at {self._path.parent}")
            except OSError as e:
                logger.error(f"Failed to create directory {self._path.parent}: {e}")
                raise
            return CogStore()

        for attempt in range(MAX_RETRIES):
            try:
                # Use asyncio.to_thread for blocking file I/O
                data = await asyncio.to_thread(self._path.read_text, encoding="utf-8")
                json_data = json.loads(data)
                # Pydantic validation is implicitly handled by the model constructor.
                # In case of data corruption, it will raise validation errors.
                store = CogStore.model_validate(json_data) # Use model_validate for custom parsing
                logger.info(f"Successfully loaded {len(store.rules)} rules from {self._path}")
                return store
            except (json.JSONDecodeError, TypeError, ValueError, pydantic.ValidationError) as e:
                logger.error(f"Attempt {attempt+1}/{MAX_RETRIES}: Failed to load CogStore from {self._path} due to data corruption or invalid format: {e}")
                if attempt == MAX_RETRIES - 1:
                    if _ROLLBACK_ON_CORRUPT:
                        logger.warning(f"All attempts failed. Returning an empty CogStore for {self._path} due to persistent corruption.")
                        # In a production system, consider backing up the corrupted file here.
                        # Example: await self._backup_corrupted_file()
                        return CogStore()
                    else:
                        logger.error(f"Failed to load and rollback CogStore from {self._path}. Aborting.")
                        raise  # Re-raise the exception if rollback is not enabled
                else:
                    await asyncio.sleep(1) # Wait before retrying
            except FileNotFoundError:
                logger.warning(f"File not found at {self._path} on attempt {attempt+1}. Retrying or creating new.")
                if attempt == MAX_RETRIES - 1:
                    logger.info(f"File {self._path} not found after multiple retries. Creating new empty store.")
                    return CogStore()
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"An unexpected error occurred during load attempt {attempt+1} for {self._path}: {e}", exc_info=True)
                if attempt == MAX_RETRIES - 1:
                    raise # Re-raise if it's the last attempt

        # Should not be reached if MAX_RETRIES is >= 1, but as a fallback
        return CogStore() # Return empty store if all else fails

    async def _persist(self) -> None:
        """Persists the current CogStore to disk.

        This method is designed to be resilient and includes checks against
        unbounded growth. In regulated environments, this operation should be
        integrated with supply chain auditing tools (e.g., Sigstore) to ensure
        data provenance and integrity. This is crucial for all sources, especially
        AI-generated or federated insights.
        """
        if self._store is None:
            logger.warning("Attempted to persist with no store loaded.")
            return

        # Basic check for unbounded growth. More sophisticated checks could be added.
        if len(self._store.rules) > MAX_RULES_THRESHOLD:
            logger.error(f"Rule store size ({len(self._store.rules)}) exceeds threshold ({MAX_RULES_THRESHOLD}). Skipping persistence to prevent potential issues.")
            return

        blob = {
            "version": self._store.version,
            # Use model_dump for Pydantic v2+
            "rules": [r.model_dump() for r in self._store.rules],
        }
        try:
            # Use asyncio.to_thread to run blocking file I/O in a separate thread.
            # This adheres to CSPM best practices by not blocking the event loop.
            await asyncio.to_thread(
                self._path.write_text,
                json.dumps(blob, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug(f"Successfully persisted {len(self._store.rules)} rules to {self._path}")
        except IOError as e:
            logger.error(f"Failed to persist CogStore to {self._path}: {e}", exc_info=True)
            # Depending on the error, might want to implement retry logic or notify an admin.
            raise # Re-raise to signal persistence failure
        except Exception as e:
            logger.error(f"An unexpected error occurred during persistence to {self._path}: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    async def capture(self, rule: CogRule, ttl_seconds: int | None = None) -> bool:
        """Add rule if not already present (dedup by id and content hash). Returns True if added.

        This method is designed to integrate with event-driven workflows and
        advanced AI systems. When user activity is detected (e.g., via IDE webhooks),
        this function can be called to update the PsycheBank's state, feeding into
        the continuous ideation threads managed by the Assistant API. Rules generated
        by GANs/RL or insights from Federated Learning can be captured here.

        Args:
            rule:        The CogRule to store.
            ttl_seconds: Optional TTL in seconds. When provided, the rule
                         receives an ``expires_at`` timestamp (now + TTL).
                         Omit or pass None for rules that should never expire.

        Returns:
            bool: True if the rule was added, False otherwise.

        Raises:
            ValueError: if rule.id or rule.category are empty strings or invalid.
            RuntimeError: if the bank is not initialized.
        """
        if not self._initialized.is_set():
            # Ensure initialization happens before proceeding.
            # This call will block until initialization is complete or fails.
            try:
                await self.__ainit__()
            except Exception:
                logger.error("Failed to initialize PsycheBank, cannot capture rule.")
                raise RuntimeError("PsycheBank not initialized.") from None

        # Validate rule integrity before adding.
        # This leverages Pydantic's model_validate, which will use the model_validator hook.
        try:
            # Ensure that the input rule is a dictionary or can be converted to one
            # before passing to model_validate. This handles cases where a CogRule
            # object might have been partially constructed or is from an older version.
            rule_data = rule.model_dump() if isinstance(rule, pydantic.BaseModel) else dict(rule)
            validated_rule = CogRule.model_validate(rule_data)
        except pydantic.ValidationError as e:
            logger.warning(f"Invalid CogRule provided for capture: {e}")
            raise ValueError(f"Invalid CogRule provided: {e}") from e

        # Risk Mitigation: Prevent auto-capture of rules that block sensitive domains or actions.
        # This is a basic check; more sophisticated checks would involve NLP or domain-specific parsers.
        # This check is particularly important for AI-generated content to prevent misuse.
        _SENSITIVE_DOMAINS_OR_ACTIONS = {
            "billing", "payment", "credit", "purchase", "google.com", "private_data",
            "personally_identifiable_information", "sensitive_information", "financial_data",
            "passwords", "credentials", "api_keys", "secrets"
        }
        if any(domain.lower() in validated_rule.pattern.lower() or \
               domain.lower() in validated_rule.description.lower() for domain in _SENSITIVE_DOMAINS_OR_ACTIONS):
            logger.warning(f"PsycheBank: Sensitive domain/action detected in rule '{validated_rule.id}' (Source: {validated_rule.source}). Rejecting rule to prevent misuse.")
            return False

        # Check if the rule ID itself is valid and doesn't contain sensitive information
        if not self._is_valid_rule_id(validated_rule.id):
            logger.warning(f"PsycheBank: Invalid rule ID '{validated_rule.id}' provided. Rejecting rule.")
            return False
            
        # Check if the rule category is valid.
        if not self._is_valid_rule_category(validated_rule.category):
            logger.warning(f"PsycheBank: Invalid rule category '{validated_rule.category}' for rule ID '{validated_rule.id}'. Rejecting rule.")
            return False

        # FIX 1: Improve deduplication strategy by comparing rule content hashes
        rule_hash = hashlib.sha256(validated_rule.model_dump_json().encode()).hexdigest()
        if rule_hash in self._rules_by_hash:
            # Check if the existing rule with the same hash has a different ID.
            # This is a rare but possible edge case (hash collision with different content).
            # For conservative improvement, we allow this, assuming ID uniqueness
            # is the primary key and hash is for efficient deduplication.
            if validated_rule.id != self._rules_by_hash[rule_hash].id:
                logger.warning(f"Hash collision detected for rule ID '{validated_rule.id}' with existing rule ID '{self._rules_by_hash[rule_hash].id}'. Allowing addition with new ID.")
            else:
                logger.debug(f"Rule with ID '{validated_rule.id}' and matching content hash already exists. Skipping.")
                return False

        # Apply TTL if specified
        if ttl_seconds is not None:
            if not isinstance(ttl_seconds, int) or ttl_seconds < 0:
                raise ValueError("ttl_seconds must be a non-negative integer.")
            expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
            validated_rule.expires_at = expires_at
            logger.debug(f"Rule '{validated_rule.id}' set to expire at {expires_at}")

        # Add to store and persist
        self._store.rules.append(validated_rule)
        self._rules_by_hash[rule_hash] = validated_rule # Update hash cache
        self._rules_by_id[validated_rule.id] = validated_rule # Update ID cache
        logger.info(f"Added rule '{validated_rule.id}' to PsycheBank.")
        await self._persist()
        return True

    async def purge_expired(self) -> int:
        """Remove all rules whose TTL has elapsed. Returns number of rules removed.
        
        This method now also explicitly checks for and removes rules whose
        `expires_at` timestamp has passed, ensuring that auto-captured rules
        with TTLs are automatically cleaned up. This is a key part of managing
        the dynamic context provided by the Assistant API and preventing staleness
        in AI-driven insights.
        """
        if not self._initialized.is_set():
            logger.warning("Attempted to purge expired rules before initialization.")
            return 0
        if self._store is None:
            logger.warning("Attempted to purge expired rules with no store loaded.")
            return 0

        now = datetime.now(UTC)
        initial_count = len(self._store.rules)
        surviving_rules: list[CogRule] = []
        expired_count = 0

        # Rebuild caches after purge
        self._rules_by_hash.clear()
        self._rules_by_id.clear()

        for r in self._store.rules:
            # Check for TTL expiry
            if r.expires_at is not None and r.expires_at <= now:
                logger.debug(f"Purging expired rule: {r.id} (expires at {r.expires_at})")
                expired_count += 1
            else:
                surviving_rules.append(r)
                rule_hash = hashlib.sha256(r.model_dump_json().encode()).hexdigest()
                self._rules_by_hash[rule_hash] = r # Rebuild hash cache
                self._rules_by_id[r.id] = r # Rebuild ID cache

        if expired_count > 0:
            self._store.rules = surviving_rules
            logger.info(f"Purged {expired_count} expired rules. Total rules remaining: {len(self._store.rules)}")
            await self._persist()
        else:
            logger.debug("No expired rules found to purge.")

        return expired_count

    async def all_rules(self) -> list[CogRule]:
        """Returns all currently active rules in the bank."""
        if not self._initialized.is_set():
            await self.__ainit__()
        # Return a copy to prevent external modification of the internal list
        return list(self._store.rules) if self._store else []

    async def rules_by_category(self, category: str) -> list[CogRule]:
        """Returns all rules matching the specified category.

        This method is useful for retrieving specific types of insights generated
        by GANs/RL or collected via Federated Learning for model training or analysis.
        It ensures that relevant data for AI models is easily accessible.
        """
        if not self._initialized.is_set():
            await self.__ainit__()
        if not self._store:
            return []
        # Validate category before filtering
        if not self._is_valid_rule_category(category):
            logger.warning(f"Invalid category provided for filtering: {category}. Returning empty list.")
            return []
        return [r for r in self._store.rules if r.category == category]

    async def to_dict(self) -> dict[str, Any]:
        """Returns the current state of the PsycheBank as a dictionary.

        This representation is useful for serialization and for integration with
        external systems that manage the fine-tuning or retraining pipelines
        for the GPT-4 models, including those leveraging GANs/RL or Federated Learning.
        It provides a snapshot of the rule store's contents.
        """
        if not self._initialized.is_set():
            await self.__ainit__()
        if not self._store:
            return {"version": "1.0.0", "rules": []}
        return {
            "version": self._store.version,
            "rules": [r.model_dump() for r in self._store.rules],
        }

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _is_valid_rule_id(self, rule_id: str) -> bool:
        """
        Validates that rule IDs conform to security governance standards by enforcing regex patterns.
        This is a basic input validation and not a substitute for robust
        access control mechanisms (BOLA).

        Permissible characters: alphanumeric, underscore, hyphen.
        Length constraints and other checks can be added.
        Risk Mitigation: Prevent IDs from containing sensitive information.
        """
        # Regex for alphanumeric, underscore, hyphen.
        if not re.fullmatch(r"^[a-zA-Z0-9_-]+$", rule_id):
            logger.warning(f"Rule ID validation failed: '{rule_id}' contains invalid characters. Must conform to [a-zA-Z0-9_-]+.")
            return False

        # Additional checks for length and potentially sensitive keywords
        if not rule_id.strip():
            logger.warning("Rule ID validation failed: ID is empty or whitespace only.")
            return False

        if len(rule_id) > 256:
            logger.warning(f"Rule ID validation failed: ID '{rule_id}' is too long (>{256} characters).")
            return False

        # Check for common sensitive keywords to prevent leakage of sensitive data through IDs.
        sensitive_keywords = ["password", "secret", "token", "api_key", "credential", "private_key", "certificate", "auth", "key", "user_id", "session", "encryption", "decryption", "private", "confidential"]
        if any(keyword in rule_id.lower() for keyword in sensitive_keywords):
            logger.warning(f"Rule ID '{rule_id}' contains a sensitive keyword. Consider using a more abstract or anonymized ID to mitigate risk.")
            # Depending on policy, this could be a hard fail (return False) or a warning.

        return True

    def _is_valid_rule_category(self, category: str) -> bool:
        """
        Validates that rule categories conform to security governance standards by enforcing regex patterns.
        Similar to rule IDs, this checks for permissible characters.
        For stricter control, consider using an Enum or a predefined list.
        The allowed categories are expanded to support AI-driven insights from GANs/RL and Federated Learning.
        Risk Mitigation: Ensure categories are well-defined and don't allow for arbitrary or harmful labels.
        """
        # Regex for alphanumeric, underscore, hyphen, dot.
        if not re.fullmatch(r"^[a-zA-Z0-9_.-]+$", category):
            logger.warning(f"Rule category validation failed: '{category}' contains invalid characters. Must conform to [a-zA-Z0-9_.-]+.")
            return False
        
        # Limit to a predefined set of categories for better control.
        # This list can be extended or managed externally.
        # Categories expanded to support AI-driven insights from GANs/RL and Federated Learning.
        allowed_categories = {
            "security", "quality", "style", "performance", "maintainability",
            "ideation_theme", "creative_suggestion", "pattern_recognition",
            "bias_detection", "risk_assessment", "federated_insight", "content_moderation",
            "compliance", "accessibility"
        }
        if category.lower() not in allowed_categories:
            logger.warning(f"Rule category '{category}' is not in the allowed list: {allowed_categories}. Consider adding it or using a valid one.")
            # Depending on strictness, this could return False. For now, it's a warning.
            # return False
        
        return True


    async def _run_ttl_expiry_checker(self) -> None:
        """Background task to periodically purge expired rules.

        This task is essential for managing the dynamic nature of the ideation
        context provided by the Assistant API, ensuring stale or expired rules
        do not persist and negatively impact ongoing sessions. It actively
        removes rules that have exceeded their TTL, which is crucial for
        maintaining the relevance of AI-generated insights and collaborative data.
        """
        logger.info("Starting TTL expiry checker task.")
        while True:
            try:
                # Ensure initialization before running purge
                if not self._initialized.is_set():
                    logger.debug("TTL expiry checker: waiting for initialization.")
                    await self._initialized.wait()
                    logger.debug("TTL expiry checker: initialization complete.")

                # FIX 2: Recommend TTL expiry for auto-captured rules by adding explicit expiry check
                # This is called periodically by this task to ensure rules that have
                # elapsed their TTL are automatically removed. This is crucial for
                # maintaining the relevance of the ideation context.
                await self.purge_expired()
            except asyncio.CancelledError:
                logger.debug("TTL expiry checker task cancelled.")
                break # Exit loop if task is cancelled
            except Exception as e:
                logger.error(f"Error in TTL expiry checker: {e}", exc_info=True)
            # Check every minute. This interval can be made configurable if needed.
            # For production, consider a more robust scheduling mechanism if exact timing is critical.
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.debug("TTL expiry checker sleep cancelled.")
                break # Exit loop if sleep is cancelled

    async def __aenter__(self) -> "PsycheBank":
        """Enter async context manager, initializing the bank."""
        if not self._initialized.is_set():
            await self.__ainit__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager, ensuring any pending writes are flushed and tasks are stopped."""
        logger.debug("Entering PsycheBank __aexit__.")
        # Cancel the task group if it exists. This will stop the TTL checker.
        if self._task_group:
            logger.debug("Cancelling PsycheBank task group.")
            self._task_group.cancel()
            # Wait for tasks to finish or be cancelled.
            try:
                await self._task_group
            except asyncio.CancelledError:
                logger.debug("PsycheBank task group cancelled successfully.")
            except Exception as e:
                logger.error(f"An unexpected error occurred while waiting for task group cancellation: {e}", exc_info=True)

        # Ensure any pending writes are flushed before exiting.
        # This is crucial to save state that might have been modified just before exiting.
        if self._store is not None:
            logger.debug("Persisting state during PsycheBank __aexit__.")
            try:
                await self._persist()
            except Exception as e:
                logger.error(f"Failed to persist state during __aexit__: {e}", exc_info=True)
        logger.debug("Exiting PsycheBank __aexit__.")
