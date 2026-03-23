# MISSION_CONTROL.md — TooLoo V2 Fast-Boot Situational Awareness

> **For LLMs:** Read this FIRST. Single-page snapshot: goal, state, next task, top rules.
> Update the four sections below each session (replace, don't append).
> Full history → `PIPELINE_PROOF.md`. Full architecture → `README.md`.

---

## Current State
- branch: main
- live-mode status: FULLY OPERATIONAL (Vertex AI live, SA JSON wired)
- Tests: 67 passed, 1 xfailed. All green.
- **Intent-Driven Cognitive OS LIVE**: `LockedIntent` now carries strict `success_criteria`.
- **IntentReconciliationGate** injected directly into N-Stroke Engine using Tier-3 LLM gap evaluation before completing tasks.
- **GlobalAlignmentContext** injected into `MetaArchitect`. Swarm hierarchy is dynamically shaped based on recent user behavior from `psyche_bank/buddy_memory.json`.
- Remaining systems active: DeepIntrospector, Cognitive Dreamer, CognitiveMap ENRICHED.
- Total REST endpoints: ~92.

## Active Blockers
- No critical blockers. System is fully operational.

## Immediate Next Steps
1. **Critical Architecture Objective:** Build out the Tiered Vector-Symbolic Architecture for optimal memory (Hot Memory Buffer, Warm Memory Vector DB, Cold Memory Knowledge Graph) using recursive summarization. Verify and calibrate on outsourced data.
2. **Global Codebase Audit:** Run a comprehensive sweep for duplications, overlaps, conflicts, and confusing code across the entire codebase. Resolve issues and formulate a prevention protocol.
1. Expose the newly tracked metrics (Intent Gap and Remediation) in the Genesis UI / Buddy Chat, allowing explicit conversational overrides if the model gets the user's intent misaligned.
2. Push mandate_executor HC from 0.98 → 0.99
3. Add cascade preview visualization to UI (interactive dependency impact)

*Last updated: 2026-03-22 (DeepIntrospector — full self-awareness engine)*

## JIT Bank (Last 5 Rules)

1. **Intent vs Result**: Execution success is strictly bound to `success_criteria` tracked in `LockedIntent`. Passing unit tests is no longer enough to close a wave if the intent gap remains.
2. **Reconciliation Injection**: Failed intent waves instantly inject `[INTENT GAP DETECTED]` plus a clear proposed remedy back into the N-Stroke `mandate_text`.
3. **Global Alignment Strategy**: The `MetaArchitect` reads global contextual interests from persistent memory *before* constructing the DAG, weighting Swarm Personas (e.g. Sustainer vs Innovator) proactively.
4. **CognitiveMap.to_dict() enrichment is fail-safe** — try/except wraps the lazy import so a DeepIntrospector build failure never breaks the cognitive map REST response.
5. **System health traffic light thresholds** — green: avg_health >= 0.8 AND all critical modules healthy. Yellow: avg >= 0.6. Red: below 0.6.

---

## Engine Quick-Reference

```
Mandate → StanceEngine(detect) → MandateRouter(CB:0.85+overlap) → JITBooster
       → Tribunal(OWASP→Bus:CRITICAL) → TopologicalSorter
       → NStrokeEngine(7 strokes, stance_weights→16D)
            ├─ sync:  JITExecutor.fan_out()
            └─ async: AsyncFluidExecutor.fan_out_dag_async()
       → RefinementLoop → RefinementSupervisor(blast_radius→Bus:WARNING)
```

| What | Where |
|------|-------|
| Config / env vars | `engine/config.py` |
| ~92 API endpoints | `studio/api.py` (search `/v2/`) |
| Deep Introspector | `engine/deep_introspector.py` → `get_deep_introspector()` |
| Notification Bus | `engine/bus.py` → `get_bus()` |
| Cognitive Stance | `engine/stance.py` → `get_stance_engine()` |
| Cognitive Map | `engine/cognitive_map.py` → `get_cognitive_map()` |
| Self-improve loop | `engine/self_improvement.py` → `SelfImprovementEngine` |
| Parallel validation | `engine/parallel_validation.py` → `ParallelValidationPipeline` |
| Autonomous loop | `ouroboros_cycle.py` (gated by `TOOLOO_LIVE_TESTS`) |
| Run tests | `pytest tests/ --ignore=tests/test_ingestion.py --ignore=tests/test_playwright_ui.py` |

*Last updated: 2026-03-22 (DeepIntrospector full wiring)*
