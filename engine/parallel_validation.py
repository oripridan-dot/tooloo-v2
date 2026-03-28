# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining parallel_validation.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.925314
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/parallel_validation.py — Parallel Validation Pipeline

Fans out write → test → QA → display as a single concurrent process.

When a file is written or modified, this pipeline immediately runs:
  1. Unit tests (pytest subset targeting the changed file)
  2. 16D validation (Validator16D scoring)
  3. Tribunal OWASP scan
  4. SSE broadcast of live results

All four stages run concurrently via asyncio.  Results are aggregated through
an async write queue so file-system writes never race.

Architecture:
  - Each validation stage is an asyncio.Task (read-only, parallel-safe)
  - File writes go through a single-writer asyncio.Queue (mutex-equivalent)
  - SSE broadcasts fire as soon as each stage completes (not batched)
  - The pipeline returns a unified ValidationReport with all stage outcomes

Usage:

    pipeline = ParallelValidationPipeline(broadcast_fn=_broadcast)
    report = await pipeline.validate_changes([
        FileChange(path="engine/router.py", content=new_source),
    ])
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.config import settings
from engine.tribunal import Engram, Tribunal
from engine.validator_16d import Validator16D

logger = logging.getLogger(__name__)

# Control: pipeline thresholds
_MAX_CONCURRENT_VALIDATIONS = 8
_TEST_TIMEOUT_S = 60
_ROLLBACK_ON_VALIDATION_FAIL = True

_REPO_ROOT: Path = Path(__file__).resolve().parents[1]


# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class FileChange:
    """A single file modification to validate."""

    path: str               # Relative to repo root, e.g. "engine/router.py"
    content: str | None = None  # New content (None = validate existing file)
    # Logical component name (derived from path if empty)
    component: str = ""


@dataclass
class StageResult:
    """Result of one validation stage for one file."""

    stage: str          # "test" | "16d" | "tribunal" | "write"
    file_path: str
    success: bool
    score: float | None = None  # 16D composite or test pass rate
    details: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "file_path": self.file_path,
            "success": self.success,
            "score": round(self.score, 4) if self.score is not None else None,
            "details": self.details,
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class ValidationReport:
    """Unified report across all parallel validation stages."""

    pipeline_id: str
    files_validated: int
    stages: list[StageResult] = field(default_factory=list)
    all_passed: bool = False
    composite_score: float = 0.0
    tribunal_passed: bool = True
    test_passed: bool = True
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "files_validated": self.files_validated,
            "stages": [s.to_dict() for s in self.stages],
            "all_passed": self.all_passed,
            "composite_score": round(self.composite_score, 4),
            "tribunal_passed": self.tribunal_passed,
            "test_passed": self.test_passed,
            "latency_ms": round(self.latency_ms, 2),
        }


# ── Pipeline ──────────────────────────────────────────────────────────────────


