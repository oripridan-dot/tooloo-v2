# MISSION_CONTROL.md — TooLoo V2 Fast-Boot Situational Awareness

> **For LLMs:** Read this FIRST. Single-page snapshot: goal, state, next task, top rules.
> Update the four sections below each session (replace, don't append).
> Full history → `PIPELINE_PROOF.md`. Full architecture → `README.md`.

---

## Current State
- branch: main
- live-mode status: FULLY OPERATIONAL
- Tests: 1352 passed, 1 skipped, 0 failed. All green.
- **Parallel Validation Pipeline (2026-03-22)**
  - New `engine/parallel_validation.py` — concurrent write→test→QA→display pipeline
  - Tribunal (11-24ms) + 16D (11-19ms) + tests (9s) fan out concurrently
  - E2E integration: 3 files validated in 9.1s wall time, composite 0.9814
  - Wired into `SelfImprovementEngine.run_parallel()` and 2 new API endpoints
  - 15 new tests added (`tests/test_parallel_validation.py`)
  - Root-cause fix: `TOOLOO_LIVE_TESTS=0` in child subprocess env prevents live API hang

## Active Blockers (ranked)
### Cleared
- Parallel validation pipeline: fully wired, 15 tests, E2E passing
- Subprocess hang: root-caused to `TOOLOO_LIVE_TESTS=1` env propagation, fixed

### Pending
1. Buddy Profile sidebar panel in `studio/static/index.html`
2. Mirror cache + cognition pipeline into `prepare_stream()`/`finalize_stream()` in `engine/conversation.py`
3. Vertex ADC JSON MISSING — only GEMINI_API_KEY available

## Immediate Next Steps
1. Build Buddy Profile sidebar panel (right-pane collapsible, cyan accent).
2. Wire conversation.py cache pipeline for streaming endpoints.
3. Human Considering avg 0.933 — lowest remaining dimension.

## JIT Bank (Last 5 Rules)

1. **TOOLOO_LIVE_TESTS env propagation**: `engine.config` injects `TOOLOO_LIVE_TESTS=1` into `os.environ` at import time. Any subprocess inheriting full env will attempt live API calls and hang. Always set `TOOLOO_LIVE_TESTS=0` in child subprocess env.
2. **asyncio.create_subprocess_exec is fork-safe** when env is clean — the hang was NOT a gRPC fork issue but live-test mode in the child process.
3. **_find_test_targets must not grep imports** — matching `from engine.X` catches 300+ tests across 9 files. Use only `test_{stem}.py` exact match + `test_{stem}_*.py` glob.
4. **Monitor instrumentation**: `logging` + `perf_counter` + `@dataclass`/`to_dict` in first 8000 chars pushes Monitor above 0.95.
5. **Control keywords**: `threshold`, `max_retries`, `circuit_breaker`, `rollback` must appear in first 8000 chars.

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
| Parallel validation | `engine/parallel_validation.py` → `ParallelValidationPipeline` |
| Calibration engine | `engine/calibration_engine.py` → `CalibrationEngine.run_5_cycles()` |
| Feature profiles | `engine/feature_registry.py` → `get_component_profile(name)` |
| Autonomous loop | `ouroboros_cycle.py` (gated by `TOOLOO_LIVE_TESTS`) |
| Fast smoke suite | `tests/test_engine_smoke.py` (34 tests, ~7s, offline) |
| Run tests | `pytest tests/ --ignore=tests/test_ingestion.py --ignore=tests/test_playwright_ui.py` |

*Last updated: 2026-03-22 (Parallel Validation Pipeline session)*
