# MISSION_CONTROL.md — TooLoo V2 Fast-Boot Situational Awareness

> **For LLMs:** Read this FIRST. Single-page snapshot: goal, state, next task, top rules.
> Update the four sections below each session (replace, don't append).
> Full history → `PIPELINE_PROOF.md`. Full architecture → `README.md`.

---

## Current State

| Key | Value |
|-----|-------|
| **Branch** | `main` |
| **Tests** | 1191 passed / 1 skipped / 0 failed |
| **Live mode** | ✅ ACTIVE — `TOOLOO_LIVE_TESTS=1` set in `.env` |
| **Vertex ADC** | ⚠️ MISSING — using `GEMINI_API_KEY` fallback |
| **StreamInterceptor** | ✅ LIVE — `engine/jit_designer.py` |
| **`/v2/buddy/chat/stream`** | ✅ LIVE — SSE streaming |
| **Mermaid / Typing cursor / N-Stroke bridge** | ✅ COMMITTED |
| **WCAG contrast** | ✅ FIXED — `--text-muted` #8E8EAE, `--text-sec` 0.64 |
| **SSE reconnection** | ✅ HARDENED — retry limit 15, backoff, offline detection |
| **Dead code** | ✅ CLEANED — 50+ SI artifacts removed, gitignore patterns added |
| **Last session** | 2026-03-21 — Operation Awakening (dead code, WCAG, SSE hardening) |

---

## Active Blockers (ranked)

### 🟡 BLOCKER 1 — Vertex ADC JSON missing (degraded to Gemini Direct only)
`_vertex_client` is constructed but all Vertex API calls fail at auth time; system uses `GEMINI_API_KEY` path.
**Fix:** Upload service account JSON and uncomment in `.env`.

### 🟢 Cleared
- ✅ buddy_demo.html streaming stack committed (1e08cd1)
- ✅ Dead code cleaned (50+ SI artifacts, 5 dead root files)
- ✅ WCAG contrast fixed (--text-muted, --text-sec)
- ✅ SSE reconnection hardened (retry limit, backoff, offline detection)
- ✅ Error boundaries added (handleSSE, component render, listener fetch)
- ✅ Test suite: 1191 passed / 1 skipped (was 13 skipped)
---

## Immediate Next Steps

```
1. Start server, verify streaming + N-Stroke + SSE reconnection in browser
2. Add prefers-reduced-motion for logo orb animation (accessibility)
3. Event feed row stagger animation (JS-based animation-delay)
4. Skeleton-placeholder cards while blocks buffer (UX polish)
5. (Optional) Restore Vertex ADC — upload service account JSON
6. Run next ouroboros cycle: python ouroboros_cycle.py
```
---

## JIT Bank (Last 5 Rules)

1. **--text-muted #6A6A8E on dark bg only achieves 2.9:1 contrast** — need #8E8EAE minimum for WCAG AA 4.5:1.
2. **EventSource auto-reconnects on error; manual .close() + setTimeout creates double-connection** — null handlers before close, add retry limit with offline/online detection.
3. **Root-level SI artifacts accumulate fast** — gitignore patterns (`full-cycle-si-*`, `tests/temp_test_*.py`) prevent future tracking.
4. **Ephemeral SI test files that are permanently skipped pollute skip count** — remove them rather than keeping skip markers.
5. **NEVER use `multi_replace_string_in_file` with large CSS blocks** — tool mangles hyphens. Use single targeted `replace_string_in_file` calls.
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

