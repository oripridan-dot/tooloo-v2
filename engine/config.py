"""
engine/config.py — All configuration read from .env via python-dotenv.
Never read os.environ directly outside this module.
"""
from __future__ import annotations

import os
from pathlib import Path

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
    _get("CIRCUIT_BREAKER_THRESHOLD", "0.85"))
CIRCUIT_BREAKER_MAX_FAILS: int = int(_get("CIRCUIT_BREAKER_MAX_FAILS", "3"))

# ── Executor ──────────────────────────────────────────────────────────────────
EXECUTOR_MAX_WORKERS: int = int(_get("EXECUTOR_MAX_WORKERS", "8"))

# ── Sandbox ───────────────────────────────────────────────────────────────────
SANDBOX_MAX_WORKERS: int = int(_get("SANDBOX_MAX_WORKERS", "25"))


class _Settings:  # noqa: N801  (simple namespace)
    gemini_api_key = GEMINI_API_KEY
    gemini_model = GEMINI_MODEL
    gcp_project_id = GCP_PROJECT_ID
    gcp_region = GCP_REGION
    vertex_default_model = VERTEX_DEFAULT_MODEL
    vertex_available = _VERTEX_AVAILABLE
    anthropic_vertex_region = ANTHROPIC_VERTEX_REGION
    cross_model_consensus_enabled = CROSS_MODEL_CONSENSUS_ENABLED
    model_garden_cache_ttl = MODEL_GARDEN_CACHE_TTL
    studio_host = STUDIO_HOST
    studio_port = STUDIO_PORT
    studio_reload = STUDIO_RELOAD
    circuit_breaker_threshold = CIRCUIT_BREAKER_THRESHOLD
    circuit_breaker_max_fails = CIRCUIT_BREAKER_MAX_FAILS
    executor_max_workers = EXECUTOR_MAX_WORKERS
    sandbox_max_workers = SANDBOX_MAX_WORKERS


settings = _Settings()
