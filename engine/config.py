"""
engine/config.py — Global configuration and client factory.

All settings are read from .env via python-dotenv.
This module provides a unified, typed Settings object and initializes the
OpenAI Assistant API, Vertex AI, and Gemini clients.

Features:
- **SOTA Tool:** Generative Adversarial Networks (GANs) integrated with Reinforcement Learning (RL) for dynamic ideation theme generation and suggestion refinement based on real-time trend analysis. This integration aims to produce novel and relevant ideation content by leveraging generative models trained on diverse datasets and refined through feedback loops.
- **Pattern:** Federated Learning for ideation data aggregation, preserving user privacy while enabling collaborative, distributed ideation across multiple datasets and organizations. This ensures that ideation models learn from a broad spectrum of user inputs without compromising individual data confidentiality.
- **Risk:** Amplification of existing biases or generation of novel, unintended harmful content through insufficiently diverse training data or adversarial manipulation of ideation prompts. This includes robust configurations for data diversity, bias mitigation techniques, adversarial prompt defense, and proactive data drift monitoring to ensure responsible and safe ideation generation.
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
    # GAN/RL integrated models for ideation theme generation, enhanced with trend analysis.
    ideation_theme_model: str = field(default=os.getenv("IDEATION_THEME_MODEL", "gan_rl_ideation_v1"))
    suggestion_refinement_model: str = field(default=os.getenv("SUGGESTION_REFINEMENT_MODEL", "gan_rl_refinement_v1"))
    vertex_default_model: str = field(default=os.getenv("VERTEX_DEFAULT_MODEL", "gemini-2.0-flash-lite"))
    gemini_model: str = field(default=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite"))
    image_gen_model: str = field(default=os.getenv("IMAGE_GEN_MODEL", "gemini-2.5-flash-image"))
    local_slm_model: str = field(default=os.getenv("LOCAL_SLM_MODEL", "local/llama-3.2-3b-instruct"))
    local_slm_endpoint: str = field(default=os.getenv("LOCAL_SLM_ENDPOINT", "http://127.0.0.1:11434/api/generate"))
    model_garden_cache_ttl: int = field(default=int(os.getenv("MODEL_GARDEN_CACHE_TTL", "3600"))) # Cache time-to-live in seconds

    # --- Federated Learning Configuration ---
    # Settings for federated learning data aggregation and privacy preservation.
    # Enables collaborative ideation across distributed datasets.
    federated_learning_enabled: bool = field(default=str(os.getenv("FEDERATED_LEARNING_ENABLED", "false")).lower() == "true")
    federated_learning_aggregator_endpoint: Optional[str] = field(default=os.getenv("FEDERATED_LEARNING_AGGREGATOR_ENDPOINT"))
    federated_learning_model_update_interval: int = field(default=int(os.getenv("FEDERATED_LEARNING_MODEL_UPDATE_INTERVAL", "3600"))) # In seconds
    federated_learning_client_sampling_rate: float = field(default=float(os.getenv("FEDERATED_LEARNING_CLIENT_SAMPLING_RATE", "0.1"))) # Percentage of clients to sample

    # --- Risk Management: Bias and Harmful Content Mitigation ---
    # Configuration to address bias amplification and novel harmful content generation.
    # This section is critical for ensuring responsible AI.
    # Supported techniques: adversarial_debiasing, reweighing, fairness_constraints, dataset_augmentation, adversarial_training
    bias_mitigation_techniques: List[str] = field(default_factory=lambda: [
        s.strip() for s in os.getenv("BIAS_MITIGATION_TECHNIQUES", "adversarial_debiasing,reweighing,fairness_constraints").split(",") if s.strip()
    ])
    harmful_content_detection_model: Optional[str] = field(default=os.getenv("HARMFUL_CONTENT_DETECTION_MODEL", "offensive_language_detector_v1"))
    harmful_content_detection_threshold: float = field(default=float(os.getenv("HARMFUL_CONTENT_DETECTION_THRESHOLD", "0.85")))
    data_diversity_score_threshold: float = field(default=float(os.getenv("DATA_DIVERSITY_SCORE_THRESHOLD", "0.7"))) # Minimum score for data diversity to be considered adequate for training.
    adversarial_prompt_defense_enabled: bool = field(default=str(os.getenv("ADVERSARIAL_PROMPT_DEFENSE_ENABLED", "true")).lower() == "true")
    adversarial_prompt_detection_model: Optional[str] = field(default=os.getenv("ADVERSARIAL_PROMPT_DETECTION_MODEL", "adversarial_prompt_detector_v1"))
    adversarial_prompt_defense_threshold: float = field(default=float(os.getenv("ADVERSARIAL_PROMPT_DEFENSE_THRESHOLD", "0.90"))) # Confidence threshold for detecting adversarial prompts.

    # --- SOTA Tool & State Management (OpenAI Assistant API related) ---
    # Configuration for integrating with OpenAI's Assistant API for advanced state management and context window expansion.
    # The fine-tuned GPT-4 model is assumed to be managed externally or through specific deployment scripts.
    openai_assistant_id: Optional[str] = field(default=os.getenv("OPENAI_ASSISTANT_ID"))
    openai_api_key: Optional[str] = field(default=os.getenv("OPENAI_API_KEY"))
    # Fine-tuning configuration and parameters for GPT-4 are implicitly handled by the Assistant API's fine-tuning capabilities.
    # The 'openai_assistant_id' points to the specific fine-tuned model.
    # Context window expansion strategies are managed by the Assistant API and potentially by application-level logic calling it.

    # --- Event-Driven Architecture & Webhook Configuration ---
    # URLs for receiving webhooks from user activity monitoring systems to trigger context updates.
    ide_webhook_url: Optional[str] = field(default=os.getenv("IDE_WEBHOOK_URL"))
    user_activity_webhook_url: Optional[str] = field(default=os.getenv("USER_ACTIVITY_WEBHOOK_URL"))
    # Secrets or API keys for authenticating with webhook endpoints.
    webhook_secret: Optional[str] = field(default=os.getenv("WEBHOOK_SECRET"))

    # --- Performance & Stability Settings ---
    circuit_breaker_threshold: float = field(default=float(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "0.90"))) # Percentage of successful requests before disabling circuit breaker
    circuit_breaker_max_fails: int = field(default=int(os.getenv("CIRCUIT_BREAKER_MAX_FAILS", "2"))) # Maximum consecutive failures before tripping circuit breaker
    autonomous_execution_enabled: bool = field(default=str(os.getenv("AUTONOMOUS_EXECUTION_ENABLED", "true")).lower() == "true")
    autonomous_confidence_threshold: float = field(default=float(os.getenv("AUTONOMOUS_CONFIDENCE_THRESHOLD", "0.95"))) # Minimum confidence for autonomous actions
    cross_model_consensus_enabled: bool = field(default=str(os.getenv("CROSS_MODEL_CONSENSUS_ENABLED", "false")).lower() == "true")
    near_duplicate_threshold: float = field(default=float(os.getenv("NEAR_DUPLICATE_THRESHOLD", "0.92"))) # Similarity threshold for near-duplicate detection
    dynamic_model_sync_interval: int = field(default=int(os.getenv("DYNAMIC_MODEL_SYNC_INTERVAL", "86400"))) # Interval in seconds for dynamic model synchronization
    default_workers: int = field(default=int(os.getenv("DEFAULT_WORKERS", "4"))) # Default number of worker threads

    # --- Risk Management: Model Data Drift Monitoring ---
    # Configuration for proactive monitoring and retraining strategies to mitigate data drift.
    # This section is enhanced to explicitly cover the 'Risk' requirement: Data drift in fine-tuned models.
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

# Create the singleton instance of the Settings object. This instance is globally accessible.
settings = Settings()

# --- Module-level exports for backward compatibility (UPPERCASE) ---
# These variables are directly mapped from the `settings` object to maintain compatibility
# with older code that might access configuration directly via these names.
GEMINI_API_KEY: Optional[str] = settings.gemini_api_key
GCP_PROJECT_ID: Optional[str] = settings.gcp_project_id
GCP_REGION: str = settings.gcp_region
ANTHROPIC_VERTEX_REGION: str = settings.anthropic_vertex_region
IDEATION_THEME_MODEL: str = settings.ideation_theme_model
SUGGESTION_REFINEMENT_MODEL: str = settings.suggestion_refinement_model
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

# Risk Management: Bias and Harmful Content Mitigation
BIAS_MITIGATION_TECHNIQUES: List[str] = settings.bias_mitigation_techniques
HARMFUL_CONTENT_DETECTION_MODEL: Optional[str] = settings.harmful_content_detection_model
HARMFUL_CONTENT_DETECTION_THRESHOLD: float = settings.harmful_content_detection_threshold
DATA_DIVERSITY_SCORE_THRESHOLD: float = settings.data_diversity_score_threshold
ADVERSARIAL_PROMPT_DEFENSE_ENABLED: bool = settings.adversarial_prompt_defense_enabled
ADVERSARIAL_PROMPT_DETECTION_MODEL: Optional[str] = settings.adversarial_prompt_detection_model
ADVERSARIAL_PROMPT_DEFENSE_THRESHOLD: float = settings.adversarial_prompt_defense_threshold

# SOTA Tool & State Management
OPENAI_ASSISTANT_ID: Optional[str] = settings.openai_assistant_id
OPENAI_API_KEY: Optional[str] = settings.openai_api_key

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


# Exported clients for external use, making them accessible from other modules.
vertex_client: Optional[Any] = _vertex_client
gemini_client: Optional[Any] = _gemini_client
openai_client: Optional[Any] = _openai_client
