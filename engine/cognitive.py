import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator
from enum import Enum

# Strict Enums prevent the system from hallucinating new components or reasons
class SystemAgency(str, Enum):
    ROUTER = "router"
    EXECUTOR = "executor"
    BUDDY_CACHE = "buddy_cache"
    TRIBUNAL = "tribunal"
    SOTA_INGESTION = "sota_ingestion"
    USER = "user"

class ExecutionIntent(str, Enum):
    """Causal intent behind the execution."""
    CALIBRATION = "CALIBRATION"
    MEMORY_RETRIEVAL = "MEMORY_RETRIEVAL"
    CODE_GENERATION = "CODE_GENERATION"
    ERROR_CORRECTION = "ERROR_CORRECTION"
    BUILD = "BUILD"
    DEBUG = "DEBUG"
    AUDIT = "AUDIT"
    DESIGN = "DESIGN"
    EXPLAIN = "EXPLAIN"
    IDEATE = "IDEATE"
    GENERAL_MANDATE = "general_mandate" # Added to support standard mandates

class CognitiveCoordinate(BaseModel):
    # The 6Ws
    when: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    where: str = Field(..., description="Namespace, filepath, or vector node ID")
    what: str = Field(..., max_length=200, description="Exact state, data point, or title")
    how: str = Field(..., description="Execution trace or pipeline route taken")
    why: ExecutionIntent = Field(..., description="The causal intent of the action")
    who: SystemAgency = Field(..., description="The module or actor initiating this")
    
    # The Heavy Payload (Decoupled from Vector Search)
    raw_payload: Dict[str, Any] = Field(default_factory=dict, description="The heavy execution data/code")
    
    # The Deterministic Hash (Generated automatically)
    hash_id: Optional[str] = None

    @model_validator(mode='after')
    def generate_deterministic_hash(self) -> 'CognitiveCoordinate':
        """Automatically locks the memory with a SHA-256 hash before execution."""
        if not self.hash_id:
            # Create a unique signature based on Time, Location, Agency, and Payload
            # We sort keys in payload to ensure deterministic hashing
            payload_json = json.dumps(self.raw_payload, sort_keys=True)
            signature = f"{self.when.isoformat()}-{self.where}-{self.who.value}-{payload_json}"
            self.hash_id = hashlib.sha256(signature.encode('utf-8')).hexdigest()
        return self

    def to_metadata(self) -> Dict[str, Any]:
        """Returns lightweight metadata for Vector DB indexing."""
        return {
            "hash_id": self.hash_id,
            "when": self.when.isoformat(),
            "where": self.where,
            "what": self.what,
            "how": self.how,
            "why": self.why.value,
            "who": self.who.value
        }
