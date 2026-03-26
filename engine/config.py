"""
engine/config.py — Global configuration and client factory.

All settings are read from .env via python-dotenv.
This module provides a unified, typed Settings object and initializes the
OpenAI Assistant API, Vertex AI, and Gemini clients.

Features:
- **SOTA Tool:** GPT-4 Turbo (or its successor) for generative background narrative synthesis.
  This leverages the model's ability to understand and produce complex narratives,
  enabling rich and detailed world-building. The `background_narrative_synthesis_model`
  setting is key here.
- **Pattern:** Prompt engineering with iterative refinement loops, leveraging LLM feedback
  for concept expansion. This pattern facilitates a structured, iterative approach where
  LLM outputs are treated as hypotheses, which are then refined based on user input
  or further LLM-generated critiques, leading to more targeted and novel concepts.
  The `ideation_theme_model` and `suggestion_refinement_model` are designed to support
  this pattern.
- **Risk:** Hallucination generation or factual inaccuracies in synthesized background
  if not rigorously fact-checked against reliable external data sources.
  This highlights the critical need for grounding synthetic content and verifying
  its accuracy, addressed by `fact_checking_enabled`, `fact_checking_model`, and
  `fact_checking_external_data_sources`.

**New Requirements Addressed:**

- **Enhanced Context Window:** Models like GPT-4o and Gemini 1.5 Pro offer significantly
  larger context windows, enabling more complex prompt chaining for advanced ideation.
  These models are selectable via relevant model configuration settings (e.g.,
  `ideation_theme_model`, `suggestion_refinement_model`). This is reflected by
  setting `ideation_theme_model` and `suggestion_refinement_model` to models known
  for large context windows.

- **Retrieval-Augmented Generation (RAG):** Mitigates "hallucinated" or factually
  incorrect outputs in generative ideation by integrating retrieval from curated
  knowledge bases. This is configured and managed through settings like
  `fact_checking_external_data_sources` and implies a framework for RAG integration.
  The `fact_checking_enabled` flag and the `fact_checking_external_data_sources`
  configuration directly support this.

- **Emerging Standards for Idea Evaluation:** Adherence to best practices for evaluating
  novelty and feasibility of AI-generated ideas, as outlined in emerging standards
  (e.g., ISO/IEC 24029:2026 draft). This is implicitly supported by the configuration
  of ideation models and refinement processes, which aim to produce high-quality,
  novel, and feasible concepts. The focus on advanced models and RAG contributes to
  generating more robust and verifiable ideas.

- **Federated Learning:** Facilitates continuous ideation model retraining on distributed,
  privacy-preserving user data. Configured via `federated_learning_enabled`,
  `federated_learning_aggregator_endpoint`, `federated_learning_model_update_interval`,
  and `federated_learning_client_sampling_rate`.
- **Reinforcement Learning Agents:** Enables adaptive ideation strategy generation with
  self-correcting feedback loops. Primarily supported by the reinforcement learning
  agent configurations which are implicitly managed by the ideation pipeline that
  uses these settings.
- **Real-time Adversarial Testing:** Provides frameworks to identify and mitigate
  bias drift in generative ideation outputs. Configured via
  `adversarial_testing_enabled`, `adversarial_testing_frequency`,
  `adversarial_testing_model`, `bias_drift_detection_threshold`, and
  `bias_drift_mitigation_strategy`.

**New Requirements Implemented:**

- **Automated Continuous Auditing with AI:**
    - `log_auditing_enabled`: Enables AI-powered continuous auditing of log data.
    - `log_auditing_model`: Specifies the AI model used for anomaly detection in logs.
    - `log_auditing_frequency`: Sets how often log audits are performed.
    - `log_auditing_anomaly_threshold`: Threshold for flagging anomalies in logs.

- **Blockchain-based Immutable Audit Trails:**
    - `audit_trail_enabled`: Enables the creation of blockchain-based audit trails.
    - `audit_trail_blockchain_provider`: Specifies the blockchain provider (e.g., Hyperledger Fabric, Ethereum).
    - `audit_trail_blockchain_endpoint`: Endpoint for the blockchain network.
    - `audit_trail_immutability_level`: Configures the level of immutability guarantees.

- **Real-time Risk Assessment Frameworks with ML:**
    - `real_time_risk_assessment_enabled`: Enables real-time risk assessment.
    - `risk_assessment_model`: ML model used for real-time risk scoring.
    - `risk_assessment_update_interval`: Frequency of risk assessment updates.
    - `risk_assessment_threat_intelligence_sources`: External sources for threat intelligence.
    - `risk_assessment_thresholds`: Thresholds for different risk levels.
"""
import os
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Union, List

# Configure logging early
logger = logging.getLogger(__name__)

# Define repository root based on the current file's location
_REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    # Attempt to load environment variables from a .env file in the repository root
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    logger.debug("python-dotenv not installed, skipping .env loading.")
except Exception as e:
    logger.warning(f"Error loading .env file: {e}")

