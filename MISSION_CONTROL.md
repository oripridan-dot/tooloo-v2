# MISSION_CONTROL.md — TooLoo V2 Fast-Boot Situational Awareness

> **For LLMs:** Read this FIRST. Single-page snapshot: goal, state, next task, top rules.
> Update the four sections below each session (replace, don't append).
> Full history → `PIPELINE_PROOF.md`. Full architecture → `README.md`.

---

## Current State

| Key | Value |
|-----|-------|
| **Branch** | `main` |
| **Tests** | 1161 passed / 13 skipped / 0 failed |
| **Live mode** | ✅ ACTIVE — `TOOLOO_LIVE_TESTS=1` set in `.env` |
| **Studio API** | ✅ RUNNING — `uvicorn studio.api:app` on port 8002 |
| **Self-improve** | ✅ LIVE — si-ba0fcfd7: 17/17 PASS |
| **Vertex ADC** | ⚠️ COMMENTED OUT — using `GEMINI_API_KEY` fallback (no JSON file on disk) |
| **GEMINI_API_KEY** | ✅ Present and active |
| **AUTONOMOUS_EXECUTION_ENABLED** | ✅ `true` (set in `.env`) |
| **Cross-session memory** | ✅ CARVED — `/memories/repo/tooloo-v2-state.md` + `/memories/cross-session.md` |
| **Buddy Demo** | ✅ HIG SOTA — `studio/static/buddy_demo.html` → Apple HIG 2026 + AI-Human Era design |
| **JITDesigner** | ✅ LIVE — `engine/jit_designer.py` wired into `/v2/buddy/chat` + SSE thought events |
| **ActiveListener** | ✅ LIVE — `POST /v2/buddy/listen` (zero-LLM < 5ms, debounced from input) |
| **Last session** | 2026-07-16 — Buddy Phase 3: HIG/SOTA demo app + JITDesigner + ActiveListener |

---

## Active Blockers (ranked)

### 🟡 BLOCKER 1 — Vertex ADC JSON missing (degraded to Gemini Direct only)
`_vertex_client` is constructed but all Vertex API calls fail at auth time; system uses `GEMINI_API_KEY` path.
The service account JSON (`too-loo-zi8g7e-755de9c9051a.json`) does **not** exist on disk and is **not** in any codespace secret. The `GOOGLE_APPLICATION_CREDENTIALS` line in `.env` is commented out.
**Fix:** Create/upload the service account JSON → `/workspaces/tooloo-v2/too-loo-zi8g7e-755de9c9051a.json` and uncomment in `.env`.

### 🟢 Cleared this session
- ✅ `engine/jit_designer.py` — `JITDesigner` + `ThoughtCard` + `DesignDirective` + `analyze_partial_prompt()`
- ✅ `psyche_bank/sota_ui_heuristics.cog.json` — HIG/M3 rules, palette map, animation tokens
- ✅ `POST /v2/buddy/listen` — pure-heuristic active listener (zero LLM, zero latency)
- ✅ `_jit_designer.evaluate()` wired into `buddy_chat_fast_path()` — `design_directive` in HTTP + SSE
- ✅ SSE `thought` events — each `ThoughtCard` broadcast individually as engine executes
- ✅ `studio/static/buddy_demo.html` — full rewrite: Apple HIG 2026, Liquid Glass, Active Listener, Thought Storybook, EQ Avatar
- ✅ `tests/test_jit_designer.py` — 39 tests; all pass
- ✅ `tests/test_buddy_listen.py` — 14 tests; all pass
- ✅ Tests: **1161 passed / 13 skipped / 0 failed**

---

## Immediate Next Steps

```
1. (Optional) Restore Vertex ADC — create service account JSON, place at path in .env, uncomment line
2. N-Stroke visual bridge: route BUILD/DEBUG from buddy_demo.html to /v2/n-stroke;
   render SSE events (n_stroke_start → scope → execution → refinement → n_stroke_complete)
   as animated wave cards inside the Thought Storybook panel
3. Inline artifact rendering: detect mermaid / html_component in Buddy responses;
   render inline (<div class="artifact">) inside the chat bubble
4. VLT patch rendering: map SSE vlt_patch events to 3D spatial glows on thought cards
5. Run next ouroboros cycle: python ouroboros_cycle.py
```

---

## JIT Bank (Last 5 Rules)

1. **JITDesigner is stateless per call** — evaluates intent+EQ+confidence → DesignDirective. No shared mutable state. Rule file hot-reloads on mtime change. Safe for concurrent fan-out (Law 17).
2. **`analyze_partial_prompt()` must never call an LLM** — pure Python heuristics only; fires on every keystroke via debounce. Latency target < 5ms. Intent detection is regex keyword matching, not Gemini.
3. **Active Listener border-color class on textarea** — `bc-clear` / `bc-vague` / `bc-complex` are added to `<textarea>` by JS. CSS defines `border-color` transitions per class. Input aura radial gradient mirrors same level.
4. **ThoughtCard → SSE before HTTP** — each card should be emitted as a `thought` SSE event as the engine runs, *before* the HTTP response is returned. The HTTP fallback (`design_directive.thought_cards`) populates the storybook if SSE was missed.
5. **`applyEmphasis()` in frontend must escape before regex replacement** — call `esc(text)` first, then regex-replace the escaped string. Never apply regex to raw untrusted text then inject as innerHTML.

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

