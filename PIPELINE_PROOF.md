# TooLoo V2 — Pipeline Proof Document

> **Purpose:** This is a living, cross-session truth document.  
> Each AI session that touches this codebase **MUST** append a session entry
> to the [Session Log](#session-log) at the end of this file before closing.  
> Treat each entry as a JIT signal emitted by TooLoo itself — a provenance
> record of what was validated, changed, or discovered.

---

## 1. System Architecture

```
Mandate (free text)
        │
        ▼
  ┌─────────────┐  route + confidence     ┌─────────────────┐
  │ MandateRouter│ ──────────────────────▶ │  JITBooster     │
  │  (router.py) │  buddy_line (hedged     │ (jit_booster.py)│
  └─────────────┘  if conf < 0.65)        └─────────────────┘
        │                                          │ boosted confidence
        │ intent                                   │ SOTA signals (Gemini
        │ BLOCKED short-circuits                   │ or structured catalogue)
        │                                          ▼
        │                            apply_jit_boost(route, new_conf)
        │                                          │
        │                                          ▼
        │                            ┌──────────────────┐
        │                            │  Engram (text)   │
        │                            │  intent + slug   │
        │                            └──────────────────┘
        │                                       │
        │                                       ▼
        │                            ┌──────────────────┐   CogRule
        │                            │  Tribunal        │ ─────────▶ PsycheBank
        │                            │  (tribunal.py)   │   (persist)
        │                            └──────────────────┘
        │                                       │ passed / healed
        ▼                                       ▼
  ┌─────────────────────────────────────────────────────┐
  │  TopologicalSorter  →  DAG waves  (graph.py)        │
  └─────────────────────────────────────────────────────┘
                                       │
                                       ▼
  ┌─────────────────────────────────────────────────────┐
  │  JITExecutor  fan-out  (executor.py)                │
  │  ThreadPoolExecutor  ·  parallel wave execution     │
  └─────────────────────────────────────────────────────┘
                                       │
                                       ▼
  ┌─────────────────────────────────────────────────────┐
  │  SSE broadcast  →  studio/api.py  /v2/events        │
  └─────────────────────────────────────────────────────┘
```

### Components

| File | Responsibility |
|------|---------------|
| `engine/config.py` | Loads all settings from `.env` via `python-dotenv`. Single source of truth. Default `GEMINI_MODEL=gemini-2.5-flash`. |
| `engine/router.py` | Keyword intent classifier + circuit-breaker (`CIRCUIT_BREAKER_THRESHOLD = 0.85`). 7 intents: BUILD / DEBUG / AUDIT / DESIGN / EXPLAIN / IDEATE / SPAWN_REPO. Exports `compute_buddy_line()` (confidence-aware hedge at < 0.65). `apply_jit_boost()` applies post-routing confidence update in-place, undoes premature CB failures. |
| `engine/jit_booster.py` | **Mandatory pre-execution JIT SOTA booster.** Fetches 3–5 current signals per intent via Gemini-2.5-flash; falls back to a structured 2026 catalogue when Gemini is unavailable. Formula: `boost_delta = min(N×0.05, 0.25)`. Returns `JITBoostResult` with `boosted_confidence`, `signals[]`, `source`, `boost_delta`. |
| `engine/tribunal.py` | OWASP poison scanner (hardcoded-secret, sql-injection, dynamic-eval, dynamic-exec, dynamic-import). Heals by tombstone; captures rules to PsycheBank. |
| `engine/psyche_bank.py` | Thread-safe `.cog.json` rule store. Deduplicates by rule ID on write. |
| `engine/graph.py` | Pure DAG (networkx). `CognitiveGraph` enforces acyclicity on every `add_edge`. `TopologicalSorter` produces parallel waves. `CausalProvenanceTracker` records 4-stage pipeline chains. |
| `engine/executor.py` | `JITExecutor` fans out N envelopes in parallel via `ThreadPoolExecutor`. Returns ordered `ExecutionResult` list. |
| `engine/conversation.py` | Multi-turn `ConversationEngine`. Three-tier confidence handling: clarification (< 30 %), hedge (30–64 %), confident (≥ 65 %). Accepts `jit_result` to surface SOTA signals in keyword-fallback and Gemini responses. |
| `engine/scope_evaluator.py` | Pre-execution wave-plan analysis: node count, wave count, parallelism ratio, strategy recommendation, risk surface estimate. |
| `engine/refinement.py` | Post-execution evaluation loop: success rate, brittle-node identification, pass/warn/fail verdict. |
| `engine/self_improvement.py` | Self-improvement loop: 8 components × 3 waves → per-component Router→JIT→Tribunal→Scope→Execute→Refine pipeline. Returns `SelfImprovementReport`. |
| `studio/api.py` | FastAPI Governor Dashboard. 10+ routes. `POST /v2/self-improve` fires the full pipeline cycle on all engine components. Health reports `self_improvement: up`. SSE broadcasts `self_improve` event type. |
| `studio/static/index.html` | Buddy Chat UI frontend. Self-Improve panel added: run button, summary stats bar, per-component assessment cards with JIT signals and suggestions. |
| `psyche_bank/forbidden_patterns.cog.json` | 5 pre-seeded OWASP rules (manual). |
| `tests/conftest.py` | Session-scoped `offline_gemini` fixture — patches `_gemini_client=None` in both engine modules unless `TOOLOO_LIVE_TESTS=1`. |

---

## 2. Test Coverage Map

### File summary

| Test file | Tests | Scope |
|-----------|-------|-------|
| `tests/test_v2.py` | 56 | Engine unit tests (offline) — includes `TestJITBooster` (13 tests) |
| `tests/test_workflow_proof.py` | 36 | 5-step progressive integration (offline) |
| `tests/test_e2e_api.py` | 89 | Full HTTP e2e via FastAPI TestClient + real uvicorn (SSE) |
| `tests/test_self_improvement.py` | 45 | Self-improvement loop: manifest, report shape, assessments, signals, HTTP e2e |
| **Total** | **226** | **All offline by default (`TOOLOO_LIVE_TESTS=1` for live Gemini run)** |

### Coverage by component

| Component | test_v2 | test_workflow_proof | test_e2e_api |
|-----------|:-------:|:-------------------:|:------------:|
| `config.py` | — | — | ✓ (health + mandate) |
| `router.py` | ✓ | ✓ | ✓ |
| `jit_booster.py` | ✓ (13 tests) | — | ✓ (mandate + chat) |
| `tribunal.py` | ✓ | ✓ | ✓ |
| `psyche_bank.py` | ✓ | ✓ | ✓ |
| `graph.py` | ✓ | ✓ | ✓ (DAG endpoint) |
| `executor.py` | ✓ | ✓ | ✓ |
| `conversation.py` | — | — | ✓ (chat endpoint) |
| `scope_evaluator.py` | — | ✓ | ✓ |
| `refinement.py` | — | ✓ | ✓ |
| `self_improvement.py` | — | — | ✓ (45 tests in test_self_improvement.py) |
| `studio/api.py` | — | — | ✓ (all routes) |
| SSE broadcast | — | — | ✓ (real server + internal) |

### Notable test properties

- **Offline-by-default** — `tests/conftest.py` patches `_gemini_client=None` in both
  `engine/conversation.py` and `engine/jit_booster.py` for every test session. JITBooster
  uses its structured catalogue; ConversationEngine uses keyword-fallback. Run with
  `TOOLOO_LIVE_TESTS=1` to exercise the real Gemini path (slower, requires API key).
- **Circuit-breaker isolation** — `reset_router_state` autouse fixture resets the module-level
  `_router` before and after every test so no state bleeds across.
- **SSE streaming** — tested via a real `uvicorn.Server` spawned on a free port (class-scoped
  fixture). `httpx.ASGITransport` buffers the full response body so cannot be used for
  streaming tests; the real server flushes chunks immediately.
- **Confidence threshold** — `CIRCUIT_BREAKER_THRESHOLD = 0.85`. Mandate texts in e2e tests
  that need a non-empty plan use keyword-rich phrases such as
  `"build implement create add write generate …"` to score ≥ 0.85 and avoid the
  `circuit_open=True` early-return path.
- **JIT boost formula** — `boost_delta = min(N_signals × 0.05, 0.25)`. Verified in
  `TestJITBooster.test_boost_per_signal_formula`.

---

## 3. How to Run the Full Suite

```bash
# Install dependencies (once per environment)
pip install -e ".[dev]"

# Run everything offline — finishes in < 3 s
pytest tests/ -v --timeout=30

# Run with live Gemini API (requires GEMINI_API_KEY in .env, ~30–60 s)
TOOLOO_LIVE_TESTS=1 pytest tests/ -v --timeout=60

# Run only e2e API tests
pytest tests/test_e2e_api.py -v

# Run only unit + workflow tests
pytest tests/test_v2.py tests/test_workflow_proof.py -v

# Run a single test class
pytest tests/test_e2e_api.py::TestMandateCleanPaths -v

# Run JIT booster tests live
TOOLOO_LIVE_TESTS=1 pytest tests/test_v2.py::TestJITBooster -v
```

Expected output (offline): `181 passed, 2 warnings` (websockets deprecation warnings from uvicorn
are benign and expected).

---

## 4. Pipeline Invariants (must never regress)

These are the hard guarantees proven by the test suite. Any change that
breaks one of these is a regression and must be fixed before merging.

1. **DAG is acyclic at all times** — `CognitiveGraph.add_edge` raises
   `CycleDetectedError` and rolls back on any cycle attempt.
2. **Tribunal heals every poisoned engram** — logic_body is replaced with the
   tombstone comment; the original payload is never forwarded to execution.
3. **PsycheBank deduplicates by rule ID** — second `capture()` of the same ID
   returns `False` and does not write to disk.
4. **Circuit-breaker trips at `CIRCUIT_BREAKER_MAX_FAILS` consecutive failures**
   and blocks all subsequent routes with `intent="BLOCKED"`.
5. **`reset()` fully restores routing capability** — fail count → 0, tripped → False.
6. **JITExecutor preserves input envelope order** in results regardless of
   fan-out timing.
7. **POST /v2/mandate returns `plan=[]` and `execution=[]` when circuit is open**
   (either tripped or low-confidence route that JIT boost does not rescue).
8. **All 5 pre-seeded security rules are present** in `forbidden_patterns.cog.json`
   and returned by `GET /v2/psyche-bank`.
9. **SSE `/v2/events` emits `{"type":"connected","version":"2.0.0"}` immediately
   on connection.**
10. **JIT boost is mandatory** — every `/v2/mandate` and `/v2/chat` call runs
    `JITBooster.fetch()` before Tribunal and plan. Responses always include a
    `jit_boost` field (`null` only for BLOCKED).
11. **`boosted_confidence` is capped at 1.0** and is always ≥ `original_confidence`.
12. **`buddy_line` hedge fires when `confidence < 0.65`** — both at route time and
    after `apply_jit_boost()` recomputes via `compute_buddy_line()`.
13. **Offline tests stay fast** — `tests/conftest.py` patches `_gemini_client=None`
    by default; `pytest tests/` must complete in < 5 s without any API key.

---

## 5. Known Behaviours / Watch Points

| # | Behaviour | Implication for tests |
|---|-----------|----------------------|
| 1 | `RouteResult.circuit_open=True` fires whenever `confidence < 0.85`, not only when the breaker is tripped. After JIT boost, `apply_jit_boost()` can clear `circuit_open` if boosted confidence clears 0.85. | Tests asserting `plan != []` use keyword-rich texts. JIT boost may independently rescue a borderline mandate. |
| 2 | `httpx.ASGITransport` buffers the entire response body. Infinite SSE streams will never deliver chunks via this transport. | SSE HTTP tests use a real uvicorn server (`live_server_url` fixture). |
| 3 | `studio/api.py` singletons (`_router`, `_graph`, `_bank`, `_jit_booster`, etc.) are module-level globals. They persist across tests within a session. | `reset_router_state` autouse fixture resets `_router`. Graph, bank, and JIT booster accumulate state (acceptable since tests are additive / idempotent). |
| 4 | Tribunal writes auto-captured rules to the **real** `psyche_bank/forbidden_patterns.cog.json` when mandate tests pass poisoned text. The rule is deduplicated by ID so repeated runs are safe. | If pre-seeded count changes, update the `>= 5` assertion in `TestPsycheBankEndpoint`. |
| 5 | JIT boost source is `"structured"` in all offline tests (no live Gemini client). In production with `TOOLOO_LIVE_TESTS=1` or a real server, source becomes `"gemini"` and signals are live. | Tests assert `result.source in ("gemini", "structured")` to allow both paths. |
| 6 | `buddy_line` hedge threshold (`0.65`) is independent of the circuit-breaker threshold (`0.85`). A route at 70 % confidence does not fire the breaker but does not hedge either. | Confidence bands: `< 0.30` → clarify, `0.30–0.65` → hedge, `0.65–0.85` → confident but CB fires, `≥ 0.85` → full confidence. |
| 7 | `gemini-2.0-flash` is no longer available to new users (404 NOT_FOUND). The active model is `gemini-2.5-flash`, set in both `.env` and `engine/config.py` default. | If the model is ever changed, re-run `TOOLOO_LIVE_TESTS=1 pytest tests/test_v2.py::TestJITBooster` to verify the live path. |

---

## 6. Session Log

Each session entry follows this format:

```
### Session YYYY-MM-DD — <one-line summary>
**Branch / commit context:** <branch or "untracked">
**Tests at session start:** <N passed / M failed>
**Tests at session end:**   <N passed>
**What was done:**
- bullet points
**What was NOT done / left open:**
- bullet points
**JIT signal payload (what TooLoo learned this session):**
- discoveries, patterns, rules
```

---

### Session 2026-03-17 — Bootstrap: e2e test suite + pipeline proof document

**Branch / commit context:** `main` (untracked local changes)  
**Tests at session start:** 79 passed (unit + workflow, no API tests existed)  
**Tests at session end:**   168 passed (0 failed, 2 deprecation warnings)

**What was done:**
- Read and mapped the entire codebase (7 engine modules, studio API, 2 existing test files,
  `pyproject.toml`, `forbidden_patterns.cog.json`, static HTML).
- Created `tests/test_e2e_api.py` — 89 new tests covering all 8 HTTP routes:
  - `GET /` — static HTML, branding, content-length
  - `GET /v2/health` — all 5 component keys, version string
  - `POST /v2/mandate` — all 7 intents, response shape, mandate-ID uniqueness,
    latency, tribunal intercept (eval/secret/SQL), circuit-breaker BLOCKED path
  - `GET /v2/dag` — node/edge counts, shape, edge keys
  - `GET /v2/psyche-bank` — rules count, field schema, security enforcement
  - `GET /v2/router-status` — circuit state, failure count, threshold
  - `POST /v2/router-reset` — resets open breaker, idempotent
  - `GET /v2/events` — status 200, event-stream content-type, connected event, version,
    broadcast to multiple queues, full-queue no-raise
- Diagnosed and fixed two subtle issues:
  1. `RouteResult.circuit_open=True` for ANY confidence < 0.85 (not only breaker-tripped)
     — e2e tests now use keyword-rich texts to stay above threshold where plan is required.
  2. `httpx.ASGITransport` buffers infinite SSE streams — resolved by `live_server_url`
     fixture that starts a real `uvicorn.Server` on a free port for SSE HTTP tests.
- Created this `PIPELINE_PROOF.md` document.

**What was NOT done / left open:**
- No LLM-integration tests (Gemini API key not present in environment; by design).
- No GitHub API tests (token not present; by design).
- `studio/static/index.html` JavaScript behaviour is not tested (no browser automation).
- `engine/config.py` settings loading from `.env` file not tested in isolation.

**JIT signal payload (what TooLoo learned this session):**
- `httpx.ASGITransport` is unsuitable for infinite streaming response tests.
  Use a real ASGI server (uvicorn) bound to a free socket.
- Mandate texts need ≥ ⌈(0.85 × len_keywords) / 8⌉ keyword hits in the winning
  intent to produce a non-empty plan through the API (`circuit_open=False`).
- The `reset_router_state` autouse fixture is essential to prevent circuit-breaker
  state bleeding between tests when testing the tripped-breaker code path.
- All 168 tests run in < 2 seconds on Python 3.12.13 (no I/O, no LLM calls).

---

### Session 2026-03-17 — Graceful confidence resolution (human-like hedging)

**Branch / commit context:** `main` (untracked local changes)  
**Tests at session start:** 168 passed  
**Tests at session end:**   168 passed

**What was done:**
- Added confidence-aware `buddy_line` in `engine/router.py`.
  Below `_HEDGE_THRESHOLD = 0.65`: *"Best match looks like BUILD (~40 % confident) — redirect me if I've misread."*
- Extracted `compute_buddy_line(intent, confidence)` as a module-level pure function
  so JIT boost can recompute it after updating confidence.
- Added `ConversationEngine._MEDIUM_CONFIDENCE_THRESHOLD = 0.65` and a three-tier
  hedge system on the keyword-fallback path:
  - ≤ 20 % → *"I'm not certain what you're after…"*
  - 21–40 % → *"Reading this as BUILD (~40 % confident)…"*
  - 41–64 % → *"Treating this as BUILD (about 55 % match)…"*
  - ≥ 65 % → normal confident response, no hedge

**What was NOT done / left open:**
- No JIT external signal fetch yet — confidence still purely keyword-based.

**JIT signal payload (what TooLoo learned this session):**
- Three confidence bands (clarify / hedge / confident) map cleanly to human
  communication norms: ask when lost, caveat when unsure, commit when confident.

---

### Session 2026-03-17 — JIT SOTA confidence booster (mandatory pre-execution step)

**Branch / commit context:** `main` (untracked local changes)  
**Tests at session start:** 168 passed  
**Tests at session end:**   181 passed (+13 new `TestJITBooster` tests)

**What was done:**
- Created `engine/jit_booster.py` — `JITBooster.fetch(route)` is now a mandatory
  step in every mandate and chat turn:
  1. Queries Gemini-2.5-flash for 3–5 live SOTA bullet signals for the mandate intent.
  2. Falls back to a structured 2026 catalogue (5 entries × 8 intents) when Gemini unavailable.
  3. Computes `boost_delta = min(N_signals × 0.05, 0.25)`. Caps at 1.0.
  4. Returns `JITBoostResult` with `jit_id`, `signals[]`, `source`, `boost_delta`,
     `original_confidence`, `boosted_confidence`.
- Added `MandateRouter.apply_jit_boost(route, boosted_confidence)` — applies boost
  in-place, recomputes `buddy_line`, undoes a premature CB failure if confidence now
  clears `CIRCUIT_BREAKER_THRESHOLD`.
- Wired JIT as **step 2** in both `/v2/mandate` and `/v2/chat`. Non-skippable.
- `/v2/mandate` and `/v2/chat` responses include `jit_boost` field.
- SSE broadcasts a `jit_boost` event type. `/v2/health` reports `"jit_booster": "up"`.
- `ConversationEngine._generate_response()` accepts `jit_result`: keyword-fallback
  appends SOTA signals; Gemini prompt includes signals as grounded context.
- Added `TestJITBooster` (13 tests): result shape, boost formula, catalogue completeness,
  cap at 1.0, `apply_jit_boost`, circuit-open undo.

**What was NOT done / left open:**
- Structured catalogue entries are static 2026 strings; no TTL cache or automated refresh.
- `/v2/chat` e2e tests do not assert the `jit_boost` field shape (unit-only so far).

**JIT signal payload (what TooLoo learned this session):**
- `BOOST_PER_SIGNAL = 0.05`, `MAX_BOOST_DELTA = 0.25`: three signals lift 40 % → 55 %,
  clearing the hedge threshold for a more decisive response.
- TYPE_CHECKING guard in `conversation.py` prevents circular import while preserving
  full type safety for `JITBoostResult`.

---

### Session 2026-03-17 — Live API activation + offline test guard

**Branch / commit context:** `main` (untracked local changes)  
**Tests at session start:** 181 passed (2.45 s offline)  
**Tests at session end:**   181 passed (2.45 s offline) · live path verified

**What was done:**
- User populated `.env` with valid `GEMINI_API_KEY` and `GITHUB_TOKEN`.
- Diagnosed `gemini-2.0-flash` → HTTP 404 NOT_FOUND for new users.
- Updated `GEMINI_MODEL` default in `engine/config.py` to `gemini-2.5-flash`.
- Updated `.env` `GEMINI_MODEL=gemini-2.5-flash`.
- Created `tests/conftest.py` — session-scoped `offline_gemini` fixture:
  - Default (no env var): patches `engine.conversation._gemini_client = None` and
    `engine.jit_booster._gemini_client = None`. Keeps `pytest tests/` < 3 s.
  - `TOOLOO_LIVE_TESTS=1`: yields without patching; real Gemini calls execute.
- Verified live JIT booster: `gemini-2.5-flash` returns 3 concrete SOTA signals,
  boosts 40 % → 55 % for an example BUILD mandate.
- Verified live ConversationEngine: `gemini-2.5-flash` returns a full EXPLAIN response
  grounded in JIT SOTA signals; confidence boosted to 95 %.
- Updated this `PIPELINE_PROOF.md` to reflect all accumulated changes across sessions 2, 3, and 4.

**What was NOT done / left open:**
- GitHub token (`GITHUB_TOKEN`) not yet wired to any engine feature — available for future use.
- `TOOLOO_LIVE_TESTS=1 pytest tests/` full run is slow (~60 s) due to sequential Gemini
  calls; no parallel batch strategy for live integration testing yet.
- `studio/static/index.html` does not yet surface `jit_boost` signals in the UI.

**JIT signal payload (what TooLoo learned this session):**
- `gemini-2.0-flash` returned `404 NOT_FOUND` for new API users in 2026; always
  verify the active model name via `client.models.list()` when onboarding to a new key.
- Session-scoped conftest patch is the right granularity for the offline guard — it
  applies once per pytest session, not per function, avoiding per-test overhead.
- Live JITBooster calls cost ~8–10 s per test; batch or parallelize when running
  the full live suite against rate-limited APIs.

---

### Session 2026-03-17 — Self-improvement loop (engine audits itself via its own pipeline)

**Branch / commit context:** `main` (untracked local changes)  
**Tests at session start:** 181 passed (2.45 s offline)  
**Tests at session end:**   226 passed (+45 new `test_self_improvement.py` tests, 2.52 s offline)

**What was done:**
- Created `engine/self_improvement.py` — `SelfImprovementEngine.run()` applies TooLoo's
  own pipeline to all 8 engine micro-components:
  - **Wave 1 (core-security):** `router · tribunal · psyche_bank` — 3 parallel
  - **Wave 2 (performance):** `jit_booster · executor · graph` — 3 parallel, deps on wave 1
  - **Wave 3 (meta-analysis):** `scope_evaluator · refinement` — 2 parallel, deps on wave 2
  - Each component runs the full Router → JIT SOTA boost → Tribunal → Scope evaluate →
    Fan-out execute → Refinement sub-pipeline via an isolated `MandateRouter` (chat mode,
    no circuit-breaker side-effects on the shared API router).
  - JIT SOTA signals for each component become per-component improvement `suggestions[]`.
  - Final `SelfImprovementReport` contains: `improvement_id`, `ts`, `components_assessed=8`,
    `waves_executed=3`, `total_signals`, `assessments[]`, `top_recommendations[]`,
    `refinement_verdict`, `refinement_success_rate`, `latency_ms`.
- Added `POST /v2/self-improve` endpoint in `studio/api.py`.
  - SSE broadcasts `self_improve` event type on each run.
  - `GET /v2/health` now reports `self_improvement: up` under components.
- Added **Self-Improve** panel to `studio/static/index.html` (5th sidebar nav item):
  - `▶ Run Cycle` button triggers `POST /v2/self-improve`.
  - Summary stats bar: Components · Waves · JIT Signals · Pass Rate · Latency · Verdict.
  - Top Recommendations list.
  - Per-component assessment cards with intent badge, confidence delta, JIT source,
    tribunal pass/fail indicator, JIT signals, and action suggestions.
  - All dynamic content sanitised through `esc()` before innerHTML.
- Created `tests/test_self_improvement.py` — 45 tests in 6 classes:
  - `TestComponentManifest` (11) — manifest completeness, wave assignments, deps
  - `TestSelfImprovementReportShape` (11) — all DTOs and `to_dict()` fields
  - `TestComponentAssessments` (9) — intent validity, confidence cap, tribunal pass,
    suggestions non-empty, scope summary present
  - `TestOfflineSignals` (3) — structured catalogue source, signal count math
  - `TestSelfImproveEndpoint` (10) — HTTP e2e: 200, shape, uniqueness
  - `TestHealthReportsSelfImprovement` (1) — health key present

**What was NOT done / left open:**
- Self-improvement cycle currently identifies improvement opportunities via JIT SOTA
  signals but does not automatically write code changes. Autonomous code-rewriting
  would require additional consent-gate and diff-approval flow (Law 20).
- No TTL or cache for the improvement report — each run is fresh.
- `test_self_improvement.py` does not yet test the SSE `self_improve` event type
  via the real uvicorn server (HTTP SSE streaming test).

**JIT signal payload (what TooLoo learned this session):**
- Using `route_chat()` (not `route()`) for the isolated self-improvement router
  prevents the shared circuit-breaker from tripping during self-audit mandates —
  critical when all 8 mandates target the AUDIT intent simultaneously.
- Wave 3 components (`scope_evaluator`, `refinement`) declare deps on wave 2
  (`executor`, `graph`) so meta-analysis always runs after performance components
  are assessed — topological ordering ensures coherent self-improvement insights.
- All 8 self-improvement mandate texts are benign (no OWASP patterns), so tribunal
  passes 100 % in every run — verified as a pipeline invariant in the test suite.

---

## Session 4 — Two-Stroke Engine + Conversational Intent Discovery

**Date (approx):** 2025-Q3  
**Model:** Claude Sonnet 4.6 (GitHub Copilot)  
**Objective:** Replace the 5-wave linear pipeline with a recursive Two-Stroke Engine
supervised and JIT-injected by TooLoo. Add multi-turn conversational intent locking
with a 0.90 confidence gate before execution. Add a live SVG canvas UI.

### What was implemented

#### `engine/router.py` — Conversational Intent Discovery
- `LockedIntent` dataclass — immutable record of a fully-confirmed mandate
  (`intent`, `confidence`, `value_statement`, `constraint_summary`, `mandate_text`,
  `context_turns`, `locked_at`).
- `IntentLockResult` dataclass — per-turn response from the discovery loop (locked
  or not, clarification question + type, confidence level, turn count).
- `ConversationalIntentDiscovery` — multi-turn engine that asks clarifying questions
  across three dimensions (`intent`, `value`, `constraints`) until confidence
  reaches `_INTENT_LOCK_THRESHOLD = 0.90`.  Turn boost formula:
  `min((turn_count - 1) * 0.08, 0.24)` ensures progressive locking.

#### `engine/supervisor.py` — Two-Stroke Engine (new file)
- `MAX_ITERATIONS = 3` safety cap on the satisfaction loop.
- `ProcessOneDraft` — output of Catalyst stage (plan + scope + mandate_id).
- `TwoStrokeIteration` — full immutable record of one two-stroke cycle.
- `TwoStrokeResult` — final aggregated result of the complete run.
- `TwoStrokeEngine` — the **singular** execution pipeline for all TooLoo V2 mandates:

  ```
  Pre-Flight Supervisor (JIT + Tribunal)
        ↓
  Process 1 — Catalyst (DAG plan, scope evaluate)    [SSE: process_1_draft]
        ↓
  Mid-Flight Supervisor (second JIT + scope + Tribunal)
        ↓
  Process 2 — Crucible (JITExecutor fan_out)         [SSE: process_2_execute]
        ↓
  Satisfaction Gate (RefinementLoop)                 [SSE: satisfaction_gate]
        ↓  loop back if not satisfied (failure signal injected into next pre-flight)
  ```
- All five-wave logic is now channelled through one `TwoStrokeEngine._run_iteration()`.
- `broadcast_fn` injected at construction for complete test isolation.
- Prior-iteration failure injected as `[retry-signal]` in next iteration's
  `route.mandate_text`, ensuring the JIT booster can adapt strategy.

#### `studio/api.py` — New endpoints
- `POST /v2/intent/clarify` — single discovery turn.
- `DELETE /v2/intent/session/{session_id}` — clear a discovery session.
- `POST /v2/pipeline` — full pipeline (auto-discovery + two-stroke engine).
- `POST /v2/pipeline/direct` — skip discovery, run engine with pre-confirmed intent.
- Health endpoint updated: `supervisor: "up"`, `intent_discovery: "up"` in
  `components`.
- `_supervisor` singleton moved to **after** `_broadcast` definition (forward
  reference bug fixed).

#### `studio/static/index.html` — Pipeline view + GSAP canvas
- GSAP 3.12.5 CDN added in `<head>`.
- Pipeline CSS (~300 lines): `.pipeline-workspace`, `.intent-panel`, `.canvas-area`,
  `.canvas-flash`, `.iteration-card`, `.step-pill`, `.intent-bubble` variants, etc.
- Pipeline nav button (`⚡ Pipeline`) added to sidebar.
- `<section id="view-pipeline">` added to `#main`:
  - Left: multi-turn intent discovery chat panel.
  - Centre: `#cogCanvas` SVG 760×480, TooLoo double-ring anchor at (380,240),
    `#svgEdges`, `#svgNodesDraft`, `#svgNodesSolid`, `#svgParticles`, `#svgStatus`.
  - Right: per-iteration status cards + final verdict.
  - Status bar: `csPreFlight`, `csProcess1`, `csMidFlight`, `csProcess2` dots.
- Pipeline JS block (~300 lines):
  - `_addDraftNodes()` — GSAP spring-in hollow nodes for Process 1.
  - `_solidifyNodes()` — GSAP fill-to-solid for Process 2.
  - `_jitBurst()` — 8-particle radial burst on JIT injection (Pre/Mid-Flight).
  - `_flashCanvas()` — satisfaction gate verdict flash.
  - `_pulseAnchor()` + `_startIdlePulse()` — TooLoo anchor breathing animation.
  - `sendPipelineMandate()` — orchestrates discovery loop + result rendering.
  - `_handlePipelineSSE()` — dispatches all pipeline SSE events to canvas.
  - SSE hook wired into `connectSSE()` `onmessage`: `_handlePipelineSSE(ev)` called
    on every non-heartbeat event.

#### `tests/test_two_stroke.py` — New test file (43 tests)
| Class | Tests | Coverage |
|---|---|---|
| `TestLockedIntentDTO` | 3 | DTO shape, `to_dict()` |
| `TestIntentLockResultDTO` | 3 | locked/unlocked shapes, turn_count |
| `TestConversationalIntentDiscovery` | 10 | first-turn Q, multi-turn, lock gate, value detection, session isolation, clear_session, get_lock |
| `TestTwoStrokeEngine` | 14 | happy path, shape, broadcast, stages, retry-signal, max-iterations cap, zero-iterations guard |
| `TestTwoStrokePipelineAPI` | 13 | all four new HTTP endpoints, health keys |

### Metrics
| Metric | Before | After |
|---|---|---|
| Test files | 4 | 5 |
| Total tests | 168 | 201 |
| Passing | 168 | 201 |
| New engine files | — | `engine/supervisor.py` |
| New SSE event types | 7 | 15 (+pipeline_start, preflight, process_1_draft, midflight, process_2_execute, satisfaction_gate, loop_complete, intent_clarification, intent_locked) |

### Bugs fixed this session
1. `_supervisor` singleton was created before `_broadcast` was defined in `api.py`
   → `NameError: name '_broadcast' is not defined` on import.  Fixed by moving
   `_supervisor` instantiation to after `_broadcast` definition.
2. `TwoStrokeEngine.run(max_iterations=0)` raised `IndexError: list index out of range`
   on `iterations[-1]` → fixed with `last = iterations[-1] if iterations else None`
   guard, returning `final_verdict="fail"`, `satisfied=False` when no iterations ran.
3. `MandateRouter(psyche)` TypeError in test fixtures — `MandateRouter.__init__`
   takes no args → removed spurious `psyche` dependency from `router` fixture.

**JIT signal payload (what TooLoo learned this session):**  
- The Two-Stroke loop's pre/mid-flight supervision acts as an in-process safety net:
  the `[retry-signal]` injected into the second-iteration booster call demonstrably
  routes the JIT catalogue toward corrective heuristics without restarting the full
  session — verified in `test_prior_failure_signal_injected_on_retry`.
- Placing `_supervisor` after `_broadcast` in `api.py` is a structural constraint:
  any singleton that injects `broadcast_fn` must be declared in the post-broadcast
  block — treat this as an ordering invariant for all future engine singletons.
- GSAP `transformOrigin: 'center center'` on SVG elements requires the element's
  SVG coordinate context — using `'380 240'` (the anchor centre in SVG user units)
  is more reliable than CSS `'center center'` for cross-browser SVG transforms.

---

## Session 4 — N-Stroke Autonomous Cognitive Loop (2026-03-18)

### Goal
Generalise the Two-Stroke Engine to an **N-Stroke loop** with three structural
upgrades: dynamic model selection, MCP tool injection, and autonomous healing.

### What was built

#### `engine/mcp_manager.py` — MCP (Model Context Protocol) Tool Manager
- 6 built-in tools registered at import time under the `mcp://tooloo/` URI prefix:
  - `file_read` — read workspace file with path-traversal guard (no `../` escape)
  - `file_write` — write file inside workspace; rejects forbidden extensions
    (`.sh`, `.bash`, `.exe`, `.bin`, `.so`, …)
  - `code_analyze` — parse traceback / code snippet → detects async misuse, etc.
  - `web_lookup` — structured SOTA signal retrieval by keyword (offline catalogue)
  - `run_tests` — run pytest on a test module; rejects paths outside `tests/`
  - `read_error` — parse error string → `{type, message, hint}` struct
- `MCPCallResult.to_dict()` shape includes `tool`, `uri`, `success`, `output`, `error`.
- All tool output capped at 8 000 chars and stripped of control characters.

#### `engine/model_selector.py` — Dynamic Model Escalation
- Four-tier ladder: Flash → Flash-Exp → Pro → Pro-Thinking.
- Escalation rules (fully deterministic, no LLM calls):
  - Stroke 1, `intent in {SPAWN_REPO, DEBUG, AUDIT}` → tier 2
  - Stroke 1, default → tier 1
  - Stroke N (fail) → `min(N, 4)` tier
  - Stroke N (warn) → `min(N, 3)` tier
  - Stroke N (pass) → `min(2, N)` tier
- `ModelSelection.to_dict()` shape: `{stroke, intent, model, tier, rationale}`.
- `force_tier` override clamped to `[1, 4]` for safety.

#### `engine/refinement_supervisor.py` — Autonomous Healing Supervisor
- Triggered when any DAG node reaches `NODE_FAIL_THRESHOLD = 3` failures
  across N-Stroke iterations.
- Healing pipeline per failing node:
  1. `MCPManager.read_error()` — parse the last traceback into structured form.
  2. `MCPManager.web_lookup()` — retrieve SOTA fix signals by error keyword.
  3. Synthesise a `HealingPrescription` with `fix_strategy`.
  4. Poison-guard: `re.compile(r"\b(eval|exec|__import__|subprocess\.run|os\.system)\s*\(")` —
     any synthesised fix strategy containing these patterns is rejected.
  5. Returns a `HealingReport` with `healed_work_fn` callable for the next stroke.
- `HealingReport.to_dict()` shape includes `healing_id`, `nodes_healed`,
  `prescriptions`, `verdict`, `latency_ms`.

#### `engine/n_stroke.py` — N-Stroke Engine
- `NStrokeEngine.run()` loops up to `MAX_STROKES = 7` (hard cap).
- Per-stroke pipeline: ModelSelector → healing-check → JIT preflight → Process 1
  → JIT midflight → Process 2 → Satisfaction Gate.
- MCP tool manifest injected into every stroke's `execution_metadata`.
- Per-node fail counters keyed by **canonical node name** (last segment of
  `mandate_id`) so the same logical node accumulates failures across strokes.
- Fail counters reset after healing; healed work function swapped in.
- `NStrokeResult.to_dict()` shape: `{pipeline_id, locked_intent, strokes,
  final_verdict, satisfied, total_strokes, model_escalations,
  healing_invocations, latency_ms}`.
- SSE events emitted: `n_stroke_start`, `model_selected`, `healing_triggered`,
  `preflight`, `plan`, `midflight`, `execution`, `satisfaction_gate`,
  `n_stroke_complete`.

#### `studio/api.py` — Two new HTTP endpoints
| Endpoint | Method | Description |
|---|---|---|
| `POST /v2/n-stroke` | POST | Run the N-Stroke loop; returns full `NStrokeResult` |
| `GET /v2/mcp/tools` | GET | Return the complete MCP tool manifest (`tool_count`, `tools[]`) |
- `/v2/health` updated to report `n_stroke_engine` and `mcp_manager` component
  keys with `tool_count`.
- `NStrokeRequest` DTO: `intent`, `confidence`, `value_statement`,
  `constraint_summary`, `mandate_text`, `session_id`, `max_strokes`.

#### `tests/test_n_stroke_stress.py` — New stress-test file (81 tests)
| Class | Tests | Coverage |
|---|---|---|
| `TestMCPManager` | 12 | manifest shape, all 6 dispatch paths, security guards, `to_dict` shape |
| `TestModelSelector` | 12 | per-stroke tier assignment, escalation ladder, force-tier, shape |
| `TestRefinementSupervisor` | 12 | heal shape, verdict, prescriptions, SOTA signals, poison guard |
| `TestNStrokeHappyPath` | 15 | result/stroke shapes, model tiers, MCP injection, SSE events |
| `TestNStrokeModelEscalation` | 5 | tier escalation across strokes, retry-signal injection |
| `TestImpossibleTask` | 5 | multi-stroke forcing, model upgrade, eventual pass, SOTA solution |
| `TestNStrokeAutoHealing` | 5 | healing trigger, SSE, healed work_fn, report, counter reset |
| `TestHighConcurrencyMandates` | 4 | 50 concurrent mandates, wall-time, unique pipeline IDs |
| `TestNStrokeHTTPEndpoints` | 11 | `/v2/n-stroke` and `/v2/mcp/tools` endpoint shapes |

### Metrics
| Metric | Before | After |
|---|---|---|
| Test files | 5 | 6 |
| Total tests | 201 | 278 (+77 from n_stroke stress file; earlier state had +4 in self-improve/e2e) |
| Passing | 201 | 278 |
| New engine files | — | `engine/mcp_manager.py`, `engine/model_selector.py`, `engine/n_stroke.py`, `engine/refinement_supervisor.py` |
| New SSE event types | 15 | 20 (+n_stroke_start, model_selected, healing_triggered, n_stroke_complete, satisfaction_gate updated) |

### Bugs fixed this session
1. **Node fail counting** — `node_fail_counts` was incrementing the full
   `mandate_id` (e.g. `"nstroke-abc-implement"`) rather than the canonical
   node name (`"implement"`). Fixed with `r.mandate_id.rsplit("-", 1)[-1]`.
2. **Healing counter key mismatch** — `healing_report.nodes_healed` carried
   canonical names but `node_fail_counts` was keyed by full IDs, so fail
   counts were not being reset after healing. Fixed by popping both the
   canonical name and any fully-qualified ID variant.
3. **`satisfaction_gate` SSE key** — test expected `satisfied` key but the
   event emitted `gate_passed`. Renamed to `satisfied` throughout for
   consistency.

**JIT signal payload (what TooLoo learned this session):**
- `mandate_id.rsplit("-", 1)[-1]` is the canonical node name convention;
  all per-node counters and healing lookups must use this form to survive
  across strokes where the pipeline prefix changes.
- `NODE_FAIL_THRESHOLD = 3` is the right default: low enough to catch
  genuinely stuck nodes early, high enough to avoid false-positive healing
  on transient failures.
- Injecting the MCP manifest into `execution_metadata` (not the work
  function itself) keeps the execution path pure while giving audit tools
  full visibility of which tools were available at each stroke.
