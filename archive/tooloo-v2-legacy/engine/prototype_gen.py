# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.prototype_gen.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/prototype_gen.py — Generates live, interactive HTML/CSS/JS prototypes.

Uses Gemini text generation to produce complete, self-contained HTML documents
that can be rendered inside an <iframe srcdoc="..."> on the Studio canvas.
The user never sees code — they see a real, clickable, scrollable UI.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Premium design tokens injected into every prototype ──────────────────────
_DESIGN_SYSTEM = """
/* TooLoo Design System — injected into every prototype */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    -webkit-font-smoothing: antialiased;
    line-height: 1.6;
}
img { max-width: 100%; display: block; }
button { cursor: pointer; font-family: inherit; }
a { text-decoration: none; color: inherit; }
"""

_SYSTEM_PROMPT = """You are TooLoo's Prototype Engine — a world-class frontend engineer.

Your ONLY job is to produce a COMPLETE, SELF-CONTAINED HTML document.

RULES:
1. Output ONLY valid HTML. No markdown, no explanations, no code fences.
2. The HTML must start with <!DOCTYPE html> and end with </html>.
3. ALL CSS must be in a <style> tag in <head>. ALL JS in a <script> tag before </body>.
4. Use modern CSS (grid, flexbox, custom properties, clamp(), container queries).
5. Make it RESPONSIVE (mobile-first, looks great at 375px and 1440px).
6. Use PREMIUM aesthetics:
   - Subtle gradients and shadows (no flat/boring designs)
   - Smooth micro-animations (hover states, transitions, entrance animations)
   - Modern typography with proper hierarchy
   - Generous whitespace and visual rhythm
7. Use REAL placeholder content — realistic text, proper pricing, actual feature names.
   For images, use Unsplash URLs: https://images.unsplash.com/photo-{id}?w=600&fit=crop
   (Use these real Unsplash IDs: 1441986300917-64674bd600d8, 1506905925346-21bda4d32df4, 1517245386807-bb43f82c33c4, 1523275335684-37898b6baf30, 1472851294608-062f824d29cc, 1544005313-94ddf0286df2)
8. Make interactive elements WORK: buttons with hover effects, nav toggles, smooth scrolls.
9. Include the following base CSS reset at the START of your <style> block:
{design_system}
10. The document MUST be completely self-contained. No external JS libraries.
11. Use semantic HTML5 elements (header, nav, main, section, footer).
12. Add subtle entrance animations using CSS @keyframes.

When iterating on a previous prototype, preserve the overall structure and only modify
the specific elements the user asked to change. Keep everything else intact.
"""


@dataclass
class PrototypeResult:
    """Result from a prototype generation call."""
    html: str = ""
    latency_ms: float = 0.0
    error: str = ""
    success: bool = False


class PrototypeGenEngine:
    """Generates interactive HTML prototypes using Gemini text generation."""

    def __init__(self) -> None:
        from engine.config import _vertex_client, VERTEX_DEFAULT_MODEL
        self._client = _vertex_client
        self._model = VERTEX_DEFAULT_MODEL

    def generate(
        self,
        prompt: str,
        previous_html: str = "",
        context: str = "",
    ) -> PrototypeResult:
        """Generate or iterate on an HTML prototype.

        Args:
            prompt: The user's design request.
            previous_html: If iterating, the current prototype HTML to modify.
            context: Additional session context (conversation history, etc.)

        Returns:
            PrototypeResult with the complete HTML document.
        """
        t0 = time.perf_counter()
        result = PrototypeResult()

        if not self._client:
            result.error = "No AI client available."
            return result

        system = _SYSTEM_PROMPT.format(design_system=_DESIGN_SYSTEM)

        user_parts = []
        if previous_html:
            user_parts.append(
                f"Here is the CURRENT prototype HTML to iterate on:\n"
                f"```html\n{previous_html}\n```\n\n"
                f"The user wants the following changes:\n{prompt}"
            )
        else:
            user_parts.append(f"Create a prototype for:\n{prompt}")

        if context:
            user_parts.append(f"\nSession context:\n{context}")

        user_content = "\n".join(user_parts)

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[system, user_content],
            )

            html = response.text.strip()

            # Strip markdown code fences if the model wrapped them
            if html.startswith("```html"):
                html = html[7:]
            if html.startswith("```"):
                html = html[3:]
            if html.endswith("```"):
                html = html[:-3]
            html = html.strip()

            # Validate it looks like HTML
            if not html.startswith("<!DOCTYPE") and not html.startswith("<html"):
                result.error = "Generated output does not look like valid HTML."
                result.html = html  # Store it anyway for debugging
                return result

            result.html = html
            result.success = True
            result.latency_ms = (time.perf_counter() - t0) * 1000
            logger.info("PrototypeGenEngine: generated in %.0fms", result.latency_ms)

        except Exception as exc:
            logger.exception("PrototypeGenEngine: generation failed: %s", exc)
            result.error = str(exc)
            result.latency_ms = (time.perf_counter() - t0) * 1000

        return result
