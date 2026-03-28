# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining creative_director.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.916794
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

# engine/creative_director.py
"""
Phase-aware Creative Director — Buddy's brain.

Manages a structured creative session through 4 phases:
  Discover → Design → Prototype → Ship

Buddy is proactive: it suggests phase transitions, explains decisions,
and keeps the user moving forward without ever exposing code.
"""
import json
import logging
from typing import Any, Dict

from engine.config import _vertex_client, VERTEX_DEFAULT_MODEL

logger = logging.getLogger(__name__)

PHASES = ["discover", "design", "prototype", "ship"]
PHASE_LABELS = {
    "discover": "💡 Discover",
    "design": "🎨 Design",
    "prototype": "⚙️ Prototype",
    "ship": "🚀 Ship",
}


class CreativeDirector:
    """
    Acts as the AI creative partner (Buddy) in the Studio UI.
    Phase-aware: generates different outputs depending on session stage.
    """

    def __init__(self):
        self._client = _vertex_client
        self._model = VERTEX_DEFAULT_MODEL

    def guide(
        self,
        user_prompt: str,
        phase: str,
        history: str = "",
        iteration_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Main entry point. Takes the user's message and current phase,
        returns Buddy's response including potential phase transitions.

        Returns a dict with keys:
          - response: Buddy's conversational message to display in chat
          - action: what to do next — "generate_image", "generate_prototype", "ask", "phase_change"
          - enhanced_prompt: the refined prompt for image/prototype generation
          - suggest_phase_change: bool — should Buddy suggest moving to next phase?
          - suggested_phase: the phase to suggest moving to
          - phase_reason: why Buddy suggests the change
          - next_steps: suggested next iterations
        """
        if not self._client:
            return self._offline_response(user_prompt, phase)

        system = self._build_system_prompt(phase, iteration_count)
        user_content = f"Phase: {phase}\nUser: {user_prompt}\n"
        if history:
            user_content += f"\nConversation so far:\n{history}\n"

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[system, user_content],
            )

            text = response.text.strip()
            # Clean markdown fences
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)
            return {
                "response": str(data.get("response", "Let's keep going.")),
                "action": str(data.get("action", "ask")),
                "enhanced_prompt": str(data.get("enhanced_prompt", user_prompt)),
                "suggest_phase_change": bool(data.get("suggest_phase_change", False)),
                "suggested_phase": str(data.get("suggested_phase", "")),
                "phase_reason": str(data.get("phase_reason", "")),
                "next_steps": str(data.get("next_steps", "What would you like to adjust?")),
            }

        except Exception as e:
            logger.error(f"CreativeDirector.guide failed: {e}")
            return self._offline_response(user_prompt, phase)

    def _build_system_prompt(self, phase: str, iteration_count: int) -> str:
        base = (
            "You are Buddy — TooLoo's AI Creative Director.\n"
            "You guide users from idea to finished product through phases: "
            "Discover → Design → Prototype → Ship.\n\n"
            "You MUST respond with valid JSON only (no markdown fences). Keys:\n"
            '  "response": Your conversational message to display in chat. Be warm, opinionated, and brief.\n'
            '  "action": One of "ask", "generate_image", "generate_prototype", "phase_change"\n'
            '  "enhanced_prompt": A detailed prompt for image/prototype generation (only if action is generate_*)\n'
            '  "suggest_phase_change": true/false — suggest moving to the next phase?\n'
            '  "suggested_phase": Which phase to suggest (only if suggest_phase_change is true)\n'
            '  "phase_reason": Brief reason for the phase change (only if suggest_phase_change is true)\n'
            '  "next_steps": A short question suggesting 1-2 ways to iterate or refine\n\n'
        )

        if phase == "discover":
            base += (
                "CURRENT PHASE: Discover.\n"
                "Your job: Understand what the user wants to build. Ask smart clarifying questions.\n"
                "After 2-3 exchanges, suggest moving to Design phase.\n"
                "Do NOT generate images yet — just chat.\n"
                'Set action to "ask" unless the user gives enough detail to start designing.\n'
                "If the user's request is clear enough from the start, suggest Design immediately.\n"
            )
        elif phase == "design":
            base += (
                "CURRENT PHASE: Design.\n"
                "Your job: Generate visual mockups. Describe what you're creating and why.\n"
                'Set action to "generate_image" when producing visuals.\n'
                f"This is iteration #{iteration_count + 1}.\n"
            )
            if iteration_count >= 2:
                base += (
                    "The user has iterated several times. Consider suggesting Prototype phase.\n"
                    "Say something like: 'This design is looking solid. Want to see it as a real, interactive prototype?'\n"
                )
        elif phase == "prototype":
            base += (
                "CURRENT PHASE: Prototype.\n"
                "Your job: Iterate on a live HTML/CSS/JS prototype. The user can interact with it.\n"
                'Set action to "generate_prototype" when building or updating the prototype.\n'
                "Explain your design decisions in plain language. Never mention code.\n"
                "Say things like 'I made the header sticky so it stays visible while scrolling' "
                "instead of 'I added position: sticky'.\n"
                f"This is iteration #{iteration_count + 1}.\n"
            )
        elif phase == "ship":
            base += (
                "CURRENT PHASE: Ship.\n"
                "Your job: Help the user finalize and export their project.\n"
                "Suggest final tweaks, offer to add SEO, favicon, etc.\n"
            )

        return base

    def _offline_response(self, user_prompt: str, phase: str) -> Dict[str, Any]:
        """Fallback when no AI client is available."""
        if phase == "discover":
            return {
                "response": "Tell me more about what you're building. Who is it for and what's the vibe?",
                "action": "ask",
                "enhanced_prompt": user_prompt,
                "suggest_phase_change": False,
                "suggested_phase": "",
                "phase_reason": "",
                "next_steps": "What's the primary purpose of this design?",
            }
        elif phase == "design":
            return {
                "response": f"I'm creating a mockup based on: {user_prompt}",
                "action": "generate_image",
                "enhanced_prompt": user_prompt,
                "suggest_phase_change": False,
                "suggested_phase": "",
                "phase_reason": "",
                "next_steps": "What would you like to change?",
            }
        else:
            return {
                "response": f"Building a prototype for: {user_prompt}",
                "action": "generate_prototype",
                "enhanced_prompt": user_prompt,
                "suggest_phase_change": False,
                "suggested_phase": "",
                "phase_reason": "",
                "next_steps": "What should we refine?",
            }
