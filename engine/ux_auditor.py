# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.ux_auditor.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

import logging
import base64
from typing import Any, Dict, List
from engine.model_garden import get_garden
from engine.utils import extract_json

logger = logging.getLogger("ux_auditor")

_AESTHETIC_PROTOCOL = (
    "AESTHETIC PROTOCOL GAURENTEE:\n"
    "1. HSL Abyss: Backgrounds must be HSL(220, 20%, 5%)-ish, not #000.\n"
    "2. Glassmorphism: Active elements must use backdrop-filter: blur(10px).\n"
    "3. Typography: Primary font 'Outfit' or 'Inter'.\n"
    "4. Micro-interactivity: Every button must have a hover:scale transition.\n"
    "5. WCAG 2.2 Level AA: Minimum contrast 4.5:1."
)

class UXAuditor:
    """Vision-aware auditor for generated UI artifacts."""
    
    def __init__(self, model_id: str = "gemini-2.0-pro-exp-02-05"):
        self.garden = get_garden()
        # Fallback to T3 pro if specific model is unavailable
        self.model_id = model_id
        
    def audit_visual(self, screenshot_b64: str, vlt_json: Dict[str, Any]) -> Dict[str, Any]:
        """Performs a vision-based aesthetic audit on a UI screenshot."""
        logger.info("Initiating Vision-Aware Aesthetic Audit...")
        
        prompt = (
            f"You are the SOTA Art Director. Audit the attached UI screenshot. \n"
            f"Compare it against our Aesthetic Protocol:\n{_AESTHETIC_PROTOCOL}\n\n"
            f"Original VLT Blueprint:\n{vlt_json}\n\n"
            f"Respond with ONLY a JSON object containing:\n"
            f"- aesthetic_score: (0.0 - 1.0)\n"
            f"- protocol_violations: [list of missing HSL/Glassmorphism features]\n"
            f"- accessibility_warnings: [WCAG 2.2 AA gaps]\n"
            f"- verdict: 'APPROVED' | 'REJECTED'\n"
            f"- remediation_directives: [specific CSS fixes if REJECTED]"
        )
        
        try:
            # Construct multi-modal payload
            # (Note: model_garden handles multipart messages for Vision)
            contents = [
                {"type": "text", "text": prompt},
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64}}
            ]
            
            raw = self.garden.call(self.model_id, contents, intent="VALIDATE_UX")
            result = extract_json(raw)
            return result or {"aesthetic_score": 0.0, "verdict": "ERROR", "message": "Raw JSON parse failed."}
            
        except Exception as e:
            logger.error(f"UX Vision Audit failed: {e}")
            return {"aesthetic_score": 0.0, "verdict": "ERROR", "error": str(e)}

    def audit_code(self, html_content: str, css_content: str) -> Dict[str, Any]:
        """Performs a static code-based audit using HSL/Token heuristics."""
        violations = []
        if "hsl(" not in css_content.lower() and "var(--" not in css_content:
            violations.append("NON_TOKEN_COLORS: Missing HSL or CSS variables.")
        if "backdrop-filter" not in css_content:
            violations.append("MISSING_GLASSMORHISM: backdrop-filter not detected.")
        if "Outfit" not in css_content and "Inter" not in css_content:
            violations.append("TYPOGRAPHY_VIOLATION: Missing SOTA fonts.")
            
        return {
            "static_score": 1.0 - (len(violations) * 0.25),
            "violations": violations,
            "verdict": "APPROVED" if not violations else "NEEDS_REVISION"
        }
