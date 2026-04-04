# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: DESIGN_KNOWLEDGE_INJECTOR | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/design_knowledge_injector.py
# WHEN: 2026-04-04T08:00:00.000000
# WHY: Injects latest SOTA design paradigms JIT without storing dusty static references.
# HOW: Uses KnowledgeGateway to fetch 'design_knowledge' and append to prompt context.
# TIER: T2:operational
# PURITY: 1.00
# ==========================================================

import logging
from tooloo_v4_hub.kernel.governance.knowledge_gateway import get_knowledge_gateway

logger = logging.getLogger("DesignInjector")

class DesignKnowledgeInjector:
    """
    Acts as a middleware for LLM clients to dynamically inject SOTA design rules
    (e.g., Glassmorphism, animations) straight from the concensused server.
    """
    def __init__(self):
        self.gateway = get_knowledge_gateway()

    async def get_design_context(self) -> str:
        """Fetches and formats design knowledge JIT."""
        try:
            design_data = await self.gateway.fetch_json("design_knowledge")
            if not design_data:
                return "SOTA Design: Use premium aesthetics (modern fonts, tailored colors, glassmorphism)."
                
            rules = design_data.get("core_rules", [])
            context = "SOTA DESIGN PARADIGMS:\n" + "\n".join(f"- {rule}" for rule in rules)
            return context
        except Exception as e:
            logger.error(f"Failed to fetch JIT design knowledge: {e}")
            return "SOTA Design rules unavailable. Fallback to basic premium heuristics."

_injector = None
def get_design_injector() -> DesignKnowledgeInjector:
    global _injector
    if _injector is None:
        _injector = DesignKnowledgeInjector()
    return _injector
