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
| `studio/api.py` | FastAPI Governor Dashboard. 9+ routes. **JIT boost is step 2 in both `/v2/mandate` and `/v2/chat`** — mandatory, non-skippable. Responses include `jit_boost` field. SSE broadcasts `jit_boost` event type. Health reports `jit_booster: up`. |
| `studio/static/index.html` | Buddy Chat UI frontend. |
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
| **Total** | **181** | **All offline by default (`TOOLOO_LIVE_TESTS=1` for live Gemini run)** |

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
