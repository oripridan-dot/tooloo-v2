# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining local_slm_client.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.930227
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/local_slm_client.py — Sub-Ollama Local SLM Integration

Supports lightweight local language models for Tier 0 (free, no API cost) execution:
  - llama.cpp: CPU-efficient inference, 4-40B models, 50-200 tokens/sec
  - MLX: Apple Silicon optimized, 3-7B models, 100-300 tokens/sec
  - Ollama with tiny models: 1-3B models (TinyLlama, Phi-2, Zephyr)

Integration with ModelGarden for aggressive Tier 0 routing:
  - Parsing, linting, routing, formatting: Tier 0 local SLM
  - Test writing, validation: Tier 0 local SLM
  - Heavy reasoning/coding: Tier 1+ cloud models

Target: $0 cost, <100ms latency, 95% first-task accuracy on syntactic tasks.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


@dataclass
class LocalSLMConfig:
    """Configuration for a local SLM instance."""

    name: str  # "llama.cpp" | "mlx" | "ollama"
    endpoint: str  # HTTP endpoint (e.g., http://localhost:8000)
    model_name: str  # Model identifier (e.g., "mistral-7b-q4")
    max_tokens: int = 200
    temperature: float = 0.1  # Low temp for determinism
    timeout_sec: int = 30


