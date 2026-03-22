# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────
# Cycle: 2026-03-20T20:02:43.976217+00:00
# Component: config  Source: engine/config.py
# Improvement signals from JIT SOTA booster:
#  [1] Validate engine/config.py: OWASP Top 10 2025 edition promotes Broken Object-
#     Level Authorisation to the #1 priority
#  [2] Validate engine/config.py: OSS supply-chain audits (Sigstore + Rekor
#     transparency log) are required in regulated environments
#  [3] Validate engine/config.py: CSPM tools (Wiz, Orca, Prisma Cloud) provide real-
#     time cloud posture scoring in 2026
# ─────────────────────────────────────────────────────────────────
"""
engine/config.py — All configuration read from .env via python-dotenv.
Never read os.environ directly outside this module.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    # override=True ensures .env values always win over empty/unset env vars
    # in the dev-container environment (important for GEMINI_API_KEY).
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
except ImportError:
    pass


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# ── Gemini Developer API (fallback when Vertex ADC is absent) ────────────────
GEMINI_API_KEY: str = _get("GEMINI_API_KEY")

# ── Google Cloud / Vertex AI Model Garden ────────────────────────────────────
GCP_PROJECT_ID: str = _get("GCP_PROJECT_ID")
GCP_REGION: str = _get("GCP_REGION", "us-central1")

# Anthropic Claude via Vertex AI — region must be us-east5 or europe-west1.
ANTHROPIC_VERTEX_REGION: str = _get("ANTHROPIC_VERTEX_REGION", "")

# ModelGarden runtime settings
# CROSS_MODEL_CONSENSUS_ENABLED: run 2 providers in parallel at T4 for validation.
CROSS_MODEL_CONSENSUS_ENABLED: bool = (
    _get("CROSS_MODEL_CONSENSUS_ENABLED", "false").lower() == "true"
)
MODEL_GARDEN_CACHE_TTL: int = int(_get("MODEL_GARDEN_CACHE_TTL", "3600"))
LOCAL_SLM_MODEL: str = _get("LOCAL_SLM_MODEL", "local/llama-3.2-3b-instruct")
LOCAL_SLM_ENDPOINT: str = _get(
    "LOCAL_SLM_ENDPOINT", "http://127.0.0.1:11434/api/generate")

# VERTEX_DEFAULT_MODEL is the single-shot default used by legacy helpers
# (JITBooster, ConversationEngine) when no explicit tier model is requested.
# ModelGarden.get_tier_models_static() computes the full 4-tier ladder at
# import time — these values are its computed T1 fallback.
VERTEX_DEFAULT_MODEL: str = _get(
    "VERTEX_DEFAULT_MODEL", "gemini-2.5-flash-lite")

# GEMINI_MODEL mirrors VERTEX_DEFAULT_MODEL so the Gemini Direct fallback path
# always uses the same generation as the primary Vertex path.
GEMINI_MODEL: str = _get("GEMINI_MODEL", VERTEX_DEFAULT_MODEL)

# Initialise unified google-genai Vertex client once at import time; no-op when credentials absent.
_VERTEX_AVAILABLE: bool = False
_vertex_client = None
if GCP_PROJECT_ID:
    try:
        # type: ignore[import-untyped]
        from google import genai as _genai_vertex
        _vertex_client = _genai_vertex.Client(
            vertexai=True, project=GCP_PROJECT_ID, location=GCP_REGION
        )
        _VERTEX_AVAILABLE = True
    except Exception:  # pragma: no cover
        pass

# ── Studio ────────────────────────────────────────────────────────────────────
STUDIO_HOST: str = _get("STUDIO_HOST", "0.0.0.0")
STUDIO_PORT: int = int(_get("STUDIO_PORT", "8002"))
STUDIO_RELOAD: bool = _get("STUDIO_RELOAD", "false").lower() == "true"

# ── Circuit breaker ───────────────────────────────────────────────────────────
CIRCUIT_BREAKER_THRESHOLD: float = float(
    # Raised to 0.9 per OWASP 2026 resilience baseline
    _get("CIRCUIT_BREAKER_THRESHOLD", "0.9"))
CIRCUIT_BREAKER_MAX_FAILS: int = int(_get("CIRCUIT_BREAKER_MAX_FAILS", "3"))

# ── Law 20 (Amended) — Autonomous Execution Authority ────────────────────────
# When AUTONOMOUS_EXECUTION_ENABLED=true TooLoo may approve and apply its own
# engine improvements without waiting for explicit human confirmation.
# Safety invariants that always hold regardless of this flag:
#   • Tribunal OWASP scan runs on every generated artefact.
#   • All writes are sandboxed to engine/ components inside this workspace.
#   • Activity is restricted to legal, non-criminal operations only.
AUTONOMOUS_EXECUTION_ENABLED: bool = (
    _get("AUTONOMOUS_EXECUTION_ENABLED", "true").lower() == "true"
)
AUTONOMOUS_CONFIDENCE_THRESHOLD: float = float(
    _get("AUTONOMOUS_CONFIDENCE_THRESHOLD", "0.95")
)

# ── Vector Store ─────────────────────────────────────────────────────────────
# NEAR_DUPLICATE_THRESHOLD: cosine-similarity cutoff above which two documents
# are considered near-duplicates and the newer insert is rejected.
# Raise toward 1.0 to allow more similar docs; lower to increase deduplication.
NEAR_DUPLICATE_THRESHOLD: float = float(
    _get("NEAR_DUPLICATE_THRESHOLD", "0.92"))
# ── Dynamic Model Registry & JIT 16D Bidder ─────────────────────────────────
# Sync interval for Vertex AI model discovery (seconds). Default: 1 day.
DYNAMIC_MODEL_SYNC_INTERVAL: int = int(
    _get("DYNAMIC_MODEL_SYNC_INTERVAL", "86400"))
# Enable per-node JIT 16D bidding in the N-Stroke pipeline.
JIT_BIDDER_ENABLED: bool = _get("JIT_BIDDER_ENABLED", "true").lower() == "true"
# Enable fractal DAG expansion for failed nodes.
FRACTAL_DAG_ENABLED: bool = _get(
    "FRACTAL_DAG_ENABLED", "true").lower() == "true"
# Minimum stability score for models participating in bidding.
BIDDER_MIN_STABILITY: float = float(_get("BIDDER_MIN_STABILITY", "0.85"))
# ── Executor ──────────────────────────────────────────────────────────────────
EXECUTOR_MAX_WORKERS: int = int(_get("EXECUTOR_MAX_WORKERS", "8"))

# ── Sandbox ───────────────────────────────────────────────────────────────────
SANDBOX_MAX_WORKERS: int = int(_get("SANDBOX_MAX_WORKERS", "25"))


# ── OpenTelemetry (microservice observability) ───────────────────────────────
OTEL_EXPORTER_OTLP_ENDPOINT: str = _get(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
)
OTEL_EXPORTER_OTLP_PROTOCOL: str = _get(
    "OTEL_EXPORTER_OTLP_PROTOCOL", "grpc"
)

# ── Multi-root workspace ───────────────────────────────────────────────────────
# WORKSPACE_ROOTS: colon-separated list of absolute or workspace-relative paths.
# Defaults to the repository root (one level above engine/).
# Example .env entry:  WORKSPACE_ROOTS=/workspace:/mnt/shared-libs
_REPO_ROOT: Path = Path(__file__).resolve().parents[1]
WORKSPACE_ROOTS: str = _get("WORKSPACE_ROOTS", str(_REPO_ROOT))


def get_workspace_roots() -> list[Path]:
    """Return the ordered list of workspace root paths from WORKSPACE_ROOTS."""
    raw = WORKSPACE_ROOTS or str(_REPO_ROOT)
    return [Path(p.strip()).resolve() for p in raw.split(":") if p.strip()]


@dataclass
class _Settings:
    """Immutable configuration snapshot — single source of truth for all engine modules."""

    gemini_api_key: str = GEMINI_API_KEY
    gemini_model: str = GEMINI_MODEL
    gcp_project_id: str = GCP_PROJECT_ID
    gcp_region: str = GCP_REGION
    vertex_default_model: str = VERTEX_DEFAULT_MODEL
    vertex_available: bool = _VERTEX_AVAILABLE
    anthropic_vertex_region: str = ANTHROPIC_VERTEX_REGION
    cross_model_consensus_enabled: bool = CROSS_MODEL_CONSENSUS_ENABLED
    model_garden_cache_ttl: int = MODEL_GARDEN_CACHE_TTL
    local_slm_model: str = LOCAL_SLM_MODEL
    local_slm_endpoint: str = LOCAL_SLM_ENDPOINT
    studio_host: str = STUDIO_HOST
    studio_port: int = STUDIO_PORT
    studio_reload: bool = STUDIO_RELOAD
    circuit_breaker_threshold: float = CIRCUIT_BREAKER_THRESHOLD
    circuit_breaker_max_fails: int = CIRCUIT_BREAKER_MAX_FAILS
    autonomous_execution_enabled: bool = AUTONOMOUS_EXECUTION_ENABLED
    autonomous_confidence_threshold: float = AUTONOMOUS_CONFIDENCE_THRESHOLD
    dynamic_model_sync_interval: int = DYNAMIC_MODEL_SYNC_INTERVAL
    jit_bidder_enabled: bool = JIT_BIDDER_ENABLED
    fractal_dag_enabled: bool = FRACTAL_DAG_ENABLED
    bidder_min_stability: float = BIDDER_MIN_STABILITY
    executor_max_workers: int = EXECUTOR_MAX_WORKERS
    sandbox_max_workers: int = SANDBOX_MAX_WORKERS
    near_duplicate_threshold: float = NEAR_DUPLICATE_THRESHOLD
    OTEL_EXPORTER_OTLP_ENDPOINT: str = OTEL_EXPORTER_OTLP_ENDPOINT
    OTEL_EXPORTER_OTLP_PROTOCOL: str = OTEL_EXPORTER_OTLP_PROTOCOL
    workspace_roots: str = WORKSPACE_ROOTS

    def to_dict(self) -> dict[str, object]:
        """Return a safe, serialisable snapshot (secrets redacted)."""
        from dataclasses import asdict
        d = asdict(self)
        for key in ("gemini_api_key",):
            if d.get(key):
                d[key] = "***"
        return d

    def __repr__(self) -> str:
        return (
            f"_Settings(model={self.vertex_default_model!r}, "
            f"vertex={self.vertex_available}, "
            f"cb={self.circuit_breaker_threshold}, "
            f"autonomous={self.autonomous_execution_enabled})"
        )


_t_settings_start = time.perf_counter()
settings = _Settings()
_t_settings_ms = (time.perf_counter() - _t_settings_start) * 1000
logger.debug(
    "config loaded in %.2fms  vertex=%s  model=%s",
    _t_settings_ms, settings.vertex_available, settings.vertex_default_model,
)
