"""tests/test_local_slm_client.py — Unit tests for engine/local_slm_client.py.

All tests run fully offline — HTTP calls are patched with unittest.mock.
Covers:
- LocalSLMConfig DTO
- LocalSLMClient.test_connectivity: reachable, unreachable
- LocalSLMClient.generate: llama.cpp, mlx, ollama dispatch, unknown backend
- LocalSLMClient.benchmark: success, unavailable
- Error normalisation (all network errors → RuntimeError)
"""
from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from engine.local_slm_client import LocalSLMClient, LocalSLMConfig


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client(name: str = "ollama", endpoint: str = "http://localhost:11434") -> LocalSLMClient:
    cfg = LocalSLMConfig(name=name, endpoint=endpoint,
                         model_name="phi-2", max_tokens=50)
    return LocalSLMClient(cfg)


def _mock_response(body: Any, status: int = 200):
    """Return a context-manager mock for urlopen."""
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = json.dumps(body).encode("utf-8")
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ── LocalSLMConfig ────────────────────────────────────────────────────────────

class TestLocalSLMConfig:
    def test_defaults(self):
        cfg = LocalSLMConfig(
            name="ollama", endpoint="http://localhost:11434", model_name="phi-2")
        assert cfg.max_tokens == 200
        assert cfg.temperature == 0.1
        assert cfg.timeout_sec == 30

    def test_custom_values(self):
        cfg = LocalSLMConfig(name="mlx", endpoint="http://localhost:8000",
                             model_name="mistral-7b", max_tokens=512, temperature=0.3)
        assert cfg.max_tokens == 512
        assert cfg.temperature == 0.3


# ── test_connectivity ─────────────────────────────────────────────────────────

class TestConnectivity:
    def test_reachable_returns_true(self):
        client = _make_client("ollama")
        with patch("engine.local_slm_client.urlrequest.urlopen") as mock_open:
            mock_open.return_value = _mock_response({"status": "ok"})
            assert client.test_connectivity() is True

    def test_unreachable_returns_false(self):
        from urllib.error import URLError
        client = _make_client("ollama")
        with patch("engine.local_slm_client.urlrequest.urlopen", side_effect=URLError("refused")):
            assert client.test_connectivity() is False

    def test_http_error_returns_false(self):
        from urllib.error import HTTPError
        client = _make_client("ollama")
        with patch("engine.local_slm_client.urlrequest.urlopen",
                   side_effect=HTTPError(url=None, code=500, msg="error", hdrs=None, fp=None)):
            assert client.test_connectivity() is False

    def test_timeout_returns_false(self):
        client = _make_client("ollama")
        with patch("engine.local_slm_client.urlrequest.urlopen", side_effect=TimeoutError()):
            assert client.test_connectivity() is False


# ── generate — Ollama ─────────────────────────────────────────────────────────

class TestGenerateOllama:
    def test_generate_returns_text(self):
        client = _make_client("ollama")
        body = {"response": "four"}
        with patch("engine.local_slm_client.urlrequest.urlopen") as mock_open:
            mock_open.return_value = _mock_response(body)
            result = client.generate("What is 2+2?")
        assert result == "four"

    def test_network_error_raises_runtime_error(self):
        from urllib.error import URLError
        client = _make_client("ollama")
        with patch("engine.local_slm_client.urlrequest.urlopen", side_effect=URLError("refused")):
            with pytest.raises(RuntimeError, match="Ollama call failed"):
                client.generate("test")

    def test_max_tokens_override(self):
        client = _make_client("ollama")
        body = {"response": "ok"}
        captured_payload: list[bytes] = []

        def _urlopen(req, timeout=None):
            captured_payload.append(req.data)
            return _mock_response(body)

        with patch("engine.local_slm_client.urlrequest.urlopen", side_effect=_urlopen):
            client.generate("test", max_tokens=99)

        sent = json.loads(captured_payload[0].decode())
        assert sent["options"]["num_predict"] == 99


# ── generate — llama.cpp ──────────────────────────────────────────────────────

class TestGenerateLlamaCpp:
    def test_llamacpp_returns_content(self):
        client = _make_client("llama.cpp", "http://localhost:8080")
        body = {"content": "the answer is 42"}
        with patch("engine.local_slm_client.urlrequest.urlopen") as mock_open:
            mock_open.return_value = _mock_response(body)
            result = client.generate("What is the answer?")
        assert result == "the answer is 42"

    def test_llamacpp_network_error_raises(self):
        from urllib.error import URLError
        client = _make_client("llama.cpp")
        with patch("engine.local_slm_client.urlrequest.urlopen", side_effect=URLError("refused")):
            with pytest.raises(RuntimeError, match="llama.cpp call failed"):
                client.generate("test")


# ── generate — MLX ───────────────────────────────────────────────────────────

class TestGenerateMLX:
    def test_mlx_returns_content(self):
        client = _make_client("mlx", "http://localhost:8000")
        body = {"choices": [{"message": {"content": "hello world"}}]}
        with patch("engine.local_slm_client.urlrequest.urlopen") as mock_open:
            mock_open.return_value = _mock_response(body)
            result = client.generate("Say hello")
        assert result == "hello world"

    def test_mlx_empty_choices_returns_empty_string(self):
        client = _make_client("mlx")
        body = {"choices": []}
        with patch("engine.local_slm_client.urlrequest.urlopen") as mock_open:
            mock_open.return_value = _mock_response(body)
            result = client.generate("test")
        assert result == ""

    def test_mlx_network_error_raises(self):
        from urllib.error import URLError
        client = _make_client("mlx")
        with patch("engine.local_slm_client.urlrequest.urlopen", side_effect=URLError("refused")):
            with pytest.raises(RuntimeError, match="MLX call failed"):
                client.generate("test")


# ── generate — unknown backend ────────────────────────────────────────────────

class TestGenerateUnknownBackend:
    def test_unknown_backend_raises_value_error(self):
        client = _make_client("unknown_backend")
        with pytest.raises(ValueError, match="Unknown SLM backend"):
            client.generate("test")


# ── benchmark ─────────────────────────────────────────────────────────────────

class TestBenchmark:
    def test_benchmark_success(self):
        client = _make_client("ollama")
        body = {"response": "four"}
        with patch("engine.local_slm_client.urlrequest.urlopen") as mock_open:
            mock_open.return_value = _mock_response(body)
            result = client.benchmark(num_runs=2)
        assert result["status"] in ("ok", None) or "tokens_per_sec" in result
        assert "latency_ms" in result

    def test_benchmark_unavailable(self):
        from urllib.error import URLError
        client = _make_client("ollama")
        with patch("engine.local_slm_client.urlrequest.urlopen", side_effect=URLError("refused")):
            result = client.benchmark(num_runs=1)
        assert result["status"] == "unavailable"
        assert result["latency_ms"] == 0
        assert result["tokens_per_sec"] == 0
