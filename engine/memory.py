import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from engine.graph import CognitiveGraph

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages the persistence of CognitiveGraphs to the psyche_bank."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path(__file__).resolve().parents[1] / "psyche_bank"
        self.storage_dir.mkdir(exist_ok=True, parents=True)
        
    def save_graph(self, name: str, graph: CognitiveGraph) -> Path:
        """Saves a CognitiveGraph to a JSON file."""
        file_path = self.storage_dir / f"{name}_graph.json"
        try:
            data = graph.to_json_data()
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved graph '{name}' to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save graph '{name}': {e}")
            raise

    def load_graph(self, name: str) -> Optional[CognitiveGraph]:
        """Loads a CognitiveGraph from a JSON file."""
        file_path = self.storage_dir / f"{name}_graph.json"
        if not file_path.exists():
            logger.warning(f"Graph file {file_path} not found.")
            return None
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            graph = CognitiveGraph.from_json_data(data)
            logger.info(f"Loaded graph '{name}' from {file_path}")
            return graph
        except Exception as e:
            logger.error(f"Failed to load graph '{name}': {e}")
            return None

# Singleton instance for the engine
memory_manager = MemoryManager()
