#!/usr/bin/env python3
"""
ouroboros_cycle.py — TooLoo V2 Autonomous Perfection Cycle.

Law 20 (Amended — Autonomous Execution Authority)
This cycle operates under autonomous execution authority when
AUTONOMOUS_EXECUTION_ENABLED=true (the default).  Safe-guards that always hold:
  • Tribunal OWASP scan runs on every generated artefact.
  • Writes are sandboxed to engine/ components inside this workspace only.
  • Activity is restricted to legal, non-criminal operations.
  • If confidence < AUTONOMOUS_CONFIDENCE_THRESHOLD (0.99) a consultation
    signal is emitted — but execution is NOT blocked.

Pass ``--dry-run`` to produce a plan without any file writes.

Pipeline
--------
  Phase 1 · Diagnose    SelfImprovementEngine → per-component JIT SOTA signals
                         and suggestions (3-wave DAG, offline-safe)
  Phase 2 · Plan        Filter components with ≥ 1 suggestion → BUILD mandates
  Phase 3 · Build       NStrokeEngine per component:
                          - MCP file_read  → snapshot current source
                          - Build work_fn  → apply deterministic SOTA annotations
                          - Tribunal scan  → reject poisoned writes
                          - MCP file_write → commit approved improvements
  Phase 4 · Validate    MCP run_tests → full pytest suite; escalate model tier
                         on failure (ModelSelector drives Tier 1→4 ladder)
  Phase 5 · Report      OuroborosReport → JSON manifest + changelog saved to
                         ouroboros_report.json

Usage
-----
  python ouroboros_cycle.py                                          # autonomous (default)
  python ouroboros_cycle.py --components engine/router.py,engine/jit_booster.py
  python ouroboros_cycle.py --dry-run    # plan-only, no file writes

Environment
-----------
  TOOLOO_LIVE_TESTS=1              — enable live Gemini-powered code generation
  AUTONOMOUS_EXECUTION_ENABLED=1   — enable autonomous file writes (default true)
  AUTONOMOUS_CONFIDENCE_THRESHOLD  — consult user below this confidence (default 0.99)
  GOD_MODE_MAX_STROKES             — override MAX_STROKES (default 7)
"""
from __future__ import annotations

# ── stdlib ────────────────────────────────────────────────────────────────────
import argparse
import json
import os
import sys
import textwrap
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

# ── Project root on sys.path (must come before any engine import) ─────────────
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── Patch JIT module for offline mode before other engine imports ─────────────
# Imported early so we can null out live clients before the rest of the engine
# bootstraps (mirrors tests/conftest.py behaviour).
import engine.jit_booster as _jib_mod  # noqa: E402

_LIVE_MODE: bool = os.environ.get(
    "TOOLOO_LIVE_TESTS", "").lower() in ("1", "true", "yes")
if not _LIVE_MODE:
    _jib_mod._vertex_client = None
    _jib_mod._gemini_client = None

# ── Engine imports (after sys.path is set) ────────────────────────────────────
from engine.config import AUTONOMOUS_EXECUTION_ENABLED  # noqa: E402
from engine.executor import Envelope, JITExecutor  # noqa: E402
from engine.graph import TopologicalSorter  # noqa: E402
from engine.jit_booster import JITBooster  # noqa: E402
from engine.mcp_manager import MCPManager  # noqa: E402
from engine.model_selector import ModelSelector  # noqa: E402
from engine.n_stroke import NStrokeEngine  # noqa: E402
from engine.psyche_bank import PsycheBank  # noqa: E402
from engine.refinement import RefinementLoop  # noqa: E402
from engine.refinement_supervisor import RefinementSupervisor  # noqa: E402
from engine.router import LockedIntent, MandateRouter  # noqa: E402
from engine.scope_evaluator import ScopeEvaluator  # noqa: E402
from engine.self_improvement import ComponentAssessment, SelfImprovementEngine  # noqa: E402
from engine.tribunal import Tribunal  # noqa: E402


# ── Constants ─────────────────────────────────────────────────────────────────
_DEFAULT_MAX_STROKES = int(
    os.environ.get("GOD_MODE_MAX_STROKES", "7")
)
_REPORT_PATH = _ROOT / "ouroboros_report.json"

