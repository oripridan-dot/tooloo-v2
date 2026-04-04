# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MODULE_CRUCIBLE_VALIDATOR | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/crucible_validator.py
# WHEN: 2026-04-03T17:30:00.000000
# WHY: Primitives 2/4/8 - Engineering-First Operational Discipline
# HOW: Boring Infrastructure Primitives + Pragmatic Validation
# TIER: T1:foundation-primitives
# DOMAINS: kernel, cognitive, validation, security, quality
# PURITY: 1.00
# ==========================================================

import logging
import hashlib
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from tooloo_v4_hub.kernel.cognitive.agent_types import AgentType, get_persona

logger = logging.getLogger("CrucibleValidator")

class AuditResult(BaseModel):
    status: str # PASS, FAIL, WARNING
    purity_score: float
    findings: List[str] = []
    remediation_plan: Optional[str] = None

class CrucibleValidator:
    """
    The Automated Gatekeeper for TooLoo V4.
    Audits every mission plan and code artifact before manifestation.
    """

    def __init__(self):
        logger.info("Crucible Validator: Initialized.")
        self._cache: Dict[str, AuditResult] = {}
        # Pre-compile SOTA patterns for speed
        self.secret_patterns = [
            re.compile(r"AIza[0-9A-Za-z-_]{35}"),           # Google API Key
            re.compile(r"sk-[a-zA-Z0-9]{48}"),               # OpenAI Key
            re.compile(r"(?i)password\s*=\s*['\"][^'\"]+['\"]"), # Generic Password
            re.compile(r"-----BEGIN RSA PRIVATE KEY-----"),  # SSH Key
            re.compile(r"client_email\":\s*\"[^\"]+\.iam\.gserviceaccount\.com\"") # GCP Service Account
        ]
        self.risky_commands = {
            "rm -rf /", "rm -rf ~", "rm -rf *", "chmod 777", 
            "curl | bash", "wget | sh", "> /etc/", "sudo ",
            "cat /etc/shadow", "find / -delete", "mv /dev/null",
            "killall -9", ":(){ :|:& };:"
        }

    async def audit_plan(self, goal: str, plan_nodes: List[Dict[str, Any]]) -> AuditResult:
        """Audits a mission plan for the 12 Engineering-First Primitives."""
        findings = []
        purity = 1.0
        goal_lower = goal.lower()
        
        # Flatten hierarchical nodes if necessary (Primitive 2: Resilient Data Intake)
        def flatten(nodes):
            flat = []
            for n in nodes:
                if isinstance(n, list):
                    flat.extend(flatten(n))
                elif isinstance(n, dict):
                    flat.append(n)
            return flat
            
        flat_nodes = flatten(plan_nodes)
        
        # 12. ROLE ALIGNMENT (Primitive 12)
        agent_type = AgentType.PLAN # Default for Mission Planning
        persona = get_persona(agent_type)
        
        # 1. PERMISSION & TRUST (Primitive 2)
        for node in flat_nodes:
            action = node.get("action", "")
            payload = node.get("payload", {}) or node.get("params", {})
            
            # Role Constraint Check
            if action in persona.forbidden_actions:
                findings.append(f"PRIMITIVE 12 VIOLATION: Role {agent_type} forbidden from {action}.")
                purity -= 0.5
            
            # CLI / Shell hardened check
            action_safe = str(action or "").lower()
            if any(k in action_safe for k in ["cli_run", "shell", "command"]):
                cmd = str(payload.get("command", "")) if isinstance(payload, dict) else str(payload)
                
                # Primitive 2/8: Block malicious patterns
                if any(bad in cmd for bad in self.risky_commands):
                    findings.append(f"PRIMITIVE 2 VIOLATION: Malicious command: {cmd}")
                    purity -= 0.6
                
                # Cloud-Native Mandate check
                if any(ext in cmd for ext in ["brew install", "apt-get", "pacman -S", "yum install"]):
                    findings.append("MANDATE VIOLATION: System mutation attempt (Non-Cloud-Native).")
                    purity -= 0.3
            
            # Primitive 12: Role Sharpening (Agent Type System)
            node_goal = str(node.get("goal", "")).lower()
            if "plan" in node_goal and "execute" in action:
                findings.append("PRIMITIVE 12 VIOLATION: Planning agent attempting execution.")
                purity -= 0.2

        # 2. PRAGMATISM & SIMPLICITY (80/20 Mandate)
        if len(plan_nodes) > 10 and "simple" in goal_lower:
            findings.append("SIMPLICITY WARNING: Excessive complexity for a simple mission.")
            purity -= 0.1

        status = "PASS"
        if purity < 0.6: status = "FAIL" 
        elif purity < 0.95: status = "WARNING"

        return AuditResult(
            status=status,
            purity_score=max(0.0, purity),
            findings=findings,
            remediation_plan="Recalibrate plan based on 80/20 Simplicity Mandate." if status == "FAIL" else None
        )

    async def audit_code(self, filename: str, content: str) -> AuditResult:
        """Primitive 8: Verification of code artifacts against the 12 Primitives."""
        # Primitive 10: Transcript/Audit Caching
        content_hash = hashlib.md5(content.encode()).hexdigest()
        cache_key = f"{filename}:{content_hash}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        findings = []
        purity = 1.0
        
        # Physical Preservation: Check for 6W Stamp
        if "# 6W_STAMP" not in content and "// 6W_STAMP" not in content:
            findings.append("MANDATE VIOLATION: Missing 6W Accountability Stamp.")
            purity -= 0.4
            
        # Security: Primitive 2 (Hardcoded Secrets)
        for pattern in self.secret_patterns:
            if pattern.search(content):
                if not any(env in content for env in ["os.getenv", "os.environ", "load_dotenv", "SecretManager"]):
                    findings.append(f"PRIMITIVE 2 CRITICAL: Hardcoded secret ({pattern.pattern}) detected.")
                    purity -= 0.5

        # Primitive 1: Metadata check (Preventing placeholders)
        if any(x in content for x in ["TODO", "FIXME", "Placeholder"]):
            findings.append("PRAGMATISM WARNING: Code contains placeholders (Primitive 1 Violation).")
            purity -= 0.1

        status = "PASS"
        if purity < 0.6: status = "FAIL"
        elif purity < 1.0: status = "WARNING"

        result = AuditResult(
            status=status,
            purity_score=max(0.0, purity),
            findings=findings
        )
        self._cache[cache_key] = result
        return result

_validator = None

def get_crucible_validator() -> CrucibleValidator:
    global _validator
    if _validator is None:
        _validator = CrucibleValidator()
    return _validator
