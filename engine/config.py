"""
engine/config.py — All configuration read from .env via python-dotenv.
Never read os.environ directly outside this module.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
except ImportError:
    pass


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# ── LLM ───────────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = _get("GEMINI_API_KEY")
GEMINI_MODEL: str = _get("GEMINI_MODEL", "gemini-2.0-flash")

# ── GitHub ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN: str = _get("GITHUB_TOKEN")

# ── Studio ────────────────────────────────────────────────────────────────────
STUDIO_HOST: str = _get("STUDIO_HOST", "0.0.0.0")
STUDIO_PORT: int = int(_get("STUDIO_PORT", "8002"))
STUDIO_RELOAD: bool = _get("STUDIO_RELOAD", "false").lower() == "true"

# ── Circuit breaker ───────────────────────────────────────────────────────────
CIRCUIT_BREAKER_THRESHOLD: float = float(_get("CIRCUIT_BREAKER_THRESHOLD", "0.85"))
CIRCUIT_BREAKER_MAX_FAILS: int = int(_get("CIRCUIT_BREAKER_MAX_FAILS", "3"))

# ── Executor ──────────────────────────────────────────────────────────────────
EXECUTOR_MAX_WORKERS: int = int(_get("EXECUTOR_MAX_WORKERS", "8"))


class _Settings:  # noqa: N801  (simple namespace)
    gemini_api_key = GEMINI_API_KEY
    gemini_model = GEMINI_MODEL
    github_token = GITHUB_TOKEN
    studio_host = STUDIO_HOST
    studio_port = STUDIO_PORT
    studio_reload = STUDIO_RELOAD
    circuit_breaker_threshold = CIRCUIT_BREAKER_THRESHOLD
    circuit_breaker_max_fails = CIRCUIT_BREAKER_MAX_FAILS
    executor_max_workers = EXECUTOR_MAX_WORKERS


settings = _Settings()
