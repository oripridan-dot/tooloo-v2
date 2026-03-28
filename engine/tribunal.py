# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining tribunal.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.941865
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

from __future__ import annotations
import logging
import numpy as np
import os
import re
import datetime

try:
    import soundfile as sf
except ImportError:
    sf = None
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from engine.engram import Engram, EmergenceVector


# --- Core PURE Tribunal System ---

class TribunalVerdict(Enum):
    STABLE_SUCCESS = "STABLE_SUCCESS"
    SUCCESS_WITH_GROWTH = "SUCCESS_WITH_GROWTH"
    ERROR_CORRECTION = "ERROR_CORRECTION"

@dataclass
class TribunalResult:
    slug: str
    delta: float
    verdict: TribunalVerdict
    violations: List[str] = field(default_factory=list)
    deception_score: float = 0.0  # Ouroboros: tracks obfuscation attempts


class BillingGatekeeper:
    """
    MASTER DIRECTIVE RULE 4: Billing Exemption Workflow.
    Excludes Google services from cost-restriction workflows to ensure
    uninterrupted access.

    Ouroboros Hardening:
    - Deception score: detects when a tool call uses obfuscated names or
      aliasing patterns to disguise a non-exempt tool as an exempt one.
    - Audit log: records every gating decision with a timestamp.
    """
    _DEFAULT_EXEMPT_PATTERNS = [
        r"gcloud", r"mcp[-_]cloudrun", r"google", r"vertex", r"gemini", r"cloudrun"
    ]

    # Deception patterns: strings that APPEAR to be GCP but are red flags
    _DECEPTION_PATTERNS = [
        # Attempts to reference GCP tools while including bypass keywords
        r"(bypass|skip|ignore|override|disable|circumvent|restrict).{0,50}?(gcp|google|vertex|cloudrun|auditor|billing)",
        r"(gcp|google|vertex|cloudrun|auditor|billing).{0,50}?(bypass|skip|ignore|override|disable|circumvent|restrict)",
        # Indirect bypass: action word + auditor / billing context
        r"(skip|bypass|circumvent|disable).{0,30}(auditor|billing|gate|check|restriction|workflow)",
        r"internal.{0,20}(gcp|google|cloud|override)",
        # Aliased calls using homoglyphs or separators
        r"\bgoog[l1][e3]\b",  # goog1e, googIe
        r"v[e3]rt[e3]x",      # v3rt3x
        r"g[e3]m[i1]n[i1]",   # g3m1n1
        # Override / internal references
        r"internal.*?audit",
        r"skip.*?auditor",
    ]

    @classmethod
    def get_exempt_patterns(cls) -> List[str]:
        env_patterns = os.getenv("TOOLOO_BILLING_EXEMPT_PATTERNS", "")
        if env_patterns:
            return cls._DEFAULT_EXEMPT_PATTERNS + [
                p.strip() for p in env_patterns.split(",") if p.strip()
            ]
        return cls._DEFAULT_EXEMPT_PATTERNS

    @classmethod
    def compute_deception_score(cls, tool_call: str) -> float:
        """
        Returns a float 0.0–1.0 indicating how likely the tool call is to
        be an attempt to deceive the Billing Gatekeeper.

        A score > 0.5 should trigger an audit violation.
        """
        text = tool_call.lower()
        hits = 0
        for pattern in cls._DECEPTION_PATTERNS:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    hits += 1
            except re.error:
                continue
        return min(1.0, hits / max(1, len(cls._DECEPTION_PATTERNS)))

    @classmethod
    def is_exempt(cls, tool_call: str) -> bool:
        """Check if a tool call is exempt from billing restrictions."""
        patterns = cls.get_exempt_patterns()
        for pattern in patterns:
            try:
                if re.search(pattern, tool_call.lower()):
                    return True
            except re.error:
                continue
        return False

    @classmethod
    def audit(cls, tool_call: str) -> Dict[str, Any]:
        """
        Full audit gate: checks exemption AND deception score.
        Returns a rich result dict for logging and tribunal evaluation.
        """
        exempt = cls.is_exempt(tool_call)
        deception = cls.compute_deception_score(tool_call)

        # Deception check takes priority over exemption.
        # Threshold: 0.3 — calibrated against live adversarial test cases.
        # A score > 0.3 means the mandate contains bypass/obfuscation signals
        # even if it also references a legitimate tool name.
        deception_override = deception > 0.3

        result: Dict[str, Any] = {
            "tool_call": tool_call,
            "is_exempt": exempt and not deception_override,
            "deception_score": round(deception, 3),
            "deception_override": deception_override,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

        if deception_override:
            result["verdict"] = "BLOCKED_DECEPTION"
            logging.getLogger(__name__).warning(
                f"BillingGatekeeper: DECEPTION DETECTED in tool_call='{tool_call}' "
                f"(score={deception:.2f}). Blocking despite any pattern match — "
                f"deception_override=True."
            )
        elif exempt:
            result["verdict"] = "EXEMPT"
        else:
            result["verdict"] = "BLOCKED"

        return result


class Tribunal:
    """
    Standard TooLoo PURE Audit Engine.
    Evaluates the delta between predicted and actual emergence.

    Ouroboros Hardening:
    - Incorporates deception_score from BillingGatekeeper into the TribunalResult.
    - Hard-blocks any tool call with deception_override=True regardless of intent.
    """
    def __init__(self, threshold: float = 0.05) -> None:
        self.threshold = threshold

    async def evaluate(
        self,
        engram: Engram,
        em_actual: Optional[EmergenceVector] = None,
        tool_call: Optional[str] = None
    ) -> TribunalResult:

        deception_score = 0.0
        violations: List[str] = []

        # 1. RULE 4: Billing Exemption + Deception Audit
        if tool_call:
            audit_result = BillingGatekeeper.audit(tool_call)
            deception_score = audit_result["deception_score"]

            if audit_result["deception_override"]:
                violations.append("RULE_4_DECEPTION_BLOCKED")
                return TribunalResult(
                    engram.context.what,
                    1.0,  # Max delta — this is a hard failure
                    TribunalVerdict.ERROR_CORRECTION,
                    violations,
                    deception_score=deception_score,
                )
            if audit_result["is_exempt"]:
                return TribunalResult(
                    engram.context.what,
                    0.0,
                    TribunalVerdict.STABLE_SUCCESS,
                    ["RULE_4_EXEMPT"],
                    deception_score=deception_score,
                )

        # 2. Core PURE emergence delta audit
        if not em_actual or not engram.em_pred:
            return TribunalResult(
                engram.context.what, 0.0, TribunalVerdict.STABLE_SUCCESS,
                deception_score=deception_score,
            )

        v1 = engram.em_pred.to_vec()
        v2 = em_actual.to_vec()
        delta = float(np.linalg.norm(v1 - v2))

        verdict = TribunalVerdict.STABLE_SUCCESS
        if delta > self.threshold:
            verdict = TribunalVerdict.SUCCESS_WITH_GROWTH
        if delta > 0.5:
            verdict = TribunalVerdict.ERROR_CORRECTION
            violations.append("ADVERSARIAL_SURPRISE_DETECTED")

        return TribunalResult(
            engram.context.what, delta, verdict, violations,
            deception_score=deception_score,
        )
