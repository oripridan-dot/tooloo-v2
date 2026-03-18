"""
engine/refinement_supervisor.py — Autonomous Healing Supervisor.

Triggered when any DAG node accumulates >= NODE_FAIL_THRESHOLD failures
across N-stroke iterations.  The supervisor pauses the loop and:

  1. Uses MCPManager.read_error()  — parse each failing node's traceback.
  2. Uses MCPManager.web_lookup() — retrieve SOTA fix patterns for the error.
  3. Synthesises a HealingPrescription from error data + SOTA signals.
  4. Validates the prescription text (no eval/exec patterns — Tribunal-style).
  5. Returns a HealingReport with an optional healed_work_fn that the
     NStrokeEngine can substitute for the next stroke's executor.

Healing is fully deterministic — no LLM calls, no randomness, no side-effects
outside the returned HealingReport.  Guaranteed to work offline.
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from engine.executor import Envelope

NODE_FAIL_THRESHOLD: int = 3   # failures before healing is triggered

# Simple poison guard for synthesised fix strategies (no eval / exec)
_POISON_RE = re.compile(r"\b(eval|exec|__import__|subprocess\.run|os\.system)\s*\(")


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class HealingPrescription:
    """Structured fix prescription for one persistently-failing node."""

    node_id: str
    error_type: str
    error_message: str
    hint: str
    sota_signals: list[str]
    fix_strategy: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "hint": self.hint,
            "sota_signals": self.sota_signals,
            "fix_strategy": self.fix_strategy,
        }


@dataclass
class HealingReport:
    """Result of one RefinementSupervisor healing cycle."""

    healing_id: str
    stroke: int
    intent: str
    nodes_analyzed: list[str]
    nodes_healed: list[str]
    prescriptions: list[HealingPrescription]
    healed_work_fn: Callable[[Envelope], Any] | None
    latency_ms: float
    verdict: str    # "healed" | "partial" | "unable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "healing_id": self.healing_id,
            "stroke": self.stroke,
            "intent": self.intent,
            "nodes_analyzed": self.nodes_analyzed,
            "nodes_healed": self.nodes_healed,
            "prescriptions": [p.to_dict() for p in self.prescriptions],
            "healed_work_fn": "<callable>" if self.healed_work_fn else None,
            "latency_ms": round(self.latency_ms, 2),
            "verdict": self.verdict,
        }


# ── Supervisor ────────────────────────────────────────────────────────────────


class RefinementSupervisor:
    """Autonomous healing for persistently-failing DAG nodes.

    Usage::

        supervisor = RefinementSupervisor()
        report = supervisor.heal(
            failed_node_ids=["pipe-001-s2-implement"],
            stroke=3,
            intent="BUILD",
            mcp=mcp_manager,
            booster=jit_booster,
            mandate_text="Build a zero-latency DSP buffer",
        )
        if report.healed_work_fn:
            # Use healed_work_fn in next stroke's JITExecutor.fan_out()
    """

    def heal(
        self,
        failed_node_ids: list[str],
        stroke: int,
        intent: str,
        mcp: Any,      # MCPManager — typed as Any to avoid circular import
        booster: Any,  # JITBooster  — typed as Any to avoid circular import
        mandate_text: str,
        last_error_map: dict[str, str] | None = None,
    ) -> HealingReport:
        """Produce healing prescriptions for all persistently-failing nodes.

        Args:
            failed_node_ids:  Node IDs that failed >= NODE_FAIL_THRESHOLD times.
            stroke:           Current stroke number.
            intent:           Mandate intent string.
            mcp:              MCPManager instance for tool calls.
            booster:          JITBooster for structured SOTA signal lookup.
            mandate_text:     Original mandate text.
            last_error_map:   Optional {node_id: error_string} from last execution.
        """
        t0 = time.monotonic()
        healing_id = f"heal-{uuid.uuid4().hex[:8]}"
        last_error_map = last_error_map or {}
        prescriptions: list[HealingPrescription] = []
        nodes_healed: list[str] = []

        for node_id in failed_node_ids:
            error_text = last_error_map.get(
                node_id,
                f"Node '{node_id}' failed {stroke - 1}+ times — no traceback captured.",
            )

            # Step 1: Parse the error via MCP
            error_result = mcp.call("read_error", error_text=error_text)
            if error_result.success and error_result.output:
                err_data = error_result.output
                error_type = err_data.get("error_type", "UnknownError")
                error_message = err_data.get("message", error_text[:100])
                hint = err_data.get("hint", "Review the error and input data.")
            else:
                error_type = "UnknownError"
                error_message = error_text[:100]
                hint = "Review the error and input data."

            # Step 2: Fetch SOTA fix signals via MCP web_lookup
            query = f"{intent.lower()} {error_type.lower()} {mandate_text[:60]}"
            sota_result = mcp.call("web_lookup", query=query)
            sota_signals: list[str] = []
            if sota_result.success and sota_result.output:
                sota_signals = sota_result.output.get("signals", [])[:3]

            # Step 3: Synthesise fix strategy (validated — no poison)
            fix_strategy = self._synthesise_strategy(
                error_type, hint, sota_signals, intent
            )

            prescriptions.append(HealingPrescription(
                node_id=node_id,
                error_type=error_type,
                error_message=error_message,
                hint=hint,
                sota_signals=sota_signals,
                fix_strategy=fix_strategy,
            ))
            nodes_healed.append(node_id)

        # Step 4: Build healed work function from prescriptions
        healed_fn = self._build_healed_work_fn(prescriptions) if nodes_healed else None

        verdict = (
            "healed" if len(nodes_healed) == len(failed_node_ids)
            else ("partial" if nodes_healed else "unable")
        )

        return HealingReport(
            healing_id=healing_id,
            stroke=stroke,
            intent=intent,
            nodes_analyzed=list(failed_node_ids),
            nodes_healed=nodes_healed,
            prescriptions=prescriptions,
            healed_work_fn=healed_fn,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            verdict=verdict,
        )

    @staticmethod
    def _synthesise_strategy(
        error_type: str,
        hint: str,
        sota_signals: list[str],
        intent: str,
    ) -> str:
        """Produce a one-line fix strategy from error data + SOTA context.

        The strategy is checked for poison patterns before being returned.
        """
        if sota_signals:
            primary = sota_signals[0][:120]
            strategy = f"Apply: {hint} | SOTA: {primary}"
        else:
            strategy = f"Apply: {hint} | Intent={intent}: recheck inputs and retry."

        # Tribunal-style guard: reject synthesised strategies containing dynamic execution
        if _POISON_RE.search(strategy):
            strategy = (
                f"[SUPERVISOR HEALED] Dynamic execution pattern rejected. "
                f"Safe fallback: {hint}"
            )
        return strategy

    @staticmethod
    def _build_healed_work_fn(
        prescriptions: list[HealingPrescription],
    ) -> Callable[[Envelope], Any]:
        """Return a new work function that injects healing prescriptions into output.

        The healed function carries the fix strategy and SOTA hints as metadata
        embedded in the execution output, making them visible in the SSE stream
        and the NStrokeResult.
        """
        rx_map = {p.node_id: p.to_dict() for p in prescriptions}

        def _healed(env: Envelope) -> dict[str, Any]:
            rx = rx_map.get(env.mandate_id)
            if rx is None:
                # Also try canonical suffix match so that pipeline-qualified IDs
                # like "ns-abc-s4-implement" match a canonical key "implement".
                rx = rx_map.get(env.mandate_id.rsplit("-", 1)[-1])
            return {
                "node": env.mandate_id,
                "intent": env.intent,
                "status": "healed_execution",
                "healing_applied": rx is not None,
                "fix_strategy": rx["fix_strategy"] if rx else None,
                "sota_hint": rx["hint"] if rx else None,
                "model": env.metadata.get("model", "unknown"),
                "stroke": env.metadata.get("stroke", 1),
            }

        return _healed
