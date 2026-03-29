# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: KERNEL_STAMPING_v3.0.0 — The 6W Protocol
# WHERE: tooloo-v3-hub/kernel/stamping.py
# WHEN: 2026-03-29T09:18:00.000000
# WHY: Single Source of 6W-Verification Truth
# HOW: Pure Sovereign Infrastructure Protocol
# ==========================================================

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class SixWProtocol(BaseModel):
    """
    The strict 6W Stamping Protocol for the Sovereign Cognitive Engine V3.
    Required for all artifacts, engrams, and execution nodes.
    """
    who: str = Field(..., description="The originating agent or principal architect ID")
    what: str = Field(..., description="Action, payload, or intent identifier")
    where: str = Field(..., description="Execution environment or logical sector")
    when: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    why: str = Field(..., description="The teleological goal or parent mandate")
    how: str = Field(..., description="The procedural strategy or tool vector used")
    
    # Procedural Payload Hash (Deep-6W)
    payload_hash: Optional[str] = Field(None, description="SHA-256 hash of the execution payload")
    
    # Optional signature for cryptographic attestation
    signature: Optional[str] = Field(None, description="Cryptographic signature of the stamp")
    
    # --- Sovereign Telemetry ---
    em_verified: bool = Field(False, description="Whether the artifact passed the Verification Gate")
    telemetry: Dict[str, Any] = Field(default_factory=dict, description="Captured EM_actual metrics")

    def to_stamp_header(self) -> str:
        """Generates the standardized 6W_STAMP comment block."""
        header = (
            f"# 6W_STAMP\n"
            f"# WHO: {self.who}\n"
            f"# WHAT: {self.what}\n"
            f"# WHERE: {self.where}\n"
            f"# WHEN: {self.when}\n"
            f"# WHY: {self.why}\n"
            f"# HOW: {self.how}\n"
        )
        if self.payload_hash:
            header += f"# HASH: {self.payload_hash}\n"
        header += f"# =========================================================="
        return header

    class Config:
        frozen = True # Stamping is immutable once issued

class StampingEngine:
    """
    Automates 6W Stamping across the TooLoo V3 system.
    Ensures 100% metadata coverage for generated and processed code.
    """
    
    _STAMP_MARKER = "# 6W_STAMP"

    @staticmethod
    def get_environment() -> str:
        """Detects the current execution environment with a focus on GCP services."""
        import os
        
        # 1. Cloud Run
        if os.environ.get("K_SERVICE"):
            return "gcp-cloud-run"
        
        # 2. Vertex AI / AI Platform
        if os.environ.get("AIP_MODE") or os.environ.get("CLOUD_ML_JOB_ID"):
            return "gcp-vertex-ai"
            
        # 3. Google Cloud Shell / GCE
        if os.path.exists("/home/google-cloud-sdk"):
             return "gcp-compute-engine"
             
        # 4. Fallback to Local/Universal
        return "local-mac-workspace"
    
    @staticmethod
    def is_stamped(content: str) -> bool:
        """Check if the content starts with a 6W stamp."""
        return content.strip().startswith(StampingEngine._STAMP_MARKER)

    @staticmethod
    def extract_metadata(content: str) -> Optional[Dict[str, str]]:
        """Extract existing 6W metadata from a file's header."""
        if not StampingEngine.is_stamped(content):
            return None
            
        header = content.split("="*58)[0]
        patterns = {
            "who": r"# WHO:\s*(.*)",
            "what": r"# WHAT:\s*(.*)",
            "where": r"# WHERE:\s*(.*)",
            "when": r"# WHEN:\s*(.*)",
            "why": r"# WHY:\s*(.*)",
            "how": r"# HOW:\s*(.*)",
        }
        
        metadata = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, header)
            if match:
                metadata[key] = match.group(1).strip()
        return metadata

    @staticmethod
    def stamp_file(path: str, protocol: SixWProtocol) -> bool:
        """Prepend a 6W stamp to a file."""
        file_path = Path(path)
        if not file_path.exists():
            return False
            
        content = file_path.read_text()
            
        if StampingEngine.is_stamped(content):
            # V3 Rule: Do not restamp if already stamped, unless it's an explicit update
            return False
            
        stamp = protocol.to_stamp_header()
        new_content = f"{stamp}\n\n{content}"
        
        file_path.write_text(new_content)
        return True

    @staticmethod
    def audit_hub(hub_path: str = "tooloo-v3-hub") -> Dict[str, List[str]]:
        """Audit the V3 Hub for 6W compliance."""
        report = {"stamped": [], "unstamped": []}
        root = Path(hub_path)
        
        for file in root.rglob("*.py"):
            content = file.read_text()
            if StampingEngine.is_stamped(content):
                report["stamped"].append(str(file))
            else:
                report["unstamped"].append(str(file))
        return report

    @staticmethod
    def compute_payload_hash(payload: Any) -> str:
        """Computes a SHA-256 hash for an arbitrary payload (Deep-6W)."""
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()

if __name__ == "__main__":
    # Self-stamping the protocol itself
    p = SixWProtocol(
        who="TooLoo V3 (Sovereign Architect)",
        what="KERNEL_STAMPING_v3.0.0",
        where="tooloo-v3-hub/kernel/stamping.py",
        why="Single Source of 6W-Verification Truth",
        how="Pure Sovereign Infrastructure Protocol"
    )
    print(p.to_stamp_header())
