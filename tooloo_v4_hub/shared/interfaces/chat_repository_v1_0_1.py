# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_CHAT_REPOSITORY.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/shared/interfaces/chat_repository.py
# WHEN: 2026-04-04T00:41:42.522444+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

from abc import ABC, abstractmethod
from typing import List, Optional
from tooloo_v4_hub.kernel.cognitive.protocols import SovereignMessage

class IChatRepository(ABC):
    """
    Interface for Chat Persistence Layer.
    Enforces Rule 13 (Physical Decoupling).
    """

    @abstractmethod
    def store_message(self, message: SovereignMessage) -> None:
        """Persists a SovereignMessage to the physical layer."""
        pass

    @abstractmethod
    def get_history(self, limit: int = 100) -> List[SovereignMessage]:
        """Retrieves history up to limit."""
        pass
