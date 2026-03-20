# MISSION_CONTROL.md — TooLoo V2 Fast-Boot Situational Awareness

> **For LLMs:** Read this FIRST. Single-page snapshot: goal, state, next task, top rules.
> Update the four sections below each session (replace, don't append).
> Full history → `PIPELINE_PROOF.md`. Full architecture → `README.md`.

---

## Current State

| Key | Value |
|-----|-------|
| **Branch** | `main` |
| **Commit** | `cc4d165` |
| **Tests** | 1161 passed / 13 skipped / 0 failed |
| **test_jit_designer** | 50 tests (up from 39) — `TestUIComponent` + `TestParseResponseBlocks` added |
| **Live mode** | ✅ ACTIVE — `TOOLOO_LIVE_TESTS=1` set in `.env` |
| **Studio API** | ✅ RUNNING — uvicorn port 8000 |
| **Vertex ADC** | ⚠️ COMMENTED OUT — using `GEMINI_API_KEY` fallback |
| **ComponentRenderer** | ✅ LIVE — glass cards, timeline, chips, glass table, code block in `buddy_demo.html` |
| **parse_response_blocks** | ✅ LIVE — Markdown parser in `engine/jit_designer.py`; wired into `api.py` |
| **ui_components SSE** | ✅ LIVE — each block broadcast as `type: ui_component` SSE + HTTP `ui_components[]` |
| **Last session** | 2026-07-17 — Dynamic Component Renderer: full HIG/Material DOM bridge |

---

## Active Blockers (ranked)

### 🟡 BLOCKER 1 — Vertex ADC JSON missing (degraded to Gemini Direct only)
`_vertex_client` is constructed but all Vertex API calls fail at auth time; system uses `GEMINI_API_KEY` path.
**Fix:** Upload service account JSON → `/workspaces/tooloo-v2/too-loo-zi8g7e-755de9c9051a.json` and uncomment in `.env`.

### 🟢 Cleared this session
- ✅ `engine/jit_designer.py` — `UIComponent` dataclass, `_strip_inline_md`, `_make_style_directives`, `parse_response_blocks()` Markdown parser (returns `[]` for pure prose)
- ✅ `studio/api.py` — `ui_component` SSE broadcast loop + `ui_components` array in HTTP response
- ✅ `studio/static/buddy_demo.html` — `ComponentRenderer` class (6 factory methods), `buildCompStream()` with grouping logic, full CSS suite (glass cards, timeline, chips, glass table, code block)
- ✅ `finishMsg()` updated — renders `buildCompStream(comps)` when non-prose components detected; falls back to `applyEmphasis()` for plain text
- ✅ `handleSSE()` updated — logs `ui_component` with `{phase: component_type}` detail
- ✅ `tests/test_jit_designer.py` — 11 new tests (50 total); all pass

---

## Immediate Next Steps

```
1. (Optional) Restore Vertex ADC — upload service account JSON, uncomment in .env
2. N-Stroke visual bridge: route BUILD/DEBUG mandates from buddy_demo.html to /v2/n-stroke;
   render SSE events (n_stroke_start → scope → execution → refinement → n_stroke_complete)
   as animated wave cards inside the Thought Storybook panel
3. SSE progressive rendering: stream ui_component fragments into loading bubble as they arrive
   (rather than waiting for HTTP response) — starts rendering as server broadcasts each block
4. Inline mermaid/artifact rendering: detect ```mermaid fences in code_block components;
   render with mermaid.js instead of plain code display
5. Run next ouroboros cycle: python ouroboros_cycle.py
```

---

## JIT Bank (Last 5 Rules)

1. **`parse_response_blocks()` returns `[]` for pure prose** — the empty-list contract signals the frontend to use `applyEmphasis()` instead of component rendering. This avoids wrapping every Buddy message in a `.cr-container`.
2. **Consecutive component grouping in `buildCompStream()`** — `timeline_step` and `insight_chip` must be consumed in a `while` inner loop (not per-element) to produce a single `.cr-timeline` / `.cr-insight-chips` wrapper. The vertical line pseudo-element on `.cr-timeline::before` only works when all steps share one parent.
3. **Transparent bubble for structured content** — when `hasStructured` is true, `b.style.cssText = 'white-space:normal;padding:6px 8px;background:transparent;border:none;box-shadow:none'` must be set to prevent the default `.msg-bub` dark background from appearing behind glass card components.
4. **`finishMsg` appends chips/meta to `lo` (message wrapper), not `b` (bubble)** — when component rendering is active, `b` is transparent; appending the suggestion chips row and meta row to `lo` places them correctly below the component stream.
5. **`applyEmphasis()` escape-first rule** — always call `esc(text)` before regex replacement when producing `innerHTML`. Never apply regex to un-escaped user/LLM text then inject raw.

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

*Last updated: 2026-03-20*