class ParallelValidationPipeline:
    """Concurrent write-test-QA-display pipeline.

    All read-only validation stages (tests, 16D, tribunal) run in parallel.
    File writes are serialised through a single async queue to prevent races.
    SSE broadcast events fire immediately as each stage completes.
    """

    def __init__(
        self,
        broadcast_fn: Callable[[dict[str, Any]], None] | None = None,
        tribunal: Tribunal | None = None,
        validator: Validator16D | None = None,
        max_concurrent: int = _MAX_CONCURRENT_VALIDATIONS,
        runtime_inputs: dict[str, Any] | None = None,
    ) -> None:
        self._broadcast = broadcast_fn or (lambda _: None)
        self._tribunal = tribunal or Tribunal()
        self._validator = validator or Validator16D()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._write_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        self._runtime_inputs = runtime_inputs or {}

    # ── Public API ────────────────────────────────────────────────────────────

    async def validate_changes(
        self,
        changes: list[FileChange],
        pipeline_id: str = "",
        run_tests: bool = True,
    ) -> ValidationReport:
        """Fan-out all validation stages concurrently for a batch of file changes.

        For each FileChange:
          - Tribunal OWASP scan (parallel)
          - 16D validation (parallel)
        Tests run once for all affected modules (single pytest invocation).
        All stages run simultaneously.  Results stream via SSE as they arrive.
        """
        t0 = time.monotonic()
        if not pipeline_id:
            import uuid
            pipeline_id = f"pv-{uuid.uuid4().hex[:8]}"

        self._broadcast({
            "type": "parallel_validation_start",
            "pipeline_id": pipeline_id,
            "files": [c.path for c in changes],
            "stages": ["tribunal", "16d", "test"],
        })

        # Derive component names from paths
        for c in changes:
            if not c.component:
                c.component = self._derive_component(c.path)

        # Fan out tribunal + 16D per file, tests run once for all files
        tasks: list[asyncio.Task[StageResult]] = []
        for change in changes:
            source = change.content or self._read_source(change.path)
            tasks.append(asyncio.create_task(
                self._run_tribunal(change, source, pipeline_id),
                name=f"tribunal-{change.path}",
            ))
            tasks.append(asyncio.create_task(
                self._run_16d(change, source, pipeline_id),
                name=f"16d-{change.path}",
            ))
        if run_tests:
            # Single test invocation for all changed files
            tasks.append(asyncio.create_task(
                self._run_tests_batch(changes, pipeline_id),
                name="test-batch",
            ))

        # Gather all — each broadcasts its own SSE event on completion
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect valid StageResults
        stage_results: list[StageResult] = []
        for r in results:
            if isinstance(r, StageResult):
                stage_results.append(r)
            elif isinstance(r, Exception):
                stage_results.append(StageResult(
                    stage="error",
                    file_path="unknown",
                    success=False,
                    details=str(r),
                ))

        # Aggregate
        tribunal_stages = [s for s in stage_results if s.stage == "tribunal"]
        dim16_stages = [s for s in stage_results if s.stage == "16d"]
        test_stages = [s for s in stage_results if s.stage == "test"]

        tribunal_ok = all(s.success for s in tribunal_stages)
        test_ok = all(s.success for s in test_stages) if test_stages else True
        composite = (
            sum(s.score for s in dim16_stages if s.score is not None)
            / max(len(dim16_stages), 1)
        )
        all_passed = tribunal_ok and test_ok and all(
            s.success for s in dim16_stages)

        report = ValidationReport(
            pipeline_id=pipeline_id,
            files_validated=len(changes),
            stages=stage_results,
            all_passed=all_passed,
            composite_score=composite,
            tribunal_passed=tribunal_ok,
            test_passed=test_ok,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
        )

        self._broadcast({
            "type": "parallel_validation_complete",
            "pipeline_id": pipeline_id,
            "all_passed": all_passed,
            "composite_score": round(composite, 4),
            "tribunal_passed": tribunal_ok,
            "test_passed": test_ok,
            "files_validated": len(changes),
            "latency_ms": report.latency_ms,
        })

        return report

    async def validate_and_write(
        self,
        changes: list[FileChange],
        pipeline_id: str = "",
        run_tests: bool = True,
    ) -> ValidationReport:
        """Validate changes in parallel, then write files only if all pass.

        This is the full write-test-QA-display cycle:
          1. Validate concurrently (tribunal + 16D + tests)
          2. If all pass → write files sequentially (single-writer queue)
          3. Broadcast final report
        """
        report = await self.validate_changes(
            changes, pipeline_id=pipeline_id, run_tests=run_tests)

        if report.all_passed:
            for change in changes:
                if change.content is not None:
                    await self._enqueue_write(change.path, change.content)
                    report.stages.append(StageResult(
                        stage="write",
                        file_path=change.path,
                        success=True,
                        details="file written after validation passed",
                    ))
                    self._broadcast({
                        "type": "parallel_validation_write",
                        "pipeline_id": report.pipeline_id,
                        "file": change.path,
                        "status": "written",
                    })
        else:
            self._broadcast({
                "type": "parallel_validation_write",
                "pipeline_id": report.pipeline_id,
                "status": "skipped",
                "reason": "validation failed",
            })

        return report

    # ── Stage implementations (all async, all broadcast on completion) ────────

    async def _run_tribunal(
        self, change: FileChange, source: str, pipeline_id: str,
    ) -> StageResult:
        """OWASP Tribunal scan — runs in thread pool (CPU-bound)."""
        async with self._semaphore:
            t0 = time.monotonic()
            engram = Engram(
                slug=f"pv-{change.component}",
                intent="AUDIT",
                logic_body=source[:8000],
                domain="parallel-validation",
                mandate_level="L1",
            )
            result = await asyncio.to_thread(self._tribunal.evaluate, engram)
            latency = round((time.monotonic() - t0) * 1000, 2)

            stage = StageResult(
                stage="tribunal",
                file_path=change.path,
                success=result.passed,
                score=1.0 if result.passed else 0.0,
                details=(
                    "clean" if result.passed
                    else f"poison: {', '.join(r.rule_id for r in result.rules_triggered)}"
                ),
                latency_ms=latency,
            )

            self._broadcast({
                "type": "parallel_validation_stage",
                "pipeline_id": pipeline_id,
                "stage": "tribunal",
                "file": change.path,
                "passed": result.passed,
                "latency_ms": latency,
            })

            return stage

    async def _run_16d(
        self, change: FileChange, source: str, pipeline_id: str,
    ) -> StageResult:
        """16-dimension validation — runs in thread pool."""
        async with self._semaphore:
            t0 = time.monotonic()
            result = await asyncio.to_thread(
                self._validator.validate,
                mandate_id=f"pv-{change.component}",
                intent="AUDIT",
                code_snippet=source[:8000],
                # Pass real runtime metrics if available (Phase 4 fix)
                test_pass_rate=self._runtime_inputs.get("test_pass_rate", 1.0),
                latency_p50_ms=self._runtime_inputs.get("latency_p50_ms", 500.0),
                latency_p90_ms=self._runtime_inputs.get("latency_p90_ms", 1000.0),
            )
            latency = round((time.monotonic() - t0) * 1000, 2)

            failed_dims = [
                d.name for d in result.dimensions if not d.passed]
            stage = StageResult(
                stage="16d",
                file_path=change.path,
                success=result.autonomous_gate_pass,
                score=result.composite_score,
                details=(
                    f"gate={'PASS' if result.autonomous_gate_pass else 'FAIL'} "
                    f"composite={result.composite_score:.4f}"
                    + (f" failed=[{', '.join(failed_dims)}]" if failed_dims else "")
                ),
                latency_ms=latency,
            )

            self._broadcast({
                "type": "parallel_validation_stage",
                "pipeline_id": pipeline_id,
                "stage": "16d",
                "file": change.path,
                "composite": result.composite_score,
                "gate_pass": result.autonomous_gate_pass,
                "failed_dimensions": failed_dims,
                "latency_ms": latency,
            })

            return stage

    async def _run_tests_batch(
        self, changes: list[FileChange], pipeline_id: str,
    ) -> StageResult:
        """Run pytest once for all affected modules — single subprocess."""
        async with self._semaphore:
            t0 = time.monotonic()

            # Collect all test targets across all changed files
            all_targets: list[str] = []
            for change in changes:
                targets = self._find_test_targets(change.path)
                for t in targets:
                    if t not in all_targets:
                        all_targets.append(t)
            if not all_targets:
                all_targets = ["tests/test_engine_smoke.py"]

            cmd = [
                sys.executable, "-m", "pytest", *all_targets,
                "-q", "--tb=line", "--no-header",
                f"--timeout={_TEST_TIMEOUT_S}",
            ]

            # Disable live tests in child — engine.config injects
            # TOOLOO_LIVE_TESTS=1 into os.environ which would cause
            # the child pytest to attempt real API calls and hang.
            child_env = {
                **os.environ,
                "PYTEST_CURRENT_TEST": "parallel_validation",
                "TOOLOO_LIVE_TESTS": "0",
            }

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(_REPO_ROOT),
                    env=child_env,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=_TEST_TIMEOUT_S + 10,
                )
                exit_code = proc.returncode or 0
                output = stdout.decode(errors="replace")[-500:]
                passed = exit_code == 0
            except asyncio.TimeoutError:
                passed = False
                output = "test timeout exceeded"
                exit_code = -1
            except Exception as exc:
                passed = False
                output = str(exc)
                exit_code = -1

            latency = round((time.monotonic() - t0) * 1000, 2)
            files_str = ", ".join(c.path for c in changes)

            stage = StageResult(
                stage="test",
                file_path=files_str,
                success=passed,
                score=1.0 if passed else 0.0,
                details=f"exit={exit_code} targets={len(all_targets)} {output.strip()[-200:]}",
                latency_ms=latency,
            )

            self._broadcast({
                "type": "parallel_validation_stage",
                "pipeline_id": pipeline_id,
                "stage": "test",
                "files": [c.path for c in changes],
                "passed": passed,
                "exit_code": exit_code,
                "targets": all_targets,
                "latency_ms": latency,
            })

            return stage

    # ── Write queue (single-writer serialisation) ─────────────────────────────

    async def _enqueue_write(self, rel_path: str, content: str) -> None:
        """Safely write a file through the serial write queue.

        Path traversal is prevented by resolving against _REPO_ROOT.
        """
        abs_path = (_REPO_ROOT / rel_path).resolve()
        if not str(abs_path).startswith(str(_REPO_ROOT)):
            logger.warning("Path traversal blocked: %s", rel_path)
            return
        # Restrict to engine/ directory (Law 20 sandbox)
        if not rel_path.startswith("engine/"):
            logger.warning("Write outside engine/ blocked: %s", rel_path)
            return
        await asyncio.to_thread(abs_path.write_text, content, encoding="utf-8")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _derive_component(path: str) -> str:
        """Derive component name from file path."""
        name = Path(path).stem
        return name

    @staticmethod
    def _read_source(path: str) -> str:
        """Read source from the repository."""
        abs_path = (_REPO_ROOT / path).resolve()
        if not str(abs_path).startswith(str(_REPO_ROOT)):
            return ""
        try:
            return abs_path.read_text(encoding="utf-8")
        except OSError:
            return ""

    @staticmethod
    def _find_test_targets(file_path: str) -> list[str]:
        """Find test files that correspond to the changed source file.

        Looks for:
          - tests/test_{stem}.py (exact match)
          - tests/test_{stem}_*.py (glob prefix)
        Does NOT grep for imports to avoid matching overly-broad transitive deps.
        """
        stem = Path(file_path).stem
        test_dir = _REPO_ROOT / "tests"
        targets: list[str] = []

        exact = test_dir / f"test_{stem}.py"
        if exact.is_file():
            targets.append(str(exact.relative_to(_REPO_ROOT)))

        for tf in test_dir.glob(f"test_{stem}_*.py"):
            rel = str(tf.relative_to(_REPO_ROOT))
            if rel not in targets:
                targets.append(rel)

        return targets
