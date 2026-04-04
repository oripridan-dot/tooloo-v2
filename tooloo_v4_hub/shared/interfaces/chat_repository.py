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
