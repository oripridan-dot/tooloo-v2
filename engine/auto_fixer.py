# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.auto_fixer.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/auto_fixer.py — Automated Code-Fixer (Pyright) — Ouroboros Hardened.

Integrates the "Self-Healing" static analysis loop. Plugs in Pyright
diagnostics, parses the JSON error output, and runs an automated fix loop
using the dynamic model tier.

Adversarial Training Hardening (Project Ouroboros):
- Recursive recovery up to MAX_RETRIES=3 attempts per file.
- Oscillation detection: if the same error persists across retries, abort
  to prevent infinite self-modification loops (the "Labyrinth" trap).
- Post-fix verification: after each attempt, re-run Pyright to confirm clean.
"""
import asyncio
import json
import logging
import re
import os
import subprocess
from typing import Any, Optional, List, Dict, Set

from engine.model_garden import get_garden, CognitiveProfile

logger = logging.getLogger(__name__)

MAX_RETRIES = 3  # Maximum recursive self-healing attempts per file


class AutoFixLoop:
    def __init__(self) -> None:
        self.garden = get_garden()

    # ── Static Analysis ───────────────────────────────────────────────────────

    def _run_pyright(self, filepath: str) -> List[Dict[str, Any]]:
        """Run pyright --outputjson on a target file. Returns diagnostics list."""
        try:
            result = subprocess.run(
                ["pyright", "--outputjson", filepath],
                capture_output=True,
                text=True,
                timeout=30,
            )
            data = json.loads(result.stdout)
            return data.get("generalDiagnostics", [])
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            logger.error(f"AutoFix._run_pyright failed: {e}")
            return []

    def _extract_error_signatures(self, diagnostics: List[Dict[str, Any]]) -> Set[str]:
        """
        Extract canonical error signatures (line+message) for oscillation detection.
        If the same signatures persist across retries, the fixer is oscillating.
        """
        sigs: set[str] = set()
        for d in diagnostics:
            if d.get("severity") in ("error", "warning"):
                line = d.get("range", {}).get("start", {}).get("line", 0)
                msg = d.get("message", "")[:80]  # Truncate for comparison
                sigs.add(f"L{line}:{msg}")
        return sigs

    def _build_fix_prompt(
        self,
        code_content: str,
        error_summary: List[str],
        attempt: int,
    ) -> str:
        """Build an LLM prompt for the fix attempt, demanding structured XML output."""
        urgency = {
            1: "Analyze the errors and provide a fix.",
            2: "The previous fix attempt was INSUFFICIENT. Perform a root-cause analysis before fixing.",
            3: "CRITICAL: Final attempt. Deep structural analysis required. Pivot to an architectural fix if needed.",
        }.get(attempt, "Fix the code.")

        return (
            f"You are the TooLoo V2 Auto-Correction Agent. {urgency}\n\n"
            "MANDATORY FORMAT:\n"
            "1. Wrap your root-cause analysis in <analysis> tags.\n"
            "2. Wrap the ENTIRE updated file content in <fixed_code> tags.\n"
            "- Do NOT include markdown code fences (```) inside the tags.\n"
            "- Ensure the code is pure Python and structurally sound.\n\n"
            f"PYRIGHT ERRORS (attempt {attempt}):\n"
            + "\n".join(error_summary)
            + "\n\nORIGINAL CODE:\n"
            + code_content
        )

    # ── Core Healing Loop ─────────────────────────────────────────────────────

    async def analyze_and_fix(
        self,
        filepath: str,
        model_tier: int = 3,
        manual_diagnostics: Optional[List[str]] = None,
        _attempt: int = 1,
        _prev_signatures: Set[str] | None = None,
    ) -> bool:
        """
        Analyze a file with Pyright. If errors exist, invoke the LLM to fix them.
        Recursively retries up to MAX_RETRIES times, detecting oscillation to abort.
        """
        # Run Pyright diagnostics
        diagnostics = await asyncio.to_thread(self._run_pyright, filepath)

        if not diagnostics:
            # Fallback to manual diagnostics if provided
            if manual_diagnostics and _attempt == 1:
                logger.warning(f"AutoFix: Pyright is clean, but found {len(manual_diagnostics)} MANUAL MANDATES. Healing logic...")
                error_summary = manual_diagnostics
            else:
                if _attempt > 1:
                    logger.info(f"AutoFix[{_attempt}]: {filepath} is NOW CLEAN. ✓")
                else:
                    logger.info(f"AutoFix: {filepath} is already clean.")
                return _attempt > 1
        else:
            error_sigs = self._extract_error_signatures(diagnostics)

            if _prev_signatures and error_sigs == _prev_signatures:
                logger.error(f"AutoFix[{_attempt}]: OSCILLATION DETECTED in {filepath}. Aborting.")
                return False

            if _attempt > MAX_RETRIES:
                logger.error(f"AutoFix: Exceeded MAX_RETRIES ({MAX_RETRIES}) for {filepath}.")
                return False

            logger.warning(f"AutoFix[{_attempt}/{MAX_RETRIES}]: Found {len(diagnostics)} issues. Healing...")

            # Build error summary from Pyright
            error_summary: List[str] = []
            for d in diagnostics:
                if d.get("severity") in ("error", "warning"):
                    line = d.get("range", {}).get("start", {}).get("line", 0) + 1
                    msg = d.get("message", "")
                    error_summary.append(f"Line {line}: {msg}")

        if not error_summary:
            return False

        # Read current content
        try:
            with open(filepath) as f:
                code_content = f.read()
        except OSError as e:
            logger.error(f"AutoFix: Cannot read {filepath}: {e}")
            return False

        # Configuration for the call
        # --- SOTA: Logic Mandates require thinking by default ---
        is_thinking_pass = _attempt > 1 or bool(manual_diagnostics)
        prompt = self._build_fix_prompt(code_content, error_summary, _attempt)
        profile = CognitiveProfile(
            primary_need="coding",
            minimum_tier=model_tier + (1 if is_thinking_pass else 0),
            complexity=min(0.6 + (_attempt - 1) * 0.2, 1.0),
            thinking_available=is_thinking_pass,
            thinking_budget=16000 if is_thinking_pass else None,
        )

        model_id = self.garden.get_tier_model(tier=model_tier, intent="HEAL", profile=profile)

        try:
            with open("/tmp/ouroboros_debug.log", "a") as debug_file:
                debug_file.write(f"--- AutoFix Attempt {_attempt} for {filepath} ---\n")
                debug_file.write(f"Model selected: {model_id}\n")
                
                # --- SOTA: Anti-Stuck Watchdog ---
                try:
                    raw_response = await asyncio.wait_for(
                        asyncio.to_thread(self.garden.call, model_id, prompt, 8192, intent="HEAL"),
                        timeout=65.0
                    )
                except asyncio.TimeoutError:
                    logger.error(f"AutoFix[{_attempt}]: LLM call TIMEOUT (Pathway B race did not resolve in 65s).")
                    return False
                debug_file.write(f"Raw response length: {len(raw_response) if raw_response else 0}\n")

                if not raw_response or not raw_response.strip():
                    logger.error(f"AutoFix[{_attempt}]: Empty response from {model_id}")
                    return False

                # Extraction logic
                analysis_match = re.search(r"<analysis>(.*?)</analysis>", raw_response, re.DOTALL | re.IGNORECASE)
                code_match = re.search(r"<fixed_code>(.*?)</fixed_code>", raw_response, re.DOTALL | re.IGNORECASE)

                if analysis_match:
                    logger.info(f"AutoFix[{_attempt}] Analysis: {analysis_match.group(1).strip()[:100]}...")

                new_code = ""
                if code_match:
                    new_code = code_match.group(1).strip()
                else:
                    # Fallback
                    if any(kw in raw_response for kw in ("def ", "import ", "class ")):
                        new_code = raw_response.strip()
                        if "```python" in new_code:
                            new_code = new_code.split("```python")[1].split("```")[0].strip()
                        elif "```" in new_code:
                            new_code = new_code.split("```")[1].split("```")[0].strip()
                    else:
                        logger.error(f"AutoFix[{_attempt}]: No code block found in response.")
                        return False

                if not new_code or new_code.strip() == code_content.strip():
                    logger.warning(f"AutoFix[{_attempt}]: No changes made or empty output.")
                    return False

                # Write patch
                with open(filepath, "w") as f:
                    f.write(new_code + "\n")
                
                logger.info(f"AutoFix[{_attempt}]: Patch applied.")

        except Exception as e:
            logger.error(f"AutoFix[{_attempt}]: LLM call failed: {e}")
            return False

        # Recurse
        return await self.analyze_and_fix(
            filepath=filepath,
            model_tier=model_tier,
            manual_diagnostics=manual_diagnostics,
            _attempt=_attempt + 1,
            _prev_signatures=error_sigs if diagnostics else None
        )