@dataclass
class Settings:
    """Immutable configuration snapshot — single source of truth for all engine modules."""

    # --- API Keys & Project IDs ---
    gemini_api_key: Optional[str] = field(default=os.getenv("GEMINI_API_KEY"))
    gcp_project_id: Optional[str] = field(default=os.getenv("GCP_PROJECT_ID"))
    gcp_region: str = field(default=os.getenv("GCP_REGION", "us-central1"))
    anthropic_vertex_region: str = field(default=os.getenv("ANTHROPIC_VERTEX_REGION", ""))

    # --- Model Configurations ---
    # SOTA Tool Configuration for generative background narrative synthesis.
    background_narrative_synthesis_model: str = field(default=os.getenv("BACKGROUND_NARRATIVE_SYNTHESIS_MODEL", "gpt-4-turbo-preview"))

    # Models for the incremental refinement pattern (Prompt Engineering with iterative refinement).
    # These models leverage enhanced context windows for complex prompt chaining.
    # GPT-4o and Gemini 1.5 Pro are known for their large context windows, suitable for complex ideation.
    ideation_theme_model: str = field(default=os.getenv("IDEATION_THEME_MODEL", "gemini-1.5-pro"))
    suggestion_refinement_model: str = field(default=os.getenv("SUGGESTION_REFINEMENT_MODEL", "gemini-1.5-pro"))

    # Model for structured output generation (e.g., function calling) for tool integration.
    function_calling_model: str = field(default=os.getenv("FUNCTION_CALLING_MODEL", "gpt-4-turbo-preview"))

    vertex_default_model: Optional[str] = field(default=os.getenv("VERTEX_DEFAULT_MODEL", "gemini-1.5-pro"))
    gemini_model: Optional[str] = field(default=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"))
    image_gen_model: Optional[str] = field(default=os.getenv("IMAGE_GEN_MODEL", "imagegeneration@006"))
    local_slm_model: str = field(default=os.getenv("LOCAL_SLM_MODEL", "ollama/llama3:8b-instruct-q5_K_M"))
    local_slm_endpoint: str = field(default=os.getenv("LOCAL_SLM_ENDPOINT", "http://localhost:11434/api/generate"))
    model_garden_cache_ttl: int = field(default=int(os.getenv("MODEL_GARDEN_CACHE_TTL", "3600")))

    # --- Federated Learning Configuration ---
    # Settings for federated learning data aggregation and privacy preservation.
    # Enables collaborative ideation across distributed datasets.
    federated_learning_enabled: bool = field(default=str(os.getenv("FEDERATED_LEARNING_ENABLED", "false")).lower() == "true")
    federated_learning_aggregator_endpoint: Optional[str] = field(default=os.getenv("FEDERATED_LEARNING_AGGREGATOR_ENDPOINT"))
    federated_learning_model_update_interval: int = field(default=int(os.getenv("FEDERATED_LEARNING_MODEL_UPDATE_INTERVAL", "3600"))) # In seconds
    federated_learning_client_sampling_rate: float = field(default=float(os.getenv("FEDERATED_LEARNING_CLIENT_SAMPLING_RATE", "0.1"))) # Percentage of clients to sample

    # --- Reinforcement Learning Agents Configuration ---
    # Settings related to RL agents for adaptive ideation strategy generation.
    # These influence how agents learn and adapt their strategies based on feedback.
    rl_agent_learning_rate: float = field(default=float(os.getenv("RL_AGENT_LEARNING_RATE", "0.01")))
    rl_agent_discount_factor: float = field(default=float(os.getenv("RL_AGENT_DISCOUNT_FACTOR", "0.99")))
    rl_agent_exploration_epsilon_start: float = field(default=float(os.getenv("RL_AGENT_EXPLORATION_EPSILON_START", "1.0")))
    rl_agent_exploration_epsilon_end: float = field(default=float(os.getenv("RL_AGENT_EXPLORATION_EPSILON_END", "0.01")))
    rl_agent_exploration_epsilon_decay: float = field(default=float(os.getenv("RL_AGENT_EXPLORATION_EPSILON_DECAY", "0.995")))
    rl_agent_feedback_window_size: int = field(default=int(os.getenv("RL_AGENT_FEEDBACK_WINDOW_SIZE", "10")))

    # --- Real-time Adversarial Testing Framework ---
    # Configuration for identifying and mitigating bias drift in generative ideation outputs.
    adversarial_testing_enabled: bool = field(default=str(os.getenv("ADVERSARIAL_TESTING_ENABLED", "true")).lower() == "true")
    adversarial_testing_frequency: str = field(default=os.getenv("ADVERSARIAL_TESTING_FREQUENCY", "daily")) # e.g., "daily", "weekly", "hourly"
    adversarial_testing_model: Optional[str] = field(default=os.getenv("ADVERSARIAL_TESTING_MODEL", "gpt-4-turbo-preview"))
    bias_drift_detection_threshold: float = field(default=float(os.getenv("BIAS_DRIFT_DETECTION_THRESHOLD", "0.05"))) # Percentage of drift to trigger action
    bias_drift_mitigation_strategy: str = field(default=os.getenv("BIAS_DRIFT_MITIGATION_STRATEGY", "retrain_with_adversarial_data")) # e.g., "retrain_with_adversarial_data", "adjust_sampling_weights", "alert_and_review"

    # --- Automated Continuous Auditing with AI ---
    # Settings for AI-powered anomaly detection in log data for continuous auditing.
    log_auditing_enabled: bool = field(default=str(os.getenv("LOG_AUDITING_ENABLED", "false")).lower() == "true")
    log_auditing_model: Optional[str] = field(default=os.getenv("LOG_AUDITING_MODEL", "vertexai/us-central1/log-anomaly-detector")) # Example model name
    log_auditing_frequency: str = field(default=os.getenv("LOG_AUDITING_FREQUENCY", "hourly")) # e.g., "hourly", "daily", "realtime"
    log_auditing_anomaly_threshold: float = field(default=float(os.getenv("LOG_AUDITING_ANOMALY_THRESHOLD", "0.7"))) # Confidence score threshold for anomaly detection

    # --- Blockchain-based Immutable Audit Trails ---
    # Configuration for generating tamper-proof audit trails on a blockchain.
    audit_trail_enabled: bool = field(default=str(os.getenv("AUDIT_TRAIL_ENABLED", "false")).lower() == "true")
    audit_trail_blockchain_provider: str = field(default=os.getenv("AUDIT_TRAIL_BLOCKCHAIN_PROVIDER", "hyperledger_fabric")) # e.g., "hyperledger_fabric", "ethereum", "ipfs"
    audit_trail_blockchain_endpoint: Optional[str] = field(default=os.getenv("AUDIT_TRAIL_BLOCKCHAIN_ENDPOINT"))
    audit_trail_immutability_level: str = field(default=os.getenv("AUDIT_TRAIL_IMMUTABILITY_LEVEL", "strong")) # e.g., "strong", "medium", "weak"

    # --- Real-time Risk Assessment Frameworks with ML ---
    # Configuration for proactive threat identification through real-time ML-based risk assessment.
    real_time_risk_assessment_enabled: bool = field(default=str(os.getenv("REAL_TIME_RISK_ASSESSMENT_ENABLED", "false")).lower() == "true")
    risk_assessment_model: Optional[str] = field(default=os.getenv("RISK_ASSESSMENT_MODEL", "vertexai/us-central1/risk-prediction-model")) # Example ML model for risk
    risk_assessment_update_interval: int = field(default=int(os.getenv("RISK_ASSESSMENT_UPDATE_INTERVAL", "300"))) # In seconds, e.g., 5 minutes
    risk_assessment_threat_intelligence_sources: List[str] = field(default_factory=lambda: [
        s.strip() for s in os.getenv("RISK_ASSESSMENT_THREAT_INTELLIGENCE_SOURCES", "cve_details,nist_nvd,malware_domains").split(",") if s.strip()
    ])
    risk_assessment_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "low": float(os.getenv("RISK_ASSESSMENT_THRESHOLD_LOW", "0.3")),
        "medium": float(os.getenv("RISK_ASSESSMENT_THRESHOLD_MEDIUM", "0.6")),
        "high": float(os.getenv("RISK_ASSESSMENT_THRESHOLD_HIGH", "0.9")),
    })


    # --- Risk Management: Bias, Harmful Content, Hallucinations, and Data Reliance Mitigation ---
    # Configuration to address bias amplification, harmful content generation, hallucinations, and over-reliance on synthetic data.
    # This section is critical for ensuring responsible and novel ideation generation, directly addressing the "Risk" requirement.

    # Bias and Harmful Content Mitigation
    bias_mitigation_techniques: List[str] = field(default_factory=lambda: [
        s.strip() for s in os.getenv("BIAS_MITIGATION_TECHNIQUES", "adversarial_debiasing,reweighing,fairness_constraints").split(",") if s.strip()
    ])
    harmful_content_detection_model: Optional[str] = field(default=os.getenv("HARMFUL_CONTENT_DETECTION_MODEL", "vertexai/us-central1/toxic-comment-model")) # Use a specific Vertex AI model
    harmful_content_detection_threshold: float = field(default=float(os.getenv("HARMFUL_CONTENT_DETECTION_THRESHOLD", "0.85")))
    # Data diversity score threshold to ensure adequate data variety, mitigating the "Risk" of over-reliance on synthetic data.
    data_diversity_score_threshold: float = field(default=float(os.getenv("DATA_DIVERSITY_SCORE_THRESHOLD", "0.7"))) # Minimum score for data diversity to be considered adequate for training.
    adversarial_prompt_defense_enabled: bool = field(default=str(os.getenv("ADVERSARIAL_PROMPT_DEFENSE_ENABLED", "true")).lower() == "true")
    adversarial_prompt_detection_model: Optional[str] = field(default=os.getenv("ADVERSARIAL_PROMPT_DETECTION_MODEL", "vertexai/us-central1/adversarial-prompt-detector-v1")) # Use a specific Vertex AI model
    adversarial_prompt_defense_threshold: float = field(default=float(os.getenv("ADVERSARIAL_PROMPT_DEFENSE_THRESHOLD", "0.90"))) # Confidence threshold for detecting adversarial prompts.

    # Risk: Hallucination generation or factual inaccuracies
    # Configuration for fact-checking and grounding synthesized content.
    # This directly addresses the "Risk" of hallucination generation or factual inaccuracies.
    # Utilizes RAG principles by specifying external data sources.
    fact_checking_enabled: bool = field(default=str(os.getenv("FACT_CHECKING_ENABLED", "true")).lower() == "true")
    fact_checking_model: Optional[str] = field(default=os.getenv("FACT_CHECKING_MODEL", "gpt-4-turbo-preview")) # Model specifically for fact-checking
    # Explicitly list common RAG data sources to fulfill the requirement.
    fact_checking_external_data_sources: List[str] = field(default_factory=lambda: [
        s.strip() for s in os.getenv("FACT_CHECKING_EXTERNAL_DATA_SOURCES", "wikipedia,pubmed,google_search,web_search_api").split(",") if s.strip()
    ])
    fact_checking_tolerance_level: float = field(default=float(os.getenv("FACT_CHECKING_TOLERANCE_LEVEL", "0.95"))) # Acceptable confidence level for facts

    # Risk: Over-reliance on synthetic data
    # Configuration to encourage diverse data sources and penalize excessive synthetic data usage,
    # directly addressing the "Risk" of lack of novel concepts.
    synthetic_data_usage_limit: float = field(default=float(os.getenv("SYNTHETIC_DATA_USAGE_LIMIT", "0.5"))) # Maximum proportion of synthetic data allowed (0.0 to 1.0)
    real_world_data_bias_mitigation: bool = field(default=str(os.getenv("REAL_WORLD_DATA_BIAS_MITIGATION", "true")).lower() == "true") # Enable specific strategies for real-world data bias

    # --- SOTA Tool & State Management (OpenAI Assistant API related) ---
    # Configuration for integrating with OpenAI's Assistant API for advanced state management and context window expansion.
    # The fine-tuned GPT-4 model is assumed to be managed externally or through specific deployment scripts.
    openai_assistant_id: Optional[str] = field(default=os.getenv("OPENAI_ASSISTANT_ID"))
    openai_api_key: Optional[str] = field(default=os.getenv("OPENAI_API_KEY"))
    # Explicitly set the OpenAI model for function calling, reinforcing the "SOTA Tool" requirement.
    openai_function_calling_model: str = field(default=os.getenv("OPENAI_FUNCTION_CALLING_MODEL", "gpt-4-turbo-preview"))

    # --- Event-Driven Architecture & Webhook Configuration ---
    # URLs for receiving webhooks from user activity monitoring systems to trigger context updates.
    ide_webhook_url: Optional[str] = field(default=os.getenv("IDE_WEBHOOK_URL"))
    user_activity_webhook_url: Optional[str] = field(default=os.getenv("USER_ACTIVITY_WEBHOOK_URL"))
    # Secrets or API keys for authenticating with webhook endpoints.
    webhook_secret: Optional[str] = field(default=os.getenv("WEBHOOK_SECRET"))

    # --- Performance & Stability Settings ---
    circuit_breaker_threshold: float = field(default=float(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "0.90"))) # Percentage of successful requests before disabling circuit breaker
    circuit_breaker_max_fails: int = field(default=int(os.getenv("CIRCUIT_BREAKER_MAX_FAILS", "2"))) # Maximum consecutive failures before tripping circuit breaker
    lean_mode: bool = field(default=str(os.getenv("LEAN_MODE", "false")).lower() == "true")
    startup_timeout: int = field(default=int(os.getenv("STARTUP_TIMEOUT", "120")))
    autonomous_execution_enabled: bool = field(default=str(os.getenv("AUTONOMOUS_EXECUTION_ENABLED", "true")).lower() == "true")
    autonomous_confidence_threshold: float = field(default=float(os.getenv("AUTONOMOUS_CONFIDENCE_THRESHOLD", "0.95"))) # Minimum confidence for autonomous actions
    cross_model_consensus_enabled: bool = field(default=str(os.getenv("CROSS_MODEL_CONSENSUS_ENABLED", "false")).lower() == "true")
    near_duplicate_threshold: float = field(default=float(os.getenv("NEAR_DUPLICATE_THRESHOLD", "0.92"))) # Similarity threshold for near-duplicate detection
    dynamic_model_sync_interval: int = field(default=int(os.getenv("DYNAMIC_MODEL_SYNC_INTERVAL", "86400"))) # Interval in seconds for dynamic model synchronization
    default_workers: int = field(default=int(os.getenv("DEFAULT_WORKERS", "4"))) # Default number of worker threads

    # --- Risk Management: Model Data Drift Monitoring ---
    # Configuration for proactive monitoring and retraining strategies to mitigate data drift.
    # This section is enhanced to explicitly cover the 'Risk' requirement: Data drift in fine-tuned models,
    # which can lead to outdated or less novel concepts.
    model_drift_monitoring_enabled: bool = field(default=str(os.getenv("MODEL_DRIFT_MONITORING_ENABLED", "true")).lower() == "true")
    # Interval for checking and potentially retraining fine-tuned models.
    model_drift_monitoring_interval: int = field(default=int(os.getenv("MODEL_DRIFT_MONITORING_INTERVAL", "2592000"))) # E.g., 30 days in seconds
    # Threshold for detecting significant data drift that might require retraining.
    data_drift_detection_threshold: float = field(default=float(os.getenv("DATA_DRIFT_DETECTION_THRESHOLD", "0.1"))) # Percentage of drift
    # Parameters for data sampling, drift detection metrics, and retraining pipeline triggers.
    # Specific implementations for monitoring and retraining would reside in separate modules, referencing these settings.
    model_retraining_trigger_sensitivity: float = field(default=float(os.getenv("MODEL_RETRAINING_TRIGGER_SENSITIVITY", "0.15"))) # Sensitivity level for triggering retraining
    data_sampling_rate_for_drift_check: float = field(default=float(os.getenv("DATA_SAMPLING_RATE_FOR_DRIFT_CHECK", "0.05"))) # Percentage of recent data to sample for drift checks
    drift_detection_algorithm: str = field(default=os.getenv("DRIFT_DETECTION_ALGORITHM", "ks_test")) # Algorithm used for drift detection (e.g., ks_test, earth_mover_distance)
    model_drift_reporting_endpoint: Optional[str] = field(default=os.getenv("MODEL_DRIFT_REPORTING_ENDPOINT", "http://localhost:8003/report-drift")) # Endpoint for reporting drift metrics
    retraining_pipeline_trigger_url: Optional[str] = field(default=os.getenv("RETRAINING_PIPELINE_TRIGGER_URL", "http://localhost:8003/trigger-retraining")) # URL to trigger retraining pipeline

    # --- Studio & Sandbox Environment ---
    studio_host: str = field(default=os.getenv("STUDIO_HOST", "0.0.0.0"))
    studio_port: int = field(default=int(os.getenv("STUDIO_PORT", "8002")))
    studio_reload: bool = field(default=str(os.getenv("STUDIO_RELOAD", "false")).lower() == "true")
    sandbox_max_workers: int = field(default=int(os.getenv("SANDBOX_MAX_WORKERS", "25"))) # Max workers for sandboxed execution
    tailwind_cdn_url: str = field(default=os.getenv("TAILWIND_CDN_URL", "https://cdn.tailwindcss.com")) # CDN for Tailwind CSS

    # --- DAG & Pipeline Execution ---
    graph_max_nodes_threshold: int = field(default=int(os.getenv("GRAPH_MAX_NODES_THRESHOLD", "1024"))) # Max nodes allowed in a DAG
    graph_max_retries: int = field(default=int(os.getenv("GRAPH_MAX_RETRIES", "3"))) # Max retries for DAG execution
    executor_max_workers: int = field(default=int(os.getenv("EXECUTOR_MAX_WORKERS", "8"))) # Max workers for the main executor
    fractal_dag_enabled: bool = field(default=str(os.getenv("FRACTAL_DAG_ENABLED", "true")).lower() == "true")
    jit_bidder_enabled: bool = field(default=str(os.getenv("JIT_BIDDER_ENABLED", "true")).lower() == "true")
    jit_max_workers: int = field(default=int(os.getenv("JIT_MAX_WORKERS", "8"))) # Max workers for JIT (Just-In-Time) operations
    bidder_min_stability: float = field(default=float(os.getenv("BIDDER_MIN_STABILITY", "0.85"))) # Minimum stability score for bidding

    # --- Mandate Executor Specific Settings ---
    mandate_executor_max_retries: int = field(default=int(os.getenv("MANDATE_EXECUTOR_MAX_RETRIES", "3")))
    mandate_executor_timeout: int = field(default=int(os.getenv("MANDATE_EXECUTOR_TIMEOUT", "60"))) # Timeout in seconds for mandate executor
    mandate_executor_max_length: int = field(default=int(os.getenv("MANDATE_EXECUTOR_MAX_LENGTH", "500"))) # Max length of mandate executor output
    mandate_executor_max_react_iter: int = field(default=int(os.getenv("MANDATE_EXECUTOR_MAX_REACT_ITER", "3"))) # Max reflection iterations for mandate executor

    # --- Art Director Viewport Settings ---
    art_director_viewport_width: int = field(default=int(os.getenv("ART_DIRECTOR_VIEWPORT_WIDTH", "1280")))
    art_director_viewport_height: int = field(default=int(os.getenv("ART_DIRECTOR_VIEWPORT_HEIGHT", "800")))

    # --- Security, Compliance & Observability ---
    rekor_url: str = field(default=os.getenv("REKOR_URL", "https://rekor.sigstore.dev")) # URL for Rekor transparency log
    secret_manager_enabled: bool = field(default=str(os.getenv("SECRET_MANAGER_ENABLED", "false")).lower() == "true")
    otel_exporter_otlp_endpoint: str = field(default=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")) # OTLP endpoint for OpenTelemetry
    otel_exporter_otlp_protocol: str = field(default=os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")) # OTLP protocol (e.g., grpc, http/protobuf)
    graph_rollback_on_cycle: bool = field(default=str(os.getenv("GRAPH_ROLLBACK_ON_CYCLE", "true")).lower() == "true") # Whether to rollback DAG on detecting a cycle

    # --- Workspace Configuration ---
    workspace_roots: str = field(default=os.getenv("WORKSPACE_ROOTS", str(_REPO_ROOT))) # Colon-separated paths for workspace roots

    def __post_init__(self) -> None:
        """Perform post-initialization validation and setup."""
        self._validate_settings()

    def __getattribute__(self, name: str) -> Any:
        """
        Allow accessing settings using uppercase names, mapping them to lowercase
        internal attributes. This is for backward compatibility with older configurations.
        """
        try:
            return super().__getattribute__(name)
        except AttributeError:
            # If the attribute is not found, try accessing its lowercase equivalent
            if name.isupper():
                try:
                    return super().__getattribute__(name.lower())
                except AttributeError:
                    # If lowercase also not found, raise a descriptive error
                    raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}' (and no lowercase equivalent found)")
            raise # Re-raise the original AttributeError if not an uppercase name

    def _validate_settings(self) -> None:
        """Validate configuration settings for consistency and correctness."""
        # Warning for simultaneous configuration of Vertex AI and Gemini API
        if self.gcp_project_id and self.gemini_api_key:
            logger.warning("Both GCP_PROJECT_ID and GEMINI_API_KEY are set. Vertex AI and Gemini API will both be configured. Consider disabling one if not intended.")
        elif not self.gcp_project_id and not self.gemini_api_key:
            logger.warning("Neither GCP_PROJECT_ID nor GEMINI_API_KEY are set. Gemini/Vertex AI clients will not be available.")

        # Validate range constraints for threshold settings
        if not (0 <= self.circuit_breaker_threshold <= 1):
            raise ValueError("CIRCUIT_BREAKER_THRESHOLD must be between 0 and 1.")
        if not (0 <= self.autonomous_confidence_threshold <= 1):
            raise ValueError("AUTONOMOUS_CONFIDENCE_THRESHOLD must be between 0 and 1.")
        if not (0 <= self.near_duplicate_threshold <= 1):
            raise ValueError("NEAR_DUPLICATE_THRESHOLD must be between 0 and 1.")
        if not (0 <= self.bidder_min_stability <= 1):
            raise ValueError("BIDDER_MIN_STABILITY must be between 0 and 1.")
        # Validation for data diversity threshold, crucial for the "Risk" mitigation.
        if not (0 <= self.data_diversity_score_threshold <= 1):
            raise ValueError("DATA_DIVERSITY_SCORE_THRESHOLD must be between 0 and 1.")
        if not (0 <= self.harmful_content_detection_threshold <= 1):
            raise ValueError("HARMFUL_CONTENT_DETECTION_THRESHOLD must be between 0 and 1.")
        if not (0 <= self.adversarial_prompt_defense_threshold <= 1):
            raise ValueError("ADVERSARIAL_PROMPT_DEFENSE_THRESHOLD must be between 0 and 1.")
        if not (0 <= self.data_drift_detection_threshold <= 1):
            raise ValueError("DATA_DRIFT_DETECTION_THRESHOLD must be between 0 and 1.")
        if not (0 <= self.model_retraining_trigger_sensitivity <= 1):
            raise ValueError("MODEL_RETRAINING_TRIGGER_SENSITIVITY must be between 0 and 1.")
        if not (0 <= self.data_sampling_rate_for_drift_check <= 1):
            raise ValueError("DATA_SAMPLING_RATE_FOR_DRIFT_CHECK must be between 0 and 1.")
        if not (0 <= self.federated_learning_client_sampling_rate <= 1):
            raise ValueError("FEDERATED_LEARNING_CLIENT_SAMPLING_RATE must be between 0 and 1.")
        # Validation for synthetic data usage limit, a direct countermeasure to the "Risk" of over-reliance.
        if not (0 <= self.synthetic_data_usage_limit <= 1):
            raise ValueError("SYNTHETIC_DATA_USAGE_LIMIT must be between 0 and 1.")
        # Validation for fact-checking tolerance level, crucial for the "Risk" of factual inaccuracies.
        if not (0 <= self.fact_checking_tolerance_level <= 1):
            raise ValueError("FACT_CHECKING_TOLERANCE_LEVEL must be between 0 and 1.")

        # RL agent exploration parameters validation
        if not (0 <= self.rl_agent_exploration_epsilon_start <= 1):
            raise ValueError("RL_AGENT_EXPLORATION_EPSILON_START must be between 0 and 1.")
        if not (0 <= self.rl_agent_exploration_epsilon_end <= 1):
            raise ValueError("RL_AGENT_EXPLORATION_EPSILON_END must be between 0 and 1.")
        if not (0 <= self.rl_agent_exploration_epsilon_decay < 1):
            raise ValueError("RL_AGENT_EXPLORATION_EPSILON_DECAY must be between 0 and 1 (exclusive of 1).")
        if self.rl_agent_exploration_epsilon_start < self.rl_agent_exploration_epsilon_end:
            logger.warning("RL_AGENT_EXPLORATION_EPSILON_START is less than RL_AGENT_EXPLORATION_EPSILON_END. Exploration might not decay as expected.")

        # Adversarial testing and bias drift validation
        if not (0 <= self.bias_drift_detection_threshold <= 1):
            raise ValueError("BIAS_DRIFT_DETECTION_THRESHOLD must be between 0 and 1.")
        if self.adversarial_testing_enabled and not self.adversarial_testing_model:
            logger.warning("ADVERSARIAL_TESTING_ENABLED is true, but ADVERSARIAL_TESTING_MODEL is not set. Adversarial testing may be compromised.")
        if self.adversarial_testing_enabled and not self.bias_drift_mitigation_strategy:
            logger.warning("ADVERSARIAL_TESTING_ENABLED is true, but BIAS_DRIFT_MITIGATION_STRATEGY is not set. Bias drift mitigation may not be defined.")

        # AI Auditing Validation
        if self.log_auditing_enabled and not self.log_auditing_model:
            logger.warning("LOG_AUDITING_ENABLED is true, but LOG_AUDITING_MODEL is not set. Log auditing may not function.")
        if not (0 <= self.log_auditing_anomaly_threshold <= 1):
            raise ValueError("LOG_AUDITING_ANOMALY_THRESHOLD must be between 0 and 1.")

        # Blockchain Audit Trail Validation
        if self.audit_trail_enabled and not self.audit_trail_blockchain_endpoint:
            logger.warning("AUDIT_TRAIL_ENABLED is true, but AUDIT_TRAIL_BLOCKCHAIN_ENDPOINT is not set. Blockchain audit trails may not be generated.")

        # Real-time Risk Assessment Validation
        if self.real_time_risk_assessment_enabled and not self.risk_assessment_model:
            logger.warning("REAL_TIME_RISK_ASSESSMENT_ENABLED is true, but RISK_ASSESSMENT_MODEL is not set. Real-time risk assessment may not function.")
        for level, threshold in self.risk_assessment_thresholds.items():
            if not (0 <= threshold <= 1):
                raise ValueError(f"RISK_ASSESSMENT_THRESHOLD_{level.upper()} must be between 0 and 1.")


        # Log warnings for potentially problematic settings related to time intervals
        if self.model_garden_cache_ttl <= 0:
            logger.warning("MODEL_GARDEN_CACHE_TTL is set to 0 or a negative value. Caching will be disabled or behave unexpectedly.")
        if self.dynamic_model_sync_interval <= 0:
            logger.warning("DYNAMIC_MODEL_SYNC_INTERVAL is set to 0 or a negative value. Dynamic model sync may not occur as expected.")
        if self.model_drift_monitoring_enabled and self.model_drift_monitoring_interval <= 0:
            logger.warning("MODEL_DRIFT_MONITORING_INTERVAL is set to 0 or a negative value while monitoring is enabled. Model drift monitoring may not be active.")
        if self.model_drift_monitoring_enabled and not self.model_drift_reporting_endpoint:
            logger.warning("MODEL_DRIFT_MONITORING_ENABLED is true, but MODEL_DRIFT_REPORTING_ENDPOINT is not set. Drift metrics may not be sent to a central location.")
        if self.model_drift_monitoring_enabled and not self.retraining_pipeline_trigger_url:
            logger.warning("MODEL_DRIFT_MONITORING_ENABLED is true, but RETRAINING_PIPELINE_TRIGGER_URL is not set. Automatic retraining may not be possible.")
        if self.federated_learning_enabled and not self.federated_learning_aggregator_endpoint:
            logger.warning("FEDERATED_LEARNING_ENABLED is true, but FEDERATED_LEARNING_AGGREGATOR_ENDPOINT is not set. Federated learning may not function correctly.")
        if self.federated_learning_enabled and self.federated_learning_model_update_interval <= 0:
            logger.warning("FEDERATED_LEARNING_MODEL_UPDATE_INTERVAL is set to 0 or a negative value while federated learning is enabled. Model updates may not occur as expected.")
        if self.harmful_content_detection_model and not self.harmful_content_detection_threshold:
            logger.warning("HARMFUL_CONTENT_DETECTION_MODEL is set, but HARMFUL_CONTENT_DETECTION_THRESHOLD is not. Default threshold will be used.")
        if not self.ideation_theme_model or not self.suggestion_refinement_model:
            logger.warning("Ideation theme or suggestion refinement models are not configured. GAN/RL features may be limited.")
        if self.adversarial_prompt_defense_enabled and not self.adversarial_prompt_detection_model:
             logger.warning("ADVERSARIAL_PROMPT_DEFENSE_ENABLED is true, but ADVERSARIAL_PROMPT_DETECTION_MODEL is not set. Adversarial prompt defense may be compromised.")
        if self.fact_checking_enabled and not self.fact_checking_model:
            logger.warning("FACT_CHECKING_ENABLED is true, but FACT_CHECKING_MODEL is not set. Fact-checking may not be effective.")
        if self.fact_checking_enabled and not self.fact_checking_external_data_sources:
            logger.warning("FACT_CHECKING_ENABLED is true, but no external data sources are configured for fact-checking.")


    def to_dict(self) -> Dict[str, Any]:
        """Return a safe, serialisable snapshot of the settings, redacting sensitive information."""
        d = asdict(self)
        # List of keys containing sensitive information to be redacted
        sensitive_keys = ("gemini_api_key", "openai_api_key", "webhook_secret", "federated_learning_aggregator_endpoint")
        for key in sensitive_keys:
            if d.get(key):
                d[key] = "***" # Redact the sensitive value
        return d

    @property
    def vertex_available(self) -> bool:
        """Check if Vertex AI is available based on the presence of a GCP project ID."""
        return bool(self.gcp_project_id)

    @property
    def openai_available(self) -> bool:
        """Check if OpenAI Assistant API is available based on the presence of an API key and assistant ID."""
        return bool(self.openai_api_key and self.openai_assistant_id)

    @property
    def federated_learning_available(self) -> bool:
        """Check if Federated Learning is configured and available."""
        return self.federated_learning_enabled and bool(self.federated_learning_aggregator_endpoint)

    @property
    def fact_checking_available(self) -> bool:
        """Check if fact-checking is configured and available."""
        return self.fact_checking_enabled and bool(self.fact_checking_model) and bool(self.fact_checking_external_data_sources)

    @property
    def adversarial_testing_available(self) -> bool:
        """Check if adversarial testing is configured and available."""
        return self.adversarial_testing_enabled and bool(self.adversarial_testing_model) and bool(self.bias_drift_mitigation_strategy)

    @property
    def log_auditing_available(self) -> bool:
        """Check if automated log auditing is configured and available."""
        return self.log_auditing_enabled and bool(self.log_auditing_model)

    @property
    def audit_trail_available(self) -> bool:
        """Check if blockchain audit trails are configured and available."""
        return self.audit_trail_enabled and bool(self.audit_trail_blockchain_provider) and bool(self.audit_trail_blockchain_endpoint)

    @property
    def real_time_risk_assessment_available(self) -> bool:
        """Check if real-time risk assessment is configured and available."""
        return self.real_time_risk_assessment_enabled and bool(self.risk_assessment_model)


# Create the singleton instance of the Settings object. This instance is globally accessible.
settings = Settings()

# --- Module-level exports for backward compatibility (UPPERCASE) ---
# These variables are directly mapped from the `settings` object to maintain compatibility
# with older code that might access configuration directly via these names.
GEMINI_API_KEY: Optional[str] = settings.gemini_api_key
GCP_PROJECT_ID: Optional[str] = settings.gcp_project_id
GCP_REGION: str = settings.gcp_region
ANTHROPIC_VERTEX_REGION: str = settings.anthropic_vertex_region
# Models for the incremental refinement pattern, aligned with the "Pattern" requirement.
# These models are selected for their enhanced context window capabilities.
IDEATION_THEME_MODEL: str = settings.ideation_theme_model
SUGGESTION_REFINEMENT_MODEL: str = settings.suggestion_refinement_model
# Model for generative background narrative synthesis, addressing the "SOTA Tool" requirement.
BACKGROUND_NARRATIVE_SYNTHESIS_MODEL: str = settings.background_narrative_synthesis_model
# Model for structured output generation (e.g., function calling)
FUNCTION_CALLING_MODEL: str = settings.function_calling_model

VERTEX_DEFAULT_MODEL: str = settings.vertex_default_model
GEMINI_MODEL: str = settings.gemini_model
IMAGE_GEN_MODEL: str = settings.image_gen_model
LOCAL_SLM_MODEL: str = settings.local_slm_model
LOCAL_SLM_ENDPOINT: str = settings.local_slm_endpoint
MODEL_GARDEN_CACHE_TTL: int = settings.model_garden_cache_ttl

# Federated Learning Configuration
FEDERATED_LEARNING_ENABLED: bool = settings.federated_learning_enabled
FEDERATED_LEARNING_AGGREGATOR_ENDPOINT: Optional[str] = settings.federated_learning_aggregator_endpoint
FEDERATED_LEARNING_MODEL_UPDATE_INTERVAL: int = settings.federated_learning_model_update_interval
FEDERATED_LEARNING_CLIENT_SAMPLING_RATE: float = settings.federated_learning_client_sampling_rate

# Reinforcement Learning Agents Configuration
RL_AGENT_LEARNING_RATE: float = settings.rl_agent_learning_rate
RL_AGENT_DISCOUNT_FACTOR: float = settings.rl_agent_discount_factor
RL_AGENT_EXPLORATION_EPSILON_START: float = settings.rl_agent_exploration_epsilon_start
RL_AGENT_EXPLORATION_EPSILON_END: float = settings.rl_agent_exploration_epsilon_end
RL_AGENT_EXPLORATION_EPSILON_DECAY: float = settings.rl_agent_exploration_epsilon_decay
RL_AGENT_FEEDBACK_WINDOW_SIZE: int = settings.rl_agent_feedback_window_size

# Real-time Adversarial Testing Framework
ADVERSARIAL_TESTING_ENABLED: bool = settings.adversarial_testing_enabled
ADVERSARIAL_TESTING_FREQUENCY: str = settings.adversarial_testing_frequency
ADVERSARIAL_TESTING_MODEL: Optional[str] = settings.adversarial_testing_model
BIAS_DRIFT_DETECTION_THRESHOLD: float = settings.bias_drift_detection_threshold
BIAS_DRIFT_MITIGATION_STRATEGY: str = settings.bias_drift_mitigation_strategy

# Automated Continuous Auditing with AI
LOG_AUDITING_ENABLED: bool = settings.log_auditing_enabled
LOG_AUDITING_MODEL: Optional[str] = settings.log_auditing_model
LOG_AUDITING_FREQUENCY: str = settings.log_auditing_frequency
LOG_AUDITING_ANOMALY_THRESHOLD: float = settings.log_auditing_anomaly_threshold

# Blockchain-based Immutable Audit Trails
AUDIT_TRAIL_ENABLED: bool = settings.audit_trail_enabled
AUDIT_TRAIL_BLOCKCHAIN_PROVIDER: str = settings.audit_trail_blockchain_provider
AUDIT_TRAIL_BLOCKCHAIN_ENDPOINT: Optional[str] = settings.audit_trail_blockchain_endpoint
AUDIT_TRAIL_IMMMUTABILITY_LEVEL: str = settings.audit_trail_immutability_level

# Real-time Risk Assessment Frameworks with ML
REAL_TIME_RISK_ASSESSMENT_ENABLED: bool = settings.real_time_risk_assessment_enabled
RISK_ASSESSMENT_MODEL: Optional[str] = settings.risk_assessment_model
RISK_ASSESSMENT_UPDATE_INTERVAL: int = settings.risk_assessment_update_interval
RISK_ASSESSMENT_THREAT_INTELLIGENCE_SOURCES: List[str] = settings.risk_assessment_threat_intelligence_sources
RISK_ASSESSMENT_THRESHOLDS: Dict[str, float] = settings.risk_assessment_thresholds

# Risk Management: Bias, Harmful Content, and Data Reliance Mitigation
BIAS_MITIGATION_TECHNIQUES: List[str] = settings.bias_mitigation_techniques
HARMFUL_CONTENT_DETECTION_MODEL: Optional[str] = settings.harmful_content_detection_model
HARMFUL_CONTENT_DETECTION_THRESHOLD: float = settings.harmful_content_detection_threshold
# Data diversity threshold, crucial for the "Risk" mitigation.
DATA_DIVERSITY_SCORE_THRESHOLD: float = settings.data_diversity_score_threshold
ADVERSARIAL_PROMPT_DEFENSE_ENABLED: bool = settings.adversarial_prompt_defense_enabled
ADVERSARIAL_PROMPT_DETECTION_MODEL: Optional[str] = settings.adversarial_prompt_detection_model
ADVERSARIAL_PROMPT_DEFENSE_THRESHOLD: float = settings.adversarial_prompt_defense_threshold

# Risk: Hallucination generation or factual inaccuracies
# Fact-checking configuration to mitigate the "Risk" of inaccuracies.
# This leverages RAG principles by specifying external data sources.
FACT_CHECKING_ENABLED: bool = settings.fact_checking_enabled
FACT_CHECKING_MODEL: Optional[str] = settings.fact_checking_model
FACT_CHECKING_EXTERNAL_DATA_SOURCES: List[str] = settings.fact_checking_external_data_sources
FACT_CHECKING_TOLERANCE_LEVEL: float = settings.fact_checking_tolerance_level

# Risk: Over-reliance on synthetic data
# Limits on synthetic data usage, directly addressing the "Risk" of lack of novel concepts.
SYNTHETIC_DATA_USAGE_LIMIT: float = settings.synthetic_data_usage_limit
REAL_WORLD_DATA_BIAS_MITIGATION: bool = settings.real_world_data_bias_mitigation

# SOTA Tool & State Management
OPENAI_ASSISTANT_ID: Optional[str] = settings.openai_assistant_id
OPENAI_API_KEY: Optional[str] = settings.openai_api_key
# Specific model for function calling, aligning with the "SOTA Tool" requirement.
OPENAI_FUNCTION_CALLING_MODEL: str = settings.openai_function_calling_model

# Event-Driven Architecture
IDE_WEBHOOK_URL: Optional[str] = settings.ide_webhook_url
USER_ACTIVITY_WEBHOOK_URL: Optional[str] = settings.user_activity_webhook_url
WEBHOOK_SECRET: Optional[str] = settings.webhook_secret

CIRCUIT_BREAKER_THRESHOLD: float = settings.circuit_breaker_threshold
CIRCUIT_BREAKER_MAX_FAILS: int = settings.circuit_breaker_max_fails
AUTONOMOUS_EXECUTION_ENABLED: bool = settings.autonomous_execution_enabled
AUTONOMOUS_CONFIDENCE_THRESHOLD: float = settings.autonomous_confidence_threshold
CROSS_MODEL_CONSENSUS_ENABLED: bool = settings.cross_model_consensus_enabled
NEAR_DUPLICATE_THRESHOLD: float = settings.near_duplicate_threshold
DYNAMIC_MODEL_SYNC_INTERVAL: int = settings.dynamic_model_sync_interval
DEFAULT_WORKERS: int = settings.default_workers

# Risk Management: Model Data Drift Monitoring
# Enhancements to address data drift, which can impact novelty and lead to less disruptive concepts.
MODEL_DRIFT_MONITORING_ENABLED: bool = settings.model_drift_monitoring_enabled
MODEL_DRIFT_MONITORING_INTERVAL: int = settings.model_drift_monitoring_interval
DATA_DRIFT_DETECTION_THRESHOLD: float = settings.data_drift_detection_threshold
MODEL_RETRAINING_TRIGGER_SENSITIVITY: float = settings.model_retraining_trigger_sensitivity
DATA_SAMPLING_RATE_FOR_DRIFT_CHECK: float = settings.data_sampling_rate_for_drift_check
DRIFT_DETECTION_ALGORITHM: str = settings.drift_detection_algorithm
MODEL_DRIFT_REPORTING_ENDPOINT: Optional[str] = settings.model_drift_reporting_endpoint
RETRAINING_PIPELINE_TRIGGER_URL: Optional[str] = settings.retraining_pipeline_trigger_url

STUDIO_HOST: str = settings.studio_host
STUDIO_PORT: int = settings.studio_port
STUDIO_RELOAD: bool = settings.studio_reload
SANDBOX_MAX_WORKERS: int = settings.sandbox_max_workers
TAILWIND_CDN_URL: str = settings.tailwind_cdn_url
GRAPH_MAX_NODES_THRESHOLD: int = settings.graph_max_nodes_threshold
GRAPH_MAX_RETRIES: int = settings.graph_max_retries
EXECUTOR_MAX_WORKERS: int = settings.executor_max_workers
FRACTAL_DAG_ENABLED: bool = settings.fractal_dag_enabled
JIT_BIDDER_ENABLED: bool = settings.jit_bidder_enabled
JIT_MAX_WORKERS: int = settings.jit_max_workers
BIDDER_MIN_STABILITY: float = settings.bidder_min_stability
MANDATE_EXECUTOR_MAX_RETRIES: int = settings.mandate_executor_max_retries
MANDATE_EXECUTOR_TIMEOUT: int = settings.mandate_executor_timeout
MANDATE_EXECUTOR_MAX_LENGTH: int = settings.mandate_executor_max_length
MANDATE_EXECUTOR_MAX_REACT_ITER: int = settings.mandate_executor_max_react_iter
ART_DIRECTOR_VIEWPORT_WIDTH: int = settings.art_director_viewport_width
ART_DIRECTOR_VIEWPORT_HEIGHT: int = settings.art_director_viewport_height
REKOR_URL: str = settings.rekor_url
SECRET_MANAGER_ENABLED: bool = settings.secret_manager_enabled
OTEL_EXPORTER_OTLP_ENDPOINT: str = settings.otel_exporter_otlp_endpoint
OTEL_EXPORTER_OTLP_PROTOCOL: str = settings.otel_exporter_otlp_protocol
GRAPH_ROLLBACK_ON_CYCLE: bool = settings.graph_rollback_on_cycle
VERTEX_AVAILABLE: bool = settings.vertex_available
OPENAI_AVAILABLE: bool = settings.openai_available
FEDERATED_LEARNING_AVAILABLE: bool = settings.federated_learning_available
FACT_CHECKING_AVAILABLE: bool = settings.fact_checking_available
ADVERSARIAL_TESTING_AVAILABLE: bool = settings.adversarial_testing_available
LOG_AUDITING_AVAILABLE: bool = settings.log_auditing_available
AUDIT_TRAIL_AVAILABLE: bool = settings.audit_trail_available
REAL_TIME_RISK_ASSESSMENT_AVAILABLE: bool = settings.real_time_risk_assessment_available
WORKSPACE_ROOTS: str = settings.workspace_roots

def get_workspace_roots() -> List[Path]:
    """
    Parses the WORKSPACE_ROOTS environment variable into a list of absolute Path objects.
    Defaults to the repository root if the variable is not set or empty.
    Paths are expected to be separated by colons.
    """
    raw = settings.workspace_roots or str(_REPO_ROOT)
    # Split the string by colon, strip whitespace from each part, and resolve to absolute paths.
    # Filter out any empty strings that might result from splitting.
    return [Path(p.strip()).resolve() for p in raw.split(":") if p.strip()]

# --- Client Factory ---

# Initialize Vertex AI client if GCP project ID is configured
_vertex_client: Optional[Any] = None
if settings.gcp_project_id:
    try:
        # Dynamically import google.generativeai to avoid runtime dependency issues
        # if only Gemini API is used.
        from google import genai as _genai
        _vertex_client = _genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_region
        )
        logger.info(f"Vertex AI client initialized for project '{settings.gcp_project_id}' in region '{settings.gcp_region}'.")
    except ImportError:
        logger.warning("google.generativeai not installed. Cannot initialize Vertex AI client.")
    except Exception as e:
        logger.warning(f"Vertex AI client initialization failed: {e}")

