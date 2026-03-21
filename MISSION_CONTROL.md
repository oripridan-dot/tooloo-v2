# MISSION_CONTROL.md — TooLoo V2 Fast-Boot Situational Awareness

> **For LLMs:** Read this FIRST. Single-page snapshot: goal, state, next task, top rules.
> Update the four sections below each session (replace, don't append).
> Full history → `PIPELINE_PROOF.md`. Full architecture → `README.md`.

---

## Current State

| Key | Value |
|-----|-------|
| **Branch** | `main` |
| **Tests** | 103 passed (smoke + jit_designer) / 0 failed — prev full suite 1191 |
| **Live mode** | ✅ ACTIVE — `TOOLOO_LIVE_TESTS=1` set in `.env` |
| **Studio API** | ✅ RUNNING — uvicorn port 8000 |
| **Vertex ADC** | ⚠️ COMMENTED OUT — using `GEMINI_API_KEY` fallback |
| **StreamInterceptor** | ✅ LIVE — `engine/jit_designer.py` line-level state machine |
| **`/v2/buddy/chat/stream`** | ✅ LIVE — SSE streaming; yields `token`/`ui_component`/`thought`/`done` |
| **Mermaid rendering** | ✅ NEW — `language='mermaid'` code blocks render as diagrams via mermaid.js v11 |
| **Typing cursor** | ✅ NEW — blinking `.typing-cursor` spans during token streaming; auto-removed on `done` |
| **N-Stroke visual bridge** | ✅ NEW — BUILD/DEBUG keywords route to `/v2/n-stroke`; wave events render in Storybook |
| **Last session** | 2026-03-21 — Mermaid + N-Stroke bridge + typing cursor in buddy_demo.html |

---

## Active Blockers (ranked)

### 🟡 BLOCKER 1 — Vertex ADC JSON missing (degraded to Gemini Direct only)
`_vertex_client` is constructed but all Vertex API calls fail at auth time; system uses `GEMINI_API_KEY` path.
**Fix:** Upload service account JSON → `/workspaces/tooloo-v2/too-loo-zi8g7e-755de9c9051a.json` and uncomment in `.env`.

### � BLOCKER 2 — buddy_demo.html streaming stack uncommitted
All new features (sendMsgStream, appendToken, insertComponent, N-Stroke bridge, mermaid, cursor) are unstaged.
**Fix:** `git add studio/static/buddy_demo.html && git commit -m "feat: streaming stack + mermaid + N-stroke bridge + typing cursor"`

### 🟢 Cleared this session (2026-03-21)
- ✅ Mermaid.js v11 inline rendering — `language='mermaid'` code blocks render as diagrams
- ✅ Typing cursor — blinking `.typing-cursor` during SSE token streaming; auto-removed on `done`
- ✅ N-Stroke visual bridge — BUILD/DEBUG keywords → `/v2/n-stroke`; wave events render in Storybook
- ✅ `sendMsgStream` / `appendToken` / `insertComponent` streaming stack reconstructed in buddy_demo

---

## Immediate Next Steps

```
1. COMMIT: git add studio/static/buddy_demo.html && git commit -m "feat: ..."
2. TEST: start server (port 8000), open /demo, send build/debug mandate → verify N-Stroke path
3. Skeleton-placeholder cards while blocks buffer (UX polish)
4. (Optional) Restore Vertex ADC — upload service account JSON, uncomment in .env
5. Run next ouroboros cycle: python ouroboros_cycle.py
```

---

## JIT Bank (Last 5 Rules)

1. **NEVER use `multi_replace_string_in_file` with large CSS blocks** — tool mangles hyphens throughout the newString (e.g. `border-left` → `border - left`). Use single targeted `replace_string_in_file` calls with minimal context hunks.
2. **Always commit `buddy_demo.html` before session end** — streaming JS is pure frontend, easy to lose via `git checkout`. Uncommitted code was wiped and had to be reconstructed from PIPELINE_PROOF this session.
3. **N-Stroke `/v2/n-stroke` is JSON, not SSE** — wave events broadcast via `/v2/events`; frontend uses existing `EventSource` for live Storybook cards. POST returns `{pipeline_id, result, latency_ms}`.
4. **`mermaid.run({ nodes: [pre] })` requires DOM insertion first** — call via `requestAnimationFrame()` after `container.appendChild(wrap)`; set `pre.textContent` BEFORE calling run, not after.
5. **Typing cursor: use `step-end` timing, not `ease`** — authentic terminal blink requires instantaneous opacity flip. Always store as `b._cursorNode` and `delete b._cursorNode` after removal.

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