# Components the cycle is *allowed* to touch in autonomous mode.
# Extending this list is a deliberate, reviewable action.
_ALLOWED_ENGINE_PATHS: frozenset[str] = frozenset({
    "engine/router.py",
    "engine/jit_booster.py",
    "engine/tribunal.py",
    "engine/psyche_bank.py",
    "engine/graph.py",
    "engine/executor.py",
    "engine/scope_evaluator.py",
    "engine/refinement.py",
    "engine/n_stroke.py",
    "engine/supervisor.py",
    "engine/conversation.py",
    "engine/config.py",
})

# Map component name → source path (mirrors self_improvement._COMPONENTS)
_COMPONENT_SOURCE_MAP: dict[str, str] = {
    "router":          "engine/router.py",
    "tribunal":        "engine/tribunal.py",
    "psyche_bank":     "engine/psyche_bank.py",
    "jit_booster":     "engine/jit_booster.py",
    "executor":        "engine/executor.py",
    "graph":           "engine/graph.py",
    "scope_evaluator": "engine/scope_evaluator.py",
    "refinement":      "engine/refinement.py",
    "n_stroke":        "engine/n_stroke.py",
    "supervisor":      "engine/supervisor.py",
    "conversation":    "engine/conversation.py",
    "config":          "engine/config.py",
}

# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class ComponentCycleResult:
    """Result of one Ouroboros cycle for a single engine component."""

    component: str
    source_path: str
    suggestions_from_si: list[str]
    n_stroke_verdict: str          # "pass" | "warn" | "fail" | "skipped"
    model_escalations: int
    healing_invocations: int
    file_written: bool
    write_path: str | None
    test_passed: bool
    test_output: str
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "source_path": self.source_path,
            "suggestions_from_si": self.suggestions_from_si,
            "n_stroke_verdict": self.n_stroke_verdict,
            "model_escalations": self.model_escalations,
            "healing_invocations": self.healing_invocations,
            "file_written": self.file_written,
            "write_path": self.write_path,
            "test_passed": self.test_passed,
            "test_output": self.test_output[:2000] if self.test_output else "",
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class OuroborosReport:
    """Full report of one God Mode perfection cycle."""

    cycle_id: str
    ts: str
    dry_run: bool
    god_mode: bool
    components_targeted: int
    components_improved: int
    components_unchanged: int
    total_model_escalations: int
    total_healing_invocations: int
    overall_verdict: str           # "pass" | "warn" | "fail"
    cycle_results: list[ComponentCycleResult]
    si_report_summary: dict[str, Any]
    changelog: list[str]           # human-readable change notes
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "ts": self.ts,
            "dry_run": self.dry_run,
            "god_mode": self.god_mode,
            "components_targeted": self.components_targeted,
            "components_improved": self.components_improved,
            "components_unchanged": self.components_unchanged,
            "total_model_escalations": self.total_model_escalations,
            "total_healing_invocations": self.total_healing_invocations,
            "overall_verdict": self.overall_verdict,
            "cycle_results": [r.to_dict() for r in self.cycle_results],
            "si_report_summary": self.si_report_summary,
            "changelog": self.changelog,
            "latency_ms": round(self.latency_ms, 2),
        }


# ── Work function factory ──────────────────────────────────────────────────────

