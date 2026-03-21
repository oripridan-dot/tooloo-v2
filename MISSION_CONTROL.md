# MISSION_CONTROL.md — TooLoo V2 Fast-Boot Situational Awareness

> **For LLMs:** Read this FIRST. Single-page snapshot: goal, state, next task, top rules.
> Update the four sections below each session (replace, don't append).
> Full history → `PIPELINE_PROOF.md`. Full architecture → `README.md`.

---

## Current State
- branch: main
- live-mode status: FULLY OPERATIONAL
- Tests: 1191 passed, 1 skipped, 0 failed. All green.
- All core calculators/selectors calibrated (see JIT Bank below).
- Autonomous Phase 1.5 injection loop de-armed (was corrupting engine files).
- Engine recovered from 3 corrupted files (config.py, executor.py, jit_booster.py).

## Active Blockers (ranked)
### 🟢 Cleared
- ✅ **Corrupted engine files**: config.py, executor.py, jit_booster.py — restored from git HEAD.
- ✅ **Duplicate Phase 1.5 injection**: self_improvement.py was calling `_implement_top_assessments` 4× per cycle — fixed.
- ✅ **Miscalibrated calculators/selectors** — all 5 calibrations applied (see JIT Bank).

## Immediate Next Steps
1. Run improvement cycles now that all calculators are calibrated correctly.
2. Optionally gate `_implement_top_assessments` with a single explicit call (not automatic) to resume autonomous SOTA patching safely.

## JIT Bank (Last 5 Rules)

1. **Autonomous file patching = corruption vector**: MCP `patch_apply` chains writing back to engine/ inject raw tool_call JSON, zeroing files. Never let the autonomous loop write to files being actively tested.
2. **RefinementLoop DEV MODE must be off before improvement runs**: Thresholds 0.45/0.25 allowed 25% success = "warn". Production is 0.70/0.50. Now restored.
3. **Validator16D Safety default must meet critical threshold**: Safety=0.80 default (no code) < threshold 0.95 → always blocks autonomous gate. Must be 0.95.
4. **BUILD is a deep intent requiring T2**: Code generation mandates need enhanced flash (T2/gemini-2.5-flash) from stroke 1, not lite (T1). Now in _DEEP_INTENTS.
5. **AUTONOMOUS_CONFIDENCE_THRESHOLD must come from config**: Both validator_16d.py and n_stroke.py must read the same source or they diverge silently.

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
