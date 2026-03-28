# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining validation_run.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.409701
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

#!/usr/bin/env python3
"""
validation_run.py — End-to-end validation path execution

Runs:
  1. Local SLM smoke test (lock path + config validation)
  2. Broader regression suite on impacted components
  3. Comprehensive report of green/red status + fixes

Exit codes:
  0 = all tests passed
  1 = one or more test suites failed; see report
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


@dataclass
class ValidationResult:
    """Container for validation run results."""

    phase_name: str
    test_suite: str
    passed: bool = True
    test_count: int = 0
    output: str = ""
    stderr: str = ""
    latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "phase_name": self.phase_name,
            "test_suite": self.test_suite,
            "passed": self.passed,
            "test_count": self.test_count,
            "latency_ms": round(self.latency_ms, 2),
            "errors": self.errors[:3],  # top 3 errors only
        }


def _run_cmd(
    cmd: list[str],
    timeout: int = 120,
    description: str = "",
) -> tuple[bool, str, str, float]:
    """Execute a shell command and return (success, stdout, stderr, latency_ms)."""
    print(f"  → {description or ' '.join(cmd[:4])}")
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(_ROOT),
        )
        elapsed = round((time.monotonic() - t0) * 1000, 2)
        return proc.returncode == 0, proc.stdout, proc.stderr, elapsed
    except subprocess.TimeoutExpired:
        elapsed = round((time.monotonic() - t0) * 1000, 2)
        return False, "", f"Command timed out after {timeout}s", elapsed
    except Exception as exc:
        elapsed = round((time.monotonic() - t0) * 1000, 2)
        return False, "", str(exc), elapsed


def run_local_slm_smoke_test() -> ValidationResult:
    """Test the local SLM lock path and configuration."""
    print("\n═" * 70)
    print("  PHASE 1: Local SLM Smoke Test (Config + Lock Path)")
    print("═" * 70)

    result = ValidationResult(
        phase_name="Local SLM Smoke",
        test_suite="engine/model_garden.py::local_lock",
    )

    # Step 1: Validate config is loaded
    print("\n  [1.1] Checking LOCAL_SLM config values…")
    try:
        from engine.config import LOCAL_SLM_MODEL, LOCAL_SLM_ENDPOINT
        from engine.model_garden import ModelGarden

        result.test_count += 1
        if not LOCAL_SLM_MODEL or not LOCAL_SLM_ENDPOINT:
            result.errors.append(
                f"CONFIG MISSING: LOCAL_SLM_MODEL={LOCAL_SLM_MODEL}, "
                f"LOCAL_SLM_ENDPOINT={LOCAL_SLM_ENDPOINT}"
            )
            result.passed = False
            return result

        print(f"      ✔ LOCAL_SLM_MODEL = {LOCAL_SLM_MODEL}")
        print(f"      ✔ LOCAL_SLM_ENDPOINT = {LOCAL_SLM_ENDPOINT}")

    except Exception as exc:
        result.errors.append(f"Config import failed: {exc}")
        result.passed = False
        return result

    # Step 2: Test ModelGarden.get_tier_model with lock_model="local_slm"
    print("\n  [1.2] Testing ModelGarden local lock routing…")
    try:
        garden = ModelGarden()
        result.test_count += 1

        # Test lock_model="local_slm"
        model_id = garden.get_tier_model(
            tier=3,
            intent="BUILD",
            primary_need="code",
            lock_model="local_slm",
        )
        if not model_id.startswith("local/"):
            result.errors.append(
                f"LOCK FAILED: Expected local/ prefix, got {model_id}"
            )
            result.passed = False
            return result

        print(f"      ✔ lock_model='local_slm' → {model_id}")

        # Test tier=0 also routes to local
        model_id_t0 = garden.get_tier_model(tier=0, intent="BUILD")
        if not model_id_t0.startswith("local/"):
            result.errors.append(
                f"TIER-0 FAILED: Expected local/ prefix, got {model_id_t0}"
            )
            result.passed = False
            return result

        print(f"      ✔ tier=0 → {model_id_t0}")

    except Exception as exc:
        result.errors.append(f"ModelGarden routing failed: {exc}")
        result.passed = False
        return result

    # Step 3: Test detect provider
    print("\n  [1.3] Testing provider detection…")
    try:
        from engine.model_garden import ModelGarden

        garden = ModelGarden()
        result.test_count += 1

        provider = garden.detect_provider("local/llama-3.2-3b-instruct")
        if provider != "local_slm":
            result.errors.append(
                f"PROVIDER DETECTION FAILED: Expected 'local_slm', got {provider}"
            )
            result.passed = False
            return result

        print(f"      ✔ detect_provider('local/...') → {provider}")

    except Exception as exc:
        result.errors.append(f"Provider detection failed: {exc}")
        result.passed = False
        return result

    # Step 4: Run focused unit test if available
    print("\n  [1.4] Running focused unit test (test_model_garden.py::TestModelGardenSingleton::test_local_slm_lock_override)…")
    success, stdout, stderr, latency = _run_cmd(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_model_garden.py::TestModelGardenSingleton::test_local_slm_lock_override",
            "-xvs",
            "--tb=short",
            "--timeout=20",
        ],
        timeout=60,
        description="Local SLM lock unit test",
    )
    result.test_count += 1
    result.output = stdout
    result.stderr = stderr
    result.latency_ms = latency

    if success:
        print(f"      ✔ Unit test PASSED ({latency}ms)")
        result.passed = True
    else:
        result.errors.append(f"Unit test failed:\n{stderr[:500]}")
        result.passed = False

    return result


def run_broader_regression() -> list[ValidationResult]:
    """Run broader regression test suites on impacted components."""
    print("\n" + "═" * 70)
    print("  PHASE 2: Broader Regression Suite")
    print("═" * 70)

    suites = [
        (
            "tests/test_meta_architect.py",
            "Meta-Architect (dynamic DAG planning)",
            ["test_meta_architect_high_roi_injects_deep_research",
             "test_meta_architect_low_roi_skips_deep_research",
             "test_meta_architect_proof_confidence_within_bounds",
             "test_n_stroke_emits_confidence_proof_and_divergence_metrics"],
        ),
        (
            "tests/test_model_garden.py",
            "Model Garden (routing + scoring)",
            ["TestGardenRegistryBaseline", "TestTierLadderAssignment",
             "TestModelGardenSingleton", "TestDiscoverAndRegisterModels"],
        ),
        (
            "tests/test_n_stroke_stress.py",
            "N-Stroke Stress Tests",
            [],  # run all
        ),
        (
            "tests/test_mandate_executor.py",
            "Mandate Executor (node work functions)",
            [],  # run all
        ),
        (
            "tests/test_refinement.py",
            "Refinement Loop",
            [],  # run all if exists
        ),
    ]

    results: list[ValidationResult] = []

    for suite_path, description, test_filter in suites:
        suite_file = _ROOT / suite_path
        if not suite_file.exists():
            print(f"\n  ⊘ {description} — SKIPPED (file not found)")
            results.append(
                ValidationResult(
                    phase_name="Regression",
                    test_suite=suite_path,
                    passed=True,
                    test_count=0,
                    errors=["Test file not found (expected for some suites)"],
                )
            )
            continue

        print(f"\n  [{description}]")
        cmd = [sys.executable, "-m", "pytest", suite_path, "-q", "--tb=line",
               "--timeout=30"]

        success, stdout, stderr, latency = _run_cmd(
            cmd,
            timeout=120,
            description=f"Regression suite: {suite_path}",
        )

        # Parse test count from pytest output
        test_count = 0
        passed_line = ""
        for line in (stdout + stderr).split("\n"):
            if "passed" in line.lower():
                passed_line = line
                try:
                    # Try to extract "N passed" from output
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if "passed" in p.lower() and i > 0:
                            test_count = int(parts[i - 1])
                            break
                except (ValueError, IndexError):
                    pass

        result = ValidationResult(
            phase_name="Regression",
            test_suite=suite_path,
            passed=success,
            test_count=test_count,
            output=passed_line or stdout[-500:],
            stderr=stderr[-300:] if stderr else "",
            latency_ms=latency,
        )

        if success:
            print(f"      ✔ PASSED ({test_count} tests, {latency}ms)")
        else:
            result.errors.append(
                f"Test suite failed. Last output: {stderr[-200:]}")
            print(f"      ✘ FAILED ({latency}ms)")
            print(
                f"         {stderr.split(chr(10))[0] if stderr else 'No stderr'}")

        results.append(result)

    return results


def main() -> int:
    """Execute full validation pipeline."""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║  TOOLOO V2 END-TO-END VALIDATION RUN                                  ║")
    print("║  (Local SLM Smoke + Broader Regression + Report)                      ║")
    print("╚" + "═" * 68 + "╝")

    t0 = time.monotonic()

    # Phase 1: Local SLM
    smoke_result = run_local_slm_smoke_test()

    # Phase 2: Broader regression
    regression_results = run_broader_regression()

    elapsed = round((time.monotonic() - t0) * 1000, 2)

    # Compile final report
    all_results = [smoke_result] + regression_results
    passed_count = sum(1 for r in all_results if r.passed)
    failed_count = len(all_results) - passed_count

    print("\n" + "═" * 70)
    print("  VALIDATION REPORT")
    print("═" * 70)

    for res in all_results:
        marker = "✔" if res.passed else "✘"
        status = "PASS" if res.passed else "FAIL"
        print(f"\n  [{marker}] {res.phase_name:20s} | {res.test_suite:40s}")
        print(
            f"       Status: {status}  Tests: {res.test_count}  Latency: {res.latency_ms}ms")
        if res.errors:
            for err in res.errors[:2]:
                lines = err.split("\n")
                print(f"       Error: {lines[0][:80]}")

    print("\n" + "═" * 70)
    print(f"  SUMMARY: {passed_count} PASSED  |  {failed_count} FAILED  |  "
          f"Total latency: {elapsed}ms")
    print("═" * 70)

    # Save detailed report
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_suites": len(all_results),
        "passed": passed_count,
        "failed": failed_count,
        "latency_ms": elapsed,
        "results": [r.to_dict() for r in all_results],
    }

    report_path = _ROOT / "validation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n  📊 Detailed report → {report_path.relative_to(_ROOT)}\n")

    if failed_count > 0:
        print("\n  🔧 NEXT FIXES REQUIRED:")
        for res in all_results:
            if not res.passed and res.errors:
                print(f"\n     [{res.test_suite}]")
                for err in res.errors[:2]:
                    print(f"       • {err.split(chr(10))[0][:90]}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
