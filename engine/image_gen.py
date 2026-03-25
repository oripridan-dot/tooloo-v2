"""
engine/image_gen.py — Gemini-powered image generation engine.

Uses the unified google-genai Vertex client from engine/config to generate
images via Gemini native image generation (gemini-2.5-flash-image).
"""
from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Style enrichment prefixes ────────────────────────────────────────────────
_STYLE_PREFIXES: dict[str, str] = {
    "cinematic": "cinematic lighting, dramatic composition, film grain, 8K, photorealistic",
    "anime": "anime art style, vibrant colors, cel-shaded, Studio Ghibli inspired",
    "photorealistic": "ultra-photorealistic, DSLR quality, 8K resolution, natural lighting",
    "watercolor": "watercolor painting style, soft edges, wet-on-wet technique, artistic",
    "oil_painting": "oil painting on canvas, thick brush strokes, rich textures, classical art",
    "digital_art": "digital art, vibrant neon colors, futuristic, concept art, trending on ArtStation",
    "sketch": "pencil sketch, detailed linework, cross-hatching, charcoal drawing",
    "3d_render": "3D render, octane render, volumetric lighting, hyper-detailed, unreal engine",
    "pixel_art": "pixel art style, 16-bit retro aesthetic, limited color palette",
    "pop_art": "pop art style, bold colors, halftone dots, Andy Warhol inspired",
}

# ── Supported aspect ratios → google-genai image_config format ───────────────
_ASPECT_RATIOS: dict[str, str] = {
    "1:1": "1:1",
    "16:9": "16:9",
    "9:16": "9:16",
    "4:3": "4:3",
    "3:4": "3:4",
}


@dataclass
class ImageGenResult:
    """Result from a single image generation call."""
    image_bytes: bytes = b""
    image_base64: str = ""
    aspect_ratio: str = "1:1"
    style: str = "cinematic"
    enriched_prompt: str = ""
    model_used: str = ""
    latency_ms: float = 0.0
    error: str = ""
    success: bool = False


class ImageGenEngine:
    """Encapsulates Gemini native image generation via google-genai."""

    def __init__(self) -> None:
        from engine.config import (
            vertex_client,
            VERTEX_AVAILABLE,
            GEMINI_API_KEY,
        )
        self._vertex_client = vertex_client
        self._vertex_available = VERTEX_AVAILABLE
        self._gemini_api_key = GEMINI_API_KEY
        self._fallback_client: Any = None

        # Try to build a Gemini Direct fallback client if Vertex is unavailable
        if not self._vertex_available and self._gemini_api_key:
            try:
                from google import genai as _genai
                self._fallback_client = _genai.Client(
                    api_key=self._gemini_api_key
                )
                logger.info("ImageGenEngine: Gemini Direct (API key) fallback ready")
            except Exception as exc:
                logger.warning("ImageGenEngine: failed to init Gemini Direct: %s", exc)

    @staticmethod
    def enrich_prompt(prompt: str, style: str) -> str:
        """Prepend a style directive to the user prompt."""
        prefix = _STYLE_PREFIXES.get(style, "")
        if prefix:
            return f"{prefix}. {prompt}"
        return prompt

    @staticmethod
    def available_styles() -> list[dict[str, str]]:
        """Return list of available style options with labels."""
        return [
            {"id": k, "label": k.replace("_", " ").title()}
            for k in _STYLE_PREFIXES
        ]

    @staticmethod
    def available_aspect_ratios() -> list[str]:
        """Return list of supported aspect ratios."""
        return list(_ASPECT_RATIOS.keys())

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        style: str = "cinematic",
    ) -> ImageGenResult:
        """Generate an image from a text prompt.

        1. Enrich the prompt with style-specific directives.
        2. Try Vertex AI client first, then Gemini Direct fallback.
        3. Return raw bytes + base64 encoded string.
        """
        from engine.config import IMAGE_GEN_MODEL
        t0 = time.perf_counter()

        enriched = self.enrich_prompt(prompt, style)
        ar = _ASPECT_RATIOS.get(aspect_ratio, "16:9")

        result = ImageGenResult(
            aspect_ratio=aspect_ratio,
            style=style,
            enriched_prompt=enriched,
        )

        # Try each client in priority order
        for client_label, client in self._get_clients():
            if client is None:
                continue
            try:
                image_bytes = self._call_generate(client, enriched, ar, IMAGE_GEN_MODEL)
                if image_bytes:
                    result.image_bytes = image_bytes
                    result.image_base64 = base64.b64encode(image_bytes).decode("ascii")
                    result.model_used = f"{client_label}/{IMAGE_GEN_MODEL}"
                    result.success = True
                    result.latency_ms = (time.perf_counter() - t0) * 1000
                    logger.info(
                        "ImageGenEngine: generated via %s in %.0fms (style=%s, ar=%s)",
                        client_label, result.latency_ms, style, aspect_ratio,
                    )
                    return result
            except Exception as exc:
                logger.warning("ImageGenEngine: %s failed: %s", client_label, exc)
                result.error = f"{client_label}: {exc}"

        # All clients failed
        result.latency_ms = (time.perf_counter() - t0) * 1000
        if not result.error:
            result.error = "No image generation client available (Vertex AI credentials or GEMINI_API_KEY required)"
        return result

    def _get_clients(self) -> list[tuple[str, Any]]:
        """Return ordered list of (label, client) pairs to try."""
        clients: list[tuple[str, Any]] = []
        if self._vertex_available and self._vertex_client:
            clients.append(("vertex", self._vertex_client))
        if self._fallback_client:
            clients.append(("gemini-direct", self._fallback_client))
        return clients

    @staticmethod
    def _call_generate(client: Any, prompt: str, aspect_ratio: str, model: str) -> bytes:
        """Call the google-genai client to generate an image."""
        from google.genai import types

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["Image"],
                iGenerateImagesConfig=types.GenerateImagesConfig(
                    aspect_ratio=aspect_ratio,
                ),
            ),
        )

        # Extract PNG bytes from the response
        if response and response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "inline_data") and part.inline_data:
                            return part.inline_data.data
        return b""
