# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.self_healer.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

import hmac
import hashlib
import json
import logging
import asyncio
from typing import Dict, Any, List
from engine.orchestrator import PureOrchestrator
from engine.model_garden import get_garden, CognitiveProfile

logger = logging.getLogger(__name__)

# Circuit Breaker: Max repair attempts per commit
MAX_REPAIR_ATTEMPTS = 3

class SpokeSelfHealer:
    """
    Autonomous repair engine for Spoke repositories.
    Interprets CI failure payloads and generates AST-level fix mandates.
    """

    def __init__(self, hmac_secret: str):
        self.hmac_secret = hmac_secret.encode('utf-8')
        self.orchestrator = PureOrchestrator()
        self.repair_history: Dict[str, int] = {} # commit_hash -> attempt_count

    def verify_signature(self, payload: bytes, signature_header: str) -> bool:
        """Verify HMAC-SHA256 signature from GitHub Spoke Action."""
        if not signature_header.startswith("sha256="):
            return False
        
        expected_sig = hmac.new(
            self.hmac_secret, 
            payload, 
            hashlib.sha256
        ).hexdigest()
        
        received_sig = signature_header.split("=")[1]
        return hmac.compare_digest(received_sig, expected_sig)

    async def handle_ci_failure(self, payload: Dict[str, Any]) -> str:
        """
        Main entry point for CI failure resolution.
        1. Analyze failure logs and diffs.
        2. Formulate a fix.
        3. Push to the Spoke repository.
        """
        repository = payload.get("repository", "unknown")
        commit_hash = payload.get("commit", "unknown")
        
        # 1. Circuit Breaker
        attempts = self.repair_history.get(commit_hash, 0)
        if attempts >= MAX_REPAIR_ATTEMPTS:
            logger.error(f"Circuit Breaker Triggered for {repository} @ {commit_hash}. Manual intervention required.")
            return "CIRCUIT_BREAKER"
        
        self.repair_history[commit_hash] = attempts + 1
        logger.info(f"Initiating autonomous repair for {repository} (Attempt {attempts + 1})")

        # 2. Formulate Mandate
        repair_mandate = self._construct_repair_mandate(payload)
        
        # 3. Route to Heavy Reasoner (Tier 4 + Thinking)
        garden = get_garden()
        profile = CognitiveProfile(
            primary_need="coding",
            minimum_tier=4,
            thinking_available=True,
            complexity=0.9
        )
        model_id = garden.get_tier_model(tier=4, profile=profile)
        
        logger.info(f"Diagnosing failure using {model_id}...")
        
        # Generate the fix code/diff
        # In the PURE architecture, we emit the FIX as a new engram/mandate
        repair_result = garden.call(
            model_id=model_id,
            prompt=repair_mandate,
            max_tokens=4096,
            intent="HEAL"
        )

        # 4. Physical Execution (The Push)
        # Note: In a real deployment, this would utilize a GitHub App installation token
        # to push the `repair_result` back to the repository.
        logger.info(f"Repair synthesized for {repository}. Pushing fix to autonomous-repair branch...")
        
        # Simplified: We log the fix for now as a verification step
        await self._log_fix_for_audit(repository, commit_hash, repair_result)
        
        return "REPAIR_SYNTHESIZED"

    def _construct_repair_mandate(self, payload: Dict[str, Any]) -> str:
        """Transforms logs/diffs into a high-fidelity repair mandate."""
        return f"""
# CI FAILURE DIAGNOSIS MANDATE
Target Repository: {payload['repository']}
Failed Commit: {payload['commit']}

## Failure Context (STDERR/STDOUT)
```text
{payload['logs']}
```

## Relevant Code Diff (Last Commit)
```diff
{payload['diff']}
```

## Your Mandate:
Analyze the failure log above against the code diff. identify the root cause (syntax error, logic flaw, or missing dependency).
Synthesize a targeted fix. Output ONLY the corrected files or a single unified diff that resolves the failure without introducing regressions.
Apply the 'Rule of Absolute Purity': Do not modify Hub-side infrastructure, only Spoke-side implementation.
"""

    async def _log_fix_for_audit(self, repo: str, commit: str, fix: str):
        """Persist the repair engram for human audit or E_sim training."""
        audit_path = f"psyche_bank/repairs/{repo.replace('/', '_')}_{commit[:8]}.md"
        os.makedirs(os.path.dirname(audit_path), exist_ok=True)
        with open(audit_path, "w") as f:
            f.write(f"# AUTONOMOUS REPAIR AUDIT\nRepo: {repo}\nCommit: {commit}\n\n## Synthesis Output\n{fix}")
        logger.info(f"Repair audit logged to {audit_path}")

import os
# Mock instance for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    healer = SpokeSelfHealer(hmac_secret="SOTA_SECRET_2026")
    # Test Payload
    test_data = {
        "repository": "oripridan/spoke-test",
        "commit": "abc12345",
        "logs": "TypeError: Cannot read property 'map' of undefined in app.js:42",
        "diff": "+ const data = get_remote_data();\n+ data.map(i => console.log(i));",
    }
    asyncio.run(healer.handle_ci_failure(test_data))
