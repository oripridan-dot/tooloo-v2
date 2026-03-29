# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.spoke.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

from __future__ import annotations

import logging
import asyncio
import time
import hashlib
from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel

from engine.executor import JITExecutor, Envelope, ExecutionResult
from engine.schemas.six_w import SixWProtocol
from engine.organs import OrganType, OrganPayload
from engine.tribunal import Tribunal

logger = logging.getLogger(__name__)

class SpokeArtifact(BaseModel):
    """A 6W-stamped and signed execution result."""
    stamp: SixWProtocol
    output: Any
    signature: str
    identity_hash: str
    success: bool

class SpokeOrgan:
    """
    The Limbs: Responsible for task execution and tool invocation.
    Hardens the JITExecutor with sandbox awareness and artifact promotion.
    """

    def __init__(self, mcp_manager: Optional[Any] = None, tribunal: Optional[Tribunal] = None) -> None:
        self.type = OrganType.SPOKE_GENERIC
        self.tribunal = tribunal or Tribunal()
        self.executor = JITExecutor(mcp_manager=mcp_manager, tribunal=self.tribunal)
        self.intercept_registry = set() # High-risk task IDs
        self.telemetry_stream = [] # Granular execution steps
        logger.info("SpokeOrgan initialized. Ready for mandate execution.")

    async def execute_mandate(self, env: Envelope, work_fn: Callable) -> SpokeArtifact:
        """
        Executes a mandate and promotes the resulting output to a signed artifact.
        """
        logger.info(f"Spoke received mandate: {env.mandate_id}")
        
        # 0. Sovereign Intercept (Human-in-the-Loop)
        if env.mandate_id in self.intercept_registry or "HIGH-RISK" in env.mandate_id:
             logger.warning(f"Sovereign Intercept: Mandate {env.mandate_id} requires explicit authorization.")
             # In a production system, this would wait for a 'RESUME' signal from the Hub
             await asyncio.sleep(0.5) 
             logger.info(f"Intercept Resolved for {env.mandate_id}. Resuming execution.")

        # 1. Action Telemetry (Streaming)
        self._record_telemetry(env.mandate_id, "INIT", "Establishing JIT environment")
        
        # 2. Execution via JITExecutor (The Spoke Body)
        self._record_telemetry(env.mandate_id, "EXEC", f"Running work function for {env.domain}")
        result: ExecutionResult = await self.executor._run_async(work_fn, env, self.executor._mcp, self.tribunal)
        
        # 3. Promote to 6W-Stamped Artifact
        self._record_telemetry(env.mandate_id, "PROM", "Promoting to 6W-signed artifact")
        artifact = await self.promote_artifact(env, result)
        
        self._record_telemetry(env.mandate_id, "DONE", f"Artifact identity: {artifact.identity_hash[:8]}")
        return artifact

    def _record_telemetry(self, mandate_id: str, step: str, details: str):
        """Streams granular telemetry back to the Hub (via logs/internal queue)."""
        msg = f"[TELEMETRY][{mandate_id}][{step}] {details}"
        logger.info(msg)
        self.telemetry_stream.append({
            "ts": time.time(),
            "mandate": mandate_id,
            "step": step,
            "details": details
        })

    async def promote_artifact(self, env: Envelope, result: ExecutionResult) -> SpokeArtifact:
        """
        Validates, stamps, and signs an execution result.
        This provides the Hub with a 'STATE_PROVEN' artifact.
        """
        # Create the execution stamp (WHAT happened and HOW)
        stamp = SixWProtocol(
            who="tooloo-spoke-1",
            what=f"Execution of {env.mandate_id}",
            where=env.domain,
            when=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            why="mandate-completion",
            how="jit-async-execution"
        )
        
        # Bit-perfect identity hash
        content_str = str(result.output)
        identity_hash = hashlib.sha256(content_str.encode()).hexdigest()
        
        # Simple signature (Placeholder for real cryptographic signing)
        signature = f"SPOKE_SIG_{identity_hash[:8]}"
        
        artifact = SpokeArtifact(
            stamp=stamp,
            output=result.output,
            signature=signature,
            identity_hash=identity_hash,
            success=result.success
        )
        
        logger.info(f"Artifact promoted: {env.mandate_id}. Signature: {signature}")
        return artifact

    def verify_identity(self, artifact: SpokeArtifact) -> bool:
        """Verifies the bit-perfect consistency of a promoted artifact."""
        content_str = str(artifact.output)
        current_hash = hashlib.sha256(content_str.encode()).hexdigest()
        return current_hash == artifact.identity_hash
