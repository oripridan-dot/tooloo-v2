# MISSION_CONTROL.md — TooLoo V2 Fast-Boot Situational Awareness

> **For LLMs:** Read this FIRST. Single-page snapshot: goal, state, next task, top rules.
> Update the four sections below each session (replace, don't append).
> Full history → `PIPELINE_PROOF.md`. Full architecture → `README.md`.

---

## Current State
- branch: main
- live-mode status: FULLY OPERATIONAL
- Tests: 1191 passed, 1 skipped, 0 failed. All green.
- Calibration Cycle 2 complete — 5 threshold/constant fixes applied (see JIT Bank).
- All engine calculators/selectors at production-correct values.

## Active Blockers (ranked)
### 🟢 Cleared
- ✅ **Calibration Cycle 2**: MAX_STROKES, NODE_FAIL_THRESHOLD, _INTENT_LOCK_THRESHOLD, proof_confidence ceiling, _SYMBOLIC_RATIO_THRESHOLD — all corrected.
- ✅ **Corrupted engine files**: config.py, executor.py, jit_booster.py — restored from git HEAD (previous session).
- ✅ **Duplicate Phase 1.5 injection**: self_improvement.py was calling `_implement_top_assessments` 4× per cycle — fixed (previous session).
- ✅ **Miscalibrated calculators/selectors** (previous session) — all calibrations applied.

## Immediate Next Steps
1. Run `ouroboros_cycle.py` or `POST /v2/self-improve` — improvement loop is now correctly calibrated at all gate thresholds.
2. Optionally wire `_implement_top_assessments` back as an explicit single call to resume autonomous SOTA patching safely.

## JIT Bank (Last 5 Rules)

1. **MetaArchitect proof_confidence ceiling must reach AUTONOMOUS_CONFIDENCE_THRESHOLD**: Component score caps must mathematically allow best-case weighted sum ≥ 0.99. Prior ceiling was 0.9829 — autonomous gate was structurally unreachable.
2. **NODE_FAIL_THRESHOLD ≤ CIRCUIT_BREAKER_MAX_FAILS**: Healing must trigger before or as the CB trips. Dev-mode inflation (6 vs 3) creates a dead-zone where CB fires but healing never runs.
3. **_INTENT_LOCK_THRESHOLD < CIRCUIT_BREAKER_THRESHOLD is the correct invariant**: Know intent (lock=0.85) before gatekeeping execution (CB=0.90). Equal values create ambiguous dual-trigger semantics.
4. **DEV MODE constant inflation must be reverted before any production run**: MAX_STROKES=12 and NODE_FAIL_THRESHOLD=6 were both dev artifacts left in production code. Always check for "DEV MODE" comments in constants.
5. **Autonomous patch_apply = corruption vector**: MCP `patch_apply` chains writing back to engine/ inject raw tool_call JSON, zeroing files. Never let the autonomous loop write to files being actively tested.

---

## Engine Quick-Reference

```
Mandate → MandateRouter(CB:0.85) → JITBooster → Tribunal(OWASP)
       → TopologicalSorter → NStrokeEngine(7 strokes)
            ├─ sync:  JITExecutor.fan_out()
            └─ async: AsyncFluidExecutor.fan_out_dag_async()
       → RefinementLoop → RefinementSupervisor(auto-heal @ 3 fails)
```

| What | Where |
|------|-------|
| Config / env vars | `engine/config.py` |
| 58 API endpoints | `studio/api.py` (search `/v2/`) |
| Self-improve loop | `engine/self_improvement.py` → `SelfImprovementEngine` |
| Autonomous loop | `ouroboros_cycle.py` (gated by `TOOLOO_LIVE_TESTS`) |
| Fast smoke suite | `tests/test_engine_smoke.py` (34 tests, ~7s, offline) |
| Run tests | `pytest tests/ --ignore=tests/test_ingestion.py --ignore=tests/test_playwright_ui.py` |

*Last updated: 2026-03-21*
