# MISSION_CONTROL.md — TooLoo V2 Fast-Boot Situational Awareness

> **For LLMs:** Read this FIRST. Single-page snapshot: goal, state, next task, top rules.
> Update the four sections below each session (replace, don't append).
> Full history → `PIPELINE_PROOF.md`. Full architecture → `README.md`.

---

## Current State
- branch: main
- live-mode status: FULLY OPERATIONAL (Vertex AI live, SA JSON wired)
- Tests: **1454 passed, 1 skipped**. All green.
- **Tiered Memory Architecture LIVE**: Hot Memory (BuddyMemory) → Warm Memory (PsycheBank) → Cold Memory (Firestore) pipeline operational.
- **Daemon auto-distill WIRED**: `BackgroundDaemon._cycle()` calls `RecursiveSummaryAgent.distill_pending()` hourly, broadcasting `{"type": "memory_distill", ...}` SSE events.
- **Global dedup audit COMPLETE**: Zero inline `_tokenize/_cosine/_jaccard/atomic_write` implementations remain in `engine/` or `studio/`. All use `engine/persistence.py` and `engine/semantics.py`.
- **buddy_cache.py cleaned**: Removed `_jaccard` wrapper — callers now use `semantics.jaccard_similarity` directly.
- Total REST endpoints: ~94.

## Active Blockers
- No critical blockers. System is fully operational.

## Immediate Next Steps
1. Expose Intent Gap and Remediation metrics in the Genesis UI / Buddy Chat for explicit conversational overrides.
2. Push mandate_executor HC from 0.98 → 0.99
3. Add cascade preview visualization to UI (interactive dependency impact)
4. Wire `engine/persistence.py` and `engine/semantics.py` into the §10 In-Repo Navigation Map in `copilot-instructions.md`.

*Last updated: 2026-03-23 (Daemon distill wired, global dedup audit complete)*

## JIT Bank (Last 5 Rules)

1. **Intent vs Result**: Execution success is strictly bound to `success_criteria` tracked in `LockedIntent`. Passing unit tests is no longer enough to close a wave if the intent gap remains.
2. **ModelGarden.call() vs invoke()**: `ModelGarden` exposes `call(model_id, prompt) → str` (not `invoke()`). Always use `.call()` and work with the returned string directly — no `.text` attribute unwrapping needed.
3. **Zero inline duplicates**: All atomic-write and similarity logic must live in `engine/persistence.py` and `engine/semantics.py`. No inline `_tokenize`/`_jaccard`/`_cosine`/tmp-rename patterns.
4. **Daemon distill SSE type**: `BackgroundDaemon` broadcasts exactly `{"type": "memory_distill", "status": ..., "processed": ..., "facts_extracted": ...}` — not `daemon_rt` — for the hourly distill cycle.
5. **ResourceGovernor in tests**: Container RAM at ~86-87% throttles NStrokeEngine to 2 strokes. Test classes that assert stroke counts must use `_no_throttle` autouse fixture (monkeypatches `get_allowed_strokes` to return `max_strokes`).

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