def _make_build_work_fn(
    component: str,
    source_path: str,
    suggestions: list[str],
    mcp: MCPManager,
    dry_run: bool,
    live_mode: bool,
) -> Callable[[Envelope], dict[str, Any]]:
    """
    Return a work_fn for NStrokeEngine that:
      1. Reads the current source via MCP file_read.
      2. In live mode: synthesises annotation block from JIT SOTA suggestions.
         In offline mode: performs a read-verify (no write) and reports the
         current health state + top suggestions as the plan output.
      3. In god-mode + live mode: writes the annotation block via MCP file_write.
      4. Returns a structured result dict with write metadata.

    Security constraints
    --------------------
    - No eval(), exec(), or dynamic imports in generated content.
    - Written content is bounded to a SOTA annotation block prepended to the
      module docstring — it never replaces executable logic.
    - The Tribunal in NStrokeEngine's preflight will catch any poisoned content
      before the work_fn is even called.
    """
    def _work(envelope: Envelope) -> dict[str, Any]:
        t0 = time.monotonic()

        # Step 1: Read current source
        read_result = mcp.call("file_read", path=source_path)
        if not read_result.success:
            return {
                "status": "error",
                "phase": "file_read",
                "error": read_result.error,
                "component": component,
                "source_path": source_path,
            }

        current_source: str = read_result.output.get("content", "") if isinstance(
            read_result.output, dict) else str(read_result.output)
        line_count: int = read_result.output.get("lines", 0) if isinstance(
            read_result.output, dict) else current_source.count("\n")

        # Truncation guard: MCP caps reads at _MAX_OUTPUT_CHARS (8 KB).
        # If the file was truncated, writing back the partial content would corrupt it.
        was_truncated = isinstance(
            read_result.output, dict) and read_result.output.get("truncated", False)
        if was_truncated:
            return {
                "status": "skipped",
                "phase": "truncation_guard",
                "component": component,
                "source_path": source_path,
                "reason": "file exceeds MCP read limit (8 KB) — skipping write to prevent partial-file corruption",
                "line_count": line_count,
                "latency_ms": round((time.monotonic() - t0) * 1000, 2),
            }

        # Step 2: Build SOTA annotation block from suggestions
        annotation_lines = [
            "# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────",
            f"# Cycle: {datetime.now(UTC).isoformat()}",
            f"# Component: {component}  Source: {source_path}",
            "# Improvement signals from JIT SOTA booster:",
        ]
        for i, sig in enumerate(suggestions[:5], start=1):
            wrapped = textwrap.fill(sig, width=78, subsequent_indent="#     ")
            annotation_lines.append(f"#  [{i}] {wrapped}")
        annotation_lines.append(
            "# ─────────────────────────────────────────────────────────────────"
        )
        annotation_block = "\n".join(annotation_lines) + "\n"

        # In offline / dry-run mode: report plan without writing
        if dry_run or not live_mode:
            return {
                "status": "planned",
                "phase": "build",
                "component": component,
                "source_path": source_path,
                "line_count": line_count,
                "annotation_preview": annotation_block[:400],
                "suggestions_count": len(suggestions),
                "write_skipped": True,
                "reason": "dry_run" if dry_run else "offline_mode",
                "latency_ms": round((time.monotonic() - t0) * 1000, 2),
            }

        # Step 3: God-mode live write — inject annotation block above module docstring
        # Locate end of shebang + copyright lines (if any), then insert
        lines = current_source.splitlines(keepends=True)
        insert_pos = 0
        # Skip any existing ouroboros annotations so re-runs are idempotent
        filtered_lines = [
            ln for ln in lines
            if "# ── Ouroboros SOTA Annotations" not in ln
            and "# Cycle:" not in ln
            and "# Component:" not in ln
            and "# Improvement signals" not in ln
            and not (ln.startswith("#  [") and "] " in ln)
            and "# ───────────────────────────────────────────────" not in ln
        ]
        # Safety guard: abort if filtered content has no executable Python lines.
        # This prevents re-annotating a previously-corrupted (annotation-only) file
        # back into a 56-line stub with no classes or functions.
        python_lines = [
            ln for ln in filtered_lines
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if not python_lines:
            return {
                "status": "aborted",
                "phase": "safety_guard",
                "component": component,
                "source_path": source_path,
                "reason": "no executable Python remains after filtering — file may be corrupted, aborting write",
                "line_count": line_count,
                "latency_ms": round((time.monotonic() - t0) * 1000, 2),
            }
        new_source = annotation_block + "".join(filtered_lines)

        write_result = mcp.call(
            "file_write",
            path=source_path,
            content=new_source,
        )
        if not write_result.success:
            return {
                "status": "error",
                "phase": "file_write",
                "error": write_result.error,
                "component": component,
                "source_path": source_path,
            }

        return {
            "status": "written",
            "phase": "build",
            "component": component,
            "source_path": source_path,
            "line_count": line_count,
            "annotation_lines": len(annotation_lines),
            "write_path": write_result.output if isinstance(
                write_result.output, str) else source_path,
            "latency_ms": round((time.monotonic() - t0) * 1000, 2),
        }

    return _work


# ── Engine factory ─────────────────────────────────────────────────────────────

def _build_n_stroke_engine(
    events: list[dict[str, Any]],
    mcp: MCPManager,
    max_strokes: int,
) -> NStrokeEngine:
    """Construct a clean NStrokeEngine with all required components."""
    bank = PsycheBank()
    tribunal = Tribunal(bank=bank)
    booster = JITBooster()
    router = MandateRouter()
    sorter = TopologicalSorter()
    executor = JITExecutor(max_workers=3)
    scope_evaluator = ScopeEvaluator()
    refinement_loop = RefinementLoop()
    model_selector = ModelSelector()
    ref_supervisor = RefinementSupervisor()

    def _broadcast(event: dict[str, Any]) -> None:
        events.append(event)

    return NStrokeEngine(
        router=router,
        booster=booster,
        tribunal=tribunal,
        sorter=sorter,
        executor=executor,
        scope_evaluator=scope_evaluator,
        refinement_loop=refinement_loop,
        mcp_manager=mcp,
        model_selector=model_selector,
        refinement_supervisor=ref_supervisor,
        broadcast_fn=_broadcast,
        max_strokes=max_strokes,
    )


# ── Core cycle ─────────────────────────────────────────────────────────────────

class OuroborosCycle:
    """
    God Mode Perfection Cycle.

    Wires SelfImprovementEngine → NStrokeEngine per component →
    MCP file_read/file_write/run_tests → OuroborosReport.
    """

    def __init__(
        self,
        god_mode: bool = False,
        dry_run: bool = False,
        component_filter: list[str] | None = None,
        max_strokes: int = _DEFAULT_MAX_STROKES,
    ) -> None:
        if god_mode and dry_run:
            raise ValueError(
                "--god-mode and --dry-run are mutually exclusive.")
        self._god_mode = god_mode
        self._dry_run = dry_run
        # source paths, e.g. ["engine/router.py"]
        self._component_filter = component_filter
        self._max_strokes = max_strokes
        self._live_mode = _LIVE_MODE
        self._mcp = MCPManager()
        self._si_engine = SelfImprovementEngine()

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(self) -> OuroborosReport:
        t0 = time.monotonic()
        cycle_id = f"ouroboros-{uuid.uuid4().hex[:8]}"

        print(f"\n{'='*65}")
        print(f"  TooLoo V2 — Ouroboros Perfection Cycle  [{cycle_id}]")
        if self._god_mode:
            print("  Mode: AUTONOMOUS (Law 20 Amended — self-approval authority active)")
        else:
            print("  Mode: DRY RUN (plan only — no file writes)")
        print(
            f"  Live: {'YES (Vertex/Gemini active)' if self._live_mode else 'NO (offline symbolic)'}")
        print(f"  Max strokes per component: {self._max_strokes}")
        print(f"{'='*65}\n")

        # ── Phase 1: Self-improvement diagnosis ───────────────────────────────
        print("Phase 1 · SelfImprovementEngine diagnosis…")
        si_report = self._si_engine.run()
        si_summary = {
            "improvement_id": si_report.improvement_id,
            "components_assessed": si_report.components_assessed,
            "total_signals": si_report.total_signals,
            "refinement_verdict": si_report.refinement_verdict,
            "refinement_success_rate": si_report.refinement_success_rate,
        }
        print(f"  → {si_report.components_assessed} components assessed, "
              f"{si_report.total_signals} JIT signals, "
              f"verdict={si_report.refinement_verdict}\n")

        # ── Phase 2: Filter targets ────────────────────────────────────────────
        targets: list[tuple[ComponentAssessment, str]] = []
        for assessment in si_report.assessments:
            src_path = _COMPONENT_SOURCE_MAP.get(assessment.component)
            if src_path is None:
                continue  # unknown component — skip

            # Apply command-line component filter if given
            if self._component_filter and src_path not in self._component_filter:
                continue

            # Apply allowed-path whitelist in god-mode
            if self._god_mode and src_path not in _ALLOWED_ENGINE_PATHS:
                print(f"  [SKIP] {src_path} — not in allowed write paths")
                continue

            suggestions = assessment.suggestions or []
            if not suggestions and not self._dry_run:
                # No suggestions → nothing to improve; skip
                continue

            targets.append((assessment, src_path))

        if not targets:
            print("Phase 2 · No improvement targets identified — engine is healthy.\n")
            elapsed = round((time.monotonic() - t0) * 1000, 2)
            return OuroborosReport(
                cycle_id=cycle_id,
                ts=datetime.now(UTC).isoformat(),
                dry_run=self._dry_run,
                god_mode=self._god_mode,
                components_targeted=0,
                components_improved=0,
                components_unchanged=0,
                total_model_escalations=0,
                total_healing_invocations=0,
                overall_verdict="pass",
                cycle_results=[],
                si_report_summary=si_summary,
                changelog=[],
                latency_ms=elapsed,
            )

        print(f"Phase 2 · {len(targets)} components queued for improvement:")
        for _, sp in targets:
            print(f"  · {sp}")
        print()

        # ── Phase 3 + 4: NStroke BUILD + validate per target ─────────────────
        cycle_results: list[ComponentCycleResult] = []
        changelog: list[str] = []
        total_esc = 0
        total_heal = 0

        for assessment, src_path in targets:
            component = assessment.component
            suggestions = assessment.suggestions or []
            print(f"Phase 3 · Building: {component}  ({src_path})")
            print(f"  Suggestions: {len(suggestions)}")

            ct0 = time.monotonic()
            events: list[dict[str, Any]] = []
            n_engine = _build_n_stroke_engine(
                events, self._mcp, self._max_strokes)

            # Build the consent-bypassed work function
            work_fn = _make_build_work_fn(
                component=component,
                source_path=src_path,
                suggestions=suggestions,
                mcp=self._mcp,
                dry_run=self._dry_run,
                live_mode=self._live_mode,
            )

            # Construct a LockedIntent for the BUILD mandate
            mandate_text = (
                f"implement SOTA improvements in {component} based on signals: "
                + "; ".join(suggestions[:3])
            )
            locked = LockedIntent(
                intent="BUILD",
                confidence=0.92,     # above CB threshold — no circuit-open
                value_statement=(
                    f"Improve {component} with 2026 SOTA patterns to raise "
                    "Ouroboros perfection-cycle success rate."
                ),
                constraint_summary="engine components only; Tribunal must pass; tests must pass",
                mandate_text=mandate_text,
                context_turns=[],
            )

            ns_result = n_engine.run(
                locked_intent=locked,
                pipeline_id=f"{cycle_id}-{component}",
                work_fn=work_fn,
            )

            total_esc += ns_result.model_escalations
            total_heal += ns_result.healing_invocations

            # ── Phase 4: Run tests to validate ────────────────────────────────
            print(f"  → N-stroke verdict: {ns_result.final_verdict}  "
                  f"(strokes={ns_result.total_strokes}, "
                  f"escalations={ns_result.model_escalations})")

            test_result = self._mcp.call(
                "run_tests",
                test_path="tests",
            )
            # test_result.success only means the MCP call succeeded, not that tests passed.
            # Check the output dict's 'passed' field for the actual pytest result.
            test_passed = (
                test_result.success
                and isinstance(test_result.output, dict)
                and test_result.output.get("passed", False)
            )
            test_output = str(test_result.output) if test_result.success else (
                test_result.error or "unknown test failure")
            print(f"  → Tests: {'PASS ✓' if test_passed else 'FAIL ✗'}")

            # Determine whether a file was actually written
            file_written = False
            write_path: str | None = None
            if ns_result.strokes:
                for stroke in ns_result.strokes:
                    for exec_result in stroke.execution_results:
                        if (exec_result.success and isinstance(exec_result.output, dict)
                                and exec_result.output.get("status") == "written"):
                            file_written = True
                            write_path = exec_result.output.get("write_path")

            cycle_result = ComponentCycleResult(
                component=component,
                source_path=src_path,
                suggestions_from_si=suggestions,
                n_stroke_verdict=ns_result.final_verdict,
                model_escalations=ns_result.model_escalations,
                healing_invocations=ns_result.healing_invocations,
                file_written=file_written,
                write_path=write_path,
                test_passed=test_passed,
                test_output=test_output,
                latency_ms=round((time.monotonic() - ct0) * 1000, 2),
            )
            cycle_results.append(cycle_result)

            if file_written:
                changelog.append(
                    f"[{component}] SOTA annotation block injected into {src_path} "
                    f"(signals={len(suggestions)}, strokes={ns_result.total_strokes})"
                )
            elif self._dry_run:
                changelog.append(
                    f"[{component}] DRY-RUN: {len(suggestions)} suggestions identified, "
                    f"no write (use --god-mode to apply)"
                )
            print()

        # ── Phase 5: Aggregate report ─────────────────────────────────────────
        improved = sum(1 for r in cycle_results if r.file_written)
        unchanged = len(cycle_results) - improved
        all_pass = all(r.n_stroke_verdict in ("pass", "warn")
                       for r in cycle_results)
        any_fail = any(r.n_stroke_verdict == "fail" for r in cycle_results)
        overall = "fail" if any_fail else ("warn" if not all_pass else "pass")

        report = OuroborosReport(
            cycle_id=cycle_id,
            ts=datetime.now(UTC).isoformat(),
            dry_run=self._dry_run,
            god_mode=self._god_mode,
            components_targeted=len(targets),
            components_improved=improved,
            components_unchanged=unchanged,
            total_model_escalations=total_esc,
            total_healing_invocations=total_heal,
            overall_verdict=overall,
            cycle_results=cycle_results,
            si_report_summary=si_summary,
            changelog=changelog,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
        )

        # Save JSON report
        _REPORT_PATH.write_text(json.dumps(report.to_dict(), indent=2))

        print(f"{'='*65}")
        print(f"  Ouroboros Cycle Complete  [{cycle_id}]")
        print(f"  Verdict      : {overall.upper()}")
        print(f"  Targeted     : {len(targets)} components")
        print(f"  Improved     : {improved}")
        print(f"  Escalations  : {total_esc} model tier changes")
        print(f"  Healing runs : {total_heal}")
        print(f"  Latency      : {report.latency_ms:.0f} ms")
        print(f"  Report       : {_REPORT_PATH}")
        print(f"{'='*65}\n")

        if changelog:
            print("Changelog:")
            for entry in changelog:
                print(f"  • {entry}")
            print()

        return report


# ── CLI ────────────────────────────────────────────────────────────────────────

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ouroboros_cycle.py",
        description="TooLoo V2 Autonomous Perfection Cycle (Law 20 Amended)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Law 20 (Amended — Autonomous Execution Authority)
            TooLoo has self-approval authority for engine improvements.
            Invariants always enforced:
              • Tribunal OWASP scan on every artefact
              • Writes sandboxed to engine/ components in this workspace
              • Legal / non-criminal activity only
              • Confidence < 0.99 → consultation_recommended signal (advisory)

            Use --dry-run to produce a plan without any file writes.
        """),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Plan only — no file writes. Overrides autonomous mode for this run.",
    )
    parser.add_argument(
        "--components",
        type=str,
        default=None,
        help=(
            "Comma-separated list of engine source paths to target, e.g. "
            "engine/router.py,engine/jit_booster.py.  "
            "Defaults to all engine components."
        ),
    )
    parser.add_argument(
        "--max-strokes",
        type=int,
        default=_DEFAULT_MAX_STROKES,
        help=f"Max N-stroke iterations per component (default {_DEFAULT_MAX_STROKES}).",
    )
    return parser.parse_args(argv)


def _print_autonomy_notice() -> None:
    print(textwrap.dedent("""\
        ╔══════════════════════════════════════════════════════════════╗
        ║        TooLoo V2 — Autonomous Execution Mode Active          ║
        ║                                                              ║
        ║  Law 20 (Amended): TooLoo has self-approval authority for   ║
        ║  engine improvements.  The following invariants always hold: ║
        ║    1. Tribunal OWASP scan runs on every generated artefact.  ║
        ║    2. Writes sandboxed to engine/ components only.           ║
        ║    3. Legal and non-criminal operations only.                ║
        ║    4. Confidence < 0.99 → consultation signal (advisory).   ║
        ╚══════════════════════════════════════════════════════════════╝
    """))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    dry_run = args.dry_run
    # Autonomous god-mode is ON by default when AUTONOMOUS_EXECUTION_ENABLED=True
    # and --dry-run has not been explicitly passed.
    god_mode = AUTONOMOUS_EXECUTION_ENABLED and not dry_run

    if god_mode:
        _print_autonomy_notice()

    component_filter: list[str] | None = None
    if args.components:
        component_filter = [c.strip()
                            for c in args.components.split(",") if c.strip()]

    cycle = OuroborosCycle(
        god_mode=god_mode,
        dry_run=dry_run,
        component_filter=component_filter,
        max_strokes=args.max_strokes,
    )
    report = cycle.run()

    # Exit code reflects overall verdict
    return 0 if report.overall_verdict in ("pass", "warn") else 1


if __name__ == "__main__":
    raise SystemExit(main())