class LocalSLMClient:
    """
    HTTP client for local SLM inference.

    Provides unified interface to llama.cpp, MLX, and Ollama with tiny models.
    Falls back gracefully if local SLM is unavailable (returns RuntimeError).
    """

    def __init__(self, config: LocalSLMConfig) -> None:
        self.config = config

    def test_connectivity(self) -> bool:
        """Test if the local SLM endpoint is reachable."""
        try:
            payload = {"prompt": "test", "n_predict": 1}
            req = urlrequest.Request(
                self.config.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlrequest.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (URLError, HTTPError, TimeoutError):
            pass
        return False

    def generate(self, prompt: str, max_tokens: int | None = None) -> str:
        """
        Generate text using the local SLM.

        Args:
            prompt: Input text
            max_tokens: Override default max_tokens for this call

        Returns:
            Generated response

        Raises:
            RuntimeError if the local SLM is unavailable or fails
        """
        tokens = max_tokens or self.config.max_tokens

        if self.config.name == "llama.cpp":
            return self._call_llamacpp(prompt, tokens)
        elif self.config.name == "mlx":
            return self._call_mlx(prompt, tokens)
        elif self.config.name == "ollama":
            return self._call_ollama(prompt, tokens)
        else:
            raise ValueError(f"Unknown SLM backend: {self.config.name}")

    def _call_llamacpp(self, prompt: str, max_tokens: int) -> str:
        """Call llama.cpp server (completion endpoint)."""
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": self.config.temperature,
            "top_p": 0.9,
        }
        req = urlrequest.Request(
            f"{self.config.endpoint}/completion",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=self.config.timeout_sec) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("content", "").strip()
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as e:
            raise RuntimeError(
                f"llama.cpp call failed at {self.config.endpoint}: {e}"
            ) from e

    def _call_mlx(self, prompt: str, max_tokens: int) -> str:
        """Call MLX server (OpenAI-compatible /v1/chat/completions endpoint)."""
        payload = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": self.config.temperature,
        }
        req = urlrequest.Request(
            f"{self.config.endpoint}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=self.config.timeout_sec) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                if body.get("choices"):
                    return body["choices"][0].get("message", {}).get("content", "").strip()
                return ""
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as e:
            raise RuntimeError(
                f"MLX call failed at {self.config.endpoint}: {e}"
            ) from e

    def _call_ollama(self, prompt: str, max_tokens: int) -> str:
        """Call Ollama server (generate endpoint)."""
        payload = {
            "model": self.config.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": self.config.temperature,
            },
        }
        req = urlrequest.Request(
            f"{self.config.endpoint}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=self.config.timeout_sec) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("response", "").strip()
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as e:
            raise RuntimeError(
                f"Ollama call failed at {self.config.endpoint}: {e}"
            ) from e

    def benchmark(self, num_runs: int = 3) -> dict[str, Any]:
        """
        Benchmark the local SLM's latency and throughput.

        Returns:
            {"tokens_per_sec": float, "latency_ms": float, "status": str}
        """
        test_prompt = "What is 2+2? Answer in one word."
        latencies: list[float] = []

        for _ in range(num_runs):
            try:
                start = time.time()
                response = self.generate(test_prompt, max_tokens=10)
                latency_ms = (time.time() - start) * 1000
                latencies.append(latency_ms)

                if response:
                    # Estimate tokens (rough: ~4 chars per token)
                    tokens = len(response) / 4
                    tokens_per_sec = tokens / \
                        (latency_ms / 1000) if latency_ms > 0 else 0
                else:
                    tokens_per_sec = 0

            except RuntimeError:
                return {
                    "tokens_per_sec": 0,
                    "latency_ms": 0,
                    "status": "unavailable",
                }

        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        return {
            "tokens_per_sec": tokens_per_sec if latencies else 0,
            "latency_ms": avg_latency,
            "status": "ok" if latencies else "timeout",
        }


# ── Recommended Configurations ───────────────────────────────────────────────

def get_default_configs() -> dict[str, LocalSLMConfig]:
    """Return recommended configuration defaults for each backend."""
    return {
        "llama.cpp": LocalSLMConfig(
            name="llama.cpp",
            endpoint="http://localhost:8000",
            model_name="mistral-7b-q4",  # 4-bit quantized, ~4GB RAM
            max_tokens=256,
            temperature=0.1,
            timeout_sec=30,
        ),
        "mlx": LocalSLMConfig(
            name="mlx",
            endpoint="http://localhost:8000",
            model_name="Mistral-7B-Instruct-v0.2",
            max_tokens=256,
            temperature=0.1,
            timeout_sec=30,
        ),
        "ollama": LocalSLMConfig(
            name="ollama",
            endpoint="http://localhost:11434",
            model_name="tinyllama",  # 1-3B parameter model
            max_tokens=256,
            temperature=0.1,
            timeout_sec=30,
        ),
    }


# ── Setup Instructions ───────────────────────────────────────────────────────

SETUP_INSTRUCTIONS = """
# Setting Up Tier 0 Local SLM

Choose one of: llama.cpp, MLX, or Ollama.

## Option 1: llama.cpp (Recommended)
CPU-efficient, works on any architecture.

1. Download llama.cpp:
   git clone https://github.com/ggerganov/llama.cpp
   cd llama.cpp && make

2. Download a quantized model:
   # 7B model, 4GB RAM, ~100 tokens/sec
   wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/Mistral-7B-Instruct-v0.2.Q4_K_M.gguf
   
3. Start the server:
   ./llama-server -m Mistral-7B-Instruct-v0.2.Q4_K_M.gguf -ngl 33 --port 8000

## Option 2: MLX (Apple Silicon Only)
Optimized for M-series chips (faster than llama.cpp on your Mac).

1. Install MLX:
   pip install mlx-lm

2. Start the server:
   mlx_lm.server --model Mistral-7B-Instruct-v0.2 --port 8000

## Option 3: Ollama
Simple Docker-like wrapper for local models.

1. Install: brew install ollama (or docker run ollama/ollama)

2. Pull a tiny model:
   ollama pull tinyllama  # 1.3B parameters

3. Start server:
   ollama serve  # Runs on port 11434 by default

---

## Testing Tier 0 Connectivity

from engine.local_slm_client import LocalSLMClient, get_default_configs

configs = get_default_configs()
client = LocalSLMClient(configs["llama.cpp"])  # or "mlx" or "ollama"

# Test connectivity
if client.test_connectivity():
    print("Tier 0 local SLM is online!")
    
# Benchmark
bench = client.benchmark()
print(f"Throughput: {bench['tokens_per_sec']:.1f} tokens/sec")
print(f"Latency: {bench['latency_ms']:.0f}ms")

# Generate
response = client.generate("What is Python?")
print(response)
"""
