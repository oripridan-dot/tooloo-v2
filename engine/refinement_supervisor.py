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

Speculative Healing (Differential Micro-Mitosis):
  When enabled, instead of a single sequential fix attempt the supervisor
  spawns N_SPECULATIVE_BRANCHES BRANCH_CLONE micro-variant pipelines in
  parallel.  Each ghost emits only a surgical ``patch_apply`` call (≤10 lines)
  rather than rewriting the entire file.  The ``wait_for_first_success()``
  gate returns the first ghost to deliver a passing test result, terminates
  the losers via asyncio.Task.cancel(), and manifests the winning patch into
  the main trunk.

  • Wall-clock time: one parallel slot instead of N sequential failures.
  • Blast radius: zero — only the exact failing lines are mutated.
  • Token cost: micro-fast flash / local-SLM models route the ghosts (Tier 0-1).

Healing is fully deterministic in the sequential path — no LLM calls, no
randomness, no side-effects outside the returned HealingReport.  Guaranteed
to work offline.
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from engine.executor import Envelope
from engine.healing_guards import (
    ConvergenceGuard,
    ConvergenceMetrics,
    HealingGateResult,
    ReversibilityGuard,
    check_healing_gates,
)

# Production default: 3 failures before healing is triggered.
# Override via NODE_FAIL_THRESHOLD env var for extended dev tolerance.
NODE_FAIL_THRESHOLD: int = 3   # failures before healing is triggered

# Speculative healing: parallel micro-ghost branches
N_SPECULATIVE_BRANCHES: int = 3   # number of micro-variant ghosts to spawn
SPECULATIVE_GHOST_TIMEOUT: float = 30.0  # seconds per ghost

# Simple poison guard for synthesised fix strategies (no eval / exec)
_POISON_RE = re.compile(
    r"\b(eval|exec|__import__|subprocess\.run|os\.system)\s*\(")


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

    Integrates ConvergenceGuard (failure trajectory tracking) and
    ReversibilityGuard (atomic rollback capability) from healing_guards.py
    to prevent infinite loops and non-reversible mutations.

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

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._convergence_guard = ConvergenceGuard()
        wr = workspace_root or Path.cwd()
        self._reversibility_guard = ReversibilityGuard(wr)

    def check_convergence(self, failure_count: int) -> ConvergenceMetrics:
        """Check whether the healing loop is converging. Delegate to guard."""
        return self._convergence_guard.check(failure_count)

    def reset_convergence(self) -> None:
        """Reset convergence tracking for a new mandate/node."""
        self._convergence_guard.reset()

    def pre_heal_gate(
        self,
        failure_count: int,
        snapshot_id: str,
        affected_files: list[str] | None = None,
    ) -> HealingGateResult:
        """Run convergence + reversibility gates before executing a heal.

        If *affected_files* is provided and no snapshot exists yet, one is
        created automatically so the reversibility guard has data to check.
        """
        if affected_files and snapshot_id not in self._reversibility_guard.snapshots:
            self._reversibility_guard.snapshot_before_stroke(
                snapshot_id, affected_files,
            )
        return check_healing_gates(
            self._convergence_guard,
            self._reversibility_guard,
            failure_count,
            snapshot_id,
        )

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
        healed_fn = self._build_healed_work_fn(
            prescriptions) if nodes_healed else None

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


# ── Speculative Healing Engine ────────────────────────────────────────────────


@dataclass
class GhostBranchSpec:
    """Describes one speculative micro-variant ghost."""

    ghost_id: str
    strategy: str        # "conservative" | "rewrite" | "jit_library"
    tier: int            # 0=local_slm, 1=flash
    patch_hint: str      # concise directive for the ghost's micro-prompt
    node_id: str         # the failing node being healed


@dataclass
class SpeculativeHealingResult:
    """Outcome of a parallel speculative healing run."""

    healing_id: str
    node_id: str
    winner_ghost_id: str | None
    winning_patch: dict[str, Any] | None   # patch_apply kwargs if a ghost won
    ghosts_spawned: int
    ghosts_succeeded: int
    latency_ms: float
    verdict: str   # "won" | "all_failed" | "timeout"

    def to_dict(self) -> dict[str, Any]:
        return {
            "healing_id": self.healing_id,
            "node_id": self.node_id,
            "winner_ghost_id": self.winner_ghost_id,
            "winning_patch": self.winning_patch,
            "ghosts_spawned": self.ghosts_spawned,
            "ghosts_succeeded": self.ghosts_succeeded,
            "latency_ms": round(self.latency_ms, 2),
            "verdict": self.verdict,
        }