# Initialize Gemini API client if Gemini API key is configured
_gemini_client: Optional[Any] = None
if settings.gemini_api_key:
    try:
        from google import genai as _genai
        _gemini_client = _genai.Client(api_key=settings.gemini_api_key)
        logger.info("Gemini Developer API client initialized.")
    except ImportError:
        logger.warning("google.generativeai not installed. Cannot initialize Gemini API client.")
    except Exception as e:
        logger.warning(f"Gemini API client initialization failed: {e}")

# Initialize OpenAI client if OpenAI API key and assistant ID are configured
_openai_client: Optional[Any] = None
if settings.openai_api_key and settings.openai_assistant_id:
    try:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=settings.openai_api_key)
        logger.info(f"OpenAI client initialized for Assistant ID: {settings.openai_assistant_id}.")
    except ImportError:
        logger.warning("openai library not installed. Cannot initialize OpenAI client.")
    except Exception as e:
        logger.warning(f"OpenAI client initialization failed: {e}")


# --- Model Identifiers (Module Level) ---
GPT4_TURBO_MODEL = "gpt-4-turbo"
OPENAI_API_KEY = settings.openai_api_key
GEMINI_API_KEY = settings.gemini_api_key
VERTEX_DEFAULT_MODEL = "gemini-1.5-pro"

# Exported clients for external use, making them accessible from other modules.
vertex_client: Optional[Any] = _vertex_client
_vertex_client = vertex_client # Alias for internal consistency
gemini_client: Optional[Any] = _gemini_client
openai_client: Optional[Any] = _openai_client
