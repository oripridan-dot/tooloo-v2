# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MODULE_PERMISSION_SYSTEM | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/governance/permission_system.py
# WHEN: 2026-04-03T16:30:00.000000
# WHY: Primitive 2: Permission System & Trust Tiers (Security Discipline)
# HOW: Layered authorization with JSONL Audit Trail (Primitive 11)
# TIER: T1:foundation-primitives
# DOMAINS: kernel, governance, security, permissions, auditing
# PURITY: 1.00
# ==========================================================

import logging
import json
import time
from enum import Enum
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger("PermissionSystem")

class PermissionTier(str, Enum):
    BUILT_IN = "BUILT_IN"   # High Trust (OS, Kernel, Core SDKs)
    PLUG_IN = "PLUG_IN"     # Medium Trust (MCP Servers, Shared Tools)
    SKILL = "SKILL"         # Low Trust (User-defined scripts, Scratch tools)

class PermissionAuditEntry:
    def __init__(self, action: str, tier: PermissionTier, result: str, reason: Optional[str] = None):
        self.timestamp = time.time()
        self.action = action
        self.tier = tier
        self.result = result
        self.reason = reason

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "tier": self.tier,
            "result": self.result,
            "reason": self.reason
        }

class PermissionSystem:
    """Primitive 2 & 11: The Sovereign Gatekeeper."""
    
    def __init__(self):
        self.audit_log_path = Path("tooloo_v4_hub/psyche_bank/permissions_audit.jsonl")
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Hardcoded trust mapping for default tools
        self.trust_map: Dict[str, PermissionTier] = {
            "run_command": PermissionTier.BUILT_IN,
            "write_to_file": PermissionTier.BUILT_IN,
            "mcp_cloudrun_deploy": PermissionTier.PLUG_IN,
            "read_url": PermissionTier.PLUG_IN,
            "search_web": PermissionTier.SKILL
        }

    def check_permission(self, action: str, agent_type: str) -> bool:
        """Primitive 2: Multi-Tier Authorization Logic."""
        tier = self.trust_map.get(action, PermissionTier.SKILL)
        
        # Logic: Low-trust agents (STATUS, GUIDE) cannot perform BUILT_IN mutations.
        allowed = True
        reason = "Authorized"
        
        if tier == PermissionTier.BUILT_IN and agent_type in ["GUIDE", "STATUS"]:
            allowed = False
            reason = f"Agent Type {agent_type} is too low-tier for {tier} action."
        
        self.log_audit(action, tier, "GRANT" if allowed else "DENY", reason)
        return allowed

    def log_audit(self, action: str, tier: PermissionTier, result: str, reason: Optional[str] = None):
        """Primitive 11: Permission Audit Trail."""
        entry = PermissionAuditEntry(action, tier, result, reason)
        try:
            with open(self.audit_log_path, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Audit Log Failure: {e}")

_permission_system = None

def get_permission_system() -> PermissionSystem:
    global _permission_system
    if _permission_system is None:
        _permission_system = PermissionSystem()
    return _permission_system
