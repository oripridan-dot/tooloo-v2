# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MODULE_STAMPING | Version: 1.2.0
# WHERE: tooloo_v3_hub/kernel/governance/stamping.py
# WHEN: 2026-03-31T21:10:00.000000
# WHY: Empirical Measurement and Rule 16 Calibration (TooLoo Formula)
# HOW: 16D Intent Mapping and Emergence-Delta Fields
# TIER: T3:architectural-purity
# DOMAINS: governance, infrastructure, stamping, measurement, calibration
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class SixWProtocol(BaseModel):
    who: str = Field(..., description="Originating agent ID")
    what: str = Field(..., description="Action or intent identifier")
    where: str = Field(..., description="Logical sector or file path")
    when: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    why: str = Field(..., description="Teleological goal")
    how: str = Field(..., description="Procedural strategy")
    
    # Federated & Dimensional Extensions
    tier_link: Optional[str] = None
    domain_tokens: Optional[str] = None
    memory_nexus: Optional[str] = None
    purity_score: float = 1.0
    # Rule 16: Empirical Calibration & SOTA Performance
    predicted_v: Optional[float] = None
    actual_v: Optional[float] = None
    eval_delta: Optional[float] = None  # Predicted - Actual
    
    # SOTA Metrics
    latency_ms: Optional[float] = None
    token_count: Optional[int] = None
    thinking_effort: Optional[int] = None
    version: str = "1.3.0"
    trust_level: str = "T3:arch-purity"
    payload_hash: Optional[str] = None

    # TooLoo Formula: (C + I) / ENV = Emergence
    intent_16d: Dict[str, float] = Field(default_factory=dict, description="16D Constitutional Weight Vector")
    env_context: Dict[str, Any] = Field(default_factory=dict, description="Build target, hardware, latency context")
    
    # Rule 16: Empirical Calibration
    predicted_v: Optional[float] = None
    actual_v: Optional[float] = None
    eval_delta: Optional[float] = None  # Predicted - Actual

    def to_stamp_header(self, file_ext: str = ".py") -> str:
        prefix = "# "
        header_wrap = ""
        footer_wrap = ""
        
        if file_ext == ".html":
            prefix = ""
            header_wrap = "<!--\n"
            footer_wrap = "-->\n"
        elif file_ext in [".js", ".ts"]:
            prefix = "// "
        elif file_ext in [".css"]:
            prefix = " * "
            header_wrap = "/*\n"
            footer_wrap = " */\n"
            
        h = header_wrap
        h += f"{prefix}6W_STAMP\n"
        h += f"{prefix}WHO: {self.who}\n"
        h += f"{prefix}WHAT: {self.what} | Version: {self.version}\n"
        h += f"{prefix}WHERE: {self.where}\n"
        if self.predicted_v is not None:
             h += f"{prefix}PRED_V: {self.predicted_v:.4f}\n"
             if self.actual_v is not None:
                  h += f"{prefix}ACTUAL_V: {self.actual_v:.4f} | DELTA: {self.eval_delta:.4f}\n"
        h += f"{prefix}WHEN: {self.when}\n"
        h += f"{prefix}WHY: {self.why}\n"
        h += f"{prefix}HOW: {self.how}\n"
        h += f"{prefix}TRUST: {self.trust_level}\n"
        if self.tier_link: h += f"{prefix}TIER: {self.tier_link}\n"
        if self.domain_tokens: h += f"{prefix}DOMAINS: {self.domain_tokens}\n"
        h += f"{prefix}PURITY: {self.purity_score:.2f}\n"
        h += f"{prefix}==========================================================\n"
        h += footer_wrap
        return h.strip()

class StampingEngine:
    _STAMP_MARKER = "6W_STAMP"

    @staticmethod
    def is_stamped(content: str) -> bool:
        return StampingEngine._STAMP_MARKER in content[:500]

    @staticmethod
    def extract_metadata(content: str) -> Optional[Dict[str, str]]:
        if not StampingEngine.is_stamped(content): return None
        header_part = content.split("=====")[0]
        patterns = {
            "who": r"WHO:\s*(.*)",
            "what": r"WHAT:\s*(.*)",
            "where": r"WHERE:\s*(.*)",
            "why": r"WHY:\s*(.*)",
            "how": r"HOW:\s*(.*)",
            "when": r"WHEN:\s*(.*)",
            "version": r"WHAT:.*Version:\s*([\d\.]+)",
            "purity_score": r"PURITY:\s*([\d\.]+)",
            "trust_level": r"TRUST:\s*(.*)",
            "predicted_v": r"PRED_V:\s*([\d\.\-]+)",
            "actual_v": r"ACTUAL_V:\s*([\d\.\-]+)",
            "eval_delta": r"DELTA:\s*([\d\.\-]+)"
        }
        metadata = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, header_part)
            if match: metadata[key] = match.group(1).strip()
        return metadata

    @staticmethod
    def compute_payload_hash(payload: Any) -> str:
        payload_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_json.encode('utf-8')).hexdigest()

    @staticmethod
    def stamp_file(path: str, protocol: SixWProtocol) -> bool:
        file_path = Path(path)
        if not file_path.exists(): return False
        content = file_path.read_text(errors="ignore")
        if StampingEngine.is_stamped(content):
            parts = content.split("==========================================================")
            if len(parts) > 1:
                content = parts[-1].strip()
        
        stamp = protocol.to_stamp_header(file_path.suffix)
        file_path.write_text(f"{stamp}\n\n{content}")
        return True

    @staticmethod
    def get_environment() -> str:
        import os
        if os.environ.get("K_SERVICE") or os.environ.get("GOOGLE_CLOUD_PROJECT"):
            return "gcp"
        return "local"