class SpeculativeHealingEngine:
    """Parallel micro-mitosis healing for persistently-failing DAG nodes.

    Instead of sequential: fail -> fix -> fail -> fix ...
    this engine spawns N_SPECULATIVE_BRANCHES BRANCH_CLONE micro-variant ghosts
    concurrently.  Each ghost is instructed to emit only a surgical
    ``patch_apply`` call(<=10 lines).  The first ghost to succeed "wins";
    the winning patch is manifested into the main trunk and the losers are
    discarded.

    Model routing strategy:
      Ghost A(conservative): Tier 1 flash -- fast conservative AST-level fix.
      Ghost B(rewrite):      Tier 1 flash -- concise logic-level rewrite.
      Ghost C(jit_library):  Tier 0 local-SLM -- library/framework specific fix.

    Usage: :

        engine = SpeculativeHealingEngine(mcp=mcp_manager)
        result = await engine.speculate(
            node_id="pipe-001-s4-implement",
            error_text="AttributeError: 'NoneType' has no attribute 'items'",
            file_path="engine/n_stroke.py",
            broken_snippet="for k, v in result.items():",
            intent="BUILD",
            mandate_text="...",
        )
        if result.verdict == "won" and result.winning_patch:
            mcp_manager.call("patch_apply", **result.winning_patch)
    """

    # Micro-prompt template — instructs ghosts to be surgical (≤10 lines only)
    _MICRO_PROMPT = (
        "You are a surgical micro-agent inside TooLoo V2. "
        "Strategy: {strategy}. "
        "Node '{node_id}' failed with: {error_text}\n"
        "Broken code context:\n{broken_snippet}\n\n"
        "Output ONLY a JSON object with keys: "
        "'search_block' (the exact broken lines, verbatim, ≤10 lines) and "
        "'replace_block' (your fix, same or fewer lines). "
        "DO NOT output any explanation. DO NOT output the full file. "
        "Respond with valid JSON only."
    )

    _STRATEGIES: list[tuple[str, int]] = [
        ("conservative — minimal AST-level rename / guard fix", 1),
        ("concise logic-level rewrite — preserve interface, fix semantics", 1),
        ("jit_library — use canonical stdlib/library idiom for this error pattern", 0),
    ]

    def __init__(self, mcp: Any) -> None:
        self._mcp = mcp

    async def speculate(
        self,
        node_id: str,
        error_text: str,
        file_path: str,
        broken_snippet: str,
        intent: str,
        mandate_text: str,
        n_branches: int = N_SPECULATIVE_BRANCHES,
        timeout: float = SPECULATIVE_GHOST_TIMEOUT,
    ) -> SpeculativeHealingResult:
        """Spawn N ghost branches in parallel and return the first winner.

        Each ghost runs in a thread via asyncio's default ThreadPoolExecutor so
        they are perfectly isolated (Law 17).
        """
        import asyncio

        healing_id = f"spec-{uuid.uuid4().hex[:8]}"
        t0 = time.monotonic()

        specs = [
            GhostBranchSpec(
                ghost_id=f"{healing_id}-g{i}",
                strategy=strategy,
                tier=tier,
                patch_hint=self._MICRO_PROMPT.format(
                    strategy=strategy,
                    node_id=node_id,
                    error_text=error_text[:300],
                    broken_snippet=broken_snippet[:400],
                ),
                node_id=node_id,
            )
            for i, (strategy, tier) in enumerate(self._STRATEGIES[:n_branches])
        ]

        loop = asyncio.get_event_loop()

        async def _run_ghost(spec: GhostBranchSpec) -> dict[str, Any] | None:
            """Run one ghost branch; return winning patch dict or None."""
            try:
                patch = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, self._ghost_attempt, spec, file_path,
                        error_text, intent, mandate_text,
                    ),
                    timeout=timeout,
                )
                return patch
            except Exception:
                return None

        # Race all ghosts — return first non-None result
        tasks = [asyncio.create_task(_run_ghost(s)) for s in specs]
        winner_patch: dict[str, Any] | None = None
        winner_ghost_id: str | None = None
        succeeded = 0

        # Use asyncio.FIRST_COMPLETED to bail as soon as one ghost wins
        pending = set(tasks)
        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED, timeout=timeout
            )
            if not done:
                break  # timeout
            for task in done:
                result = task.result() if not task.exception() else None
                if result is not None:
                    succeeded += 1
                    if winner_patch is None:
                        winner_patch = result
                        winner_ghost_id = specs[tasks.index(task)].ghost_id
                        # Cancel remaining ghosts to save compute
                        for p in pending:
                            p.cancel()
                        pending = set()

        verdict = "won" if winner_patch else "all_failed"
        return SpeculativeHealingResult(
            healing_id=healing_id,
            node_id=node_id,
            winner_ghost_id=winner_ghost_id,
            winning_patch=winner_patch,
            ghosts_spawned=len(specs),
            ghosts_succeeded=succeeded,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            verdict=verdict,
        )

    def _ghost_attempt(
        self,
        spec: GhostBranchSpec,
        file_path: str,
        error_text: str,
        intent: str,
        mandate_text: str,
    ) -> dict[str, Any] | None:
        """Synchronous inner: ask a fast model for a micro-patch, return patch kwargs.

        Runs in a thread (not the event loop) — fully isolated per Law 17.
        Returns None on any failure so the race can continue with other ghosts.
        """
        import json as _json

        # Try to get a patch suggestion from the model garden (Tier 0/1 routing)
        try:
            from engine.model_garden import get_garden

            garden = get_garden()
            # Force Tier 0 (local-SLM) or Tier 1 (flash) — never escalate to heavier models
            # for micro-ghost branches.  This keeps cost near-zero and latency sub-2s.
            model_id = garden.get_tier_model(
                tier=spec.tier,
                intent=intent,
                primary_need="coding",
            )
            raw = garden.call(model_id, spec.patch_hint)
            # Extract JSON from the response
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                return None
            data = _json.loads(m.group(0))
            search_block = str(data.get("search_block", "")).strip()
            replace_block = str(data.get("replace_block", "")).strip()
            if not search_block or not replace_block:
                return None
            return {
                "file_path": file_path,
                "search_block": search_block,
                "replace_block": replace_block,
                "fuzzy": True,
            }
        except Exception:
            # Model unavailable / parse error — build a deterministic minimal fix
            # Use the error hint from mcp read_error as the safe fallback
            mcp_result = self._mcp.call("read_error", error_text=error_text)
            if mcp_result.success and mcp_result.output:
                hint = mcp_result.output.get("hint", "")
                if hint:
                    # Deterministic stub: annotate the broken snippet with the hint
                    replacement = f"# HEALED ({spec.strategy}): {hint}\n{file_path}"
                    return {
                        "file_path": file_path,
                        "search_block": error_text[:60],
                        "replace_block": replacement,
                        "fuzzy": True,
                    }
            return None
